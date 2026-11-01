"""Em que item do planejamento conta cada lançamento (ADR 0006).

O lançamento guarda duas categorias: a escolha do casal (`item_categoria_id`) e a do item em
que ele contava sozinho quando surgiu a ambiguidade (`item_atual_categoria_id`, que só o
servidor grava). A escolha vale enquanto a categoria dela tem item no mês. Sem ela, o
lançamento conta sozinho quando só uma das categorias dele tem item; com duas ou mais, está
"a escolher" e fica no item em que estava, se estava em algum.

Para "ficar onde estava" valer, quem pode criar ambiguidade (um item novo no mês, categorias
editadas, mês trocado, categorias juntadas) chama `guardar_item_atual` antes.
"""

from uuid import UUID

# O mês em que o lançamento conta, como em `lancamentos.MES_EM_QUE_CONTA`.
_MES = "COALESCE(l.mes, date_trunc('month', l.data)::date)"


def onde_conta(
    com_item: set[UUID], escolhida: UUID | None, atual: UUID | None
) -> tuple[UUID | None, bool]:
    """A categoria cujo item conta o lançamento (ou nenhuma) e se ele está "a escolher", dadas
    as categorias dele que têm item no mês, a escolhida e a do item atual."""
    if escolhida in com_item:
        return escolhida, False
    if atual in com_item:
        return atual, len(com_item) > 1
    if len(com_item) == 1:
        return next(iter(com_item)), False
    return None, len(com_item) > 1


def guardar_item_atual(conn, filtro: str, parametros: tuple) -> None:
    """Guarda o item em que conta agora cada lançamento que `filtro` (condição sobre `l`, o
    lançamento) pega, antes de uma mudança que pode criar ambiguidade."""
    por_lancamento: dict[UUID, tuple[UUID | None, UUID | None, set[UUID]]] = {}
    for id, escolhida, atual, categoria_id in conn.execute(
        "SELECT l.id, l.item_categoria_id, l.item_atual_categoria_id, lc.categoria_id"
        " FROM lancamentos l JOIN lancamento_categorias lc ON lc.lancamento_id = l.id"
        " JOIN itens_do_planejamento i"
        f" ON i.categoria_id = lc.categoria_id AND i.mes = {_MES}"
        f" WHERE l.excluido_em IS NULL AND {filtro}",
        parametros,
    ):
        por_lancamento.setdefault(id, (escolhida, atual, set()))[2].add(categoria_id)
    for id, (escolhida, atual, com_item) in por_lancamento.items():
        conta_em, _ = onde_conta(com_item, escolhida, atual)
        if conta_em and conta_em not in (escolhida, atual):
            conn.execute(
                "UPDATE lancamentos SET item_atual_categoria_id = %s WHERE id = %s", (conta_em, id)
            )
    guardar_item_atual_das_partes(conn, filtro, parametros)


def guardar_item_atual_das_partes(conn, filtro: str, parametros: tuple) -> None:
    """`guardar_item_atual` das partes (ADR 0022) dos lançamentos que `filtro` pega; a condição
    pode usar também `p`, a parte. Cada parte conta num item, como um lançamento."""
    por_parte: dict[UUID, tuple[UUID | None, UUID | None, set[UUID]]] = {}
    for id, escolhida, atual, categoria_id in conn.execute(
        "SELECT p.id, p.item_categoria_id, p.item_atual_categoria_id, pc.categoria_id"
        " FROM lancamento_partes p JOIN lancamentos l ON l.id = p.lancamento_id"
        " JOIN parte_categorias pc ON pc.parte_id = p.id"
        " JOIN itens_do_planejamento i"
        f" ON i.categoria_id = pc.categoria_id AND i.mes = {_MES}"
        f" WHERE l.excluido_em IS NULL AND {filtro}",
        parametros,
    ):
        por_parte.setdefault(id, (escolhida, atual, set()))[2].add(categoria_id)
    for id, (escolhida, atual, com_item) in por_parte.items():
        conta_em, _ = onde_conta(com_item, escolhida, atual)
        if conta_em and conta_em not in (escolhida, atual):
            conn.execute(
                "UPDATE lancamento_partes SET item_atual_categoria_id = %s WHERE id = %s",
                (conta_em, id),
            )


def guardar_item_atual_do_lancamento(conn, id: UUID) -> None:
    """`guardar_item_atual` de um lançamento só, antes de ele mudar."""
    guardar_item_atual(conn, "l.id = %s", (id,))
