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


@dataclass
class Cruzamento:
    pares: list[Par] = field(default_factory=list)
    # Todos os prováveis; os juntados também estão em `pares`, os separados nas sobras, e os
    # abertos só aqui (cada lado entra sozinho até o dono decidir).
    provaveis: list[Provavel] = field(default_factory=list)
    fatura_sem_par: list[LinhaDeFatura] = field(default_factory=list)
    geral_sem_par: list[LinhaDoGeral] = field(default_factory=list)
    # Grupos de mesma chave em que as linhas do geral diferem nas tags ou na situação: casaram
    # na ordem, mas outra ordem daria outro resultado. Cada item é um par do grupo.
    ambiguos: list[list[tuple[LinhaDeFatura | None, LinhaDoGeral | None]]] = field(
        default_factory=list
    )


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


def cruzar(
    geral: list[LinhaDoGeral],
    faturas: list[LinhaDeFatura],
    decisoes_dos_provaveis: dict[tuple, str] | None = None,
) -> Cruzamento:
    resultado = Cruzamento()
    sobra_da_fatura = sorted(faturas, key=lambda x: (x.pasta, x.mes, x.data))
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
            sobra_da_fatura, sobra_do_geral, chave_da_fatura, chave_do_geral
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
    for chave, linhas in da_fatura.items():
        candidatas = do_geral.get(chave, [])
        pares.extend(zip(linhas, candidatas))
        sobra_da_fatura.extend(linhas[len(candidatas) :])
        if len(candidatas) > 1 and len({(g.tags, g.situacao) for g in candidatas}) > 1:
            tamanho = max(len(linhas), len(candidatas))
            ambiguos.append(
                [
                    (
                        linhas[i] if i < len(linhas) else None,
                        candidatas[i] if i < len(candidatas) else None,
                    )
                    for i in range(tamanho)
                ]
            )
    usadas = {g.posicao for _, g in pares}
    ordem = {id(x): i for i, x in enumerate(faturas)}
    sobra_da_fatura.sort(key=lambda x: ordem[id(x)])
    return pares, sobra_da_fatura, [x for x in geral if x.posicao not in usadas], ambiguos
