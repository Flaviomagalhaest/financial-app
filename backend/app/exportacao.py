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
from psycopg.rows import dict_row

from app.backup import conferir_backup, gerar_backup
from app.banco import conectar, em_transacao
from app.lancamentos import MES_EM_QUE_CONTA, NO_CARTAO, PARCELAS
from app.pessoas import configuradas

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
    em_transacao(
        url,
        lambda conn: conn.execute(
            "INSERT INTO exportacoes (id, usuario, formato) VALUES (%s, %s, %s)",
            (id_, usuario, formato),
        ),
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
    """Lançamentos e transferências com nomes no lugar dos ids, de todo o histórico (sem filtro
    por período), em ordem de data. O excluído fica de fora, como em todas as leituras.

    A transferência sai numa linha, com "origem → destino" e o valor sem sinal: não é despesa
    nem receita (ADR 0014). A pessoa, quem criou e quem alterou saem pelo nome de `PESSOAS`.
    """
    pessoas = configuradas()
    contas = dict(conn.execute("SELECT id, nome FROM contas").fetchall())
    contas |= dict(conn.execute("SELECT id, nome FROM cartoes").fetchall())
    categorias: dict = {}
    for lancamento_id, nome in conn.execute(
        "SELECT lc.lancamento_id, c.nome FROM lancamento_categorias lc"
        " JOIN categorias c ON c.id = lc.categoria_id ORDER BY c.nome"
    ):
        categorias.setdefault(lancamento_id, []).append(nome)
    tags: dict = {}
    for lancamento_id, nome in conn.execute(
        "SELECT lt.lancamento_id, t.nome FROM lancamento_tags lt JOIN tags t ON t.id = lt.tag_id"
        " ORDER BY t.nome"
    ):
        tags.setdefault(lancamento_id, []).append(nome)

    def nome(pessoa: str | None) -> str:
        return pessoas.get(pessoa, pessoa) if pessoa else ""

    def linha(data, criado_em, situacao, criado_por, alterado_por, **colunas) -> tuple:
        # "efetivado" é a palavra do Mobills, que o casal conhece da planilha (ticket 25).
        return (
            data,
            criado_em,
            {
                "data": data.isoformat(),
                "situacao": "efetivado" if situacao == "realizado" else "previsto",
                "criado_por": nome(criado_por),
                "alterado_por": nome(alterado_por),
            }
            | colunas,
        )

    linhas = [
        linha(
            l["data"],
            l["criado_em"],
            l["situacao"],
            l["criado_por"],
            l["alterado_por"],
            # A parcela como o Mobills a escreve: "Geladeira (3/10)".
            descricao=(
                f"{l['descricao']} ({l['parcela']}/{l['parcelas']})".lstrip()
                if l["parcela"]
                else l["descricao"]
            ),
            valor=_reais(-l["valor"] if l["tipo"] == "despesa" else l["valor"]),
            conta_ou_cartao=contas.get(l["conta_id"], ""),
            fatura=l["mes"].strftime("%Y-%m") if l["no_cartao"] else "",
            categorias=categorias.get(l["id"], []),
            tags=tags.get(l["id"], []),
            pessoa=nome(l["pessoa"]),
        )
        for l in _dicionarios(
            conn,
            "SELECT id, tipo, situacao, valor_centavos AS valor, data, descricao, conta_id,"
            f" pessoa, criado_por, alterado_por, criado_em, {MES_EM_QUE_CONTA} AS mes,"
            f" {NO_CARTAO} AS no_cartao, parcela, {PARCELAS} AS parcelas"
            # As parcelas no cartão têm a mesma data: a ordem delas fica a do número.
            " FROM lancamentos WHERE excluido_em IS NULL ORDER BY parcela",
        )
    ] + [
        linha(
            t["data"],
            t["criado_em"],
            t["situacao"],
            t["criado_por"],
            t["alterado_por"],
            descricao=t["descricao"],
            valor=_reais(t["valor_centavos"]),
            conta_ou_cartao=(
                f"{contas.get(t['conta_origem_id'], '')} → {contas.get(t['conta_destino_id'], '')}"
            ),
            fatura="",
            categorias=[t["categoria"]] if t["categoria"] else [],
            tags=[],
            pessoa="",
        )
        for t in _dicionarios(
            conn,
            "SELECT t.*, c.nome AS categoria FROM transferencias t"
            " LEFT JOIN categorias c ON c.id = t.categoria_id",
        )
    ]
    return [colunas for *_, colunas in sorted(linhas, key=lambda linha: linha[:2])]


def _dicionarios(conn: psycopg.Connection, consulta: str) -> list[dict]:
    with conn.cursor(row_factory=dict_row) as cursor:
        return cursor.execute(consulta).fetchall()


def _reais(centavos: int) -> str:
    sinal = "-" if centavos < 0 else ""
    return f"{sinal}{abs(centavos) // 100}.{abs(centavos) % 100:02d}"


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
