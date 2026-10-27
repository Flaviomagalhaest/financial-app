"""Escreve o OpenAPI da API em openapi.json na raiz do repositório."""

import json
from pathlib import Path

from app.main import create_app

DESTINO = Path(__file__).resolve().parents[1] / "openapi.json"

if __name__ == "__main__":
    DESTINO.write_text(json.dumps(create_app().openapi(), indent=2, ensure_ascii=False) + "\n")
