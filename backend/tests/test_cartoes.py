from datetime import date

import pytest

from app import lancamentos
from tests.conftest import Casal
from tests.test_lancamentos import lancamento


def novo_cartao(casal: Casal, nome="Nubank", **campos) -> dict:
    resposta = casal.pedir(
        "flavio",
        "POST",
        "/api/cartoes",
        json={"nome": nome, "dia_fechamento": 25, "dia_vencimento": 5} | campos,
    )
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def comprar(casal: Casal, cartao: str, data: str, quem="flavio", **campos) -> dict:
    resposta = casal.pedir(
        quem,
        "POST",
        "/api/lancamentos",
        json=lancamento(cartao, [casal.categoria()], data=data) | campos,
    )
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def test_compra_de_28_03_na_fatura_que_fecha_em_25_04_conta_em_abril(casal: Casal):
    # O exemplo do glossário (ADR 0003): mercado de 28/03 é "alimentação de abril".
    cartao = novo_cartao(casal)["id"]

    compra = comprar(casal, cartao, "2026-03-28")

    assert compra["fatura_mes"] == "2026-04-01"
    assert compra["mes"] == "2026-04-01"


def test_compra_no_proprio_dia_do_fechamento_vai_para_a_fatura_seguinte(casal: Casal):
    cartao = novo_cartao(casal)["id"]

    vespera = comprar(casal, cartao, "2026-04-24")
    no_dia = comprar(casal, cartao, "2026-04-25")

    assert vespera["fatura_mes"] == "2026-04-01"
    assert no_dia["fatura_mes"] == "2026-05-01"


def test_cartao_que_conta_no_mes_anterior_ao_fechamento(casal: Casal):
    # Fecha no dia 3: a fatura que fecha em 03/05 é a de abril.
    cartao = novo_cartao(
        casal, dia_fechamento=3, dia_vencimento=10, mes_anterior_ao_fechamento=True
    )["id"]

    compra = comprar(casal, cartao, "2026-04-20")

    assert compra["fatura_mes"] == "2026-04-01"
    assert compra["mes"] == "2026-04-01"
    faturas = casal.pedir("esposa", "GET", f"/api/cartoes/{cartao}/faturas").json()
    assert [(f["mes"], f["fechamento"], f["vencimento"]) for f in faturas] == [
        ("2026-04-01", "2026-05-03", "2026-05-10")
    ]


def test_fatura_nasce_na_primeira_compra_com_as_datas_padrao(casal: Casal):
    cartao = novo_cartao(casal, dia_fechamento=31, dia_vencimento=8)["id"]
    assert casal.pedir("flavio", "GET", f"/api/cartoes/{cartao}/faturas").json() == []

    comprar(casal, cartao, "2026-02-10")
    comprar(casal, cartao, "2026-02-12")

    faturas = casal.pedir("flavio", "GET", f"/api/cartoes/{cartao}/faturas").json()
    # Dia 31 em fevereiro cai no último dia do mês; vence no mês seguinte.
    assert faturas == [
        {
            "cartao_id": cartao,
            "mes": "2026-02-01",
            "fechamento": "2026-02-28",
            "vencimento": "2026-03-08",
            "situacao": "fechada",
            "total_centavos": 24070,
            "saldo_anterior_centavos": 0,
            "pago_centavos": 0,
            "a_pagar_centavos": 24070,
        }
    ]


def test_compra_do_adicional_cai_na_fatura_do_titular(casal: Casal):
    titular = novo_cartao(casal, limite_centavos=500000)["id"]
    adicional = casal.pedir(
        "esposa", "POST", "/api/cartoes", json={"nome": "Nubank da esposa", "titular_id": titular}
    ).json()

    compra = comprar(casal, adicional["id"], "2026-03-28", quem="esposa")

    assert adicional["titular_id"] == titular
    assert compra["conta_id"] == adicional["id"]
    assert compra["fatura_mes"] == "2026-04-01"
    faturas = casal.pedir("flavio", "GET", f"/api/cartoes/{titular}/faturas").json()
    assert [f["mes"] for f in faturas] == ["2026-04-01"]
    assert casal.pedir("flavio", "GET", f"/api/cartoes/{adicional['id']}/faturas").json() == faturas


