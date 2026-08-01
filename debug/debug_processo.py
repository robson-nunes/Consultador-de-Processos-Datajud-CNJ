import asyncio
import json
import re
import aiohttp

API_KEY = "cDZHYzlZa0JadVREZDJCendQbXY6SkJlTzNjLV9TRENyQk1RdnFKZGRQdw=="

# 🎯 COLOQUE AQUI O NÚMERO DO PROCESSO QUE DEU DIVERGÊNCIA
PROCESSO_ALVO = "3033691-38.2026.8.19.0001"  # Altere para o seu processo

def extrair_sigla(numero: str) -> str:
    limpo = re.sub(r"\D", "", str(numero))
    if len(limpo) == 20 and limpo[13] == "8":
        mapa = {
            "01": "tjac", "02": "tjal", "03": "tjam", "04": "tjap", "05": "tjba",
            "06": "tjce", "07": "tjdft", "08": "tjes", "09": "tjgo", "10": "tjma",
            "11": "tjmt", "12": "tjms", "13": "tjmg", "14": "tjpa", "15": "tjpb",
            "16": "tjpr", "17": "tjpe", "18": "tjpi", "19": "tjrj", "20": "tjrn",
            "21": "tjrs", "22": "tjro", "23": "tjrr", "24": "tjsc", "25": "tjse",
            "26": "tjsp", "27": "tjto"
        }
        return mapa.get(limpo[14:16])
    return None

async def inspecionar():
    sigla = extrair_sigla(PROCESSO_ALVO)
    if not sigla:
        print("❌ Número de processo ou tribunal não identificado.")
        return

    url = f"https://api-publica.datajud.cnj.jus.br/api_publica_{sigla}/_search"
    limpo = re.sub(r"\D", "", PROCESSO_ALVO)

    payload = {"query": {"match": {"numeroProcesso": limpo}}}
    headers = {"Authorization": f"APIKey {API_KEY}", "Content-Type": "application/json"}

    print(f"🔍 Consultando endpoint '{sigla}' para o processo {PROCESSO_ALVO}...")

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers=headers) as resp:
            data = await resp.json()

            # 1. SALVA O PAYLOAD COMPLETO EM UM ARQUIVO JSON
            arquivo_saida = f"payload_{limpo}.json"
            with open(arquivo_saida, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            print(f"💾 Payload completo salvo com sucesso em: {arquivo_saida}\n")

            # 2. ANALISA E EXIBE AS MOVIMENTAÇÕES NO CONSOLE
            hits = data.get("hits", {}).get("hits", [])
            if not hits:
                print("⚠️ Nenhum registro encontrado na API do Datajud para este processo.")
                return

            source = hits[0].get("_source", {})
            movimentos = source.get("movimentos", [])

            print(f"📊 Total de movimentações registradas no Datajud: {len(movimentos)}")
            print("------------------------------------------------------------------")

            # Ordena do mais recente para o mais antigo
            movs_ordenados = sorted(movimentos, key=lambda x: x.get("dataHora", ""), reverse=True)

            print("📋 ÚLTIMAS 10 MOVIMENTAÇÕES REGISTRADAS:")
            for idx, m in enumerate(movs_ordenados[:10], start=1):
                data_h = m.get("dataHora", "S/D")[:10]
                nome = m.get("nome") or m.get("nomeMovimento") or "Sem Descrição"
                codigo = m.get("codigo", "S/C")
                print(f"{idx:02d}. [{data_h}] Código TPU: {codigo:<5} | Texto: {nome}")

if __name__ == "__main__":
    asyncio.run(inspecionar())
