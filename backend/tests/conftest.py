import os

import psycopg
import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.migrations import aplicar_migrations


@pytest.fixture
def database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        pytest.fail("DATABASE_URL não definida: veja o README (scripts/postgres-local.sh)")
    with psycopg.connect(url, autocommit=True) as conn:
        conn.execute("DROP SCHEMA public CASCADE")
        conn.execute("CREATE SCHEMA public")
    return url


@pytest.fixture
def client(database_url: str) -> TestClient:
    aplicar_migrations(database_url)
    return TestClient(create_app(database_url))
