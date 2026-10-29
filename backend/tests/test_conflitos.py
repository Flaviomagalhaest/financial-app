"""Os dois mexem no mesmo lançamento (ADR 0011): campos diferentes ficam os dois, o mesmo campo
vira conflito, e a exclusão vence a edição."""

from uuid import uuid4

from tests.conftest import Casal
from tests.test_lancamentos import lancamento


def criar(casal: Casal, quem: str = "flavio", **campos) -> dict:
    novo = lancamento(casal.conta(), [casal.categoria()], **campos)
    resposta = casal.pedir(quem, "POST", "/api/lancamentos", json=novo)
    assert resposta.status_code == 201
    return resposta.json()


def editar(casal: Casal, quem: str, id: str, versao: int, **campos):
    return casal.pedir(quem, "PATCH", f"/api/lancamentos/{id}", json={"versao": versao, **campos})


def test_o_lancamento_nasce_na_versao_1_e_cada_mudanca_sobe_a_versao(casal: Casal):
    criado = criar(casal)

    editado = editar(casal, "esposa", criado["id"], 1, valor_centavos=500)

    assert criado["versao"] == 1
    assert editado.status_code == 200
    assert (editado.json()["versao"], editado.json()["valor_centavos"]) == (2, 500)


def test_mudancas_em_campos_diferentes_ficam_as_duas(casal: Casal):
    criado = criar(casal)

    editar(casal, "flavio", criado["id"], 1, valor_centavos=32000)
    resposta = editar(casal, "esposa", criado["id"], 1, descricao="Mercado do mês")

    assert resposta.status_code == 200
    visto = resposta.json()
    assert (visto["valor_centavos"], visto["descricao"]) == (32000, "Mercado do mês")
    assert (visto["versao"], visto["alterado_por"]) == (3, "esposa")


def test_mudanca_identica_a_do_outro_lado_nao_e_conflito(casal: Casal):
    criado = criar(casal)
    editar(casal, "esposa", criado["id"], 1, valor_centavos=230, tags=["Viagem"])

    resposta = editar(casal, "flavio", criado["id"], 1, valor_centavos=230, tags=["viagem"])

    assert resposta.status_code == 200
    assert resposta.json()["versao"] == 2


def test_mudar_o_campo_que_o_outro_lado_mudou_depois_e_conflito_e_nada_se_grava(casal: Casal):
    criado = criar(casal)
    editar(casal, "esposa", criado["id"], 1, valor_centavos=23000)

    resposta = editar(
        casal, "flavio", criado["id"], 1, valor_centavos=32000, descricao="Mercado do mês"
    )

    assert resposta.status_code == 409
    conflito = resposta.json()
    [campo] = conflito["campos"]
    assert campo | {"alterado_em": None} == {
        "campo": "valor_centavos",
        "alterado_por": "esposa",
        "alterado_em": None,
        "por_voce": False,
        "origem": None,
    }
    assert conflito["lancamento"]["valor_centavos"] == 23000
    [visto] = casal.pedir("flavio", "GET", "/api/lancamentos").json()
    assert (visto["valor_centavos"], visto["descricao"], visto["versao"]) == (23000, "Mercado", 2)


def test_quem_decide_o_conflito_reenvia_sobre_a_versao_do_servidor(casal: Casal):
    criado = criar(casal)
    editar(casal, "esposa", criado["id"], 1, valor_centavos=23000)
    conflito = editar(casal, "flavio", criado["id"], 1, valor_centavos=32000).json()

    resposta = editar(
        casal, "flavio", criado["id"], conflito["lancamento"]["versao"], valor_centavos=32000
    )

    assert resposta.status_code == 200
    assert resposta.json()["valor_centavos"] == 32000


def test_a_mesma_pessoa_de_outro_aparelho_aparece_como_voce(casal: Casal):
    criado = criar(casal)
    editar(casal, "flavio", criado["id"], 1, descricao="No celular")

    resposta = editar(casal, "flavio", criado["id"], 1, descricao="No computador")

    assert resposta.status_code == 409
    assert resposta.json()["campos"][0]["por_voce"] is True