def test_adicional_usa_os_dias_e_o_limite_do_titular_e_nao_tem_adicional(casal: Casal):
    titular = novo_cartao(casal)["id"]
    adicional = casal.pedir(
        "flavio", "POST", "/api/cartoes", json={"nome": "Adicional", "titular_id": titular}
    ).json()["id"]

    for corpo in [
        {"nome": "Com dias", "titular_id": titular, "dia_fechamento": 10},
        {"nome": "Com limite", "titular_id": titular, "limite_centavos": 100},
        {"nome": "Adicional do adicional", "titular_id": adicional},
        {"nome": "Sem titular", "titular_id": "00000000-0000-0000-0000-000000000001"},
    ]:
        assert casal.pedir("flavio", "POST", "/api/cartoes", json=corpo).status_code == 422


def test_cartao_arquivado_sai_das_opcoes_e_recusa_compra_nova(casal: Casal):
    cartao = novo_cartao(casal)
    antiga = comprar(casal, cartao["id"], "2026-03-28")

    arquivado = casal.pedir(
        "esposa",
        "PUT",
        f"/api/cartoes/{cartao['id']}",
        json={"nome": "Nubank", "dia_fechamento": 25, "dia_vencimento": 5, "arquivado": True},
    )
    nova = casal.pedir(
        "flavio",
        "POST",
        "/api/lancamentos",
        json=lancamento(cartao["id"], [casal.categoria("Outra")], data="2026-04-02"),
    )
    editada = casal.pedir(
        "flavio",
        "PATCH",
        f"/api/lancamentos/{antiga['id']}",
        json={"versao": 1, "descricao": "Mercado do mês"},
    )

    assert arquivado.status_code == 200
    assert arquivado.json()["arquivado"] is True
    assert casal.pedir("flavio", "GET", "/api/cartoes").json() == []
    assert [
        c["id"] for c in casal.pedir("flavio", "GET", "/api/cartoes?arquivados=true").json()
    ] == [cartao["id"]]
    assert nova.status_code == 422
    assert nova.json()["detail"] == "cartão arquivado"
    # O histórico se edita: a compra antiga fica no cartão e na fatura dela.
    assert editada.status_code == 200
    assert editada.json()["fatura_mes"] == "2026-04-01"


def test_troca_a_fatura_de_uma_compra_a_mao(casal: Casal):
    # O banco lançou a compra de 24/04 só na fatura de maio.
    cartao = novo_cartao(casal)["id"]
    compra = comprar(casal, cartao, "2026-04-24")

    trocada = casal.pedir(
        "esposa",
        "PATCH",
        f"/api/lancamentos/{compra['id']}",
        json={"versao": 1, "fatura_mes": "2026-05-01"},
    )

    assert trocada.status_code == 200, trocada.text
    assert trocada.json()["fatura_mes"] == "2026-05-01"
    assert trocada.json()["mes"] == "2026-05-01"
    faturas = casal.pedir("flavio", "GET", f"/api/cartoes/{cartao}/faturas").json()
    assert [f["mes"] for f in faturas] == ["2026-04-01", "2026-05-01"]


def test_compra_ja_lancada_na_fatura_escolhida_e_que_a_fatura_a_mao_fica_ao_mudar_a_data(
    casal: Casal,
):
    cartao = novo_cartao(casal)["id"]
    compra = comprar(casal, cartao, "2026-04-20", fatura_mes="2026-05-01")

    nova_data = casal.pedir(
        "flavio",
        "PATCH",
        f"/api/lancamentos/{compra['id']}",
        json={"versao": 1, "data": "2026-04-21"},
    ).json()

    assert compra["fatura_mes"] == "2026-05-01"
    assert nova_data["fatura_mes"] == "2026-05-01"


