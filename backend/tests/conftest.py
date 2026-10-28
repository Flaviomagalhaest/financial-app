import os

import psycopg
import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.migrations import aplicar_migrations
from tests.emissor import Emissor


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
