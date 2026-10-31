"""Recorrência: regra que gera previstos a cada N semanas ou N meses (ADR 0004)."""

from datetime import date
from uuid import uuid4

import pytest

from app import lancamentos, recorrencias
from app.tarefa_diaria import fazer_tarefa_diaria
from tests.conftest import Casal

HOJE = date(2026, 10, 28)


@pytest.fixture(autouse=True)
def hoje_fixo(monkeypatch: pytest.MonkeyPatch) -> None:
    """Hoje é 28/10/2026 em São Paulo; o horizonte de 24 meses vai até 28/10/2028."""
    monkeypatch.setattr(lancamentos, "hoje", lambda: HOJE)


def recorrencia(conta: str, categorias: list[str], **campos) -> dict:
    return {
        "id": str(uuid4()),
        "tipo": "despesa",
        "valor_centavos": 18990,
        "tipo_do_valor": "estimado",
        "descricao": "Luz",
        "conta_id": conta,
        "categoria_ids": categorias,
        "inicio": "2026-11-10",
        "a_cada": 1,
        "unidade": "meses",
    } | campos


def gerados(casal: Casal, id: str) -> list[dict]:
    return [
        l
        for l in casal.pedir("esposa", "GET", "/api/lancamentos").json()
        if l["recorrencia_id"] == id
    ][::-1]


def test_recorrencia_mensal_sem_fim_gera_previstos_ate_o_horizonte_com_31_no_ultimo_dia(
    casal: Casal,
):
    conta, aluguel = casal.conta(), casal.categoria("Aluguel")
    nova = recorrencia(conta, [aluguel], descricao="Aluguel", inicio="2026-10-31")

    resposta = casal.pedir("flavio", "POST", "/api/recorrencias", json=nova)

    assert resposta.status_code == 201
    previstos = gerados(casal, nova["id"])
    assert [l["data"] for l in previstos[:6]] == [
        "2026-10-31",
        "2026-11-30",
        "2026-12-31",
        "2027-01-31",
        "2027-02-28",
        "2027-03-31",
    ]
    # Fevereiro de 2028 tem 29 dias; o último antes do horizonte (28/10/2028) é o de setembro.
    assert [l["data"] for l in previstos[-9:-6]] == ["2028-01-31", "2028-02-29", "2028-03-31"]
    assert previstos[-1]["data"] == "2028-09-30"
    assert len(previstos) == 24
    assert {
        (l["situacao"], l["valor_centavos"], l["descricao"], l["conta_id"], l["criado_por"])
        for l in previstos
    } == {("previsto", 18990, "Aluguel", conta, "flavio")}
    assert {tuple(l["categoria_ids"]) for l in previstos} == {(aluguel,)}
    assert [l["ocorrencia"] for l in previstos] == list(range(1, 25))


def test_recorrencia_a_cada_duas_semanas_termina_na_data_de_fim(casal: Casal):
    conta, diarista = casal.conta(), casal.categoria("Diarista")
    nova = recorrencia(conta, [diarista], inicio="2026-11-02", a_cada=2, unidade="semanas")
    nova |= {"ate": "2026-12-28"}

    casal.pedir("flavio", "POST", "/api/recorrencias", json=nova)

    # 28/12 fica a 8 semanas de 02/11: a data de fim entra.
    assert [l["data"] for l in gerados(casal, nova["id"])] == [
        "2026-11-02",
        "2026-11-16",
        "2026-11-30",
        "2026-12-14",
        "2026-12-28",
    ]


def test_recorrencia_por_tres_vezes_para_na_terceira_mesmo_com_horizonte_sobrando(casal: Casal):
    conta, seguro = casal.conta(), casal.categoria("Seguro")
    nova = recorrencia(conta, [seguro], inicio="2026-11-15", a_cada=6, vezes=3)

    casal.pedir("flavio", "POST", "/api/recorrencias", json=nova)

    assert [l["data"] for l in gerados(casal, nova["id"])] == [
        "2026-11-15",
        "2027-05-15",
        "2027-11-15",
    ]


def test_inicio_no_passado_so_lanca_de_hoje_em_diante_e_a_de_hoje_nasce_realizada(
    casal: Casal,
):
    conta, luz = casal.conta(), casal.categoria("Luz")
    nova = recorrencia(conta, [luz], inicio="2026-08-28", vezes=5)

    resposta = casal.pedir("flavio", "POST", "/api/recorrencias", json=nova)

    assert resposta.status_code == 201
    # Agosto e setembro já passaram: não viram lançamento, mas contam nas 5 vezes.
    assert [(l["ocorrencia"], l["data"], l["situacao"]) for l in gerados(casal, nova["id"])] == [
        (3, "2026-10-28", "realizado"),
        (4, "2026-11-28", "previsto"),
        (5, "2026-12-28", "previsto"),
    ]
    assert (resposta.json()["inicio"], resposta.json()["ocorrencia_do_inicio"]) == (
        "2026-08-28",
        1,
    )
    semana = casal.pedir("esposa", "GET", "/api/hoje").json()["contas_da_semana"]
    assert not any(l["atrasado"] for l in semana)
    [saldo] = [c["saldo_centavos"] for c in casal.pedir("flavio", "GET", "/api/contas").json()]
    assert saldo == -18990


def test_enviada_no_dia_seguinte_a_ocorrencia_do_dia_do_lancamento_nasce_realizada(
    casal: Casal,
):
    # Lançada sem internet em 27/10, com a 1ª ocorrência nesse dia; a fila só subiu em 28/10.
    conta, luz = casal.conta(), casal.categoria("Luz")
    nova = recorrencia(conta, [luz], inicio="2026-09-27", dia_do_lancamento="2026-10-27")

    resposta = casal.pedir("flavio", "POST", "/api/recorrencias", json=nova)

    assert resposta.status_code == 201
    assert resposta.json()["dia_do_lancamento"] == "2026-10-27"
    assert [(l["ocorrencia"], l["data"], l["situacao"]) for l in gerados(casal, nova["id"])][
        :2
    ] == [(2, "2026-10-27", "realizado"), (3, "2026-11-27", "previsto")]


def test_o_dia_do_lancamento_conta_no_fim_e_nao_passa_de_hoje(casal: Casal):
    conta, luz = casal.conta(), casal.categoria("Luz")
    ontem = recorrencia(
        conta, [luz], inicio="2026-10-27", ate="2026-10-27", dia_do_lancamento="2026-10-27"
    )
    # O relógio do aparelho adiantado não lança nada antes da hora: vale hoje.
    adiantado = recorrencia(conta, [luz], inicio="2026-10-29", dia_do_lancamento="2026-10-29")

    assert casal.pedir("flavio", "POST", "/api/recorrencias", json=ontem).status_code == 201
    adiantada = casal.pedir("flavio", "POST", "/api/recorrencias", json=adiantado)

    assert [(l["data"], l["situacao"]) for l in gerados(casal, ontem["id"])] == [
        ("2026-10-27", "realizado")
    ]
    assert adiantada.json()["dia_do_lancamento"] == "2026-10-28"
    assert gerados(casal, adiantado["id"])[0]["situacao"] == "previsto"


