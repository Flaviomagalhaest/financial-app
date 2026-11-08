"""A edição em lote (ticket 24, ticket 61): nos marcados da busca, ou em todos do resultado,
acrescenta, tira, troca ou substitui categorias e tags de uma vez. Mostra a prévia, aplica tudo
ou nada e se desfaz por `desfazerEdicaoEmLoteDias` dias, pulando o que mudou depois. Só com
internet: não entra na fila nem gera conflito (ADR 0011).

O DSQL aceita até 3.000 linhas por transação, então o lote grava em partes de uma transação cada
e, se uma parte é recusada, desfaz as anteriores: o tudo ou nada vale para o resultado, como na
restauração (ADR 0012)."""

import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from functools import partial
from typing import Literal, NamedTuple
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.backup import LINHAS_POR_LOTE
from app.banco import conectar, em_transacao
from app.busca import CriteriosDaBusca, lancamentos_do_resultado, partes_achadas_no_resultado
from app.config import valores_iniciais
from app.item_em_que_conta import guardar_item_atual, onde_conta
from app.lancamentos import (
    Lancamento,
    Parte,
    acompanhar_estornos,
    acompanhar_estornos_do_parcelamento,
    gravar_categorias,
    ids_das_tags,
    ler_por_ids,
    recusar,
    registrar_mudancas,
    sem_repetidas,
    subir_versao,
    tags_limpas,
    url_do_banco,
)
from app.login import UsuarioLogado
from app.parcelamentos import ler_um, origem
from app.partes import id_na_parcela

router = APIRouter(prefix="/api")
_log = logging.getLogger(__name__)

