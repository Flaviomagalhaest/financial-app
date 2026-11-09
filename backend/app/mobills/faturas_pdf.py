"""O total de cada fatura lido do texto do PDF do banco (ticket 220).

O dono extrai o texto dos PDFs com `pdftotext -raw -enc UTF-8` fora do repositório, numa subpasta
por cartão com o nome do cartão no Mobills. O importador não abre PDF nem usa senha. No `-layout`
o valor de outra coluna pode cair na linha do total.

A fatura que o PDF diz vencer num mês é a que o Mobills rotula com o mês anterior: nos quatro
cartões com PDF, 56 das 62 faturas reais exportadas fecham ao centavo assim e no máximo 3 por
cartão pelo mês do vencimento.
"""

import re
from pathlib import Path

from app.mobills.parcelas import mes_anterior

_VENCIMENTO = re.compile(r"Vencimento:\s*\d\d/(\d\d)/(\d{4})")
_TOTAL = re.compile(r"Total desta fatura\s+(-?[\d.]+,\d\d)")


def ler_totais(pasta: Path) -> tuple[dict[tuple[str, str], int], list[str]]:
    """O total em centavos por (subpasta do cartão, rótulo AAAA-MM) e os avisos do que não deu
    para ler."""
    totais: dict[tuple[str, str], int] = {}
    origem: dict[tuple[str, str], str] = {}
    avisos = []
    for arquivo in sorted(pasta.glob("*/*.txt")):
        nome = f"{arquivo.parent.name}/{arquivo.name}"
        texto = _texto(arquivo.read_bytes())
        vencimento, total = _VENCIMENTO.search(texto), _TOTAL.search(texto)
        if not vencimento or not total:
            avisos.append(f"fatura em texto {nome} sem vencimento ou sem 'Total desta fatura'")
            continue
        chave = (arquivo.parent.name, mes_anterior(f"{vencimento[2]}-{vencimento[1]}"))
        if chave in totais:
            avisos.append(f"fatura em texto {nome} repete o mês {chave[1]} de {origem[chave]}")
            continue
        totais[chave], origem[chave] = _centavos(total[1]), nome
    return totais, avisos


def _texto(conteudo: bytes) -> str:
    """O `pdftotext` grava em UTF-8 ou em Latin-1, conforme a opção `-enc`."""
    try:
        return conteudo.decode("utf-8")
    except UnicodeDecodeError:
        return conteudo.decode("latin-1")


def _centavos(valor: str) -> int:
    return int(valor.replace(".", "").replace(",", ""))