def test_pelo_lote_da_fila_a_ocorrencia_de_ontem_nasce_realizada(casal: Casal):
    conta, luz = casal.conta(), casal.categoria("Luz")
    nova = recorrencia(conta, [luz], inicio="2026-10-27", vezes=2, dia_do_lancamento="2026-10-27")
    lote = {"acoes": [{"acao": "criar_recorrencia", "recorrencia": nova}]}

    [aceita] = casal.pedir("esposa", "POST", "/api/lancamentos/lote", json=lote).json()[
        "resultados"
    ]

    assert (aceita["resultado"], aceita["recorrencia"]["dia_do_lancamento"]) == (
        "aceita",
        "2026-10-27",
    )
    assert [(l["data"], l["situacao"]) for l in gerados(casal, nova["id"])] == [
        ("2026-10-27", "realizado"),
        ("2026-11-27", "previsto"),
    ]


def test_a_tarefa_diaria_termina_a_geracao_parada_a_partir_do_dia_do_lancamento(
    casal: Casal, database_url: str, monkeypatch: pytest.MonkeyPatch
):
    # O envio gravou a regra em 28/10, mas a geração caiu antes do primeiro lote.
    conta, luz = casal.conta(), casal.categoria("Luz")
    nova = recorrencia(conta, [luz], inicio="2026-10-28", vezes=3)

    def cai(conn, id):
        raise RuntimeError("a Lambda acabou")

    monkeypatch.setattr(recorrencias, "_gerar_um_lote", cai)
    with pytest.raises(RuntimeError):
        casal.pedir("flavio", "POST", "/api/recorrencias", json=nova)
    monkeypatch.undo()
    no_dia(monkeypatch, "2026-10-29")

    fazer_tarefa_diaria(database_url)

    assert [(l["data"], l["situacao"]) for l in gerados(casal, nova["id"])] == [
        ("2026-10-28", "realizado"),
        ("2026-11-28", "previsto"),
        ("2026-12-28", "previsto"),
    ]


def test_mudada_a_regra_a_geracao_nao_volta_ao_dia_do_lancamento(
    casal: Casal, database_url: str, monkeypatch: pytest.MonkeyPatch
):
    # Lançada em 27/10 por 1 vez; em 28/10 o casal a estende para 3 vezes, a partir da 2ª.
    conta, luz = casal.conta(), casal.categoria("Luz")
    nova = recorrencia(
        conta,
        [luz],
        inicio="2026-10-27",
        a_cada=1,
        unidade="semanas",
        vezes=1,
        dia_do_lancamento="2026-10-27",
    )
    casal.pedir("flavio", "POST", "/api/recorrencias", json=nova)
    no_dia(monkeypatch, "2026-11-04")

    resposta = casal.pedir(
        "flavio",
        "PATCH",
        f"/api/recorrencias/{nova['id']}",
        json={"a_partir_da_ocorrencia": 2, "vezes": 3},
    )

    assert resposta.status_code == 200
    # A 2ª (03/11) já tinha passado quando a regra mudou: não vira lançamento.
    assert [(l["data"], l["situacao"]) for l in gerados(casal, nova["id"])] == [
        ("2026-10-27", "realizado"),
        ("2026-11-10", "previsto"),
    ]


def test_automatico_com_inicio_no_passado_nao_realiza_o_que_passou(casal: Casal):
    conta, assinatura = casal.conta(), casal.categoria("Assinaturas")
    nova = recorrencia(
        conta,
        [assinatura],
        descricao="Spotify",
        valor_centavos=2190,
        tipo_do_valor="fixo",
        automatico=True,
        inicio="2026-10-05",
    )
    casal.pedir("flavio", "POST", "/api/recorrencias", json=nova)

    spotify = gerados(casal, nova["id"])
    assert [(l["ocorrencia"], l["data"], l["situacao"], l["automatico"]) for l in spotify[:2]] == [
        (2, "2026-11-05", "previsto", True),
        (3, "2026-12-05", "previsto", True),
    ]
    [saldo] = [c["saldo_centavos"] for c in casal.pedir("flavio", "GET", "/api/contas").json()]
    assert saldo == 0


@pytest.mark.parametrize(
    "fim", [{"ate": "2026-10-27"}, {"inicio": "2026-08-28", "vezes": 2}], ids=["ate", "vezes"]
)
def test_recorrencia_que_termina_antes_de_hoje_e_recusada_sem_gravar(casal: Casal, fim):
    conta, luz = casal.conta(), casal.categoria("Luz")
    nova = recorrencia(conta, [luz], inicio="2026-08-28") | fim

    resposta = casal.pedir("flavio", "POST", "/api/recorrencias", json=nova)

    assert resposta.status_code == 422
    assert resposta.json()["detail"] == "a recorrência termina antes de hoje"
    assert casal.pedir("flavio", "GET", "/api/recorrencias").json() == []


def test_recorrencia_de_valor_estimado_nao_pode_ser_automatica(casal: Casal):
    conta, salario = casal.conta(), casal.categoria("Salário", "receita")
    nova = recorrencia(conta, [salario], tipo="receita", tipo_do_valor="estimado", automatico=True)

    resposta = casal.pedir("flavio", "POST", "/api/recorrencias", json=nova)

    assert resposta.status_code == 422
    assert "valor fixo" in str(resposta.json())
    assert casal.pedir("flavio", "GET", "/api/recorrencias").json() == []


def test_reenviar_a_mesma_recorrencia_devolve_a_gravada_sem_gerar_de_novo(casal: Casal):
    conta, luz = casal.conta(), casal.categoria("Luz")
    nova = recorrencia(
        conta, [luz], tags=["casa nova"], pessoa="esposa", inicio="2026-11-10", vezes=3
    )

    primeira = casal.pedir("flavio", "POST", "/api/recorrencias", json=nova)
    segunda = casal.pedir("flavio", "POST", "/api/recorrencias", json=nova)

    assert (primeira.status_code, segunda.status_code) == (201, 200)
    assert segunda.json() == primeira.json()
    assert primeira.json() | {"criado_em": None, "alterado_em": None} == nova | {
        "automatico": False,
        "ate": None,
        "item_categoria_id": None,
        "ocorrencia_do_inicio": 1,
        # Sem o dia no pedido, vale o da chegada.
        "dia_do_lancamento": "2026-10-28",
        "criado_por": "flavio",
        "alterado_por": "flavio",
        "criado_em": None,
        "alterado_em": None,
    }
    assert casal.pedir("esposa", "GET", "/api/recorrencias").json() == [primeira.json()]
    previstos = gerados(casal, nova["id"])
    assert len(previstos) == 3
    assert {(tuple(l["tags"]), l["pessoa"]) for l in previstos} == {(("casa nova",), "esposa")}


def test_sem_internet_a_recorrencia_sobe_no_lote_como_um_pedido_so(casal: Casal):
    conta, luz = casal.conta(), casal.categoria("Luz")
    nova = recorrencia(conta, [luz], vezes=3)
    sem_conta = recorrencia(str(uuid4()), [luz], descricao="Água")
    lote = {
        "acoes": [
            {"acao": "criar_recorrencia", "recorrencia": nova},
            {"acao": "criar_recorrencia", "recorrencia": sem_conta},
        ]
    }

    primeiro = casal.pedir("esposa", "POST", "/api/lancamentos/lote", json=lote)
    # A fila repete o lote que ficou sem resposta.
    segundo = casal.pedir("esposa", "POST", "/api/lancamentos/lote", json=lote)

    assert primeiro.status_code == 200
    [aceita, recusada] = primeiro.json()["resultados"]
    assert aceita["resultado"] == "aceita"
    assert aceita["recorrencia"] | {"criado_em": None, "alterado_em": None} == nova | {
        "automatico": False,
        "ate": None,
        "tags": [],
        "pessoa": None,
        "item_categoria_id": None,
        "ocorrencia_do_inicio": 1,
        "dia_do_lancamento": "2026-10-28",
        "criado_por": "esposa",
        "alterado_por": "esposa",
        "criado_em": None,
        "alterado_em": None,
    }
    assert (recusada["resultado"], recusada["motivo"]) == ("recusada", "conta não encontrada")
    assert [r["resultado"] for r in segundo.json()["resultados"]] == ["aceita", "recusada"]
    assert segundo.json()["resultados"][0]["recorrencia"] == aceita["recorrencia"]
    assert [l["data"] for l in gerados(casal, nova["id"])] == [
        "2026-11-10",
        "2026-12-10",
        "2027-01-10",
    ]
    assert len(casal.pedir("esposa", "GET", "/api/lancamentos").json()) == 3


