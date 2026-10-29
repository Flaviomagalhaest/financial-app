"""O reagrupamento das parcelas `(n/total)` do geral em parcelamentos (`## Answer` do ticket 18): a
mesma descrição base, o mesmo valor (tolerância de 1 centavo), o mesmo total e números `n` em
meses consecutivos. As parcelas que faltam e as futuras são do ticket 68."""

from collections import defaultdict
from dataclasses import dataclass

TOLERANCIA_EM_CENTAVOS = 1


@dataclass
class Parcelamento:
    descricao: str
    total: int
    lancamentos: list  # as parcelas encontradas, em ordem
    quebra: str | None  # por que a sequência está quebrada, se estiver

    @property
    def primeira(self):
        return self.lancamentos[0]

    @property
    def ultima(self):
        return self.lancamentos[-1]

    @property
    def cartao(self) -> str | None:
        return next((x.cartao for x in self.lancamentos if x.cartao), None)

    def faixa(self) -> str:
        """`1 a 3 de 10`, ou `3 de 3` quando é uma só."""
        primeira, ultima = self.primeira.parcela[0], self.ultima.parcela[0]
        inicio = f"{primeira}" if primeira == ultima else f"{primeira} a {ultima}"
        return f"{inicio} de {self.total}"


def mes_seguinte(mes: str) -> str:
    ano, numero = int(mes[:4]), int(mes[5:])
    return f"{ano + numero // 12}-{numero % 12 + 1:02d}"


def reagrupar(lancamentos, primeiro_mes: str, ultimo_mes: str) -> list[Parcelamento]:
    """Uma sequência que começa depois do primeiro mês do export sem a parcela 1, ou acaba antes
    do último sem a última parcela, está quebrada."""
    grupos = defaultdict(list)
    for lancamento in lancamentos:
        if lancamento.parcela:
            chave = (lancamento.tipo, lancamento.descricao.casefold(), lancamento.parcela[1])
            grupos[chave].append(lancamento)
    parcelamentos = []
    for (_, _, total), parcelas in grupos.items():
        cadeias: list[list] = []
        for parcela in sorted(parcelas, key=lambda x: (x.mes, x.parcela[0])):
            continua = [
                c
                for c in cadeias
                if c[-1].parcela[0] == parcela.parcela[0] - 1
                and mes_seguinte(c[-1].mes) == parcela.mes
                and abs(c[-1].valor_centavos - parcela.valor_centavos) <= TOLERANCIA_EM_CENTAVOS
            ]
            # Entre parcelamentos iguais em paralelo, fica junto o do mesmo cartão.
            continua.sort(key=lambda c: c[-1].cartao != parcela.cartao)
            if continua:
                continua[0].append(parcela)
            else:
                cadeias.append([parcela])
        for cadeia in cadeias:
            parcelamentos.append(
                Parcelamento(
                    descricao=cadeia[0].descricao,
                    total=total,
                    lancamentos=cadeia,
                    quebra=_quebra(cadeia, total, primeiro_mes, ultimo_mes),
                )
            )
    parcelamentos.sort(key=lambda p: (p.descricao.casefold(), p.primeira.mes))
    return parcelamentos


def _quebra(cadeia: list, total: int, primeiro_mes: str, ultimo_mes: str) -> str | None:
    primeira, ultima = cadeia[0], cadeia[-1]
    if primeira.parcela[0] > 1 and primeira.mes > primeiro_mes:
        return f"falta a parcela {primeira.parcela[0] - 1} antes de {primeira.mes}"
    if ultima.parcela[0] < total and ultima.mes < ultimo_mes:
        return f"falta a parcela {ultima.parcela[0] + 1} depois de {ultima.mes}"
    return None
