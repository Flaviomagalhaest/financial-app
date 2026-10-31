"""O lote da fila do aparelho: as ações feitas sem internet, na ordem, cada uma na sua transação
e com um resultado por ação (ADR 0011). O parcelamento e a recorrência vão como um pedido só, e o
servidor gera as parcelas e os previstos ao receber."""

import logging
from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

import psycopg
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app import parcelamentos, recorrencias
from app.banco import em_transacao
from app.lancamentos import (
    AlteracaoDeLancamento,
    CampoEmConflito,
    Confirmacao,
    ConflitoDeCampos,
    Exclusao,
    Lancamento,
    LancamentoExcluido,
    LancamentoNaoEncontrado,
    NovoLancamento,
    confirmar,
    criar,
    editar,
    excluir,
    url_do_banco,
)
from app.login import UsuarioLogado
from app.parcelamentos import NovoParcelamento, Parcelamento
from app.recorrencias import (
    AlteracaoDeRecorrencia,
    CamposDaRecorrencia,
    NovaRecorrencia,
    Recorrencia,
)

router = APIRouter(prefix="/api")
log = logging.getLogger(__name__)

LIMITE_DO_LOTE = 100


class AcaoCriar(BaseModel):
    acao: Literal["criar"]
    lancamento: NovoLancamento


class AcaoEditar(BaseModel):
    acao: Literal["editar"]
    id: UUID
    alteracao: AlteracaoDeLancamento


class AcaoExcluir(BaseModel):
    acao: Literal["excluir"]
    id: UUID
    # A versão que o aparelho tinha; sem ela, exclui de qualquer jeito.
    versao: int | None = None
    acao_em: datetime | None = None


class AcaoConfirmar(BaseModel):
    acao: Literal["confirmar"]
    id: UUID
    # A versão que o aparelho tinha e só os ajustes que a pessoa fez.
    confirmacao: Confirmacao


class AcaoCriarParcelamento(BaseModel):
    acao: Literal["criar_parcelamento"]
    parcelamento: NovoParcelamento


class AcaoCriarRecorrencia(BaseModel):
    acao: Literal["criar_recorrencia"]
    recorrencia: NovaRecorrencia


class AcaoAlterarRecorrencia(BaseModel):
    acao: Literal["alterar_recorrencia"]
    id: UUID
    alteracao: AlteracaoDeRecorrencia
    # A regra como a tela a mostrava, nos campos que a mudança traz: o que a outra pessoa mudou
    # depois nesses campos recusa a mudança, em vez de ser sobrescrito em silêncio.
    antes: CamposDaRecorrencia | None = None


class AcaoExcluirRecorrencia(BaseModel):
    acao: Literal["excluir_recorrencia"]
    id: UUID


Acao = (
    AcaoCriar
    | AcaoEditar
    | AcaoExcluir
    | AcaoConfirmar
    | AcaoCriarParcelamento
    | AcaoCriarRecorrencia
    | AcaoAlterarRecorrencia
    | AcaoExcluirRecorrencia
)


class Lote(BaseModel):
    acoes: list[Annotated[Acao, Field(discriminator="acao")]] = Field(
        min_length=1, max_length=LIMITE_DO_LOTE
    )


class Resultado(BaseModel):
    """`recusada` traz o motivo para mostrar; `conflito` traz o lançamento do servidor e os
    campos em conflito; `descartada` é a edição de algo já excluído, com quem excluiu. O
    parcelamento e a recorrência aceitos voltam gravados, e as parcelas e os previstos vêm na
    leitura dos lançamentos."""

    resultado: Literal["aceita", "conflito", "recusada", "descartada"]
    motivo: str | None = None
    lancamento: Lancamento | None = None
    parcelamento: Parcelamento | None = None
    recorrencia: Recorrencia | None = None
    campos: list[CampoEmConflito] | None = None
    exclusao: Exclusao | None = None


class ResultadoDoLote(BaseModel):
    resultados: list[Resultado]


