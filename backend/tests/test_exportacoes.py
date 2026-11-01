import csv
import io
import uuid
import zipfile
from datetime import datetime
from urllib.parse import parse_qs, urlparse

import psycopg
from fastapi.testclient import TestClient

from app.exportacao import formatar_planilha
from app.main import create_app
from tests.conftest import Casal
from tests.emissor import Emissor
from tests.test_cartoes import comprar, novo_cartao
from tests.test_lancamentos import lancamento


class S3Falso:
    """Só a fronteira com a AWS: guarda o que seria enviado e assina uma URL de mentira."""

    def __init__(self) -> None:
        self.enviados: list[dict] = []
        self.assinados: list[dict] = []

    def put_object(self, **pedido) -> dict:
        self.enviados.append(pedido)
        return {}

    def generate_presigned_url(self, operacao: str, Params: dict, ExpiresIn: int) -> str:
        self.assinados.append({"operacao": operacao, "params": Params, "expira_em": ExpiresIn})
        return f"https://s3.exemplo/{Params['Bucket']}/{Params['Key']}?X-Amz-Expires={ExpiresIn}"


def _cliente(database_url: str, emissor: Emissor, s3: S3Falso) -> TestClient:
    app = create_app(
        database_url,
        verificador=emissor.verificador(),
        s3=s3,
        bucket_de_exportacoes="bucket-de-exportacoes",
    )
    return TestClient(app)


