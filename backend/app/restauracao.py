"""Restauração pela linha de comando, rodada pelo dono com a credencial dele (ADR 0012).

    uv run python -m app.restauracao <arquivo.zip> [--esvaziar]

Use pelo `scripts/restaurar-backup.sh`, que acha o banco do ambiente. Depois de gravar, exporta
de novo e exige o mesmo zip: a ida e volta do CI, agora no banco de verdade.
"""

import argparse
import io
import json
import os
import sys
import zipfile
from pathlib import Path

from app.backup import (
    VERSAO_FORMATO,
    RestauracaoDesfeita,
    RestauracaoRecusada,
    esvaziar_banco,
    gerar_backup,
    restaurar_backup,
)
from app.banco import conectar


def main(argumentos: list[str] | None = None) -> int:
    leitor = argparse.ArgumentParser(prog="python -m app.restauracao")
    leitor.add_argument("arquivo", type=Path, help="o zip do backup")
    leitor.add_argument(
        "--esvaziar",
        action="store_true",
        help="apaga os dados do banco antes de restaurar; só com AMBIENTE=dev",
    )
    opcoes = leitor.parse_args(argumentos)
    # Esvaziar é o ensaio no dev com o backup de prod; em prod, só se restaura num banco vazio.
    if opcoes.esvaziar and os.environ.get("AMBIENTE") != "dev":
        leitor.error("--esvaziar só roda com AMBIENTE=dev")
    backup = opcoes.arquivo.read_bytes()

    with conectar(autocommit=True, admin=True) as conn:
        if opcoes.esvaziar:
            esvaziar_banco(conn)
            print("banco esvaziado")
        try:
            manifesto = restaurar_backup(conn, backup)
        except RestauracaoRecusada as erro:
            print(f"recusada, nada foi gravado: {erro}", file=sys.stderr)
            return 1
        except RestauracaoDesfeita as erro:
            print(f"falhou e foi desfeita, o banco está vazio: {erro}", file=sys.stderr)
            return 1
        for tabela, conferido in sorted(manifesto["tabelas"].items()):
            print(f"{tabela}: {conferido['linhas']} linhas")
        print("restaurado e conferido contra o manifesto")
        with conn.transaction():
            de_novo = gerar_backup(conn)
    if de_novo == backup:
        print("exportado de novo: mesmo zip")
        return 0
    with zipfile.ZipFile(io.BytesIO(backup)) as compactado:
        versao = json.loads(compactado.read("manifesto.json"))["versao_formato"]
    # Um backup convertido de versão antiga não volta igual: o zip novo já sai na atual.
    if versao != VERSAO_FORMATO:
        print(f"convertido da versão {versao} para a {VERSAO_FORMATO}")
        return 0
    print("o backup exportado de novo não é o mesmo zip", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
