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

    monkeypatch.setattr(parcelamentos, "parcelas_por_lote", lambda conn, regra: 1)


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


def test_a_parcela_de_fatura_paga_fica_como_esta_na_mudanca_com_alcance(
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

    # A 3ª, da fatura paga, fica como está, como a mudada à mão (ticket 171).
    resposta = mudar_parcela(
        casal,
        primeira,
        "esta_e_as_proximas",
        valor_centavos=12000,
        confirmar_realizadas=True,
    )

    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["parcelas_mantidas"] == 1
    assert [l["valor_centavos"] for l in parcelas(casal, novo["id"])] == [12000, 12000, 10000]


def test_parcela_que_entraria_numa_fatura_paga_num_lote_seguinte_recusa_antes_de_gravar(
    casal: Casal, monkeypatch: pytest.MonkeyPatch
):
    from tests.test_contas import nova_conta
    from tests.test_pagamento_de_fatura import pagar

    # Hoje é 10/06: as parcelas caem em março, abril e maio, todas fechadas; só abril foi paga.
    monkeypatch.setattr(lancamentos, "hoje", lambda: date(2026, 6, 10))
    um_lote_por_parcela(monkeypatch)
    nubank = cartao(casal)
    novo = criar_geladeira(casal, nubank, data="2026-03-20", parcelas=3, valor_total_centavos=30000)
    [primeira, *_] = parcelas(casal, novo["id"])
    pago = pagar(
        casal,
        nova_conta(casal)["id"],
        nubank,
        fatura_mes="2026-04-01",
        valor_centavos=10000,
        data="2026-05-05",
    )
    assert pago.status_code == 201, pago.text

    # Um mês para trás: a 2ª, de abril (paga), fica; a 3ª, no lote seguinte, entraria em abril.
    resposta = mudar_parcela(
        casal, primeira, "esta_e_as_proximas", data="2026-02-20", confirmar_realizadas=True
    )

    assert resposta.status_code == 422
    assert resposta.json()["detail"] == (
        "a fatura de 04/2026 do Nubank está paga: para mudá-la, use a correção da fatura"
    )
    assert [l["fatura_mes"] for l in parcelas(casal, novo["id"])] == [
        "2026-03-01",
        "2026-04-01",
        "2026-05-01",
    ]


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
    from tests.test_cartoes import comprar
    from tests.test_contas import nova_conta
    from tests.test_pagamento_de_fatura import pagar

    # Hoje é 10/06: as parcelas caem em março, abril e maio, todas fechadas e a pagar.
    monkeypatch.setattr(lancamentos, "hoje", lambda: date(2026, 6, 10))
    um_lote_por_parcela(monkeypatch)
    nubank = cartao(casal)
    # Abril tem outra compra, para poder ser paga depois que a 2ª sair dela.
    comprar(casal, nubank, "2026-04-10", valor_centavos=10000)
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
                data="2026-02-20",
                confirmar_realizadas=True,
            )
    # Abril, em que a 3ª entraria, é paga entre o pedido que caiu e a tarefa diária.
    pago = pagar(
        casal,
        nova_conta(casal)["id"],
        nubank,
        fatura_mes="2026-04-01",
        valor_centavos=10000,
        data="2026-06-05",
    )
    assert pago.status_code == 201, pago.text

    assert fazer_tarefa_diaria(casal.client.app.state.url)["mudancas_na_parcela"] == 0

    assert [l["fatura_mes"] for l in parcelas(casal, novo["id"])] == [
        "2026-02-01",
        "2026-03-01",
        "2026-05-01",
    ]
    assert parcelamento(casal, novo["id"])["mudanca_recusada"] == (
        "a fatura de 04/2026 do Nubank está paga: para mudá-la, use a correção da fatura."
        " Da 3ª parcela em diante, as que faltavam mudar ficaram como estavam"
    )

    # A próxima mudança com alcance tira o aviso.
    [primeira, *_] = parcelas(casal, novo["id"])
    resposta = mudar_parcela(casal, primeira, "todas", descricao="Geladeira nova")
    assert resposta.status_code == 200, resposta.text
    assert parcelamento(casal, novo["id"])["mudanca_recusada"] is None


