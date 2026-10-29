import os
from pathlib import Path

import psycopg

from app.banco import PAPEL_DA_API, PAPEL_DO_BACKUP, conectar

PASTA = Path(__file__).resolve().parents[1] / "migrations"


def aplicar_migrations(url: str | None = None) -> None:
    """Aplica em ordem os arquivos NNNN_*.sql ainda não registrados, um DDL por arquivo.

    O DSQL só cria índice com `CREATE INDEX ASYNC`, que o Postgres local e o do CI não
    conhecem: fora do DSQL, o índice é criado na hora.
    """
    no_dsql = url is None and bool(os.environ.get("DSQL_ENDPOINT"))
    with conectar(url, autocommit=True, admin=True) as conn:
        ja_aplicadas: set[str] = set()
        if conn.execute("SELECT to_regclass('controle_de_migrations') IS NOT NULL").fetchone()[0]:
            ja_aplicadas = {
                linha[0] for linha in conn.execute("SELECT nome FROM controle_de_migrations")
            }
        for arquivo in sorted(PASTA.glob("[0-9][0-9][0-9][0-9]_*.sql")):
            if arquivo.name in ja_aplicadas:
                continue
            sql = arquivo.read_text()
            conn.execute(sql if no_dsql else sql.replace("CREATE INDEX ASYNC", "CREATE INDEX"))
            conn.execute("INSERT INTO controle_de_migrations (nome) VALUES (%s)", (arquivo.name,))
        if os.environ.get("DSQL_ENDPOINT"):
            if papel_arn := os.environ.get("API_ROLE_ARN"):
                _conceder_ao_papel_da_api(conn, papel_arn)
            if papel_arn := os.environ.get("BACKUP_ROLE_ARN"):
                _conceder_ao_papel_do_backup(conn, papel_arn)


def _literal(texto: str) -> str:
    return texto.replace("'", "''")


def _conceder_ao_papel_da_api(conn: psycopg.Connection, papel_arn: str) -> None:
    """Liga o papel da API à role IAM da Lambda e libera leitura e escrita nas tabelas (só leitura em `controle_de_migrations`).

    Roda a cada deploy: o DSQL não tem `ALTER DEFAULT PRIVILEGES`, então as tabelas criadas
    pelas migrations novas recebem o `GRANT` aqui, depois de aplicadas.
    """
    papel = PAPEL_DA_API
    _ligar_papel_a_role(conn, papel, papel_arn)
    # Sem GRANT USAGE: o DSQL recusa no schema `public` (entidade de sistema) e já o libera.
    conn.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {papel}")
    # A API só lê o controle das migrations (a /api/saude conta as aplicadas).
    conn.execute(f"REVOKE INSERT, UPDATE, DELETE ON controle_de_migrations FROM {papel}")


def _conceder_ao_papel_do_backup(conn: psycopg.Connection, papel_arn: str) -> None:
    """Liga o papel do backup à role IAM da Lambda do backup, só com leitura (ADR 0012)."""
    _ligar_papel_a_role(conn, PAPEL_DO_BACKUP, papel_arn)
    conn.execute(f"GRANT SELECT ON ALL TABLES IN SCHEMA public TO {PAPEL_DO_BACKUP}")


def _ligar_papel_a_role(conn: psycopg.Connection, papel: str, papel_arn: str) -> None:
    """Cria o papel do banco, se faltar, e o deixa ligado só à role IAM de `papel_arn`."""
    if not conn.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (papel,)).fetchone():
        conn.execute(f"CREATE ROLE {papel} WITH LOGIN")
    # AWS IAM GRANT não aceita parâmetros; o ARN vem da saída da pilha, não de entrada externa.
    mapeados = {
        linha[0]
        for linha in conn.execute(
            "SELECT arn FROM sys.iam_pg_role_mappings WHERE pg_role_name = %s", (papel,)
        )
    }
    # Role da Lambda substituída: o ARN novo troca o antigo, senão o login falha.
    for antigo in mapeados - {papel_arn}:
        conn.execute(f"AWS IAM REVOKE {papel} FROM '{_literal(antigo)}'")
    if papel_arn not in mapeados:
        conn.execute(f"AWS IAM GRANT {papel} TO '{_literal(papel_arn)}'")


def total_aplicadas(conn: psycopg.Connection) -> int:
    return conn.execute("SELECT count(*) FROM controle_de_migrations").fetchone()[0]


if __name__ == "__main__":
    aplicar_migrations()