# Cada lançamento grava a linha dele, a versão de até três campos, o registro do desfazer e as
# ligações de categoria e tag, apagadas e gravadas de novo (umas quinze, com folga); o
# parcelamento dele, uma vez por lote, grava as dele.
LINHAS_POR_LANCAMENTO = 20
POR_TRANSACAO = max(1, LINHAS_POR_LOTE // LINHAS_POR_LANCAMENTO)
# Uma gravação que passa disto (a Lambda da API tem 29 s, então é folga) parou no meio: a tarefa
# diária e o reenvio desfazem o lote.
PARADO_HA = timedelta(minutes=5)
PRAZO_EM_DIAS: int = valores_iniciais()["desfazerEdicaoEmLoteDias"]
TAMANHO_DA_AMOSTRA: int = valores_iniciais()["amostraDaEdicaoEmLote"]
# Os campos que o lote muda (na compra com partes, as partes): mudou um deles depois, o desfazer
# pula o lançamento. Nas partes, o desfazer olha cada uma (`_voltar_partes`).
CAMPOS_DA_COMPRA = ["categoria_ids", "tags", "item_categoria_id"]
CAMPOS_DO_LOTE = [*CAMPOS_DA_COMPRA, "partes"]

Acao = Literal["acrescentar", "remover", "trocar", "substituir"]


def _conferir_por(acao: Acao, por) -> None:
    if (acao == "trocar") != (por is not None):
        raise ValueError("só o trocar tem `por`, e ele é obrigatório")


class MudancaDeCategorias(BaseModel):
    acao: Acao
    # As que entram (acrescentar, substituir) ou as que saem (remover, trocar).
    categoria_ids: list[UUID] = Field(min_length=1)
    # Só no trocar: a que entra no lugar das que saem.
    por: UUID | None = None

    _categorias = field_validator("categoria_ids")(sem_repetidas)

    @model_validator(mode="after")
    def _por_so_no_trocar(self):
        _conferir_por(self.acao, self.por)
        if self.por in self.categoria_ids:
            raise ValueError("trocar uma categoria por ela mesma")
        return self


class MudancaDeTags(BaseModel):
    acao: Acao
    # Pelo nome, sem distinguir maiúsculas; substituir por nenhuma tira todas.
    tags: list[str]
    por: str | None = None

    _tags = field_validator("tags")(tags_limpas)

    @model_validator(mode="after")
    def _completa(self):
        _conferir_por(self.acao, self.por)
        if self.por is not None:
            (self.por,) = tags_limpas([self.por])
        if not self.tags and self.acao != "substituir":
            raise ValueError("nenhuma tag")
        return self


class SelecaoDoLote(BaseModel):
    """Os marcados no resultado e, com `busca`, todos do resultado com esses critérios. A parcela
    marcada leva o parcelamento todo, e a compra leva os estornos dela (ADR 0016)."""

    model_config = ConfigDict(extra="forbid")

    lancamento_ids: list[UUID] = []
    parcelamento_ids: list[UUID] = []
    busca: CriteriosDaBusca | None = None


class PedidoDeEdicaoEmLote(BaseModel):
    selecao: SelecaoDoLote
    categorias: MudancaDeCategorias | None = None
    tags: MudancaDeTags | None = None

    @model_validator(mode="after")
    def _alguma_mudanca(self):
        if not self.categorias and not self.tags:
            raise ValueError("nenhuma mudança pedida")
        return self


class NovaEdicaoEmLote(PedidoDeEdicaoEmLote):
    # Nasce no aparelho: reenviar o mesmo id devolve o lote gravado, sem aplicar de novo.
    id: UUID


class AntesEDepois(BaseModel):
    # Como está agora.
    lancamento: Lancamento
    # Como fica.
    categoria_ids: list[UUID]
    tags: list[str]
    # Na compra com partes, que não tem categorias nem tags próprias: as partes como ficam.
    partes: list[Parte] = []


class PreviaDaEdicaoEmLote(BaseModel):
    # As linhas da busca (o parcelamento conta como uma) e os lançamentos que elas têm.
    compras: int
    lancamentos: int
    mudam: int
    ja_estao_como_pedido: int
    # A categoria pedida é de outro tipo (de despesa numa receita): as categorias dele ficam.
    de_outro_tipo: int
    # Lançamentos e partes que passam a contar em outro item do planejamento, ou em nenhum
    # (ADR 0006); não impede.
    trocam_de_item: int
    # Estornos marcados sem a compra: o estorno segue a compra (ADR 0016) e fica de fora.
    estornos_fora: int
    # Das compras com partes que mudam (contadas em `mudam`), as partes que mudam: a mudança vale
    # em cada parte (ADR 0022) ou, na busca com filtro de categoria, tag ou pessoa, nas que ela
    # achou.
    partes_que_mudam: int
    # Os primeiros que mudam, na ordem da busca.
    amostra: list[AntesEDepois]
    # Por que aplicar recusaria o lote inteiro; sem ela, aplica.
    recusa: str | None


class EdicaoEmLote(BaseModel):
    id: UUID
    # A mudança em palavras: "Categorias: trocar Mercado por Feira · Tags: tirar #viagem".
    resumo: str
    # `aplicando` fica quando a gravação parou no meio: desfazer volta o que já foi gravado.
    situacao: Literal["aplicando", "aplicada", "desfeita"]
    # Quantos lançamentos mudaram.
    lancamentos: int
    criado_por: str
    criado_em: datetime
    desfazer_ate: datetime


class PuladoNoDesfazer(BaseModel):
    lancamento_id: UUID
    descricao: str
    # A parte pulada da compra com partes; vazios quando o pulado é o lançamento inteiro. A parte
    # apagada vem sem descrição: o lote não a guarda.
    parte_id: UUID | None = None
    parte_descricao: str = ""
    # `mudou_depois`: alguém mudou as categorias, as tags ou o item depois do lote; `excluido`;
    # `saiu`: uma categoria ou tag de antes do lote foi juntada a outra ou excluída.
    motivo: Literal["mudou_depois", "excluido", "saiu"]
    # Quem mudou ou excluiu depois, e quando.
    alterado_por: str | None
    alterado_em: datetime | None
    por_voce: bool


class DesfazerDaEdicaoEmLote(BaseModel):
    desfeitos: int
    pulados: list[PuladoNoDesfazer]


class LoteRecusado(Exception):
    def __init__(self, motivo: str) -> None:
        self.motivo = motivo


def _sem_categoria(lancamentos: int, partes: int = 0) -> str:
    ficariam = [
        f"{n} {nome}{'s' * (n != 1)}"
        for n, nome in ((lancamentos, "lançamento"), (partes, "parte"))
        if n
    ]
    return f"o lote deixaria {' e '.join(ficariam)} sem categoria"


class _Mudancas:
    """As mudanças conferidas no banco: as categorias que entram existem, não estão arquivadas e
    são do mesmo tipo; as tags valem pelo nome que já têm, e a arquivada não entra."""

    def __init__(self, conn, pedido: PedidoDeEdicaoEmLote) -> None:
        self.categorias, self.tags = pedido.categorias, pedido.tags
        self.tipo: str | None = None
        self.nomes_das_categorias: dict[UUID, str] = {}
        self._tags_existentes: dict[str, str] = {}
        if c := self.categorias:
            entram = _entram(c.acao, c.categoria_ids, c.por)
            lidas = {
                id: (nome, tipo, arquivada)
                for id, nome, tipo, arquivada in conn.execute(
                    "SELECT id, nome, tipo, arquivada_em IS NOT NULL FROM categorias"
                    " WHERE id = ANY(%s)",
                    ([*c.categoria_ids, *entram],),
                )
            }
            if {*c.categoria_ids, *entram} - lidas.keys():
                raise recusar("categoria não encontrada")
            if any(lidas[id][2] for id in entram):
                raise recusar("categoria arquivada")
            tipos = {lidas[id][1] for id in [*c.categoria_ids, *entram]} if entram else set()
            if len(tipos) > 1:
                raise recusar("categorias de tipos diferentes")
            if "transferencia" in tipos:
                raise recusar("categoria de transferência num lançamento")
            self.tipo = next(iter(tipos), None)
            self.nomes_das_categorias = {id: nome for id, (nome, _, _) in lidas.items()}
        if t := self.tags:
            existentes = {
                nome.casefold(): (nome, arquivada)
                for nome, arquivada in conn.execute(
                    "SELECT nome, arquivada_em IS NOT NULL FROM tags"
                )
            }
            for nome in _entram(t.acao, t.tags, t.por):
                if existentes.get(nome.casefold(), ("", False))[1]:
                    raise recusar(f"tag arquivada: {nome}")
            self._tags_existentes = {chave: nome for chave, (nome, _) in existentes.items()}

    def nome_da_tag(self, nome: str) -> str:
        return self._tags_existentes.get(nome.casefold(), nome)

    def depois(
        self, tipo: str, categorias: list[UUID], tags: list[str]
    ) -> tuple[list[UUID], list[str], bool]:
        """As categorias e as tags (de um lançamento ou de um parcelamento) depois do lote, e se
        a categoria pedida é de outro tipo (aí as categorias ficam como estão)."""
        categorias, tags, outro_tipo = list(categorias), list(tags), False
        if c := self.categorias:
            if c.acao in ("acrescentar", "substituir") and self.tipo != tipo:
                outro_tipo = True
            else:
                categorias = _aplicar(c.acao, categorias, c.categoria_ids, c.por, lambda x: x)
        if t := self.tags:
            pedidas = [self.nome_da_tag(n) for n in t.tags]
            por = t.por and self.nome_da_tag(t.por)
            tags = _aplicar(t.acao, tags, pedidas, por, str.casefold)
        return categorias, tags, outro_tipo

    def partes_depois(
        self, tipo: str, partes: list[Parte], achadas: set[UUID] | None
    ) -> tuple[list[Parte], set[UUID], bool]:
        """As partes depois do lote, as que mudam e se a categoria pedida é de outro tipo. A
        mudança vale em cada parte ou, com `achadas` (a busca com filtro de classificação), só
        nelas; a escolha do item sai com a categoria dela, como no lançamento."""
        depois, mudam, outro_tipo = [], set(), False
        for p in partes:
            if achadas is not None and p.id not in achadas:
                depois.append(p)
                continue
            categorias, tags, outro = self.depois(tipo, p.categoria_ids, p.tags)
            outro_tipo |= outro
            if any(_mudou(p, categorias, tags)):
                mudam.add(p.id)
                escolhida = p.item_categoria_id if p.item_categoria_id in categorias else None
                p = p.model_copy(
                    update={
                        "categoria_ids": categorias,
                        "tags": tags,
                        "item_categoria_id": escolhida,
                    }
                )
            depois.append(p)
        return depois, mudam, outro_tipo

    def resumo(self) -> str:
        partes = []
        if c := self.categorias:
            nome = self.nomes_das_categorias.__getitem__
            partes.append(
                "Categorias: "
                + _frase(c.acao, [nome(id) for id in c.categoria_ids], c.por and nome(c.por))
            )
        if t := self.tags:
            partes.append(
                "Tags: "
                + _frase(
                    t.acao,
                    [f"#{self.nome_da_tag(n)}" for n in t.tags],
                    t.por and f"#{self.nome_da_tag(t.por)}",
                )
            )
        return " · ".join(partes)


def _entram[T](acao: Acao, valores: list[T], por: T | None) -> list[T]:
    """O que a mudança põe nos lançamentos."""
    if acao == "trocar":
        return [por]
    return [] if acao == "remover" else valores


def _aplicar[T](acao: Acao, atuais: list[T], pedidos: list[T], por: T | None, chave) -> list[T]:
    tem = {chave(v) for v in atuais}
    saem = {chave(v) for v in pedidos}
    match acao:
        case "acrescentar":
            return atuais + [v for v in pedidos if chave(v) not in tem]
        case "remover":
            return [v for v in atuais if chave(v) not in saem]
        case "trocar":
            if not tem & saem:
                return atuais
            ficam = [v for v in atuais if chave(v) not in saem]
            return ficam + [por] * (chave(por) not in {chave(v) for v in ficam})
        case "substituir":
            return list(pedidos)


def _frase(acao: Acao, nomes: list[str], por: str | None) -> str:
    match acao:
        case "acrescentar":
            return f"acrescentar {', '.join(nomes)}"
        case "remover":
            return f"tirar {', '.join(nomes)}"
        case "trocar":
            return f"trocar {', '.join(nomes)} por {por}"
        case "substituir":
            return f"substituir por {', '.join(nomes)}" if nomes else "tirar todas"


def _mudou(l: Lancamento | Parte, categorias: list[UUID], tags: list[str]) -> tuple[bool, bool]:
    return (
        set(categorias) != set(l.categoria_ids),
        {t.casefold() for t in tags} != {t.casefold() for t in l.tags},
    )


def _selecionados(
    conn, selecao: SelecaoDoLote
) -> tuple[list[Lancamento], int, dict[UUID, set[UUID]]]:
    """Os lançamentos do lote, quantos estornos marcados ficaram de fora sem a compra e, das
    compras com partes e dos parcelamentos com partes que a busca trouxe, as partes que ela achou
    (`_partes_achadas`)."""
    ids, parcelamentos = list(selecao.lancamento_ids), list(selecao.parcelamento_ids)
    avulsos: list[UUID] = []
    achados: list[UUID] = []
    if selecao.busca:
        avulsos, achados = lancamentos_do_resultado(conn, selecao.busca)
        ids, parcelamentos = ids + avulsos, parcelamentos + achados
    marcados = [
        id
        for (id,) in conn.execute(
            "SELECT id FROM lancamentos WHERE excluido_em IS NULL AND (id = ANY(%s)"
            " OR parcelamento_id = ANY(%s) OR parcelamento_id IN"
            " (SELECT parcelamento_id FROM lancamentos WHERE id = ANY(%s)))",
            (ids, parcelamentos, ids),
        )
    ]
    # O estorno segue a compra: vem com ela e não muda sozinho.
    estornos = dict(
        conn.execute(
            "SELECT id, estorno_de FROM lancamentos WHERE excluido_em IS NULL"
            " AND (id = ANY(%s) OR estorno_de = ANY(%s))",
            (marcados, marcados),
        ).fetchall()
    )
    fora = {id for id, compra in estornos.items() if compra and compra not in marcados}
    lidos = ler_por_ids(conn, list(({*marcados} | estornos.keys()) - fora))
    achadas = (
        _partes_achadas(conn, selecao.busca, lidos, {*avulsos}, {*achados}) if selecao.busca else {}
    )
    return lidos, len(fora), achadas


def _partes_achadas(
    conn,
    busca: CriteriosDaBusca,
    lidos: list[Lancamento],
    avulsos: set[UUID],
    parcelamentos: set[UUID],
) -> dict[UUID, set[UUID]]:
    """Na busca com filtro de categoria, tag ou pessoa, o lote muda só as partes que ela achou
    (ticket 150): as de cada compra que veio dela e, no parcelamento, as dele cuja parte numa
    parcela ela achou. A linha também marcada à mão segue a busca. Sem o filtro, nenhuma: a
    mudança vale em todas as partes."""
    da_busca = [
        l.id for l in lidos if l.partes and (l.id in avulsos or l.parcelamento_id in parcelamentos)
    ]
    achadas = partes_achadas_no_resultado(conn, busca, da_busca)
    if achadas is None:
        return {}
    for parcelamento_id in parcelamentos:
        regra = ler_um(conn, parcelamento_id)
        if not regra or not regra.partes:
            continue
        achadas[parcelamento_id] = {
            p.id
            for l in lidos
            if l.parcelamento_id == parcelamento_id and l.id in achadas
            for p in _partes_do_parcelamento_achadas(regra.partes, l, achadas[l.id])
        }
    return achadas


def _partes_do_parcelamento_achadas(
    partes: list[Parte], parcela: Lancamento, achadas: set[UUID]
) -> list[Parte]:
    """As partes do parcelamento que a busca achou numa parcela. A parcela com partes refeitas
    "só esta" (ids que não vêm de `id_na_parcela`) vale pela posição, se tem tantas partes quanto o
    parcelamento."""
    if all(id_na_parcela(parcela.id, p.id) in {q.id for q in parcela.partes} for p in partes):
        return [p for p in partes if id_na_parcela(parcela.id, p.id) in achadas]
    if len(parcela.partes) != len(partes):
        return []
    return [p for p, propria in zip(partes, parcela.partes) if propria.id in achadas]


def _itens_por_mes(conn, meses: set[date]) -> dict[date, set[UUID]]:
    """As categorias com item do planejamento em cada mês."""
    itens: dict[date, set[UUID]] = {}
    for mes, categoria in conn.execute(
        "SELECT mes, categoria_id FROM itens_do_planejamento WHERE mes = ANY(%s)", (list(meses),)
    ):
        itens.setdefault(mes, set()).add(categoria)
    return itens


def _itens_atuais(conn, ids: list[UUID]) -> dict[UUID, UUID | None]:
    return dict(
        conn.execute(
            "SELECT id, item_atual_categoria_id FROM lancamentos WHERE id = ANY(%s)", (ids,)
        ).fetchall()
    )


def _item_depois(
    l: Lancamento, categorias: list[UUID], item_atual: UUID | None
) -> tuple[UUID | None, UUID | None]:
    """A escolha e o item atual depois do lote: cada um sai com a categoria dele, como na
    edição de um lançamento."""
    return (
        l.item_categoria_id if l.item_categoria_id in categorias else None,
        item_atual if item_atual in categorias else None,
    )


@dataclass
class _Muda:
    """Um lançamento que o lote muda, com as categorias e as tags de depois. A compra com partes
    não tem as próprias (ADR 0022): muda nas partes, que vêm como ficam, com as que mudam."""

    lancamento: Lancamento
    categorias: list[UUID]
    tags: list[str]
    partes: list[Parte] = field(default_factory=list)
    nas_partes: set[UUID] = field(default_factory=set)

    @property
    def partes_sem_categoria(self) -> int:
        return _partes_sem_categoria(self.partes, self.nas_partes)


def _partes_sem_categoria(partes: list[Parte], nas_partes: set[UUID]) -> int:
    """Das partes que o lote muda, as que ficariam sem categoria."""
    return sum(not p.categoria_ids for p in partes if p.id in nas_partes)


@dataclass
class _Plano:
    mudancas: _Mudancas
    lancamentos: list[Lancamento]
    estornos_fora: int
    mudam: list[_Muda]
    ja_estao_como_pedido: int
    de_outro_tipo: int
    sem_categoria: int
    partes_sem_categoria: int
    # As partes que a busca achou, por compra e por parcelamento (`_partes_achadas`).
    achadas: dict[UUID, set[UUID]]

    @property
    def recusa(self) -> str | None:
        if self.sem_categoria or self.partes_sem_categoria:
            return _sem_categoria(self.sem_categoria, self.partes_sem_categoria)
        return None


def _o_que_muda(
    mudancas: _Mudancas, l: Lancamento, achadas: dict[UUID, set[UUID]]
) -> tuple[_Muda | None, bool]:
    """O que o lote muda num lançamento (nada, se ele já está como pedido) e se a categoria pedida
    é de outro tipo."""
    if l.partes:
        partes, nas_partes, outro_tipo = mudancas.partes_depois(l.tipo, l.partes, achadas.get(l.id))
        return (_Muda(l, [], [], partes, nas_partes) if nas_partes else None), outro_tipo
    categorias, tags, outro_tipo = mudancas.depois(l.tipo, l.categoria_ids, l.tags)
    return (_Muda(l, categorias, tags) if any(_mudou(l, categorias, tags)) else None), outro_tipo


def _planejar(conn, pedido: PedidoDeEdicaoEmLote) -> _Plano:
    mudancas = _Mudancas(conn, pedido)
    lancamentos, estornos_fora, achadas = _selecionados(conn, pedido.selecao)
    # O estorno da compra com partes segue a parte estornada (ticket 138): muda com ela.
    com_partes = {l.id for l in lancamentos if l.partes}
    lancamentos = [l for l in lancamentos if l.estorno_de not in com_partes]
    mudam, ja_estao, de_outro_tipo, sem_categoria, partes_sem_categoria = [], 0, 0, 0, 0
    for l in lancamentos:
        muda, outro_tipo = _o_que_muda(mudancas, l, achadas)
        de_outro_tipo += outro_tipo
        if not muda:
            # A parcela cujas partes a busca não achou não foi pedida: não "já está como pedido".
            nao_achada = bool(l.parcelamento_id and l.partes and achadas.get(l.id) == set())
            ja_estao += not (outro_tipo or nao_achada)
            continue
        mudam.append(muda)
        if l.partes:
            partes_sem_categoria += muda.partes_sem_categoria
        else:
            sem_categoria += not muda.categorias
    return _Plano(
        mudancas,
        lancamentos,
        estornos_fora,
        mudam,
        ja_estao,
        de_outro_tipo,
        sem_categoria,
        partes_sem_categoria,
        achadas,
    )


def _troca_de_item(
    com_item: set[UUID],
    antes: list[UUID],
    escolhida: UUID | None,
    atual: UUID | None,
    depois: list[UUID],
) -> bool:
    """Se um lançamento ou uma parte passa a contar em outro item (ou em nenhum) quando as
    categorias vão de `antes` para `depois`; a escolha sai com a categoria dela."""
    conta_antes, _ = onde_conta(com_item & {*antes}, escolhida, atual)
    escolhida_depois = escolhida if escolhida in depois else None
    conta_depois, _ = onde_conta(com_item & {*depois}, escolhida_depois, conta_antes)
    return conta_antes != conta_depois


def _trocam_de_item(conn, plano: _Plano) -> int:
    itens = _itens_por_mes(conn, {m.lancamento.mes for m in plano.mudam})
    atuais = _itens_atuais(conn, [m.lancamento.id for m in plano.mudam])
    atuais_das_partes = dict(
        conn.execute(
            "SELECT id, item_atual_categoria_id FROM lancamento_partes WHERE id = ANY(%s)",
            ([id for m in plano.mudam for id in m.nas_partes],),
        ).fetchall()
    )
    trocam = 0
    for m in plano.mudam:
        l, com_item = m.lancamento, itens.get(m.lancamento.mes, set())
        if not l.partes:
            trocam += _troca_de_item(
                com_item, l.categoria_ids, l.item_categoria_id, atuais[l.id], m.categorias
            )
            continue
        for antes, depois in zip(l.partes, m.partes):
            if antes.id in m.nas_partes:
                trocam += _troca_de_item(
                    com_item,
                    antes.categoria_ids,
                    antes.item_categoria_id,
                    atuais_das_partes.get(antes.id),
                    depois.categoria_ids,
                )
    return trocam


def _partes_que_mudam(mudam: list[_Muda]) -> int:
    """As partes que o lote muda: no parcelamento, as da compra (cada posição uma vez), não as de
    cada parcela."""
    avulsas = 0
    do_parcelamento: dict[UUID, set[int]] = {}
    for m in mudam:
        posicoes = {i for i, p in enumerate(m.lancamento.partes) if p.id in m.nas_partes}
        if m.lancamento.parcelamento_id and m.lancamento.partes:
            do_parcelamento.setdefault(m.lancamento.parcelamento_id, set()).update(posicoes)
        else:
            avulsas += len(posicoes)
    return avulsas + sum(len(posicoes) for posicoes in do_parcelamento.values())


def previa(conn, pedido: PedidoDeEdicaoEmLote) -> PreviaDaEdicaoEmLote:
    plano = _planejar(conn, pedido)
    return PreviaDaEdicaoEmLote(
        compras=len({l.parcelamento_id or l.id for l in plano.lancamentos}),
        lancamentos=len(plano.lancamentos),
        mudam=len(plano.mudam),
        partes_que_mudam=_partes_que_mudam(plano.mudam),
        ja_estao_como_pedido=plano.ja_estao_como_pedido,
        de_outro_tipo=plano.de_outro_tipo,
        trocam_de_item=_trocam_de_item(conn, plano),
        estornos_fora=plano.estornos_fora,
        amostra=[
            AntesEDepois(
                lancamento=m.lancamento, categoria_ids=m.categorias, tags=m.tags, partes=m.partes
            )
            for m in plano.mudam[:TAMANHO_DA_AMOSTRA]
        ],
        recusa=plano.recusa,
    )


def _tags_das(conn, ids: list[UUID]) -> dict[UUID, list[UUID]]:
    tags: dict[UUID, list[UUID]] = {id: [] for id in ids}
    for lancamento, tag in conn.execute(
        "SELECT lancamento_id, tag_id FROM lancamento_tags WHERE lancamento_id = ANY(%s)", (ids,)
    ):
        tags[lancamento].append(tag)
    return tags


def _religar(conn, tabela: str, dono: str, ligado: str, id: UUID, ids: list[UUID]) -> None:
    """Troca as ligações de `id` em `tabela` (categorias ou tags de um lançamento ou de um
    parcelamento) pelas de `ids`."""
    conn.execute(f"DELETE FROM {tabela} WHERE {dono} = %s", (id,))
    for ligado_id in ids:
        conn.execute(f"INSERT INTO {tabela} ({dono}, {ligado}) VALUES (%s, %s)", (id, ligado_id))


def _existem(conn, categorias: list[UUID], tags: list[UUID]) -> bool:
    """As categorias e as tags ainda existem: nenhuma foi juntada a outra nem excluída."""
    (existem,) = conn.execute(
        "SELECT (SELECT count(*) FROM categorias WHERE id = ANY(%s))"
        " + (SELECT count(*) FROM tags WHERE id = ANY(%s))",
        (categorias, tags),
    ).fetchone()
    return existem == len(categorias) + len(tags)


def _json(ids) -> str:
    return json.dumps([str(id) for id in ids])


def _ids(texto: str) -> list[UUID]:
    return [UUID(id) for id in json.loads(texto)]


def _origem_da_parcela(conn, lancamento: Lancamento) -> str | None:
    """O lote leva o parcelamento inteiro: a parcela muda com ele, não à mão só nela (ticket
    136), e a tela de conflito diz que foi o parcelamento."""
    if not lancamento.parcelamento_id:
        return None
    linha = conn.execute(
        "SELECT descricao FROM parcelamentos WHERE id = %s", (lancamento.parcelamento_id,)
    ).fetchone()
    return origem(linha[0] if linha else lancamento.descricao)


def _regravar(
    conn,
    atual: Lancamento,
    categorias: list[UUID] | None,
    tags: list[UUID] | None,
    item: tuple[UUID | None, UUID | None],
    usuario: str,
    momento: datetime,
) -> int:
    """Grava a classificação de um lançamento (categorias ou tags `None` ficam como estão) e a
    escolha e o item atual do planejamento; sobe a versão, registra os campos que mudaram e
    devolve a versão nova."""
    escolhida, item_atual = item
    versao = subir_versao(
        conn,
        atual.id,
        atual.versao,
        "item_categoria_id = %s, item_atual_categoria_id = %s, alterado_por = %s, alterado_em = %s",
        (escolhida, item_atual, usuario, momento),
    )
    mudaram = (categorias is not None, tags is not None, escolhida != atual.item_categoria_id)
    campos = [campo for campo, mudou in zip(CAMPOS_DO_LOTE, mudaram) if mudou]
    registrar_mudancas(
        conn, atual.id, campos, versao, usuario, momento, origem=_origem_da_parcela(conn, atual)
    )
    if categorias is not None:
        gravar_categorias(conn, atual.id, categorias)
    if tags is not None:
        _religar(conn, "lancamento_tags", "lancamento_id", "tag_id", atual.id, tags)
    return versao


# As tabelas das partes da compra e das do parcelamento: categorias, tags e as partes.
_TABELAS_DAS_PARTES = {
    "lancamento": ("parte_categorias", "parte_tags", "lancamento_partes"),
    "parcelamento": (
        "parcelamento_parte_categorias",
        "parcelamento_parte_tags",
        "parcelamento_partes",
    ),
}


def _mudar_partes(
    conn,
    lote_id: UUID,
    dono_id: UUID,
    de: str,
    antes: list[Parte],
    depois: list[Parte],
    nas_partes: set[UUID],
    usuario: str,
) -> None:
    """Grava a classificação das partes que o lote muda (de uma compra ou de um parcelamento) e
    guarda a de antes e a de depois para o desfazer. A parte da compra segue no item em que
    contava, se a categoria dele continua nela, como no lançamento."""
    categorias_das_partes, tags_das_partes, tabela = _TABELAS_DAS_PARTES[de]
    for parte, nova in zip(antes, depois):
        if parte.id not in nas_partes:
            continue
        tags_antes = [
            t
            for (t,) in conn.execute(
                f"SELECT tag_id FROM {tags_das_partes} WHERE parte_id = %s", (parte.id,)
            )
        ]
        tag_ids = ids_das_tags(conn, nova.tags, usuario, set(tags_antes))
        _religar(
            conn, categorias_das_partes, "parte_id", "categoria_id", parte.id, nova.categoria_ids
        )
        _religar(conn, tags_das_partes, "parte_id", "tag_id", parte.id, tag_ids)
        item_atual = None
        if de == "lancamento":
            (item_atual,) = conn.execute(
                "SELECT item_atual_categoria_id FROM lancamento_partes WHERE id = %s", (parte.id,)
            ).fetchone()
            conn.execute(
                "UPDATE lancamento_partes SET item_categoria_id = %s, item_atual_categoria_id = %s"
                " WHERE id = %s",
                (
                    nova.item_categoria_id,
                    item_atual if item_atual in nova.categoria_ids else None,
                    parte.id,
                ),
            )
        else:
            conn.execute(
                f"UPDATE {tabela} SET item_categoria_id = %s WHERE id = %s",
                (nova.item_categoria_id, parte.id),
            )
        conn.execute(
            "INSERT INTO edicao_em_lote_partes (lote_id, parte_id, dono_id, categoria_ids_antes,"
            " tag_ids_antes, item_categoria_id_antes, item_atual_categoria_id_antes,"
            " categoria_ids_depois, tag_ids_depois) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (
                lote_id,
                parte.id,
                dono_id,
                _json(parte.categoria_ids),
                _json(tags_antes),
                parte.item_categoria_id,
                item_atual,
                _json(nova.categoria_ids),
                _json(tag_ids),
            ),
        )