def test_a_recusa_achada_ao_terminar_o_pedido_anterior_fica_no_parcelamento(
    casal: Casal, monkeypatch: pytest.MonkeyPatch
):
    from tests.test_cartoes import comprar
    from tests.test_contas import nova_conta
    from tests.test_pagamento_de_fatura import pagar

    monkeypatch.setattr(lancamentos, "hoje", lambda: date(2026, 6, 10))
    um_lote_por_parcela(monkeypatch)
    nubank = cartao(casal)
    # Abril tem outra compra, para poder ser paga depois que a 2ª sair dela.
    comprar(casal, nubank, "2026-04-10", valor_centavos=10000)
    novo = criar_geladeira(casal, nubank, data="2026-03-20", parcelas=3, valor_total_centavos=30000)
    [primeira, *_] = parcelas(casal, novo["id"])
    with monkeypatch.context() as queda:
        interromper_depois_do_primeiro_lote(queda)
        with pytest.raises(RuntimeError):
            mudar_parcela(
                casal,
                primeira,
                "esta_e_as_proximas",
                data="2026-02-20",
                confirmar_realizadas=True,
            )
    pago = pagar(
        casal,
        nova_conta(casal)["id"],
        nubank,
        fatura_mes="2026-04-01",
        valor_centavos=10000,
        data="2026-06-05",
    )
    assert pago.status_code == 201, pago.text

    # O pedido seguinte, de outro campo, termina antes o anterior e acha a recusa: ela fica.
    [primeira, *_] = parcelas(casal, novo["id"])
    resposta = mudar_parcela(casal, primeira, "todas", descricao="Geladeira nova")

    assert resposta.status_code == 200, resposta.text
    assert [l["fatura_mes"] for l in parcelas(casal, novo["id"])] == [
        "2026-02-01",
        "2026-03-01",
        "2026-05-01",
    ]
    assert parcelamento(casal, novo["id"])["mudanca_recusada"] == (
        "a fatura de 04/2026 do Nubank está paga: para mudá-la, use a correção da fatura."
        " Da 3ª parcela em diante, as que faltavam mudar ficaram como estavam"
    )


def test_a_parcela_que_faria_nascer_uma_fatura_tirando_o_saldo_da_seguinte_recusa_antes_de_gravar(
    casal: Casal, monkeypatch: pytest.MonkeyPatch
):
    from tests.test_cartoes import comprar
    from tests.test_contas import nova_conta
    from tests.test_pagamento_de_fatura import pagar

    # Hoje é 10/06. No Itaú, abril está paga com 60,00 faltando, que passam a junho (aberta, sem
    # fatura em maio); junho tem 100,00 de compras e recebeu os 160,00 que deve.
    monkeypatch.setattr(lancamentos, "hoje", lambda: date(2026, 6, 10))
    um_lote_por_parcela(monkeypatch)
    conta = nova_conta(casal)["id"]
    nubank, itau = cartao(casal), cartao(casal, nome="Itaú")
    comprar(casal, itau, "2026-04-20", valor_centavos=10000)
    comprar(casal, itau, "2026-06-01", valor_centavos=10000)
    abril = pagar(
        casal, conta, itau, fatura_mes="2026-04-01", valor_centavos=4000, data="2026-05-05"
    )
    junho = pagar(
        casal, conta, itau, fatura_mes="2026-06-01", valor_centavos=16000, data="2026-06-05"
    )
    assert abril.status_code == 201, abril.text
    assert junho.status_code == 201, junho.text
    # A geladeira do Nubank cai de março a junho; a 2ª foi para a conta à mão e fica nela.
    novo = criar_geladeira(casal, nubank, data="2026-03-20", parcelas=4, valor_total_centavos=4000)
    [_, segunda, _, _] = parcelas(casal, novo["id"])
    editar_so_nela(casal, segunda, conta_id=conta)

    # A 4ª vai para junho e a 1ª faz nascer março, no primeiro lote; a 3ª, no seguinte, faria
    # nascer maio, que levaria os 60,00 de abril e deixaria junho devendo menos que o pago.
    resposta = mudar_parcela(
        casal,
        parcelas(casal, novo["id"])[3],
        "todas",
        conta_id=itau,
        confirmar_realizadas=True,
    )

    assert resposta.status_code == 422, resposta.text
    assert resposta.json()["detail"] == "o pagamento passa do valor da fatura"
    assert [l["conta_id"] for l in parcelas(casal, novo["id"])] == [nubank, conta, nubank, nubank]


