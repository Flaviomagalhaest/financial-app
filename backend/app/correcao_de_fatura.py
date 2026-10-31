"""Correção de fatura: a fatura paga só muda por aqui, toda de uma vez (ADR 0021). Na mesma
transação acerta as datas e o ajuste, cria, edita e exclui compras e troca os pagamentos; as
regras da fatura paga valem no resultado, e o saldo anterior da seguinte se refaz sozinho, porque
é sempre calculado. Não existe estado "reaberta"."""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app import cartoes, faturas, lancamentos
from app.banco import conectar
from app.lancamentos import conferir_conta, recusar, url_do_banco
from app.login import UsuarioLogado

router = APIRouter(prefix="/api")


class PagamentoDaCorrecao(BaseModel):
    """Um pagamento realizado da fatura: o id que já existe é editado, o novo é criado."""

    id: UUID
    conta_origem_id: UUID
    valor_centavos: int = Field(gt=0)
    data: date
    descricao: str = ""


class CompraEditada(lancamentos.AlteracaoDeLancamento):
    id: UUID


class CompraExcluida(BaseModel):
    id: UUID
    versao: int | None = None


class CorrecaoDeFatura(cartoes.AlteracaoDeFatura):
    # Os pagamentos realizados da fatura depois da correção: o que não vem na lista sai. Sem o
    # campo, ficam como estão; a fatura continua paga, então a lista não vem vazia.
    pagamentos: list[PagamentoDaCorrecao] | None = Field(default=None, min_length=1)
    compras_novas: list[lancamentos.NovoLancamento] = Field(default_factory=list)
    compras_editadas: list[CompraEditada] = Field(default_factory=list)
    compras_excluidas: list[CompraExcluida] = Field(default_factory=list)


def _trocar_pagamentos(
    conn, titular: faturas.Titular, mes: date, pagamentos: list[PagamentoDaCorrecao], usuario: str
) -> None:
    atuais = dict(
        conn.execute(
            "SELECT t.id, t.conta_origem_id FROM transferencias t"
            " JOIN cartoes c ON c.id = t.conta_destino_id"
            " WHERE COALESCE(c.titular_id, c.id) = %s AND t.fatura_mes = %s"
            " AND t.situacao = 'realizado'",
            (titular.id, mes),
        ).fetchall()
    )
    for p in pagamentos:
        # A conta arquivada segue no pagamento que já saía dela (o histórico se edita).
        conferir_conta(conn, p.conta_origem_id, ja_ligada=atuais.get(p.id) == p.conta_origem_id)
        if p.id in atuais:
            conn.execute(
                "UPDATE transferencias SET conta_origem_id = %s, valor_centavos = %s, data = %s,"
                " descricao = %s, alterado_por = %s, alterado_em = now() WHERE id = %s",
                (p.conta_origem_id, p.valor_centavos, p.data, p.descricao, usuario, p.id),
            )
            continue
        if conn.execute("SELECT 1 FROM transferencias WHERE id = %s", (p.id,)).fetchone():
            raise recusar("o pagamento da correção é de outra fatura")
        conn.execute(
            "INSERT INTO transferencias (id, conta_origem_id, conta_destino_id, valor_centavos,"
            " data, descricao, situacao, fatura_mes, criado_por, alterado_por)"
            " VALUES (%s, %s, %s, %s, %s, %s, 'realizado', %s, %s, %s)",
            (
                p.id,
                p.conta_origem_id,
                titular.id,
                p.valor_centavos,
                p.data,
                p.descricao,
                mes,
                usuario,
                usuario,
            ),
        )
    ficam = {p.id for p in pagamentos}
    for id in atuais.keys() - ficam:
        conn.execute("DELETE FROM transferencias WHERE id = %s", (id,))


@router.post(
    "/cartoes/{id}/faturas/{mes}/correcao",
    response_model=cartoes.Fatura,
    operation_id="corrigir_fatura",
    responses={409: {"model": lancamentos.Conflito, "description": "Uma compra mudou depois"}},
)
def corrigir_fatura(
    id: UUID, mes: date, correcao: CorrecaoDeFatura, usuario: UsuarioLogado, request: Request
) -> cartoes.Fatura | JSONResponse:
    """Corrige a fatura paga de uma vez: datas e ajuste, compras novas, editadas e excluídas, e
    os pagamentos. Tudo ou nada: a correção que deixaria o pago acima do total, mexeria em outra
    fatura paga ou cairia num conflito não grava nada."""
    mes = faturas.mes_de(mes)
    with conectar(url_do_banco(request)) as conn:
        titular = cartoes.cartao_ou_404(conn, id).titular

    def gravar(conn) -> cartoes.Fatura:
        fatura = next(iter(cartoes.faturas_do_titular(conn, titular.id, mes)), None)
        if not fatura or not cartoes.paga_pelo_pagamento(fatura):
            raise recusar("só a fatura paga se corrige")
        datas_e_ajuste = cartoes.AlteracaoDeFatura(
            **correcao.model_dump(include=set(cartoes.AlteracaoDeFatura.model_fields))
        )
        cartoes.alterar_fatura(conn, titular, mes, datas_e_ajuste, usuario)
        for excluida in correcao.compras_excluidas:
            lancamentos.excluir(conn, excluida.id, excluida.versao, usuario)
        for editada in correcao.compras_editadas:
            alteracao = lancamentos.AlteracaoDeLancamento(**editada.model_dump(exclude={"id"}))
            lancamentos.editar(conn, editada.id, alteracao, usuario)
        for nova in correcao.compras_novas:
            lancamentos.criar(conn, nova, usuario)
        if correcao.pagamentos is not None:
            _trocar_pagamentos(conn, titular, mes, correcao.pagamentos, usuario)
        return cartoes.faturas_do_titular(conn, titular.id, mes)[0]

    return lancamentos.na_rota(request, gravar, corrigida=(titular.id, mes))