def test_reenviar_a_recorrencia_com_outros_dados_devolve_a_gravada_sem_mudar_nada(casal: Casal):
    # O aparelho não edita a recorrência não enviada (só a descarta), então o mesmo id com outros
    # dados não vem do app: o reenvio é idempotente e quem muda a regra é o PATCH (ticket 86).
    conta, luz = casal.conta(), casal.categoria("Luz")
    nova = recorrencia(conta, [luz], vezes=2)
    casal.pedir("flavio", "POST", "/api/recorrencias", json=nova)
    outra = nova | {"valor_centavos": 99, "vezes": 5}

    resposta = casal.pedir(
        "esposa",
        "POST",
        "/api/lancamentos/lote",
        json={"acoes": [{"acao": "criar_recorrencia", "recorrencia": outra}]},
    )

    [resultado] = resposta.json()["resultados"]
    assert resultado["resultado"] == "aceita"
    assert (resultado["recorrencia"]["valor_centavos"], resultado["recorrencia"]["vezes"]) == (
        18990,
        2,
    )
    assert [l["valor_centavos"] for l in gerados(casal, nova["id"])] == [18990, 18990]


@pytest.mark.parametrize(
    ("mudar", "motivo"),
    [
        (
            lambda casal, conta: {"categoria_ids": [casal.categoria("Salário", "receita")]},
            "categoria de receita",
        ),
        (lambda casal, conta: {"conta_id": str(uuid4())}, "conta não encontrada"),
        (lambda casal, conta: {"pessoa": "vizinho"}, "pessoa não encontrada"),
        (lambda casal, conta: {"ate": "2026-11-01", "vezes": 2}, "não nos dois"),
        (lambda casal, conta: {"ate": "2026-11-01"}, "antes do início"),
        (lambda casal, conta: {"a_cada": 0}, "a_cada"),
    ],
)
def test_recorrencia_com_regra_ou_ligacao_invalida_e_recusada_sem_gravar(
    casal: Casal, mudar, motivo
):
    conta, luz = casal.conta(), casal.categoria("Luz")
    nova = recorrencia(conta, [luz]) | mudar(casal, conta)

    resposta = casal.pedir("flavio", "POST", "/api/recorrencias", json=nova)

    assert resposta.status_code == 422
    assert motivo in str(resposta.json())
    assert casal.pedir("flavio", "GET", "/api/recorrencias").json() == []
    assert casal.pedir("flavio", "GET", "/api/lancamentos").json() == []


def no_dia(monkeypatch: pytest.MonkeyPatch, dia: str) -> None:
    monkeypatch.setattr(lancamentos, "hoje", lambda: date.fromisoformat(dia))


def test_tarefa_diaria_estende_o_horizonte_das_recorrencias(
    casal: Casal, database_url: str, monkeypatch: pytest.MonkeyPatch
):
    conta, luz, seguro = casal.conta(), casal.categoria("Luz"), casal.categoria("Seguro")
    mensal = recorrencia(conta, [luz], inicio="2026-11-10")
    anual = recorrencia(
        conta, [seguro], descricao="Seguro", inicio="2027-02-28", a_cada=12, vezes=3
    )
    casal.pedir("flavio", "POST", "/api/recorrencias", json=mensal)
    casal.pedir("flavio", "POST", "/api/recorrencias", json=anual)
    assert gerados(casal, mensal["id"])[-1]["data"] == "2028-10-10"
    assert [l["data"] for l in gerados(casal, anual["id"])] == ["2027-02-28", "2028-02-28"]

    no_dia(monkeypatch, "2027-03-01")
    fazer_tarefa_diaria(database_url)
    fazer_tarefa_diaria(database_url)

    # Horizonte em 01/03/2029: a luz chega a 10/02/2029 e o seguro, à terceira vez.
    assert gerados(casal, mensal["id"])[-1]["data"] == "2029-02-10"
    assert len(gerados(casal, mensal["id"])) == 28
    assert [l["data"] for l in gerados(casal, anual["id"])] == [
        "2027-02-28",
        "2028-02-28",
        "2029-02-28",
    ]


def test_tarefa_diaria_realiza_o_automatico_na_data_e_deixa_o_estimado_pedindo_confirmacao(
    casal: Casal, database_url: str, monkeypatch: pytest.MonkeyPatch
):
    conta, assinatura = casal.conta(), casal.categoria("Assinaturas")
    spotify = recorrencia(
        conta,
        [assinatura],
        descricao="Spotify",
        valor_centavos=2190,
        tipo_do_valor="fixo",
        automatico=True,
        inicio="2026-11-05",
    )
    luz = recorrencia(conta, [assinatura], inicio="2026-11-05")
    casal.pedir("flavio", "POST", "/api/recorrencias", json=spotify)
    casal.pedir("esposa", "POST", "/api/recorrencias", json=luz)

    no_dia(monkeypatch, "2026-11-06")
    fazer_tarefa_diaria(database_url)

    [spotify_de_novembro, spotify_de_dezembro] = gerados(casal, spotify["id"])[:2]
    assert (spotify_de_novembro["situacao"], spotify_de_novembro["versao"]) == ("realizado", 2)
    assert spotify_de_novembro["alterado_por"] == "flavio"
    assert spotify_de_dezembro["situacao"] == "previsto"
    [luz_de_novembro] = gerados(casal, luz["id"])[:1]
    assert (luz_de_novembro["situacao"], luz_de_novembro["atrasado"]) == ("previsto", True)
    [saldo] = [c["saldo_centavos"] for c in casal.pedir("flavio", "GET", "/api/contas").json()]
    assert saldo == -2190
    # Quem mudou a situação sem internet, sobre a versão de antes, vê que foi a regra.
    resposta = casal.pedir(
        "esposa",
        "PATCH",
        f"/api/lancamentos/{spotify_de_novembro['id']}",
        json={"versao": 1, "situacao": "previsto"},
    )
    assert resposta.status_code == 409
    assert [(c["campo"], c["origem"]) for c in resposta.json()["campos"]] == [
        ("situacao", "a recorrência Spotify")
    ]


def test_tarefa_diaria_nao_traz_de_volta_nem_realiza_o_previsto_excluido(
    casal: Casal, database_url: str, monkeypatch: pytest.MonkeyPatch
):
    conta, assinatura = casal.conta(), casal.categoria("Assinaturas")
    spotify = recorrencia(
        conta, [assinatura], tipo_do_valor="fixo", automatico=True, inicio="2026-11-05", vezes=2
    )
    casal.pedir("flavio", "POST", "/api/recorrencias", json=spotify)
    novembro = gerados(casal, spotify["id"])[0]
    casal.pedir("esposa", "DELETE", f"/api/lancamentos/{novembro['id']}")

    no_dia(monkeypatch, "2026-12-05")
    fazer_tarefa_diaria(database_url)

    assert [(l["data"], l["situacao"]) for l in gerados(casal, spotify["id"])] == [
        ("2026-12-05", "realizado")
    ]


