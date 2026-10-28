import csv
import io
import zipfile
from datetime import datetime
from urllib.parse import parse_qs, urlparse

import psycopg
from fastapi.testclient import TestClient

from app.exportacao import formatar_planilha
from app.main import create_app
from tests.emissor import Emissor


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
        assert sorted(zip.namelist()) == [
            "contas.csv",
            "exportacoes.csv",
            "lancamentos.csv",
            "manifesto.json",
        ]
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