def test_o_cartao_reemitido_em_todas_vai_para_o_parcelamento_e_a_parcela_nova_nasce_nele(
    casal: Casal,
):
    antigo, reemitido = cartao(casal), cartao(casal, nome="Nubank novo")
    novo = criar_geladeira(casal, antigo, data="2026-11-10", parcelas=3)
    [_, segunda, _] = parcelas(casal, novo["id"])

    resposta = mudar_parcela(casal, segunda, "todas", conta_id=reemitido)

    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["parcelas_mantidas"] == 0
    assert parcelamento(casal, novo["id"])["conta_id"] == reemitido
    # A correção seguinte cresce o parcelamento: a parcela nova nasce no cartão novo, e as de
    # antes não aparecem como mudadas à mão.
    corrigido = casal.pedir(
        "flavio", "PATCH", f"/api/parcelamentos/{novo['id']}", json={"parcelas": 4}
    )
    assert corrigido.status_code == 200, corrigido.text
    depois = parcelas(casal, novo["id"])
    assert [(l["conta_id"], l["alterada_a_mao"]) for l in depois] == [(reemitido, False)] * 4
    assert [l["fatura_mes"] for l in depois] == [
        "2026-11-01",
        "2026-12-01",
        "2027-01-01",
        "2027-02-01",
    ]


def test_a_troca_de_cartao_para_conta_em_todas_segue_a_mao_em_cada_parcela(casal: Casal):
    nubank, conta = cartao(casal), casal.conta()
    novo = criar_geladeira(casal, nubank, data="2026-11-10", parcelas=3)
    [_, segunda, _] = parcelas(casal, novo["id"])

    resposta = mudar_parcela(casal, segunda, "todas", conta_id=conta)

    assert resposta.status_code == 200, resposta.text
    # O parcelamento fica no cartão, que manda as datas; as parcelas vão para a conta à mão.
    assert parcelamento(casal, novo["id"])["conta_id"] == nubank
    depois = parcelas(casal, novo["id"])
    assert [(l["conta_id"], l["alterada_a_mao"]) for l in depois] == [(conta, True)] * 3
    assert [l["fatura_mes"] for l in depois] == [None] * 3


def test_esta_e_as_proximas_leva_o_cartao_novo_a_mao_sem_mudar_o_parcelamento(casal: Casal):
    antigo, reemitido = cartao(casal), cartao(casal, nome="Nubank novo")
    novo = criar_geladeira(casal, antigo, data="2026-11-10", parcelas=3)
    [_, segunda, _] = parcelas(casal, novo["id"])

    resposta = mudar_parcela(casal, segunda, "esta_e_as_proximas", conta_id=reemitido)

    assert resposta.status_code == 200, resposta.text
    assert parcelamento(casal, novo["id"])["conta_id"] == antigo
    assert [(l["conta_id"], l["alterada_a_mao"]) for l in parcelas(casal, novo["id"])] == [
        (antigo, False),
        (reemitido, True),
        (reemitido, True),
    ]


