#!/bin/bash
cd "$(dirname "$0")"
echo "==================================================="
echo "  INICIANDO CONSULTA DE PROCESSOS (DATAJUD + CNJ)"
echo "==================================================="
echo ""
python3 consulta_datajud_v2.py
echo ""
echo "==================================================="
echo "  Processamento concluido com sucesso!"
echo "  Verifique a planilha de resultado gerada."
echo "==================================================="
echo ""
read -p "Pressione ENTER para fechar esta janela..."