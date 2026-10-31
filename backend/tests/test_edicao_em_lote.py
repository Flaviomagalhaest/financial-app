"""A edição em lote de categorias e tags (ticket 61): prévia, aplicação tudo ou nada a partir da
busca, parcelamento inteiro e desfazer por 30 dias pulando o que mudou depois."""

from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

import psycopg
import pytest

from app import edicao_em_lote, lancamentos
from tests.conftest import Casal
from tests.test_busca import lancar, parcelar
from tests.test_cartoes import novo_cartao
from tests.test_estorno_e_ajuste import estornar
from tests.test_planejamento import item


@pytest.fixture(autouse=True)
def hoje_e_15_de_outubro(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(lancamentos, "hoje", lambda: date(2026, 10, 15))


def previa(casal: Casal, selecao: dict, quem="esposa", **mudancas) -> dict:
    resposta = casal.pedir(
        quem,
        "POST",
        "/api/edicoes-em-lote/previa",
        json={"selecao": selecao} | mudancas,
    )
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


def aplicar(casal: Casal, selecao: dict, quem="esposa", id=None, **mudancas):
    return casal.pedir(
        quem,
        "POST",
        "/api/edicoes-em-lote",
        json={"id": id or str(uuid4()), "selecao": selecao} | mudancas,
    )


def aplicada(casal: Casal, selecao: dict, quem="esposa", **mudancas) -> dict:
    resposta = aplicar(casal, selecao, quem, **mudancas)
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def desfazer(casal: Casal, lote: dict, quem="esposa"):
    return casal.pedir(quem, "POST", f"/api/edicoes-em-lote/{lote['id']}/desfazer")


def todos(casal: Casal) -> dict[str, dict]:
    return {l["id"]: l for l in casal.pedir("flavio", "GET", "/api/lancamentos").json()}


def classificacao(casal: Casal, *lancados: dict) -> list[tuple[set[str], set[str]]]:
    agora = todos(casal)
    return [(set(agora[l["id"]]["categoria_ids"]), set(agora[l["id"]]["tags"])) for l in lancados]


def marcados(*lancados: dict) -> dict:
    return {"lancamento_ids": [l["id"] for l in lancados]}


def test_acrescenta_categoria_aos_marcados_com_previa_e_versao_nova(casal: Casal):
    conta = casal.conta()
    mercado, casa = casal.categoria("Mercado"), casal.categoria("Casa")
    feira = lancar(casal, conta, [mercado], descricao="Feira", data="2026-10-03")
    padaria = lancar(casal, conta, [mercado], descricao="Padaria", data="2026-10-04")
    ja_tem = lancar(casal, conta, [mercado, casa], descricao="Atacadão", data="2026-10-05")
    mudanca = {"categorias": {"acao": "acrescentar", "categoria_ids": [casa]}}

    vista = previa(casal, marcados(feira, padaria, ja_tem), **mudanca)

    assert {k: vista[k] for k in ("compras", "lancamentos", "mudam", "ja_estao_como_pedido")} == {
        "compras": 3,
        "lancamentos": 3,
        "mudam": 2,
        "ja_estao_como_pedido": 1,
    }
    assert vista["recusa"] is None
    # A amostra traz os primeiros que mudam, na ordem da busca, antes e depois.
    assert [(a["lancamento"]["descricao"], set(a["categoria_ids"])) for a in vista["amostra"]] == [
        ("Padaria", {mercado, casa}),
        ("Feira", {mercado, casa}),
    ]
    assert vista["amostra"][0]["lancamento"]["categoria_ids"] == [mercado]
    # A prévia não grava nada.
    assert classificacao(casal, feira) == [({mercado}, set())]

    lote = aplicada(casal, marcados(feira, padaria, ja_tem), **mudanca)

    assert lote["lancamentos"] == 2
    assert lote["situacao"] == "aplicada"
    assert lote["resumo"] == "Categorias: acrescentar Casa"
    assert classificacao(casal, feira, padaria, ja_tem) == [({mercado, casa}, set())] * 3
    agora = todos(casal)
    assert (agora[feira["id"]]["versao"], agora[feira["id"]]["alterado_por"]) == (2, "esposa")
    assert agora[ja_tem["id"]]["versao"] == 1


def test_remove_troca_e_substitui_categorias_e_tags(casal: Casal):
    conta = casal.conta()
    mercado, feira, casa = (
        casal.categoria("Mercado"),
        casal.categoria("Feira"),
        casal.categoria("Casa"),
    )
    um = lancar(casal, conta, [mercado, casa], tags=["Rotina", "viagem"])
    dois = lancar(casal, conta, [casa], tags=["Viagem"])

    aplicada(
        casal,
        marcados(um, dois),
        categorias={"acao": "trocar", "categoria_ids": [mercado], "por": feira},
        tags={"acao": "remover", "tags": ["VIAGEM"]},
    )
    assert classificacao(casal, um, dois) == [({feira, casa}, {"Rotina"}), ({casa}, set())]

    aplicada(
        casal,
        marcados(um),
        categorias={"acao": "remover", "categoria_ids": [casa, mercado]},
        tags={"acao": "acrescentar", "tags": ["rotina", "Férias"]},
    )
    # A tag nova nasce e a existente vem pelo nome, sem repetir.
    assert classificacao(casal, um) == [({feira}, {"Rotina", "Férias"})]


def test_substituir_poe_so_as_pedidas_e_trocar_tag_mantem_o_nome_existente(casal: Casal):
    conta = casal.conta()
    mercado, casa, feira = (
        casal.categoria("Mercado"),
        casal.categoria("Casa"),
        casal.categoria("Feira"),
    )
    lancar(casal, casal.conta("Outra"), [casa], tags=["Viagem"])
    um = lancar(casal, conta, [mercado, casa], tags=["Rotina", "praia"])

    aplicada(
        casal,
        marcados(um),
        categorias={"acao": "substituir", "categoria_ids": [feira]},
        tags={"acao": "trocar", "tags": ["praia"], "por": "VIAGEM"},
    )
    assert classificacao(casal, um) == [({feira}, {"Rotina", "Viagem"})]

    aplicada(casal, marcados(um), tags={"acao": "substituir", "tags": []})
    assert classificacao(casal, um) == [({feira}, set())]


def test_lote_que_deixaria_lancamento_sem_categoria_e_recusado_inteiro(casal: Casal):
    conta = casal.conta()
    mercado, casa = casal.categoria("Mercado"), casal.categoria("Casa")
    com_duas = lancar(casal, conta, [mercado, casa])
    so_mercado = lancar(casal, conta, [mercado])
    mudanca = {"categorias": {"acao": "remover", "categoria_ids": [mercado]}}

    vista = previa(casal, marcados(com_duas, so_mercado), **mudanca)
    resposta = aplicar(casal, marcados(com_duas, so_mercado), **mudanca)

    assert vista["recusa"] == "o lote deixaria 1 lançamento sem categoria"
    assert resposta.status_code == 422
    assert resposta.json()["detail"] == "o lote deixaria 1 lançamento sem categoria"
    assert classificacao(casal, com_duas, so_mercado) == [
        ({mercado, casa}, set()),
        ({mercado}, set()),
    ]
    assert casal.pedir("flavio", "GET", "/api/edicoes-em-lote").json() == []


def test_lote_que_nao_muda_nada_e_recusado(casal: Casal):
    conta, mercado = casal.conta(), casal.categoria("Mercado")
    feira = lancar(casal, conta, [mercado])

    resposta = aplicar(
        casal, marcados(feira), categorias={"acao": "acrescentar", "categoria_ids": [mercado]}
    )

    assert resposta.status_code == 422
    assert resposta.json()["detail"] == "nenhum lançamento muda"


@pytest.mark.parametrize(
    "mudanca",
    [
        {"categorias": {"acao": "acrescentar", "categoria_ids": ["arquivada"]}},
        {"categorias": {"acao": "trocar", "categoria_ids": ["mercado"], "por": "salario"}},
        {"categorias": {"acao": "trocar", "categoria_ids": ["mercado"]}},
        {"categorias": {"acao": "acrescentar", "categoria_ids": ["nenhuma"]}},
        {"tags": {"acao": "acrescentar", "tags": ["Antiga"]}},
        {"tags": {"acao": "acrescentar", "tags": []}},
        {},
    ],
)
def test_mudanca_invalida_e_recusada(casal: Casal, mudanca: dict):
    conta = casal.conta()
    ids = {
        "mercado": casal.categoria("Mercado"),
        "salario": casal.categoria("Salário", "receita"),
        "arquivada": casal.categoria("Velha"),
        "nenhuma": str(uuid4()),
    }
    casal.pedir("flavio", "PATCH", f"/api/categorias/{ids['arquivada']}", json={"arquivada": True})
    tag = casal.pedir("flavio", "POST", "/api/tags", json={"nome": "Antiga"}).json()
    casal.pedir("flavio", "PATCH", f"/api/tags/{tag['id']}", json={"arquivada": True})
    feira = lancar(casal, conta, [ids["mercado"]])
    if categorias := mudanca.get("categorias"):
        categorias["categoria_ids"] = [ids[c] for c in categorias["categoria_ids"]]
        if "por" in categorias:
            categorias["por"] = ids[categorias["por"]]

    resposta = casal.pedir(
        "esposa",
        "POST",
        "/api/edicoes-em-lote/previa",
        json={"selecao": marcados(feira)} | mudanca,
    )

    assert resposta.status_code == 422, resposta.text


def test_categoria_de_outro_tipo_nao_entra_em_receita(casal: Casal):
    conta = casal.conta()
    mercado, casa = casal.categoria("Mercado"), casal.categoria("Casa")
    salario = casal.categoria("Salário", "receita")
    feira = lancar(casal, conta, [mercado])
    pagamento = lancar(casal, conta, [salario], tipo="receita")

    vista = previa(
        casal,
        marcados(feira, pagamento),
        categorias={"acao": "substituir", "categoria_ids": [casa]},
    )
    aplicada(
        casal,
        marcados(feira, pagamento),
        categorias={"acao": "substituir", "categoria_ids": [casa]},
    )

    assert (vista["mudam"], vista["de_outro_tipo"]) == (1, 1)
    assert classificacao(casal, feira, pagamento) == [({casa}, set()), ({salario}, set())]


def test_parcela_marcada_leva_o_parcelamento_todo_com_a_contagem(casal: Casal):
    nubank, eletro, casa = (
        novo_cartao(casal)["id"],
        casal.categoria("Eletro"),
        casal.categoria("Casa"),
    )
    geladeira = parcelar(casal, nubank, [eletro])
    fogao = parcelar(casal, nubank, [eletro], parcelas=4, descricao="Fogão")
    avulso = lancar(casal, casal.conta(), [eletro], descricao="Liquidificador")
    uma_parcela = next(l for l in todos(casal).values() if l["parcelamento_id"] == fogao)

    vista = previa(
        casal,
        {"parcelamento_ids": [geladeira], "lancamento_ids": [uma_parcela["id"], avulso["id"]]},
        categorias={"acao": "acrescentar", "categoria_ids": [casa]},
    )

    assert (vista["compras"], vista["lancamentos"], vista["mudam"]) == (3, 15, 15)
    lote = aplicada(
        casal,
        {"parcelamento_ids": [geladeira], "lancamento_ids": [uma_parcela["id"], avulso["id"]]},
        categorias={"acao": "acrescentar", "categoria_ids": [casa]},
    )
    assert lote["lancamentos"] == 15
    assert all(set(l["categoria_ids"]) == {eletro, casa} for l in todos(casal).values())


def test_todos_do_resultado_da_busca_sem_as_transferencias(casal: Casal):
    conta, poupanca = casal.conta(), casal.conta("Poupança")
    mercado, casa = casal.categoria("Mercado"), casal.categoria("Casa")
    feira = lancar(casal, conta, [mercado], descricao="Feira da rua")
    outra = lancar(casal, conta, [mercado], descricao="Outra coisa")
    casal.pedir(
        "flavio",
        "POST",
        "/api/transferencias",
        json={
            "id": str(uuid4()),
            "valor_centavos": 1000,
            "data": "2026-10-02",
            "descricao": "Feira guardada",
            "conta_origem_id": conta,
            "conta_destino_id": poupanca,
        },
    )

    lote = aplicada(
        casal,
        {"busca": {"texto": "feira"}},
        categorias={"acao": "acrescentar", "categoria_ids": [casa]},
    )

    assert lote["lancamentos"] == 1
    assert classificacao(casal, feira, outra) == [({mercado, casa}, set()), ({mercado}, set())]


def test_previa_conta_quem_troca_de_item_e_a_escolha_sai_com_a_categoria(casal: Casal):
    conta = casal.conta()
    mercado, feira, casa = (
        casal.categoria("Mercado"),
        casal.categoria("Feira"),
        casal.categoria("Casa"),
    )
    item(casal, mercado, 100000)
    item(casal, feira, 50000)
    no_mercado = lancar(casal, conta, [mercado])
    escolhido = lancar(casal, conta, [mercado, casa], item_categoria_id=mercado)
    sem_item = lancar(casal, conta, [casa])
    mudanca = {"categorias": {"acao": "trocar", "categoria_ids": [mercado], "por": feira}}

    vista = previa(casal, marcados(no_mercado, escolhido, sem_item), **mudanca)
    aplicada(casal, marcados(no_mercado, escolhido, sem_item), **mudanca)

    assert (vista["mudam"], vista["trocam_de_item"]) == (2, 2)
    agora = todos(casal)
    assert agora[escolhido["id"]]["item_categoria_id"] is None
    plano = casal.pedir("esposa", "GET", "/api/planejamento/2026-10").json()
    realizados = {i["categoria_id"]: i["realizado_centavos"] for i in plano["itens"]}
    assert realizados == {mercado: 0, feira: 2 * 12035}


def test_estorno_segue_a_compra_e_sozinho_fica_de_fora(casal: Casal):
    nubank, mercado, casa = (
        novo_cartao(casal)["id"],
        casal.categoria("Mercado"),
        casal.categoria("Casa"),
    )
    compra = lancar(casal, nubank, [mercado], descricao="Compra")
    estorno = estornar(casal, compra, "2026-10-05", valor_centavos=1000).json()
    outra = lancar(casal, nubank, [mercado], descricao="Outra")
    estorno_da_outra = estornar(casal, outra, "2026-10-06", valor_centavos=500).json()
    mudanca = {"categorias": {"acao": "acrescentar", "categoria_ids": [casa]}}

    vista = previa(casal, marcados(compra, estorno_da_outra), **mudanca)
    aplicada(casal, marcados(compra, estorno_da_outra), **mudanca)

    assert (vista["lancamentos"], vista["mudam"], vista["estornos_fora"]) == (2, 2, 1)
    assert classificacao(casal, compra, estorno, outra, estorno_da_outra) == [
        ({mercado, casa}, set()),
        ({mercado, casa}, set()),
        ({mercado}, set()),
        ({mercado}, set()),
    ]


def test_tudo_ou_nada_desfaz_as_partes_ja_gravadas_quando_uma_falha(
    casal: Casal, monkeypatch: pytest.MonkeyPatch
):
    conta, mercado, casa = casal.conta(), casal.categoria("Mercado"), casal.categoria("Casa")
    lancados = [lancar(casal, conta, [mercado], data=f"2026-10-0{d}") for d in range(1, 5)]
    monkeypatch.setattr(edicao_em_lote, "POR_TRANSACAO", 1)
    original = edicao_em_lote._aplicar_parte
    partes = [0]

    def falhar_na_terceira(conn, *args):
        partes[0] += 1
        if partes[0] == 3:
            raise edicao_em_lote.LoteRecusado("o lançamento mudou no meio")
        return original(conn, *args)

    monkeypatch.setattr(edicao_em_lote, "_aplicar_parte", falhar_na_terceira)

    resposta = aplicar(
        casal, marcados(*lancados), categorias={"acao": "acrescentar", "categoria_ids": [casa]}
    )

    assert resposta.status_code == 422
    assert classificacao(casal, *lancados) == [({mercado}, set())] * 4
    assert casal.pedir("flavio", "GET", "/api/edicoes-em-lote").json() == []


def test_mesmo_id_reenviado_devolve_o_lote_gravado(casal: Casal):
    conta, mercado, casa = casal.conta(), casal.categoria("Mercado"), casal.categoria("Casa")
    feira = lancar(casal, conta, [mercado])
    id = str(uuid4())
    mudanca = {"categorias": {"acao": "acrescentar", "categoria_ids": [casa]}}

    primeira = aplicar(casal, marcados(feira), id=id, **mudanca)
    segunda = aplicar(casal, marcados(feira), id=id, **mudanca)

    assert (primeira.status_code, segunda.status_code) == (201, 200)
    assert segunda.json() == primeira.json()
    assert todos(casal)[feira["id"]]["versao"] == 2


def test_desfazer_volta_o_que_estava_e_pula_o_que_mudou_depois(casal: Casal):
    conta, mercado, casa = casal.conta(), casal.categoria("Mercado"), casal.categoria("Casa")
    feira = lancar(casal, conta, [mercado], descricao="Feira", tags=["Rotina"])
    padaria = lancar(casal, conta, [mercado], descricao="Padaria")
    excluido = lancar(casal, conta, [mercado], descricao="Açougue")
    lote = aplicada(
        casal,
        marcados(feira, padaria, excluido),
        categorias={"acao": "substituir", "categoria_ids": [casa]},
        tags={"acao": "acrescentar", "tags": ["Lote"]},
    )
    # Depois do lote, o Flávio troca as tags da padaria e exclui o açougue; mudar o valor da
    # feira não mexe no que o lote mudou.
    agora = todos(casal)
    casal.pedir(
        "flavio",
        "PATCH",
        f"/api/lancamentos/{padaria['id']}",
        json={"versao": agora[padaria["id"]]["versao"], "tags": ["Café"]},
    )
    casal.pedir(
        "flavio",
        "PATCH",
        f"/api/lancamentos/{feira['id']}",
        json={"versao": agora[feira["id"]]["versao"], "valor_centavos": 999},
    )
    casal.pedir("flavio", "DELETE", f"/api/lancamentos/{excluido['id']}")

    resposta = desfazer(casal, lote)

    assert resposta.status_code == 200, resposta.text
    resultado = resposta.json()
    assert resultado["desfeitos"] == 1
    assert [
        (p["descricao"], p["motivo"], p["alterado_por"], p["por_voce"])
        for p in resultado["pulados"]
        # Na ordem da busca: o mais recente primeiro.
    ] == [("Açougue", "excluido", "flavio", False), ("Padaria", "mudou_depois", "flavio", False)]
    agora = todos(casal)
    assert classificacao(casal, feira, padaria) == [
        ({mercado}, {"Rotina"}),
        ({casa}, {"Café"}),
    ]
    assert (agora[feira["id"]]["valor_centavos"], agora[feira["id"]]["alterado_por"]) == (
        999,
        "esposa",
    )
    # Desfeito, sai da lista e não se desfaz de novo.
    assert casal.pedir("flavio", "GET", "/api/edicoes-em-lote").json() == []
    assert desfazer(casal, lote).json() == resultado


def test_desfazer_devolve_a_escolha_do_item(casal: Casal):
    conta = casal.conta()
    mercado, casa = casal.categoria("Mercado"), casal.categoria("Casa")
    item(casal, mercado, 100000)
    item(casal, casa, 100000)
    escolhido = lancar(casal, conta, [mercado, casa], item_categoria_id=casa)
    lote = aplicada(
        casal, marcados(escolhido), categorias={"acao": "remover", "categoria_ids": [casa]}
    )
    assert todos(casal)[escolhido["id"]]["item_categoria_id"] is None

    desfazer(casal, lote)

    agora = todos(casal)[escolhido["id"]]
    assert (set(agora["categoria_ids"]), agora["item_categoria_id"]) == ({mercado, casa}, casa)


def test_lista_os_lotes_desfaziveis_e_recusa_depois_de_30_dias(casal: Casal, database_url: str):
    conta, mercado, casa = casal.conta(), casal.categoria("Mercado"), casal.categoria("Casa")
    feira = lancar(casal, conta, [mercado])
    antigo = aplicada(
        casal, marcados(feira), categorias={"acao": "acrescentar", "categoria_ids": [casa]}
    )
    novo = aplicada(
        casal,
        marcados(feira),
        quem="flavio",
        tags={"acao": "acrescentar", "tags": ["Casa nova"]},
    )
    with psycopg.connect(database_url, autocommit=True) as conn:
        conn.execute(
            "UPDATE edicoes_em_lote SET criado_em = %s WHERE id = %s",
            (datetime.now(UTC) - timedelta(days=31), antigo["id"]),
        )

    lista = casal.pedir("esposa", "GET", "/api/edicoes-em-lote").json()

    assert [(l["id"], l["criado_por"], l["resumo"]) for l in lista] == [
        (novo["id"], "flavio", "Tags: acrescentar #Casa nova")
    ]
    assert datetime.fromisoformat(lista[0]["desfazer_ate"]) - datetime.fromisoformat(
        lista[0]["criado_em"]
    ) == timedelta(days=30)
    recusado = desfazer(casal, antigo)
    assert recusado.status_code == 422
    assert recusado.json()["detail"] == "passou o prazo de 30 dias para desfazer"
    assert desfazer(casal, {"id": str(uuid4())}).status_code == 404


def test_lote_recusado_no_meio_reenviado_e_recusado_de_novo(
    casal: Casal, monkeypatch: pytest.MonkeyPatch
):
    conta, mercado, casa = casal.conta(), casal.categoria("Mercado"), casal.categoria("Casa")
    feira = lancar(casal, conta, [mercado])
    id, mudanca = str(uuid4()), {"categorias": {"acao": "acrescentar", "categoria_ids": [casa]}}

    def recusar(*args):
        raise edicao_em_lote.LoteRecusado("o lote deixaria 1 lançamento sem categoria")

    with monkeypatch.context() as so_agora:
        so_agora.setattr(edicao_em_lote, "_aplicar_parte", recusar)
        aplicar(casal, marcados(feira), id=id, **mudanca)
    reenvio = aplicar(casal, marcados(feira), id=id, **mudanca)

    assert reenvio.status_code == 422
    assert reenvio.json()["detail"] == "o lote deixaria 1 lançamento sem categoria"
    assert desfazer(casal, {"id": id}).status_code == 404


def test_lote_interrompido_aparece_na_lista_e_o_desfazer_volta_o_que_foi_gravado(
    casal: Casal, database_url: str
):
    conta, mercado, casa = casal.conta(), casal.categoria("Mercado"), casal.categoria("Casa")
    feira = lancar(casal, conta, [mercado])
    lote = aplicada(
        casal, marcados(feira), categorias={"acao": "acrescentar", "categoria_ids": [casa]}
    )
    # A gravação que parou no meio (a Lambda caiu) deixa o lote em `aplicando`.
    with psycopg.connect(database_url, autocommit=True) as conn:
        conn.execute(
            "UPDATE edicoes_em_lote SET situacao = 'aplicando' WHERE id = %s", (lote["id"],)
        )

    [listado] = casal.pedir("flavio", "GET", "/api/edicoes-em-lote").json()
    assert listado["situacao"] == "aplicando"
    reenvio = aplicar(
        casal,
        marcados(feira),
        id=lote["id"],
        categorias={"acao": "remover", "categoria_ids": [casa]},
    )
    assert (reenvio.status_code, reenvio.json()["situacao"]) == (200, "aplicando")

    assert desfazer(casal, lote, quem="flavio").json() == {"desfeitos": 1, "pulados": []}
    assert classificacao(casal, feira) == [({mercado}, set())]


def test_desfazer_pula_o_que_tinha_tag_juntada_depois(casal: Casal):
    conta, mercado, casa = casal.conta(), casal.categoria("Mercado"), casal.categoria("Casa")
    feira = lancar(casal, conta, [mercado], descricao="Feira", tags=["Rotina"])
    lote = aplicada(
        casal, marcados(feira), categorias={"acao": "acrescentar", "categoria_ids": [casa]}
    )
    tags = {t["nome"]: t["id"] for t in casal.pedir("flavio", "GET", "/api/tags").json()}
    destino = casal.pedir("flavio", "POST", "/api/tags", json={"nome": "Dia a dia"}).json()
    juntada = casal.pedir(
        "flavio", "POST", f"/api/tags/{tags['Rotina']}/juntar", json={"destino_id": destino["id"]}
    )
    assert juntada.status_code == 200, juntada.text

    resultado = desfazer(casal, lote).json()

    assert resultado["desfeitos"] == 0
    assert [(p["descricao"], p["motivo"]) for p in resultado["pulados"]] == [("Feira", "saiu")]
    assert classificacao(casal, feira) == [({mercado, casa}, {"Dia a dia"})]


def test_o_parcelamento_muda_junto_e_a_parcela_que_volta_vem_com_a_classificacao_do_lote(
    casal: Casal,
):
    conta, mercado, casa = casal.conta(), casal.categoria("Mercado"), casal.categoria("Casa")
    emprestimo = parcelar(
        casal, conta, [mercado], parcelas=3, data="2026-11-10", descricao="Empréstimo"
    )
    lote = aplicada(
        casal,
        {"parcelamento_ids": [emprestimo]},
        categorias={"acao": "trocar", "categoria_ids": [mercado], "por": casa},
        tags={"acao": "acrescentar", "tags": ["Banco"]},
    )

    def corrigir(parcelas: int):
        resposta = casal.pedir(
            "flavio", "PATCH", f"/api/parcelamentos/{emprestimo}", json={"parcelas": parcelas}
        )
        assert resposta.status_code == 200, resposta.text

    # O parcelamento encolhe e cresce de novo: a 3ª parcela volta com a classificação dele.
    corrigir(2)
    corrigir(3)
    parcelas = [l for l in todos(casal).values() if l["parcelamento_id"] == emprestimo]
    assert [
        (p["parcela"], p["categoria_ids"], p["tags"])
        for p in sorted(parcelas, key=lambda p: p["parcela"])
    ] == [(n, [casa], ["Banco"]) for n in (1, 2, 3)]

    # O desfazer volta o parcelamento também; a parcela que voltou depois do lote é dele, não do
    # lote, e fica como está.
    resultado = desfazer(casal, lote).json()
    assert resultado["desfeitos"] == 2
    corrigir(2)
    corrigir(3)
    parcelas = sorted(
        (l for l in todos(casal).values() if l["parcelamento_id"] == emprestimo),
        key=lambda p: p["parcela"],
    )
    assert [(p["categoria_ids"], p["tags"]) for p in parcelas] == [([mercado], [])] * 3


def test_desfazer_pula_tambem_o_que_a_propria_pessoa_mudou_depois(casal: Casal):
    conta, mercado, casa = casal.conta(), casal.categoria("Mercado"), casal.categoria("Casa")
    feira = lancar(casal, conta, [mercado], descricao="Feira")
    lote = aplicada(
        casal, marcados(feira), categorias={"acao": "acrescentar", "categoria_ids": [casa]}
    )
    casal.pedir(
        "esposa",
        "PATCH",
        f"/api/lancamentos/{feira['id']}",
        json={"versao": todos(casal)[feira["id"]]["versao"], "tags": ["À mão"]},
    )

    resultado = desfazer(casal, lote).json()

    assert [(p["descricao"], p["motivo"], p["por_voce"]) for p in resultado["pulados"]] == [
        ("Feira", "mudou_depois", True)
    ]
    assert classificacao(casal, feira) == [({mercado, casa}, {"À mão"})]
