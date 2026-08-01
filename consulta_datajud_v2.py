import asyncio
import re
import aiohttp
import pandas as pd

# ==============================================================================
# CONFIGURAÇÕES E CONSTANTES
# ==============================================================================
API_KEY = "cDZHYzlZa0JadVREZDJCendQbXY6SkJlTzNjLV9TRENyQk1RdnFKZGRQdw=="
CONCURRENCY_LIMIT = 5  # Requisições simultâneas ao Datajud

# Configurações de Resiliência de Rede
HTTP_TIMEOUT = 30     # Aumentado de 12s para 30s (ideal para instabilidades do TJSP/TJRJ)
MAX_RETRIES = 2       # Se houver timeout ou erro de rede, tenta até +2 vezes antes de desistir

ARQUIVO_ENTRADA = "Busca_Arquivados.xlsx"
ARQUIVO_SAIDA = "Busca_Arquivados_RESULTADO.xlsx"

# Base de códigos TPU de arquivamento já conhecidos de largada
CODIGOS_ARQUIVAMENTO_CONHECIDOS = {246, 861, 22, 10963}

# Cache em memória para não repetir chamadas de rede para um mesmo Código TPU
TPU_CACHE = {}


# ==============================================================================
# WEBSERVICE SGT / CNJ (CONSULTA DINÂMICA DE CÓDIGOS TPU)
# ==============================================================================
async def verificar_tpu_no_sgt(session: aiohttp.ClientSession, codigo_tpu: int, nome_movimento_local: str) -> bool:
    """
    Verifica se um Código TPU representa arquivamento/baixa/extinção.
    Consulta o WebService do SGT do CNJ e armazena o aprendizado em cache.
    """
    if not codigo_tpu:
        # Fallback de texto caso não exista código TPU
        termos = ["arquivad", "arquivament", "definitiv", "baixa definitiv", "baixad"]
        return any(t in nome_movimento_local.lower() for t in termos)

    # 1. Se já é um código famoso de arquivamento, retorna True direto
    if codigo_tpu in CODIGOS_ARQUIVAMENTO_CONHECIDOS:
        return True

    # 2. Se já consultamos esse código nesta execução, pega do cache local
    if codigo_tpu in TPU_CACHE:
        return TPU_CACHE[codigo_tpu]

    # 3. Consulta o WebService do SGT no CNJ para códigos desconhecidos
    url = f"https://sgt.cnj.jus.br/services/movimento/{codigo_tpu}"
    try:
        async with session.get(url, timeout=10) as resp:
            if resp.status == 200:
                dados = await resp.json()
                nome_oficial = (dados.get("nome") or "").lower()
                glossario = (dados.get("glossario") or "").lower()

                # Avalia se a definição oficial do CNJ cita arquivamento ou baixa
                termos_chaves = ["arquiv", "baixa", "extincao", "extinção", "definitiv"]
                eh_arquivamento = any(t in nome_oficial or t in glossario for t in termos_chaves)

                # Salva no Cache em Memória
                TPU_CACHE[codigo_tpu] = eh_arquivamento
                return eh_arquivamento
    except Exception:
        pass  # Em caso de timeout no SGT, recorre ao fallback por texto local

    # Fallback por texto da última movimentação
    termos = ["arquivad", "arquivament", "definitiv", "baixa definitiv", "baixad"]
    eh_arquivamento = any(t in nome_movimento_local.lower() for t in termos)
    TPU_CACHE[codigo_tpu] = eh_arquivamento
    return eh_arquivamento


# ==============================================================================
# ROTEAMENTO DE TRIBUNAIS E REGRAS DE NEGÓCIO
# ==============================================================================
def extrair_sigla_tribunal(numero_cnj: str) -> str:
    """
    Mapeamento correto dos Tribunais pelo padrão do CNJ.
    """
    limpo = re.sub(r"\D", "", str(numero_cnj))
    if len(limpo) != 20:
        return None

    j = limpo[13]
    tr = limpo[14:16]

    # Justiça Estadual (J = 8) - Mapeamento com SP=26 e SE=25 corrigidos
    if j == "8":
        mapa_estaduais = {
            "01": "tjac", "02": "tjal", "03": "tjam", "04": "tjap", "05": "tjba",
            "06": "tjce", "07": "tjdft", "08": "tjes", "09": "tjgo", "10": "tjma",
            "11": "tjmt", "12": "tjms", "13": "tjmg", "14": "tjpa", "15": "tjpb",
            "16": "tjpr", "17": "tjpe", "18": "tjpi", "19": "tjrj", "20": "tjrn",
            "21": "tjrs", "22": "tjro", "23": "tjrr", "24": "tjsc", "25": "tjse",
            "26": "tjsp", "27": "tjto"
        }
        return mapa_estaduais.get(tr)
    elif j == "5":  # Justiça do Trabalho
        return f"trt{int(tr)}"
    elif j == "4":  # Justiça Federal
        return f"trf{int(tr)}"
    elif j == "3":  # STJ
        return "stj"

    return None