def test_o_cartao_reemitido_em_todas_mantem_a_parcela_de_fatura_paga_e_a_de_conta_mudada_a_mao(
    casal: Casal, monkeypatch: pytest.MonkeyPatch
):
    from tests.test_contas import nova_conta
    from tests.test_pagamento_de_fatura import pagar

    # Hoje é 10/06: as parcelas caem de março a junho; maio foi paga, e a 2ª foi para o Itaú.
    monkeypatch.setattr(lancamentos, "hoje", lambda: date(2026, 6, 10))
    um_lote_por_parcela(monkeypatch)
    antigo, reemitido, itau = (
        cartao(casal),
        cartao(casal, nome="Nubank novo"),
        cartao(casal, nome="Itaú"),
    )
    novo = criar_geladeira(casal, antigo, data="2026-03-20", parcelas=4, valor_total_centavos=40000)
    pago = pagar(
        casal,
        nova_conta(casal)["id"],
        antigo,
        fatura_mes="2026-05-01",
        valor_centavos=10000,
        data="2026-06-05",
    )
    assert pago.status_code == 201, pago.text
    editar_so_nela(casal, parcelas(casal, novo["id"])[1], conta_id=itau)

    resposta = mudar_parcela(
        casal,
        parcelas(casal, novo["id"])[3],
        "todas",
        conta_id=reemitido,
        confirmar_realizadas=True,
    )

    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["parcelas_mantidas"] == 2
    assert parcelamento(casal, novo["id"])["conta_id"] == reemitido
    assert [(l["conta_id"], l["alterada_a_mao"]) for l in parcelas(casal, novo["id"])] == [
        (reemitido, False),
        (itau, True),
        (antigo, False),
        (reemitido, False),
    ]


def test_a_tarefa_diaria_termina_o_cartao_reemitido_que_parou_no_meio_sem_marcar_as_parcelas(
    casal: Casal, monkeypatch: pytest.MonkeyPatch
):
    from app.tarefa_diaria import fazer_tarefa_diaria

    um_lote_por_parcela(monkeypatch)
    antigo, reemitido = cartao(casal), cartao(casal, nome="Nubank novo")
    novo = criar_geladeira(casal, antigo, data="2026-11-10", parcelas=4)
    [primeira, *_] = parcelas(casal, novo["id"])
    with monkeypatch.context() as queda:
        interromper_depois_do_primeiro_lote(queda)
        with pytest.raises(RuntimeError):
            mudar_parcela(casal, primeira, "todas", conta_id=reemitido)
    # A conta do parcelamento mudou junto com a parcela mudada e o primeiro lote.
    assert parcelamento(casal, novo["id"])["conta_id"] == reemitido
    assert [l["conta_id"] for l in parcelas(casal, novo["id"])] == [
        reemitido,
        reemitido,
        antigo,
        antigo,
    ]

    assert fazer_tarefa_diaria(casal.client.app.state.url)["mudancas_na_parcela"] == 1

    assert [(l["conta_id"], l["alterada_a_mao"]) for l in parcelas(casal, novo["id"])] == [
        (reemitido, False)
    ] * 4


def test_a_correcao_antes_de_terminar_o_cartao_reemitido_poe_cada_parcela_na_fatura_do_cartao_dela(
    casal: Casal, monkeypatch: pytest.MonkeyPatch
):
    um_lote_por_parcela(monkeypatch)
    # O antigo fecha dia 25; o novo, dia 5: a compra de 20/11 cai em novembro num e dezembro no
    # outro.
    antigo = cartao(casal)
    reemitido = cartao(casal, nome="Nubank novo", dia_fechamento=5, dia_vencimento=15)
    novo = criar_geladeira(casal, antigo, data="2026-11-10", parcelas=4)
    [primeira, *_] = parcelas(casal, novo["id"])
    with monkeypatch.context() as queda:
        interromper_depois_do_primeiro_lote(queda)
        with pytest.raises(RuntimeError):
            mudar_parcela(casal, primeira, "todas", conta_id=reemitido)
        # A 3ª e a 4ª ainda estão no cartão antigo quando a correção muda a data.
        corrigido = casal.pedir(
            "flavio", "PATCH", f"/api/parcelamentos/{novo['id']}", json={"data": "2026-11-20"}
        )
    assert corrigido.status_code == 200, corrigido.text

    assert [(l["conta_id"], l["fatura_mes"]) for l in parcelas(casal, novo["id"])] == [
        (reemitido, "2026-12-01"),
        (reemitido, "2027-01-01"),
        (antigo, "2027-01-01"),
        (antigo, "2027-02-01"),
    ]