def test_mudar_a_data_da_compra_escolhe_a_fatura_de_novo(casal: Casal):
    cartao = novo_cartao(casal)["id"]
    compra = comprar(casal, cartao, "2026-04-20")

    editada = casal.pedir(
        "flavio",
        "PATCH",
        f"/api/lancamentos/{compra['id']}",
        json={"versao": 1, "data": "2026-04-26"},
    ).json()

    assert editada["fatura_mes"] == "2026-05-01"
    assert editada["mes"] == "2026-05-01"


def test_lancamento_de_conta_conta_no_mes_da_data_e_nao_aceita_fatura(casal: Casal):
    conta, mercado = casal.conta(), casal.categoria()

    criado = casal.pedir(
        "flavio", "POST", "/api/lancamentos", json=lancamento(conta, [mercado], data="2026-03-28")
    ).json()
    com_fatura = casal.pedir(
        "flavio",
        "POST",
        "/api/lancamentos",
        json=lancamento(conta, [mercado], fatura_mes="2026-04-01"),
    )

    assert (criado["mes"], criado["fatura_mes"]) == ("2026-03-01", None)
    assert com_fatura.status_code == 422
    assert com_fatura.json()["detail"] == "fatura só em compra no cartão"


def test_passar_a_compra_da_conta_para_o_cartao_e_de_volta(casal: Casal):
    conta, cartao = casal.conta(), novo_cartao(casal)["id"]
    compra = casal.pedir(
        "flavio",
        "POST",
        "/api/lancamentos",
        json=lancamento(conta, [casal.categoria()], data="2026-03-28"),
    ).json()

    no_cartao = casal.pedir(
        "flavio",
        "PATCH",
        f"/api/lancamentos/{compra['id']}",
        json={"versao": 1, "conta_id": cartao},
    ).json()
    de_volta = casal.pedir(
        "flavio", "PATCH", f"/api/lancamentos/{compra['id']}", json={"versao": 2, "conta_id": conta}
    ).json()

    assert (no_cartao["mes"], no_cartao["fatura_mes"]) == ("2026-04-01", "2026-04-01")
    assert (de_volta["mes"], de_volta["fatura_mes"]) == ("2026-03-01", None)


