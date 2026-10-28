from uuid import uuid4

import pytest
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


@pytest.fixture
def casal(client: TestClient, emissor: Emissor) -> Casal:
    return Casal(client, emissor)


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


def test_cria_um_lancamento_e_o_ve_na_lista(casal: Casal):
    conta, alimentacao = casal.conta(), casal.categoria()
    novo = lancamento(conta, [alimentacao])

    criado = casal.pedir("flavio", "POST", "/api/lancamentos", json=novo)
    lista = casal.pedir("esposa", "GET", "/api/lancamentos")

    assert criado.status_code == 201
    assert lista.status_code == 200
    [visto] = lista.json()
    assert visto | {"criado_em": None, "alterado_em": None} == novo | {
        "situacao": "realizado",
        "criado_por": "flavio",
        "alterado_por": "flavio",
        "criado_em": None,
        "alterado_em": None,
    }


def test_edita_um_lancamento_e_registra_quem_alterou(casal: Casal):
    conta, alimentacao, viagem = casal.conta(), casal.categoria(), casal.categoria("Viagem")
    novo = lancamento(conta, [alimentacao])
    casal.pedir("flavio", "POST", "/api/lancamentos", json=novo)
    editado = novo | {
        "valor_centavos": 23000,
        "descricao": "Jantar em Ilhabela",
        "categoria_ids": [alimentacao, viagem],
    }

    resposta = casal.pedir("esposa", "PUT", f"/api/lancamentos/{novo['id']}", json=editado)

    assert resposta.status_code == 200
    [visto] = casal.pedir("flavio", "GET", "/api/lancamentos").json()
    assert visto["valor_centavos"] == 23000
    assert visto["descricao"] == "Jantar em Ilhabela"
    assert sorted(visto["categoria_ids"]) == sorted([alimentacao, viagem])
    assert (visto["criado_por"], visto["alterado_por"]) == ("flavio", "esposa")


def test_editar_um_lancamento_que_nao_existe_e_404(casal: Casal):
    conta, alimentacao = casal.conta(), casal.categoria()
    novo = lancamento(conta, [alimentacao])

    resposta = casal.pedir("flavio", "PUT", f"/api/lancamentos/{novo['id']}", json=novo)

    assert resposta.status_code == 404


def test_exclui_um_lancamento_com_as_categorias_dele(casal: Casal, database_url: str):
    conta, alimentacao = casal.conta(), casal.categoria()
    novo = lancamento(conta, [alimentacao])
    casal.pedir("flavio", "POST", "/api/lancamentos", json=novo)

    resposta = casal.pedir("esposa", "DELETE", f"/api/lancamentos/{novo['id']}")

    assert resposta.status_code == 204
    assert casal.pedir("flavio", "GET", "/api/lancamentos").json() == []
    # Excluir de novo (a fila reenviou, a outra pessoa já excluiu) não é erro.
    assert casal.pedir("flavio", "DELETE", f"/api/lancamentos/{novo['id']}").status_code == 204


def test_reenviar_o_mesmo_lancamento_nao_duplica(casal: Casal):
    conta, alimentacao = casal.conta(), casal.categoria()
    novo = lancamento(conta, [alimentacao])

    primeira = casal.pedir("flavio", "POST", "/api/lancamentos", json=novo)
    segunda = casal.pedir("flavio", "POST", "/api/lancamentos", json=novo)

    assert (primeira.status_code, segunda.status_code) == (201, 200)
    assert segunda.json() == primeira.json()
    assert len(casal.pedir("flavio", "GET", "/api/lancamentos").json()) == 1


def test_a_lista_vem_da_data_mais_recente_para_a_mais_antiga(casal: Casal):
    conta, alimentacao = casal.conta(), casal.categoria()
    for dia in ["2026-10-01", "2026-10-03", "2026-10-02"]:
        casal.pedir(
            "flavio", "POST", "/api/lancamentos", json=lancamento(conta, [alimentacao], data=dia)
        )

    datas = [l["data"] for l in casal.pedir("flavio", "GET", "/api/lancamentos").json()]

    assert datas == ["2026-10-03", "2026-10-02", "2026-10-01"]


