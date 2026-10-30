"""O importador do Mobills gera um backup válido, e a restauração o grava num banco vazio (ADR 0012,
ticket 68). Só exports fictícios (ADR 0007)."""

from datetime import UTC, date, datetime
from pathlib import Path

import psycopg
import pytest

from app import lancamentos
from app.backup import gerar_backup, restaurar_backup
from app.mobills import gerar_backup_da_importacao, importar
from app.mobills.__main__ import main
from tests.mobills_ficticio import editar_aba, escrever_fatura, escrever_geral, linha

AGORA = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)
PAPEL = "Papel (categoria, tag, pessoa ou descartar)"


@pytest.fixture
def exports(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path, Path]:
    """Um export até agosto de 2026 com cartão ativo e arquivado, parcelamento no cartão e no
    boleto, reajuste de fatura, pendentes avulsos e uma tag que é pessoa, já revisado."""
    monkeypatch.setenv("PESSOAS", '{"flavio": "Flávio", "esposa": "Fulana"}')
    geral, faturas, revisao = tmp_path / "geral", tmp_path / "faturas", tmp_path / "revisao.xlsx"
    escrever_geral(
        geral,
        "geral.xlsx",
        [
            linha("05/07/2026", "Salário", 5000.00, "Salário"),
            linha("31/07/2026", "Mercado", -120.00, "Alimentação", tags="fulana"),
            linha("31/07/2026", "TV (1/4)", -300.00, "Casa"),
            linha("05/08/2026", "Salário", 5000.00, "Salário"),
            linha("31/08/2026", "TV (2/4)", -300.00, "Casa", situacao="Pendente"),
            linha("31/08/2026", "Reajuste", -0.05, "Reajuste de fatura"),
            linha("30/09/2026", "TV (3/4)", -300.00, "Casa", situacao="Pendente"),
            linha("10/08/2026", "Faculdade (5/7)", -800.00, "Educação"),
            linha("10/09/2026", "Faculdade (6/7)", -800.00, "Educação", situacao="Pendente"),
            linha("10/08/2026", "Luz", -90.00, "Casa", situacao="Pendente"),
            # O parcelamento do app é de despesa e tem 2 parcelas ou mais: estes entram avulsos.
            linha("05/08/2026", "Bônus (1/2)", 1000.00, "Salário"),
            linha("05/09/2026", "Bônus (2/2)", 1000.00, "Salário", situacao="Pendente"),
            linha("12/08/2026", "Taxa (1/1)", -10.00, "Casa"),
            linha("10/09/2026", "Luz", -95.00, "Casa", situacao="Pendente"),
        ],
    )
    escrever_fatura(
        faturas,
        "Cartao A",
        "202607",
        [("12/07/2026", "Mercado", "Alimentação", 120.00), ("14/07/2026", "TV", "Casa", 300.00)],
    )
    escrever_fatura(
        faturas,
        "Cartao A",
        "202608",
        [
            ("14/07/2026", "TV", "Casa", 300.00),
            ("31/08/2026", "Reajuste", "Reajuste de fatura", 0.05),
        ],
    )
    escrever_fatura(faturas, "Cartao B", "202606", [("02/06/2026", "Café", "Alimentação", 9.00)])
    assert importar(geral, faturas, revisao).impedimentos
    editar_aba(revisao, "Cartões", "Pasta", "Cartao A", "Dia do fechamento", 25)
    editar_aba(revisao, "Cartões", "Pasta", "Cartao A", "Dia do vencimento", 5)
    editar_aba(revisao, "De-para", "Nome no Mobills", "fulana", PAPEL, "pessoa")
    editar_aba(revisao, "De-para", "Nome no Mobills", "fulana", "Nome no app", "Fulana")
    return geral, faturas, revisao


@pytest.fixture
def importacao(exports):
    importacao = importar(*exports)
    assert importacao.impedimentos == []
    return importacao


def test_backup_do_importador_restaura_num_banco_vazio_e_exporta_de_novo_o_mesmo_zip(
    importacao, client, database_url
):
    backup = gerar_backup_da_importacao(importacao, AGORA)

    with psycopg.connect(database_url, autocommit=True) as conn:
        manifesto = restaurar_backup(conn, backup)
        with conn.transaction():
            assert gerar_backup(conn) == backup
    contagens = {tabela: m["linhas"] for tabela, m in manifesto["tabelas"].items()}
    assert contagens["contas"] == 1
    assert contagens["cartoes"] == 2
    assert contagens["parcelamentos"] == 2
    # Salário 2x, Mercado, TV 1 a 4, Faculdade 5 a 7, Luz de setembro, Bônus 2x, Taxa e o Café.
    assert contagens["lancamentos"] == 15


