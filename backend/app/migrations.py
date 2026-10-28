from pathlib import Path

import psycopg

from app.banco import conectar

PASTA = Path(__file__).resolve().parents[1] / "migrations"


def aplicar_migrations(url: str | None = None) -> None:
    """Aplica em ordem os arquivos NNNN_*.sql ainda não registrados, um DDL por arquivo."""
    with conectar(url, autocommit=True) as conn:
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


def total_aplicadas(conn: psycopg.Connection) -> int:
    return conn.execute("SELECT count(*) FROM controle_de_migrations").fetchone()[0]


if __name__ == "__main__":
    aplicar_migrations()