def test_mudar_a_data_nao_desfaz_a_confirmacao_que_o_outro_lado_fez_depois(casal: Casal):
    criado = criar(casal, data="2099-01-10")
    assert criado["situacao"] == "previsto"
    confirmar = casal.pedir("esposa", "POST", f"/api/lancamentos/{criado['id']}/confirmar", json={})
    assert confirmar.json()["situacao"] == "realizado"

    resposta = editar(casal, "flavio", criado["id"], 1, data="2099-01-12")

    assert resposta.status_code == 200
    assert (resposta.json()["data"], resposta.json()["situacao"]) == ("2099-01-12", "realizado")


def test_sem_mudanca_do_outro_lado_mudar_a_data_ainda_refaz_a_situacao(casal: Casal):
    criado = criar(casal)

    resposta = editar(casal, "flavio", criado["id"], 1, data="2099-01-12")

    assert resposta.json()["situacao"] == "previsto"


def test_a_exclusao_vence_a_edicao_e_diz_quem_excluiu(casal: Casal):
    criado = criar(casal)
    assert casal.pedir("esposa", "DELETE", f"/api/lancamentos/{criado['id']}").status_code == 204

    resposta = editar(casal, "flavio", criado["id"], 1, valor_centavos=500)

    assert resposta.status_code == 410
    exclusao = resposta.json()
    assert (exclusao["excluido_por"], exclusao["por_voce"]) == ("esposa", False)
    assert casal.pedir("flavio", "GET", "/api/lancamentos").json() == []


def test_editar_o_que_nunca_existiu_continua_404(casal: Casal):
    resposta = editar(casal, "flavio", str(uuid4()), 1, valor_centavos=500)

    assert resposta.status_code == 404


def test_reenviar_o_criar_de_algo_ja_excluido_nao_o_ressuscita(casal: Casal):
    novo = lancamento(casal.conta(), [casal.categoria()])
    casal.pedir("flavio", "POST", "/api/lancamentos", json=novo)
    casal.pedir("esposa", "DELETE", f"/api/lancamentos/{novo['id']}")

    resposta = casal.pedir("flavio", "POST", "/api/lancamentos", json=novo)

    assert resposta.status_code == 410
    assert casal.pedir("flavio", "GET", "/api/lancamentos").json() == []


def test_o_excluido_sai_do_saldo_da_conta(casal: Casal):
    conta = casal.conta()
    novo = lancamento(conta, [casal.categoria()], valor_centavos=1000)
    casal.pedir("flavio", "POST", "/api/lancamentos", json=novo)

    casal.pedir("esposa", "DELETE", f"/api/lancamentos/{novo['id']}")

    [vista] = casal.pedir("flavio", "GET", "/api/contas").json()
    assert vista["saldo_centavos"] == 0


def test_excluir_o_que_o_outro_lado_mudou_depois_pergunta_antes(casal: Casal):
    criado = criar(casal)
    editar(casal, "esposa", criado["id"], 1, valor_centavos=230)

    resposta = casal.pedir("flavio", "DELETE", f"/api/lancamentos/{criado['id']}?versao=1")

    assert resposta.status_code == 409
    conflito = resposta.json()
    assert [(c["campo"], c["alterado_por"]) for c in conflito["campos"]] == [
        ("valor_centavos", "esposa")
    ]
    assert len(casal.pedir("flavio", "GET", "/api/lancamentos").json()) == 1


def test_excluir_mesmo_assim_e_sobre_a_versao_do_servidor(casal: Casal):
    criado = criar(casal)
    editar(casal, "esposa", criado["id"], 1, valor_centavos=230)

    resposta = casal.pedir("flavio", "DELETE", f"/api/lancamentos/{criado['id']}?versao=2")

    assert resposta.status_code == 204
    assert casal.pedir("flavio", "GET", "/api/lancamentos").json() == []