def test_historico_restaurado_tem_as_faturas_pagas_os_parcelamentos_e_os_previstos(
    importacao, casal, database_url, monkeypatch
):
    monkeypatch.setattr(lancamentos, "hoje", lambda: date(2026, 9, 1))
    with psycopg.connect(database_url, autocommit=True) as conn:
        restaurar_backup(conn, gerar_backup_da_importacao(importacao, AGORA))

    def ler(caminho):
        resposta = casal.pedir("flavio", "GET", caminho)
        assert resposta.status_code == 200, resposta.text
        return resposta.json()

    cartoes = {c["nome"]: c for c in ler("/api/cartoes?arquivados=true")}
    assert (cartoes["Cartao A"]["arquivado"], cartoes["Cartao B"]["arquivado"]) == (False, True)
    assert (cartoes["Cartao A"]["dia_fechamento"], cartoes["Cartao A"]["dia_vencimento"]) == (25, 5)
    faturas = [
        (f["mes"], f["situacao"], f["fechamento"], f["compras_centavos"], f["ajuste_centavos"])
        + (f["saldo_anterior_centavos"], f["a_pagar_centavos"])
        for f in ler(f"/api/cartoes/{cartoes['Cartao A']['id']}/faturas")
    ]
    assert faturas == [
        # As importadas: fechadas e pagas, sem datas e sem pagamento de fatura.
        ("2026-07-01", "paga", None, 42000, 0, 0, 0),
        ("2026-08-01", "paga", None, 30000, 5, 0, 0),
        # As das parcelas futuras nascem dos dias padrão do cartão.
        ("2026-09-01", "aberta", "2026-09-25", 30000, 0, 0, 30000),
        ("2026-10-01", "aberta", "2026-10-25", 30000, 0, 0, 30000),
    ]
    [cafe] = ler(f"/api/cartoes/{cartoes['Cartao B']['id']}/faturas")
    assert (cafe["mes"], cafe["situacao"], cafe["compras_centavos"]) == ("2026-06-01", "paga", 900)

    parcelamentos = {p["descricao"]: p for p in ler("/api/parcelamentos")}
    tv, faculdade = parcelamentos["TV"], parcelamentos["Faculdade"]
    assert (tv["conta_id"], tv["data"], tv["parcelas"], tv["automatico"]) == (
        cartoes["Cartao A"]["id"],
        "2026-07-14",
        4,
        True,
    )
    assert tv["valor_total_centavos"] == 120000
    [conta] = ler("/api/contas")
    assert conta["nome"] == "Carteira"
    assert (faculdade["conta_id"], faculdade["data"], faculdade["automatico"]) == (
        conta["id"],
        "2026-04-10",
        False,
    )
    assert faculdade["valor_total_centavos"] == 7 * 80000

    todos = ler("/api/lancamentos")
    assert {x["fonte"] for x in todos} == {"mobills"}
    assert len({x["criado_por"] for x in todos}) == 1
    por_descricao = {}
    for x in todos:
        por_descricao.setdefault(x["descricao"], []).append(x)
    [mercado] = por_descricao["Mercado"]
    assert (mercado["pessoa"], mercado["tags"], mercado["conta_id"]) == (
        "esposa",
        [],
        cartoes["Cartao A"]["id"],
    )
    assert (mercado["data"], mercado["mes"]) == ("2026-07-12", "2026-07-01")
    [luz] = por_descricao["Luz"]
    assert (luz["situacao"], luz["data"], luz["parcelamento_id"]) == (
        "previsto",
        "2026-09-10",
        None,
    )
    assert sorted((x["parcela"], x["situacao"], x["mes"]) for x in por_descricao["TV"]) == [
        (1, "realizado", "2026-07-01"),
        (2, "previsto", "2026-08-01"),
        (3, "previsto", "2026-09-01"),
        (4, "previsto", "2026-10-01"),
    ]
    assert {x["parcelamento_id"] for x in por_descricao["TV"]} == {tv["id"]}
    avulsos = por_descricao["Bônus"] + por_descricao["Taxa"]
    assert [(x["parcelamento_id"], x["parcela"]) for x in avulsos] == [(None, None)] * 3
    assert sorted((x["parcela"], x["data"]) for x in por_descricao["Faculdade"]) == [
        (5, "2026-08-10"),
        (6, "2026-09-10"),
        (7, "2026-10-10"),
    ]


def test_linha_de_comando_grava_o_backup_so_sem_impedimentos(exports, client, database_url, capsys):
    geral, faturas, revisao = exports
    backup = revisao.parent / "backup.zip"

    assert main([str(geral), str(faturas), str(revisao), "--backup", str(backup)]) == 0

    assert f"backup em {backup}" in capsys.readouterr().out
    with psycopg.connect(database_url, autocommit=True) as conn:
        restaurar_backup(conn, backup.read_bytes())

    backup.unlink()
    editar_aba(revisao, "Cartões", "Pasta", "Cartao A", "Dia do fechamento", None)
    assert main([str(geral), str(faturas), str(revisao), "--backup", str(backup)]) == 2
    assert "backup não gravado" in capsys.readouterr().err
    assert not backup.exists()
