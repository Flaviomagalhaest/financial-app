"""Transferência entre duas contas do casal: não é despesa nem receita, só move o saldo.
Tabela própria porque o DSQL não altera o `CHECK` do tipo dos lançamentos (ADR 0014)."""

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

from app.banco import conectar
from app.lancamentos import conferir_conta, recusar, situacao_pela_data, url_do_banco
from app.login import UsuarioLogado

router = APIRouter(prefix="/api")


class NovaTransferencia(BaseModel):
    id: UUID
    conta_origem_id: UUID
    conta_destino_id: UUID
    valor_centavos: int = Field(gt=0)
    data: date
    descricao: str = ""
    # Opcional, e só da lista de categorias de transferência.
    categoria_id: UUID | None = None
    situacao: Literal["previsto", "realizado"] | None = None


class Transferencia(NovaTransferencia):
    situacao: Literal["previsto", "realizado"]
    criado_por: str
    criado_em: datetime
    alterado_por: str
    alterado_em: datetime


_COLUNAS = (
    "id, conta_origem_id, conta_destino_id, valor_centavos, data, descricao, categoria_id,"
    " situacao, criado_por, criado_em, alterado_por, alterado_em"
)

_NOMES_DAS_COLUNAS = _COLUNAS.replace(" ", "").split(",")


def _ler_transferencias(conn, id: UUID | None = None) -> list[Transferencia]:
    filtro, parametros = ("WHERE id = %s", (id,)) if id else ("", ())
    linhas = conn.execute(
        f"SELECT {_COLUNAS} FROM transferencias {filtro} ORDER BY data DESC, criado_em DESC, id",
        parametros,
    ).fetchall()
    return [Transferencia(**dict(zip(_NOMES_DAS_COLUNAS, linha))) for linha in linhas]


def _conferir_transferencia(
    conn, t: NovaTransferencia, atual: tuple[UUID, UUID] | None = None
) -> None:
    if t.conta_origem_id == t.conta_destino_id:
        raise recusar("origem e destino são a mesma conta")
    # Arquivada só segue com quem já estava nela (o histórico se edita).
    conferir_conta(conn, t.conta_origem_id, ja_ligada=bool(atual) and t.conta_origem_id == atual[0])
    conferir_conta(
        conn, t.conta_destino_id, ja_ligada=bool(atual) and t.conta_destino_id == atual[1]
    )
    if t.categoria_id:
        tipo = conn.execute(
            "SELECT tipo FROM categorias WHERE id = %s", (t.categoria_id,)
        ).fetchone()
        if not tipo:
            raise recusar("categoria não encontrada")
        if tipo[0] != "transferencia":
            raise recusar(f"categoria de {tipo[0]} numa transferência")


@router.post(
    "/transferencias",
    status_code=201,
    response_model=Transferencia,
    operation_id="criar_transferencia",
)
def criar_transferencia(
    nova: NovaTransferencia, usuario: UsuarioLogado, request: Request, response: Response
) -> Transferencia:
    """Reenviar o mesmo id (a fila repete) devolve o que já está gravado, com 200."""
    with conectar(url_do_banco(request)) as conn:
        _conferir_transferencia(conn, nova)
        gravadas = conn.execute(
            "INSERT INTO transferencias (id, conta_origem_id, conta_destino_id, valor_centavos,"
            " data, descricao, categoria_id, situacao, criado_por, alterado_por)"
            " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT (id) DO NOTHING",
            (
                nova.id,
                nova.conta_origem_id,
                nova.conta_destino_id,
                nova.valor_centavos,
                nova.data,
                nova.descricao,
                nova.categoria_id,
                nova.situacao or situacao_pela_data(nova.data),
                usuario,
                usuario,
            ),
        ).rowcount
        if not gravadas:
            response.status_code = 200
        return _ler_transferencias(conn, nova.id)[0]


@router.get(
    "/transferencias", response_model=list[Transferencia], operation_id="listar_transferencias"
)
def listar_transferencias(usuario: UsuarioLogado, request: Request) -> list[Transferencia]:
    with conectar(url_do_banco(request)) as conn:
        return _ler_transferencias(conn)


@router.put(
    "/transferencias/{id}", response_model=Transferencia, operation_id="editar_transferencia"
)
def editar_transferencia(
    id: UUID, editada: NovaTransferencia, usuario: UsuarioLogado, request: Request
) -> Transferencia:
    if editada.id != id:
        raise recusar("o id do corpo difere do id da URL")
    with conectar(url_do_banco(request)) as conn:
        atual = conn.execute(
            "SELECT data, situacao, conta_origem_id, conta_destino_id FROM transferencias"
            " WHERE id = %s",
            (id,),
        ).fetchone()
        if not atual:
            raise HTTPException(status_code=404, detail="transferência não encontrada")
        data_atual, situacao_atual, origem, destino = atual
        _conferir_transferencia(conn, editada, (origem, destino))
        # Como no lançamento: sem situação no pedido, só mudar a data refaz a inferência.
        if editada.situacao:
            situacao = editada.situacao
        elif editada.data != data_atual:
            situacao = situacao_pela_data(editada.data)
        else:
            situacao = situacao_atual
        conn.execute(
            "UPDATE transferencias SET conta_origem_id = %s, conta_destino_id = %s,"
            " valor_centavos = %s, data = %s, descricao = %s, categoria_id = %s, situacao = %s,"
            " alterado_por = %s, alterado_em = now() WHERE id = %s",
            (
                editada.conta_origem_id,
                editada.conta_destino_id,
                editada.valor_centavos,
                editada.data,
                editada.descricao,
                editada.categoria_id,
                situacao,
                usuario,
                id,
            ),
        )
        return _ler_transferencias(conn, id)[0]


@router.delete("/transferencias/{id}", status_code=204, operation_id="excluir_transferencia")
def excluir_transferencia(id: UUID, usuario: UsuarioLogado, request: Request) -> Response:
    """Idempotente: excluir o que já não existe também dá 204."""
    with conectar(url_do_banco(request)) as conn:
        conn.execute("DELETE FROM transferencias WHERE id = %s", (id,))
    return Response(status_code=204)
