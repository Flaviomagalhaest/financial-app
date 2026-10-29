"""Em que item do planejamento conta cada lançamento (ADR 0006).

O lançamento guarda a categoria cujo item ele conta (`item_categoria_id`) e se foi o casal que
a escolheu (`item_explicito`). A categoria guardada vale enquanto ela tem item no mês; sem ela,
o lançamento conta sozinho quando só uma das categorias dele tem item. Com duas ou mais e sem
escolha explícita, ele está "a escolher": fica no item em que estava, se estava em algum.

Para "ficar onde estava" valer, quem pode criar ambiguidade (um item novo no mês, categorias
editadas, mês trocado, categorias juntadas) chama `fixar` antes, e o item em que o lançamento
conta sozinho passa a ser guardado.
"""

from uuid import UUID

# O mês em que o lançamento conta, como em `lancamentos.MES_EM_QUE_CONTA`.
_MES = "COALESCE(l.mes, date_trunc('month', l.data)::date)"


def onde_conta(
    com_item: set[UUID], guardada: UUID | None, explicita: bool
) -> tuple[UUID | None, bool]:
    """A categoria cujo item conta o lançamento (ou nenhuma) e se ele está "a escolher", dadas
    as categorias dele que têm item no mês e a categoria guardada."""
    if guardada in com_item:
        return guardada, len(com_item) > 1 and not explicita
    if len(com_item) == 1:
        return next(iter(com_item)), False
    return None, len(com_item) > 1


def fixar(conn, filtro: str, parametros: tuple) -> None:
    """Guarda o item em que conta agora cada lançamento sem escolha explícita que `filtro`
    (condição sobre `l`, o lançamento) pega, antes de uma mudança que pode criar ambiguidade."""
    por_lancamento: dict[UUID, tuple[UUID | None, set[UUID]]] = {}
    for id, guardada, categoria_id in conn.execute(
        "SELECT l.id, l.item_categoria_id, lc.categoria_id FROM lancamentos l"
        " JOIN lancamento_categorias lc ON lc.lancamento_id = l.id"
        " JOIN itens_do_planejamento i"
        f" ON i.categoria_id = lc.categoria_id AND i.mes = {_MES}"
        " WHERE l.excluido_em IS NULL AND NOT COALESCE(l.item_explicito, false)"
        f" AND {filtro}",
        parametros,
    ):
        por_lancamento.setdefault(id, (guardada, set()))[1].add(categoria_id)
    for id, (guardada, com_item) in por_lancamento.items():
        conta_em, _ = onde_conta(com_item, guardada, explicita=False)
        if conta_em and conta_em != guardada:
            conn.execute(
                "UPDATE lancamentos SET item_categoria_id = %s WHERE id = %s", (conta_em, id)
            )
