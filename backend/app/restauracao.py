"""Restauração pela linha de comando, rodada pelo dono com a credencial dele (ADR 0012).

    uv run python -m app.restauracao <arquivo.zip> [--esvaziar | --refazer-importacao]

Use pelo `scripts/restaurar-backup.sh`, que acha o banco do ambiente. Depois de gravar, exporta
de novo e exige o mesmo zip: a ida e volta do CI, agora no banco de verdade.

`--refazer-importacao` troca a importação do Mobills gravada pela do zip, em qualquer ambiente,
até a virada (ticket 91): recusa, sem apagar nada, se o banco ou o zip tiver uso pelo app.
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
    refazer_importacao,
    restaurar_backup,
)
from app.banco import conectar


def main(argumentos: list[str] | None = None) -> int:
    leitor = argparse.ArgumentParser(prog="python -m app.restauracao")
    leitor.add_argument("arquivo", type=Path, help="o zip do backup")
    modo = leitor.add_mutually_exclusive_group()
    modo.add_argument(
        "--esvaziar",
        action="store_true",
        help="apaga os dados do banco antes de restaurar; só com AMBIENTE=dev",
    )
    modo.add_argument(
        "--refazer-importacao",
        action="store_true",
        help="troca a importação do Mobills pela do zip; recusa se o banco tiver uso pelo app",
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
        perdidos: list[str] = []
        try:
            if opcoes.refazer_importacao:
                manifesto, perdidos = refazer_importacao(conn, backup)
            else:
                manifesto = restaurar_backup(conn, backup)
        except RestauracaoRecusada as erro:
            nada = (
                "nada foi apagado nem gravado" if opcoes.refazer_importacao else "nada foi gravado"
            )
            print(f"recusada, {nada}: {erro}", file=sys.stderr)
            return 1
        except RestauracaoDesfeita as erro:
            print(f"falhou e foi desfeita, o banco está vazio: {erro}", file=sys.stderr)
            return 1
        for tabela, conferido in sorted(manifesto["tabelas"].items()):
            print(f"{tabela}: {conferido['linhas']} linhas")
        print("restaurado e conferido contra o manifesto")
        if opcoes.refazer_importacao:
            print("importação refeita: banco esvaziado e restaurado")
        for perdido in perdidos:
            print(f"informe de novo: {perdido}")
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
