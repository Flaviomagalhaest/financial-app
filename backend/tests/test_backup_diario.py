import io
import json
import zipfile
from datetime import date

import pytest

from app.backup_diario import fazer_backup_diario


class S3Falso:
    """Só a fronteira com a AWS: guarda o que seria enviado ao bucket."""

    def __init__(self) -> None:
        self.enviados: list[dict] = []

    def put_object(self, **pedido) -> dict:
        self.enviados.append(pedido)
        return {"VersionId": "v1"}


def test_backup_diario_grava_o_zip_do_dia_no_bucket(database_url: str, banco_ficticio):
    s3 = S3Falso()

    fazer_backup_diario(s3, "bucket-de-backup", "dev", date(2026, 10, 28), database_url)

    (pedido,) = s3.enviados
    assert pedido["Bucket"] == "bucket-de-backup"
    assert pedido["Key"] == "diario/2026-10-28.zip"
    # O Object Lock exige checksum no envio de objeto com retenção.
    assert pedido["ChecksumAlgorithm"] == "SHA256"
    with zipfile.ZipFile(io.BytesIO(pedido["Body"])) as zip:
        assert sorted(zip.namelist()) == ["contas.csv", "lancamentos.csv", "manifesto.json"]


def test_backup_diario_concluido_publica_a_metrica_do_alarme(
    database_url: str,
    banco_ficticio,
    capsys: pytest.CaptureFixture[str],
):
    fazer_backup_diario(S3Falso(), "bucket-de-backup", "dev", date(2026, 10, 28), database_url)

    # Formato de métrica embutida do CloudWatch: a linha no log vira a métrica que o alarme
    # de 26 horas observa (infra/lib/pilha-app.ts).
    (linha,) = [linha for linha in capsys.readouterr().out.splitlines() if '"_aws"' in linha]
    metrica = json.loads(linha)
    assert metrica["_aws"]["CloudWatchMetrics"] == [
        {
            "Namespace": "FinancialApp",
            "Dimensions": [["Ambiente"]],
            "Metrics": [{"Name": "BackupsConcluidos", "Unit": "Count"}],
        }
    ]
    assert metrica["Ambiente"] == "dev"
    assert metrica["BackupsConcluidos"] == 1
