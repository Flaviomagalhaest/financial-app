"""Alcance da mudança na parcela: só esta, esta e as próximas, todas (ticket 136)."""

from datetime import date

import pytest

from app import lancamentos
from tests.conftest import Casal
from tests.test_parcelamentos import cartao, criar_geladeira, parcelas

HOJE = date(2026, 10, 28)


@pytest.fixture(autouse=True)
def hoje_fixo(monkeypatch: pytest.MonkeyPatch) -> None:
    """Hoje é 28/10/2026 em São Paulo."""
    monkeypatch.setattr(lancamentos, "hoje", lambda: HOJE)


def mudar_parcela(casal: Casal, parcela: dict, alcance: str, quem: str = "flavio", **campos):
    return casal.pedir(
        quem,
        "PATCH",
        f"/api/parcelas/{parcela['id']}",
        json={"versao": parcela["versao"], "alcance": alcance} | campos,
    )


def editar_so_nela(casal: Casal, parcela: dict, **campos) -> dict:
    """A edição comum do lançamento: muda a parcela só nela."""
    resposta = casal.pedir(
        "flavio",
        "PATCH",
        f"/api/lancamentos/{parcela['id']}",
        json={"versao": parcela["versao"]} | campos,
    )
    assert resposta.status_code == 200
    return resposta.json()


def test_esta_e_as_proximas_muda_a_descricao_daqui_para_frente_sem_tocar_a_alterada_a_mao(
    casal: Casal,
):
    novo = criar_geladeira(casal, casal.conta(), data="2026-11-10", parcelas=4)
    [_, segunda, _, quarta] = parcelas(casal, novo["id"])
    editar_so_nela(casal, quarta, descricao="Geladeira, última")

    resposta = mudar_parcela(casal, segunda, "esta_e_as_proximas", descricao="Geladeira nova")

    assert resposta.status_code == 200
    assert resposta.json()["parcelas_mantidas"] == 1
    assert resposta.json()["lancamento"]["descricao"] == "Geladeira nova"
    assert [(l["descricao"], l["alterada_a_mao"]) for l in parcelas(casal, novo["id"])] == [
        ("Geladeria", False),
        ("Geladeira nova", False),
        ("Geladeira nova", False),
        ("Geladeira, última", True),
    ]
    # O parcelamento passa a ter a descrição nova: as parcelas que ainda vierem nascem com ela.
    [regra] = [
        p
        for p in casal.pedir("flavio", "GET", "/api/parcelamentos").json()
        if p["id"] == novo["id"]
    ]
    assert regra["descricao"] == "Geladeira nova"


def valores(casal: Casal, id: str) -> list[tuple]:
    return [
        (l["parcela"], l["valor_centavos"], l["data"], l["situacao"], l["alterada_a_mao"])
        for l in parcelas(casal, id)
    ]


def test_todas_muda_o_valor_de_todas_e_avisa_antes_de_mudar_a_realizada(casal: Casal):
    # Lançada em 10/10 com a 1ª nesse dia: hoje (28/10) ela é realizada, as outras, previstas.
    novo = criar_geladeira(
        casal,
        casal.conta(),
        lancada_em="2026-10-10",
        data="2026-10-10",
        automatico=True,
        parcelas=4,
        valor_total_centavos=40000,
    )
    [_, segunda, terceira, _] = parcelas(casal, novo["id"])
    editar_so_nela(casal, terceira, valor_centavos=9000)
    segunda = parcelas(casal, novo["id"])[1]

    aviso = mudar_parcela(casal, segunda, "todas", valor_centavos=12000)

    assert aviso.status_code == 409
    assert [
        (p["parcela"], p["valor_centavos"], p["valor_novo_centavos"])
        for p in aviso.json()["parcelas"]
    ] == [(1, 10000, 12000)]
    assert [v[1] for v in valores(casal, novo["id"])] == [10000, 10000, 9000, 10000]

    resposta = mudar_parcela(
        casal, segunda, "todas", valor_centavos=12000, confirmar_realizadas=True
    )

    assert resposta.status_code == 200
    assert resposta.json()["parcelas_mantidas"] == 1
    assert valores(casal, novo["id"]) == [
        (1, 12000, "2026-10-10", "realizado", False),
        (2, 12000, "2026-11-10", "previsto", False),
        (3, 9000, "2026-12-10", "previsto", True),
        (4, 12000, "2027-01-10", "previsto", False),
    ]
    # O parcelamento passa a valer o valor da parcela vezes o número delas.
    [regra] = [
        p
        for p in casal.pedir("flavio", "GET", "/api/parcelamentos").json()
        if p["id"] == novo["id"]
    ]
    assert regra["valor_total_centavos"] == 48000


