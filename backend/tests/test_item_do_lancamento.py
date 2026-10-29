"""Em que item do planejamento cada lançamento conta e a lista "a escolher" (ADR 0006)."""

from datetime import date

import pytest

from app import lancamentos
from tests.conftest import Casal
from tests.test_cartoes import novo_cartao
from tests.test_estorno_e_ajuste import estornar
from tests.test_planejamento import item, lancar, ler
from tests.test_recorrencias import gerados, recorrencia


@pytest.fixture(autouse=True)
def hoje_e_15_de_outubro(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(lancamentos, "hoje", lambda: date(2026, 10, 15))


def realizados(plano: dict) -> dict[str, int]:
    return {i["categoria_id"]: i["realizado_centavos"] for i in plano["itens"]}


def test_com_duas_categorias_com_item_conta_no_item_escolhido_e_sem_escolha_fica_a_escolher(
    casal: Casal,
):
    conta = casal.conta()
    restaurante, viagem = casal.categoria("Restaurante"), casal.categoria("Viagem")
    item(casal, restaurante, 100000)
    item(casal, viagem, 300000)
    jantar = lancar(
        casal, conta, [restaurante, viagem], 25000, "2026-10-03", item_categoria_id=viagem
    )
    sem_escolha = lancar(casal, conta, [restaurante, viagem], 4000, "2026-10-04")

    plano = ler(casal)

    assert jantar["item_categoria_id"] == viagem
    assert sem_escolha["item_categoria_id"] is None
    assert realizados(plano) == {restaurante: 0, viagem: 25000}
    assert plano["a_escolher"] == [
        {
            "lancamento_id": sem_escolha["id"],
            "item_categoria_id": None,
            "categorias_com_item": sorted([restaurante, viagem]),
        }
    ]


def escolher(casal: Casal, lancado: dict, categoria: str, quem="esposa"):
    return casal.pedir(
        quem,
        "PATCH",
        f"/api/lancamentos/{lancado['id']}",
        json={"versao": lancado["versao"], "item_categoria_id": categoria},
    )


def test_item_criado_no_meio_do_mes_mantem_o_item_atual_e_poe_o_lancamento_a_escolher(
    casal: Casal,
):
    conta = casal.conta()
    restaurante, viagem = casal.categoria("Restaurante"), casal.categoria("Viagem")
    item(casal, restaurante, 100000)
    jantar = lancar(casal, conta, [restaurante, viagem], 25000, "2026-10-03")
    assert realizados(ler(casal)) == {restaurante: 25000}

    item(casal, viagem, 300000)

    plano = ler(casal)
    assert realizados(plano) == {restaurante: 25000, viagem: 0}
    assert plano["a_escolher"] == [
        {
            "lancamento_id": jantar["id"],
            "item_categoria_id": restaurante,
            "categorias_com_item": sorted([restaurante, viagem]),
        }
    ]

    escolhido = escolher(casal, jantar, viagem)

    assert escolhido.status_code == 200, escolhido.text
    assert escolhido.json()["item_categoria_id"] == viagem
    plano = ler(casal)
    assert realizados(plano) == {restaurante: 0, viagem: 25000}
    assert plano["a_escolher"] == []


def editar(casal: Casal, lancado: dict, **campos) -> dict:
    resposta = casal.pedir(
        "flavio",
        "PATCH",
        f"/api/lancamentos/{lancado['id']}",
        json={"versao": lancado["versao"]} | campos,
    )
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


def test_categoria_com_item_acrescentada_ao_lancamento_o_mantem_no_item_e_o_poe_a_escolher(
    casal: Casal,
):
    conta = casal.conta()
    mercado, festa, extra = (casal.categoria(n) for n in ("Mercado", "Festa", "Extra"))
    item(casal, mercado, 100000)
    item(casal, festa, 50000)
    compra = lancar(casal, conta, [mercado], 8000, "2026-10-08")

    editado = editar(casal, compra, categoria_ids=[mercado, festa, extra])

    plano = ler(casal)
    assert editado["item_categoria_id"] is None
    assert realizados(plano) == {mercado: 8000, festa: 0}
    assert [(e["lancamento_id"], e["item_categoria_id"]) for e in plano["a_escolher"]] == [
        (compra["id"], mercado)
    ]


def test_tirar_do_lancamento_a_categoria_escolhida_desfaz_a_escolha(casal: Casal):
    conta = casal.conta()
    mercado, festa, extra = (casal.categoria(n) for n in ("Mercado", "Festa", "Extra"))
    item(casal, mercado, 100000)
    item(casal, festa, 50000)
    compra = lancar(casal, conta, [mercado, festa, extra], 8000, "2026-10-08")
    compra = editar(casal, compra, item_categoria_id=festa)

    editado = editar(casal, compra, categoria_ids=[mercado, extra])

    assert editado["item_categoria_id"] is None
    assert realizados(ler(casal)) == {mercado: 8000, festa: 0}


def test_escolha_de_item_fora_das_categorias_do_lancamento_e_recusada(casal: Casal):
    conta = casal.conta()
    mercado, festa = casal.categoria("Mercado"), casal.categoria("Festa")
    criado = casal.pedir(
        "flavio",
        "POST",
        "/api/lancamentos",
        json={
            "id": "00000000-0000-0000-0000-000000000051",
            "tipo": "despesa",
            "valor_centavos": 1000,
            "data": "2026-10-08",
            "conta_id": conta,
            "categoria_ids": [mercado],
            "item_categoria_id": festa,
        },
    )
    assert criado.status_code == 422
    compra = lancar(casal, conta, [mercado], 8000, "2026-10-08")

    editado = casal.pedir(
        "flavio",
        "PATCH",
        f"/api/lancamentos/{compra['id']}",
        json={"versao": compra["versao"], "item_categoria_id": festa},
    )

    assert editado.status_code == 422
    assert editado.json()["detail"] == "o item escolhido não é de uma categoria do lançamento"


def test_escolha_explicita_nunca_muda_sozinha(casal: Casal):
    conta = casal.conta()
    restaurante, viagem, lazer = (casal.categoria(n) for n in ("Restaurante", "Viagem", "Lazer"))
    item(casal, restaurante, 100000)
    do_item_viagem = item(casal, viagem, 300000)
    jantar = lancar(
        casal,
        conta,
        [restaurante, viagem, lazer],
        25000,
        "2026-10-03",
        item_categoria_id=viagem,
    )

    item(casal, lazer, 40000)  # mais uma categoria com item: a escolha fica
    assert realizados(ler(casal))[viagem] == 25000
    assert ler(casal)["a_escolher"] == []

    # Sem o item da viagem, conta em nenhum, mas a escolha continua guardada.
    casal.pedir("flavio", "DELETE", f"/api/planejamento/itens/{do_item_viagem['id']}")
    sem_o_item = ler(casal)
    assert realizados(sem_o_item) == {restaurante: 0, lazer: 0}
    assert sem_o_item["a_escolher"][0]["item_categoria_id"] is None

    item(casal, viagem, 300000)
    assert realizados(ler(casal)) == {restaurante: 0, viagem: 25000, lazer: 0}
    lido = casal.pedir("esposa", "GET", "/api/lancamentos").json()[0]
    assert (lido["id"], lido["item_categoria_id"]) == (jantar["id"], viagem)


def test_planejamento_copiado_poe_a_escolher_o_lancamento_com_duas_categorias_com_item(
    casal: Casal,
):
    conta = casal.conta()
    restaurante, viagem = casal.categoria("Restaurante"), casal.categoria("Viagem")
    item(casal, restaurante, 100000)
    item(casal, viagem, 300000)
    jantar = lancar(casal, conta, [restaurante, viagem], 25000, "2026-11-03")

    copiado = casal.pedir(
        "flavio", "POST", "/api/planejamento/2026-11/copiar", json={"de": "2026-10"}
    )

    assert copiado.status_code == 201
    assert [(e["lancamento_id"], e["item_categoria_id"]) for e in copiado.json()["a_escolher"]] == [
        (jantar["id"], None)
    ]


def test_lancamento_que_muda_de_mes_fica_no_item_em_que_estava(casal: Casal):
    conta = casal.conta()
    mercado, festa = casal.categoria("Mercado"), casal.categoria("Festa")
    item(casal, mercado, 100000)
    item(casal, mercado, 100000, mes="2026-11")
    item(casal, festa, 50000, mes="2026-11")
    compra = lancar(casal, conta, [mercado, festa], 8000, "2026-10-20", situacao="previsto")

    casal.pedir(
        "flavio", "POST", f"/api/lancamentos/{compra['id']}/confirmar", json={"data": "2026-11-02"}
    )

    novembro = ler(casal, "2026-11")
    assert realizados(novembro) == {mercado: 8000, festa: 0}
    assert [e["item_categoria_id"] for e in novembro["a_escolher"]] == [mercado]


def test_recorrencia_guarda_a_escolha_e_os_previstos_ja_nascem_com_ela(casal: Casal):
    conta = casal.conta()
    casa, assinaturas = casal.categoria("Casa"), casal.categoria("Assinaturas")
    item(casal, casa, 100000, mes="2026-11")
    item(casal, assinaturas, 20000, mes="2026-11")
    regra = recorrencia(conta, [casa, assinaturas], vezes=3, item_categoria_id=assinaturas)

    criada = casal.pedir("flavio", "POST", "/api/recorrencias", json=regra)

    assert criada.status_code == 201, criada.text
    assert criada.json()["item_categoria_id"] == assinaturas
    previstos = gerados(casal, regra["id"])
    assert [p["item_categoria_id"] for p in previstos] == [assinaturas] * 3
    novembro = ler(casal, "2026-11")
    assert realizados(novembro) == {casa: 0, assinaturas: 0}
    assert {i["categoria_id"]: i["previsto_centavos"] for i in novembro["itens"]} == {
        casa: 0,
        assinaturas: 18990,
    }
    assert novembro["a_escolher"] == []


def test_recorrencia_recusa_escolha_de_item_fora_das_categorias(casal: Casal):
    conta = casal.conta()
    casa, assinaturas = casal.categoria("Casa"), casal.categoria("Assinaturas")

    criada = casal.pedir(
        "flavio",
        "POST",
        "/api/recorrencias",
        json=recorrencia(conta, [casa], item_categoria_id=assinaturas),
    )

    assert criada.status_code == 422


def test_juntar_categorias_move_as_escolhas_de_item_e_mantem_quem_contava_sozinho(casal: Casal):
    conta = casal.conta()
    restaurante, viagem, passeio = (
        casal.categoria(n) for n in ("Restaurante", "Viagem", "Passeio")
    )
    item(casal, restaurante, 100000)
    item(casal, passeio, 300000)
    jantar = lancar(
        casal, conta, [restaurante, passeio], 25000, "2026-10-03", item_categoria_id=passeio
    )
    # Só o restaurante tem item; com a junção, a viagem passa a ter o do passeio.
    lanche = lancar(casal, conta, [restaurante, viagem], 3000, "2026-10-04")
    regra = recorrencia(conta, [restaurante, passeio], vezes=1, item_categoria_id=passeio)
    assert casal.pedir("flavio", "POST", "/api/recorrencias", json=regra).status_code == 201

    juntada = casal.pedir(
        "flavio", "POST", f"/api/categorias/{passeio}/juntar", json={"destino_id": viagem}
    )

    assert juntada.status_code == 200, juntada.text
    lidos = {l["id"]: l for l in casal.pedir("esposa", "GET", "/api/lancamentos").json()}
    assert lidos[jantar["id"]]["item_categoria_id"] == viagem
    plano = ler(casal)
    assert realizados(plano) == {restaurante: 3000, viagem: 25000}
    assert [(e["lancamento_id"], e["item_categoria_id"]) for e in plano["a_escolher"]] == [
        (lanche["id"], restaurante)
    ]
    [lida] = casal.pedir("esposa", "GET", "/api/recorrencias").json()
    assert (sorted(lida["categoria_ids"]), lida["item_categoria_id"]) == (
        sorted([restaurante, viagem]),
        viagem,
    )


def test_estorno_nasce_com_a_escolha_de_item_da_compra(casal: Casal):
    cartao = novo_cartao(casal)["id"]
    restaurante, viagem = casal.categoria("Restaurante"), casal.categoria("Viagem")
    item(casal, restaurante, 100000)
    item(casal, viagem, 300000)
    jantar = lancar(
        casal, cartao, [restaurante, viagem], 25000, "2026-10-02", item_categoria_id=viagem
    )

    estorno = estornar(casal, jantar, "2026-10-12", valor_centavos=10000)

    assert estorno.status_code == 201, estorno.text
    assert estorno.json()["item_categoria_id"] == viagem
    plano = ler(casal)
    assert realizados(plano) == {restaurante: 0, viagem: 15000}
    assert plano["a_escolher"] == []


def test_escolhas_de_item_diferentes_sobre_a_mesma_versao_sao_conflito(casal: Casal):
    conta = casal.conta()
    restaurante, viagem = casal.categoria("Restaurante"), casal.categoria("Viagem")
    item(casal, restaurante, 100000)
    item(casal, viagem, 300000)
    jantar = lancar(casal, conta, [restaurante, viagem], 25000, "2026-10-03")
    assert escolher(casal, jantar, viagem, quem="esposa").status_code == 200

    depois = escolher(casal, jantar, restaurante, quem="flavio")

    assert depois.status_code == 409
    assert [c["campo"] for c in depois.json()["campos"]] == ["item_categoria_id"]
    assert depois.json()["lancamento"]["item_categoria_id"] == viagem