def _cartoes_com_fatura_paga_em_fevereiro(casal: Casal, monkeypatch, paga_no: str):
    """O cartão antigo e o reemitido, com a geladeira de 20/03 em 3 parcelas no antigo (março a
    maio) e a fatura de fevereiro paga só no cartão `paga_no` ("antigo" ou "reemitido")."""
    from tests.test_cartoes import comprar
    from tests.test_contas import nova_conta
    from tests.test_pagamento_de_fatura import pagar

    monkeypatch.setattr(lancamentos, "hoje", lambda: date(2026, 6, 10))
    antigo, reemitido = cartao(casal), cartao(casal, nome="Nubank novo")
    com_a_paga = {"antigo": antigo, "reemitido": reemitido}[paga_no]
    comprar(casal, com_a_paga, "2026-02-10", valor_centavos=10000)
    pago = pagar(
        casal,
        nova_conta(casal)["id"],
        com_a_paga,
        fatura_mes="2026-02-01",
        valor_centavos=10000,
        data="2026-03-05",
    )
    assert pago.status_code == 201, pago.text
    novo = criar_geladeira(casal, antigo, data="2026-03-20", parcelas=3, valor_total_centavos=30000)
    return antigo, reemitido, novo


def test_o_cartao_reemitido_com_a_data_nova_em_todas_recusa_antes_de_gravar_pela_paga_do_novo(
    casal: Casal, monkeypatch: pytest.MonkeyPatch
):
    antigo, reemitido, novo = _cartoes_com_fatura_paga_em_fevereiro(
        casal, monkeypatch, paga_no="reemitido"
    )
    antes = parcelas(casal, novo["id"])

    # No fim, a 1ª ficaria no cartão novo em fevereiro, que está paga; no caminho, nem a troca
    # de cartão (com a data de antes) nem a da data (no cartão antigo) passam por ela.
    resposta = mudar_parcela(
        casal, antes[2], "todas", conta_id=reemitido, data="2026-02-20", confirmar_realizadas=True
    )

    assert resposta.status_code == 422, resposta.text
    assert "02/2026" in resposta.json()["detail"]
    assert parcelamento(casal, novo["id"])["conta_id"] == antigo
    assert [(l["conta_id"], l["fatura_mes"]) for l in parcelas(casal, novo["id"])] == [
        (l["conta_id"], l["fatura_mes"]) for l in antes
    ]


def test_o_cartao_reemitido_com_a_data_nova_em_todas_nao_olha_a_paga_do_cartao_antigo(
    casal: Casal, monkeypatch: pytest.MonkeyPatch
):
    _, reemitido, novo = _cartoes_com_fatura_paga_em_fevereiro(casal, monkeypatch, paga_no="antigo")

    # A data nova levaria a 1ª a fevereiro, paga no cartão antigo; mas ela vai para o novo.
    resposta = mudar_parcela(
        casal,
        parcelas(casal, novo["id"])[2],
        "todas",
        conta_id=reemitido,
        data="2026-02-20",
        confirmar_realizadas=True,
    )

    assert resposta.status_code == 200, resposta.text
    assert parcelamento(casal, novo["id"])["conta_id"] == reemitido
    assert [
        (l["conta_id"], l["fatura_mes"], l["alterada_a_mao"]) for l in parcelas(casal, novo["id"])
    ] == [
        (reemitido, "2026-02-01", False),
        (reemitido, "2026-03-01", False),
        (reemitido, "2026-04-01", False),
    ]