def test_esta_e_as_proximas_muda_valor_e_dia_do_boleto_daqui_para_frente_a_mao_em_cada_uma(
    casal: Casal,
):
    novo = criar_geladeira(
        casal, casal.conta(), data="2026-11-10", parcelas=4, valor_total_centavos=40000
    )
    [_, segunda, *_] = parcelas(casal, novo["id"])

    resposta = mudar_parcela(
        casal, segunda, "esta_e_as_proximas", valor_centavos=11000, data="2026-12-15"
    )

    assert resposta.status_code == 200
    assert resposta.json()["parcelas_mantidas"] == 0
    # O parcelamento tem um valor e uma data só: daqui para frente, cada parcela fica à mão.
    assert valores(casal, novo["id"]) == [
        (1, 10000, "2026-11-10", "previsto", False),
        (2, 11000, "2026-12-15", "previsto", True),
        (3, 11000, "2027-01-15", "previsto", True),
        (4, 11000, "2027-02-15", "previsto", True),
    ]
    # A correção do parcelamento depois não as desfaz.
    assert (
        casal.pedir(
            "flavio",
            "PATCH",
            f"/api/parcelamentos/{novo['id']}",
            json={"valor_total_centavos": 80000},
        ).json()["parcelas_mantidas"]
        == 3
    )
    assert [v[1] for v in valores(casal, novo["id"])] == [20000, 11000, 11000, 11000]


def test_so_esta_muda_so_a_parcela_e_a_deixa_alterada_a_mao_no_campo(casal: Casal):
    novo = criar_geladeira(casal, casal.conta(), data="2026-11-10", parcelas=3)
    [primeira, *_] = parcelas(casal, novo["id"])

    resposta = mudar_parcela(casal, primeira, "so_esta", pessoa="esposa")

    assert resposta.status_code == 200
    assert resposta.json()["parcelas_mantidas"] == 0
    assert [(l["pessoa"], l["alterada_a_mao"]) for l in parcelas(casal, novo["id"])] == [
        ("esposa", True),
        (None, False),
        (None, False),
    ]
    # A correção da pessoa no parcelamento a preserva.
    corrigido = casal.pedir(
        "flavio", "PATCH", f"/api/parcelamentos/{novo['id']}", json={"pessoa": "flavio"}
    )
    assert corrigido.json()["parcelas_mantidas"] == 1
    assert [l["pessoa"] for l in parcelas(casal, novo["id"])] == ["esposa", "flavio", "flavio"]


def test_todas_leva_a_descricao_mudada_a_mao_nesta_e_a_conta_a_todas(casal: Casal):
    nubank, inter = cartao(casal), cartao(casal, nome="Inter")
    novo = criar_geladeira(casal, nubank, data="2026-11-10", parcelas=3)
    [_, segunda, _] = parcelas(casal, novo["id"])
    segunda = editar_so_nela(casal, segunda, descricao="Geladeira, a do meio")

    resposta = mudar_parcela(casal, segunda, "todas", descricao="Geladeira", conta_id=inter)

    assert resposta.status_code == 200
    # A parcela mudada segue a descrição nova, mesmo tendo sido mudada à mão antes.
    assert resposta.json()["parcelas_mantidas"] == 0
    depois = parcelas(casal, novo["id"])
    assert [(l["descricao"], l["conta_id"]) for l in depois] == [("Geladeira", inter)] * 3
    # Compra em 10/11, antes do fechamento: cada parcela cai uma fatura depois da outra.
    assert [l["fatura_mes"] for l in depois] == ["2026-11-01", "2026-12-01", "2027-01-01"]