def _origem_das_partes(conn, lancamento: Lancamento) -> str | None:
    """A origem da mudança nas partes: a do parcelamento, como `_origem_da_parcela`, menos na
    parcela com partes próprias ("só esta", ADR 0023), que segue alterada à mão nelas e não volta
    a receber as do parcelamento."""
    if (
        lancamento.parcelamento_id
        and conn.execute(
            "SELECT 1 FROM lancamento_campos WHERE lancamento_id = %s AND campo = 'partes'"
            " AND origem IS NULL",
            (lancamento.id,),
        ).fetchone()
    ):
        return None
    return _origem_da_parcela(conn, lancamento)


def _regravar_partes(
    conn,
    lote_id: UUID,
    atual: Lancamento,
    muda: _Muda,
    usuario: str,
    momento: datetime,
) -> int:
    """Grava as partes que o lote muda numa compra, sobe a versão dela com as partes como o campo
    que mudou e leva a mudança aos estornos das partes. Devolve a versão nova."""
    versao = subir_versao(
        conn, atual.id, atual.versao, "alterado_por = %s, alterado_em = %s", (usuario, momento)
    )
    registrar_mudancas(
        conn, atual.id, ["partes"], versao, usuario, momento, origem=_origem_das_partes(conn, atual)
    )
    _mudar_partes(
        conn, lote_id, atual.id, "lancamento", atual.partes, muda.partes, muda.nas_partes, usuario
    )
    acompanhar_estornos(conn, atual.id)
    return versao


