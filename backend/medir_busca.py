"""Mede a busca (`app.busca.buscar`) num banco com o volume do histórico do Mobills desde 2019
(ticket 112). Gera lançamentos fictícios com `generate_series`, roda cada cenário algumas vezes e
imprime a mediana. Apaga as tabelas do schema `public`: use só num banco de teste.

Uso: DATABASE_URL=... (Postgres) ou DSQL_ENDPOINT=... e AWS_REGION=... (Aurora DSQL, ticket 119),
depois `uv run python medir_busca.py [lançamentos avulsos] [parcelamentos de 5 parcelas] [--explicar]`.
"""

import statistics
import sys
import time

import psycopg

from app import busca
from app.banco import conectar
from app.migrations import aplicar_migrations

LOTE = 2_500  # abaixo das 3.000 linhas por transação do DSQL (ADR 0009)
DESCRICOES = [
    "Mercado", "Padaria", "Farmácia", "Posto de gasolina", "Restaurante", "Pão de Açúcar",
    "Uber", "Netflix", "Aluguel", "Conta de luz", "Salário", "Açougue", "Feira", "Drogaria",
]  # fmt: skip


def gerar(conn, avulsos: int, parcelamentos: int) -> None:
    # O schema `public` pertence ao sistema no DSQL (nem o admin o apaga): esvazia as tabelas.
    for (tabela,) in conn.execute(
        "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
    ).fetchall():
        conn.execute(f'DROP TABLE IF EXISTS public."{tabela}" CASCADE')
    aplicar_migrations()  # DSQL_ENDPOINT, se houver; senão DATABASE_URL
    conn.execute(
        "INSERT INTO contas (id, nome, tipo, criado_por) SELECT gen_random_uuid(), 'Conta ' || n,"
        " 'corrente', 'flavio' FROM generate_series(1, 4) n"
    )
    conn.execute(
        "INSERT INTO categorias (id, nome, tipo, criado_por) SELECT gen_random_uuid(),"
        " 'Categoria ' || n, 'despesa', 'flavio' FROM generate_series(1, 40) n"
    )
    conn.execute(
        "INSERT INTO tags (id, nome, criado_por) SELECT gen_random_uuid(), 'tag' || n, 'flavio'"
        " FROM generate_series(1, 15) n"
    )
    descricoes = "(ARRAY[" + ",".join(f"'{d}'" for d in DESCRICOES) + "])"
    # Os ids saem de md5 do número, para ligar categorias e tags sem reler os lançamentos.
    # O DSQL aceita até 3.000 linhas por transação: cada comando insere um lote de LOTE linhas.
    for de in range(1, avulsos + 1, LOTE):
        ate = min(de + LOTE - 1, avulsos)
        conn.execute(
            f"""INSERT INTO lancamentos (id, tipo, situacao, valor_centavos, data, descricao,
                conta_id, criado_por, criado_em, alterado_por, alterado_em, pessoa, mes, fonte)
            SELECT md5('l' || n)::uuid, 'despesa',
                CASE WHEN n % 50 = 0 THEN 'previsto' ELSE 'realizado' END,
                100 + (n * 7919) % 90000, d, {descricoes}[1 + n % {len(DESCRICOES)}] || ' ' || n % 997,
                (SELECT id FROM contas ORDER BY id OFFSET n % 4 LIMIT 1), 'flavio', d, 'flavio', d,
                CASE n % 3 WHEN 0 THEN 'flavio' WHEN 1 THEN 'esposa' END,
                date_trunc('month', d)::date, CASE WHEN n % 20 = 0 THEN NULL ELSE 'mobills' END
            FROM (SELECT n, date '2019-01-01' + (n * 2047) % 2860 AS d
                  FROM generate_series({de}, {ate}) n) s"""
        )
        conn.execute(
            f"""INSERT INTO lancamento_categorias SELECT md5('l' || n)::uuid, c.id
            FROM generate_series({de}, {ate}) n JOIN
              (SELECT id, row_number() OVER (ORDER BY id) r FROM categorias) c ON c.r = 1 + n % 40"""
        )
        conn.execute(
            f"""INSERT INTO lancamento_tags SELECT md5('l' || n)::uuid, t.id
            FROM generate_series({de}, {ate}) n JOIN
              (SELECT id, row_number() OVER (ORDER BY id) r FROM tags) t ON t.r = 1 + n % 15
            WHERE n % 4 = 0"""
        )
    for de in range(1, parcelamentos + 1, LOTE // 5):  # 5 parcelas por parcelamento
        ate = min(de + LOTE // 5 - 1, parcelamentos)
        conn.execute(
            f"""INSERT INTO parcelamentos (id, valor_total_centavos, parcelas, data, automatico,
                descricao, conta_id, criado_por, alterado_por)
            SELECT md5('p' || n)::uuid, 50000, 5, date '2019-01-01' + (n * 131) % 2700, false,
                'Compra parcelada ' || n,
                (SELECT id FROM contas ORDER BY id OFFSET n % 4 LIMIT 1), 'flavio', 'flavio'
            FROM generate_series({de}, {ate}) n"""
        )
        conn.execute(
            f"""INSERT INTO lancamentos (id, tipo, situacao, valor_centavos, data, descricao,
                conta_id, criado_por, alterado_por, mes, parcelamento_id, parcela)
            SELECT md5('q' || n || '-' || k)::uuid, 'despesa', 'realizado', 5000 + (n * 37) % 20000, p.data + 30 * k,
                p.descricao, p.conta_id, 'flavio', 'flavio', date_trunc('month', p.data + 30 * k)::date,
                p.id, k + 1
            FROM generate_series({de}, {ate}) n, generate_series(0, 4) k,
                LATERAL (SELECT * FROM parcelamentos WHERE id = md5('p' || n)::uuid) p"""
        )
        conn.execute(
            f"""INSERT INTO lancamento_categorias
            SELECT md5('q' || n || '-' || k)::uuid, (SELECT id FROM categorias LIMIT 1)
            FROM generate_series({de}, {ate}) n, generate_series(0, 4) k"""
        )
    # O DSQL só analisa uma tabela por comando.
    for (tabela,) in conn.execute(
        "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
    ).fetchall():
        conn.execute(f'ANALYZE public."{tabela}"')


CENARIOS = {
    "sem filtro, 1ª página": {},
    "sem filtro, última página": {"pagina": "ultima"},
    "texto 'mercado'": {"texto": "mercado"},
    "texto raro 'drogaria 12'": {"texto": "drogaria 12"},
    "texto sem acento 'pao de acucar'": {"texto": "pao de acucar"},
    "período 2024": {"periodo_de": "2024-01-01", "periodo_ate": "2024-12-31"},
    "valor 100 a 200 reais": {"valor_minimo_centavos": 10000, "valor_maximo_centavos": 20000},
    "texto + período + situação": {
        "texto": "padaria",
        "periodo_de": "2023-01-01",
        "periodo_ate": "2025-12-31",
        "situacoes": ["realizado"],
    },
    "ordem por valor": {"ordem": "valor"},
}


def main() -> None:
    numeros = [a for a in sys.argv[1:] if not a.startswith("--")]
    avulsos = int(numeros[0]) if numeros else 100_000
    parcelamentos = int(numeros[1]) if len(numeros) > 1 else 4_000
    explicar = "--explicar" in sys.argv
    with conectar(autocommit=True, admin=True) as conn:
        gerar(conn, avulsos, parcelamentos)
        total = conn.execute("SELECT count(*) FROM lancamentos").fetchone()[0]
        print(f"{total} lançamentos ({avulsos} avulsos + {parcelamentos} parcelamentos)")
        # Uma categoria e uma tag que existem juntas num mesmo lançamento, senão o cenário acha 0.
        categoria, tag = conn.execute(
            "SELECT lc.categoria_id, t.nome FROM lancamento_tags lt"
            " JOIN lancamento_categorias lc ON lc.lancamento_id = lt.lancamento_id"
            " JOIN tags t ON t.id = lt.tag_id LIMIT 1"
        ).fetchone()
        cenarios = {**CENARIOS, "categoria + tag": {"categoria_ids": [categoria], "tags": [tag]}}
        for nome, criterios in cenarios.items():
            criterios = dict(criterios)
            if criterios.get("pagina") == "ultima":
                quantidade = busca.buscar(conn, busca.PedidoDeBusca()).totais.quantidade
                criterios["pagina"] = (quantidade - 1) // busca.POR_PAGINA
            pedido = busca.PedidoDeBusca(**criterios)
            tempos = []
            for _ in range(5):
                inicio = time.perf_counter()
                resultado = busca.buscar(conn, pedido)
                tempos.append((time.perf_counter() - inicio) * 1000)
            print(
                f"{nome:36} {statistics.median(tempos):7.0f} ms"
                f"  ({resultado.totais.quantidade} linhas achadas)"
            )
        if explicar:
            explicar_as_lentas(conn)


def _cronometrar(conn, sql: str, parametros=()) -> float:
    inicio = time.perf_counter()
    conn.execute(sql, parametros).fetchall()
    return (time.perf_counter() - inicio) * 1000


_COMANDOS: list[tuple[float, str]] = []


class _Cronometrado(psycopg.Cursor):
    """Cursor que anota o tempo e o começo de cada comando, para ver qual da busca é lento."""

    def execute(self, query, params=None, **kwargs):
        inicio = time.perf_counter()
        resultado = super().execute(query, params, **kwargs)
        texto = query if isinstance(query, str) else str(query)
        _COMANDOS.append(((time.perf_counter() - inicio) * 1000, " ".join(texto.split())[:110]))
        return resultado


def explicar_as_lentas(conn) -> None:
    """Separa o custo de ler a tabela do custo da consulta da busca; mostra o tempo de cada comando e o plano da página das lentas
    (`--explicar`, ticket 119): o plano diz onde o DSQL gasta os segundos."""
    print("\n== linhas base ==")
    for nome, sql in {
        "count(*) em lancamentos": "SELECT count(*) FROM lancamentos",
        "group by id (sem filtro)": "SELECT count(*) FROM (SELECT id FROM lancamentos GROUP BY 1) g",
        "ida e volta (SELECT 1)": "SELECT 1",
    }.items():
        print(f"{nome:36} {statistics.median(_cronometrar(conn, sql) for _ in range(3)):7.0f} ms")
    conn.cursor_factory = _Cronometrado
    for nome in ("período 2024", "sem filtro, última página", "categoria + tag"):
        criterios = dict(CENARIOS.get(nome, {}))
        if criterios.get("pagina") == "ultima":
            quantidade = busca.buscar(conn, busca.PedidoDeBusca()).totais.quantidade
            criterios["pagina"] = (quantidade - 1) // busca.POR_PAGINA
        if nome == "categoria + tag":
            categoria, tag = conn.execute(
                "SELECT lc.categoria_id, t.nome FROM lancamento_tags lt"
                " JOIN lancamento_categorias lc ON lc.lancamento_id = lt.lancamento_id"
                " JOIN tags t ON t.id = lt.tag_id LIMIT 1"
            ).fetchone()
            criterios = {"categoria_ids": [categoria], "tags": [tag]}
        _COMANDOS.clear()
        busca.buscar(conn, busca.PedidoDeBusca(**criterios))
        print(f"\n== comandos da busca: {nome} ==")
        for ms, texto in _COMANDOS:
            print(f"{ms:7.0f} ms  {texto}")
        pedido = busca.PedidoDeBusca(**criterios)
        linhas, parametros = busca._linhas(pedido)
        print(f"-- plano da página: {nome}")
        for (linha,) in conn.execute(
            f"EXPLAIN ANALYZE SELECT chave, parcelado, transferencia FROM {linhas}"
            f" ORDER BY {busca._ORDENS[pedido.ordem]} LIMIT %s OFFSET %s",
            [*parametros, busca.POR_PAGINA + 1, pedido.pagina * busca.POR_PAGINA],
        ):
            print(linha)
    conn.cursor_factory = psycopg.Cursor


if __name__ == "__main__":
    main()
