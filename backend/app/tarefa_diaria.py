"""Tarefa diária: o EventBridge Scheduler chama esta Lambda logo depois da meia-noite de São
Paulo. Ela estende as recorrências até o horizonte do dia, completa os parcelamentos cuja
geração parou no meio e realiza os previstos automáticos que chegaram (ADR 0004). Rodar de novo
no mesmo dia não muda nada."""

from app.automaticos import realizar_automaticos
from app.parcelamentos import completar_todos
from app.recorrencias import estender_todas


def fazer_tarefa_diaria(url: str | None = None) -> dict:
    # Primeiro gera: o automático que acabou de nascer com data de hoje já nasce realizado.
    recorrencias = estender_todas(url)
    parcelamentos = completar_todos(url)
    realizados = realizar_automaticos(url)
    return {"recorrencias": recorrencias, "parcelamentos": parcelamentos, "realizados": realizados}


def handler(evento: dict, contexto) -> dict:
    return fazer_tarefa_diaria()