def _aplicar(acao: Acao, usuario: str, request: Request) -> Resultado:
    """As mesmas regras das rotas de um lançamento só; a recusa de uma não para as outras.

    Banco fora do ar ou disputa perdida derrubam o lote inteiro, que o aparelho reenvia; outro
    erro fica só nesta ação, recusada, para não travar a fila para sempre.
    """
    try:
        return _executar(url_do_banco(request), acao, usuario)
    except LancamentoNaoEncontrado:
        return Resultado(resultado="recusada", motivo="lançamento não encontrado")
    except LancamentoExcluido as e:
        return Resultado(resultado="descartada", motivo=e.exclusao.motivo, exclusao=e.exclusao)
    except ConflitoDeCampos as e:
        conflito = e.conflito
        return Resultado(
            resultado="conflito",
            motivo=conflito.motivo,
            lancamento=conflito.lancamento,
            campos=conflito.campos,
        )
    except HTTPException as erro:
        # A regra que o aparelho mudou já não existe: a outra pessoa a excluiu.
        if erro.status_code == 404 and isinstance(acao, AcaoAlterarRecorrencia):
            return Resultado(resultado="recusada", motivo="a recorrência foi excluída")
        if erro.status_code == 422:
            return Resultado(resultado="recusada", motivo=erro.detail)
        raise
    except psycopg.OperationalError:
        raise
    except Exception:
        log.exception("ação do lote falhou")
        return Resultado(resultado="recusada", motivo="erro no servidor")


def _executar(url: str | None, acao: Acao, usuario: str) -> Resultado:
    """A ação aceita; a do lançamento numa transação, a do parcelamento e a da recorrência em
    várias."""
    match acao:
        case AcaoCriar(lancamento=novo):
            criado = em_transacao(url, lambda conn: criar(conn, novo, usuario)[0])
            return Resultado(resultado="aceita", lancamento=criado)
        case AcaoEditar(id=id, alteracao=alteracao):
            editado = em_transacao(url, lambda conn: editar(conn, id, alteracao, usuario))
            return Resultado(resultado="aceita", lancamento=editado)
        case AcaoConfirmar(id=id, confirmacao=confirmacao):
            confirmado = em_transacao(url, lambda conn: confirmar(conn, id, confirmacao, usuario))
            return Resultado(resultado="aceita", lancamento=confirmado)
        case AcaoExcluir(id=id, versao=versao, acao_em=acao_em):
            em_transacao(url, lambda conn: excluir(conn, id, versao, usuario, acao_em))
            return Resultado(resultado="aceita")
        case AcaoCriarParcelamento(parcelamento=novo):
            # Grava numa transação e gera as parcelas em outras (o limite de linhas do DSQL).
            criado, _ = parcelamentos.criar(url, novo, usuario)
            return Resultado(resultado="aceita", parcelamento=criado)
        case AcaoCriarRecorrencia(recorrencia=nova):
            # Grava numa transação e gera os previstos em outras, como o parcelamento.
            criada, _ = recorrencias.criar(url, nova, usuario)
            return Resultado(resultado="aceita", recorrencia=criada)
        case AcaoAlterarRecorrencia(id=id, alteracao=alteracao, antes=antes):
            # A regra numa transação e o reajuste dos previstos em outras, como na rota.
            alterada = recorrencias.alterar(url, id, alteracao, usuario, antes)
            return Resultado(resultado="aceita", recorrencia=alterada)
        case AcaoExcluirRecorrencia(id=id):
            recorrencias.excluir_regra(url, id, usuario)
            return Resultado(resultado="aceita")


@router.post("/lancamentos/lote", response_model=ResultadoDoLote, operation_id="enviar_lote")
def enviar_lote(lote: Lote, usuario: UsuarioLogado, request: Request) -> ResultadoDoLote:
    """A fila do aparelho: as ações na ordem, cada uma na sua transação, um resultado por ação."""
    return ResultadoDoLote(resultados=[_aplicar(a, usuario, request) for a in lote.acoes])
