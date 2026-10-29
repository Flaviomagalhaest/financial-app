"""Importação do Mobills pela linha de comando, rodada pelo dono sobre os exports (ADR 0007).

    uv run python -m app.mobills <pasta do geral> <pasta das faturas> <planilha de revisão>

A pasta do geral tem os XLSX de "todas as transações"; a das faturas, uma subpasta por cartão com
os arquivos `<cartão>_-_<AAAAMM>.xlsx`. A planilha de revisão é lida, se existir, e reescrita com
as decisões mantidas. Guarde tudo fora do repositório (`data/` está no `.gitignore`).
"""

import argparse
import sys
from pathlib import Path

from app.mobills import importar
from app.mobills.leitura import ArquivoInvalido


def main(argumentos: list[str] | None = None) -> int:
    leitor = argparse.ArgumentParser(prog="python -m app.mobills")
    leitor.add_argument("geral", type=Path, help="pasta com os XLSX do export geral")
    leitor.add_argument("faturas", type=Path, help="pasta com uma subpasta por cartão")
    leitor.add_argument("revisao", type=Path, help="planilha de revisão (.xlsx)")
    opcoes = leitor.parse_args(argumentos)
    for pasta in (opcoes.geral, opcoes.faturas):
        if not pasta.is_dir():
            leitor.error(f"{pasta} não é uma pasta")

    try:
        importacao = importar(opcoes.geral, opcoes.faturas, opcoes.revisao)
    except ArquivoInvalido as erro:
        print(f"arquivo inválido: {erro}", file=sys.stderr)
        return 1

    cruzamento = importacao.cruzamento
    abertos = sum(1 for p in cruzamento.provaveis if p.decisao is None)
    casadas = len(cruzamento.pares)
    # Os juntados estão nos pares e os separados nas sobras; os abertos, só nos prováveis.
    da_fatura = casadas + len(cruzamento.fatura_sem_par) + abertos
    no_cartao = sum(1 for x in importacao.lancamentos if x.cartao)
    print(f"{len(importacao.lancamentos)} lançamentos, {no_cartao} no cartão")
    if da_fatura:
        print(f"{casadas} de {da_fatura} linhas de fatura casadas ({casadas / da_fatura:.1%})")
    provaveis = len(cruzamento.provaveis)
    print(
        f"{provaveis} {'par provável' if provaveis == 1 else 'pares prováveis'} ({abertos} abertos),"
        f" grupos ambíguos: {len(cruzamento.ambiguos)},"
        f" parcelas quebradas: {sum(1 for p in importacao.parcelamentos if p.quebra)},"
        f" ajustes de fatura: {len(importacao.ajustes)}"
    )
    print(f"planilha de revisão em {opcoes.revisao}")
    for impedimento in importacao.impedimentos:
        print(f"impede gravar: {impedimento}", file=sys.stderr)
    # A planilha foi escrita; o código 2 diz que ela ainda precisa de edição.
    return 2 if importacao.impedimentos else 0


if __name__ == "__main__":
    sys.exit(main())
