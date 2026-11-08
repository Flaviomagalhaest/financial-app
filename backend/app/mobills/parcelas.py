"""O reagrupamento das parcelas `(n/total)` do geral em parcelamentos (`## Answer` do ticket 18): a
mesma descrição base, o mesmo valor (tolerância de 1 centavo sobre a primeira parcela), o mesmo
total e números `n` em meses consecutivos. As parcelas que o export não traz são do ticket 68."""

from collections import defaultdict
from dataclasses import dataclass, replace
from datetime import date

from app.recorrencias import mais_meses

TOLERANCIA_EM_CENTAVOS = 1


@dataclass
class Parcelamento:
    descricao: str
    total: int
    lancamentos: list  # as parcelas encontradas, em ordem
    quebra: str | None  # por que a sequência está quebrada, se estiver
    # O dono mandou tratar a sequência quebrada como um parcelamento só (ticket 216).
    aceito: bool = False

    @property
    def primeira(self):
        return self.lancamentos[0]

    @property
    def ultima(self):
        return self.lancamentos[-1]

    @property
    def do_app(self) -> bool:
        """Vira parcelamento no app: é de despesa, tem 2 parcelas ou mais e a sequência não está
        quebrada, ou o dono a aceitou na revisão. Os outros (a receita parcelada, o `(1/1)` e a
        sequência quebrada sem decisão) entram como lançamentos avulsos, sem gerar o que falta:
        os pedaços de uma sequência quebrada seriam dois parcelamentos da mesma compra."""
        return (
            self.primeira.tipo == "despesa"
            and self.total >= 2
            and (self.quebra is None or self.aceito)
        )

    @property
    def anteriores(self) -> int:
        """Quantas parcelas vieram antes do histórico, que não entram."""
        return self.primeira.parcela[0] - 1

    def data_da_1a(self) -> date:
        """Fora do cartão, a data da 1ª parcela, mesmo a de antes do histórico."""
        return mais_meses(self.primeira.data, -self.anteriores)

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


def mes_anterior(mes: str) -> str:
    ano, numero = int(mes[:4]), int(mes[5:])
    return f"{ano - (numero == 1)}-{(numero - 2) % 12 + 1:02d}"


def reagrupar(
    lancamentos: list, primeiro_mes: str, ultimo_mes: str
) -> tuple[list[Parcelamento], list]:
    """Uma sequência que começa depois do primeiro mês do export sem a parcela 1, que acaba antes
    do último sem a última parcela, ou que tem a mesma parcela repetida num mês, está quebrada.

    A linha sem `(n/total)` com a mesma descrição, o valor da parcela vizinha (tolerância de 1
    centavo) e o mês exato de uma parcela que falta é essa parcela, com o número deduzido pela
    posição (ticket 219). Devolve também os lançamentos, com ela no lugar da avulsa."""
    grupos = defaultdict(list)
    avulsas = defaultdict(list)
    for lancamento in lancamentos:
        if lancamento.parcela:
            chave = (lancamento.tipo, lancamento.descricao.casefold(), lancamento.parcela[1])
            grupos[chave].append(lancamento)
        else:
            avulsas[(lancamento.tipo, lancamento.descricao.casefold())].append(lancamento)
    trocadas: dict[int, object] = {}
    parcelamentos = []
    for (tipo, descricao, total), parcelas in grupos.items():
        cadeias = _cadeias(parcelas)
        _preencher_buracos(cadeias, total, avulsas[(tipo, descricao)], trocadas)
        no_mes = defaultdict(list)
        for x in (x for c in cadeias for x in c):
            no_mes[(x.mes, x.parcela[0])].append(x)
        for cadeia in cadeias:
            motivos = _faltas(cadeia, total, primeiro_mes, ultimo_mes)
            repetida = next((x for x in cadeia if _tem_par_no_mes(x, no_mes)), None)
            if repetida is not None:
                motivos.append(f"duas parcelas {repetida.parcela[0]} de {total} em {repetida.mes}")
            parcelamentos.append(
                Parcelamento(
                    descricao=cadeia[0].descricao,
                    total=total,
                    lancamentos=cadeia,
                    quebra="; ".join(motivos) or None,
                )
            )
    parcelamentos.sort(key=lambda p: (p.descricao.casefold(), p.primeira.mes))
    return parcelamentos, [trocadas.get(id(x), x) for x in lancamentos]