def test_recorrencia_semanal_com_muitas_categorias_e_tags_gera_em_mais_de_uma_transacao(
    casal: Casal,
):
    # 1 lançamento + 5 categorias + 5 tags = 11 linhas por previsto: 90 cabem num lote de 1.000,
    # e 24 meses de semanas são 105.
    conta = casal.conta()
    categorias = [casal.categoria(f"Categoria {n}") for n in range(5)]
    nova = recorrencia(
        conta,
        categorias,
        tags=[f"tag {n}" for n in range(5)],
        inicio="2026-10-29",
        unidade="semanas",
    )

    casal.pedir("flavio", "POST", "/api/recorrencias", json=nova)

    previstos = gerados(casal, nova["id"])
    assert len(previstos) == 105
    assert previstos[-1]["data"] == "2028-10-26"
    assert [l["ocorrencia"] for l in previstos] == list(range(1, 106))


def test_recorrencia_no_cartao_conta_cada_previsto_no_mes_da_fatura(casal: Casal):
    # O Spotify no cartão que fecha no dia 25: o do dia 26 cai na fatura do mês seguinte.
    cartao = casal.pedir(
        "flavio",
        "POST",
        "/api/cartoes",
        json={"nome": "Nubank", "dia_fechamento": 25, "dia_vencimento": 5},
    ).json()["id"]
    nova = recorrencia(
        cartao, [casal.categoria("Assinaturas")], inicio="2026-11-26", vezes=2, descricao="Spotify"
    )

    assert casal.pedir("flavio", "POST", "/api/recorrencias", json=nova).status_code == 201

    assert [(l["data"], l["mes"], l["fatura_mes"]) for l in gerados(casal, nova["id"])] == [
        ("2026-11-26", "2026-12-01", "2026-12-01"),
        ("2026-12-26", "2027-01-01", "2027-01-01"),
    ]


def mudar(casal: Casal, id: str, a_partir_da_ocorrencia: int, **campos):
    return casal.pedir(
        "esposa",
        "PATCH",
        f"/api/recorrencias/{id}",
        json={"a_partir_da_ocorrencia": a_partir_da_ocorrencia} | campos,
    )


def test_mudar_daqui_para_frente_reajusta_os_previstos_e_deixa_o_passado_como_esta(
    casal: Casal, monkeypatch: pytest.MonkeyPatch
):
    conta, luz = casal.conta(), casal.categoria("Luz")
    nova = recorrencia(conta, [luz], inicio="2026-09-10", vezes=6)
    no_dia(monkeypatch, "2026-09-01")
    casal.pedir("flavio", "POST", "/api/recorrencias", json=nova)
    no_dia(monkeypatch, HOJE.isoformat())
    # Setembro e outubro já passaram: o casal confirmou setembro e outubro segue atrasado.
    setembro = gerados(casal, nova["id"])[0]
    casal.pedir(
        "flavio", "POST", f"/api/lancamentos/{setembro['id']}/confirmar", json={"versao": 1}
    )

    resposta = mudar(casal, nova["id"], 3, valor_centavos=21000, descricao="Luz (reajuste)")

    assert resposta.status_code == 200
    assert resposta.json()["valor_centavos"] == 21000
    assert casal.pedir("flavio", "GET", "/api/recorrencias").json() == [resposta.json()]
    assert [
        (l["ocorrencia"], l["situacao"], l["valor_centavos"], l["descricao"])
        for l in gerados(casal, nova["id"])
    ] == [
        (1, "realizado", 18990, "Luz"),
        (2, "previsto", 18990, "Luz"),
        (3, "previsto", 21000, "Luz (reajuste)"),
        (4, "previsto", 21000, "Luz (reajuste)"),
        (5, "previsto", 21000, "Luz (reajuste)"),
        (6, "previsto", 21000, "Luz (reajuste)"),
    ]


def test_previsto_alterado_a_mao_nao_e_sobrescrito_por_mudanca_daqui_para_frente(casal: Casal):
    conta, luz = casal.conta(), casal.categoria("Luz")
    nova = recorrencia(conta, [luz], inicio="2026-11-10", vezes=4)
    casal.pedir("flavio", "POST", "/api/recorrencias", json=nova)
    [_, dezembro, janeiro, _] = gerados(casal, nova["id"])
    # A conta de dezembro vem atípica; a de janeiro só ganha uma tag, o que também é à mão.
    casal.pedir(
        "flavio",
        "PATCH",
        f"/api/lancamentos/{dezembro['id']}",
        json={"versao": 1, "valor_centavos": 35000},
    )
    casal.pedir(
        "flavio", "PATCH", f"/api/lancamentos/{janeiro['id']}", json={"versao": 1, "tags": ["ap"]}
    )

    mudar(casal, nova["id"], 1, valor_centavos=21000)

    assert [(l["valor_centavos"], l["versao"]) for l in gerados(casal, nova["id"])] == [
        (21000, 2),
        (35000, 2),
        (18990, 2),
        (21000, 2),
    ]


def test_mudanca_da_regra_que_colide_com_edicao_sem_internet_vira_conflito_vindo_da_regra(
    casal: Casal,
):
    conta, luz = casal.conta(), casal.categoria("Luz")
    nova = recorrencia(conta, [luz], inicio="2026-11-10", vezes=2)
    casal.pedir("flavio", "POST", "/api/recorrencias", json=nova)
    novembro = gerados(casal, nova["id"])[0]

    mudar(casal, nova["id"], 1, valor_centavos=21000, descricao="Luz nova")

    # A esposa editou sem internet o valor, sobre a versão 1; a regra já tinha reajustado.
    resposta = casal.pedir(
        "esposa",
        "PATCH",
        f"/api/lancamentos/{novembro['id']}",
        json={"versao": 1, "valor_centavos": 20000, "descricao": "Luz do mês"},
    )
    assert resposta.status_code == 409
    assert {(c["campo"], c["origem"], c["alterado_por"]) for c in resposta.json()["campos"]} == {
        ("valor_centavos", "a recorrência Luz nova", "esposa"),
        ("descricao", "a recorrência Luz nova", "esposa"),
    }
    assert resposta.json()["lancamento"]["valor_centavos"] == 21000


def test_encerrar_por_data_tira_os_previstos_depois_dela_e_deixa_o_realizado(
    casal: Casal, database_url: str, monkeypatch: pytest.MonkeyPatch
):
    conta, assinatura = casal.conta(), casal.categoria("Assinaturas")
    nova = recorrencia(conta, [assinatura], descricao="Netflix", inicio="2026-11-10")
    casal.pedir("flavio", "POST", "/api/recorrencias", json=nova)
    fevereiro = gerados(casal, nova["id"])[3]
    # Fevereiro foi mexido à mão e março já foi confirmado: o fim vale para o previsto, não
    # para o que o casal confirmou.
    casal.pedir(
        "flavio",
        "PATCH",
        f"/api/lancamentos/{fevereiro['id']}",
        json={"versao": 1, "valor_centavos": 5000},
    )
    marco = gerados(casal, nova["id"])[4]
    casal.pedir("flavio", "POST", f"/api/lancamentos/{marco['id']}/confirmar", json={})

    resposta = mudar(casal, nova["id"], 3, ate="2027-01-10")

    assert resposta.status_code == 200
    assert (resposta.json()["ate"], resposta.json()["vezes"]) == ("2027-01-10", None)
    assert [(l["data"], l["situacao"]) for l in gerados(casal, nova["id"])] == [
        ("2026-11-10", "previsto"),
        ("2026-12-10", "previsto"),
        ("2027-01-10", "previsto"),
        ("2027-03-10", "realizado"),
    ]
    # A tarefa diária estende o horizonte, mas a regra acabou: nada volta.
    no_dia(monkeypatch, "2027-02-01")
    fazer_tarefa_diaria(database_url)
    assert len(gerados(casal, nova["id"])) == 4