def _mudar_as_partes_do_parcelamento(
    conn,
    lote_id: UUID,
    id: UUID,
    tipo: str,
    mudancas: _Mudancas,
    achadas: set[UUID] | None,
    usuario: str,
    momento: datetime,
) -> bool:
    """No parcelamento com partes, que não tem classificação própria, o lote muda as partes dele,
    com que as parcelas nascem (nada, se nenhuma muda); devolve se ele tem partes."""
    regra = ler_um(conn, id)
    if not regra or not regra.partes:
        return False
    partes, nas_partes, _ = mudancas.partes_depois(tipo, regra.partes, achadas)
    if not nas_partes:
        return True
    if sem_categoria := _partes_sem_categoria(partes, nas_partes):
        raise LoteRecusado(_sem_categoria(0, sem_categoria))
    _mudar_partes(conn, lote_id, id, "parcelamento", regra.partes, partes, nas_partes, usuario)
    acompanhar_estornos_do_parcelamento(conn, id)
    conn.execute(
        "UPDATE parcelamentos SET alterado_por = %s, alterado_em = %s WHERE id = %s",
        (usuario, momento, id),
    )
    conn.execute(
        "INSERT INTO edicao_em_lote_parcelamentos (lote_id, parcelamento_id,"
        " categoria_ids_antes, tag_ids_antes, item_categoria_id_antes, categoria_ids_depois,"
        " tag_ids_depois) VALUES (%s, %s, '[]', '[]', NULL, '[]', '[]')",
        (lote_id, id),
    )
    return True


