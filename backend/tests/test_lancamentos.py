from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.banco import TENTATIVAS_NA_SERIALIZACAO
from tests.conftest import Casal


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
        "atrasado": False,
        "versao": 1,
        "tags": [],
        "recorrencia_id": None,
        "ocorrencia": None,
        "automatico": False,
        "estorno_de": None,
        "estorno_avulso": False,
        "parcelamento_id": None,
        "parcela": None,
        "parcelas": None,
        "alterada_a_mao": False,
        "item_categoria_id": None,
        "partes": [],
        # Lançamento de conta conta no mês da data e não tem fatura (ADR 0003).
        "mes": "2026-10-01",
        "fatura_mes": None,
        "criado_por": "flavio",
        "alterado_por": "flavio",
        "criado_em": None,
        "alterado_em": None,
        "pessoa": None,
        "fonte": "app",
        "parece_repetido_de": None,
    }


def test_edita_um_lancamento_e_registra_quem_alterou(casal: Casal):
    conta, alimentacao, viagem = casal.conta(), casal.categoria(), casal.categoria("Viagem")
    novo = lancamento(conta, [alimentacao])
    casal.pedir("flavio", "POST", "/api/lancamentos", json=novo)
    editado = {
        "versao": 1,
        "valor_centavos": 23000,
        "descricao": "Jantar em Ilhabela",
        "categoria_ids": [alimentacao, viagem],
    }

    resposta = casal.pedir("esposa", "PATCH", f"/api/lancamentos/{novo['id']}", json=editado)

    assert resposta.status_code == 200
    [visto] = casal.pedir("flavio", "GET", "/api/lancamentos").json()
    assert visto["valor_centavos"] == 23000
    assert visto["descricao"] == "Jantar em Ilhabela"
    assert sorted(visto["categoria_ids"]) == sorted([alimentacao, viagem])
    assert (visto["criado_por"], visto["alterado_por"]) == ("flavio", "esposa")


def test_editar_um_lancamento_que_nao_existe_e_404(casal: Casal):
    conta, alimentacao = casal.conta(), casal.categoria()
    novo = lancamento(conta, [alimentacao])

    resposta = casal.pedir(
        "flavio", "PATCH", f"/api/lancamentos/{novo['id']}", json={"versao": 1, "descricao": "x"}
    )

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
        "flavio", "PATCH", f"/api/lancamentos/{novo['id']}", json={"versao": 1, "categoria_ids": []}
    )

    assert resposta.status_code == 422
    [visto] = casal.pedir("flavio", "GET", "/api/lancamentos").json()
    assert visto["categoria_ids"] == [alimentacao]