def test_encerrar_por_numero_de_vezes_tira_a_data_de_fim_e_vice_versa(casal: Casal):
    conta, assinatura = casal.conta(), casal.categoria("Assinaturas")
    nova = recorrencia(conta, [assinatura], inicio="2026-11-10", ate="2027-03-10")
    casal.pedir("flavio", "POST", "/api/recorrencias", json=nova)
    assert len(gerados(casal, nova["id"])) == 5

    por_vezes = mudar(casal, nova["id"], 1, vezes=3)

    assert (por_vezes.json()["ate"], por_vezes.json()["vezes"]) == (None, 3)
    assert len(gerados(casal, nova["id"])) == 3
    por_data = mudar(casal, nova["id"], 1, ate="2026-12-31")
    assert (por_data.json()["ate"], por_data.json()["vezes"]) == ("2026-12-31", None)
    assert len(gerados(casal, nova["id"])) == 2


def test_excluir_a_recorrencia_tira_a_regra_e_os_previstos_de_hoje_em_diante(
    casal: Casal, database_url: str, monkeypatch: pytest.MonkeyPatch
):
    conta, assinatura = casal.conta(), casal.categoria("Assinaturas")
    nova = recorrencia(conta, [assinatura], tags=["streaming"], inicio="2026-08-28")
    no_dia(monkeypatch, "2026-08-01")
    casal.pedir("flavio", "POST", "/api/recorrencias", json=nova)
    no_dia(monkeypatch, HOJE.isoformat())
    agosto = gerados(casal, nova["id"])[0]
    casal.pedir("flavio", "POST", f"/api/lancamentos/{agosto['id']}/confirmar", json={})

    resposta = casal.pedir("esposa", "DELETE", f"/api/recorrencias/{nova['id']}")

    assert resposta.status_code == 204
    assert casal.pedir("flavio", "GET", "/api/recorrencias").json() == []
    # O realizado é o que aconteceu; o atrasado só some quando o casal confirmar ou excluir;
    # os de hoje (28/10) em diante saem.
    assert [(l["data"], l["situacao"], l["atrasado"]) for l in gerados(casal, nova["id"])] == [
        ("2026-08-28", "realizado", False),
        ("2026-09-28", "previsto", True),
    ]
    assert casal.pedir("esposa", "DELETE", f"/api/recorrencias/{nova['id']}").status_code == 204
    no_dia(monkeypatch, "2026-12-01")
    fazer_tarefa_diaria(database_url)
    assert len(gerados(casal, nova["id"])) == 2


def test_pular_um_mes_e_excluir_o_previsto_e_ele_nao_volta_por_mudanca_nem_pela_tarefa_diaria(
    casal: Casal, database_url: str, monkeypatch: pytest.MonkeyPatch
):
    conta, luz = casal.conta(), casal.categoria("Luz")
    nova = recorrencia(conta, [luz], inicio="2026-11-10", vezes=3)
    casal.pedir("flavio", "POST", "/api/recorrencias", json=nova)
    dezembro = gerados(casal, nova["id"])[1]
    casal.pedir("esposa", "DELETE", f"/api/lancamentos/{dezembro['id']}")

    mudar(casal, nova["id"], 1, valor_centavos=21000)
    no_dia(monkeypatch, "2026-12-01")
    fazer_tarefa_diaria(database_url)

    assert [(l["ocorrencia"], l["valor_centavos"]) for l in gerados(casal, nova["id"])] == [
        (1, 21000),
        (3, 21000),
    ]


def test_recorrencia_guarda_o_item_do_planejamento_e_mudar_troca_ou_tira(casal: Casal):
    conta, luz, casa = casal.conta(), casal.categoria("Luz"), casal.categoria("Casa")
    nova = recorrencia(conta, [luz, casa], item_categoria_id=luz, vezes=2)

    criada = casal.pedir("flavio", "POST", "/api/recorrencias", json=nova)

    assert criada.json()["item_categoria_id"] == luz
    assert mudar(casal, nova["id"], 1, item_categoria_id=casa).json()["item_categoria_id"] == casa
    assert [p["item_categoria_id"] for p in gerados(casal, nova["id"])] == [casa, casa]
    assert mudar(casal, nova["id"], 2, item_categoria_id=None).json()["item_categoria_id"] is None
    assert [p["item_categoria_id"] for p in gerados(casal, nova["id"])] == [casa, None]
    assert mudar(casal, nova["id"], 1, valor_centavos=1000).json()["item_categoria_id"] is None
    # A escolha sai com a categoria dela.
    mudar(casal, nova["id"], 1, item_categoria_id=luz)
    sem_luz = mudar(casal, nova["id"], 1, categoria_ids=[casa])
    assert (sem_luz.status_code, sem_luz.json()["item_categoria_id"]) == (200, None)
    fora = mudar(casal, nova["id"], 1, item_categoria_id=luz)
    assert fora.status_code == 422


def test_mudar_o_calendario_daqui_para_frente_renumera_sem_mexer_no_passado(
    casal: Casal, database_url: str, monkeypatch: pytest.MonkeyPatch
):
    conta, seguro = casal.conta(), casal.categoria("Seguro")
    nova = recorrencia(conta, [seguro], inicio="2026-11-10", unidade="meses", vezes=6)
    casal.pedir("flavio", "POST", "/api/recorrencias", json=nova)

    # Da 3ª em diante (10/01/2027): a cada 2 meses, e o dia passa a ser 15 na 3ª.
    resposta = mudar(casal, nova["id"], 3, a_cada=2, inicio="2027-01-15")

    assert resposta.status_code == 200
    assert (resposta.json()["inicio"], resposta.json()["ocorrencia_do_inicio"]) == (
        "2027-01-15",
        3,
    )
    assert [(l["ocorrencia"], l["data"]) for l in gerados(casal, nova["id"])] == [
        (1, "2026-11-10"),
        (2, "2026-12-10"),
        (3, "2027-01-15"),
        (4, "2027-03-15"),
        (5, "2027-05-15"),
        (6, "2027-07-15"),
    ]


def test_mudar_o_calendario_sem_informar_o_inicio_continua_da_data_que_a_ocorrencia_tinha(
    casal: Casal, database_url: str, monkeypatch: pytest.MonkeyPatch
):
    conta, seguro = casal.conta(), casal.categoria("Seguro")
    nova = recorrencia(conta, [seguro], inicio="2026-11-10")
    casal.pedir("flavio", "POST", "/api/recorrencias", json=nova)

    # A 2ª fica em 10/12/2026 e as outras vêm de 2 em 2 semanas. De 10/12/2026 a 28/10/2028
    # (o horizonte) cabem 50 quinzenas: da 2ª à 51ª ocorrência, a última em 26/10/2028.
    mudar(casal, nova["id"], 2, a_cada=2, unidade="semanas")

    previstos = gerados(casal, nova["id"])
    assert [l["ocorrencia"] for l in previstos] == list(range(1, 52))
    assert [l["data"] for l in previstos[:4]] == [
        "2026-11-10",
        "2026-12-10",
        "2026-12-24",
        "2027-01-07",
    ]
    assert previstos[-1]["data"] == "2028-10-26"
    # Dois anos depois, a tarefa diária segue a numeração e o calendário novos até 28/11/2030,
    # sem lançar as que já passaram (a 52ª em 09/11/2028 e a 53ª em 23/11/2028).
    no_dia(monkeypatch, "2028-11-28")
    fazer_tarefa_diaria(database_url)
    previstos = gerados(casal, nova["id"])
    assert [l["ocorrencia"] for l in previstos] == [*range(1, 52), *range(54, 106)]
    assert previstos[-1]["data"] == "2030-11-21"


