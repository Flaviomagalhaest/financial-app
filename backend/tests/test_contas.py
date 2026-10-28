from uuid import uuid4

from tests.conftest import Casal
from tests.test_lancamentos import lancamento


def nova_conta(casal: Casal, nome="Corrente", **campos) -> dict:
    resposta = casal.pedir(
        "flavio", "POST", "/api/contas", json={"nome": nome, "tipo": "corrente"} | campos
    )
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def saldo(casal: Casal, conta_id: str) -> int:
    contas = casal.pedir("esposa", "GET", "/api/contas?arquivadas=true").json()
    return next(c for c in contas if c["id"] == conta_id)["saldo_centavos"]


def test_so_realizados_depois_do_saldo_de_abertura_mexem_no_saldo(casal: Casal):
    conta = nova_conta(casal, saldo_abertura_centavos=100000, data_abertura="2026-10-10")["id"]
    mercado, salario = casal.categoria(), casal.categoria("Salário", "receita")
    for dados in [
        lancamento(
            conta, [mercado], valor_centavos=3000, data="2026-10-09"
        ),  # antes: só estatística
        lancamento(
            conta, [mercado], valor_centavos=5000, data="2026-10-10"
        ),  # no dia: já está no saldo informado
        lancamento(conta, [mercado], valor_centavos=12035, data="2026-10-11"),
        lancamento(conta, [salario], tipo="receita", valor_centavos=50000, data="2026-10-12"),
        lancamento(conta, [mercado], valor_centavos=9999, data="2026-10-13", situacao="previsto"),
    ]:
        assert casal.pedir("flavio", "POST", "/api/lancamentos", json=dados).status_code == 201

    # 1.000,00 - 120,35 + 500,00; o previsto e os de antes (ou do dia) da abertura ficam fora
    assert saldo(casal, conta) == 100000 - 12035 + 50000


def test_conta_sem_saldo_de_abertura_soma_todos_os_realizados_a_partir_de_zero(casal: Casal):
    conta = nova_conta(casal)["id"]
    mercado = casal.categoria()
    casal.pedir(
        "flavio", "POST", "/api/lancamentos", json=lancamento(conta, [mercado], valor_centavos=700)
    )

    assert saldo(casal, conta) == -700


def test_saldo_de_abertura_exige_a_data_e_a_data_exige_o_saldo(casal: Casal):
    for campos in [{"saldo_abertura_centavos": 100}, {"data_abertura": "2026-10-10"}]:
        resposta = casal.pedir(
            "flavio", "POST", "/api/contas", json={"nome": "X", "tipo": "corrente"} | campos
        )
        assert resposta.status_code == 422


def test_informar_o_saldo_de_abertura_depois_recalcula_o_saldo(casal: Casal):
    conta = nova_conta(casal)["id"]
    mercado = casal.categoria()
    for dia, valor in [("2026-10-01", 4000), ("2026-10-20", 1000)]:
        casal.pedir(
            "flavio",
            "POST",
            "/api/lancamentos",
            json=lancamento(conta, [mercado], valor_centavos=valor, data=dia),
        )

    editada = casal.pedir(
        "esposa",
        "PUT",
        f"/api/contas/{conta}",
        json={
            "nome": "Corrente Itaú",
            "tipo": "corrente",
            "saldo_abertura_centavos": 20000,
            "data_abertura": "2026-10-10",
        },
    )

    assert editada.status_code == 200
    assert editada.json()["nome"] == "Corrente Itaú"
    assert editada.json()["saldo_centavos"] == 20000 - 1000


def test_editar_conta_que_nao_existe_da_404(casal: Casal):
    resposta = casal.pedir(
        "flavio", "PUT", f"/api/contas/{uuid4()}", json={"nome": "X", "tipo": "carteira"}
    )

    assert resposta.status_code == 404


def test_arquivar_conta_tira_das_opcoes_e_mantem_o_historico(casal: Casal):
    conta, outra = nova_conta(casal)["id"], nova_conta(casal, "Carteira")["id"]
    mercado = casal.categoria()
    gasto = lancamento(conta, [mercado])
    casal.pedir("flavio", "POST", "/api/lancamentos", json=gasto)

    arquivada = casal.pedir(
        "flavio",
        "PUT",
        f"/api/contas/{conta}",
        json={"nome": "Corrente", "tipo": "corrente", "arquivada": True},
    )

    assert arquivada.json()["arquivada"] is True
    opcoes = casal.pedir("esposa", "GET", "/api/contas").json()
    assert [c["id"] for c in opcoes] == [outra]
    todas = casal.pedir("esposa", "GET", "/api/contas?arquivadas=true").json()
    assert {c["id"] for c in todas} == {conta, outra}
    [visto] = casal.pedir("esposa", "GET", "/api/lancamentos").json()
    assert visto["id"] == gasto["id"] and visto["conta_id"] == conta
    assert saldo(casal, conta) == -12035