def _reemitido_recusado_no_meio(casal: Casal, monkeypatch, parcelas_da_compra: int):
    """A geladeira de 20/03 no cartão antigo (março em diante) vai para o reemitido em "todas",
    um lote por parcela; o pedido cai depois do primeiro lote, maio do reemitido (em que a 3ª
    entraria) é paga, e a tarefa diária para na 3ª. Devolve os cartões, o parcelamento e o
    pagamento."""
    from app.tarefa_diaria import fazer_tarefa_diaria
    from tests.test_cartoes import comprar
    from tests.test_contas import nova_conta
    from tests.test_pagamento_de_fatura import pagar

    monkeypatch.setattr(lancamentos, "hoje", lambda: date(2026, 6, 10))
    um_lote_por_parcela(monkeypatch)
    antigo, reemitido = cartao(casal), cartao(casal, nome="Nubank novo")
    comprar(casal, reemitido, "2026-05-10", valor_centavos=10000)
    novo = criar_geladeira(
        casal,
        antigo,
        data="2026-03-20",
        parcelas=parcelas_da_compra,
        valor_total_centavos=10000 * parcelas_da_compra,
    )
    [primeira, *_] = parcelas(casal, novo["id"])
    with monkeypatch.context() as queda:
        interromper_depois_do_primeiro_lote(queda)
        with pytest.raises(RuntimeError):
            mudar_parcela(casal, primeira, "todas", conta_id=reemitido, confirmar_realizadas=True)
    pago = pagar(
        casal,
        nova_conta(casal)["id"],
        reemitido,
        fatura_mes="2026-05-01",
        valor_centavos=10000,
        data="2026-06-05",
    )
    assert pago.status_code == 201, pago.text
    assert fazer_tarefa_diaria(casal.client.app.state.url)["mudancas_na_parcela"] == 0
    return antigo, reemitido, novo, pago.json()["id"]


def _tirar_o_pagamento(casal: Casal, id: str) -> None:
    """Sem o pagamento, a fatura deixa de estar paga (a API não tira o pagamento da paga: só a
    correção da fatura)."""
    import psycopg

    with psycopg.connect(casal.client.app.state.url, autocommit=True) as conn:
        conn.execute("DELETE FROM transferencias WHERE id = %s", (id,))


def test_o_cartao_reemitido_recusado_no_meio_deixa_as_que_faltavam_no_antigo_e_todas_as_leva(
    casal: Casal, monkeypatch: pytest.MonkeyPatch
):
    antigo, reemitido, novo, pago = _reemitido_recusado_no_meio(casal, monkeypatch, 3)

    # A 3ª fica no cartão antigo, sem a marca de mudada à mão, e a recusa diz isso.
    assert parcelamento(casal, novo["id"])["conta_id"] == reemitido
    assert [(l["conta_id"], l["alterada_a_mao"]) for l in parcelas(casal, novo["id"])] == [
        (reemitido, False),
        (reemitido, False),
        (antigo, False),
    ]
    assert parcelamento(casal, novo["id"])["mudanca_recusada"] == (
        "a fatura de 05/2026 do Nubank novo está paga: para mudá-la, use a correção da fatura."
        " Da 3ª parcela em diante, as que faltavam mudar ficaram no cartão antigo:"
        ' mude a conta de uma delas de novo, em "todas"'
    )

    # Paga, maio recusa de novo, antes de gravar.
    terceira = parcelas(casal, novo["id"])[2]
    de_novo = mudar_parcela(casal, terceira, "todas", conta_id=reemitido)
    assert de_novo.status_code == 422, de_novo.text
    assert parcelas(casal, novo["id"])[2]["conta_id"] == antigo

    # Sem o pagamento, a 3ª, mudada de novo em "todas", vai para o cartão do parcelamento sem a
    # marca.
    _tirar_o_pagamento(casal, pago)
    resposta = mudar_parcela(casal, terceira, "todas", conta_id=reemitido)

    assert resposta.status_code == 200, resposta.text
    assert parcelamento(casal, novo["id"])["mudanca_recusada"] is None
    assert [(l["conta_id"], l["alterada_a_mao"]) for l in parcelas(casal, novo["id"])] == [
        (reemitido, False)
    ] * 3


