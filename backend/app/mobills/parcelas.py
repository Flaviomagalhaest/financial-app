"""O reagrupamento das parcelas `(n/total)` do geral em parcelamentos (`## Answer` do ticket 18): a
mesma descrição base, o mesmo total e números `n` em meses consecutivos. O valor não separa a
compra, só desempata compras iguais em paralelo, e a linha sem `(n/total)` no mês de uma parcela
que falta é essa parcela (ticket 219). As parcelas que o export não traz são do ticket 68."""

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

    A linha sem `(n/total)` com a mesma descrição, o valor de uma parcela vizinha (tolerância de 1
    centavo) e o mês exato de uma parcela que falta é essa parcela, com o número deduzido pela
    posição (ticket 219). Devolve também os lançamentos, com a parcela deduzida no lugar da linha
    sem `(n/total)`."""
    grupos = defaultdict(list)
    sem_sufixo = defaultdict(list)
    for lancamento in lancamentos:
        if lancamento.parcela:
            chave = (lancamento.tipo, lancamento.descricao.casefold(), lancamento.parcela[1])
            grupos[chave].append(lancamento)
        else:
            sem_sufixo[(lancamento.tipo, lancamento.descricao.casefold())].append(lancamento)
    deduzidas: dict[int, object] = {}  # pelo id da linha sem `(n/total)`
    parcelamentos = []
    for (tipo, descricao, total), parcelas in grupos.items():
        cadeias = _cadeias(parcelas)
        deduzidas |= _preencher_buracos(cadeias, total, sem_sufixo[(tipo, descricao)])
        no_mes = defaultdict(list)
        for cadeia in cadeias:
            for parcela in cadeia:
                no_mes[(parcela.mes, parcela.parcela[0])].append(parcela)
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
    return parcelamentos, [deduzidas.get(id(x), x) for x in lancamentos]


def mesmo_valor(a, b) -> bool:
    return abs(a.valor_centavos - b.valor_centavos) <= TOLERANCIA_EM_CENTAVOS


def _tem_par_no_mes(parcela, no_mes: dict) -> bool:
    """Outra parcela de mesmo número no mês e com o mesmo valor; com outro valor é outra compra
    igual em paralelo (ticket 219)."""
    return any(
        outra is not parcela and mesmo_valor(outra, parcela)
        for outra in no_mes[(parcela.mes, parcela.parcela[0])]
    )


def _mais_perto(candidatas: list, de) -> list:
    """O desempate entre compras iguais em paralelo (ticket 219): o valor mais perto, depois o
    mesmo cartão. Cada candidata é uma parcela."""
    return sorted(
        candidatas,
        key=lambda x: (abs(x.valor_centavos - de.valor_centavos), x.cartao != de.cartao),
    )


def _cadeias(parcelas: list) -> list[list]:
    """As parcelas `(n/total)` de uma descrição em sequências de números e meses seguidos. O valor
    não separa a compra (ticket 219): só desempata parcelamentos iguais em paralelo."""
    cadeias: list[list] = []
    for parcela in sorted(parcelas, key=lambda x: (x.mes, x.parcela[0])):
        continua = {
            id(c[-1]): c
            for c in cadeias
            if c[-1].parcela[0] == parcela.parcela[0] - 1 and mes_seguinte(c[-1].mes) == parcela.mes
        }
        if continua:
            ultimas = _mais_perto([c[-1] for c in continua.values()], parcela)
            continua[id(ultimas[0])].append(parcela)
        else:
            cadeias.append([parcela])
    return cadeias


def _preencher_buracos(cadeias: list[list], total: int, sem_sufixo: list) -> dict[int, object]:
    """Põe a linha sem `(n/total)` no lugar da parcela que falta antes ou depois de cada sequência
    e junta a sequência com a que continua no mês seguinte (muda `cadeias`). Devolve as parcelas
    deduzidas pelo id da linha sem `(n/total)`."""
    deduzidas: dict[int, object] = {}

    def deduzir(vizinhas: list, mes: str, numero: int):
        candidatas = [
            x
            for x in sem_sufixo
            if id(x) not in deduzidas
            and x.mes == mes
            and any(mesmo_valor(x, vizinha) for vizinha in vizinhas)
        ]
        if not candidatas:
            return None
        linha = _mais_perto(candidatas, vizinhas[0])[0]
        deduzidas[id(linha)] = replace(linha, parcela=(numero, total))
        return deduzidas[id(linha)]

    for cadeia in sorted(cadeias, key=lambda c: c[0].mes):
        if not any(c is cadeia for c in cadeias):
            continue  # já entrou numa sequência anterior
        while cadeia[-1].parcela[0] < total:
            ultima = cadeia[-1]
            mes = mes_seguinte(ultima.mes)
            seguintes = {
                id(c[0]): c
                for c in cadeias
                if c is not cadeia
                and c[0].parcela[0] == ultima.parcela[0] + 2
                and c[0].mes == mes_seguinte(mes)
            }
            primeiras = [c[0] for c in seguintes.values()]
            parcela = deduzir([ultima, *primeiras], mes, ultima.parcela[0] + 1)
            if parcela is None:
                break
            cadeia.append(parcela)
            if primeiras:
                seguinte = seguintes[id(_mais_perto(primeiras, parcela)[0])]
                cadeias[:] = [c for c in cadeias if c is not seguinte]
                cadeia.extend(seguinte)
        while cadeia[0].parcela[0] > 1:
            primeira = cadeia[0]
            parcela = deduzir([primeira], mes_anterior(primeira.mes), primeira.parcela[0] - 1)
            if parcela is None:
                break
            cadeia.insert(0, parcela)
    return deduzidas


def _faltas(cadeia: list, total: int, primeiro_mes: str, ultimo_mes: str) -> list[str]:
    primeira, ultima = cadeia[0], cadeia[-1]
    faltas = []
    if primeira.parcela[0] > 1 and primeira.mes > primeiro_mes:
        faltas.append(f"falta a parcela {primeira.parcela[0] - 1} antes de {primeira.mes}")
    if ultima.parcela[0] < total and ultima.mes < ultimo_mes:
        faltas.append(f"falta a parcela {ultima.parcela[0] + 1} depois de {ultima.mes}")
    return faltas
