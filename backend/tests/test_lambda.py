import json

import pytest

from app.migrations import PASTA, aplicar_migrations


def evento_da_http_api(metodo: str, caminho: str) -> dict:
    """Evento no formato 2.0 que a HTTP API manda à Lambda."""
    return {
        "version": "2.0",
        "routeKey": f"{metodo} {caminho}",
        "rawPath": caminho,
        "rawQueryString": "",
        "headers": {"host": "dxxxx.cloudfront.net", "accept": "application/json"},
        "requestContext": {
            "accountId": "123456789012",
            "apiId": "api",
            "domainName": "api.execute-api.sa-east-1.amazonaws.com",
            "domainPrefix": "api",
            "http": {
                "method": metodo,
                "path": caminho,
                "protocol": "HTTP/1.1",
                "sourceIp": "203.0.113.1",
                "userAgent": "teste",
            },
            "requestId": "id",
            "routeKey": f"{metodo} {caminho}",
            "stage": "$default",
            "time": "28/Oct/2026:00:00:00 +0000",
            "timeEpoch": 1793145600000,
        },
        "isBase64Encoded": False,
    }


def test_lambda_responde_a_saude_pela_http_api(database_url: str, monkeypatch: pytest.MonkeyPatch):
    aplicar_migrations(database_url)
    monkeypatch.setenv("DATABASE_URL", database_url)
    from app.lambda_handler import handler

    resposta = handler(evento_da_http_api("GET", "/api/saude"), None)

    assert resposta["statusCode"] == 200
    assert json.loads(resposta["body"]) == {
        "status": "ok",
        "migrations": len(list(PASTA.glob("*.sql"))),
    }


def handler_com_rotas_de_teste():
    from mangum import Mangum

    from app.main import create_app

    app = create_app()

    @app.get("/api/grande")
    def grande() -> list[dict]:
        return [{"descricao": "Mercado do bairro", "valor": 1234} for _ in range(2000)]

    @app.get("/api/pequena")
    def pequena() -> dict:
        return {"ok": True}

    return Mangum(app, lifespan="off")


def test_resposta_grande_sai_comprimida_em_base64_quando_o_cliente_aceita_gzip():
    import base64
    import gzip

    evento = evento_da_http_api("GET", "/api/grande")
    evento["headers"]["accept-encoding"] = "gzip, deflate"

    resposta = handler_com_rotas_de_teste()(evento, None)

    assert resposta["statusCode"] == 200
    assert resposta["headers"]["content-encoding"] == "gzip"
    assert resposta["isBase64Encoded"] is True
    lista = json.loads(gzip.decompress(base64.b64decode(resposta["body"])))
    assert len(lista) == 2000


def test_resposta_grande_sai_como_hoje_sem_accept_encoding():
    resposta = handler_com_rotas_de_teste()(evento_da_http_api("GET", "/api/grande"), None)

    assert "content-encoding" not in resposta["headers"]
    assert resposta["isBase64Encoded"] is False
    assert len(json.loads(resposta["body"])) == 2000


def test_resposta_pequena_nao_e_comprimida():
    evento = evento_da_http_api("GET", "/api/pequena")
    evento["headers"]["accept-encoding"] = "gzip"

    resposta = handler_com_rotas_de_teste()(evento, None)

    assert resposta["statusCode"] == 200
    assert "content-encoding" not in resposta["headers"]
