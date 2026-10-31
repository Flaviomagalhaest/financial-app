"""Filtros salvos (ticket 60): buscas que o casal guarda com nome e repete com um toque. Guardam os
critérios, a ordenação e o período, relativo ("este mês", resolvido a cada leitura) ou fixo (os dois
dias nos critérios). São do casal inteiro e, como as demais mudanças, precisam de internet (ADR 0011)."""

import json
from datetime import date, timedelta
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field, field_validator

from app.banco import conectar, em_transacao
from app.busca import CriteriosDaBusca, PedidoDeBusca
from app.lancamentos import hoje, url_do_banco
from app.login import UsuarioLogado

router = APIRouter(prefix="/api")

PeriodoRelativo = Literal["este_mes", "mes_passado", "este_ano", "ultimos_30_dias"]


def periodo_de(relativo: PeriodoRelativo, dia: date) -> tuple[date, date]:
    """Os dois dias (inclusive) do período relativo, vistos de `dia`."""
    if relativo == "este_mes":
        inicio = dia.replace(day=1)
        return inicio, _fim_do_mes(inicio)
    if relativo == "mes_passado":
        inicio = (dia.replace(day=1) - timedelta(days=1)).replace(day=1)
        return inicio, _fim_do_mes(inicio)
    if relativo == "este_ano":
        return date(dia.year, 1, 1), date(dia.year, 12, 31)
    return dia - timedelta(days=29), dia


def _fim_do_mes(inicio: date) -> date:
    return (inicio.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)


def _nome_aparado(nome: str) -> str:
    nome = nome.strip()
    if not nome:
        raise ValueError("o nome não pode ficar vazio")
    return nome


class DadosDoFiltroSalvo(BaseModel):
    nome: str = Field(min_length=1)
    # Com período relativo, o período dos critérios é ignorado.
    criterios: CriteriosDaBusca
    ordem: Literal["recentes", "valor"] = "recentes"
    periodo_relativo: PeriodoRelativo | None = None

    _nome = field_validator("nome")(_nome_aparado)


class NovoFiltroSalvo(DadosDoFiltroSalvo):
    id: UUID


class FiltroSalvo(NovoFiltroSalvo):
    # O que a busca recebe hoje: os critérios com o período relativo já resolvido.
    pedido: PedidoDeBusca


class NovoNome(BaseModel):
    nome: str = Field(min_length=1)

    _nome = field_validator("nome")(_nome_aparado)


def _pedido(dados: DadosDoFiltroSalvo) -> PedidoDeBusca:
    criterios = dados.criterios.model_copy()
    if dados.periodo_relativo:
        criterios.periodo_de, criterios.periodo_ate = periodo_de(dados.periodo_relativo, hoje())
    return PedidoDeBusca(**criterios.model_dump(), ordem=dados.ordem)


def _filtros(conn) -> list[FiltroSalvo]:
    filtros = []
    for id, nome, criterios, ordem, relativo in conn.execute(
        "SELECT id, nome, criterios, ordem, periodo_relativo FROM filtros_salvos"
        " ORDER BY lower(nome), criado_em, id"
    ):
        dados = DadosDoFiltroSalvo(
            nome=nome,
            criterios=CriteriosDaBusca(**json.loads(criterios)),
            ordem=ordem,
            periodo_relativo=relativo,
        )
        filtros.append(FiltroSalvo(id=id, **dados.model_dump(), pedido=_pedido(dados)))
    return filtros


@router.get(
    "/filtros-salvos", response_model=list[FiltroSalvo], operation_id="listar_filtros_salvos"
)
def listar_filtros_salvos(usuario: UsuarioLogado, request: Request) -> list[FiltroSalvo]:
    with conectar(url_do_banco(request)) as conn:
        return _filtros(conn)


@router.post(
    "/filtros-salvos", status_code=201, response_model=FiltroSalvo, operation_id="salvar_filtro"
)
def salvar_filtro(
    novo: NovoFiltroSalvo, usuario: UsuarioLogado, request: Request, response: Response
) -> FiltroSalvo:
    """Reenviar o mesmo id devolve o que já está gravado, com 200."""

    def gravar(conn) -> FiltroSalvo:
        if not conn.execute("SELECT 1 FROM filtros_salvos WHERE id = %s", (novo.id,)).fetchone():
            criterios = novo.criterios.model_copy()
            if novo.periodo_relativo:
                criterios.periodo_de = criterios.periodo_ate = None
            conn.execute(
                "INSERT INTO filtros_salvos (id, nome, criterios, ordem, periodo_relativo,"
                " criado_por, alterado_por) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (
                    novo.id,
                    novo.nome,
                    criterios.model_dump_json(),
                    novo.ordem,
                    novo.periodo_relativo,
                    usuario,
                    usuario,
                ),
            )
        else:
            response.status_code = 200
        return next(f for f in _filtros(conn) if f.id == novo.id)

    return em_transacao(url_do_banco(request), gravar)


@router.put("/filtros-salvos/{id}", response_model=FiltroSalvo, operation_id="renomear_filtro")
def renomear_filtro(
    id: UUID, novo: NovoNome, usuario: UsuarioLogado, request: Request
) -> FiltroSalvo:
    def renomear(conn) -> FiltroSalvo:
        atualizado = conn.execute(
            "UPDATE filtros_salvos SET nome = %s, alterado_por = %s, alterado_em = now()"
            " WHERE id = %s",
            (novo.nome, usuario, id),
        ).rowcount
        if not atualizado:
            raise HTTPException(status_code=404, detail="filtro salvo não encontrado")
        return next(f for f in _filtros(conn) if f.id == id)

    return em_transacao(url_do_banco(request), renomear)


@router.delete("/filtros-salvos/{id}", status_code=204, operation_id="excluir_filtro")
def excluir_filtro(id: UUID, usuario: UsuarioLogado, request: Request) -> Response:
    """Idempotente."""
    em_transacao(
        url_do_banco(request),
        lambda conn: conn.execute("DELETE FROM filtros_salvos WHERE id = %s", (id,)),
    )
    return Response(status_code=204)
