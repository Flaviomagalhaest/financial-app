"""Pessoa do lançamento (o Flávio, a esposa ou o conjunto), autoria e "Parece repetido"."""

from tests.conftest import Casal
from tests.test_conflitos import criar, editar
from tests.test_lancamentos import lancamento


def test_lista_as_pessoas_do_casal_com_a_que_esta_logada(casal: Casal):
    resposta = casal.pedir("esposa", "GET", "/api/pessoas")

    assert resposta.status_code == 200
    assert resposta.json() == [
        {"id": "flavio", "nome": "Flávio", "eu": False},
        {"id": "esposa", "nome": "Fulana", "eu": True},
    ]


def test_o_lancamento_sem_pessoa_e_do_conjunto(casal: Casal):
    assert criar(casal)["pessoa"] is None


def test_o_lancamento_guarda_a_pessoa_e_ela_se_edita(casal: Casal):
    criado = criar(casal, pessoa="flavio")

    editado = editar(casal, "esposa", criado["id"], 1, pessoa="esposa")
    do_conjunto = editar(casal, "esposa", criado["id"], 2, pessoa=None)

    assert criado["pessoa"] == "flavio"
    assert editado.json()["pessoa"] == "esposa"
    # Sem o campo, a pessoa fica; voltar ao conjunto é mandar `pessoa` vazia de propósito.
    assert do_conjunto.json()["pessoa"] == "esposa"
    voltou = casal.pedir(
        "esposa",
        "PATCH",
        f"/api/lancamentos/{criado['id']}",
        json={"versao": 2, "pessoa": ""},
    )
    assert voltou.json()["pessoa"] is None


def test_pessoa_desconhecida_e_recusada(casal: Casal):
    novo = lancamento(casal.conta(), [casal.categoria()], pessoa="outro")

    resposta = casal.pedir("flavio", "POST", "/api/lancamentos", json=novo)

    assert resposta.status_code == 422


def test_mudar_a_pessoa_que_o_outro_lado_mudou_depois_e_conflito(casal: Casal):
    criado = criar(casal)
    editar(casal, "esposa", criado["id"], 1, pessoa="esposa")

    resposta = editar(casal, "flavio", criado["id"], 1, pessoa="flavio")

    assert resposta.status_code == 409
    assert [c["campo"] for c in resposta.json()["campos"]] == ["pessoa"]


# A hora que vale é a da ação no aparelho, não a da chegada ao servidor (ADR 0011).
ONTEM_14H32 = "2026-10-12T17:32:00Z"


def test_criar_grava_a_hora_da_acao_no_aparelho(casal: Casal):
    criado = criar(casal, acao_em=ONTEM_14H32)

    assert criado["criado_em"] == criado["alterado_em"] == "2026-10-12T17:32:00Z"
    assert "acao_em" not in criado
    assert criado["fonte"] == "app"


def test_editar_grava_a_hora_da_acao_e_o_conflito_a_devolve(casal: Casal):
    criado = criar(casal)

    editado = editar(casal, "esposa", criado["id"], 1, valor_centavos=23000, acao_em=ONTEM_14H32)
    conflito = editar(casal, "flavio", criado["id"], 1, valor_centavos=32000)

    assert editado.json()["alterado_em"] == "2026-10-12T17:32:00Z"
    assert conflito.status_code == 409
    assert conflito.json()["campos"][0]["alterado_em"] == "2026-10-12T17:32:00Z"


def test_a_hora_do_aparelho_no_futuro_vale_a_do_servidor(casal: Casal):
    criado = criar(casal, acao_em="2999-01-01T00:00:00Z")

    assert criado["criado_em"] < "2100"


def test_excluir_grava_a_hora_da_acao(casal: Casal):
    criado = criar(casal)
    casal.pedir(
        "esposa", "DELETE", f"/api/lancamentos/{criado['id']}", params={"acao_em": ONTEM_14H32}
    )

    resposta = editar(casal, "flavio", criado["id"], 1, valor_centavos=1)

    assert resposta.status_code == 410
    assert resposta.json()["excluido_em"] == "2026-10-12T17:32:00Z"