@pytest.mark.parametrize(
    "metodo, caminho",
    [
        ("GET", "/api/contas"),
        ("POST", "/api/contas"),
        ("GET", "/api/categorias"),
        ("POST", "/api/categorias"),
        ("GET", "/api/lancamentos"),
        ("POST", "/api/lancamentos"),
        ("PATCH", f"/api/lancamentos/{uuid4()}"),
        ("DELETE", f"/api/lancamentos/{uuid4()}"),
        ("POST", "/api/lancamentos/lote"),
        ("POST", f"/api/lancamentos/{uuid4()}/confirmar"),
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


def test_editar_a_data_para_o_passado_realiza_o_que_era_futuro_mas_a_escolha_manual_fica(
    casal: Casal,
):
    conta, alimentacao = casal.conta(), casal.categoria()
    futuro = lancamento(conta, [alimentacao], data="2999-01-01")
    casal.pedir("flavio", "POST", "/api/lancamentos", json=futuro)

    passado = casal.pedir(
        "flavio",
        "PATCH",
        f"/api/lancamentos/{futuro['id']}",
        json={"versao": 1, "data": "2020-01-01"},
    )
    mesmo_dia = casal.pedir(
        "flavio",
        "PATCH",
        f"/api/lancamentos/{futuro['id']}",
        json={"versao": 2, "data": "2020-01-01", "valor_centavos": 5, "situacao": "previsto"},
    )
    sem_mexer_na_data = casal.pedir(
        "flavio",
        "PATCH",
        f"/api/lancamentos/{futuro['id']}",
        json={"versao": 3, "data": "2020-01-01", "valor_centavos": 6},
    )

    assert passado.json()["situacao"] == "realizado"
    assert mesmo_dia.json()["situacao"] == "previsto"
    assert sem_mexer_na_data.json()["situacao"] == "previsto"


def test_renomeia_uma_categoria_e_o_lancamento_antigo_mostra_o_nome_novo(casal: Casal):
    conta, categoria = casal.conta(), casal.categoria("Alimentacao")
    casal.pedir("flavio", "POST", "/api/lancamentos", json=lancamento(conta, [categoria]))

    resposta = casal.pedir(
        "esposa", "PATCH", f"/api/categorias/{categoria}", json={"nome": "Alimentação"}
    )

    assert resposta.status_code == 200
    assert resposta.json() == {
        "id": categoria,
        "nome": "Alimentação",
        "tipo": "despesa",
        "arquivada": False,
    }
    [lida] = casal.pedir("flavio", "GET", "/api/categorias").json()
    assert lida["nome"] == "Alimentação"
    [visto] = casal.pedir("flavio", "GET", "/api/lancamentos").json()
    assert visto["categoria_ids"] == [categoria]


def test_categoria_arquivada_nao_aceita_lancamento_novo_mas_o_antigo_fica_e_desarquivar_volta(
    casal: Casal,
):
    conta, categoria = casal.conta(), casal.categoria()
    antigo = lancamento(conta, [categoria])
    casal.pedir("flavio", "POST", "/api/lancamentos", json=antigo)

    arquivada = casal.pedir(
        "flavio", "PATCH", f"/api/categorias/{categoria}", json={"arquivada": True}
    )
    novo = casal.pedir("flavio", "POST", "/api/lancamentos", json=lancamento(conta, [categoria]))
    [visto] = casal.pedir("flavio", "GET", "/api/lancamentos").json()
    [lida] = casal.pedir("flavio", "GET", "/api/categorias").json()
    casal.pedir("flavio", "PATCH", f"/api/categorias/{categoria}", json={"arquivada": False})
    depois = casal.pedir("flavio", "POST", "/api/lancamentos", json=lancamento(conta, [categoria]))

    assert arquivada.json()["arquivada"] is True
    assert novo.status_code == 422
    assert novo.json()["detail"] == "categoria arquivada"
    assert visto["id"] == antigo["id"]
    assert lida["arquivada"] is True and lida["nome"] == "Alimentação"
    assert depois.status_code == 201


def test_editar_lancamento_antigo_mantem_categoria_arquivada_mas_nao_troca_por_outra(
    casal: Casal,
):
    conta, velha, outra = casal.conta(), casal.categoria("Velha"), casal.categoria("Outra")
    ativa = casal.categoria("Ativa")
    antigo = lancamento(conta, [velha])
    casal.pedir("flavio", "POST", "/api/lancamentos", json=antigo)
    for id in (velha, outra):
        casal.pedir("flavio", "PATCH", f"/api/categorias/{id}", json={"arquivada": True})

    mantida = casal.pedir(
        "flavio",
        "PATCH",
        f"/api/lancamentos/{antigo['id']}",
        json={"versao": 1, "categoria_ids": [velha, ativa]},
    )
    trocada = casal.pedir(
        "flavio",
        "PATCH",
        f"/api/lancamentos/{antigo['id']}",
        json={"versao": 2, "categoria_ids": [outra]},
    )

    assert mantida.status_code == 200
    assert trocada.status_code == 422


@pytest.mark.parametrize("corpo", [{"nome": ""}, {"nome": "   "}])
def test_renomear_para_nome_vazio_e_recusado(casal: Casal, corpo):
    categoria = casal.categoria("Mercado")

    resposta = casal.pedir("flavio", "PATCH", f"/api/categorias/{categoria}", json=corpo)

    assert resposta.status_code == 422
    assert casal.pedir("flavio", "GET", "/api/categorias").json()[0]["nome"] == "Mercado"


def test_alterar_categoria_que_nao_existe_e_404_e_sem_login_e_401(casal: Casal, client: TestClient):
    caminho = f"/api/categorias/{uuid4()}"

    assert casal.pedir("flavio", "PATCH", caminho, json={"nome": "X"}).status_code == 404
    assert client.patch(caminho, json={"nome": "X"}).status_code == 401


def test_reenviar_lancamento_cuja_categoria_foi_arquivada_depois_devolve_o_gravado(casal: Casal):
    conta, categoria = casal.conta(), casal.categoria()
    novo = lancamento(conta, [categoria])
    casal.pedir("flavio", "POST", "/api/lancamentos", json=novo)
    casal.pedir("flavio", "PATCH", f"/api/categorias/{categoria}", json={"arquivada": True})

    de_novo = casal.pedir("flavio", "POST", "/api/lancamentos", json=novo)

    assert de_novo.status_code == 200


def test_nome_da_categoria_e_gravado_sem_espacos_nas_pontas(casal: Casal):
    categoria = casal.categoria()

    resposta = casal.pedir(
        "flavio", "PATCH", f"/api/categorias/{categoria}", json={"nome": "  Feira "}
    )

    assert resposta.json()["nome"] == "Feira"


def test_escrita_termina_bem_na_segunda_tentativa_do_erro_de_serializacao(
    casal: Casal, falhar_ao_confirmar
):
    conta = casal.conta()
    categoria = casal.categoria()
    falhar_ao_confirmar(1)

    novo = lancamento(conta, [categoria])
    resposta = casal.pedir("flavio", "POST", "/api/lancamentos", json=novo)

    assert resposta.status_code == 201
    assert resposta.json()["id"] == novo["id"]
    listados = casal.pedir("flavio", "GET", "/api/lancamentos").json()
    assert [l["id"] for l in listados] == [novo["id"]]


def test_escrita_desiste_com_erro_se_a_serializacao_nunca_passa(casal: Casal, falhar_ao_confirmar):
    conta = casal.conta()
    categoria = casal.categoria()
    abertas = falhar_ao_confirmar(100)

    resposta = casal.pedir(
        "flavio", "POST", "/api/lancamentos", json=lancamento(conta, [categoria])
    )

    assert resposta.status_code == 503
    assert abertas[0] == TENTATIVAS_NA_SERIALIZACAO


def lote(*acoes: dict) -> dict:
    return {"acoes": list(acoes)}


def test_o_lote_grava_na_ordem_e_reenviar_nao_duplica(casal: Casal):
    conta, alimentacao = casal.conta(), casal.categoria()
    novo = lancamento(conta, [alimentacao])
    acoes = lote(
        {"acao": "criar", "lancamento": novo},
        {"acao": "editar", "id": novo["id"], "alteracao": {"versao": 1, "valor_centavos": 999}},
    )

    primeira = casal.pedir("flavio", "POST", "/api/lancamentos/lote", json=acoes)
    segunda = casal.pedir("flavio", "POST", "/api/lancamentos/lote", json=acoes)

    assert primeira.status_code == segunda.status_code == 200
    resultados = primeira.json()["resultados"]
    assert [r["resultado"] for r in resultados] == ["aceita", "aceita"]
    assert resultados[1]["lancamento"]["valor_centavos"] == 999
    assert [r["resultado"] for r in segunda.json()["resultados"]] == ["aceita", "aceita"]
    [visto] = casal.pedir("esposa", "GET", "/api/lancamentos").json()
    assert (visto["id"], visto["valor_centavos"]) == (novo["id"], 999)


def test_no_lote_a_recusa_traz_o_motivo_e_nao_trava_as_seguintes(casal: Casal):
    conta, alimentacao = casal.conta(), casal.categoria()
    sem_conta = lancamento(str(uuid4()), [alimentacao])
    bom = lancamento(conta, [alimentacao])

    resposta = casal.pedir(
        "flavio",
        "POST",
        "/api/lancamentos/lote",
        json=lote({"acao": "criar", "lancamento": sem_conta}, {"acao": "criar", "lancamento": bom}),
    )

    recusada, aceita = resposta.json()["resultados"]
    assert (recusada["resultado"], recusada["motivo"]) == ("recusada", "conta não encontrada")
    assert aceita["resultado"] == "aceita"
    assert [l["id"] for l in casal.pedir("flavio", "GET", "/api/lancamentos").json()] == [bom["id"]]


def test_no_lote_editar_o_que_foi_excluido_e_descartado_e_excluir_de_novo_e_aceito(casal: Casal):
    conta, alimentacao = casal.conta(), casal.categoria()
    novo = lancamento(conta, [alimentacao])
    casal.pedir("flavio", "POST", "/api/lancamentos", json=novo)
    casal.pedir("esposa", "DELETE", f"/api/lancamentos/{novo['id']}")

    resposta = casal.pedir(
        "flavio",
        "POST",
        "/api/lancamentos/lote",
        json=lote(
            {"acao": "editar", "id": novo["id"], "alteracao": {"versao": 1, "valor_centavos": 5}},
            {"acao": "excluir", "id": novo["id"]},
        ),
    )

    editar, excluir = resposta.json()["resultados"]
    assert (editar["resultado"], editar["motivo"]) == ("descartada", "lançamento excluído")
    assert excluir["resultado"] == "aceita"
    assert casal.pedir("flavio", "GET", "/api/lancamentos").json() == []


def test_no_lote_um_erro_inesperado_numa_acao_vira_recusa_e_nao_trava_as_seguintes(casal: Casal):
    conta, alimentacao = casal.conta(), casal.categoria()
    # O Postgres não guarda o caractere NUL num texto: o banco erra nesta ação só.
    estranho = lancamento(conta, [alimentacao], descricao="a\x00b")
    bom = lancamento(conta, [alimentacao])

    resposta = casal.pedir(
        "flavio",
        "POST",
        "/api/lancamentos/lote",
        json=lote({"acao": "criar", "lancamento": estranho}, {"acao": "criar", "lancamento": bom}),
    )

    assert resposta.status_code == 200
    recusada, aceita = resposta.json()["resultados"]
    assert (recusada["resultado"], recusada["motivo"]) == ("recusada", "erro no servidor")
    assert aceita["resultado"] == "aceita"
    assert [l["id"] for l in casal.pedir("flavio", "GET", "/api/lancamentos").json()] == [bom["id"]]
