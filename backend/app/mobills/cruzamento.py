"""O cruzamento das faturas com o geral (ADR 0007, `## Answer` do ticket 18): cada linha de fatura
procura o seu par no geral pelo mês, a descrição sem `(n/total)`, o valor e a categoria."""

from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field

from app.mobills.leitura import LinhaDeFatura, LinhaDoGeral


@dataclass(frozen=True)
class Par:
    fatura: LinhaDeFatura
    geral: LinhaDoGeral
    como: str  # 'exato', 'sem categoria' ou 'provável' (só o valor, confirmado pelo dono)


@dataclass(frozen=True)
class Provavel:
    """No mesmo mês, a única linha de fatura e a única do geral que sobraram com o mesmo valor."""

    fatura: LinhaDeFatura
    geral: LinhaDoGeral
    decisao: str | None  # do dono na planilha: 'juntar', 'separar' ou ainda aberto


@dataclass(frozen=True)
class LinhaDoGrupo:
    """Uma linha de um grupo ambíguo: o par, ou o lado que sobrou, e o que aconteceu com ela."""

    fatura: LinhaDeFatura | None
    geral: LinhaDoGeral | None
    resultado: str  # 'par', 'descartada' (a duplicada do Mobills, que não entra) ou 'sem par'


@dataclass(frozen=True)
class Repetida:
    """Linha de fatura sem par que repete o cartão, a data e o valor de uma linha já casada (o
    Mobills duplicou a compra na fatura, ticket 217). Entra como compra até o dono decidir."""

    fatura: LinhaDeFatura
    casada: Par
    decisao: str | None  # do dono na planilha: 'descartar', 'manter' ou ainda aberto


@dataclass
class Cruzamento:
    pares: list[Par] = field(default_factory=list)
    # Todos os prováveis; os juntados também estão em `pares`, os separados nas sobras, e os
    # abertos só aqui (cada lado entra sozinho até o dono decidir).
    provaveis: list[Provavel] = field(default_factory=list)
    fatura_sem_par: list[LinhaDeFatura] = field(default_factory=list)
    geral_sem_par: list[LinhaDoGeral] = field(default_factory=list)
    # Grupos de mesma chave em que as linhas do geral diferem nas tags ou na situação: casaram
    # na ordem, mas outra ordem daria outro resultado. Quando a diferença é a situação, a fatura
    # casa primeiro com a paga e a pendente que sobra é a duplicada do Mobills (ticket 216).
    ambiguos: list[list[LinhaDoGrupo]] = field(default_factory=list)
    # Todas as linhas de fatura sem par que repetem uma casada; as que o dono mandou descartar
    # não estão em `fatura_sem_par`.
    repetidas: list[Repetida] = field(default_factory=list)

    def descartadas(self) -> list[tuple[str | None, str, int]]:
        """O que o importador deixou de fora e o Mobills pode contar: a pasta (sem ela, quando só
        o geral tinha a linha), o mês e o custo, pelos grupos ambíguos e pelas repetidas."""
        saida = []
        for grupo in self.ambiguos:
            for x in grupo:
                if x.resultado == "descartada":
                    if x.fatura:
                        saida.append((x.fatura.pasta, x.fatura.mes, x.fatura.valor_centavos))
                    elif x.geral:
                        saida.append((None, x.geral.mes, -x.geral.valor_centavos))
        saida += [
            (r.fatura.pasta, r.fatura.mes, r.fatura.valor_centavos)
            for r in self.repetidas
            if _descartar(r.decisao)
        ]
        return saida


def chave_do_provavel(fatura: LinhaDeFatura, geral: LinhaDoGeral) -> tuple:
    """O que identifica um par provável de uma rodada para a outra, mesmo com o export refeito."""
    return (
        fatura.pasta,
        fatura.mes,
        fatura.data,
        fatura.descricao,
        fatura.valor_centavos,
        geral.data,
        geral.descricao,
    )


def chave_da_repetida(fatura: LinhaDeFatura) -> tuple:
    """O que identifica a linha repetida de uma rodada para a outra."""
    return (fatura.pasta, fatura.mes, fatura.data, fatura.descricao, fatura.valor_centavos)