def _mudar_parcelamento(
    conn,
    lote_id: UUID,
    id: UUID,
    tipo: str,
    mudancas: _Mudancas,
    achadas: dict[UUID, set[UUID]],
    usuario: str,
    momento: datetime,
) -> None:
    """O parcelamento guarda a classificação com que as parcelas voltam quando ele cresce (ticket
    47): ela muda junto com as parcelas, uma vez por lote, e o de antes fica para o desfazer."""
    if conn.execute(
        "SELECT 1 FROM edicao_em_lote_parcelamentos WHERE lote_id = %s AND parcelamento_id = %s",
        (lote_id, id),
    ).fetchone():
        return
    if _mudar_as_partes_do_parcelamento(
        conn, lote_id, id, tipo, mudancas, achadas.get(id), usuario, momento
    ):
        return
    categorias = [
        c
        for (c,) in conn.execute(
            "SELECT categoria_id FROM parcelamento_categorias WHERE parcelamento_id = %s", (id,)
        )
    ]
    tags = dict(
        conn.execute(
            "SELECT t.id, t.nome FROM parcelamento_tags pt JOIN tags t ON t.id = pt.tag_id"
            " WHERE pt.parcelamento_id = %s",
            (id,),
        ).fetchall()
    )
    (escolhida,) = conn.execute(
        "SELECT item_categoria_id FROM parcelamentos WHERE id = %s", (id,)
    ).fetchone()
    novas_categorias, novas_tags, _ = mudancas.depois(tipo, categorias, list(tags.values()))
    tag_ids = ids_das_tags(conn, novas_tags, usuario, set(tags))
    _religar(
        conn, "parcelamento_categorias", "parcelamento_id", "categoria_id", id, novas_categorias
    )
    _religar(conn, "parcelamento_tags", "parcelamento_id", "tag_id", id, tag_ids)
    acompanhar_estornos_do_parcelamento(conn, id)
    conn.execute(
        "UPDATE parcelamentos SET item_categoria_id = %s, alterado_por = %s, alterado_em = %s"
        " WHERE id = %s",
        (escolhida if escolhida in novas_categorias else None, usuario, momento, id),
    )
    conn.execute(
        "INSERT INTO edicao_em_lote_parcelamentos (lote_id, parcelamento_id,"
        " categoria_ids_antes, tag_ids_antes, item_categoria_id_antes, categoria_ids_depois,"
        " tag_ids_depois) VALUES (%s, %s, %s, %s, %s, %s, %s)",
        (
            lote_id,
            id,
            _json(categorias),
            _json(tags),
            escolhida,
            _json(novas_categorias),
            _json(tag_ids),
        ),
    )


def _aplicar_bloco(
    conn,
    lote_id: UUID,
    ids: list[UUID],
    pedido: PedidoDeEdicaoEmLote,
    usuario: str,
    momento: datetime,
    achadas: dict[UUID, set[UUID]],
) -> int:
    """Aplica o lote num bloco de lançamentos, numa transação, sobre o que eles têm agora, e
    guarda o de antes para o desfazer. Devolve quantos mudaram."""
    mudancas = _Mudancas(conn, pedido)
    guardar_item_atual(conn, "l.id = ANY(%s)", (ids,))
    atuais, tags_antes = _itens_atuais(conn, ids), _tags_das(conn, ids)
    parcelamentos: set[tuple[UUID, str]] = set()
    mudaram = 0
    for l in ler_por_ids(conn, ids):
        muda, _ = _o_que_muda(mudancas, l, achadas)
        if not muda:
            continue
        if l.parcelamento_id:
            parcelamentos.add((l.parcelamento_id, l.tipo))
        mudaram += 1
        if l.partes:
            if sem_categoria := muda.partes_sem_categoria:
                raise LoteRecusado(_sem_categoria(0, sem_categoria))
            versao = _regravar_partes(conn, lote_id, l, muda, usuario, momento)
            conn.execute(
                "INSERT INTO edicao_em_lote_lancamentos (lote_id, lancamento_id, versao,"
                " categoria_ids_antes, tag_ids_antes) VALUES (%s, %s, %s, '[]', '[]')",
                (lote_id, l.id, versao),
            )
            continue
        categorias, tags = muda.categorias, muda.tags
        muda_categorias, muda_tags = _mudou(l, categorias, tags)
        if not categorias:
            raise LoteRecusado(_sem_categoria(1))
        versao = _regravar(
            conn,
            l,
            categorias if muda_categorias else None,
            ids_das_tags(conn, tags, usuario, set(tags_antes[l.id])) if muda_tags else None,
            _item_depois(l, categorias, atuais[l.id]),
            usuario,
            momento,
        )
        conn.execute(
            "INSERT INTO edicao_em_lote_lancamentos (lote_id, lancamento_id, versao,"
            " categoria_ids_antes, tag_ids_antes, item_categoria_id_antes,"
            " item_atual_categoria_id_antes) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (
                lote_id,
                l.id,
                versao,
                _json(l.categoria_ids),
                _json(tags_antes[l.id]),
                l.item_categoria_id,
                atuais[l.id],
            ),
        )
    for parcelamento_id, tipo in parcelamentos:
        _mudar_parcelamento(
            conn, lote_id, parcelamento_id, tipo, mudancas, achadas, usuario, momento
        )
    return mudaram


class _AntesDoLote(NamedTuple):
    """O que um lançamento tinha antes do lote, e a versão em que o lote o deixou."""

    lancamento_id: UUID
    versao: int
    categoria_ids: str
    tag_ids: str
    item_categoria_id: UUID | None
    item_atual_categoria_id: UUID | None


class _ParteDoLote(NamedTuple):
    """O que uma parte tinha antes do lote e o que ele deu a ela."""

    parte_id: UUID
    categoria_ids_antes: str
    tag_ids_antes: str
    item_categoria_id_antes: UUID | None
    item_atual_categoria_id_antes: UUID | None
    categoria_ids_depois: str
    tag_ids_depois: str

    @property
    def item_depois(self) -> UUID | None:
        """A escolha do item sai com a categoria dela, como na aplicação (`partes_depois`)."""
        escolhida = self.item_categoria_id_antes
        return escolhida if escolhida in _ids(self.categoria_ids_depois) else None


def _partes_do_lote(conn, lote_id: UUID, dono_id: UUID) -> list[_ParteDoLote]:
    return [
        _ParteDoLote(*linha)
        for linha in conn.execute(
            f"SELECT {', '.join(_ParteDoLote._fields)}"
            " FROM edicao_em_lote_partes WHERE lote_id = %s AND dono_id = %s",
            (lote_id, dono_id),
        )
    ]


