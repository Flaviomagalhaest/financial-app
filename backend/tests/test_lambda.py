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