def test_confirmar_com_outros_valores_o_que_ja_foi_confirmado_e_conflito_com_quem_confirmou(
    casal: Casal,
):
    criado = criar(casal, data="2099-01-10")
    casal.pedir("esposa", "POST", f"/api/lancamentos/{criado['id']}/confirmar", json={})

    resposta = casal.pedir(
        "flavio",
        "POST",
        f"/api/lancamentos/{criado['id']}/confirmar",
        json={"valor_centavos": 999, "data": "2099-01-10"},
    )

    assert resposta.status_code == 409
    conflito = resposta.json()
    assert conflito["motivo"] == "já confirmado com outros valores"
    assert [(c["campo"], c["alterado_por"]) for c in conflito["campos"]] == [
        ("valor_centavos", "esposa")
    ]
    assert conflito["lancamento"]["valor_centavos"] == criado["valor_centavos"]


def test_no_lote_cada_regra_vira_o_seu_resultado(casal: Casal):
    mesclado, em_conflito, excluido = criar(casal), criar(casal), criar(casal)
    editar(casal, "esposa", mesclado["id"], 1, descricao="Dela")
    editar(casal, "esposa", em_conflito["id"], 1, valor_centavos=230)
    casal.pedir("esposa", "DELETE", f"/api/lancamentos/{excluido['id']}")

    def edicao(criado: dict, **campos) -> dict:
        return {"acao": "editar", "id": criado["id"], "alteracao": {"versao": 1, **campos}}

    resposta = casal.pedir(
        "flavio",
        "POST",
        "/api/lancamentos/lote",
        json={
            "acoes": [
                edicao(mesclado, valor_centavos=320),
                edicao(em_conflito, valor_centavos=320),
                edicao(excluido, valor_centavos=320),
                {"acao": "excluir", "id": em_conflito["id"], "versao": 1},
            ]
        },
    )

    aceita, conflito, descartada, exclusao = resposta.json()["resultados"]
    assert aceita["resultado"] == "aceita"
    assert (aceita["lancamento"]["valor_centavos"], aceita["lancamento"]["descricao"]) == (
        320,
        "Dela",
    )
    assert conflito["resultado"] == "conflito"
    assert conflito["lancamento"]["valor_centavos"] == 230
    assert [c["campo"] for c in conflito["campos"]] == ["valor_centavos"]
    assert descartada["resultado"] == "descartada"
    assert descartada["exclusao"]["excluido_por"] == "esposa"
    assert exclusao["resultado"] == "conflito"


def test_confirmar_ajustando_so_a_data_nao_desfaz_o_valor_que_o_outro_lado_mudou(casal: Casal):
    criado = criar(casal, data="2099-01-10", valor_centavos=10000)
    editar(casal, "esposa", criado["id"], 1, valor_centavos=12000)

    resposta = casal.pedir(
        "flavio",
        "POST",
        f"/api/lancamentos/{criado['id']}/confirmar",
        json={"versao": 1, "data": "2099-01-11"},
    )

    assert resposta.status_code == 200
    confirmado = resposta.json()
    assert (confirmado["situacao"], confirmado["data"]) == ("realizado", "2099-01-11")
    assert confirmado["valor_centavos"] == 12000


def test_confirmar_ajustando_o_valor_que_o_outro_lado_mudou_depois_e_conflito(casal: Casal):
    criado = criar(casal, data="2099-01-10", valor_centavos=10000)
    editar(casal, "esposa", criado["id"], 1, valor_centavos=12000)

    resposta = casal.pedir(
        "flavio",
        "POST",
        f"/api/lancamentos/{criado['id']}/confirmar",
        json={"versao": 1, "valor_centavos": 9000},
    )

    assert resposta.status_code == 409
    assert [c["campo"] for c in resposta.json()["campos"]] == ["valor_centavos"]
    [visto] = casal.pedir("flavio", "GET", "/api/lancamentos").json()
    assert (visto["situacao"], visto["valor_centavos"]) == ("previsto", 12000)