def test_mudanca_com_alcance_recusada(casal: Casal):
    conta = casal.conta()
    novo = criar_geladeira(casal, conta, data="2026-11-10", parcelas=3)
    [primeira, *_] = parcelas(casal, novo["id"])
    editar_so_nela(casal, primeira, descricao="Outra")

    # Sobre a versão de antes, o campo que mudou depois recusa o pedido inteiro.
    velha = mudar_parcela(casal, primeira, "todas", descricao="Mais outra", quem="esposa")
    assert velha.status_code == 422
    assert "descricao" in velha.json()["detail"]
    avulso = casal.pedir(
        "flavio",
        "POST",
        "/api/lancamentos",
        json={
            "id": "00000000-0000-4000-8000-000000000136",
            "tipo": "despesa",
            "valor_centavos": 100,
            "data": "2026-10-28",
            "conta_id": conta,
            "categoria_ids": primeira["categoria_ids"],
        },
    ).json()
    assert mudar_parcela(casal, avulso, "todas", descricao="x").status_code == 422
    assert (
        mudar_parcela(casal, parcelas(casal, novo["id"])[1], "todas", tipo="receita").status_code
        == 422
    )
    assert [l["descricao"] for l in parcelas(casal, novo["id"])] == [
        "Outra",
        "Geladeria",
        "Geladeria",
    ]


def test_so_conta_como_mantida_a_parcela_do_alcance_no_campo_pedido(casal: Casal):
    novo = criar_geladeira(casal, casal.conta(), data="2026-11-10", parcelas=4)
    [primeira, _, terceira, _] = parcelas(casal, novo["id"])
    # O valor da 1ª, mudado à mão, não é o que o pedido muda, e ela está fora do alcance.
    editar_so_nela(casal, primeira, valor_centavos=1234)

    resposta = mudar_parcela(casal, terceira, "esta_e_as_proximas", descricao="Geladeira")

    assert resposta.json()["parcelas_mantidas"] == 0
    corrigido = casal.pedir(
        "flavio", "PATCH", f"/api/parcelamentos/{novo['id']}", json={"descricao": "Geladeira"}
    )
    assert corrigido.json()["parcelas_mantidas"] == 0


def test_encolher_tira_a_parcela_que_so_teve_a_classificacao_mudada_a_mao(casal: Casal):
    novo = criar_geladeira(casal, casal.conta(), data="2026-11-10", parcelas=4)
    quarta = parcelas(casal, novo["id"])[3]
    editar_so_nela(casal, quarta, tags=["extra"])

    resposta = casal.pedir(
        "flavio", "PATCH", f"/api/parcelamentos/{novo['id']}", json={"parcelas": 3}
    )

    assert resposta.status_code == 200
    assert [l["parcela"] for l in parcelas(casal, novo["id"])] == [1, 2, 3]


