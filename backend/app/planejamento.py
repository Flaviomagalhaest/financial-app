"""Planejamento do mês (ADR 0006): itens de uma categoria e um valor, comparados com o que
conta neles. Não é lançamento e não mexe em saldo."""

from datetime import date
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Path, Request, Response
from pydantic import BaseModel, Field

from app.banco import conectar, em_transacao
from app.lancamentos import recusar, url_do_banco
from app.login import UsuarioLogado

router = APIRouter(prefix="/api")

Mes = Annotated[str, Path(pattern=r"^\d{4}-(0[1-9]|1[0-2])$", examples=["2026-10"])]


def _primeiro_dia(mes: str) -> date:
    ano, numero = map(int, mes.split("-"))
    return date(ano, numero, 1)


def _proximo_mes(dia: date) -> date:
    return date(dia.year + dia.month // 12, dia.month % 12 + 1, 1)


class NovoItem(BaseModel):
    id: UUID
    categoria_id: UUID
    valor_centavos: int = Field(gt=0)


class ItemDoPlanejamento(BaseModel):
    id: UUID
    categoria_id: UUID
    planejado_centavos: int
    realizado_centavos: int
    previsto_centavos: int
    # (realizado + previsto) sobre o planejado, arredondado; passa de 100 quando estoura.
    percentual: int
    # Planejado menos realizado e previsto; negativo quando o item estoura.
    ainda_da_para_gastar_centavos: int


class Planejamento(BaseModel):
    mes: str
    itens: list[ItemDoPlanejamento]
    # A soma do que falta em cada item, sem compensar item estourado com a sobra de outro.
    ainda_da_para_gastar_centavos: int


class ItemDoModelo(BaseModel):
    categoria_id: UUID
    valor_centavos: int = Field(gt=0)


class ModeloPadrao(BaseModel):
    itens: list[ItemDoModelo]


class CopiaDeMes(BaseModel):
    de: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$", examples=["2026-09"])


class MudancaDeItem(BaseModel):
    valor_centavos: int = Field(gt=0)


def _movimentos_por_item(conn, mes: date, categorias_com_item: dict[UUID, UUID]):
    """(item, situacao, valor) de cada lançamento e transferência do mês que conta em um item:
    automaticamente, quando só uma das categorias dele tem item no mês. O lançamento com mais de
    uma (a escolha é do ticket 51) ainda não conta em nenhum."""
    ate = _proximo_mes(mes)
    movimentos: list[tuple[UUID, str, int]] = []
    por_lancamento: dict[UUID, tuple[str, int, set[UUID]]] = {}
    for id, situacao, valor, categoria_id in conn.execute(
        "SELECT l.id, l.situacao, l.valor_centavos, lc.categoria_id FROM lancamentos l"
        " JOIN lancamento_categorias lc ON lc.lancamento_id = l.id"
        " WHERE l.excluido_em IS NULL AND l.data >= %s AND l.data < %s"
        " AND lc.categoria_id = ANY(%s)",
        (mes, ate, list(categorias_com_item)),
    ):
        por_lancamento.setdefault(id, (situacao, valor, set()))[2].add(categoria_id)
    for situacao, valor, categorias in por_lancamento.values():
        if len(categorias) == 1:
            movimentos.append((categorias_com_item[next(iter(categorias))], situacao, valor))
    for situacao, valor, categoria_id in conn.execute(
        "SELECT situacao, valor_centavos, categoria_id FROM transferencias"
        " WHERE data >= %s AND data < %s AND categoria_id = ANY(%s)",
        (mes, ate, list(categorias_com_item)),
    ):
        movimentos.append((categorias_com_item[categoria_id], situacao, valor))
    return movimentos


def _ler(conn, mes: str) -> Planejamento:
    dia = _primeiro_dia(mes)
    linhas = conn.execute(
        "SELECT id, categoria_id, valor_centavos FROM itens_do_planejamento WHERE mes = %s"
        " ORDER BY criado_em, id",
        (dia,),
    ).fetchall()
    item_da_categoria = {categoria_id: id for id, categoria_id, _ in linhas}
    somas: dict[UUID, dict[str, int]] = {id: {"realizado": 0, "previsto": 0} for id, _, _ in linhas}
    if linhas:
        for item, situacao, valor in _movimentos_por_item(conn, dia, item_da_categoria):
            somas[item][situacao] += valor
    itens = [
        ItemDoPlanejamento(
            id=id,
            categoria_id=categoria_id,
            planejado_centavos=planejado,
            realizado_centavos=somas[id]["realizado"],
            previsto_centavos=somas[id]["previsto"],
            percentual=round((somas[id]["realizado"] + somas[id]["previsto"]) * 100 / planejado),
            ainda_da_para_gastar_centavos=planejado
            - somas[id]["realizado"]
            - somas[id]["previsto"],
        )
        for id, categoria_id, planejado in linhas
    ]
    return Planejamento(
        mes=mes,
        itens=itens,
        ainda_da_para_gastar_centavos=sum(max(i.ainda_da_para_gastar_centavos, 0) for i in itens),
    )


def _gravar_itens(conn, dia: date, itens, usuario: str) -> None:
    for categoria_id, valor in itens:
        conn.execute(
            "INSERT INTO itens_do_planejamento (id, mes, categoria_id, valor_centavos,"
            " criado_por, alterado_por) VALUES (%s, %s, %s, %s, %s, %s)",
            (uuid4(), dia, categoria_id, valor, usuario, usuario),
        )


def _gravar_itens_no_mes_vazio(conn, dia: date, itens, usuario: str) -> None:
    if conn.execute("SELECT 1 FROM itens_do_planejamento WHERE mes = %s", (dia,)).fetchone():
        raise HTTPException(status_code=409, detail="o mês já tem itens")
    _gravar_itens(conn, dia, itens, usuario)


def _item(conn, id: UUID) -> ItemDoPlanejamento:
    mes = conn.execute("SELECT mes FROM itens_do_planejamento WHERE id = %s", (id,)).fetchone()
    if not mes:
        raise HTTPException(status_code=404, detail="item não encontrado")
    return next(i for i in _ler(conn, mes[0].strftime("%Y-%m")).itens if i.id == id)


def _modelo(conn) -> ModeloPadrao:
    return ModeloPadrao(
        itens=[
            ItemDoModelo(categoria_id=categoria_id, valor_centavos=valor)
            for categoria_id, valor in conn.execute(
                "SELECT categoria_id, valor_centavos FROM modelo_do_planejamento"
                " ORDER BY alterado_em, categoria_id"
            )
        ]
    )


# As rotas do modelo vêm antes das de `{mes}`, para "modelo" não ser lido como mês.
@router.get("/planejamento/modelo", response_model=ModeloPadrao, operation_id="ler_modelo_padrao")
def ler_modelo(usuario: UsuarioLogado, request: Request) -> ModeloPadrao:
    with conectar(url_do_banco(request)) as conn:
        return _modelo(conn)


@router.put(
    "/planejamento/modelo", response_model=ModeloPadrao, operation_id="definir_modelo_padrao"
)
def definir_modelo(modelo: ModeloPadrao, usuario: UsuarioLogado, request: Request) -> ModeloPadrao:
    """Troca o modelo padrão inteiro pelo conjunto enviado (categoria e valor, sem repetir)."""
    categorias = [i.categoria_id for i in modelo.itens]
    if len(set(categorias)) != len(categorias):
        raise recusar("categoria repetida no modelo")

    def gravar(conn):
        achadas = conn.execute(
            "SELECT count(*) FROM categorias WHERE id = ANY(%s)", (categorias,)
        ).fetchone()[0]
        if achadas != len(categorias):
            raise recusar("categoria não encontrada")
        conn.execute("DELETE FROM modelo_do_planejamento")
        for item in modelo.itens:
            conn.execute(
                "INSERT INTO modelo_do_planejamento (categoria_id, valor_centavos, alterado_por)"
                " VALUES (%s, %s, %s)",
                (item.categoria_id, item.valor_centavos, usuario),
            )
        return _modelo(conn)

    return em_transacao(url_do_banco(request), gravar)


@router.post(
    "/planejamento/{mes}/aplicar-modelo",
    status_code=201,
    response_model=Planejamento,
    operation_id="aplicar_modelo_padrao",
)
def aplicar_modelo(mes: Mes, usuario: UsuarioLogado, request: Request) -> Planejamento:
    """Cria os itens do modelo padrão neste mês, que precisa estar vazio."""

    def gravar(conn):
        dia = _primeiro_dia(mes)
        itens = [(i.categoria_id, i.valor_centavos) for i in _modelo(conn).itens]
        if not itens:
            raise recusar("o modelo padrão está vazio")
        _gravar_itens_no_mes_vazio(conn, dia, itens, usuario)
        return _ler(conn, mes)

    return em_transacao(url_do_banco(request), gravar)


@router.get("/planejamento/{mes}", response_model=Planejamento, operation_id="ler_planejamento")
def ler_planejamento(mes: Mes, usuario: UsuarioLogado, request: Request) -> Planejamento:
    with conectar(url_do_banco(request)) as conn:
        return _ler(conn, mes)


@router.post(
    "/planejamento/{mes}/itens",
    status_code=201,
    response_model=ItemDoPlanejamento,
    operation_id="criar_item_do_planejamento",
)
def criar_item(
    mes: Mes, novo: NovoItem, usuario: UsuarioLogado, request: Request, response: Response
) -> ItemDoPlanejamento:
    def gravar(conn):
        dia = _primeiro_dia(mes)
        existente = conn.execute(
            "SELECT mes, categoria_id, valor_centavos FROM itens_do_planejamento WHERE id = %s",
            (novo.id,),
        ).fetchone()
        if existente:
            # A fila ou o toque repetido reenvia o mesmo id: devolve o gravado.
            if existente[:2] != (dia, novo.categoria_id):
                raise HTTPException(status_code=409, detail="id já usado por outro item")
            response.status_code = 200
            return _item(conn, novo.id)
        if not conn.execute(
            "SELECT 1 FROM categorias WHERE id = %s", (novo.categoria_id,)
        ).fetchone():
            raise recusar("categoria não encontrada")
        if conn.execute(
            "SELECT 1 FROM itens_do_planejamento WHERE mes = %s AND categoria_id = %s",
            (dia, novo.categoria_id),
        ).fetchone():
            raise HTTPException(status_code=409, detail="a categoria já tem item neste mês")
        conn.execute(
            "INSERT INTO itens_do_planejamento (id, mes, categoria_id, valor_centavos,"
            " criado_por, alterado_por) VALUES (%s, %s, %s, %s, %s, %s)",
            (novo.id, dia, novo.categoria_id, novo.valor_centavos, usuario, usuario),
        )
        return _item(conn, novo.id)

    return em_transacao(url_do_banco(request), gravar)


@router.post(
    "/planejamento/{mes}/copiar",
    status_code=201,
    response_model=Planejamento,
    operation_id="copiar_planejamento",
)
def copiar_planejamento(
    mes: Mes, copia: CopiaDeMes, usuario: UsuarioLogado, request: Request
) -> Planejamento:
    """Copia os itens (categoria e valor) de outro mês para este, que precisa estar vazio."""
    if copia.de == mes:
        raise recusar("a origem é o próprio mês")

    def gravar(conn):
        dia = _primeiro_dia(mes)
        itens = conn.execute(
            "SELECT categoria_id, valor_centavos FROM itens_do_planejamento WHERE mes = %s",
            (_primeiro_dia(copia.de),),
        ).fetchall()
        if not itens:
            raise recusar("o mês de origem não tem itens")
        _gravar_itens_no_mes_vazio(conn, dia, itens, usuario)
        return _ler(conn, mes)

    return em_transacao(url_do_banco(request), gravar)


@router.patch(
    "/planejamento/itens/{id}",
    response_model=ItemDoPlanejamento,
    operation_id="mudar_item_do_planejamento",
)
def mudar_item(
    id: UUID, mudanca: MudancaDeItem, usuario: UsuarioLogado, request: Request
) -> ItemDoPlanejamento:
    def gravar(conn):
        _item(conn, id)  # 404 se não existe
        conn.execute(
            "UPDATE itens_do_planejamento SET valor_centavos = %s, alterado_por = %s,"
            " alterado_em = now() WHERE id = %s",
            (mudanca.valor_centavos, usuario, id),
        )
        return _item(conn, id)

    return em_transacao(url_do_banco(request), gravar)


@router.delete(
    "/planejamento/itens/{id}", status_code=204, operation_id="excluir_item_do_planejamento"
)
def excluir_item(id: UUID, usuario: UsuarioLogado, request: Request) -> Response:
    """Idempotente. Os lançamentos ficam como estão: só deixam de contar no item."""
    em_transacao(
        url_do_banco(request),
        lambda conn: conn.execute("DELETE FROM itens_do_planejamento WHERE id = %s", (id,)),
    )
    return Response(status_code=204)
