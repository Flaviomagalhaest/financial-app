"""Backup diário: o EventBridge Scheduler chama esta Lambda, que gera o backup, confere o zip
contra o banco e grava no bucket com Object Lock (ADR 0012). O alarme de 26 horas observa a
métrica publicada no fim; sem ela, ou com erro na Lambda, o dono recebe e-mail."""

import json
import os
import time
from datetime import UTC, date, datetime

import boto3
from psycopg import IsolationLevel

from app.backup import conferir_backup, gerar_backup
from app.banco import PAPEL_DO_BACKUP, conectar


def fazer_backup_diario(s3, bucket: str, ambiente: str, dia: date, url: str | None = None) -> str:
    """Grava `diario/AAAA-MM-DD.zip` e devolve a chave; levanta erro se o zip não bater."""
    with conectar(url, papel=PAPEL_DO_BACKUP) as conn:
        # A geração e a conferência leem o mesmo instante do banco.
        conn.isolation_level = IsolationLevel.REPEATABLE_READ
        conn.read_only = True
        with conn.transaction():
            backup = gerar_backup(conn)
            conferir_backup(conn, backup)
    chave = f"diario/{dia.isoformat()}.zip"
    # O Object Lock exige checksum em todo envio de objeto com retenção.
    s3.put_object(
        Bucket=bucket,
        Key=chave,
        Body=backup,
        ContentType="application/zip",
        ChecksumAlgorithm="SHA256",
    )
    _publicar_metrica(ambiente, "BackupsConcluidos", 1)
    return chave


def _publicar_metrica(ambiente: str, nome: str, valor: int) -> None:
    """Métrica embutida no log (formato EMF do CloudWatch): sem chamada de API nem permissão."""
    print(
        json.dumps(
            {
                "_aws": {
                    "Timestamp": int(time.time() * 1000),
                    "CloudWatchMetrics": [
                        {
                            "Namespace": "FinancialApp",
                            "Dimensions": [["Ambiente"]],
                            "Metrics": [{"Name": nome, "Unit": "Count"}],
                        }
                    ],
                },
                "Ambiente": ambiente,
                nome: valor,
            }
        ),
        flush=True,
    )


def handler(evento: dict, contexto) -> dict:
    chave = fazer_backup_diario(
        boto3.client("s3"),
        os.environ["BACKUP_BUCKET"],
        os.environ["AMBIENTE"],
        datetime.now(UTC).date(),
    )
    return {"chave": chave}