@pytest.mark.parametrize(
    ("corpo", "motivo"),
    [
        ({"a_partir_da_ocorrencia": 0}, "greater than or equal to 1"),
        ({"a_partir_da_ocorrencia": 5}, "ainda não foi gerada"),
        ({"a_partir_da_ocorrencia": 1, "valor_centavos": None}, "valid integer"),
        ({"a_partir_da_ocorrencia": 1, "automatico": True}, "valor fixo"),
        ({"a_partir_da_ocorrencia": 1, "ate": "2026-11-01"}, "antes do início"),
        ({"a_partir_da_ocorrencia": 1, "ate": "2027-03-01", "vezes": 2}, "não nos dois"),
        ({"a_partir_da_ocorrencia": 1, "pessoa": "vizinho"}, "pessoa não encontrada"),
        ({"a_partir_da_ocorrencia": 1, "conta_id": str(uuid4())}, "conta não encontrada"),
    ],
)
def test_mudar_recorrencia_invalida_e_recusado_sem_gravar(casal: Casal, corpo, motivo):
    conta, luz = casal.conta(), casal.categoria("Luz")
    nova = recorrencia(conta, [luz], vezes=3)
    criada = casal.pedir("flavio", "POST", "/api/recorrencias", json=nova).json()

    resposta = casal.pedir("esposa", "PATCH", f"/api/recorrencias/{nova['id']}", json=corpo)

    assert resposta.status_code == 422
    assert motivo in str(resposta.json())
    assert casal.pedir("flavio", "GET", "/api/recorrencias").json() == [criada]
    assert [l["versao"] for l in gerados(casal, nova["id"])] == [1, 1, 1]


def test_mudar_ou_excluir_recorrencia_que_nao_existe(casal: Casal):
    resposta = mudar(casal, str(uuid4()), 1, valor_centavos=100)

    assert resposta.status_code == 404
    assert casal.pedir("esposa", "DELETE", f"/api/recorrencias/{uuid4()}").status_code == 204


def test_mudar_um_campo_de_antes_da_mudanca_de_calendario_nao_remarca_as_datas_do_passado(
    casal: Casal,
):
    conta, seguro = casal.conta(), casal.categoria("Seguro")
    nova = recorrencia(conta, [seguro], inicio="2026-11-10", vezes=6)
    casal.pedir("flavio", "POST", "/api/recorrencias", json=nova)
    mudar(casal, nova["id"], 5, a_cada=2)

    mudar(casal, nova["id"], 2, valor_centavos=21000)

    assert [
        (l["ocorrencia"], l["data"], l["valor_centavos"]) for l in gerados(casal, nova["id"])
    ] == [
        (1, "2026-11-10", 18990),
        (2, "2026-12-10", 21000),
        (3, "2027-01-10", 21000),
        (4, "2027-02-10", 21000),
        (5, "2027-03-10", 21000),
        (6, "2027-05-10", 21000),
    ]


def test_mudar_o_dia_da_recorrencia_no_cartao_registra_a_fatura_como_mudanca_da_regra(
    casal: Casal,
):
    cartao = casal.pedir(
        "flavio",
        "POST",
        "/api/cartoes",
        json={"nome": "Nubank", "dia_fechamento": 25, "dia_vencimento": 5},
    ).json()["id"]
    nova = recorrencia(cartao, [casal.categoria("Assinaturas")], inicio="2026-11-20", vezes=1)
    casal.pedir("flavio", "POST", "/api/recorrencias", json=nova)
    [previsto] = gerados(casal, nova["id"])

    # O dia 20 passa para o 26, que fecha na fatura seguinte.
    mudar(casal, nova["id"], 1, inicio="2026-11-26")

    [depois] = gerados(casal, nova["id"])
    assert (depois["data"], depois["fatura_mes"]) == ("2026-11-26", "2026-12-01")
    resposta = casal.pedir(
        "esposa",
        "PATCH",
        f"/api/lancamentos/{previsto['id']}",
        json={"versao": 1, "fatura_mes": "2026-11-01"},
    )
    assert resposta.status_code == 409
    assert [(c["campo"], c["origem"]) for c in resposta.json()["campos"]] == [
        ("fatura_mes", "a recorrência Luz")
    ]


def test_reabrir_o_fim_traz_de_volta_o_que_o_fim_tirou_e_nao_o_mes_que_o_casal_pulou(
    casal: Casal,
):
    conta, luz = casal.conta(), casal.categoria("Luz")
    nova = recorrencia(conta, [luz], inicio="2026-11-10", tags=["casa"])
    casal.pedir("flavio", "POST", "/api/recorrencias", json=nova)
    dezembro = gerados(casal, nova["id"])[1]
    casal.pedir("esposa", "DELETE", f"/api/lancamentos/{dezembro['id']}")
    mudar(casal, nova["id"], 1, ate="2027-01-10")
    assert [l["ocorrencia"] for l in gerados(casal, nova["id"])] == [1, 3]

    # Tirar o fim: a 4ª em diante volta pela regra, a 2ª continua pulada, e o pedido pode vir de
    # uma ocorrência que só existe por causa do fim que saiu.
    resposta = mudar(casal, nova["id"], 10, ate=None)

    assert resposta.status_code == 200
    previstos = gerados(casal, nova["id"])
    assert [l["ocorrencia"] for l in previstos] == [1, *range(3, 25)]
    assert previstos[-1]["data"] == "2028-10-10"
    volta = previstos[5]
    assert (volta["situacao"], volta["tags"], volta["categoria_ids"]) == (
        "previsto",
        ["casa"],
        [luz],
    )
    assert len({l["id"] for l in previstos}) == len(previstos)


def test_o_mes_pulado_no_trecho_que_o_fim_tirou_segue_pulado_ao_reabrir(casal: Casal):
    conta, luz = casal.conta(), casal.categoria("Luz")
    nova = recorrencia(conta, [luz], inicio="2026-11-10")
    casal.pedir("flavio", "POST", "/api/recorrencias", json=nova)
    casal.pedir("esposa", "DELETE", f"/api/lancamentos/{gerados(casal, nova['id'])[11]['id']}")
    mudar(casal, nova["id"], 1, vezes=10)
    assert [l["ocorrencia"] for l in gerados(casal, nova["id"])] == list(range(1, 11))

    mudar(casal, nova["id"], 1, vezes=None)

    assert [l["ocorrencia"] for l in gerados(casal, nova["id"])] == [
        *range(1, 12),
        *range(13, 25),
    ]


def test_excluir_o_que_o_fim_ja_tirou_conta_como_pular_o_mes(casal: Casal):
    conta, luz = casal.conta(), casal.categoria("Luz")
    nova = recorrencia(conta, [luz], inicio="2026-11-10")
    casal.pedir("flavio", "POST", "/api/recorrencias", json=nova)
    doze = gerados(casal, nova["id"])[11]["id"]
    mudar(casal, nova["id"], 1, vezes=10)

    # A exclusão do aparelho chega depois de o fim já ter tirado a 12ª.
    casal.pedir("esposa", "DELETE", f"/api/lancamentos/{doze}")
    mudar(casal, nova["id"], 1, vezes=None)

    assert [l["ocorrencia"] for l in gerados(casal, nova["id"])] == [
        *range(1, 12),
        *range(13, 25),
    ]