def test_todas_de_novo_com_a_data_nova_confere_as_que_ficaram_no_antigo_ja_no_cartao_novo(
    casal: Casal, monkeypatch: pytest.MonkeyPatch
):
    from tests.test_cartoes import comprar
    from tests.test_contas import nova_conta
    from tests.test_pagamento_de_fatura import pagar

    antigo, reemitido, novo, pago = _reemitido_recusado_no_meio(casal, monkeypatch, 4)
    _tirar_o_pagamento(casal, pago)
    # Abril do cartão antigo, que a 2ª já deixou, recebe outra compra e é paga.
    comprar(casal, antigo, "2026-04-10", valor_centavos=10000)
    pago_no_antigo = pagar(
        casal,
        nova_conta(casal)["id"],
        antigo,
        fatura_mes="2026-04-01",
        valor_centavos=10000,
        data="2026-06-05",
    )
    assert pago_no_antigo.status_code == 201, pago_no_antigo.text

    # A data nova levaria a 4ª a abril: no cartão antigo, paga, mas ela vai para o novo.
    resposta = mudar_parcela(
        casal,
        parcelas(casal, novo["id"])[2],
        "todas",
        conta_id=reemitido,
        data="2026-01-20",
        confirmar_realizadas=True,
    )

    assert resposta.status_code == 200, resposta.text
    assert [
        (l["conta_id"], l["fatura_mes"], l["alterada_a_mao"]) for l in parcelas(casal, novo["id"])
    ] == [
        (reemitido, "2026-01-01", False),
        (reemitido, "2026-02-01", False),
        (reemitido, "2026-03-01", False),
        (reemitido, "2026-04-01", False),
    ]


def test_a_recusa_no_meio_do_proprio_pedido_diz_que_as_que_faltavam_ficaram_no_cartao_antigo(
    casal: Casal, monkeypatch: pytest.MonkeyPatch
):
    from app import mudanca_na_parcela
    from tests.test_cartoes import comprar
    from tests.test_contas import nova_conta
    from tests.test_pagamento_de_fatura import pagar

    monkeypatch.setattr(lancamentos, "hoje", lambda: date(2026, 6, 10))
    um_lote_por_parcela(monkeypatch)
    antigo, reemitido = cartao(casal), cartao(casal, nome="Nubank novo")
    comprar(casal, reemitido, "2026-05-10", valor_centavos=10000)
    pago = pagar(
        casal,
        nova_conta(casal)["id"],
        reemitido,
        fatura_mes="2026-05-01",
        valor_centavos=10000,
        data="2026-06-05",
    )
    assert pago.status_code == 201, pago.text
    novo = criar_geladeira(casal, antigo, data="2026-03-20", parcelas=3, valor_total_centavos=30000)
    # Maio do cartão novo como se fosse paga depois da conferência de antes de gravar, entre o
    # primeiro lote e o seguinte.
    monkeypatch.setattr(mudanca_na_parcela, "_conferir_antes_de_gravar", lambda *_: None)

    resposta = mudar_parcela(
        casal,
        parcelas(casal, novo["id"])[0],
        "todas",
        conta_id=reemitido,
        confirmar_realizadas=True,
    )

    assert resposta.status_code == 422, resposta.text
    assert resposta.json()["detail"] == (
        "a fatura de 05/2026 do Nubank novo está paga: para mudá-la, use a correção da fatura."
        " A parcela, a classificação e as primeiras das outras parcelas mudaram; as demais"
        ' ficaram no cartão antigo: mude a conta de uma delas de novo, em "todas"'
    )
    assert [(l["conta_id"], l["alterada_a_mao"]) for l in parcelas(casal, novo["id"])] == [
        (reemitido, False),
        (reemitido, False),
        (antigo, False),
    ]