def _voltar_parte(conn, de: str, parte: _ParteDoLote) -> str:
    """Volta a classificação de uma parte que o lote mudou, se ela ainda tem a que o lote deu.
    A descrição, o valor, a pessoa e a ordem dela não contam (tickets 191 e 201)."""
    categorias_das_partes, tags_das_partes, tabela = _TABELAS_DAS_PARTES[de]
    id = parte.parte_id
    linha = conn.execute(f"SELECT item_categoria_id FROM {tabela} WHERE id = %s", (id,)).fetchone()
    if not linha:
        return "excluido"
    categorias = {
        c
        for (c,) in conn.execute(
            f"SELECT categoria_id FROM {categorias_das_partes} WHERE parte_id = %s", (id,)
        )
    }
    tags = {
        t
        for (t,) in conn.execute(f"SELECT tag_id FROM {tags_das_partes} WHERE parte_id = %s", (id,))
    }
    antes = _ids(parte.categoria_ids_antes), _ids(parte.tag_ids_antes)
    # Antes de olhar se mudou: juntar a tag de antes muda a parte sem ninguém a ter mudado.
    if not _existem(conn, *antes):
        return "saiu"
    if (
        categorias != {*_ids(parte.categoria_ids_depois)}
        or tags != {*_ids(parte.tag_ids_depois)}
        or linha[0] != parte.item_depois
    ):
        return "mudou_depois"
    categorias, tags = antes
    _religar(conn, categorias_das_partes, "parte_id", "categoria_id", id, categorias)
    _religar(conn, tags_das_partes, "parte_id", "tag_id", id, tags)
    if de == "lancamento":
        conn.execute(
            "UPDATE lancamento_partes SET item_categoria_id = %s, item_atual_categoria_id = %s"
            " WHERE id = %s",
            (parte.item_categoria_id_antes, parte.item_atual_categoria_id_antes, id),
        )
    else:
        conn.execute(
            f"UPDATE {tabela} SET item_categoria_id = %s WHERE id = %s",
            (parte.item_categoria_id_antes, id),
        )
    return "desfeito"


def _quem_mudou_as_partes(conn, de: str, dono_id: UUID, versao: int | None) -> tuple:
    """Quem mudou as partes depois do lote, e quando: a versão do campo das partes da compra (o
    desfazer a sobrescreve, por isso fica gravado com a parte) ou a última mudança no
    parcelamento. A parte refeita pelo parcelamento não sobe a versão de um campo da parcela."""
    if de == "parcelamento":
        return conn.execute(
            "SELECT alterado_por, alterado_em FROM parcelamentos WHERE id = %s", (dono_id,)
        ).fetchone() or (None, None)
    return conn.execute(
        "SELECT alterado_por, alterado_em FROM lancamento_campos"
        " WHERE lancamento_id = %s AND campo = 'partes' AND versao > %s",
        (dono_id, versao),
    ).fetchone() or (None, None)


def _voltar_partes(
    conn,
    lote_id: UUID,
    de: str,
    dono_id: UUID,
    partes: list[_ParteDoLote],
    versao: int | None = None,
) -> str:
    """Volta, uma a uma, as partes que o lote mudou numa compra (ou num parcelamento, sem
    `versao`) e grava o resultado de cada uma; a parte criada depois do lote fica como está. A
    compra que perdeu todas as partes é pulada inteira. Devolve `desfeito` se pelo menos uma
    parte voltou."""
    tabela = _TABELAS_DAS_PARTES[de][2]
    dono = "lancamento_id" if de == "lancamento" else "parcelamento_id"
    if not conn.execute(f"SELECT 1 FROM {tabela} WHERE {dono} = %s", (dono_id,)).fetchone():
        return "mudou_depois"
    quem = _quem_mudou_as_partes(conn, de, dono_id, versao)
    voltou = False
    for parte in partes:
        resultado = _voltar_parte(conn, de, parte)
        voltou |= resultado == "desfeito"
        por, em = quem if resultado in ("mudou_depois", "excluido") else (None, None)
        conn.execute(
            "UPDATE edicao_em_lote_partes SET resultado_do_desfazer = %s, alterado_por = %s,"
            " alterado_em = %s WHERE lote_id = %s AND parte_id = %s",
            (resultado, por, em, lote_id, parte.parte_id),
        )
    # Nenhuma voltou: os pulados são as partes, cada uma com o seu motivo.
    return "desfeito" if voltou else "mudou_depois"


def _desfazer_lancamento(
    conn, lote_id: UUID, antes: _AntesDoLote, usuario: str, momento: datetime
) -> str:
    """Volta um lançamento ao que era antes do lote, se ninguém mudou depois o que o lote mudou."""
    id = antes.lancamento_id
    excluido = conn.execute("SELECT excluido_em FROM lancamentos WHERE id = %s", (id,)).fetchone()
    if not excluido or excluido[0]:
        return "excluido"
    partes = _partes_do_lote(conn, lote_id, id)
    if conn.execute(
        "SELECT 1 FROM lancamento_campos WHERE lancamento_id = %s AND campo = ANY(%s)"
        " AND versao > %s",
        (id, CAMPOS_DA_COMPRA if partes else CAMPOS_DO_LOTE, antes.versao),
    ).fetchone():
        return "mudou_depois"
    if partes:
        (atual,) = ler_por_ids(conn, [id])
        if (
            resultado := _voltar_partes(conn, lote_id, "lancamento", id, partes, antes.versao)
        ) != "desfeito":
            return resultado
        versao = subir_versao(
            conn, id, atual.versao, "alterado_por = %s, alterado_em = %s", (usuario, momento)
        )
        registrar_mudancas(
            conn, id, ["partes"], versao, usuario, momento, origem=_origem_das_partes(conn, atual)
        )
        acompanhar_estornos(conn, id)
        return "desfeito"
    categorias, tags = _ids(antes.categoria_ids), _ids(antes.tag_ids)
    if not _existem(conn, categorias, tags):
        return "saiu"
    (atual,) = ler_por_ids(conn, [id])
    _regravar(
        conn,
        atual,
        categorias if set(categorias) != set(atual.categoria_ids) else None,
        tags if set(tags) != set(_tags_das(conn, [id])[id]) else None,
        (antes.item_categoria_id, antes.item_atual_categoria_id),
        usuario,
        momento,
    )
    return "desfeito"


def _desfazer_parcelamento(conn, lote_id: UUID, registro: tuple) -> str:
    """Volta a classificação do parcelamento (ou das partes dele), se ninguém a mudou depois do
    lote."""
    id, categorias_antes, tags_antes, escolhida, categorias_depois, tags_depois = registro
    if partes := _partes_do_lote(conn, lote_id, id):
        resultado = _voltar_partes(conn, lote_id, "parcelamento", id, partes)
        if resultado == "desfeito":
            acompanhar_estornos_do_parcelamento(conn, id)
        return resultado
    categorias = {
        c
        for (c,) in conn.execute(
            "SELECT categoria_id FROM parcelamento_categorias WHERE parcelamento_id = %s", (id,)
        )
    }
    tags = {
        t
        for (t,) in conn.execute(
            "SELECT tag_id FROM parcelamento_tags WHERE parcelamento_id = %s", (id,)
        )
    }
    if categorias != {*_ids(categorias_depois)} or tags != {*_ids(tags_depois)}:
        return "mudou_depois"
    categorias, tags = _ids(categorias_antes), _ids(tags_antes)
    if not _existem(conn, categorias, tags):
        return "saiu"
    _religar(conn, "parcelamento_categorias", "parcelamento_id", "categoria_id", id, categorias)
    _religar(conn, "parcelamento_tags", "parcelamento_id", "tag_id", id, tags)
    acompanhar_estornos_do_parcelamento(conn, id)
    conn.execute("UPDATE parcelamentos SET item_categoria_id = %s WHERE id = %s", (escolhida, id))
    return "desfeito"


def _pesos_das_partes(conn, lote_id: UUID, donos: list[UUID]) -> dict[UUID, int]:
    """Quantas partes o lote mudou em cada compra ou parcelamento: cada uma grava as ligações dela
    ao voltar, e pesa como um lançamento no bloco (`_blocos`)."""
    return dict(
        conn.execute(
            "SELECT dono_id, count(*) FROM edicao_em_lote_partes"
            " WHERE lote_id = %s AND dono_id = ANY(%s) GROUP BY dono_id",
            (lote_id, donos),
        ).fetchall()
    )