@pytest.fixture
def hoje_10_04(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(lancamentos, "hoje", lambda: date(2026, 4, 10))


def faturas_de(casal: Casal, cartao: str) -> list[tuple[str, str, str, str]]:
    return [
        (f["mes"], f["fechamento"], f["vencimento"], f["situacao"])
        for f in casal.pedir("flavio", "GET", f"/api/cartoes/{cartao}/faturas").json()
    ]


def fatura_de(casal: Casal, compra: dict) -> str:
    [lida] = [
        l
        for l in casal.pedir("flavio", "GET", "/api/lancamentos").json()
        if l["id"] == compra["id"]
    ]
    return lida["fatura_mes"]


def test_fechamento_que_escorregou_por_feriado_traz_as_compras_para_a_fatura(
    casal: Casal, hoje_10_04
):
    cartao = novo_cartao(casal)["id"]
    antes = comprar(casal, cartao, "2026-04-20")
    no_fechamento = comprar(casal, cartao, "2026-04-25")
    depois = comprar(casal, cartao, "2026-04-28")

    editada = casal.pedir(
        "esposa",
        "PATCH",
        f"/api/cartoes/{cartao}/faturas/2026-04-01",
        json={"fechamento": "2026-04-27", "vencimento": "2026-05-06"},
    )

    assert editada.status_code == 200, editada.text
    assert editada.json()["fechamento"] == "2026-04-27"
    assert faturas_de(casal, cartao) == [
        ("2026-04-01", "2026-04-27", "2026-05-06", "aberta"),
        ("2026-05-01", "2026-05-25", "2026-06-05", "aberta"),
    ]
    assert [fatura_de(casal, c) for c in (antes, no_fechamento, depois)] == [
        "2026-04-01",
        "2026-04-01",
        "2026-05-01",
    ]


def test_editar_a_fatura_que_ainda_nao_nasceu_cria_ela_com_as_datas_pedidas(
    casal: Casal, hoje_10_04
):
    cartao = novo_cartao(casal)["id"]

    casal.pedir(
        "flavio",
        "PATCH",
        f"/api/cartoes/{cartao}/faturas/2026-06-01",
        json={"fechamento": "2026-06-26"},
    )
    compra = comprar(casal, cartao, "2026-06-25")

    assert faturas_de(casal, cartao) == [("2026-06-01", "2026-06-26", "2026-07-05", "aberta")]
    assert compra["fatura_mes"] == "2026-06-01"


def test_fatura_recusa_vencimento_antes_do_fechamento(casal: Casal, hoje_10_04):
    cartao = novo_cartao(casal)["id"]

    resposta = casal.pedir(
        "flavio",
        "PATCH",
        f"/api/cartoes/{cartao}/faturas/2026-04-01",
        json={"vencimento": "2026-04-20"},
    )

    assert resposta.status_code == 422


def test_mudar_o_dia_padrao_redistribui_so_as_faturas_abertas_e_futuras(casal: Casal, hoje_10_04):
    cartao = novo_cartao(casal)["id"]
    fechada = comprar(casal, cartao, "2026-03-20")  # março, fechou em 25/03
    cedo = comprar(casal, cartao, "2026-04-05")  # abril, aberta
    tarde = comprar(casal, cartao, "2026-04-20")  # abril, aberta
    a_mao = comprar(casal, cartao, "2026-04-08")  # o banco lançou só em maio
    casal.pedir(
        "flavio",
        "PATCH",
        f"/api/lancamentos/{a_mao['id']}",
        json={"versao": 1, "fatura_mes": "2026-05-01"},
    )
    futura = comprar(casal, cartao, "2026-04-30")  # maio

    mudou = casal.pedir(
        "esposa",
        "PUT",
        f"/api/cartoes/{cartao}",
        json={"nome": "Nubank", "dia_fechamento": 15, "dia_vencimento": 5},
    )

    assert mudou.status_code == 200, mudou.text
    assert faturas_de(casal, cartao) == [
        ("2026-03-01", "2026-03-25", "2026-04-05", "fechada"),  # fatura fechada nunca muda
        ("2026-04-01", "2026-04-15", "2026-05-05", "aberta"),
        ("2026-05-01", "2026-05-15", "2026-06-05", "aberta"),
    ]
    assert [fatura_de(casal, c) for c in (fechada, cedo, tarde, a_mao, futura)] == [
        "2026-03-01",
        "2026-04-01",
        "2026-05-01",  # 20/04 já passou do novo fechamento
        "2026-05-01",  # a troca à mão fica
        "2026-05-01",
    ]


def test_compra_redistribuida_conta_como_mudanca_do_outro_lado(casal: Casal, hoje_10_04):
    # A mudança do app sobe a versão: quem trocou a fatura sobre a versão antiga vê o conflito,
    # com a origem dela (ADR 0011).
    cartao = novo_cartao(casal)["id"]
    compra = comprar(casal, cartao, "2026-04-20")
    casal.pedir(
        "esposa",
        "PUT",
        f"/api/cartoes/{cartao}",
        json={"nome": "Nubank", "dia_fechamento": 15, "dia_vencimento": 5},
    )

    trocada = casal.pedir(
        "flavio",
        "PATCH",
        f"/api/lancamentos/{compra['id']}",
        json={"versao": 1, "fatura_mes": "2026-06-01"},
    )
    descrita = casal.pedir(
        "flavio",
        "PATCH",
        f"/api/lancamentos/{compra['id']}",
        json={"versao": 1, "descricao": "Feira"},
    )

    assert trocada.status_code == 409
    [campo] = trocada.json()["campos"]
    assert (campo["campo"], campo["origem"]) == ("fatura_mes", "datas do cartão Nubank")
    assert descrita.status_code == 200
    assert (descrita.json()["versao"], descrita.json()["fatura_mes"]) == (3, "2026-05-01")


def test_confirmar_a_compra_prevista_com_outra_data_escolhe_a_fatura_de_novo(
    casal: Casal, hoje_10_04
):
    cartao = novo_cartao(casal)["id"]
    prevista = comprar(casal, cartao, "2026-04-30")

    confirmada = casal.pedir(
        "flavio",
        "POST",
        f"/api/lancamentos/{prevista['id']}/confirmar",
        json={"data": "2026-04-12"},
    ).json()

    assert (prevista["situacao"], prevista["fatura_mes"]) == ("previsto", "2026-05-01")
    assert (confirmada["situacao"], confirmada["fatura_mes"]) == ("realizado", "2026-04-01")


def test_compra_no_cartao_arquivado_pela_fila_fica_recusada_com_o_motivo(casal: Casal):
    cartao = novo_cartao(casal)
    casal.pedir("flavio", "PUT", f"/api/cartoes/{cartao['id']}", json=cartao | {"arquivado": True})

    resposta = casal.pedir(
        "esposa",
        "POST",
        "/api/lancamentos/lote",
        json={
            "acoes": [
                {"acao": "criar", "lancamento": lancamento(cartao["id"], [casal.categoria()])}
            ]
        },
    )

    assert resposta.json()["resultados"] == [
        {
            "resultado": "recusada",
            "motivo": "cartão arquivado",
            "lancamento": None,
            "campos": None,
            "exclusao": None,
        }
    ]


def test_troca_a_mao_recusa_fatura_que_fechou_antes_da_compra(casal: Casal):
    cartao = novo_cartao(casal)["id"]

    resposta = casal.pedir(
        "flavio",
        "POST",
        "/api/lancamentos",
        json=lancamento(cartao, [casal.categoria()], data="2026-04-20", fatura_mes="2026-03-01"),
    )

    assert resposta.status_code == 422
    assert resposta.json()["detail"] == "a fatura escolhida fechou antes da compra"


def test_fechamento_editado_fica_entre_o_da_fatura_anterior_e_o_da_seguinte(
    casal: Casal, hoje_10_04
):
    cartao = novo_cartao(casal)["id"]

    for fechamento in ["2026-05-25", "2026-03-25"]:
        resposta = casal.pedir(
            "flavio",
            "PATCH",
            f"/api/cartoes/{cartao}/faturas/2026-04-01",
            json={"fechamento": fechamento, "vencimento": "2026-06-30"},
        )
        assert resposta.status_code == 422, fechamento


def test_adicional_de_titular_arquivado_recusa_compra_nova(casal: Casal):
    titular = novo_cartao(casal)
    adicional = casal.pedir(
        "esposa", "POST", "/api/cartoes", json={"nome": "Adicional", "titular_id": titular["id"]}
    ).json()["id"]
    casal.pedir(
        "flavio", "PUT", f"/api/cartoes/{titular['id']}", json=titular | {"arquivado": True}
    )

    resposta = casal.pedir(
        "esposa", "POST", "/api/lancamentos", json=lancamento(adicional, [casal.categoria()])
    )

    assert resposta.status_code == 422
    assert resposta.json()["detail"] == "cartão arquivado"


def test_mesma_compra_no_mesmo_cartao_pelos_dois_parece_repetida(casal: Casal):
    cartao = novo_cartao(casal)["id"]
    mercado = casal.categoria()
    do_flavio = casal.pedir(
        "flavio", "POST", "/api/lancamentos", json=lancamento(cartao, [mercado], data="2026-04-02")
    ).json()

    da_esposa = casal.pedir(
        "esposa", "POST", "/api/lancamentos", json=lancamento(cartao, [mercado], data="2026-04-03")
    ).json()

    assert da_esposa["parece_repetido_de"] == do_flavio["id"]
