"""Exportação a pedido (ADR 0012): `POST /api/exportacoes` gera o backup (zip) ou o CSV de
planilha, grava no bucket de exportações e devolve uma URL assinada de 5 minutos.

O backup usa o mesmo gerador do backup diário (`app.backup`). O CSV de planilha é um segundo
formato, só de leitura, com nomes no lugar dos ids.
"""

import csv
import io
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal
from zoneinfo import ZoneInfo

import psycopg
from psycopg import IsolationLevel

from app.backup import conferir_backup, gerar_backup
from app.banco import conectar

Formato = Literal["backup", "planilha"]
VALIDADE_DA_URL = 300
SAO_PAULO = ZoneInfo("America/Sao_Paulo")

COLUNAS_DA_PLANILHA = [
    "data",
    "descricao",
    "valor",
    "conta_ou_cartao",
    "fatura",
    "categorias",
    "tags",
    "pessoa",
    "situacao",
    "criado_por",
    "alterado_por",
]
TABELAS_DA_PLANILHA = {"lancamentos", "contas", "cartoes", "faturas", "categorias", "tags"}


@dataclass
class Exportacao:
    url: str
    arquivo: str
    expira_em: datetime


def exportar(s3, bucket: str, usuario: str, formato: Formato, url: str | None = None) -> Exportacao:
    """Gera o arquivo, grava no bucket, registra quem pediu e assina a URL de download."""
    agora = datetime.now(SAO_PAULO)
    id_ = uuid.uuid4()
    with conectar(url) as conn:
        # Tabelas, contagens e somas saem do mesmo instante do banco.
        conn.isolation_level = IsolationLevel.REPEATABLE_READ
        conn.read_only = True
        with conn.transaction():
            if formato == "backup":
                conteudo = gerar_backup(conn)
                conferir_backup(conn, conteudo)
            else:
                conteudo = formatar_planilha(ler_lancamentos(conn))
    if formato == "backup":
        extensao, tipo, prefixo = "zip", "application/zip", "financial-app-backup"
    else:
        extensao, tipo, prefixo = "csv", "text/csv; charset=utf-8", "financial-app-lancamentos"
    arquivo = f"{prefixo}-{agora.date().isoformat()}.{extensao}"
    chave = f"exportacoes/{id_}.{extensao}"
    s3.put_object(Bucket=bucket, Key=chave, Body=conteudo, ContentType=tipo)
    # Só depois de o arquivo existir: um pedido que falhou não conta como exportação.
    with conectar(url) as conn:
        conn.execute(
            "INSERT INTO exportacoes (id, usuario, formato) VALUES (%s, %s, %s)",
            (id_, usuario, formato),
        )
    assinada = s3.generate_presigned_url(
        "get_object",
        Params={
            "Bucket": bucket,
            "Key": chave,
            "ResponseContentType": tipo,
            "ResponseContentDisposition": f'attachment; filename="{arquivo}"',
        },
        ExpiresIn=VALIDADE_DA_URL,
    )
    expira_em = agora + timedelta(seconds=VALIDADE_DA_URL)
    return Exportacao(url=assinada, arquivo=arquivo, expira_em=expira_em)


def ler_lancamentos(conn: psycopg.Connection) -> list[dict]:
    """Lançamentos com nomes no lugar dos ids, de todo o histórico (sem filtro por período).

    As tabelas de lançamentos, contas, cartões e categorias ainda não existem (tickets 32, 36,
    37 e 40): enquanto faltarem, a planilha sai só com o cabeçalho. Ligar a consulta ao esquema
    real é o ticket 74.
    """
    existentes = {
        nome
        for (nome,) in conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
        )
    }
    if not TABELAS_DA_PLANILHA <= existentes:
        return []
    raise NotImplementedError("consulta da planilha: ticket 74")


def formatar_planilha(linhas: list[dict]) -> bytes:
    """CSV para o Excel e o Google Planilhas em português: `;`, vírgula decimal, UTF-8 com BOM."""
    texto = io.StringIO(newline="")
    escritor = csv.writer(texto, delimiter=";", lineterminator="\r\n")
    escritor.writerow(COLUNAS_DA_PLANILHA)
    for linha in linhas:
        escritor.writerow(
            [
                str(linha[coluna]).replace(".", ",")
                if coluna == "valor"
                else " | ".join(linha[coluna])
                if coluna in ("categorias", "tags")
                else linha[coluna]
                for coluna in COLUNAS_DA_PLANILHA
            ]
        )
    return texto.getvalue().encode("utf-8-sig")