def _desfazer_bloco(conn, lote_id: UUID, usuario: str, momento: datetime) -> bool:
    """Desfaz, numa transação, o próximo bloco do que o lote gravou: os lançamentos e, depois
    deles, os parcelamentos, cada parte pesando como um lançamento. Devolve se o bloco encheu, e
    então pode haver mais."""
    peso = 0
    lancamentos = conn.execute(
        "SELECT lancamento_id, versao, categoria_ids_antes, tag_ids_antes,"
        " item_categoria_id_antes, item_atual_categoria_id_antes FROM edicao_em_lote_lancamentos"
        " WHERE lote_id = %s AND resultado_do_desfazer IS NULL ORDER BY lancamento_id LIMIT %s",
        (lote_id, POR_TRANSACAO),
    ).fetchall()
    pesos = _pesos_das_partes(conn, lote_id, [antes[0] for antes in lancamentos])
    for antes in lancamentos:
        do_lancamento = 1 + pesos.get(antes[0], 0)
        if peso and peso + do_lancamento > POR_TRANSACAO:
            return True
        conn.execute(
            "UPDATE edicao_em_lote_lancamentos SET resultado_do_desfazer = %s"
            " WHERE lote_id = %s AND lancamento_id = %s",
            (
                _desfazer_lancamento(conn, lote_id, _AntesDoLote(*antes), usuario, momento),
                lote_id,
                antes[0],
            ),
        )
        peso += do_lancamento
    if len(lancamentos) == POR_TRANSACAO:
        return True
    parcelamentos = conn.execute(
        "SELECT parcelamento_id, categoria_ids_antes, tag_ids_antes, item_categoria_id_antes,"
        " categoria_ids_depois, tag_ids_depois FROM edicao_em_lote_parcelamentos"
        " WHERE lote_id = %s AND resultado_do_desfazer IS NULL ORDER BY parcelamento_id LIMIT %s",
        (lote_id, max(1, POR_TRANSACAO - peso)),
    ).fetchall()
    pesos = _pesos_das_partes(conn, lote_id, [registro[0] for registro in parcelamentos])
    for registro in parcelamentos:
        do_parcelamento = 1 + pesos.get(registro[0], 0)
        if peso and peso + do_parcelamento > POR_TRANSACAO:
            return True
        conn.execute(
            "UPDATE edicao_em_lote_parcelamentos SET resultado_do_desfazer = %s"
            " WHERE lote_id = %s AND parcelamento_id = %s",
            (_desfazer_parcelamento(conn, lote_id, registro), lote_id, registro[0]),
        )
        peso += do_parcelamento
    return peso >= POR_TRANSACAO


def _voltar(url: str | None, lote_id: UUID, usuario: str) -> None:
    """Desfaz, em blocos, tudo o que o lote gravou e ainda não foi desfeito; parado no meio,
    chamar de novo continua de onde parou."""
    momento = datetime.now(UTC)
    while em_transacao(
        url, partial(_desfazer_bloco, lote_id=lote_id, usuario=usuario, momento=momento)
    ):
        pass


class _LoteGravado(NamedTuple):
    id: UUID
    resumo: str
    situacao: str
    lancamentos: int
    criado_por: str
    criado_em: datetime
    # Por que o lote parou no meio e foi desfeito (`cancelada`).
    recusa: str | None

    @property
    def edicao(self) -> EdicaoEmLote:
        return EdicaoEmLote(
            id=self.id,
            resumo=self.resumo,
            situacao=self.situacao,
            lancamentos=self.lancamentos,
            criado_por=self.criado_por,
            criado_em=self.criado_em,
            desfazer_ate=self.criado_em + timedelta(days=PRAZO_EM_DIAS),
        )


_COLUNAS_DO_LOTE = ", ".join(_LoteGravado._fields)


def _ler(conn, id: UUID) -> _LoteGravado | None:
    linha = conn.execute(
        f"SELECT {_COLUNAS_DO_LOTE} FROM edicoes_em_lote WHERE id = %s", (id,)
    ).fetchone()
    return linha and _LoteGravado(*linha)


def _mudar_lote(url: str | None, id: UUID, atribuicoes: str, parametros: tuple) -> None:
    em_transacao(
        url,
        lambda conn: conn.execute(
            f"UPDATE edicoes_em_lote SET {atribuicoes} WHERE id = %s", (*parametros, id)
        ),
    )


def _cancelar(url: str | None, id: UUID, usuario: str, motivo: str) -> str:
    """Desfaz o que o lote gravou e o marca `cancelada`. O desfazer pula o lançamento que alguém
    mudou depois: o lote avisa quantos ficaram com a mudança dele. Devolve o motivo completo."""
    _voltar(url, id, usuario)
    with conectar(url) as conn:
        ficaram = sum(
            conn.execute(
                f"SELECT count(*) FROM {tabela} e WHERE lote_id = %s"
                " AND (resultado_do_desfazer <> 'desfeito'"
                # A compra (ou o parcelamento) que voltou só em parte também ficou com a mudança.
                " OR EXISTS (SELECT FROM edicao_em_lote_partes r WHERE r.lote_id = e.lote_id"
                f" AND r.dono_id = e.{dono} AND r.resultado_do_desfazer <> 'desfeito'))",
                (id,),
            ).fetchone()[0]
            for tabela, dono in (
                ("edicao_em_lote_lancamentos", "lancamento_id"),
                ("edicao_em_lote_parcelamentos", "parcelamento_id"),
            )
        )
    if ficaram:
        motivo += (
            f"; {ficaram} lançamento{'s' if ficaram > 1 else ''} mudado depois "
            f"ficou com a mudança do lote"
        )
    _mudar_lote(url, id, "situacao = 'cancelada', recusa = %s", (motivo,))
    return motivo


def cancelar_parados(url: str | None = None) -> int:
    """Desfaz os lotes que ficaram em `aplicando` além do tempo máximo da gravação (a Lambda caiu
    ou estourou o tempo no meio). Devolve quantos cancelou."""
    with conectar(url) as conn:
        parados = conn.execute(
            "SELECT id, criado_por FROM edicoes_em_lote"
            " WHERE situacao = 'aplicando' AND criado_em < %s ORDER BY criado_em",
            (datetime.now(UTC) - PARADO_HA,),
        ).fetchall()
    cancelados = 0
    for id, usuario in parados:
        try:
            _cancelar(url, id, usuario, "a gravação parou no meio")
            cancelados += 1
        except Exception:  # noqa: BLE001
            # Um lote que falha (conflito do banco) fica para a próxima rodada, sem derrubar os
            # outros; o desfazer continua de onde parou.
            _log.exception("não foi possível desfazer a edição em lote %s", id)
    return cancelados


class _Gravacao(NamedTuple):
    # Os lançamentos que mudam, um bloco por transação.
    blocos: list[list[UUID]]
    achadas: dict[UUID, set[UUID]]


def _blocos(mudam: list[_Muda]) -> list[list[UUID]]:
    """Os lançamentos em blocos de uma transação: cada parte de uma compra pesa como um
    lançamento, porque grava as ligações e o registro do desfazer dela; o mesmo vale para as partes
    do parcelamento, na primeira parcela dele."""
    blocos: list[list[UUID]] = []
    peso = 0
    vistos: set[UUID] = set()
    for m in mudam:
        do_lancamento = 1 + len(m.lancamento.partes)
        # O parcelamento muda uma vez, com a primeira parcela dele: as partes dele pesam nela.
        if m.lancamento.parcelamento_id and m.lancamento.parcelamento_id not in vistos:
            vistos.add(m.lancamento.parcelamento_id)
            do_lancamento += len(m.lancamento.partes)
        if not blocos or peso + do_lancamento > POR_TRANSACAO:
            blocos.append([])
            peso = 0
        blocos[-1].append(m.lancamento.id)
        peso += do_lancamento
    return blocos