def test_o_mes_pulado_que_o_horizonte_tirou_segue_pulado_quando_ele_chega(
    casal: Casal, database_url: str, monkeypatch: pytest.MonkeyPatch
):
    conta, luz = casal.conta(), casal.categoria("Luz")
    nova = recorrencia(conta, [luz], inicio="2026-11-10")
    casal.pedir("flavio", "POST", "/api/recorrencias", json=nova)
    casal.pedir("esposa", "DELETE", f"/api/lancamentos/{gerados(casal, nova['id'])[14]['id']}")

    # De 3 em 3 meses a 15ª (10/05/2030) passa do horizonte e a 8ª é a última dentro dele.
    mudar(casal, nova["id"], 1, a_cada=3)
    no_dia(monkeypatch, "2028-11-01")
    fazer_tarefa_diaria(database_url)

    assert [l["ocorrencia"] for l in gerados(casal, nova["id"])] == [*range(1, 15), 16]


def test_reabrir_o_fim_meses_depois_nao_lanca_as_ocorrencias_que_ja_passaram(
    casal: Casal, monkeypatch: pytest.MonkeyPatch
):
    conta, luz = casal.conta(), casal.categoria("Luz")
    nova = recorrencia(conta, [luz], inicio="2026-11-10", ate="2026-12-10")
    casal.pedir("flavio", "POST", "/api/recorrencias", json=nova)

    no_dia(monkeypatch, "2027-03-01")
    mudar(casal, nova["id"], 1, ate=None)

    # Janeiro e fevereiro de 2027 passaram com a regra encerrada: a correção não os lança.
    assert [(l["ocorrencia"], l["data"]) for l in gerados(casal, nova["id"])[:4]] == [
        (1, "2026-11-10"),
        (2, "2026-12-10"),
        (5, "2027-03-10"),
        (6, "2027-04-10"),
    ]


def test_adiar_o_fim_para_uma_data_mais_tarde_gera_as_ocorrencias_do_meio(casal: Casal):
    conta, luz = casal.conta(), casal.categoria("Luz")
    nova = recorrencia(conta, [luz], inicio="2026-11-10", ate="2027-04-10")
    casal.pedir("flavio", "POST", "/api/recorrencias", json=nova)
    mudar(casal, nova["id"], 1, ate="2027-01-10")
    assert len(gerados(casal, nova["id"])) == 3

    mudar(casal, nova["id"], 1, ate="2027-06-10")

    assert [l["data"] for l in gerados(casal, nova["id"])] == [
        "2026-11-10",
        "2026-12-10",
        "2027-01-10",
        "2027-02-10",
        "2027-03-10",
        "2027-04-10",
        "2027-05-10",
        "2027-06-10",
    ]


def test_aumentar_o_numero_de_vezes_depois_de_encerrar_nao_deixa_buraco(casal: Casal):
    conta, luz = casal.conta(), casal.categoria("Luz")
    nova = recorrencia(conta, [luz], inicio="2026-11-10", vezes=5)
    casal.pedir("flavio", "POST", "/api/recorrencias", json=nova)
    mudar(casal, nova["id"], 1, vezes=2)
    assert [l["ocorrencia"] for l in gerados(casal, nova["id"])] == [1, 2]

    mudar(casal, nova["id"], 1, vezes=4)

    assert [l["ocorrencia"] for l in gerados(casal, nova["id"])] == [1, 2, 3, 4]


def test_a_ocorrencia_trazida_de_volta_vem_com_a_regra_de_hoje(casal: Casal):
    conta, luz = casal.conta(), casal.categoria("Luz")
    nova = recorrencia(conta, [luz], inicio="2026-11-10", vezes=4)
    casal.pedir("flavio", "POST", "/api/recorrencias", json=nova)
    mudar(casal, nova["id"], 1, vezes=2)

    mudar(casal, nova["id"], 1, vezes=4, valor_centavos=21000, descricao="Luz (reajuste)")

    assert [
        (l["ocorrencia"], l["valor_centavos"], l["descricao"]) for l in gerados(casal, nova["id"])
    ] == [
        (1, 21000, "Luz (reajuste)"),
        (2, 21000, "Luz (reajuste)"),
        (3, 21000, "Luz (reajuste)"),
        (4, 21000, "Luz (reajuste)"),
    ]


def test_reagendar_para_menos_frequente_tira_o_que_passa_do_horizonte_e_a_tarefa_diaria_traz(
    casal: Casal, database_url: str, monkeypatch: pytest.MonkeyPatch
):
    conta, luz = casal.conta(), casal.categoria("Luz")
    nova = recorrencia(conta, [luz], inicio="2026-11-10")
    casal.pedir("flavio", "POST", "/api/recorrencias", json=nova)
    assert len(gerados(casal, nova["id"])) == 24

    # De mês em mês para de 3 em 3 meses: a 9ª cairia em 10/11/2028, depois do horizonte
    # (28/10/2028).
    mudar(casal, nova["id"], 1, a_cada=3)

    previstos = gerados(casal, nova["id"])
    assert [l["ocorrencia"] for l in previstos] == list(range(1, 9))
    assert previstos[-1]["data"] == "2028-08-10"
    # O horizonte anda: 9ª e 10ª entram, a 11ª (10/05/2029) ainda não.
    no_dia(monkeypatch, "2027-03-01")
    fazer_tarefa_diaria(database_url)
    previstos = gerados(casal, nova["id"])
    assert [(l["ocorrencia"], l["data"]) for l in previstos[-3:]] == [
        (8, "2028-08-10"),
        (9, "2028-11-10"),
        (10, "2029-02-10"),
    ]
    assert len(previstos) == len({l["id"] for l in previstos}) == 10


def test_reagendar_nao_tira_o_previsto_que_o_casal_alterou_a_mao(casal: Casal):
    conta, luz = casal.conta(), casal.categoria("Luz")
    nova = recorrencia(conta, [luz], inicio="2026-11-10")
    casal.pedir("flavio", "POST", "/api/recorrencias", json=nova)
    ultimo = gerados(casal, nova["id"])[-1]
    casal.pedir(
        "flavio",
        "PATCH",
        f"/api/lancamentos/{ultimo['id']}",
        json={"versao": 1, "valor_centavos": 5000},
    )

    mudar(casal, nova["id"], 1, a_cada=3)

    previstos = gerados(casal, nova["id"])
    assert [l["ocorrencia"] for l in previstos] == [*range(1, 9), 24]
    assert (previstos[-1]["data"], previstos[-1]["valor_centavos"]) == ("2028-10-10", 5000)


def test_tirar_o_numero_de_vezes_traz_de_volta_o_que_o_fim_tirou(casal: Casal):
    conta, luz = casal.conta(), casal.categoria("Luz")
    nova = recorrencia(conta, [luz], inicio="2026-11-10", vezes=3)
    casal.pedir("flavio", "POST", "/api/recorrencias", json=nova)
    mudar(casal, nova["id"], 1, vezes=1)
    assert [l["ocorrencia"] for l in gerados(casal, nova["id"])] == [1]

    resposta = mudar(casal, nova["id"], 1, vezes=None)

    assert (resposta.json()["ate"], resposta.json()["vezes"]) == (None, None)
    assert len(gerados(casal, nova["id"])) == 24


