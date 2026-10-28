import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from app.main import create_app
from tests.conftest import Emissor


def test_a_api_tira_o_usuario_do_token(client: TestClient, emissor: Emissor):
    flavio = client.get("/api/eu", headers=emissor.cabecalho("flavio"))
    esposa = client.get("/api/eu", headers=emissor.cabecalho("esposa"))

    assert flavio.status_code == 200
    assert flavio.json() == {"usuario": "flavio"}
    assert esposa.json() == {"usuario": "esposa"}


def test_token_de_outro_cliente_e_recusado(client: TestClient, emissor: Emissor):
    resposta = client.get("/api/eu", headers=emissor.cabecalho("flavio", client_id="outro"))

    assert resposta.status_code == 401


def test_token_padrao_com_aud_e_aceito(client: TestClient, emissor: Emissor):
    cabecalho = emissor.cabecalho("esposa", client_id=None, aud=emissor.audiencia)

    resposta = client.get("/api/eu", headers=cabecalho)

    assert resposta.json() == {"usuario": "esposa"}


def _token_sem_assinatura(emissor: Emissor) -> str:
    agora = int(time.time())
    claims = {"sub": "flavio", "iss": emissor.emissor, "client_id": emissor.audiencia}
    return jwt.encode(claims | {"exp": agora + 900}, None, algorithm="none")


@pytest.mark.parametrize(
    "cabecalho",
    [
        pytest.param(lambda e: {}, id="sem token"),
        pytest.param(lambda e: {"Authorization": "Bearer lixo"}, id="token malformado"),
        pytest.param(lambda e: e.cabecalho("flavio", exp=int(time.time()) - 60), id="vencido"),
        pytest.param(lambda e: e.cabecalho("flavio", iss="https://outro"), id="outro emissor"),
        pytest.param(
            lambda e: e.cabecalho(
                "flavio", chave=rsa.generate_private_key(public_exponent=65537, key_size=2048)
            ),
            id="assinado por outra chave",
        ),
        pytest.param(
            lambda e: {"Authorization": f"Bearer {_token_sem_assinatura(e)}"},
            id="sem assinatura",
        ),
    ],
)
def test_sem_token_valido_a_api_recusa(client: TestClient, emissor: Emissor, cabecalho):
    resposta = client.get("/api/eu", headers=cabecalho(emissor))

    assert resposta.status_code == 401
    assert resposta.headers["www-authenticate"] == "Bearer"


def test_sem_emissor_configurado_ninguem_entra(database_url: str, emissor: Emissor, monkeypatch):
    monkeypatch.delenv("JWT_EMISSOR", raising=False)
    monkeypatch.delenv("JWT_AUDIENCIA", raising=False)
    client = TestClient(create_app(database_url))

    resposta = client.get("/api/eu", headers=emissor.cabecalho("flavio"))

    assert resposta.status_code == 503


def test_com_emissor_configurado_as_chaves_vem_do_jwks_dele(
    database_url: str, emissor: Emissor, monkeypatch
):
    jwks = json.dumps(emissor.jwks()).encode()

    class Jwks(BaseHTTPRequestHandler):
        def do_GET(self):
            assert self.path == "/pool/.well-known/jwks.json"
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(jwks)

        def log_message(self, *args):
            pass

    servidor = ThreadingHTTPServer(("127.0.0.1", 0), Jwks)
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    endereco = f"http://127.0.0.1:{servidor.server_port}/pool"
    monkeypatch.setenv("JWT_EMISSOR", endereco)
    monkeypatch.setenv("JWT_AUDIENCIA", emissor.audiencia)
    try:
        client = TestClient(create_app(database_url))
        resposta = client.get("/api/eu", headers=emissor.cabecalho("esposa", iss=endereco))
    finally:
        servidor.shutdown()

    assert resposta.json() == {"usuario": "esposa"}


def test_sem_as_chaves_do_emissor_a_api_diz_que_esta_fora(
    database_url: str, emissor: Emissor, monkeypatch
):
    monkeypatch.setenv("JWT_EMISSOR", "http://127.0.0.1:1/pool")
    monkeypatch.setenv("JWT_AUDIENCIA", emissor.audiencia)
    client = TestClient(create_app(database_url))

    cabecalho = emissor.cabecalho("flavio", iss="http://127.0.0.1:1/pool")
    resposta = client.get("/api/eu", headers=cabecalho)

    assert resposta.status_code == 503
