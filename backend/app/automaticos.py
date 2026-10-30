"""O automático: o previsto de uma recorrência de valor fixo ou de um parcelamento que vira
realizado sozinho, sem confirmação, quando chega o dia (ADR 0004). A tarefa diária o realiza."""

from datetime import UTC, datetime
from uuid import UUID

from app import lancamentos, parcelamentos, recorrencias
from app.banco import conectar, em_transacao
from app.lancamentos import registrar_mudancas, subir_versao

# O previsto automático com data até o dia do parâmetro.
_DEVIDO = (
    "l.situacao = 'previsto' AND COALESCE(l.automatico, false) AND l.excluido_em IS NULL"
    " AND l.data <= %s"
)


def _chegou(conn, conta_id: UUID, parcela: int | None, mes, data) -> bool:
    """A data já chegou (a consulta confere); a parcela no cartão espera a fatura de antes
    fechar."""
    if parcela is None:
        return True
    return parcelamentos.realiza_em(conn, conta_id, parcela, mes, data) <= lancamentos.hoje()


def _realizar(conn, id: UUID) -> bool:
    """Realiza o previsto automático, se ele ainda for um: a leitura fora da transação pode ter
    envelhecido (alguém confirmou ou excluiu no meio)."""
    linha = conn.execute(
        f"SELECT {lancamentos.VERSAO}, l.conta_id, l.parcela, l.mes, l.data,"
        " r.descricao, r.alterado_por, p.descricao, p.alterado_por FROM lancamentos l"
        " LEFT JOIN recorrencias r ON r.id = l.recorrencia_id"
        " LEFT JOIN parcelamentos p ON p.id = l.parcelamento_id"
        f" WHERE l.id = %s AND {_DEVIDO}",
        (id, lancamentos.hoje()),
    ).fetchone()
    if not linha:
        return False
    (
        versao,
        conta_id,
        parcela,
        mes,
        data,
        recorrencia,
        quem_na_recorrencia,
        parcelamento,
        quem_no_parcelamento,
    ) = linha
    if not _chegou(conn, conta_id, parcela, mes, data):
        return False
    if parcelamento is not None:
        origem, quem = parcelamentos.origem(parcelamento), quem_no_parcelamento
    else:
        origem, quem = recorrencias.origem(recorrencia), quem_na_recorrencia
    # Quem responde pela regra é quem a mudou por último; a `origem` diz que foi a regra.
    nova = subir_versao(
        conn, id, versao, "situacao = 'realizado', alterado_por = %s, alterado_em = now()", (quem,)
    )
    registrar_mudancas(conn, id, ["situacao"], nova, quem, datetime.now(UTC), origem=origem)
    return True


def realizar_automaticos(url: str | None, parcelamento_id: UUID | None = None) -> int:
    """Vira realizado, sem confirmação, cada previsto automático que chegou, um por transação;
    devolve quantos. Com `parcelamento_id`, só as parcelas dele (depois de corrigido)."""
    with conectar(url) as conn:
        devidos = [
            id
            for id, conta_id, parcela, mes, data in conn.execute(
                "SELECT l.id, l.conta_id, l.parcela, l.mes, l.data FROM lancamentos l"
                f" WHERE {_DEVIDO}" + (" AND l.parcelamento_id = %s" if parcelamento_id else ""),
                (lancamentos.hoje(), *([parcelamento_id] if parcelamento_id else [])),
            ).fetchall()
            if _chegou(conn, conta_id, parcela, mes, data)
        ]
    return sum(em_transacao(url, lambda conn, id=id: _realizar(conn, id)) for id in devidos)