def test_a_hora_da_acao_vale_no_lote_e_na_confirmacao(casal: Casal):
    criado = criar(casal, situacao="previsto", data="2026-12-01")

    confirmado = casal.pedir(
        "esposa",
        "POST",
        f"/api/lancamentos/{criado['id']}/confirmar",
        json={"acao_em": ONTEM_14H32},
    )
    novo = lancamento(casal.conta(), [casal.categoria()], acao_em=ONTEM_14H32)
    lote = casal.pedir(
        "esposa",
        "POST",
        "/api/lancamentos/lote",
        json={"acoes": [{"acao": "criar", "lancamento": novo}]},
    )

    assert confirmado.json()["alterado_em"] == "2026-10-12T17:32:00Z"
    assert lote.json()["resultados"][0]["lancamento"]["criado_em"] == "2026-10-12T17:32:00Z"


def lancar_dos_dois(casal: Casal, **da_esposa) -> tuple[dict, dict]:
    """O Flávio lança o mercado; depois a esposa lança o mesmo, com o que `da_esposa` mudar."""
    conta, categoria = casal.conta(), casal.categoria()
    do_flavio = lancamento(conta, [categoria], data="2026-10-02")
    da_outra = lancamento(conta, [categoria], data="2026-10-02") | da_esposa
    assert casal.pedir("flavio", "POST", "/api/lancamentos", json=do_flavio).status_code == 201
    assert casal.pedir("esposa", "POST", "/api/lancamentos", json=da_outra).status_code == 201
    vistos = {l["id"]: l for l in casal.pedir("flavio", "GET", "/api/lancamentos").json()}
    return vistos[do_flavio["id"]], vistos[da_outra["id"]]


def test_parece_repetido_quando_chega_o_da_outra_pessoa_com_mesmo_valor_e_conta(casal: Casal):
    do_flavio, da_esposa = lancar_dos_dois(casal, data="2026-10-03")

    assert da_esposa["parece_repetido_de"] == do_flavio["id"]
    assert do_flavio["parece_repetido_de"] is None


def test_nao_parece_repetido_com_valor_conta_data_ou_pessoa_diferentes(casal: Casal):
    outra_conta = casal.conta("Poupança", "poupanca")
    categoria = casal.categoria("Mercado")
    for diferente in (
        {"valor_centavos": 12036},
        {"data": "2026-10-04"},
        {"conta_id": outra_conta},
    ):
        _, da_esposa = lancar_dos_dois(casal, **diferente | {"categoria_ids": [categoria]})
        assert da_esposa["parece_repetido_de"] is None, diferente


def test_o_mesmo_lancamento_da_mesma_pessoa_nao_parece_repetido(casal: Casal):
    conta, categoria = casal.conta(), casal.categoria()
    for _ in range(2):
        novo = lancamento(conta, [categoria])
        casal.pedir("flavio", "POST", "/api/lancamentos", json=novo)

    assert all(
        l["parece_repetido_de"] is None
        for l in casal.pedir("flavio", "GET", "/api/lancamentos").json()
    )


def test_manter_os_dois_tira_o_aviso(casal: Casal):
    _, da_esposa = lancar_dos_dois(casal)

    mantido = casal.pedir("flavio", "POST", f"/api/lancamentos/{da_esposa['id']}/manter-os-dois")

    assert mantido.status_code == 200
    assert mantido.json()["parece_repetido_de"] is None
    [primeiro, segundo] = casal.pedir("flavio", "GET", "/api/lancamentos").json()
    assert primeiro["parece_repetido_de"] is None and segundo["parece_repetido_de"] is None


def test_excluir_um_dos_dois_tira_o_aviso_do_outro(casal: Casal):
    do_flavio, da_esposa = lancar_dos_dois(casal)

    casal.pedir("flavio", "DELETE", f"/api/lancamentos/{do_flavio['id']}")

    [restante] = casal.pedir("flavio", "GET", "/api/lancamentos").json()
    assert restante["id"] == da_esposa["id"] and restante["parece_repetido_de"] is None
