"""As partes de uma regra que gera lançamentos (ADR 0022): a recorrência que junta coisas
diferentes (ticket 140; o parcelamento do ticket 139 pode guardar as dele aqui também, pelo id).
A regra guarda as partes no valor dela, como proporção; cada lançamento que ela gera recebe as
suas, com ids próprios, divididas pelo valor dele (`partes.redividir`)."""

from uuid import UUID, uuid5

from app.lancamentos import Parte, ids_das_tags


def ler(conn, ids: list[UUID]) -> dict[UUID, list[Parte]]:
    """As partes de cada regra, na ordem."""
    linhas = conn.execute(
        "SELECT id, regra_id, descricao, valor_centavos, pessoa, item_categoria_id"
        " FROM regra_partes WHERE regra_id = ANY(%s) ORDER BY regra_id, ordem",
        (ids,),
    ).fetchall()
    partes = [linha[0] for linha in linhas]
    categorias: dict[UUID, list[UUID]] = {}
    for parte_id, categoria_id in conn.execute(
        "SELECT parte_id, categoria_id FROM regra_parte_categorias WHERE parte_id = ANY(%s)"
        " ORDER BY categoria_id",
        (partes,),
    ):
        categorias.setdefault(parte_id, []).append(categoria_id)
    tags: dict[UUID, list[str]] = {}
    for parte_id, nome in conn.execute(
        "SELECT pt.parte_id, t.nome FROM regra_parte_tags pt JOIN tags t ON t.id = pt.tag_id"
        " WHERE pt.parte_id = ANY(%s) ORDER BY t.nome",
        (partes,),
    ):
        tags.setdefault(parte_id, []).append(nome)
    por_regra: dict[UUID, list[Parte]] = {}
    for id, regra_id, descricao, valor, pessoa, item in linhas:
        por_regra.setdefault(regra_id, []).append(
            Parte.model_construct(
                id=id,
                descricao=descricao,
                valor_centavos=valor,
                categoria_ids=categorias.get(id, []),
                tags=tags.get(id, []),
                pessoa=pessoa,
                item_categoria_id=item,
            )
        )
    return por_regra


def categorias(conn, regra_id: UUID) -> frozenset[UUID]:
    """As categorias que as partes da regra já têm: a arquivada segue valendo para ela."""
    return frozenset(
        c
        for (c,) in conn.execute(
            "SELECT pc.categoria_id FROM regra_parte_categorias pc"
            " JOIN regra_partes p ON p.id = pc.parte_id WHERE p.regra_id = %s",
            (regra_id,),
        )
    )


def tags(conn, regra_id: UUID) -> frozenset[UUID]:
    """As tags que as partes da regra já têm, como `categorias`."""
    return frozenset(
        t
        for (t,) in conn.execute(
            "SELECT pt.tag_id FROM regra_parte_tags pt"
            " JOIN regra_partes p ON p.id = pt.parte_id WHERE p.regra_id = %s",
            (regra_id,),
        )
    )


def gravar(conn, regra_id: UUID, partes: list[Parte], usuario: str, ja_tinha: set[UUID]) -> None:
    """Troca as partes da regra pela lista. A tag arquivada só vale para quem já a tinha
    (`ja_tinha`: as da regra e as das partes dela)."""
    tags_de_cada = [ids_das_tags(conn, p.tags, usuario, ja_tinha) for p in partes]
    apagar(conn, [regra_id])
    for ordem, (parte, tags_da_parte) in enumerate(zip(partes, tags_de_cada)):
        conn.execute(
            "INSERT INTO regra_partes (id, regra_id, ordem, descricao, valor_centavos, pessoa,"
            " item_categoria_id) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (
                parte.id,
                regra_id,
                ordem,
                parte.descricao,
                parte.valor_centavos,
                parte.pessoa,
                parte.item_categoria_id,
            ),
        )
        for categoria in parte.categoria_ids:
            conn.execute(
                "INSERT INTO regra_parte_categorias (parte_id, categoria_id) VALUES (%s, %s)",
                (parte.id, categoria),
            )
        for tag in tags_da_parte:
            conn.execute(
                "INSERT INTO regra_parte_tags (parte_id, tag_id) VALUES (%s, %s)", (parte.id, tag)
            )


def apagar(conn, regra_ids: list[UUID]) -> None:
    partes = [
        p
        for (p,) in conn.execute(
            "SELECT id FROM regra_partes WHERE regra_id = ANY(%s)", (regra_ids,)
        )
    ]
    if not partes:
        return
    conn.execute("DELETE FROM regra_parte_categorias WHERE parte_id = ANY(%s)", (partes,))
    conn.execute("DELETE FROM regra_parte_tags WHERE parte_id = ANY(%s)", (partes,))
    conn.execute("DELETE FROM regra_partes WHERE id = ANY(%s)", (partes,))


def do_lancamento(lancamento_id: UUID, partes: list[Parte]) -> list[Parte]:
    """As partes da regra como um lançamento gerado as recebe: o id vem do lançamento e da parte
    da regra, e gerar ou reajustar de novo não muda o id da mesma parte."""
    return [p.model_copy(update={"id": uuid5(lancamento_id, str(p.id))}) for p in partes]


def linhas(partes: list[Parte]) -> int:
    """Quantas linhas as partes ocupam num lançamento, para a folga da transação."""
    return sum(1 + len(p.categoria_ids) + len(p.tags) for p in partes)