def _descartar(decisao: str | None) -> bool:
    return (decisao or "").casefold() == "descartar"


def chave_do_grupo(geral: LinhaDoGeral) -> tuple:
    """Mês, descrição e valor (como a fatura, compra positiva): o que a aba mostra do grupo."""
    return (geral.mes, geral.descricao, -geral.valor_centavos)


def cruzar(
    geral: list[LinhaDoGeral],
    faturas: list[LinhaDeFatura],
    decisoes_dos_provaveis: dict[tuple, str] | None = None,
    grupos_mantidos: set[tuple] | None = None,
    decisoes_das_repetidas: dict[tuple, str] | None = None,
) -> Cruzamento:
    resultado = Cruzamento()
    # A ordem em que as linhas de um grupo casam: pela data da compra, de qualquer cartão.
    sobra_da_fatura = sorted(faturas, key=lambda x: (x.mes, x.data, x.pasta))
    sobra_do_geral = list(geral)
    for como, chave_da_fatura, chave_do_geral in (
        (
            "exato",
            lambda x: (x.mes, x.descricao.casefold(), x.valor_centavos, x.categoria),
            lambda x: (x.mes, x.descricao.casefold(), -x.valor_centavos, x.categoria),
        ),
        (
            "sem categoria",
            lambda x: (x.mes, x.descricao.casefold(), x.valor_centavos),
            lambda x: (x.mes, x.descricao.casefold(), -x.valor_centavos),
        ),
    ):
        pares, sobra_da_fatura, sobra_do_geral, ambiguos = _casar_na_ordem(
            sobra_da_fatura,
            sobra_do_geral,
            chave_da_fatura,
            chave_do_geral,
            grupos_mantidos or set(),
        )
        resultado.pares.extend(Par(f, g, como) for f, g in pares)
        resultado.ambiguos.extend(ambiguos)

    decisoes = decisoes_dos_provaveis or {}
    candidatos_da_fatura = _unicos_por(sobra_da_fatura, lambda x: (x.mes, x.valor_centavos))
    candidatos_do_geral = _unicos_por(sobra_do_geral, lambda x: (x.mes, -x.valor_centavos))
    for chave, fatura in candidatos_da_fatura.items():
        par = candidatos_do_geral.get(chave)
        if par is None:
            continue
        decisao = decisoes.get(chave_do_provavel(fatura, par))
        resultado.provaveis.append(Provavel(fatura, par, decisao))
        if decisao == "juntar":
            resultado.pares.append(Par(fatura, par, "provável"))
    fora = {
        id(lado)
        for provavel in resultado.provaveis
        if provavel.decisao != "separar"
        for lado in (provavel.fatura, provavel.geral)
    }
    resultado.fatura_sem_par = [x for x in sobra_da_fatura if id(x) not in fora]
    resultado.geral_sem_par = [x for x in sobra_do_geral if id(x) not in fora]

    casadas: dict[tuple, Par] = {}
    for par in resultado.pares:
        casadas.setdefault((par.fatura.pasta, par.fatura.data, par.fatura.valor_centavos), par)
    for fatura in resultado.fatura_sem_par:
        casada = casadas.get((fatura.pasta, fatura.data, fatura.valor_centavos))
        if casada is not None:
            decisao = (decisoes_das_repetidas or {}).get(chave_da_repetida(fatura))
            resultado.repetidas.append(Repetida(fatura, casada, decisao))
    descartadas = {id(r.fatura) for r in resultado.repetidas if _descartar(r.decisao)}
    resultado.fatura_sem_par = [x for x in resultado.fatura_sem_par if id(x) not in descartadas]
    return resultado


def _unicos_por[T](linhas: list[T], chave: Callable[[T], tuple]) -> dict[tuple, T]:
    """As linhas que são as únicas com a sua chave."""
    grupos: dict[tuple, list[T]] = defaultdict(list)
    for linha in linhas:
        grupos[chave(linha)].append(linha)
    return {c: grupo[0] for c, grupo in grupos.items() if len(grupo) == 1}