def test_data_futura_nasce_prevista_e_a_situacao_pode_ser_trocada(casal: Casal):
    conta, alimentacao = casal.conta(), casal.categoria()
    futuro = lancamento(conta, [alimentacao], data="2999-01-01")
    futuro_realizado = lancamento(conta, [alimentacao], data="2999-01-01", situacao="realizado")
    passado_previsto = lancamento(conta, [alimentacao], data="2020-01-01", situacao="previsto")

    situacoes = [
        casal.pedir("flavio", "POST", "/api/lancamentos", json=corpo).json()["situacao"]
        for corpo in (futuro, futuro_realizado, passado_previsto)
    ]

    assert situacoes == ["previsto", "realizado", "previsto"]


@pytest.mark.parametrize(
    "estrago",
    [
        pytest.param(lambda c, a: {"valor_centavos": 0}, id="valor zero"),
        pytest.param(lambda c, a: {"valor_centavos": -5}, id="valor negativo"),
        pytest.param(lambda c, a: {"categoria_ids": []}, id="sem categoria"),
        pytest.param(lambda c, a: {"categoria_ids": [str(uuid4())]}, id="categoria que não existe"),
        pytest.param(lambda c, a: {"conta_id": str(uuid4())}, id="conta que não existe"),
        pytest.param(lambda c, a: {"tipo": "receita"}, id="categoria de despesa numa receita"),
        pytest.param(lambda c, a: {"categoria_ids": [a, a]}, id="categoria repetida"),
    ],
)
def test_lancamento_invalido_e_recusado_e_nada_e_gravado(casal: Casal, estrago):
    conta, alimentacao = casal.conta(), casal.categoria()
    invalido = lancamento(conta, [alimentacao]) | estrago(conta, alimentacao)

    resposta = casal.pedir("flavio", "POST", "/api/lancamentos", json=invalido)

    assert resposta.status_code == 422
    assert casal.pedir("flavio", "GET", "/api/lancamentos").json() == []


def test_editar_para_um_lancamento_invalido_mantem_o_que_estava(casal: Casal):
    conta, alimentacao = casal.conta(), casal.categoria()
    novo = lancamento(conta, [alimentacao])
    casal.pedir("flavio", "POST", "/api/lancamentos", json=novo)

    resposta = casal.pedir(
        "flavio", "PUT", f"/api/lancamentos/{novo['id']}", json=novo | {"categoria_ids": []}
    )

    assert resposta.status_code == 422
    [visto] = casal.pedir("flavio", "GET", "/api/lancamentos").json()
    assert visto["categoria_ids"] == [alimentacao]


def test_o_id_do_corpo_tem_de_ser_o_da_url(casal: Casal):
    conta, alimentacao = casal.conta(), casal.categoria()
    novo = lancamento(conta, [alimentacao])
    casal.pedir("flavio", "POST", "/api/lancamentos", json=novo)

    resposta = casal.pedir(
        "flavio", "PUT", f"/api/lancamentos/{novo['id']}", json=novo | {"id": str(uuid4())}
    )

    assert resposta.status_code == 422


@pytest.mark.parametrize(
    "metodo, caminho",
    [
        ("GET", "/api/contas"),
        ("POST", "/api/contas"),
        ("GET", "/api/categorias"),
        ("POST", "/api/categorias"),
        ("GET", "/api/lancamentos"),
        ("POST", "/api/lancamentos"),
        ("PUT", f"/api/lancamentos/{uuid4()}"),
        ("DELETE", f"/api/lancamentos/{uuid4()}"),
    ],
)
def test_sem_login_nada_de_lancamentos(client: TestClient, metodo: str, caminho: str):
    assert client.request(metodo, caminho).status_code == 401


def test_listas_de_contas_e_categorias(casal: Casal):
    casal.conta("Poupança", "poupanca")
    casal.categoria("Salário", "receita")

    contas = casal.pedir("esposa", "GET", "/api/contas").json()
    categorias = casal.pedir("esposa", "GET", "/api/categorias").json()

    assert [(c["nome"], c["tipo"]) for c in contas] == [("Poupança", "poupanca")]
    assert [(c["nome"], c["tipo"]) for c in categorias] == [("Salário", "receita")]