def aplicar(url: str | None, nova: NovaEdicaoEmLote, usuario: str) -> tuple[EdicaoEmLote, bool]:
    """Aplica o lote inteiro ou nada. Devolve o lote e se ele foi gravado agora."""

    def preparar(conn) -> tuple[_LoteGravado, _Gravacao | None]:
        if gravado := _ler(conn, nova.id):
            return gravado, None
        plano = _planejar(conn, nova)
        if plano.recusa:
            raise recusar(plano.recusa)
        if not plano.mudam:
            raise recusar("nenhum lançamento muda")
        conn.execute(
            "INSERT INTO edicoes_em_lote (id, resumo, situacao, criado_por)"
            " VALUES (%s, %s, 'aplicando', %s)",
            (nova.id, plano.mudancas.resumo(), usuario),
        )
        return _ler(conn, nova.id), _Gravacao(_blocos(plano.mudam), plano.achadas)

    gravado, gravacao = em_transacao(url, preparar)
    if gravacao is None:
        if gravado.situacao == "cancelada":
            raise recusar(gravado.recusa)
        if gravado.situacao == "aplicando" and gravado.criado_em < datetime.now(UTC) - PARADO_HA:
            # Parado há tempo: desfaz em vez de devolver o lote pela metade. Não grava de novo
            # com o mesmo id; o aparelho manda um lote novo.
            raise recusar(_cancelar(url, nova.id, gravado.criado_por, "a gravação parou no meio"))
        return gravado.edicao, False
    momento, mudaram = datetime.now(UTC), 0

    def aplicar_bloco(bloco: list[UUID]) -> int:
        return em_transacao(
            url,
            lambda conn: _aplicar_bloco(
                conn, nova.id, bloco, nova, usuario, momento, gravacao.achadas
            ),
        )

    try:
        for bloco in gravacao.blocos:
            mudaram += aplicar_bloco(bloco)
    except Exception as erro:
        # Um bloco recusado (o lançamento mudou no meio) desfaz os que já foram gravados.
        motivo = (
            erro.motivo
            if isinstance(erro, LoteRecusado)
            else erro.detail
            if isinstance(erro, HTTPException)
            else "a gravação parou no meio"
        )
        motivo = _cancelar(url, nova.id, usuario, motivo)
        if isinstance(erro, LoteRecusado):
            raise recusar(motivo) from erro
        raise
    _mudar_lote(url, nova.id, "situacao = 'aplicada', lancamentos = %s", (mudaram,))
    with conectar(url) as conn:
        return _ler(conn, nova.id).edicao, True


def _partes_puladas(conn, lote_id: UUID) -> dict[UUID, list[tuple]]:
    """As partes que o desfazer pulou, por compra, na ordem delas (a apagada no fim, sem
    descrição)."""
    puladas: dict[UUID, list[tuple]] = {}
    for dono_id, *pulada in conn.execute(
        "SELECT r.dono_id, r.parte_id, COALESCE(p.descricao, ''), r.resultado_do_desfazer,"
        " r.alterado_por, r.alterado_em FROM edicao_em_lote_partes r"
        " JOIN edicao_em_lote_lancamentos e ON e.lote_id = r.lote_id"
        " AND e.lancamento_id = r.dono_id"
        " LEFT JOIN lancamento_partes p ON p.id = r.parte_id"
        " WHERE r.lote_id = %s AND r.resultado_do_desfazer <> 'desfeito'"
        " ORDER BY r.dono_id, p.ordem NULLS LAST, r.parte_id",
        (lote_id,),
    ):
        puladas.setdefault(dono_id, []).append(pulada)
    return puladas


def _pulados(conn, lote_id: UUID, usuario: str) -> list[PuladoNoDesfazer]:
    pulados = []
    partes = _partes_puladas(conn, lote_id)
    for id, motivo, versao, descricao, excluido_por, excluido_em in conn.execute(
        "SELECT r.lancamento_id, r.resultado_do_desfazer, r.versao, l.descricao, l.excluido_por,"
        " l.excluido_em FROM edicao_em_lote_lancamentos r"
        " JOIN lancamentos l ON l.id = r.lancamento_id"
        " WHERE r.lote_id = %s AND (r.resultado_do_desfazer <> 'desfeito' OR r.lancamento_id"
        " = ANY(%s)) ORDER BY l.data DESC, l.criado_em DESC, l.id",
        (lote_id, list(partes)),
    ):
        if id in partes:
            # O desfazer olhou cada parte: os pulados são as partes.
            pulados.extend(
                PuladoNoDesfazer(
                    lancamento_id=id,
                    descricao=descricao,
                    parte_id=parte_id,
                    parte_descricao=parte_descricao,
                    motivo=motivo_da_parte,
                    alterado_por=por,
                    alterado_em=em,
                    por_voce=por == usuario,
                )
                for parte_id, parte_descricao, motivo_da_parte, por, em in partes[id]
            )
            continue
        por, em = excluido_por, excluido_em
        if motivo == "mudou_depois":
            # A parte refeita pelo parcelamento não sobe a versão de um campo da parcela.
            por, em = conn.execute(
                "SELECT alterado_por, alterado_em FROM lancamento_campos"
                " WHERE lancamento_id = %s AND campo = ANY(%s) AND versao > %s"
                " ORDER BY versao DESC LIMIT 1",
                (id, CAMPOS_DO_LOTE, versao),
            ).fetchone() or (None, None)
        elif motivo == "saiu":
            por, em = None, None
        pulados.append(
            PuladoNoDesfazer(
                lancamento_id=id,
                descricao=descricao,
                motivo=motivo,
                alterado_por=por,
                alterado_em=em,
                por_voce=por == usuario,
            )
        )
    return pulados


def desfazer(url: str | None, id: UUID, usuario: str) -> DesfazerDaEdicaoEmLote:
    """Volta o que o lote mudou, pulando o que alguém mudou depois. Pedir de novo devolve o
    mesmo resultado."""

    def conferir(conn) -> str:
        gravado = _ler(conn, id)
        if not gravado or gravado.situacao == "cancelada":
            raise HTTPException(status_code=404, detail="edição em lote não encontrada")
        if gravado.situacao != "desfeita" and gravado.edicao.desfazer_ate < datetime.now(UTC):
            raise recusar(f"passou o prazo de {PRAZO_EM_DIAS} dias para desfazer")
        return gravado.situacao

    if em_transacao(url, conferir) != "desfeita":
        _voltar(url, id, usuario)
        _mudar_lote(
            url,
            id,
            "situacao = 'desfeita', desfeita_por = %s, desfeita_em = %s",
            (usuario, datetime.now(UTC)),
        )
    with conectar(url) as conn:
        (desfeitos,) = conn.execute(
            "SELECT count(*) FROM edicao_em_lote_lancamentos"
            " WHERE lote_id = %s AND resultado_do_desfazer = 'desfeito'",
            (id,),
        ).fetchone()
        return DesfazerDaEdicaoEmLote(desfeitos=desfeitos, pulados=_pulados(conn, id, usuario))


@router.post(
    "/edicoes-em-lote/previa",
    response_model=PreviaDaEdicaoEmLote,
    operation_id="previa_da_edicao_em_lote",
)
def ver_previa(
    pedido: PedidoDeEdicaoEmLote, usuario: UsuarioLogado, request: Request
) -> PreviaDaEdicaoEmLote:
    with conectar(url_do_banco(request)) as conn:
        return previa(conn, pedido)


@router.post(
    "/edicoes-em-lote",
    status_code=201,
    response_model=EdicaoEmLote,
    operation_id="aplicar_edicao_em_lote",
)
def aplicar_edicao_em_lote(
    nova: NovaEdicaoEmLote, usuario: UsuarioLogado, request: Request, response: Response
) -> EdicaoEmLote:
    """Tudo ou nada; o mesmo id reenviado devolve o lote gravado, com 200."""
    lote, gravado = aplicar(url_do_banco(request), nova, usuario)
    response.status_code = 201 if gravado else 200
    return lote


@router.get(
    "/edicoes-em-lote",
    response_model=list[EdicaoEmLote],
    operation_id="listar_edicoes_em_lote",
)
def listar(usuario: UsuarioLogado, request: Request) -> list[EdicaoEmLote]:
    """As que ainda se desfazem, da mais recente à mais antiga."""
    with conectar(url_do_banco(request)) as conn:
        return [
            _LoteGravado(*linha).edicao
            for linha in conn.execute(
                f"SELECT {_COLUNAS_DO_LOTE} FROM edicoes_em_lote"
                " WHERE situacao IN ('aplicando', 'aplicada') AND criado_em > %s"
                " ORDER BY criado_em DESC",
                (datetime.now(UTC) - timedelta(days=PRAZO_EM_DIAS),),
            )
        ]


@router.post(
    "/edicoes-em-lote/{id}/desfazer",
    response_model=DesfazerDaEdicaoEmLote,
    operation_id="desfazer_edicao_em_lote",
)
def desfazer_edicao_em_lote(
    id: UUID, usuario: UsuarioLogado, request: Request
) -> DesfazerDaEdicaoEmLote:
    return desfazer(url_do_banco(request), id, usuario)