def _tem_par_no_mes(parcela, no_mes: dict) -> bool:
    """Outra parcela de mesmo número no mês e com o mesmo valor; com outro valor é outra compra
    igual em paralelo (ticket 219)."""
    return any(
        outra is not parcela
        and abs(outra.valor_centavos - parcela.valor_centavos) <= TOLERANCIA_EM_CENTAVOS
        for outra in no_mes[(parcela.mes, parcela.parcela[0])]
    )


def _cadeias(parcelas: list) -> list[list]:
    """As parcelas `(n/total)` de uma descrição em sequências de números e meses seguidos."""
    cadeias: list[list] = []
    for parcela in sorted(parcelas, key=lambda x: (x.mes, x.parcela[0])):
        continua = [
            c
            for c in cadeias
            if c[-1].parcela[0] == parcela.parcela[0] - 1 and mes_seguinte(c[-1].mes) == parcela.mes
        ]
        # O valor não separa a compra (ticket 219): só desempata parcelamentos iguais em
        # paralelo, pelo valor mais perto e depois pelo mesmo cartão.
        continua.sort(
            key=lambda c: (
                abs(c[0].valor_centavos - parcela.valor_centavos),
                c[-1].cartao != parcela.cartao,
            )
        )
        if continua:
            continua[0].append(parcela)
        else:
            cadeias.append([parcela])
    return cadeias


def _preencher_buracos(cadeias: list[list], total: int, avulsas: list, trocadas: dict) -> None:
    """Põe a linha sem sufixo no lugar da parcela que falta antes ou depois de cada sequência e
    junta a sequência com a que continua no mês seguinte."""
    usadas = set()

    def deduzida(vizinha, mes: str, numero: int):
        avulsa = next(
            (
                x
                for x in avulsas
                if id(x) not in usadas
                and x.mes == mes
                and abs(x.valor_centavos - vizinha.valor_centavos) <= TOLERANCIA_EM_CENTAVOS
            ),
            None,
        )
        if avulsa is None:
            return None
        usadas.add(id(avulsa))
        trocadas[id(avulsa)] = replace(avulsa, parcela=(numero, total))
        return trocadas[id(avulsa)]

    for cadeia in sorted(cadeias, key=lambda c: c[0].mes):
        if not any(c is cadeia for c in cadeias):
            continue  # já entrou numa sequência anterior
        while cadeia[-1].parcela[0] < total:
            ultima = cadeia[-1]
            parcela = deduzida(ultima, mes_seguinte(ultima.mes), ultima.parcela[0] + 1)
            if parcela is None:
                break
            cadeia.append(parcela)
            seguinte = next(
                (
                    i
                    for i, c in enumerate(cadeias)
                    if c is not cadeia
                    and c[0].parcela[0] == parcela.parcela[0] + 1
                    and c[0].mes == mes_seguinte(parcela.mes)
                ),
                None,
            )
            if seguinte is not None:
                cadeia.extend(cadeias.pop(seguinte))
        while cadeia[0].parcela[0] > 1:
            primeira = cadeia[0]
            parcela = deduzida(primeira, mes_anterior(primeira.mes), primeira.parcela[0] - 1)
            if parcela is None:
                break
            cadeia.insert(0, parcela)


def _faltas(cadeia: list, total: int, primeiro_mes: str, ultimo_mes: str) -> list[str]:
    primeira, ultima = cadeia[0], cadeia[-1]
    faltas = []
    if primeira.parcela[0] > 1 and primeira.mes > primeiro_mes:
        faltas.append(f"falta a parcela {primeira.parcela[0] - 1} antes de {primeira.mes}")
    if ultima.parcela[0] < total and ultima.mes < ultimo_mes:
        faltas.append(f"falta a parcela {ultima.parcela[0] + 1} depois de {ultima.mes}")
    return faltas
