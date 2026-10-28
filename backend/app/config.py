import json
from pathlib import Path

# No repositório, `config/` fica na raiz; no pacote da Lambda, ao lado de `app/`.
RAIZ = next(p for p in Path(__file__).resolve().parents if (p / "config").is_dir())


def valores_iniciais() -> dict:
    """Valores iniciais da spec; o arquivo é compartilhado com o app."""
    return json.loads((RAIZ / "config" / "valores-iniciais.json").read_text())
