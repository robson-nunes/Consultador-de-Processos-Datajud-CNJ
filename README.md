# 📄 Consultador de Processos (Datajud + CNJ)

> **Resumo Executivo:** Ferramenta automatizada em Python para leitura de planilhas Excel, consulta em lote à base nacional de dados do Poder Judiciário (Datajud) e classificação precisa do status de arquivamento de processos judiciais.

---

## 💡 Visão de Arquitetura

Para garantir que o sistema não falhe e apresente dados 100% confiáveis para o time jurídico e operacional, a solução combina **duas abordagens tecnológicas complementares**:

```
[ Planilha Excel ] ➡️ [ Motor em Python (Async) ] ➡️ [ 1. API Datajud (Metadados) ] ➡️ [ 2. WebService SGT/TPU (Tradução) ]
```

### 1. A API Pública do Datajud (Consulta em Lote)
O Datajud é o repositório centralizador de dados do Conselho Nacional de Justiça (CNJ). A nossa ferramenta lê cada linha da planilha, identifica a qual estado/tribunal o processo pertence (TJMG, TJRJ, TJSP, TRT, etc.) e faz a consulta de forma **assíncrona e em paralelo**.
* **Benefício de Negócio:** Processamento ultrarrápido (centenas de processos em segundos) sem travar a máquina do usuário.

### 2. A Consulta Dinâmica ao SGT/TPU do CNJ (Inteligência de Classificação)
Os tribunais brasileiros usam termos diferentes para registrar a baixa de um processo (ex: o TJMG pode registrar `"Definitivo"`, o TJSP pode registrar `"Arquivamento Definitivo"` e o TJRJ `"Baixa"`). 
Para evitar que processos baixados passem despercebidos, o sistema consulta a **Tabela Processual Unificada (TPU)** do CNJ em tempo real através do WebService do SGT.
* **Benefício de Negócio:** Tolerância zero a variações de texto dos tribunais. Se o código numérico do CNJ indicar arquivamento ou baixa, o sistema aprende e classifica como **`ARQUIVADO`** com precisão absoluta.

---

## 🛠️ Guia Prático de Execução

### 📋 Pré-requisitos

> *Nota: Este passo só precisa ser feito **uma única vez** no computador onde o script vai rodar.*

1. Certifique-se de que o **Python 3** está instalado na sua máquina.
2. Abra o Terminal (macOS/Linux) ou Prompt de Comando (Windows) e execute o comando abaixo para instalar as bibliotecas necessárias:

```bash
python3 -m pip install pandas openpyxl aiohttp
```

---

### 🚀 Como Rodar no Dia a Dia

#### Opção A: Execução Super Simples (Duplo Clique) ⭐ *Recomendado*

1. Deixe o arquivo da sua planilha Excel na mesma pasta do projeto com o nome **`Busca_Arquivados.xlsx`**.
2. **No Windows:** Dê dois cliques no arquivo **`executar.bat`**.
3. **No macOS:** Dê dois cliques no arquivo **`executar.command`**.
4. Uma janela abrirá mostrando o progresso e fechará ao concluir.

---

#### Opção B: Execução via Terminal

1. Coloque a planilha Excel com o nome **`Busca_Arquivados.xlsx`** na mesma pasta do script.
2. Abra o terminal e navegue até a pasta do projeto:
   ```bash
   cd /caminho/para/a/pasta
   ```
3. Execute o comando:
   ```bash
   python3 consulta_datajud_v2.py
   ```

---

### 📄 Coletando o Resultado

Após a execução, o sistema gerará automaticamente um novo arquivo chamado:
📄 **`Busca_Arquivados_RESULTADO.xlsx`**

---

## 📊 Entendendo as Colunas da Planilha de Resultado

A planilha gerada preservará todas as colunas originais do seu arquivo e preencherá duas novas colunas estratégicas:

| Coluna Gerada | Valores Possíveis | O que significa? |
| :--- | :--- | :--- |
| **`STATUS`** | **`ARQUIVADO`** | O processo foi baixado/arquivado definitivamente. |
| | **`ATIVO`** | O processo continua em andamento regular no tribunal. |
| | **`NÃO ENCONTRADO / SIGILO`** | O processo tramita em Segredo de Justiça ou não foi localizado. |
| | **`ERRO CONEXÃO`** | Houve falha temporária de internet ou instabilidade no portal do tribunal. |
| **`DATA DO ARQUIVAMENTO`** | *Ex: `2026-06-19`* | Exibe a data exata em que ocorreu a movimentação de arquivamento (preenchido apenas quando o status for `ARQUIVADO`). |

---

## ❓ Solução de Problemas Frequentes (Troubleshooting)

* **Erro `Arquivo 'Busca_Arquivados.xlsx' não encontrado`:**
  * *Causa:* A planilha não está na mesma pasta do script ou o nome do arquivo está diferente.
  * *Solução:* Renomeie o arquivo para `Busca_Arquivados.xlsx` (ou altere o nome do arquivo na constante `ARQUIVO_ENTRADA` dentro do arquivo `consulta_datajud_v2.py`).
* **Mensagem `Permission Denied` ao dar duplo clique no macOS:**
  * *Causa:* O macOS bloqueia scripts executáveis criados recentemente por segurança.
  * *Solução:* Abra o terminal na pasta e rode o comando: `chmod +x executar.command`.
