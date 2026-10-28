"""Exemplo fictício para o backup: as tabelas de exemplo têm prefixo `exemplo_` para não
colidir com as do domínio, e o gerador lê qualquer tabela do banco. Dado real nunca entra aqui (ADR 0012)."""

import psycopg

ESQUEMA_FICTICIO = [
    """CREATE TABLE exemplo_contas (
        id uuid PRIMARY KEY,
        nome text NOT NULL,
        saldo_de_abertura numeric(12, 2) NOT NULL
    )""",
    """CREATE TABLE exemplo_lancamentos (
        id uuid PRIMARY KEY,
        conta_id uuid NOT NULL,
        descricao text NOT NULL,
        valor numeric(12, 2) NOT NULL,
        data date NOT NULL,
        observacao text
    )""",
]

CONTA_CORRENTE = "00000000-0000-0000-0000-00000000000a"
CONTA_POUPANCA = "00000000-0000-0000-0000-00000000000b"


def criar_exemplo_ficticio(conn: psycopg.Connection) -> None:
    for ddl in ESQUEMA_FICTICIO:
        conn.execute(ddl)
    conn.execute(
        "INSERT INTO exemplo_contas VALUES (%s, 'Poupança', 1000.00), (%s, 'Corrente', 250.50)",
        (CONTA_POUPANCA, CONTA_CORRENTE),
    )
    conn.execute(
        """INSERT INTO exemplo_lancamentos VALUES
        ('00000000-0000-0000-0000-000000000003', %(c)s, 'Mercado', -120.35, '2026-10-02', ''),
        ('00000000-0000-0000-0000-000000000001', %(c)s, 'Salário', 5000.00, '2026-10-01', NULL),
        ('00000000-0000-0000-0000-000000000002', %(c)s, 'Pão; "fresco"', -8.90, '2026-10-01',
         E'linha 1\\nlinha 2')""",
        {"c": CONTA_CORRENTE},
    )
