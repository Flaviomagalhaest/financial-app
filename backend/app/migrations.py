import os
from pathlib import Path

import psycopg

from app.banco import PAPEL_DA_API, conectar

PASTA = Path(__file__).resolve().parents[1] / "migrations"


def aplicar_migrations(url: str | None = None) -> None:
    """Aplica em ordem os arquivos NNNN_*.sql ainda não registrados, um DDL por arquivo."""
    with conectar(url, autocommit=True, admin=True) as conn:
        ja_aplicadas: set[str] = set()
        if conn.execute("SELECT to_regclass('controle_de_migrations') IS NOT NULL").fetchone()[0]:
            ja_aplicadas = {
                linha[0] for linha in conn.execute("SELECT nome FROM controle_de_migrations")
            }
        for arquivo in sorted(PASTA.glob("[0-9][0-9][0-9][0-9]_*.sql")):
            if arquivo.name in ja_aplicadas:
                continue
            conn.execute(arquivo.read_text())
            conn.execute("INSERT INTO controle_de_migrations (nome) VALUES (%s)", (arquivo.name,))
        if papel_arn := os.environ.get("API_ROLE_ARN"):
            _conceder_ao_papel_da_api(conn, papel_arn)


def _conceder_ao_papel_da_api(conn: psycopg.Connection, papel_arn: str) -> None:
    """Cria o papel da API (ligado à role IAM da Lambda) e libera leitura e escrita nas tabelas.

    Roda a cada deploy: o DSQL não tem `ALTER DEFAULT PRIVILEGES`, então as tabelas criadas
    pelas migrations novas recebem o `GRANT` aqui, depois de aplicadas.
    """
    papel = PAPEL_DA_API
    if not conn.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (papel,)).fetchone():
        conn.execute(f"CREATE ROLE {papel} WITH LOGIN")
    # AWS IAM GRANT não aceita parâmetros; o ARN vem da saída da pilha, não de entrada externa.
    arn = papel_arn.replace("'", "''")
    if not conn.execute(
        "SELECT 1 FROM sys.iam_pg_role_mappings WHERE pg_role_name = %s", (papel,)
    ).fetchone():
        conn.execute(f"AWS IAM GRANT {papel} TO '{arn}'")
    conn.execute(f"GRANT USAGE ON SCHEMA public TO {papel}")
    conn.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {papel}")


def total_aplicadas(conn: psycopg.Connection) -> int:
    return conn.execute("SELECT count(*) FROM controle_de_migrations").fetchone()[0]


if __name__ == "__main__":
    aplicar_migrations()