def test_exportar_tudo_devolve_url_de_5_minutos_para_o_zip_do_backup(
    database_url: str, emissor: Emissor, banco_ficticio
):
    s3 = S3Falso()

    resposta = _cliente(database_url, emissor, s3).post(
        "/api/exportacoes", json={"formato": "backup"}, headers=emissor.cabecalho("flavio")
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    (enviado,) = s3.enviados
    assert enviado["Bucket"] == "bucket-de-exportacoes"
    assert enviado["Key"].startswith("exportacoes/") and enviado["Key"].endswith(".zip")
    with zipfile.ZipFile(io.BytesIO(enviado["Body"])) as zip:
        nomes = set(zip.namelist())
    assert {"exemplo_contas.csv", "exemplo_lancamentos.csv", "exportacoes.csv"} <= nomes
    (assinado,) = s3.assinados
    assert assinado["operacao"] == "get_object"
    assert assinado["expira_em"] == 300
    assert assinado["params"]["Key"] == enviado["Key"]
    # O aparelho baixa o arquivo, não o abre: tipo e nome vêm da assinatura.
    assert "attachment" in assinado["params"]["ResponseContentDisposition"]
    assert corpo["arquivo"].startswith("financial-app-backup-") and corpo["arquivo"].endswith(
        ".zip"
    )
    assert assinado["params"]["ResponseContentDisposition"].endswith(f'"{corpo["arquivo"]}"')
    assert parse_qs(urlparse(corpo["url"]).query)["X-Amz-Expires"] == ["300"]


def test_cada_exportacao_a_pedido_registra_quem_e_quando(
    database_url: str, emissor: Emissor, banco_ficticio
):
    cliente = _cliente(database_url, emissor, S3Falso())

    cliente.post(
        "/api/exportacoes", json={"formato": "backup"}, headers=emissor.cabecalho("flavio")
    )
    cliente.post(
        "/api/exportacoes", json={"formato": "planilha"}, headers=emissor.cabecalho("esposa")
    )

    with psycopg.connect(database_url) as conn:
        registros = conn.execute(
            "SELECT usuario, formato, criada_em FROM exportacoes ORDER BY criada_em"
        ).fetchall()
    assert [(usuario, formato) for usuario, formato, _ in registros] == [
        ("flavio", "backup"),
        ("esposa", "planilha"),
    ]
    assert all(isinstance(quando, datetime) for _, _, quando in registros)


def test_o_backup_exportado_ja_traz_o_registro_dos_pedidos_anteriores(
    database_url: str, emissor: Emissor, banco_ficticio
):
    s3 = S3Falso()
    cliente = _cliente(database_url, emissor, s3)
    cabecalho = emissor.cabecalho("flavio")

    cliente.post("/api/exportacoes", json={"formato": "backup"}, headers=cabecalho)
    cliente.post("/api/exportacoes", json={"formato": "backup"}, headers=cabecalho)

    with zipfile.ZipFile(io.BytesIO(s3.enviados[1]["Body"])) as zip:
        linhas = list(csv.DictReader(io.StringIO(zip.read("exportacoes.csv").decode())))
    assert [(l["usuario"], l["formato"]) for l in linhas] == [("flavio", "backup")]


def test_exportar_a_planilha_envia_um_csv_que_abre_no_excel_em_portugues(
    database_url: str, emissor: Emissor, client: TestClient
):
    s3 = S3Falso()

    resposta = _cliente(database_url, emissor, s3).post(
        "/api/exportacoes", json={"formato": "planilha"}, headers=emissor.cabecalho("flavio")
    )

    assert resposta.status_code == 200
    (enviado,) = s3.enviados
    assert enviado["Key"].endswith(".csv")
    assert enviado["ContentType"] == "text/csv; charset=utf-8"
    assert enviado["Body"].startswith(b"\xef\xbb\xbfdata;descricao;valor;")
    assert resposta.json()["arquivo"].startswith("financial-app-lancamentos-")


def test_planilha_traz_todo_o_historico_com_nomes_no_lugar_dos_ids(
    database_url: str, emissor: Emissor, casal: Casal
):
    corrente, poupanca = casal.conta("Corrente"), casal.conta("Poupança", "poupanca")
    mercado, casa = casal.categoria("Mercado"), casal.categoria("Casa")
    salario, reserva = (
        casal.categoria("Salário", "receita"),
        casal.categoria("Reserva", "transferencia"),
    )
    cartao = casal.pedir(
        "flavio",
        "POST",
        "/api/cartoes",
        json={"nome": "Nubank", "dia_fechamento": 25, "dia_vencimento": 5},
    ).json()["id"]
    feira = lancamento(
        corrente,
        [mercado, casa],
        valor_centavos=12035,
        data="2026-03-02",
        descricao="Feira",
        tags=["sábado", "casa nova"],
        pessoa="flavio",
    )
    casal.pedir("flavio", "POST", "/api/lancamentos", json=feira)
    casal.pedir(
        "flavio",
        "PATCH",
        f"/api/lancamentos/{feira['id']}",
        json={"versao": 1, "descricao": "Feira!"},
    )
    compra_no_cartao = lancamento(cartao, [mercado], valor_centavos=5000, data="2026-03-28")
    for quem, dados in [
        ("esposa", compra_no_cartao),
        (
            "flavio",
            lancamento(
                corrente,
                [salario],
                tipo="receita",
                valor_centavos=500000,
                data="2026-03-05",
                descricao="Salário",
            ),
        ),
        ("flavio", lancamento(corrente, [mercado], data="2099-01-01", descricao="Futuro")),
    ]:
        assert casal.pedir(quem, "POST", "/api/lancamentos", json=dados).status_code == 201
    # O estorno é um crédito: sai da planilha com o sinal contrário ao da compra.
    estorno = lancamento(
        cartao, [mercado], valor_centavos=5000, data="2026-04-26", estorno_de=compra_no_cartao["id"]
    )
    assert casal.pedir("flavio", "POST", "/api/lancamentos", json=estorno).status_code == 201
    excluido = lancamento(corrente, [mercado], data="2026-03-03", descricao="Excluído")
    casal.pedir("flavio", "POST", "/api/lancamentos", json=excluido)
    casal.pedir("flavio", "DELETE", f"/api/lancamentos/{excluido['id']}")
    casal.pedir(
        "esposa",
        "POST",
        "/api/transferencias",
        json={
            "id": str(uuid.uuid4()),
            "conta_origem_id": corrente,
            "conta_destino_id": poupanca,
            "valor_centavos": 100000,
            "data": "2026-03-10",
            "descricao": "Guardar",
            "categoria_id": reserva,
        },
    )
    casal.pedir(
        "esposa",
        "POST",
        "/api/transferencias",
        json={
            "id": str(uuid.uuid4()),
            "conta_origem_id": corrente,
            "conta_destino_id": cartao,
            "valor_centavos": 5000,
            "data": "2026-04-05",
            "descricao": "Fatura Nubank",
            "fatura_mes": "2026-04-01",
        },
    )
    s3 = S3Falso()

    resposta = _cliente(database_url, emissor, s3).post(
        "/api/exportacoes", json={"formato": "planilha"}, headers=emissor.cabecalho("flavio")
    )

    assert resposta.status_code == 200, resposta.text
    linhas = s3.enviados[0]["Body"].decode("utf-8-sig").split("\r\n")
    assert linhas[1:] == [
        (
            "2026-03-02;Feira!;-120,35;Corrente;;Casa | Mercado;casa nova | sábado;Flávio;"
            "efetivado;Flávio;Flávio"
        ),
        "2026-03-05;Salário;5000,00;Corrente;;Salário;;;efetivado;Flávio;Flávio",
        "2026-03-10;Guardar;1000,00;Corrente → Poupança;;Reserva;;;efetivado;Fulana;Fulana",
        "2026-03-28;Mercado;-50,00;Nubank;2026-04;Mercado;;;efetivado;Fulana;Fulana",
        "2026-04-05;Fatura Nubank;50,00;Corrente → Nubank;2026-04;;;;efetivado;Fulana;Fulana",
        "2026-04-26;Mercado;50,00;Nubank;2026-05;Mercado;;;efetivado;Flávio;Flávio",
        "2099-01-01;Futuro;-120,35;Corrente;;Mercado;;;previsto;Flávio;Flávio",
        "",
    ]


def test_planilha_traz_cada_parcela_com_o_numero_dela_como_no_mobills(
    database_url: str, emissor: Emissor, casal: Casal
):
    cartao = casal.pedir(
        "flavio",
        "POST",
        "/api/cartoes",
        json={"nome": "Nubank", "dia_fechamento": 25, "dia_vencimento": 5},
    ).json()["id"]
    casal.pedir(
        "flavio",
        "POST",
        "/api/parcelamentos",
        json={
            "id": str(uuid.uuid4()),
            "valor_total_centavos": 300001,
            "parcelas": 2,
            "data": "2026-03-28",
            "descricao": "Geladeira",
            "conta_id": cartao,
            "categoria_ids": [casal.categoria("Casa")],
        },
    )
    s3 = S3Falso()

    _cliente(database_url, emissor, s3).post(
        "/api/exportacoes", json={"formato": "planilha"}, headers=emissor.cabecalho("flavio")
    )

    linhas = s3.enviados[0]["Body"].decode("utf-8-sig").split("\r\n")
    assert linhas[1:] == [
        "2026-03-28;Geladeira (1/2);-1500,01;Nubank;2026-04;Casa;;;efetivado;Flávio;Flávio",
        "2026-03-28;Geladeira (2/2);-1500,00;Nubank;2026-05;Casa;;;efetivado;Flávio;Flávio",
        "",
    ]


def test_planilha_traz_uma_linha_por_ajuste_de_fatura_diferente_de_zero_e_fecha_com_o_mes(
    database_url: str, emissor: Emissor, casal: Casal
):
    novo = novo_cartao(casal)
    cartao, nome = novo["id"], novo["nome"]
    comprar(casal, cartao, "2026-04-02", valor_centavos=10000)
    casal.pedir(
        "flavio",
        "PATCH",
        f"/api/cartoes/{cartao}/faturas/2026-04-01",
        json={"ajuste_centavos": 2350},
    )
    casal.pedir(
        "flavio",
        "PATCH",
        f"/api/cartoes/{cartao}/faturas/2026-05-01",
        json={"ajuste_centavos": -500},
    )
    casal.pedir(
        "flavio", "PATCH", f"/api/cartoes/{cartao}/faturas/2026-06-01", json={"ajuste_centavos": 0}
    )
    s3 = S3Falso()

    _cliente(database_url, emissor, s3).post(
        "/api/exportacoes", json={"formato": "planilha"}, headers=emissor.cabecalho("flavio")
    )

    linhas = s3.enviados[0]["Body"].decode("utf-8-sig").split("\r\n")[1:-1]
    ajustes = [l for l in linhas if ";Ajuste de fatura " in l]
    assert ajustes == [
        f"2026-04-01;Ajuste de fatura {nome} 2026-04;-23,50;{nome};2026-04;;;;efetivado;;",
        f"2026-05-01;Ajuste de fatura {nome} 2026-05;5,00;{nome};2026-05;;;;efetivado;;",
    ]


def test_exportar_sem_token_e_recusado(database_url: str, emissor: Emissor, banco_ficticio):
    s3 = S3Falso()

    resposta = _cliente(database_url, emissor, s3).post(
        "/api/exportacoes", json={"formato": "backup"}
    )

    assert resposta.status_code == 401
    assert s3.enviados == []


def test_formato_desconhecido_e_recusado(database_url: str, emissor: Emissor, banco_ficticio):
    resposta = _cliente(database_url, emissor, S3Falso()).post(
        "/api/exportacoes", json={"formato": "pdf"}, headers=emissor.cabecalho("flavio")
    )

    assert resposta.status_code == 422


def test_sem_o_bucket_configurado_a_api_diz_que_nao_exporta(
    database_url: str, emissor: Emissor, banco_ficticio, monkeypatch
):
    monkeypatch.delenv("EXPORTACOES_BUCKET", raising=False)
    cliente = TestClient(create_app(database_url, verificador=emissor.verificador()))

    resposta = cliente.post(
        "/api/exportacoes", json={"formato": "backup"}, headers=emissor.cabecalho("flavio")
    )

    assert resposta.status_code == 503


def test_falha_ao_gravar_no_s3_nao_registra_a_exportacao(
    database_url: str, emissor: Emissor, banco_ficticio
):
    class S3Fora(S3Falso):
        def put_object(self, **pedido):
            raise RuntimeError("s3 fora")

    cliente = _cliente(database_url, emissor, S3Fora())
    cliente = TestClient(cliente.app, raise_server_exceptions=False)

    resposta = cliente.post(
        "/api/exportacoes", json={"formato": "backup"}, headers=emissor.cabecalho("flavio")
    )

    assert resposta.status_code == 500
    with psycopg.connect(database_url) as conn:
        assert conn.execute("SELECT count(*) FROM exportacoes").fetchone() == (0,)


# --- CSV de planilha: o formato que o Excel e o Google Planilhas abrem em português ---

LINHA = {
    "data": "2026-10-02",
    "descricao": 'Pão; "fresco"',
    "valor": "-1234.50",
    "conta_ou_cartao": "Nubank",
    "fatura": "2026-11",
    "categorias": ["Alimentação", "Casa"],
    "tags": ["feira"],
    "pessoa": "Flavio",
    "situacao": "efetivado",
    "criado_por": "flavio",
    "alterado_por": "esposa",
}


def test_planilha_usa_ponto_e_virgula_virgula_decimal_e_bom():
    dados = formatar_planilha([LINHA])

    assert dados.startswith(b"\xef\xbb\xbf")
    linhas = dados.decode("utf-8-sig").split("\r\n")
    assert linhas[0] == (
        "data;descricao;valor;conta_ou_cartao;fatura;categorias;tags;pessoa;situacao;"
        "criado_por;alterado_por"
    )
    assert linhas[1] == (
        '2026-10-02;"Pão; ""fresco""";-1234,50;Nubank;2026-11;Alimentação | Casa;feira;'
        "Flavio;efetivado;flavio;esposa"
    )


def test_planilha_vazia_traz_so_o_cabecalho():
    linhas = formatar_planilha([]).decode("utf-8-sig").split("\r\n")

    assert linhas[0].startswith("data;descricao;valor;")
    assert linhas[1:] == [""]
