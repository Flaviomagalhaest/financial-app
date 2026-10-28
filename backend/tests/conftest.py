import os

import psycopg
import pytest
from fastapi.testclient import TestClient

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


class Casal:
    """O casal falando com a API: cada um com o seu token."""

    def __init__(self, client: TestClient, emissor: Emissor) -> None:
        self.client, self.emissor = client, emissor

    def pedir(self, quem: str, metodo: str, caminho: str, **corpo):
        return self.client.request(metodo, caminho, headers=self.emissor.cabecalho(quem), **corpo)

    def conta(self, nome="Conta corrente", tipo="corrente") -> str:
        resposta = self.pedir("flavio", "POST", "/api/contas", json={"nome": nome, "tipo": tipo})
        assert resposta.status_code == 201
        return resposta.json()["id"]

    def categoria(self, nome="Alimentação", tipo="despesa") -> str:
        resposta = self.pedir(
            "flavio", "POST", "/api/categorias", json={"nome": nome, "tipo": tipo}
        )
        assert resposta.status_code == 201
        return resposta.json()["id"]


@pytest.fixture
def casal(client: TestClient, emissor: Emissor) -> Casal:
    return Casal(client, emissor)
