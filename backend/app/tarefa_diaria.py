"""Tarefa diária: o EventBridge Scheduler chama esta Lambda logo depois da meia-noite de São
Paulo. Ela estende as recorrências até o horizonte do dia e realiza os previstos automáticos
com data até hoje (ADR 0004). Rodar de novo no mesmo dia não muda nada."""

from app.recorrencias import estender_todas, realizar_automaticos


def fazer_tarefa_diaria(url: str | None = None) -> dict:
    # Primeiro gera: o automático que acabou de nascer com data de hoje já nasce realizado.
    recorrencias = estender_todas(url)
    realizados = realizar_automaticos(url)
    return {"recorrencias": recorrencias, "realizados": realizados}


def handler(evento: dict, contexto) -> dict:
    return fazer_tarefa_diaria()