def _casar_na_ordem(
    faturas: list[LinhaDeFatura],
    geral: list[LinhaDoGeral],
    chave_da_fatura: Callable[[LinhaDeFatura], tuple],
    chave_do_geral: Callable[[LinhaDoGeral], tuple],
    grupos_mantidos: set[tuple],
):
    """Linhas com a mesma chave casam na ordem: a fatura pela data da compra (a ordem de
    `faturas`), o geral pela posição; a sobra de contagem fica sem par. Devolve os pares, as
    sobras de cada lado e os grupos ambíguos."""
    do_geral: dict[tuple, list[LinhaDoGeral]] = defaultdict(list)
    for linha in geral:
        do_geral[chave_do_geral(linha)].append(linha)
    da_fatura: dict[tuple, list[LinhaDeFatura]] = defaultdict(list)
    for linha in faturas:
        da_fatura[chave_da_fatura(linha)].append(linha)
    pares = []
    sobra_da_fatura = []
    ambiguos = []
    usadas = set()
    for chave, linhas in da_fatura.items():
        candidatas = do_geral.get(chave, [])
        ambiguo = len(candidatas) > 1 and len({(g.tags, g.situacao) for g in candidatas}) > 1
        if (
            ambiguo
            and len({g.situacao for g in candidatas}) > 1
            and chave_do_grupo(candidatas[0]) not in grupos_mantidos
        ):
            grupo = _sem_as_pendentes_duplicadas(linhas, candidatas)
        else:
            grupo = [LinhaDoGrupo(f, g, "par") for f, g in zip(linhas, candidatas)]
            grupo += [LinhaDoGrupo(f, None, "sem par") for f in linhas[len(candidatas) :]]
            grupo += [LinhaDoGrupo(None, g, "sem par") for g in candidatas[len(linhas) :]]
        pares.extend((x.fatura, x.geral) for x in grupo if x.resultado == "par")
        sobra_da_fatura.extend(x.fatura for x in grupo if x.fatura and x.resultado == "sem par")
        usadas.update(x.geral.posicao for x in grupo if x.geral and x.resultado != "sem par")
        if ambiguo:
            ambiguos.append(grupo)
    ordem = {id(x): i for i, x in enumerate(faturas)}
    sobra_da_fatura.sort(key=lambda x: ordem[id(x)])
    return pares, sobra_da_fatura, [x for x in geral if x.posicao not in usadas], ambiguos


def _sem_as_pendentes_duplicadas(
    linhas: list[LinhaDeFatura], candidatas: list[LinhaDoGeral]
) -> list[LinhaDoGrupo]:
    """A fatura casa primeiro com as pagas. A pendente que sobra é a previsão que o Mobills
    deixou junto da compra paga e é descartada, com a linha de fatura que repete a data e o
    cartão de uma já casada (o Mobills duplicou as duas). Uma linha de fatura de outra data
    casa com a pendente, como antes: são duas compras."""
    pagas = [g for g in candidatas if g.situacao != "Pendente"]
    pendentes = [g for g in candidatas if g.situacao == "Pendente"]
    grupo = [LinhaDoGrupo(f, g, "par") for f, g in zip(linhas, pagas)]
    casadas = {(x.fatura.pasta, x.fatura.data) for x in grupo}
    restantes = []
    for fatura in linhas[len(pagas) :]:
        if pendentes and (fatura.pasta, fatura.data) in casadas:
            grupo.append(LinhaDoGrupo(fatura, pendentes.pop(0), "descartada"))
        else:
            restantes.append(fatura)
    grupo += [LinhaDoGrupo(f, g, "par") for f, g in zip(restantes, pendentes)]
    grupo += [LinhaDoGrupo(f, None, "sem par") for f in restantes[len(pendentes) :]]
    grupo += [LinhaDoGrupo(None, g, "descartada") for g in pendentes[len(restantes) :]]
    grupo += [LinhaDoGrupo(None, g, "sem par") for g in pagas[len(linhas) :]]
    return grupo