def test_previsto_alterado_a_mao_que_o_fim_tirou_volta_com_a_regra_e_a_mudanca_seguinte_o_alcanca(
    casal: Casal,
):
    conta, luz = casal.conta(), casal.categoria("Luz")
    nova = recorrencia(conta, [luz], inicio="2026-11-10", vezes=3)
    casal.pedir("flavio", "POST", "/api/recorrencias", json=nova)
    terceiro = gerados(casal, nova["id"])[2]
    casal.pedir(
        "flavio",
        "PATCH",
        f"/api/lancamentos/{terceiro['id']}",
        json={"versao": 1, "valor_centavos": 5000},
    )
    mudar(casal, nova["id"], 1, vezes=2)

    mudar(casal, nova["id"], 1, vezes=3)
    assert [l["valor_centavos"] for l in gerados(casal, nova["id"])] == [18990] * 3
    mudar(casal, nova["id"], 1, valor_centavos=21000)

    assert [l["valor_centavos"] for l in gerados(casal, nova["id"])] == [21000] * 3


def lote(casal: Casal, quem: str, *acoes: dict) -> list[dict]:
    resposta = casal.pedir(quem, "POST", "/api/lancamentos/lote", json={"acoes": list(acoes)})
    assert resposta.status_code == 200
    return resposta.json()["resultados"]


def test_sem_internet_mudar_daqui_para_frente_e_excluir_sobem_no_lote_e_o_reenvio_nao_muda_nada(
    casal: Casal,
):
    conta, luz = casal.conta(), casal.categoria("Luz")
    nova = recorrencia(conta, [luz], inicio="2026-11-10", vezes=3)
    agua = recorrencia(conta, [luz], descricao="Água", inicio="2026-11-15")
    casal.pedir("flavio", "POST", "/api/recorrencias", json=nova)
    casal.pedir("flavio", "POST", "/api/recorrencias", json=agua)
    acoes = (
        {
            "acao": "alterar_recorrencia",
            "id": nova["id"],
            "alteracao": {"a_partir_da_ocorrencia": 2, "valor_centavos": 21000},
        },
        {"acao": "excluir_recorrencia", "id": agua["id"]},
    )

    primeiro = lote(casal, "esposa", *acoes)
    # A fila repete o lote que ficou sem resposta.
    segundo = lote(casal, "esposa", *acoes)

    assert [r["resultado"] for r in primeiro + segundo] == ["aceita"] * 4
    assert primeiro[0]["recorrencia"]["valor_centavos"] == 21000
    sem_hora = {"alterado_em": None}
    assert segundo[0]["recorrencia"] | sem_hora == primeiro[0]["recorrencia"] | sem_hora
    assert [l["valor_centavos"] for l in gerados(casal, nova["id"])] == [18990, 21000, 21000]
    assert [l["versao"] for l in gerados(casal, nova["id"])] == [1, 2, 2]
    assert gerados(casal, agua["id"]) == []
    assert [r["id"] for r in casal.pedir("flavio", "GET", "/api/recorrencias").json()] == [
        nova["id"]
    ]


def test_excluir_a_recorrencia_que_ainda_nao_comecou_tira_todos_os_previstos(
    casal: Casal, database_url: str, monkeypatch: pytest.MonkeyPatch
):
    conta, luz = casal.conta(), casal.categoria("Luz")
    nova = recorrencia(conta, [luz], inicio="2026-11-10")
    casal.pedir("flavio", "POST", "/api/recorrencias", json=nova)

    assert casal.pedir("esposa", "DELETE", f"/api/recorrencias/{nova['id']}").status_code == 204

    assert casal.pedir("flavio", "GET", "/api/recorrencias").json() == []
    assert gerados(casal, nova["id"]) == []
    no_dia(monkeypatch, "2026-12-01")
    fazer_tarefa_diaria(database_url)
    assert gerados(casal, nova["id"]) == []


def test_mudar_pelo_lote_a_recorrencia_que_a_outra_pessoa_excluiu_e_recusado_e_o_resto_segue(
    casal: Casal,
):
    conta, luz = casal.conta(), casal.categoria("Luz")
    nova = recorrencia(conta, [luz], inicio="2026-11-10", vezes=2)
    casal.pedir("flavio", "POST", "/api/recorrencias", json=nova)
    casal.pedir("flavio", "DELETE", f"/api/recorrencias/{nova['id']}")
    agua = recorrencia(conta, [luz], descricao="Água", vezes=2)

    resultados = lote(
        casal,
        "esposa",
        {
            "acao": "alterar_recorrencia",
            "id": nova["id"],
            "alteracao": {"a_partir_da_ocorrencia": 1, "valor_centavos": 21000},
        },
        {"acao": "criar_recorrencia", "recorrencia": agua},
    )

    assert [(r["resultado"], r["motivo"]) for r in resultados] == [
        ("recusada", "a recorrência foi excluída"),
        ("aceita", None),
    ]


def test_a_mudanca_da_fila_sobre_um_campo_que_a_outra_pessoa_mudou_depois_e_recusada(casal: Casal):
    conta, luz = casal.conta(), casal.categoria("Luz")
    nova = recorrencia(conta, [luz], inicio="2026-11-10", vezes=3)
    casal.pedir("flavio", "POST", "/api/recorrencias", json=nova)
    # A esposa viu a regra a R$ 189,90 e mudou sem internet; o Flávio reajustou antes de ela subir.
    mudar(casal, nova["id"], 1, valor_centavos=21000)

    def alterar(alteracao: dict, antes: dict) -> dict:
        return {
            "acao": "alterar_recorrencia",
            "id": nova["id"],
            "alteracao": {"a_partir_da_ocorrencia": 2} | alteracao,
            "antes": antes,
        }

    resultados = lote(
        casal,
        "esposa",
        alterar({"valor_centavos": 19500}, {"valor_centavos": 18990}),
        # A mesma mudança que o outro lado já fez passa, e campos diferentes se mesclam.
        alterar(
            {"valor_centavos": 21000, "descricao": "Luz da casa"},
            {"valor_centavos": 18990, "descricao": "Luz"},
        ),
        alterar({"pessoa": "esposa"}, {"pessoa": None}),
    )

    assert [(r["resultado"], r["motivo"]) for r in resultados] == [
        ("recusada", "a regra mudou depois (valor): confira e mude de novo"),
        ("aceita", None),
        ("aceita", None),
    ]
    assert [
        (l["valor_centavos"], l["descricao"], l["pessoa"]) for l in gerados(casal, nova["id"])
    ] == [
        (21000, "Luz", None),
        (21000, "Luz da casa", "esposa"),
        (21000, "Luz da casa", "esposa"),
    ]


def test_encerrar_pela_fila_numa_data_e_recusado_se_a_outra_pessoa_encerrou_por_vezes(casal: Casal):
    conta, luz = casal.conta(), casal.categoria("Luz")
    nova = recorrencia(conta, [luz], inicio="2026-11-10")
    casal.pedir("flavio", "POST", "/api/recorrencias", json=nova)
    # O fim é um campo só: encerrar por data tiraria em silêncio as 5 vezes que o Flávio pôs.
    mudar(casal, nova["id"], 1, vezes=5)

    [resultado] = lote(
        casal,
        "esposa",
        {
            "acao": "alterar_recorrencia",
            "id": nova["id"],
            "alteracao": {"a_partir_da_ocorrencia": 1, "ate": "2027-02-28"},
            "antes": {"ate": None, "vezes": None},
        },
    )

    assert (resultado["resultado"], resultado["motivo"]) == (
        "recusada",
        "a regra mudou depois (fim): confira e mude de novo",
    )
    assert len(gerados(casal, nova["id"])) == 5