def um_lote_por_parcela(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cada transação muda uma parcela só: o parcelamento curto passa por vários lotes, como o de
    perto de 80 parcelas."""
    from app import parcelamentos

    monkeypatch.setattr(parcelamentos, "parcelas_por_lote", lambda regra: 1)


def interromper_depois_do_primeiro_lote(monkeypatch: pytest.MonkeyPatch) -> None:
    """O pedido grava a parcela mudada e o primeiro lote e cai antes dos seguintes."""
    from app import mudanca_na_parcela

    def cai(*_):
        raise RuntimeError("a Lambda caiu")

    monkeypatch.setattr(mudanca_na_parcela, "_mudar_um_lote", cai)


def test_a_tarefa_diaria_termina_a_mudanca_parcela_a_parcela_que_parou_no_meio(
    casal: Casal, monkeypatch: pytest.MonkeyPatch
):
    from app.tarefa_diaria import fazer_tarefa_diaria

    um_lote_por_parcela(monkeypatch)
    novo = criar_geladeira(
        casal, casal.conta(), data="2026-11-10", parcelas=4, valor_total_centavos=40000
    )
    [_, segunda, *_] = parcelas(casal, novo["id"])
    with monkeypatch.context() as queda:
        interromper_depois_do_primeiro_lote(queda)
        with pytest.raises(RuntimeError):
            mudar_parcela(
                casal, segunda, "esta_e_as_proximas", valor_centavos=11000, data="2026-12-15"
            )
    assert [v[1] for v in valores(casal, novo["id"])] == [10000, 11000, 11000, 10000]

    feito = fazer_tarefa_diaria(casal.client.app.state.url)

    assert feito["mudancas_na_parcela"] == 1
    assert valores(casal, novo["id"]) == [
        (1, 10000, "2026-11-10", "previsto", False),
        (2, 11000, "2026-12-15", "previsto", True),
        (3, 11000, "2027-01-15", "previsto", True),
        (4, 11000, "2027-02-15", "previsto", True),
    ]
    assert fazer_tarefa_diaria(casal.client.app.state.url)["mudancas_na_parcela"] == 0


def test_fatura_paga_num_lote_seguinte_recusa_a_mudanca_antes_de_gravar(
    casal: Casal, monkeypatch: pytest.MonkeyPatch
):
    from tests.test_contas import nova_conta
    from tests.test_pagamento_de_fatura import pagar

    # Hoje é 10/06: as parcelas caem em março, abril e maio, todas fechadas; só maio foi paga.
    monkeypatch.setattr(lancamentos, "hoje", lambda: date(2026, 6, 10))
    um_lote_por_parcela(monkeypatch)
    nubank = cartao(casal)
    novo = criar_geladeira(casal, nubank, data="2026-03-20", parcelas=3, valor_total_centavos=30000)
    [primeira, *_] = parcelas(casal, novo["id"])
    assert [l["fatura_mes"] for l in parcelas(casal, novo["id"])] == [
        "2026-03-01",
        "2026-04-01",
        "2026-05-01",
    ]
    pago = pagar(
        casal,
        nova_conta(casal)["id"],
        nubank,
        fatura_mes="2026-05-01",
        valor_centavos=10000,
        data="2026-06-05",
    )
    assert pago.status_code == 201, pago.text

    # A 2ª cabe no primeiro lote; a 3ª, da fatura paga, viria no seguinte.
    resposta = mudar_parcela(
        casal,
        primeira,
        "esta_e_as_proximas",
        valor_centavos=12000,
        confirmar_realizadas=True,
    )

    assert resposta.status_code == 422
    assert resposta.json()["detail"] == (
        "a fatura de 05/2026 do Nubank está paga: para mudá-la, use a correção da fatura"
    )
    assert [l["valor_centavos"] for l in parcelas(casal, novo["id"])] == [10000] * 3


def test_esta_e_as_proximas_nao_leva_o_valor_novo_as_de_antes_da_classificacao_pendente(
    casal: Casal, monkeypatch: pytest.MonkeyPatch
):
    from tests.test_parcelamentos import interromper_o_refazer

    novo = criar_geladeira(casal, casal.conta(), data="2026-11-10", parcelas=4)
    with monkeypatch.context() as queda:
        interromper_o_refazer(queda)
        with pytest.raises(RuntimeError):
            casal.pedir(
                "flavio",
                "PATCH",
                f"/api/parcelamentos/{novo['id']}",
                json={"descricao": "Geladeira"},
            )
    # A correção da descrição desde a 1ª ficou pendente no parcelamento.
    terceira = parcelas(casal, novo["id"])[2]
    assert terceira["descricao"] == "Geladeria"

    # O pedido termina antes a correção pendente: a 3ª mudou depois do que o aparelho viu.
    velha = mudar_parcela(casal, terceira, "esta_e_as_proximas", descricao="Geladeira nova")
    assert velha.status_code == 422
    assert "descricao" in velha.json()["detail"]
    resposta = mudar_parcela(
        casal, parcelas(casal, novo["id"])[2], "esta_e_as_proximas", descricao="Geladeira nova"
    )

    assert resposta.status_code == 200
    assert [l["descricao"] for l in parcelas(casal, novo["id"])] == [
        "Geladeira",
        "Geladeira",
        "Geladeira nova",
        "Geladeira nova",
    ]


def test_pagamento_que_passaria_do_valor_num_lote_seguinte_recusa_antes_de_gravar(
    casal: Casal, monkeypatch: pytest.MonkeyPatch
):
    from tests.test_contas import nova_conta
    from tests.test_pagamento_de_fatura import pagar

    # Hoje é 10/06: as parcelas caem em abril, maio e junho; junho está aberta e já recebeu um
    # pagamento de 100,00, o valor da parcela dela.
    monkeypatch.setattr(lancamentos, "hoje", lambda: date(2026, 6, 10))
    um_lote_por_parcela(monkeypatch)
    nubank = cartao(casal)
    novo = criar_geladeira(casal, nubank, data="2026-04-20", parcelas=3, valor_total_centavos=30000)
    [primeira, *_] = parcelas(casal, novo["id"])
    assert [l["fatura_mes"] for l in parcelas(casal, novo["id"])] == [
        "2026-04-01",
        "2026-05-01",
        "2026-06-01",
    ]
    pago = pagar(
        casal,
        nova_conta(casal)["id"],
        nubank,
        fatura_mes="2026-06-01",
        valor_centavos=10000,
        data="2026-06-05",
    )
    assert pago.status_code == 201, pago.text

    # A 3ª, que viria no lote seguinte, deixaria o pagamento de junho acima da fatura.
    resposta = mudar_parcela(
        casal, primeira, "esta_e_as_proximas", valor_centavos=5000, confirmar_realizadas=True
    )

    assert resposta.status_code == 422
    assert resposta.json()["detail"] == "o pagamento passa do valor da fatura"
    assert [l["valor_centavos"] for l in parcelas(casal, novo["id"])] == [10000] * 3


def parcelamento(casal: Casal, id: str) -> dict:
    [lido] = [p for p in casal.pedir("esposa", "GET", "/api/parcelamentos").json() if p["id"] == id]
    return lido


def test_a_recusa_na_tarefa_diaria_fica_no_parcelamento_ate_a_proxima_mudanca(
    casal: Casal, monkeypatch: pytest.MonkeyPatch
):
    from app.tarefa_diaria import fazer_tarefa_diaria
    from tests.test_contas import nova_conta
    from tests.test_pagamento_de_fatura import pagar

    # Hoje é 10/06: as parcelas caem em março, abril e maio, todas fechadas e a pagar.
    monkeypatch.setattr(lancamentos, "hoje", lambda: date(2026, 6, 10))
    um_lote_por_parcela(monkeypatch)
    nubank = cartao(casal)
    novo = criar_geladeira(casal, nubank, data="2026-03-20", parcelas=3, valor_total_centavos=30000)
    [primeira, *_] = parcelas(casal, novo["id"])
    assert parcelamento(casal, novo["id"])["mudanca_recusada"] is None
    with monkeypatch.context() as queda:
        interromper_depois_do_primeiro_lote(queda)
        with pytest.raises(RuntimeError):
            mudar_parcela(
                casal,
                primeira,
                "esta_e_as_proximas",
                valor_centavos=12000,
                confirmar_realizadas=True,
            )
    # Maio é paga entre o pedido que caiu e a tarefa diária.
    pago = pagar(
        casal,
        nova_conta(casal)["id"],
        nubank,
        fatura_mes="2026-05-01",
        valor_centavos=10000,
        data="2026-06-05",
    )
    assert pago.status_code == 201, pago.text

    assert fazer_tarefa_diaria(casal.client.app.state.url)["mudancas_na_parcela"] == 0

    assert [l["valor_centavos"] for l in parcelas(casal, novo["id"])] == [12000, 12000, 10000]
    assert parcelamento(casal, novo["id"])["mudanca_recusada"] == (
        "a fatura de 05/2026 do Nubank está paga: para mudá-la, use a correção da fatura."
        " Da 3ª parcela em diante, as que faltavam mudar ficaram como estavam"
    )

    # A próxima mudança com alcance tira o aviso.
    [primeira, *_] = parcelas(casal, novo["id"])
    resposta = mudar_parcela(casal, primeira, "todas", descricao="Geladeira nova")
    assert resposta.status_code == 200, resposta.text
    assert parcelamento(casal, novo["id"])["mudanca_recusada"] is None
