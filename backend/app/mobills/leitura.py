"""Leitura dos exports do Mobills (tickets 01 e 07): o geral, com a aba `Receitas e Despesas`, e as
faturas por cartão e mês, uma pasta por cartão com arquivos `<cartão>_-_<AAAAMM>.xlsx`."""

import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from openpyxl import load_workbook

ABA_DO_GERAL = "Receitas e Despesas"
ROTULO_DA_FATURA = re.compile(r"(\d{4})(\d{2})\.xlsx$", re.IGNORECASE)
PARCELA = re.compile(r"\s*\((\d+)/(\d+)\)\s*$")


class ExportInvalido(Exception):
    """Um arquivo do export que o importador não sabe ler."""


@dataclass(frozen=True)
class LinhaDoGeral:
    posicao: int  # a ordem no export inteiro
    arquivo: str
    linha: int  # a linha na aba, para o dono achar
    data: date
    descricao: str
    valor_centavos: int  # com o sinal do Mobills: despesa negativa
    conta: str
    situacao: str
    categoria: str
    tags: tuple[str, ...]
    parcela: tuple[int, int] | None

    @property
    def mes(self) -> str:
        return f"{self.data:%Y-%m}"


@dataclass(frozen=True)
class LinhaDeFatura:
    pasta: str
    mes: str  # o rótulo AAAAMM do arquivo, que é o mês da fatura
    arquivo: str
    data: date  # a data da compra
    descricao: str
    categoria: str
    valor_centavos: int  # como na fatura: compra positiva, crédito negativo


def ler_geral(pasta: Path) -> list[LinhaDoGeral]:
    """As linhas de lançamento de todos os XLSX da pasta, na ordem dos arquivos e das linhas. A
    linha em branco e a de total de cada aba não têm data e ficam de fora."""
    linhas: list[LinhaDoGeral] = []
    for arquivo in sorted(pasta.glob("*.xlsx")):
        livro = load_workbook(arquivo, read_only=True, data_only=True)
        if ABA_DO_GERAL not in livro.sheetnames:
            raise ExportInvalido(f"{arquivo.name}: falta a aba '{ABA_DO_GERAL}'")
        for numero, valores in _linhas_com_cabecalho(livro[ABA_DO_GERAL], arquivo):
            data = _data(valores.get("Data"))
            if data is None:
                continue
            descricao, parcela = _sem_parcela(_texto(valores.get("Descrição")))
            linhas.append(
                LinhaDoGeral(
                    posicao=len(linhas),
                    arquivo=arquivo.name,
                    linha=numero,
                    data=data,
                    descricao=descricao,
                    valor_centavos=_centavos(valores.get("Valor"), arquivo),
                    conta=_texto(valores.get("Conta")),
                    situacao=_texto(valores.get("Situação")),
                    categoria=_texto(valores.get("Categoria")),
                    tags=_tags(valores.get("Tags")),
                    parcela=parcela,
                )
            )
        livro.close()
    return linhas


def ler_faturas(pasta: Path) -> list[LinhaDeFatura]:
    """As compras de todas as faturas, uma subpasta por cartão."""
    linhas: list[LinhaDeFatura] = []
    for subpasta in sorted(p for p in pasta.iterdir() if p.is_dir()):
        for arquivo in sorted(subpasta.glob("*.xlsx")):
            rotulo = ROTULO_DA_FATURA.search(arquivo.name)
            if rotulo is None:
                raise ExportInvalido(f"{arquivo.name}: falta o rótulo AAAAMM no fim do nome")
            mes = f"{rotulo[1]}-{rotulo[2]}"
            livro = load_workbook(arquivo, read_only=True, data_only=True)
            for _, valores in _linhas_com_cabecalho(livro.worksheets[0], arquivo):
                data = _data(valores.get("Data"))
                if data is None:
                    continue
                linhas.append(
                    LinhaDeFatura(
                        pasta=subpasta.name,
                        mes=mes,
                        arquivo=arquivo.name,
                        data=data,
                        descricao=_sem_parcela(_texto(valores.get("Descrição")))[0],
                        categoria=_texto(valores.get("Categoria")),
                        valor_centavos=_centavos(valores.get("Valor"), arquivo),
                    )
                )
            livro.close()
    return linhas


def pastas_de_fatura(pasta: Path) -> dict[str, list[str]]:
    """Cada pasta de cartão com os meses das faturas dela, inclusive as vazias."""
    pastas: dict[str, list[str]] = {}
    for subpasta in sorted(p for p in pasta.iterdir() if p.is_dir()):
        meses = []
        for arquivo in sorted(subpasta.glob("*.xlsx")):
            rotulo = ROTULO_DA_FATURA.search(arquivo.name)
            if rotulo:
                meses.append(f"{rotulo[1]}-{rotulo[2]}")
        pastas[subpasta.name] = sorted(meses)
    return pastas


def _linhas_com_cabecalho(aba, arquivo: Path):
    linhas = aba.iter_rows(values_only=True)
    cabecalho = [_texto(c) for c in next(linhas, ())]
    if "Data" not in cabecalho or "Valor" not in cabecalho:
        raise ExportInvalido(f"{arquivo.name}: cabeçalho sem 'Data' e 'Valor'")
    for numero, valores in enumerate(linhas, start=2):
        yield numero, dict(zip(cabecalho, valores))


def _texto(valor) -> str:
    return "" if valor is None else " ".join(str(valor).split())


def _data(valor) -> date | None:
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    try:
        return datetime.strptime(_texto(valor), "%d/%m/%Y").date()
    except ValueError:
        return None


def _centavos(valor, arquivo: Path) -> int:
    """O valor em centavos: número do geral (`-120.35`) ou texto da fatura (`R$ 1.234,56`)."""
    if isinstance(valor, int | float):
        return int((Decimal(str(valor)) * 100).quantize(Decimal(1)))
    texto = _texto(valor).replace("R$", "").replace(" ", "")
    negativo = texto.startswith("-")
    texto = texto.lstrip("-").replace(".", "").replace(",", ".")
    try:
        centavos = int((Decimal(texto) * 100).quantize(Decimal(1)))
    except ArithmeticError:
        raise ExportInvalido(f"{arquivo.name}: valor que não é número: {valor!r}") from None
    return -centavos if negativo else centavos


def _sem_parcela(descricao: str) -> tuple[str, tuple[int, int] | None]:
    """A descrição sem o sufixo `(n/total)` e a parcela que ele dizia."""
    achado = PARCELA.search(descricao)
    if achado is None:
        return descricao, None
    return descricao[: achado.start()], (int(achado[1]), int(achado[2]))


def _tags(valor) -> tuple[str, ...]:
    # O separador de várias tags não apareceu nos exports (ticket 01); a vírgula é a aposta.
    return tuple(t.strip() for t in _texto(valor).split(",") if t.strip())