async def classificar_status(session: aiohttp.ClientSession, movimentos: list) -> tuple:
    """
    Analisa a movimentação mais recente usando Inteligência de TPU e SGT.
    """
    if not movimentos:
        return "ATIVO", ""

    # Ordena movimentos por dataHora (mais recente primeiro)
    movs_ordenados = sorted(
        movimentos, key=lambda x: x.get("dataHora", ""), reverse=True
    )

    ultimo_mov = movs_ordenados[0]
    nome_mov = (ultimo_mov.get("nome") or ultimo_mov.get("nomeMovimento") or "").lower()
    codigo_tpu = ultimo_mov.get("codigo")
    data_mov = ultimo_mov.get("dataHora", "")[:10]  # Formato YYYY-MM-DD

    # Exceção de desarquivamento
    if "desarquivamento" in nome_mov:
        return "ATIVO", data_mov

    # Verifica se a movimentação é de arquivamento via SGT / TPU
    eh_arquivado = await verificar_tpu_no_sgt(session, codigo_tpu, nome_mov)

    if eh_arquivado:
        return "ARQUIVADO", data_mov

    return "ATIVO", data_mov


# ==============================================================================
# PIPELINE PRINCIPAL DE PROCESSAMENTO (COM RETRY E TIMEOUT AUMENTADO)
# ==============================================================================
async def consultar_processo(session: aiohttp.ClientSession, numero_cnj: str, semaphore: asyncio.Semaphore) -> dict:
    sigla_tribunal = extrair_sigla_tribunal(numero_cnj)

    if not sigla_tribunal:
        return {"STATUS": "ERRO: CNJ INVÁLIDO", "DATA DO ARQUIVAMENTO": ""}

    url = f"https://api-publica.datajud.cnj.jus.br/api_publica_{sigla_tribunal}/_search"
    limpo = re.sub(r"\D", "", str(numero_cnj))

    payload = {"query": {"match": {"numeroProcesso": limpo}}}
    headers = {"Authorization": f"APIKey {API_KEY}", "Content-Type": "application/json"}

    async with semaphore:
        # Loop de retentativas automáticas (Retry pattern)
        for tentativa in range(1 + MAX_RETRIES):
            try:
                async with session.post(url, json=payload, headers=headers, timeout=HTTP_TIMEOUT) as response:
                    if response.status == 200:
                        dados = await response.json()
                        hits = dados.get("hits", {}).get("hits", [])

                        if not hits:
                            return {"STATUS": "NÃO ENCONTRADO / SIGILO", "DATA DO ARQUIVAMENTO": ""}

                        processo = hits[0].get("_source", {})
                        movimentos = processo.get("movimentos", [])
                        
                        status, data_arq = await classificar_status(session, movimentos)

                        return {
                            "STATUS": status,
                            "DATA DO ARQUIVAMENTO": data_arq if status == "ARQUIVADO" else ""
                        }

                    elif response.status in (401, 403):
                        return {"STATUS": "ERRO 401/403: CHAVE INVÁLIDA", "DATA DO ARQUIVAMENTO": ""}
                    else:
                        if tentativa < MAX_RETRIES:
                            await asyncio.sleep(1)
                            continue
                        return {"STATUS": f"ERRO HTTP {response.status}", "DATA DO ARQUIVAMENTO": ""}

            except Exception as e:
                # Se der erro de rede ou TimeoutError, aguarda um pouco e tenta novamente
                if tentativa < MAX_RETRIES:
                    await asyncio.sleep(1.5 * (tentativa + 1))  # Backoff progressivo (1.5s, 3s...)
                    continue
                return {"STATUS": f"ERRO CONEXÃO: {type(e).__name__}", "DATA DO ARQUIVAMENTO": ""}


async def main():
    print("📥 Lendo planilha de entrada...")
    try:
        df = pd.read_excel(ARQUIVO_ENTRADA)
    except FileNotFoundError:
        print(f"❌ Erro: Arquivo '{ARQUIVO_ENTRADA}' não encontrado.")
        return

    coluna_processo = next((col for col in df.columns if "PROCESSO" in col.upper()), None)
    if not coluna_processo:
        print("❌ Erro: Coluna 'PROCESSO' não encontrada na planilha.")
        return

    total = len(df)
    print(f"🚀 Processando {total} processos em paralelo (Timeout: {HTTP_TIMEOUT}s, Max Retries: {MAX_RETRIES})...")

    semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)

    async with aiohttp.ClientSession() as session:
        tarefas = [
            consultar_processo(session, linha[coluna_processo], semaphore)
            for _, linha in df.iterrows()
        ]

        resultados = await asyncio.gather(*tarefas)

    df["STATUS"] = [r["STATUS"] for r in resultados]
    df["DATA DO ARQUIVAMENTO"] = [r["DATA DO ARQUIVAMENTO"] for r in resultados]

    df.to_excel(ARQUIVO_SAIDA, index=False)
    print("--------------------------------------------------")
    print(f"✅ Concluído! Códigos TPU aprendidos nesta execução: {len(TPU_CACHE)}")
    print(f"📄 Resultado salvo em: {ARQUIVO_SAIDA}")


if __name__ == "__main__":
    asyncio.run(main())
