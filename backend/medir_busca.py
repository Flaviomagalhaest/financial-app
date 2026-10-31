"""Mede a busca (`app.busca.buscar`) num banco com o volume do histórico do Mobills desde 2019
(ticket 112). Gera lançamentos fictícios com `generate_series`, roda cada cenário algumas vezes e
imprime a mediana. Apaga o schema `public`: use só num banco de teste.

Uso: DATABASE_URL=... uv run python medir_busca.py [lançamentos avulsos] [parcelamentos de 5 parcelas]
"""

import os
import statistics
import sys
import time

import psycopg

from app import busca
from app.migrations import aplicar_migrations

DESCRICOES = [
    "Mercado", "Padaria", "Farmácia", "Posto de gasolina", "Restaurante", "Pão de Açúcar",
    "Uber", "Netflix", "Aluguel", "Conta de luz", "Salário", "Açougue", "Feira", "Drogaria",
]  # fmt: skip


def gerar(conn, avulsos: int, parcelamentos: int) -> None:
    conn.execute("DROP SCHEMA public CASCADE")
    conn.execute("CREATE SCHEMA public")
    aplicar_migrations(os.environ["DATABASE_URL"])
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
    conn.execute(
        f"""INSERT INTO lancamentos (id, tipo, situacao, valor_centavos, data, descricao, conta_id,
            criado_por, criado_em, alterado_por, alterado_em, pessoa, mes, fonte)
        SELECT gen_random_uuid(), 'despesa', CASE WHEN n % 50 = 0 THEN 'previsto' ELSE 'realizado' END,
            100 + (n * 7919) % 90000, d, {descricoes}[1 + n % {len(DESCRICOES)}] || ' ' || n % 997,
            (SELECT id FROM contas ORDER BY id OFFSET n % 4 LIMIT 1), 'flavio', d, 'flavio', d,
            CASE n % 3 WHEN 0 THEN 'flavio' WHEN 1 THEN 'esposa' END, date_trunc('month', d)::date,
            CASE WHEN n % 20 = 0 THEN NULL ELSE 'mobills' END
        FROM (SELECT n, date '2019-01-01' + (n * 2047) % 2860 AS d FROM generate_series(1, {avulsos}) n) s"""
    )
    conn.execute(
        """INSERT INTO lancamento_categorias SELECT l.id, c.id FROM
           (SELECT id, row_number() OVER () n FROM lancamentos) l JOIN
           (SELECT id, row_number() OVER () n FROM categorias) c ON c.n = 1 + l.n % 40"""
    )
    conn.execute(
        """INSERT INTO lancamento_tags SELECT l.id, t.id FROM
           (SELECT id, row_number() OVER () n FROM lancamentos) l JOIN
           (SELECT id, row_number() OVER () n FROM tags) t ON t.n = 1 + l.n % 15 WHERE l.n % 4 = 0"""
    )
    conn.execute(
        f"""INSERT INTO parcelamentos (id, valor_total_centavos, parcelas, data, automatico, descricao,
            conta_id, criado_por, alterado_por)
        SELECT gen_random_uuid(), 50000, 5, date '2019-01-01' + (n * 131) % 2700, false,
            'Compra parcelada ' || n, (SELECT id FROM contas LIMIT 1), 'flavio', 'flavio'
        FROM generate_series(1, {parcelamentos}) n"""
    )
    conn.execute(
        """INSERT INTO lancamentos (id, tipo, situacao, valor_centavos, data, descricao, conta_id,
            criado_por, alterado_por, mes, parcelamento_id, parcela)
        SELECT gen_random_uuid(), 'despesa', 'realizado', 10000, p.data + 30 * k, p.descricao, p.conta_id,
            'flavio', 'flavio', date_trunc('month', p.data + 30 * k)::date, p.id, k + 1
        FROM parcelamentos p, generate_series(0, 4) k"""
    )
    conn.execute(
        """INSERT INTO lancamento_categorias SELECT l.id, (SELECT id FROM categorias LIMIT 1)
           FROM lancamentos l WHERE l.parcelamento_id IS NOT NULL"""
    )
    conn.execute("ANALYZE")


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
    avulsos = int(sys.argv[1]) if len(sys.argv) > 1 else 100_000
    parcelamentos = int(sys.argv[2]) if len(sys.argv) > 2 else 4_000
    with psycopg.connect(os.environ["DATABASE_URL"], autocommit=True) as conn:
        gerar(conn, avulsos, parcelamentos)
        total = conn.execute("SELECT count(*) FROM lancamentos").fetchone()[0]
        print(f"{total} lançamentos ({avulsos} avulsos + {parcelamentos} parcelamentos)")
        conta = conn.execute("SELECT id FROM categorias LIMIT 1").fetchone()[0]
        cenarios = {**CENARIOS, "categoria + tag": {"categoria_ids": [conta], "tags": ["tag1"]}}
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


if __name__ == "__main__":
    main()
