"""O importador do Mobills gera um backup válido, e a restauração o grava num banco vazio (ADR 0012,
ticket 68). Só exports fictícios (ADR 0007)."""

from datetime import UTC, date, datetime
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest

from app import lancamentos, restauracao
from app.automaticos import realizar_automaticos
from app.backup import (
    RestauracaoRecusada,
    esvaziar_banco,
    gerar_backup,
    refazer_importacao,
    restaurar_backup,
)
from app.mobills import gerar_backup_da_importacao, importar
from app.mobills.__main__ import main
from tests.exemplo_ficticio import trocar_arquivo
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
            # Começou antes do histórico: a 4/7 está no primeiro mês do export.
            linha("10/07/2026", "Faculdade (4/7)", -800.00, "Educação"),
            linha("10/08/2026", "Faculdade (5/7)", -800.00, "Educação"),
            linha("10/09/2026", "Faculdade (6/7)", -800.00, "Educação", situacao="Pendente"),
            linha("10/08/2026", "Luz", -90.00, "Casa", situacao="Pendente"),
            # O parcelamento do app é de despesa e tem 2 parcelas ou mais: estes entram avulsos.
            linha("05/08/2026", "Bônus (1/2)", 1000.00, "Salário"),
            linha("05/09/2026", "Bônus (2/2)", 1000.00, "Salário", situacao="Pendente"),
            linha("12/08/2026", "Taxa (1/1)", -10.00, "Casa"),
            # Sequência quebrada (falta a 2/3): vai para a revisão e entra avulsa, sem inventar.
            linha("10/07/2026", "Curso (1/3)", -100.00, "Educação"),
            linha("10/09/2026", "Curso (3/3)", -100.00, "Educação", situacao="Pendente"),
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
    # Salário 2x, Mercado, TV 1 a 4, Faculdade 4 a 7, Luz de setembro, Bônus 2x, Taxa, Curso 2x
    # e o Café.
    assert contagens["lancamentos"] == 18


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
    # O histórico pago não ocupa o limite nem sai da projeção do mês atual (ticket 58): só as
    # parcelas que faltam da TV, nas faturas abertas.
    limite = ler(f"/api/cartoes/{cartoes['Cartao A']['id']}/limite")
    assert (limite["faturas_fechadas_centavos"], limite["parcelas_futuras_centavos"]) == (0, 60000)
    projecao = {m["mes"]: m["faturas_centavos"] for m in ler("/api/futuro")["proximos_meses"]}
    assert (projecao["2026-09-01"], projecao["2026-10-01"]) == (30000, 30000)
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
    avulsos = por_descricao["Bônus"] + por_descricao["Taxa"] + por_descricao["Curso"]
    assert [(x["parcelamento_id"], x["parcela"]) for x in avulsos] == [(None, None)] * 5
    assert sorted((x["parcela"], x["data"]) for x in por_descricao["Faculdade"]) == [
        (4, "2026-07-10"),
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


def restaurar(database_url: str, backup: bytes) -> None:
    with psycopg.connect(database_url, autocommit=True) as conn:
        restaurar_backup(conn, backup)


def refazer(database_url: str, backup: bytes):
    with psycopg.connect(database_url, autocommit=True) as conn:
        return refazer_importacao(conn, backup)


def exportar(database_url: str) -> bytes:
    with psycopg.connect(database_url) as conn:
        return gerar_backup(conn)


def test_refazer_num_banco_so_com_o_importado_grava_o_importado_novo(
    importacao, client, database_url
):
    restaurar(database_url, gerar_backup_da_importacao(importacao, AGORA))
    novo = gerar_backup_da_importacao(importacao, datetime(2026, 9, 2, 12, 0, tzinfo=UTC))

    _, perdidos = refazer(database_url, novo)

    assert exportar(database_url) == novo
    assert perdidos == []


def test_refazer_recusa_depois_de_lancar_pelo_app_e_o_lancado_continua(
    importacao, casal, database_url
):
    restaurar(database_url, gerar_backup_da_importacao(importacao, AGORA))
    lancar_pelo_app(casal)
    antes = exportar(database_url)

    with pytest.raises(RestauracaoRecusada, match="uso pelo app em lancamentos"):
        refazer(database_url, gerar_backup_da_importacao(importacao, AGORA))

    assert exportar(database_url) == antes


def lancar_pelo_app(casal) -> None:
    [conta] = casal.pedir("flavio", "GET", "/api/contas").json()
    [casa] = [
        c for c in casal.pedir("flavio", "GET", "/api/categorias").json() if c["nome"] == "Casa"
    ]
    lancado = {"id": str(uuid4()), "tipo": "despesa", "valor_centavos": 4500}
    lancado |= {"data": "2026-09-03", "descricao": "Padaria", "conta_id": conta["id"]}
    lancado |= {"categoria_ids": [casa["id"]]}
    assert casal.pedir("flavio", "POST", "/api/lancamentos", json=lancado).status_code == 201


def test_refazer_recusa_um_backup_que_nao_e_so_da_importacao(importacao, casal, database_url):
    importado = gerar_backup_da_importacao(importacao, AGORA)
    restaurar(database_url, importado)
    lancar_pelo_app(casal)
    com_o_app = exportar(database_url)
    with psycopg.connect(database_url, autocommit=True) as conn:
        esvaziar_banco(conn)
    restaurar(database_url, importado)

    with pytest.raises(RestauracaoRecusada, match="não é só da importação: .* em lancamentos"):
        refazer(database_url, com_o_app)

    assert exportar(database_url) == importado


def test_refazer_confere_o_zip_novo_antes_de_apagar(importacao, client, database_url):
    importado = gerar_backup_da_importacao(importacao, AGORA)
    restaurar(database_url, importado)
    sem_manifesto = trocar_arquivo(importado, "manifesto.json", b"{}")

    with pytest.raises(RestauracaoRecusada):
        refazer(database_url, sem_manifesto)

    assert exportar(database_url) == importado


def test_refazer_avisa_a_preparacao_da_virada_que_se_perdeu(importacao, casal, database_url):
    importado = gerar_backup_da_importacao(importacao, AGORA)
    restaurar(database_url, importado)
    [conta] = casal.pedir("flavio", "GET", "/api/contas").json()
    cartoes = {c["nome"]: c for c in casal.pedir("flavio", "GET", "/api/cartoes").json()}
    abertura = {"saldo_abertura_centavos": 150000, "data_abertura": "2026-09-01"}
    corpo = {"nome": conta["nome"], "tipo": conta["tipo"]} | abertura
    assert casal.pedir("flavio", "PUT", f"/api/contas/{conta['id']}", json=corpo).status_code == 200
    cartao = cartoes["Cartao A"]
    corpo = {"nome": cartao["nome"], "dia_fechamento": 25, "dia_vencimento": 5}
    corpo |= {"limite_centavos": 800000}
    assert (
        casal.pedir("flavio", "PUT", f"/api/cartoes/{cartao['id']}", json=corpo).status_code == 200
    )
    datas = {"fechamento": "2026-08-25", "vencimento": "2026-09-05"}
    caminho = f"/api/cartoes/{cartao['id']}/faturas/2026-08-01"
    assert casal.pedir("flavio", "PATCH", caminho, json=datas).status_code == 200

    _, perdidos = refazer(database_url, importado)

    assert perdidos == [
        "saldo de abertura em 1 conta",
        "limite ou titular em 1 cartão",
        "datas em 1 fatura",
    ]
    assert exportar(database_url) == importado


def test_a_tarefa_diaria_nas_parcelas_importadas_nao_impede_o_refazer(
    importacao, client, database_url, monkeypatch
):
    importado = gerar_backup_da_importacao(importacao, AGORA)
    restaurar(database_url, importado)
    monkeypatch.setattr(lancamentos, "hoje", lambda: date(2026, 9, 1))
    assert realizar_automaticos(database_url) > 0

    refazer(database_url, importado)

    assert exportar(database_url) == importado


def test_linha_de_comando_refaz_a_importacao_em_prod_e_recusa_depois_do_app(
    importacao, casal, database_url, monkeypatch, capsys, tmp_path
):
    monkeypatch.setenv("AMBIENTE", "prod")
    zip = tmp_path / "importado.zip"
    zip.write_bytes(gerar_backup_da_importacao(importacao, AGORA))
    restaurar(database_url, zip.read_bytes())

    assert restauracao.main([str(zip), "--refazer-importacao"]) == 0
    saida = capsys.readouterr().out
    assert "importação refeita: banco esvaziado e restaurado" in saida
    assert "exportado de novo: mesmo zip" in saida

    lancar_pelo_app(casal)
    assert restauracao.main([str(zip), "--refazer-importacao"]) == 1
    erro = capsys.readouterr().err
    assert "recusada, nada foi apagado nem gravado: o banco tem uso pelo app em" in erro


def test_linha_de_comando_avisa_o_que_o_refazer_perdeu(
    importacao, casal, database_url, capsys, tmp_path
):
    zip = tmp_path / "importado.zip"
    zip.write_bytes(gerar_backup_da_importacao(importacao, AGORA))
    restaurar(database_url, zip.read_bytes())
    [conta] = casal.pedir("flavio", "GET", "/api/contas").json()
    corpo = {"nome": conta["nome"], "tipo": conta["tipo"], "saldo_abertura_centavos": 100}
    corpo |= {"data_abertura": "2026-09-01"}
    assert casal.pedir("flavio", "PUT", f"/api/contas/{conta['id']}", json=corpo).status_code == 200

    assert restauracao.main([str(zip), "--refazer-importacao"]) == 0

    assert "informe de novo: saldo de abertura em 1 conta" in capsys.readouterr().out


def test_linha_de_comando_nao_junta_esvaziar_e_refazer(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("AMBIENTE", "dev")
    with pytest.raises(SystemExit):
        restauracao.main([str(tmp_path / "x.zip"), "--esvaziar", "--refazer-importacao"])
    assert "not allowed with argument --esvaziar" in capsys.readouterr().err
