"""As contas que o dono confere contra o Mobills (`## Answer` do ticket 18): o resultado de cada mês,
no mês da fatura, e o total de cada fatura."""

from dataclasses import dataclass, field

from app.mobills.parcelas import mes_seguinte


@dataclass(frozen=True)
class AjusteDeFatura:
    """O `Reajuste de fatura` do Mobills (ADR 0008): não é lançamento, conta no total da fatura e
    nas despesas do mês. Positivo aumenta a fatura. Sem cartão quando só o geral o trouxe."""

    cartao: str | None
    mes: str
    valor_centavos: int


@dataclass
class Mes:
    mes: str
    receitas: int = 0
    despesas: int = 0
    ajustes: int = 0
    # O que o importador acrescentou e o Mobills não conta no mês: (quantas, efeito no resultado).
    sem_par: list[int] = field(default_factory=list)
    provaveis_abertos: list[int] = field(default_factory=list)

    @property
    def resultado(self) -> int:
        return self.receitas - self.despesas - self.ajustes


@dataclass
class Fatura:
    cartao: str
    mes: str
    compras: int = 0
    ajuste: int = 0

    @property
    def total(self) -> int:
        return self.compras + self.ajuste


def meses(lancamentos, ajustes, cruzamento, primeiro: str, ultimo: str) -> list[Mes]:
    """Uma linha por mês, do primeiro ao último do export, inclusive os vazios."""
    por_mes: dict[str, Mes] = {}
    mes = primeiro
    while primeiro and mes <= ultimo:
        por_mes[mes] = Mes(mes)
        mes = mes_seguinte(mes)
    for lancamento in lancamentos:
        linha = por_mes.setdefault(lancamento.mes, Mes(lancamento.mes))
        if lancamento.tipo == "receita":
            linha.receitas += lancamento.valor_centavos
        else:
            linha.despesas += lancamento.valor_centavos
    for ajuste in ajustes:
        por_mes.setdefault(ajuste.mes, Mes(ajuste.mes)).ajustes += ajuste.valor_centavos
    for fatura in cruzamento.fatura_sem_par:
        if not e_ajuste(fatura.categoria):
            por_mes[fatura.mes].sem_par.append(-fatura.valor_centavos)
    for provavel in cruzamento.provaveis:
        if provavel.decisao is None:
            por_mes[provavel.fatura.mes].provaveis_abertos.append(-provavel.fatura.valor_centavos)
    return [por_mes[m] for m in sorted(por_mes)]


def faturas(lancamentos, ajustes, meses_das_pastas: dict[str, list[str]]) -> list[Fatura]:
    """Cada fatura exportada, mesmo vazia, e as que um parcelamento sem cartão criou."""
    por_fatura: dict[tuple[str, str], Fatura] = {}
    for cartao, lista in meses_das_pastas.items():
        for mes in lista:
            por_fatura[(cartao, mes)] = Fatura(cartao, mes)
    for lancamento in lancamentos:
        if lancamento.cartao:
            chave = (lancamento.cartao, lancamento.mes)
            fatura = por_fatura.setdefault(chave, Fatura(*chave))
            sinal = 1 if lancamento.tipo == "despesa" else -1
            fatura.compras += sinal * lancamento.valor_centavos
    for ajuste in ajustes:
        if ajuste.cartao:
            chave = (ajuste.cartao, ajuste.mes)
            por_fatura.setdefault(chave, Fatura(*chave)).ajuste += ajuste.valor_centavos
    return [por_fatura[c] for c in sorted(por_fatura)]


def e_ajuste(categoria: str) -> bool:
    return categoria.casefold() == "reajuste de fatura"


def separar_ajustes(lancamentos) -> tuple[list, list[AjusteDeFatura]]:
    """Os lançamentos sem os `Reajuste de fatura`, que viram ajustes da fatura em que aparecem."""
    restantes, ajustes = [], []
    for lancamento in lancamentos:
        if e_ajuste(lancamento.categorias[0]):
            sinal = 1 if lancamento.tipo == "despesa" else -1
            ajustes.append(
                AjusteDeFatura(lancamento.cartao, lancamento.mes, sinal * lancamento.valor_centavos)
            )
        else:
            restantes.append(lancamento)
    return restantes, ajustes