def test_o_cartao_reemitido_com_o_valor_novo_em_todas_nao_olha_a_paga_do_cartao_antigo(
    casal: Casal, monkeypatch: pytest.MonkeyPatch
):
    from tests.test_contas import nova_conta
    from tests.test_pagamento_de_fatura import pagar

    # Hoje é 10/06: as parcelas caem de março a maio no cartão antigo, e abril foi paga. O valor
    # novo e o cartão novo vão juntos para as outras; a 2ª, na fatura paga, fica como está.
    monkeypatch.setattr(lancamentos, "hoje", lambda: date(2026, 6, 10))
    antigo, reemitido = cartao(casal), cartao(casal, nome="Nubank novo")
    novo = criar_geladeira(casal, antigo, data="2026-03-20", parcelas=3, valor_total_centavos=30000)
    pago = pagar(
        casal,
        nova_conta(casal)["id"],
        antigo,
        fatura_mes="2026-04-01",
        valor_centavos=10000,
        data="2026-06-05",
    )
    assert pago.status_code == 201, pago.text

    resposta = mudar_parcela(
        casal,
        parcelas(casal, novo["id"])[2],
        "todas",
        conta_id=reemitido,
        valor_centavos=8000,
        confirmar_realizadas=True,
    )

    assert resposta.status_code == 200, resposta.text
    assert [
        (l["conta_id"], l["valor_centavos"], l["alterada_a_mao"])
        for l in parcelas(casal, novo["id"])
    ] == [(reemitido, 8000, False), (antigo, 10000, False), (reemitido, 8000, False)]


def test_simular_o_cartao_novo_nao_usa_savepoint_e_nao_deixa_rastro(
    casal: Casal, monkeypatch: pytest.MonkeyPatch
):
    # O DSQL recusa SAVEPOINT (ticket 203): a simulação da correção não abre transação aninhada.
    import psycopg

    from tests.test_cartoes import comprar
    from tests.test_contas import nova_conta
    from tests.test_pagamento_de_fatura import pagar

    antigo, reemitido, novo, pago = _reemitido_recusado_no_meio(casal, monkeypatch, 4)
    _tirar_o_pagamento(casal, pago)
    comprar(casal, antigo, "2026-04-10", valor_centavos=10000)
    pago_no_antigo = pagar(
        casal,
        nova_conta(casal)["id"],
        antigo,
        fatura_mes="2026-04-01",
        valor_centavos=10000,
        data="2026-06-05",
    )
    assert pago_no_antigo.status_code == 201, pago_no_antigo.text

    def sem_savepoint(*_a, **_k):
        raise psycopg.errors.FeatureNotSupported("unsupported transaction statement: SAVEPOINT")

    monkeypatch.setattr(psycopg.Connection, "transaction", sem_savepoint)
    resposta = mudar_parcela(
        casal,
        parcelas(casal, novo["id"])[2],
        "todas",
        conta_id=reemitido,
        data="2026-01-20",
        confirmar_realizadas=True,
    )

    assert resposta.status_code == 200, resposta.text
    assert [(l["conta_id"], l["fatura_mes"]) for l in parcelas(casal, novo["id"])] == [
        (reemitido, "2026-01-01"),
        (reemitido, "2026-02-01"),
        (reemitido, "2026-03-01"),
        (reemitido, "2026-04-01"),
    ]
