from uuid import uuid4

from fastapi.testclient import TestClient

from tests.emissor import Emissor


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


def lancamento(conta: str, categorias: list[str], **campos) -> dict:
    return {
        "id": str(uuid4()),
        "tipo": "despesa",
        "valor_centavos": 12035,
        "data": "2026-10-02",
        "descricao": "Mercado",
        "conta_id": conta,
        "categoria_ids": categorias,
    } | campos
