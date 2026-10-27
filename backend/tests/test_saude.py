import psycopg
from fastapi.testclient import TestClient

from app.main import create_app
from app.migrations import aplicar_migrations


def test_saude_responde_ok_com_o_banco_migrado(client: TestClient):
    resposta = client.get("/api/saude")

    assert resposta.status_code == 200
    assert resposta.json() == {"status": "ok", "migrations": 1}


def test_saude_diz_que_o_banco_esta_fora_quando_nao_conecta():
    client = TestClient(create_app("postgresql://postgres@localhost:1/nada?connect_timeout=1"))

    resposta = client.get("/api/saude")

    assert resposta.status_code == 503


def test_migrations_reaplicadas_nao_repetem(database_url: str):
    aplicar_migrations(database_url)
    aplicar_migrations(database_url)

    with psycopg.connect(database_url) as conn:
        total = conn.execute("SELECT count(*) FROM controle_de_migrations").fetchone()[0]
    assert total == 1
