import os

import psycopg
import psycopg.errors
import pytest
from fastapi.testclient import TestClient

from app import banco
from app.main import create_app
from app.migrations import aplicar_migrations
from tests.emissor import Emissor
from tests.exemplo_ficticio import criar_exemplo_ficticio


@pytest.fixture(scope="session")
def emissor() -> Emissor:
    return Emissor()


@pytest.fixture
def database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        pytest.fail("DATABASE_URL não definida: veja o README (scripts/postgres-local.sh)")
    with psycopg.connect(url, autocommit=True) as conn:
        banco = conn.execute("SELECT current_database()").fetchone()[0]
        if "financial_app" not in banco:
            pytest.fail(f"recusado: os testes apagam o schema e '{banco}' não parece de teste")
        conn.execute("DROP SCHEMA public CASCADE")
        conn.execute("CREATE SCHEMA public")
    return url


@pytest.fixture
def client(database_url: str, emissor: Emissor) -> TestClient:
    aplicar_migrations(database_url)
    return TestClient(create_app(database_url, verificador=emissor.verificador()))


@pytest.fixture
def banco_ficticio(database_url: str):
    """Banco migrado com o exemplo fictício do backup (tests/exemplo_ficticio.py)."""
    aplicar_migrations(database_url)
    with psycopg.connect(database_url, autocommit=True) as conn:
        criar_exemplo_ficticio(conn)
        yield conn


class ConexaoQueFalhaNoCommit:
    """Conexão real que, quando `falhar`, perde a disputa otimista ao confirmar (40001)."""

    def __init__(self, real, falhar: bool):
        self._real, self._falhar = real, falhar

    def __getattr__(self, nome):
        return getattr(self._real, nome)

    def __enter__(self):
        self._real.__enter__()
        return self

    def __exit__(self, tipo, valor, tb):
        if tipo is None and self._falhar:
            self._real.rollback()
            self._real.__exit__(None, None, None)
            raise psycopg.errors.SerializationFailure("OC000")
        return self._real.__exit__(tipo, valor, tb)


@pytest.fixture
def falhar_ao_confirmar(monkeypatch: pytest.MonkeyPatch):
    """Faz as `n` primeiras transações de escrita terminarem em erro de serialização (40001)."""

    def preparar(n: int) -> list[int]:
        abertas = [0]
        original = psycopg.connect

        def conectar(*args, **kwargs):
            abertas[0] += 1
            return ConexaoQueFalhaNoCommit(original(*args, **kwargs), abertas[0] <= n)

        monkeypatch.setattr(banco.psycopg, "connect", conectar)
        return abertas

    return preparar