def test_conta_arquivada_nao_recebe_lancamento_novo_e_pode_voltar(casal: Casal):
    conta = nova_conta(casal)["id"]
    mercado = casal.categoria()
    corpo = {"nome": "Corrente", "tipo": "corrente"}
    casal.pedir("flavio", "PUT", f"/api/contas/{conta}", json=corpo | {"arquivada": True})

    recusado = casal.pedir("flavio", "POST", "/api/lancamentos", json=lancamento(conta, [mercado]))
    casal.pedir("flavio", "PUT", f"/api/contas/{conta}", json=corpo)
    aceito = casal.pedir("flavio", "POST", "/api/lancamentos", json=lancamento(conta, [mercado]))

    assert recusado.status_code == 422
    assert "arquivada" in recusado.json()["detail"]
    assert aceito.status_code == 201


def transferencia(origem: str, destino: str, **campos) -> dict:
    return {
        "id": str(uuid4()),
        "conta_origem_id": origem,
        "conta_destino_id": destino,
        "valor_centavos": 30000,
        "data": "2026-10-15",
        "descricao": "Guardar na reserva",
    } | campos


def test_transferencia_move_o_saldo_das_duas_contas_sem_ser_despesa(casal: Casal):
    corrente = nova_conta(casal, saldo_abertura_centavos=100000, data_abertura="2026-10-01")["id"]
    poupanca = nova_conta(
        casal, "Poupança", saldo_abertura_centavos=5000, data_abertura="2026-10-01"
    )["id"]
    reserva = casal.categoria("Reserva", "transferencia")
    nova = transferencia(corrente, poupanca, categoria_id=reserva)

    criada = casal.pedir("flavio", "POST", "/api/transferencias", json=nova)

    assert criada.status_code == 201
    assert criada.json() | {"criado_em": None, "alterado_em": None} == nova | {
        "situacao": "realizado",
        "criado_por": "flavio",
        "alterado_por": "flavio",
        "criado_em": None,
        "alterado_em": None,
    }
    assert saldo(casal, corrente) == 100000 - 30000
    assert saldo(casal, poupanca) == 5000 + 30000
    # Não vira despesa nem receita: a lista de lançamentos segue vazia.
    assert casal.pedir("esposa", "GET", "/api/lancamentos").json() == []
    assert casal.pedir("esposa", "GET", "/api/transferencias").json() == [criada.json()]


def test_transferencia_antes_da_abertura_ou_prevista_nao_mexe_no_saldo(casal: Casal):
    a = nova_conta(casal, saldo_abertura_centavos=10000, data_abertura="2026-10-10")["id"]
    b = nova_conta(casal, "Outra")["id"]
    casal.pedir(
        "flavio", "POST", "/api/transferencias", json=transferencia(a, b, data="2026-10-05")
    )
    casal.pedir(
        "flavio", "POST", "/api/transferencias", json=transferencia(a, b, situacao="previsto")
    )

    assert saldo(casal, a) == 10000
    # Sem abertura em `b`, a de antes da abertura de `a` entra no saldo dela.
    assert saldo(casal, b) == 30000


def test_categoria_da_transferencia_e_opcional_e_da_lista_de_transferencia(casal: Casal):
    a, b = nova_conta(casal)["id"], nova_conta(casal, "Outra")["id"]
    despesa = casal.categoria("Mercado")

    sem = casal.pedir("flavio", "POST", "/api/transferencias", json=transferencia(a, b))
    errada = casal.pedir(
        "flavio", "POST", "/api/transferencias", json=transferencia(a, b, categoria_id=despesa)
    )

    assert sem.status_code == 201 and sem.json()["categoria_id"] is None
    assert errada.status_code == 422


def test_transferencia_recusa_mesma_conta_conta_inexistente_e_arquivada(casal: Casal):
    a, b = nova_conta(casal)["id"], nova_conta(casal, "Outra")["id"]
    casal.pedir(
        "flavio",
        "PUT",
        f"/api/contas/{b}",
        json={"nome": "Outra", "tipo": "corrente", "arquivada": True},
    )

    for dados in [transferencia(a, a), transferencia(a, str(uuid4())), transferencia(a, b)]:
        resposta = casal.pedir("flavio", "POST", "/api/transferencias", json=dados)
        assert resposta.status_code == 422, dados


def test_edita_e_exclui_transferencia(casal: Casal):
    a, b = nova_conta(casal)["id"], nova_conta(casal, "Outra")["id"]
    nova = transferencia(a, b)
    casal.pedir("flavio", "POST", "/api/transferencias", json=nova)

    editada = casal.pedir(
        "esposa", "PUT", f"/api/transferencias/{nova['id']}", json=nova | {"valor_centavos": 1000}
    )
    assert editada.status_code == 200
    assert editada.json()["alterado_por"] == "esposa"
    assert saldo(casal, a) == -1000

    for _ in range(2):  # idempotente
        assert (
            casal.pedir("flavio", "DELETE", f"/api/transferencias/{nova['id']}").status_code == 204
        )
    assert saldo(casal, a) == 0
    assert (
        casal.pedir("flavio", "PUT", f"/api/transferencias/{nova['id']}", json=nova).status_code
        == 404
    )


def test_reenviar_o_mesmo_id_nao_duplica_a_transferencia(casal: Casal):
    a, b = nova_conta(casal)["id"], nova_conta(casal, "Outra")["id"]
    nova = transferencia(a, b)

    primeira = casal.pedir("flavio", "POST", "/api/transferencias", json=nova)
    segunda = casal.pedir("flavio", "POST", "/api/transferencias", json=nova)

    assert (primeira.status_code, segunda.status_code) == (201, 200)
    assert saldo(casal, a) == -30000
