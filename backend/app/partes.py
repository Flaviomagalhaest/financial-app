"""Partes da compra (ADR 0022) para quem soma: categoria, tag, pessoa e item do planejamento leem
a parte, não a compra; a fatura, o mês e o saldo seguem lendo a compra (`lancamentos`).

Cada fragmento é uma tabela derivada com uma linha por classificação que conta: a do lançamento
sem partes, com `parte_id` e `valor_da_parte` nulos (vale o valor do lançamento), e a de cada
parte, com o valor e a ordem dela. A compra com partes não tem categoria, tag nem pessoa próprias, então
nada conta duas vezes."""

CATEGORIAS_QUE_CONTAM = (
    "(SELECT lancamento_id, categoria_id, NULL::uuid AS parte_id, NULL::bigint AS valor_da_parte,"
    " NULL::integer AS ordem FROM lancamento_categorias"
    " UNION ALL SELECT p.lancamento_id, pc.categoria_id, p.id, p.valor_centavos, p.ordem"
    " FROM parte_categorias pc JOIN lancamento_partes p ON p.id = pc.parte_id)"
)

TAGS_QUE_CONTAM = (
    "(SELECT lancamento_id, tag_id, NULL::uuid AS parte_id, NULL::bigint AS valor_da_parte,"
    " NULL::integer AS ordem FROM lancamento_tags"
    " UNION ALL SELECT p.lancamento_id, pt.tag_id, p.id, p.valor_centavos, p.ordem"
    " FROM parte_tags pt JOIN lancamento_partes p ON p.id = pt.parte_id)"
)

# A pessoa de cada pedaço que conta: a do lançamento sem partes e a de cada parte.
PESSOAS_QUE_CONTAM = (
    "(SELECT id AS lancamento_id, pessoa, NULL::uuid AS parte_id, NULL::bigint AS valor_da_parte,"
    " NULL::integer AS ordem FROM lancamentos WHERE NOT EXISTS"
    " (SELECT FROM lancamento_partes p WHERE p.lancamento_id = lancamentos.id)"
    " UNION ALL SELECT p.lancamento_id, p.pessoa, p.id, p.valor_centavos, p.ordem"
    " FROM lancamento_partes p)"
)


def e_estorno(tabela: str = "lancamentos") -> str:
    """O teste SQL do crédito que diminui (ADR 0016): o estorno de uma compra ou de uma parte, o de
    todas as parcelas (ticket 138) e o avulso (ticket 135). Quem soma despesas o usa."""
    return (
        f"({tabela}.estorno_de IS NOT NULL OR {tabela}.estorno_parcelamento_id IS NOT NULL"
        f" OR COALESCE({tabela}.estorno_avulso, false))"
    )


def valor(apelido: str) -> str:
    """O valor de uma linha de um dos fragmentos (`apelido`): o da parte, ou o do lançamento."""
    return f"COALESCE({apelido}.valor_da_parte, lancamentos.valor_centavos)"


def com_sinal(apelido: str) -> str:
    """O valor da linha com o sinal de quem soma despesas, como `lancamentos.VALOR_COM_SINAL`."""
    return (
        f"CASE WHEN lancamentos.tipo = 'despesa' AND NOT {e_estorno()}"
        f" THEN {valor(apelido)} ELSE -{valor(apelido)} END"
    )
