"""Mede o custo de `cartoes.protegida` (ticket 127): o tempo de um lançamento no cartão e de um lote
de 50 ações, com e sem a proteção, num banco com o volume do histórico do Mobills (dois cartões
titulares, uma fatura por mês desde 2019, todas as passadas pagas). Apaga o schema `public`: use só
num banco de teste.

Uso: DATABASE_URL=... uv run python medir_fatura_paga.py [lançamentos de cartão] [repetições]
"""

import os
import statistics
import sys
import time
from datetime import date
from unittest import mock
from uuid import uuid4

import psycopg

from app import cartoes, lancamentos, lote
from app.banco import em_transacao
from app.lancamentos import NovoLancamento
from app.migrations import aplicar_migrations

URL = os.environ["DATABASE_URL"]


def gerar(conn, por_cartao: int) -> tuple[list, str]:
    conn.execute("DROP SCHEMA public CASCADE")
    conn.execute("CREATE SCHEMA public")
    aplicar_migrations(URL)
    conn.execute(
        "INSERT INTO contas (id, nome, tipo, criado_por) VALUES (gen_random_uuid(), 'Corrente',"
        " 'corrente', 'flavio')"
    )
    conn.execute(
        "INSERT INTO categorias (id, nome, tipo, criado_por) VALUES (gen_random_uuid(), 'Mercado',"
        " 'despesa', 'flavio')"
    )
    categoria = str(conn.execute("SELECT id FROM categorias").fetchone()[0])
    ids = []
    for nome in ("Nubank", "Inter"):
        (id,) = conn.execute(
            "INSERT INTO cartoes (id, nome, dia_fechamento, dia_vencimento, limite_centavos,"
            " criado_por) VALUES (gen_random_uuid(), %s, 25, 5, NULL, 'flavio') RETURNING id",
            (nome,),
        ).fetchone()
        ids.append(id)
        # Uma fatura por mês, de 2019-01 até o mês que vem; as fechadas (até 2026-09) pagas.
        conn.execute(
            "INSERT INTO faturas (cartao_id, mes, fechamento, vencimento)"
            " SELECT %s, m::date, (m + interval '24 days')::date, (m + interval '1 month 4 days')::date"
            " FROM generate_series(date '2019-01-01', date '2026-11-01', interval '1 month') m",
            (id,),
        )
        conn.execute(
            "INSERT INTO lancamentos (id, tipo, situacao, valor_centavos, data, descricao, conta_id,"
            " criado_por, alterado_por, mes) SELECT gen_random_uuid(), 'despesa', 'realizado',"
            " 100 + (n * 7919) %% 90000, d, 'Compra ' || n, %s, 'flavio', 'flavio',"
            " date_trunc('month', d)::date FROM (SELECT n, date '2019-01-01' + (n * 7) %% 2800 AS d"
            " FROM generate_series(1, %s) n) s",
            (id, por_cartao),
        )
        conn.execute(
            "INSERT INTO lancamento_categorias SELECT l.id, %s FROM lancamentos l"
            " WHERE l.conta_id = %s",
            (categoria, id),
        )
    conta = conn.execute("SELECT id FROM contas").fetchone()[0]
    # O pagamento de cada fatura passada, de qualquer valor, a deixa paga (ADR 0021).
    conn.execute(
        "INSERT INTO transferencias (id, situacao, valor_centavos, data, descricao,"
        " conta_origem_id, conta_destino_id, fatura_mes, criado_por, alterado_por)"
        " SELECT gen_random_uuid(), 'realizado', 1000, f.vencimento, 'Fatura', %s, f.cartao_id,"
        " f.mes, 'flavio', 'flavio' FROM faturas f WHERE f.mes <= date '2026-09-01'",
        (conta,),
    )
    conn.execute("ANALYZE")
    return ids, categoria


def novo(cartao, categoria) -> NovoLancamento:
    return NovoLancamento(
        id=uuid4(),
        tipo="despesa",
        valor_centavos=5000,
        data=date.today(),
        descricao="Medida",
        conta_id=cartao,
        categoria_ids=[categoria],
    )


def lancar(cartao, categoria) -> float:
    inicio = time.perf_counter()
    em_transacao(
        URL, cartoes.protegida(lambda c: lancamentos.criar(c, novo(cartao, categoria), "flavio"))
    )
    return (time.perf_counter() - inicio) * 1000


def lote_de_50(cartao, categoria) -> float:
    acoes = [lote.AcaoCriar(acao="criar", lancamento=novo(cartao, categoria)) for _ in range(50)]
    inicio = time.perf_counter()
    for acao in acoes:
        lote._executar(URL, acao, "flavio")
    return (time.perf_counter() - inicio) * 1000


def mediana(medida, repeticoes, *args) -> float:
    return statistics.median(medida(*args) for _ in range(repeticoes))


def main() -> None:
    por_cartao = int(sys.argv[1]) if len(sys.argv) > 1 else 5_500
    repeticoes = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    with psycopg.connect(URL, autocommit=True) as conn:
        ids, categoria = gerar(conn, por_cartao)
        total = conn.execute("SELECT count(*) FROM lancamentos").fetchone()[0]
        faturas = conn.execute("SELECT count(*) FROM faturas").fetchone()[0]
    print(f"{total} lançamentos de cartão, {faturas} faturas, {len(ids)} titulares")
    cartao = ids[0]
    with psycopg.connect(URL, autocommit=True) as conn:
        inicio = time.perf_counter()
        cartoes._todas(conn)
        print(f"uma leitura de todas as faturas: {(time.perf_counter() - inicio) * 1000:.0f} ms")
    for rotulo, medida, vezes in (
        ("lançamento", lancar, repeticoes),
        ("lote de 50 ações", lote_de_50, max(repeticoes // 2, 1)),
    ):
        with_ = mediana(medida, vezes, cartao, categoria)
        with mock.patch.object(cartoes, "protegida", lambda trabalho, corrigida=None: trabalho):
            sem = mediana(medida, vezes, cartao, categoria)
        print(
            f"{rotulo:18} com proteção {with_:8.0f} ms | sem {sem:8.0f} ms | custo {with_ - sem:8.0f} ms"
        )


if __name__ == "__main__":
    main()
