"""Importador do histórico do Mobills (ADR 0007), rodado localmente pelo dono:

    uv run python -m app.mobills <pasta do geral> <pasta das faturas> <planilha de revisão>

Dados reais nunca entram no repositório nem no CI: os testes usam só exports fictícios.
"""

from app.mobills.backup import gerar_backup_da_importacao
from app.mobills.conferencia import AjusteDeFatura
from app.mobills.importacao import Cartao, Conta, Importacao, Lancamento, importar

__all__ = [
    "AjusteDeFatura",
    "Cartao",
    "Conta",
    "Importacao",
    "Lancamento",
    "gerar_backup_da_importacao",
    "importar",
]
