import json
import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]


def database_url() -> str:
    return os.environ["DATABASE_URL"]


def valores_iniciais() -> dict:
    """Valores iniciais da spec; o arquivo é compartilhado com o app."""
    return json.loads((RAIZ / "config" / "valores-iniciais.json").read_text())
