"""Exemplo fictício para o backup: as tabelas do domínio ainda não existem, e o gerador lê
qualquer tabela do banco. Dado real nunca entra aqui (ADR 0012)."""

import io
import zipfile

import psycopg

ESQUEMA_FICTICIO = [
    """CREATE TABLE contas (
        id uuid PRIMARY KEY,
        nome text NOT NULL,
        saldo_de_abertura numeric(12, 2) NOT NULL
    )""",
    """CREATE TABLE lancamentos (
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
        "INSERT INTO contas VALUES (%s, 'Poupança', 1000.00), (%s, 'Corrente', 250.50)",
        (CONTA_POUPANCA, CONTA_CORRENTE),
    )
    conn.execute(
        """INSERT INTO lancamentos VALUES
        ('00000000-0000-0000-0000-000000000003', %(c)s, 'Mercado', -120.35, '2026-10-02', ''),
        ('00000000-0000-0000-0000-000000000001', %(c)s, 'Salário', 5000.00, '2026-10-01', NULL),
        ('00000000-0000-0000-0000-000000000002', %(c)s, 'Pão; "fresco"', -8.90, '2026-10-01',
         E'linha 1\\nlinha 2')""",
        {"c": CONTA_CORRENTE},
    )


def trocar_arquivo(backup: bytes, nome: str, conteudo: bytes) -> bytes:
    """O mesmo zip com um arquivo trocado, para simular um backup estragado."""
    saida = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(backup)) as origem, zipfile.ZipFile(saida, "w") as destino:
        for info in origem.infolist():
            destino.writestr(info, conteudo if info.filename == nome else origem.read(info))
    return saida.getvalue()
