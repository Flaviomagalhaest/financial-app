"""Parcelamento: a compra ou a dívida em N parcelas. Ele não é um lançamento (ADR 0004): cada
parcela é um lançamento comum, ligado a ele pelo `parcelamento_id` e pelo número da parcela,
para o valor inteiro nunca contar de uma vez num mês só. No cartão, todas as parcelas têm a data
da compra e a parcela n cai n - 1 faturas depois da fatura da compra; fora dele (o boleto), a
parcela n vence n - 1 meses depois da primeira."""

from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Literal, NamedTuple
from uuid import UUID, uuid5

import psycopg
from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

from app import cartoes, faturas, lancamentos
from app.backup import LINHAS_POR_LOTE
from app.banco import conectar, em_transacao
from app.config import valores_iniciais
from app.lancamentos import (
    SEM_CENTAVO_POR_PARTE,
    SEM_CLASSIFICACAO_PROPRIA,
    Parte,
    conferir_ligacoes,
    conferir_sem_estorno,
    excluir,
    gravar_categorias,
    ids_das_tags,
    recusar,
    registrar_mudancas,
    sem_repetidas,
    subir_versao,
    tags_limpas,
    url_do_banco,
)
from app.login import UsuarioLogado
from app.partes import dividir as dividir_pela_proporcao
from app.partes import id_na_parcela
from app.recorrencias import com_o_dia_do_lancamento, mais_meses

router = APIRouter(prefix="/api")

# 35 anos de prestações da casa; o limite só protege a geração de um número sem sentido.
MAXIMO_DE_PARCELAS = valores_iniciais()["maximoDeParcelas"]


class DadosDoParcelamento(BaseModel):
    id: UUID
    # Compra ou dívida: as parcelas são despesas. Não é gravado: a receita parcelada, se vier,
    # ganha a coluna.
    tipo: Literal["despesa"] = "despesa"
    parcelas: int = Field(ge=2, le=MAXIMO_DE_PARCELAS)
    # No cartão, a data da compra, a mesma em todas as parcelas; fora dele, a da 1ª parcela.
    data: date
    descricao: str = ""
    # O cartão ou a conta de onde sai o boleto.
    conta_id: UUID
    # Vazia só na compra com partes, que não tem classificação própria (ADR 0022).
    categoria_ids: list[UUID] = []
    tags: list[str] = []
    # O id de uma pessoa do casal, que as parcelas herdam; sem ela, é do conjunto.
    pessoa: str | None = None
    # A escolha do item do planejamento, pela categoria dele, com que as parcelas nascem
    # (ADR 0006).
    item_categoria_id: UUID | None = None
    # As partes da compra parcelada que junta coisas diferentes (ADR 0022, ticket 139): duas ou
    # mais, guardadas como proporção. Cada parcela se divide por elas, e o que vale é o valor da
    # parcela. Com partes, o parcelamento não tem categoria, tag, pessoa nem item próprios.
    partes: list[Parte] = []
    # O dia (São Paulo) em que o casal lançou no aparelho; sem ele, o da chegada. No boleto, o
    # "antes de hoje" se conta a partir dele e a parcela desse dia nasce realizada (ticket 127).
    dia_do_lancamento: date | None = None

    _tags = field_validator("tags")(tags_limpas)
    _categorias = field_validator("categoria_ids")(sem_repetidas)

    @model_validator(mode="after")
    def _item_de_uma_das_categorias(self):
        if self.item_categoria_id and self.item_categoria_id not in self.categoria_ids:
            raise ValueError(lancamentos.ITEM_FORA_DAS_CATEGORIAS)
        return self

    @model_validator(mode="after")
    def _classificacao(self):
        if not self.partes:
            if not self.categoria_ids:
                raise ValueError("parcelamento sem categoria")
            return self
        if self.categoria_ids or self.tags or self.pessoa or self.item_categoria_id:
            raise ValueError(SEM_CLASSIFICACAO_PROPRIA)
        if len(self.partes) < 2:
            raise ValueError(lancamentos.DUAS_PARTES_OU_MAIS)
        if len({p.id for p in self.partes}) != len(self.partes):
            raise ValueError("parte repetida")
        return self


class NovoParcelamento(DadosDoParcelamento):
    # O total (compra sem juros) ou o da parcela (com juros); os centavos que sobram da divisão
    # do total vão na 1ª parcela.
    valor_total_centavos: int | None = Field(default=None, gt=0)
    valor_da_parcela_centavos: int | None = Field(default=None, gt=0)
    # Sem o campo, o do cartão nasce automático e o boleto pede confirmação de cada parcela.
    automatico: bool | None = None

    @model_validator(mode="after")
    def _um_valor(self):
        if (self.valor_total_centavos is None) == (self.valor_da_parcela_centavos is None):
            raise ValueError("informe o valor total ou o da parcela, um dos dois")
        if self.valor_total_centavos is not None and self.valor_total_centavos < self.parcelas:
            raise ValueError("o total não chega a um centavo por parcela")
        return self

    @model_validator(mode="after")
    def _partes_somam_o_valor(self):
        """As partes dividem o valor digitado, o total ou o da parcela; a menor parcela ainda dá
        um centavo a cada parte."""
        if not self.partes:
            return self
        informado = self.valor_total_centavos or self.valor_da_parcela_centavos
        soma = sum(p.valor_centavos for p in self.partes)
        if soma != informado:
            raise ValueError(f"as partes somam {soma} centavos e a compra, {informado}")
        proporcao = [p.valor_centavos for p in self.partes]
        if min(dividir_pela_proporcao(self.total // self.parcelas, proporcao)) <= 0:
            raise ValueError(SEM_CENTAVO_POR_PARTE)
        return self

    @property
    def total(self) -> int:
        return self.valor_total_centavos or self.valor_da_parcela_centavos * self.parcelas


class Parcelamento(DadosDoParcelamento):
    valor_total_centavos: int
    # A parcela vira realizada sozinha na data, sem confirmação.
    automatico: bool
    criado_por: str
    criado_em: datetime
    alterado_por: str
    alterado_em: datetime
    # As parcelas do boleto que já tinham passado quando ele foi lançado (ticket 87): não viram
    # lançamento, mas contam na numeração e no total.
    parcelas_anteriores: int = 0
    # A recusa que parou a parte parcela a parcela de uma mudança com alcance depois do pedido
    # (ticket 149): as parcelas que faltavam ficaram como estavam até a próxima mudança.
    mudanca_recusada: str | None = None
    # Na leitura, com as partes divididas pelo total (ticket 158), a proporção guardada delas, na
    # mesma ordem: a tela a manda de volta quando só a classificação muda, e o estorno de todas as
    # parcelas faz a conta por ela, como o servidor.
    proporcao_das_partes: list[int] = []


class AlteracaoDeParcelamento(BaseModel):
    """O que se corrige num parcelamento; campo ausente fica como está. Descrição, categorias,
    tags, pessoa e item valem para todas as parcelas, inclusive as realizadas. Valor, número de
    parcelas e data refazem as parcelas, salvo as que uma pessoa editou à mão; se uma realizada
    mudar ou sair, o pedido só vale com `confirmar_realizadas`."""

    # Sem `None` no tipo: mandar null num campo obrigatório do parcelamento é erro, não "limpar".
    descricao: str = Field(default=None)
    # Vazia só junto com as partes, que tiram a classificação própria do parcelamento.
    categoria_ids: list[UUID] = Field(default=None)
    tags: list[str] = Field(default=None)
    # Vazia, passa o parcelamento para o conjunto.
    pessoa: str | None = None
    # Vazio tira a escolha; ela também sai com a categoria dela.
    item_categoria_id: UUID | None = None
    # A lista inteira de partes, como na compra à vista (ADR 0022): duas ou mais dividem o
    # parcelamento, e o valor de cada uma é a proporção dela; uma só junta, e o parcelamento
    # volta a ter a classificação dela. As parcelas se dividem de novo.
    partes: list[Parte] = Field(default=None)
    # O total novo, ou o da parcela (vale vezes o número de parcelas); só o número de parcelas
    # mantém o total, e as parcelas se dividem de novo.
    valor_total_centavos: int | None = Field(default=None, gt=0)
    valor_da_parcela_centavos: int | None = Field(default=None, gt=0)
    parcelas: int = Field(default=None, ge=2, le=MAXIMO_DE_PARCELAS)
    # Como na criação: no cartão, a data da compra; fora dele, a da 1ª parcela.
    data: date = Field(default=None)
    confirmar_realizadas: bool = False

    _tags = field_validator("tags")(tags_limpas)
    _categorias = field_validator("categoria_ids")(sem_repetidas)

    @model_validator(mode="after")
    def _um_valor(self):
        if self.valor_total_centavos is not None and self.valor_da_parcela_centavos is not None:
            raise ValueError("informe o valor total ou o da parcela, um dos dois")
        return self


class ParcelaQueMuda(BaseModel):
    """Uma parcela realizada que a correção muda ou tira."""

    id: UUID
    parcela: int
    valor_centavos: int
    data: date
    # Como fica; vazios quando ela sai.
    valor_novo_centavos: int | None
    data_nova: date | None
    sai: bool


class AvisoDeRealizadas(BaseModel):
    """A correção mudaria parcelas já realizadas; nada foi gravado. Repetir o pedido com
    `confirmar_realizadas` as muda."""

    motivo: str
    parcelas: list[ParcelaQueMuda]


class RealizadasMudam(Exception):
    """A correção pede confirmação: muda parcelas realizadas."""

    def __init__(self, aviso: AvisoDeRealizadas):
        self.aviso = aviso


_COLUNAS = (
    "id, valor_total_centavos, parcelas, data, automatico, descricao, conta_id, pessoa,"
    " criado_por, criado_em, alterado_por, alterado_em, item_categoria_id, dia_do_lancamento"
)
_NOMES_DAS_COLUNAS = _COLUNAS.replace(" ", "").split(",")


def valor_da_parcela(total: int, parcelas: int, n: int) -> int:
    """O total dividido por igual; os centavos que sobram vão na 1ª."""
    return total // parcelas + (total % parcelas if n == 1 else 0)


def parcelas_puladas(parcelas: int, data: date, hoje: date, no_cartao: bool) -> int:
    """Quantas parcelas do boleto caem antes de `hoje` e não viram lançamento (ticket 87); o
    cartão não pula nenhuma. O app repete esta conta para avisar (ADR 0018); a tabela
    `tabelas-de-teste/puladas.json` vale para os dois."""
    if no_cartao:
        return 0
    return sum(1 for n in range(1, parcelas + 1) if mais_meses(data, n - 1) < hoje)


def realiza_em(conn, conta_id: UUID, parcela: int, mes: date, data: date) -> date:
    """O dia em que a parcela automática vira realizada. No cartão, a parcela n > 1 entra na
    fatura aberta quando a fatura de antes fecha (a importada, sem datas, já está fechada, e
    a que ainda não nasceu fecha no dia padrão); a 1ª e a do boleto, na data."""
    cartao = faturas.ler_cartao(conn, conta_id)
    if cartao is None or parcela == 1:
        return data
    anterior = faturas.somar_meses(mes, -1)
    gravada = conn.execute(
        "SELECT fechamento FROM faturas WHERE cartao_id = %s AND mes = %s",
        (cartao.titular.id, anterior),
    ).fetchone()
    fechamento = gravada[0] if gravada else faturas.datas_padrao(cartao.titular, anterior)[0]
    return fechamento or data


def para_a_leitura(regra: Parcelamento) -> Parcelamento:
    """O parcelamento como a API o mostra (ticket 158): as partes divididas pelo total, somando
    o valor dele (os centavos na maior parte, a primeira no empate). O banco e as contas daqui
    guardam a proporção, que pode vir do valor de uma parcela; dividir as parcelas pelo total já
    arredondado mudaria os centavos delas."""
    if not regra.partes:
        return regra
    valores = dividir_pela_proporcao(
        regra.valor_total_centavos, [p.valor_centavos for p in regra.partes]
    )
    partes = [p.model_copy(update={"valor_centavos": v}) for p, v in zip(regra.partes, valores)]
    proporcao = [p.valor_centavos for p in regra.partes]
    return regra.model_copy(update={"partes": partes, "proporcao_das_partes": proporcao})


def ler_um(conn, id: UUID) -> Parcelamento | None:
    lidos = _ler(conn, "id = %s", (id,))
    return lidos[0] if lidos else None


def _ler(conn, filtro: str = "", parametros: tuple = ()) -> list[Parcelamento]:
    # Cada parcela gerada tem um lançamento só (o id vem do número), excluída ou não: a que
    # falta foi pulada na geração, e a que a correção levou para antes de hoje saiu pulada
    # (`excluido_pela_regra`).
    linhas = conn.execute(
        f"SELECT {_COLUNAS}, LEAST(geradas, parcelas) - (SELECT count(*) FROM lancamentos l"
        " WHERE l.parcelamento_id = parcelamentos.id AND l.parcela <= parcelamentos.parcelas"
        " AND l.excluido_pela_regra IS NOT TRUE), mudanca_recusada"
        f" FROM parcelamentos {'WHERE ' + filtro if filtro else ''}"
        " ORDER BY data DESC, descricao, id",
        parametros,
    ).fetchall()
    ids = [linha[0] for linha in linhas]
    categorias: dict[UUID, list[UUID]] = {}
    for parcelamento_id, categoria_id in conn.execute(
        "SELECT parcelamento_id, categoria_id FROM parcelamento_categorias"
        " WHERE parcelamento_id = ANY(%s) ORDER BY categoria_id",
        (ids,),
    ):
        categorias.setdefault(parcelamento_id, []).append(categoria_id)
    tags: dict[UUID, list[str]] = {}
    for parcelamento_id, nome in conn.execute(
        "SELECT pt.parcelamento_id, t.nome FROM parcelamento_tags pt"
        " JOIN tags t ON t.id = pt.tag_id WHERE pt.parcelamento_id = ANY(%s) ORDER BY t.nome",
        (ids,),
    ):
        tags.setdefault(parcelamento_id, []).append(nome)
    partes = _ler_partes(conn, ids)
    return [
        Parcelamento(
            **dict(zip([*_NOMES_DAS_COLUNAS, "parcelas_anteriores", "mudanca_recusada"], linha)),
            categoria_ids=categorias.get(linha[0], []),
            tags=tags.get(linha[0], []),
            partes=partes.get(linha[0], []),
        )
        for linha in linhas
    ]


def _ler_partes(conn, ids: list[UUID]) -> dict[UUID, list[Parte]]:
    """As partes de cada parcelamento, na ordem, com o valor que é a proporção delas."""
    linhas = conn.execute(
        "SELECT id, parcelamento_id, descricao, valor_centavos, pessoa, item_categoria_id"
        " FROM parcelamento_partes WHERE parcelamento_id = ANY(%s)"
        " ORDER BY parcelamento_id, ordem",
        (ids,),
    ).fetchall()
    if not linhas:
        return {}
    categorias: dict[UUID, list[UUID]] = {}
    for parte_id, categoria_id in conn.execute(
        "SELECT pc.parte_id, pc.categoria_id FROM parcelamento_parte_categorias pc"
        " JOIN parcelamento_partes p ON p.id = pc.parte_id"
        " WHERE p.parcelamento_id = ANY(%s) ORDER BY pc.categoria_id",
        (ids,),
    ):
        categorias.setdefault(parte_id, []).append(categoria_id)
    tags: dict[UUID, list[str]] = {}
    for parte_id, nome in conn.execute(
        "SELECT pt.parte_id, t.nome FROM parcelamento_parte_tags pt"
        " JOIN parcelamento_partes p ON p.id = pt.parte_id JOIN tags t ON t.id = pt.tag_id"
        " WHERE p.parcelamento_id = ANY(%s) ORDER BY t.nome",
        (ids,),
    ):
        tags.setdefault(parte_id, []).append(nome)
    por_parcelamento: dict[UUID, list[Parte]] = {}
    for id, parcelamento_id, descricao, valor, pessoa, item in linhas:
        por_parcelamento.setdefault(parcelamento_id, []).append(
            Parte.model_construct(
                id=id,
                descricao=descricao,
                valor_centavos=valor,
                categoria_ids=categorias.get(id, []),
                tags=tags.get(id, []),
                pessoa=pessoa,
                item_categoria_id=item,
            )
        )
    return por_parcelamento


def _tags_das_partes(conn, id: UUID) -> dict[UUID, list[UUID]]:
    """Os ids das tags de cada parte do parcelamento: a parcela nasce com eles, mesmo arquivadas."""
    tags: dict[UUID, list[UUID]] = {}
    for parte_id, tag_id in conn.execute(
        "SELECT pt.parte_id, pt.tag_id FROM parcelamento_parte_tags pt"
        " JOIN parcelamento_partes p ON p.id = pt.parte_id WHERE p.parcelamento_id = %s",
        (id,),
    ):
        tags.setdefault(parte_id, []).append(tag_id)
    return tags


def _gravar_partes(conn, id: UUID, partes: list[Parte], usuario: str) -> None:
    """Troca as partes do parcelamento pela lista; a tag arquivada só vale para quem já a tinha."""
    ja_tinha = {t for ids in _tags_das_partes(conn, id).values() for t in ids}
    tags_de_cada = [ids_das_tags(conn, p.tags, usuario, ja_tinha) for p in partes]
    _apagar_partes(conn, id)
    for ordem, (parte, tags) in enumerate(zip(partes, tags_de_cada)):
        conn.execute(
            "INSERT INTO parcelamento_partes (id, parcelamento_id, ordem, descricao,"
            " valor_centavos, pessoa, item_categoria_id) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (
                parte.id,
                id,
                ordem,
                parte.descricao,
                parte.valor_centavos,
                parte.pessoa,
                parte.item_categoria_id,
            ),
        )
        for categoria in parte.categoria_ids:
            conn.execute(
                "INSERT INTO parcelamento_parte_categorias (parte_id, categoria_id)"
                " VALUES (%s, %s)",
                (parte.id, categoria),
            )
        for tag in tags:
            conn.execute(
                "INSERT INTO parcelamento_parte_tags (parte_id, tag_id) VALUES (%s, %s)",
                (parte.id, tag),
            )


def _apagar_partes(conn, id: UUID) -> None:
    partes = [
        p
        for (p,) in conn.execute(
            "SELECT id FROM parcelamento_partes WHERE parcelamento_id = %s", (id,)
        )
    ]
    if not partes:
        return
    conn.execute("DELETE FROM parcelamento_parte_categorias WHERE parte_id = ANY(%s)", (partes,))
    conn.execute("DELETE FROM parcelamento_parte_tags WHERE parte_id = ANY(%s)", (partes,))
    conn.execute("DELETE FROM parcelamento_partes WHERE id = ANY(%s)", (partes,))


@dataclass
class PartesDaParcela:
    """As partes do parcelamento numa parcela: cada uma com o id dela na parcela (vem da parcela e
    da parte, e gerar de novo não duplica), o valor da parcela dividido na proporção e os ids das
    tags; a `proporcao`, que a parcela guarda para se dividir de novo."""

    partes: list[tuple[Parte, list[UUID]]]
    proporcao: list[int]

    def sem_ids(self) -> list[lancamentos.ParteNormalizada]:
        return [lancamentos.parte_sem_id(p) for p, _ in self.partes]


def partes_da_parcela(
    regra: Parcelamento, tags: dict[UUID, list[UUID]], lancamento_id: UUID, valor: int
) -> PartesDaParcela:
    proporcao = [p.valor_centavos for p in regra.partes]
    return PartesDaParcela(
        [
            (
                p.model_copy(
                    update={"id": id_na_parcela(lancamento_id, p.id), "valor_centavos": v}
                ),
                tags.get(p.id, []),
            )
            for p, v in zip(regra.partes, dividir_pela_proporcao(valor, proporcao))
        ],
        proporcao,
    )


def _linhas_das_partes(regra: Parcelamento) -> int:
    """As linhas que as partes de uma parcela gravam: a parte, as categorias e as tags dela."""
    return sum(1 + len(p.categoria_ids) + len(p.tags) for p in regra.partes)


def _dia_do_lancamento_vigente(conn, regra: Parcelamento) -> date | None:
    """O dia do lançamento, enquanto o parcelamento não foi corrigido (`corrigido_em`, que só a
    correção de valor, parcelas ou data grava, ticket 144). A classificação que a edição em lote
    muda também mexe em `alterado_em` e não no calendário, por isso não conta (ticket 132)."""
    return regra.dia_do_lancamento if _corrigido_em(conn, regra.id) is None else None


def _muda_o_calendario(atual: Parcelamento, nova: Parcelamento) -> bool:
    """Se a correção mexe no valor, nas parcelas ou na data, o que desfaz o dia do lançamento."""
    return (nova.valor_total_centavos, nova.parcelas, nova.data) != (
        atual.valor_total_centavos,
        atual.parcelas,
        atual.data,
    )


def _corrigido_em(conn, id: UUID) -> date | None:
    """O dia da última correção do parcelamento; nunca corrigido (ou excluído), nenhum."""
    linha = conn.execute("SELECT corrigido_em FROM parcelamentos WHERE id = %s", (id,)).fetchone()
    return linha[0] if linha else None


def _gerar_um_lote(conn, id: UUID) -> bool:
    """Grava as próximas parcelas, quantas cabem numa transação, e devolve se pode faltar
    alguma. O id de cada parcela vem do parcelamento e do número dela: gerar de novo não
    duplica. No boleto, a parcela de antes de hoje não vira lançamento (ticket 87); enquanto o
    parcelamento é o que o casal lançou, o "hoje" é o dia do lançamento
    (`_dia_do_lancamento_vigente`), e a parcela desse dia nasce realizada. O cartão segue o
    ticket 99. Antes das próximas, nascem as puladas que uma correção trouxe para hoje ou
    depois (ticket 126)."""
    if not (lidos := _ler(conn, "id = %s", (id,))):
        return False  # excluído no meio da geração
    [regra] = lidos
    (geradas,) = conn.execute("SELECT geradas FROM parcelamentos WHERE id = %s", (id,)).fetchone()
    categorias = regra.categoria_ids
    tags = [
        tag
        for (tag,) in conn.execute(
            "SELECT tag_id FROM parcelamento_tags WHERE parcelamento_id = %s", (id,)
        )
    ]
    no_cartao = faturas.ler_cartao(conn, regra.conta_id) is not None
    tags_das_partes = _tags_das_partes(conn, id) if regra.partes else {}
    # O DSQL aceita até 3.000 linhas por transação; no cartão, cada parcela pode criar a fatura.
    por_lote = max(
        1, LINHAS_POR_LOTE // (2 + len(categorias) + len(tags) + _linhas_das_partes(regra))
    )
    proximas = range(geradas + 1, min(regra.parcelas, geradas + por_lote) + 1)
    puladas = _puladas_que_chegaram(conn, regra, geradas)
    if puladas:
        numeros: Sequence[int] = puladas[:por_lote]
    elif proximas:
        _reviver_as_que_a_correcao_tirou(conn, regra, geradas, proximas)
        numeros = proximas
    else:
        return False
    dia_de_hoje = lancamentos.hoje()
    lancado = _dia_do_lancamento_vigente(conn, regra)
    desde = lancado or dia_de_hoje
    for n in numeros:
        lancamento_id = uuid5(id, str(n))
        dia = regra.data if no_cartao else mais_meses(regra.data, n - 1)
        if not no_cartao and dia < desde:
            continue
        mes = lancamentos.mes_em_que_conta(conn, regra.conta_id, dia, n)
        # A parcela automática que já chegou nasce realizada; o resto, prevista.
        chegou = realiza_em(conn, regra.conta_id, n, mes, dia) <= dia_de_hoje
        situacao = (
            "realizado"
            if chegou and (regra.automatico or (dia == lancado and not no_cartao))
            else "previsto"
        )
        gravado = conn.execute(
            "INSERT INTO lancamentos (id, tipo, situacao, valor_centavos, data, descricao,"
            " conta_id, criado_por, alterado_por, versao, parcelamento_id, parcela, automatico,"
            " pessoa, fonte, mes, item_categoria_id)"
            " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 1, %s, %s, %s, %s, 'app', %s, %s)"
            " ON CONFLICT (id) DO NOTHING",
            (
                lancamento_id,
                regra.tipo,
                situacao,
                valor_da_parcela(regra.valor_total_centavos, regra.parcelas, n),
                dia,
                regra.descricao,
                regra.conta_id,
                regra.alterado_por,
                regra.alterado_por,
                id,
                n,
                regra.automatico,
                regra.pessoa,
                mes,
                regra.item_categoria_id,
            ),
        ).rowcount
        if not gravado:
            continue
        for categoria in categorias:
            conn.execute(
                "INSERT INTO lancamento_categorias (lancamento_id, categoria_id) VALUES (%s, %s)",
                (lancamento_id, categoria),
            )
        for tag in tags:
            conn.execute(
                "INSERT INTO lancamento_tags (lancamento_id, tag_id) VALUES (%s, %s)",
                (lancamento_id, tag),
            )
        if regra.partes:
            divididas = partes_da_parcela(
                regra,
                tags_das_partes,
                lancamento_id,
                valor_da_parcela(regra.valor_total_centavos, regra.parcelas, n),
            )
            lancamentos.gravar_partes_por_id(
                conn, lancamento_id, divididas.partes, divididas.proporcao
            )
    if puladas:
        return True  # as próximas vêm no lote seguinte
    if not conn.execute(
        "UPDATE parcelamentos SET geradas = %s WHERE id = %s AND geradas = %s",
        (proximas[-1], id, geradas),
    ).rowcount:
        # Outra geração andou junto: a transação recomeça e parte do que ela gravou.
        raise psycopg.errors.SerializationFailure("o parcelamento mudou durante a geração")
    return proximas[-1] < regra.parcelas


def _puladas_que_chegaram(
    conn, regra: Parcelamento, geradas: int, lancamentos_existentes: int | None = None
) -> list[int]:
    """As parcelas do boleto que a geração pulou por estarem antes de hoje (não têm lançamento,
    nem excluído) e que a data corrigida pôs em hoje ou depois. O cartão não pula nenhuma.
    Só lê as parcelas do boleto quando falta alguma: `geradas` maior que o número de
    lançamentos (ticket 131)."""
    if faturas.ler_cartao(conn, regra.conta_id) is not None:
        return []
    if lancamentos_existentes is None:
        (lancamentos_existentes,) = conn.execute(
            "SELECT count(*) FROM lancamentos WHERE parcelamento_id = %s AND parcela <= %s",
            (regra.id, regra.parcelas),
        ).fetchone()
    if lancamentos_existentes >= min(geradas, regra.parcelas):
        return []
    existem = {
        n
        for (n,) in conn.execute(
            "SELECT parcela FROM lancamentos WHERE parcelamento_id = %s", (regra.id,)
        )
    }
    dia_de_hoje = lancamentos.hoje()
    return [
        n
        for n in range(1, min(geradas, regra.parcelas) + 1)
        if n not in existem and mais_meses(regra.data, n - 1) >= dia_de_hoje
    ]


def _reviver_as_que_a_correcao_tirou(
    conn, regra: Parcelamento, geradas: int, proximas: range
) -> None:
    """Uma parcela de depois de `geradas` que já existe, excluída, saiu quando o parcelamento
    encolheu. Se ele cresceu e a geração chega antes do refazer da correção, o `INSERT ... ON
    CONFLICT DO NOTHING` a pularia e ela ficaria excluída para sempre: volta aqui."""
    (ha,) = conn.execute(
        "SELECT EXISTS (SELECT FROM lancamentos WHERE parcelamento_id = %s"
        " AND excluido_em IS NOT NULL AND parcela = ANY(%s))",
        (regra.id, list(proximas)),
    ).fetchone()
    if not ha:
        return
    tags = _tags_do_parcelamento(conn, regra.id)
    agora = datetime.now(UTC)
    for correcao in _correcoes(conn, regra, geradas, {}):
        if correcao.acao in ("reviver", "pular") and correcao.parcela in proximas:
            _aplicar(conn, regra, correcao, tags, regra.alterado_por, agora)


def gerar_as_parcelas(url: str | None, id: UUID) -> None:
    """Gera, em lotes de uma transação cada, as parcelas que faltam. Se parar no meio, o reenvio
    ou a tarefa diária continuam de onde parou."""
    while em_transacao(url, lambda conn: _gerar_um_lote(conn, id)):
        pass


def completar_todos(url: str | None) -> int:
    """Conserta os parcelamentos que um pedido deixou pela metade: gera as parcelas que faltam
    (a geração parou no meio) e refaz as que destoam do parcelamento (a correção parou no
    meio), inclusive a classificação (descrição, categorias, tags, pessoa, item) que o pedido
    trouxe, gravada no parcelamento até o refazer terminar. Devolve quantos consertou; o que uma
    recusa trava (a fatura de uma parcela foi paga no meio) sai do pendente e mostra a recusa
    no parcelamento, sem parar a tarefa nos outros."""
    with conectar(url) as conn:
        ids = [id for (id,) in conn.execute("SELECT id FROM parcelamentos")]
    consertados = 0
    for id in ids:
        try:
            consertados += completar(url, id)
        except HTTPException:
            continue  # a recusa ficou gravada no parcelamento (`_refazer_protegido`)
    return consertados


_A_CORRECAO_PAROU = "A correção do parcelamento parou:"
_FICARAM_COMO_ESTAVAM = "as parcelas que faltavam corrigir ficaram como estavam"


def tirar_a_recusa(conn, id: UUID, so_a_da_correcao: bool = False) -> None:
    """Tira do parcelamento a recusa que a tela mostra; `so_a_da_correcao` deixa a de uma
    mudança com alcance (ticket 149), que só a próxima mudança tira."""
    conn.execute(
        "UPDATE parcelamentos SET mudanca_recusada = NULL WHERE id = %s"
        " AND mudanca_recusada IS NOT NULL AND (NOT %s OR mudanca_recusada LIKE %s)",
        (id, so_a_da_correcao, f"%{_A_CORRECAO_PAROU}%"),
    )


def _desistir_do_conserto(
    conn, id: UUID, recusa: HTTPException, manter_a_de_alcance: bool = False
) -> None:
    """Tira a classificação pendente que o refazer não consegue levar e grava a recusa no
    parcelamento, com a parcela em que a correção parou, para o casal ver (tickets 157 e 182).
    A tentativa diária (`manter_a_de_alcance`) não troca a recusa de uma mudança com alcance
    (ticket 149), que é mais nova que a correção: só a recusa da própria correção se regrava."""
    texto = f"{_A_CORRECAO_PAROU} {_FICARAM_COMO_ESTAVAM}"
    if lidos := _ler(conn, "id = %s", (id,)):
        [regra] = lidos
        (geradas,) = conn.execute(
            "SELECT geradas FROM parcelamentos WHERE id = %s", (id,)
        ).fetchone()
        faltam = _correcoes(conn, regra, geradas, classificacao_pendente(conn, id))
        if faltam:
            desde = min(c.parcela for c in faltam)
            texto = f"{_A_CORRECAO_PAROU} da {desde}ª parcela em diante, {_FICARAM_COMO_ESTAVAM}"
    conn.execute(
        "UPDATE parcelamentos SET classificacao_pendente = '',"
        " mudanca_recusada = CASE WHEN %s AND mudanca_recusada IS NOT NULL"
        " AND mudanca_recusada NOT LIKE %s THEN mudanca_recusada ELSE %s END WHERE id = %s",
        (manter_a_de_alcance, f"%{_A_CORRECAO_PAROU}%", f"{recusa.detail}. {texto}", id),
    )


def completar(url: str | None, id: UUID) -> bool:
    """Conserta um parcelamento que um pedido deixou pela metade; devolve se faltava algo."""
    if not em_transacao(url, lambda conn: _falta_conserto(conn, id)):
        return False
    pendente = em_transacao(url, lambda conn: classificacao_pendente(conn, id))
    _refazer_protegido(
        url,
        id,
        lambda conn: _reajustar_do_parcelamento(conn, id),
        pendente,
        manter_a_de_alcance=True,
    )
    return True


# Os campos de classificação a levar às parcelas, cada um com a parcela a partir da qual vale: a
# correção leva a todas (1), e "esta e as próximas" a partir da parcela mudada (ticket 136).
Classificacao = Mapping[str, int]


def _ler_classificacao(texto: str | None) -> dict[str, int]:
    """`descricao,tags@5`: a descrição desde a 1ª, as tags desde a 5ª."""
    lida = {}
    for item in filter(None, (texto or "").split(",")):
        campo, _, desde = item.partition("@")
        lida[campo] = int(desde or 1)
    return lida


def _gravar_classificacao(classificacao: Classificacao) -> str:
    return ",".join(
        sorted(c if desde == 1 else f"{c}@{desde}" for c, desde in classificacao.items())
    )


def _juntar(*classificacoes: Classificacao) -> dict[str, int]:
    """O campo pedido por mais de uma vale desde a menor parcela."""
    juntas: dict[str, int] = {}
    for classificacao in classificacoes:
        for campo, desde in classificacao.items():
            juntas[campo] = min(desde, juntas.get(campo, desde))
    return juntas


def classificacao_pendente(conn, id: UUID) -> dict[str, int]:
    """Os campos de classificação que correções já gravadas ainda não levaram às parcelas."""
    linha = conn.execute(
        "SELECT classificacao_pendente FROM parcelamentos WHERE id = %s", (id,)
    ).fetchone()
    return _ler_classificacao(linha[0]) if linha else {}


def _dar_por_refeita(conn, id: UUID, feita: Classificacao) -> None:
    """Tira do pendente o que acabou de ser refeito; se outra correção gravou campos novos no
    meio, o pendente mudou e fica para ela."""
    conn.execute(
        "UPDATE parcelamentos SET classificacao_pendente = '' WHERE id = %s"
        " AND coalesce(classificacao_pendente, '') = %s",
        (id, _gravar_classificacao(feita)),
    )


def _refazer_protegido(
    url: str | None,
    id: UUID,
    um_lote: Callable[[psycopg.Connection], bool],
    classificacao: Classificacao,
    manter_a_de_alcance: bool = False,
) -> None:
    """Os lotes do refazer da correção e a geração das parcelas que faltam, cada um com as
    regras da fatura paga (`cartoes.protegida`). A conferência de antes de gravar
    (`_conferir_os_lotes`) não vê a fatura paga depois dela: se um lote levaria uma parcela para
    dentro de uma, ele é recusado, as parcelas que faltam ficam como estão, a recusa fica
    gravada no parcelamento e sobe (ticket 180). A tarefa diária tenta de novo a cada dia: se a
    fatura deixar de estar paga, o conserto termina e a recusa sai."""
    try:
        while em_transacao(url, cartoes.protegida(um_lote)):
            pass
        # Antes de gerar: a geração já cria as parcelas com a classificação inteira.
        em_transacao(url, lambda conn: _dar_por_refeita(conn, id, classificacao))
        while em_transacao(url, cartoes.protegida(lambda conn: _gerar_um_lote(conn, id))):
            pass
        em_transacao(url, lambda conn: tirar_a_recusa(conn, id, so_a_da_correcao=True))
    except HTTPException as recusa:
        em_transacao(
            url,
            lambda conn, recusa=recusa: _desistir_do_conserto(
                conn, id, recusa, manter_a_de_alcance
            ),
        )
        raise


def _falta_conserto(conn, id: UUID) -> bool:
    if not (lidos := _ler(conn, "id = %s", (id,))):
        return False
    [regra] = lidos
    (geradas,) = conn.execute("SELECT geradas FROM parcelamentos WHERE id = %s", (id,)).fetchone()
    pendente = classificacao_pendente(conn, id)
    return (
        geradas < regra.parcelas
        or bool(pendente)
        or bool(_puladas_que_chegaram(conn, regra, geradas))
        or bool(_correcoes(conn, regra, geradas, pendente))
    )


def _reajustar_do_parcelamento(conn, id: UUID) -> bool:
    """Um lote do conserto da tarefa diária, em nome de quem alterou o parcelamento por último."""
    if not (lidos := _ler(conn, "id = %s", (id,))):
        return False
    return _reajustar_um_lote(conn, id, lidos[0].alterado_por, classificacao_pendente(conn, id))


def origem(descricao: str) -> str:
    """Como a tela de conflito nomeia a regra que mudou o lançamento ("O da regra ...")."""
    return f"o parcelamento {descricao}".strip()


def _conferir_faturas_das_parcelas(conn, novo: NovoParcelamento, primeira: date) -> None:
    """Nenhuma parcela cai numa fatura paga (ADR 0021). A parcela n cai n - 1 faturas depois da
    primeira, e a paga pode vir depois de uma fechada sem pagamento: confere todas aqui, porque
    a geração em lotes não volta atrás."""
    titular = faturas.ler_cartao(conn, novo.conta_id).titular
    ultima = faturas.somar_meses(primeira, novo.parcelas - 1)
    for mes in sorted(cartoes.meses_pagos(conn, titular.id)):
        if primeira <= mes <= ultima:
            raise cartoes.recusa_da_paga(conn, titular.id, mes)


def gravar(conn, novo: NovoParcelamento, usuario: str) -> tuple[Parcelamento, bool]:
    """Grava o parcelamento sem as parcelas (`gerar_as_parcelas` as gera depois) e devolve se é
    novo. Reenviar o mesmo id (a fila repete) devolve o gravado."""
    if ja := _ler(conn, "id = %s", (novo.id,)):
        return ja[0], False
    conferir_ligacoes(conn, novo)
    no_cartao = faturas.ler_cartao(conn, novo.conta_id) is not None
    if no_cartao and novo.automatico is False:
        raise recusar("o parcelamento no cartão é automático")
    novo = com_o_dia_do_lancamento(novo)
    # Como a recorrência (ticket 87): o boleto que já venceu inteiro não teria parcela nenhuma.
    if not no_cartao and mais_meses(novo.data, novo.parcelas - 1) < novo.dia_do_lancamento:
        raise recusar("o parcelamento termina antes de hoje")
    # A fatura da 1ª parcela (no cartão sem dia de fechamento, não há como escolher) é
    # conferida antes de gravar: senão a regra ficaria sem parcelas, e a tarefa diária
    # tentaria gerá-las todo dia.
    primeira = lancamentos.mes_em_que_conta(conn, novo.conta_id, novo.data)
    if no_cartao:
        _conferir_faturas_das_parcelas(conn, novo, primeira)
    tags = ids_das_tags(conn, novo.tags, usuario, set())
    gravado = conn.execute(
        f"INSERT INTO parcelamentos ({_COLUNAS}, geradas)"
        " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, now(), %s, now(), %s, %s, 0)"
        # Dois reenvios ao mesmo tempo: o segundo fica com o que o primeiro gravou.
        " ON CONFLICT (id) DO NOTHING",
        (
            novo.id,
            novo.total,
            novo.parcelas,
            novo.data,
            no_cartao or bool(novo.automatico),
            novo.descricao,
            novo.conta_id,
            novo.pessoa,
            usuario,
            usuario,
            novo.item_categoria_id,
            novo.dia_do_lancamento,
        ),
    ).rowcount
    if not gravado:
        return _ler(conn, "id = %s", (novo.id,))[0], False
    for categoria in novo.categoria_ids:
        conn.execute(
            "INSERT INTO parcelamento_categorias (parcelamento_id, categoria_id) VALUES (%s, %s)",
            (novo.id, categoria),
        )
    for tag in tags:
        conn.execute(
            "INSERT INTO parcelamento_tags (parcelamento_id, tag_id) VALUES (%s, %s)",
            (novo.id, tag),
        )
    if novo.partes:
        _gravar_partes(conn, novo.id, novo.partes, usuario)
    return _ler(conn, "id = %s", (novo.id,))[0], True


def criar(url: str | None, novo: NovoParcelamento, usuario: str) -> tuple[Parcelamento, bool]:
    """Grava o parcelamento e gera as parcelas; serve à rota e ao lote da fila."""
    criado, gravado = em_transacao(url, lambda conn: gravar(conn, novo, usuario))
    gerar_as_parcelas(url, novo.id)
    # Lido de novo depois da geração: as parcelas puladas só se sabem com ela. Excluído por
    # outra sessão no meio, fica o que foi gravado.
    with conectar(url) as conn:
        lidos = _ler(conn, "id = %s", (novo.id,))
    return para_a_leitura(lidos[0] if lidos else criado), gravado


@router.post(
    "/parcelamentos",
    status_code=201,
    response_model=Parcelamento,
    operation_id="criar_parcelamento",
)
def criar_parcelamento(
    novo: NovoParcelamento, usuario: UsuarioLogado, request: Request, response: Response
) -> Parcelamento:
    """Grava o parcelamento e gera todas as parcelas. Reenviar o mesmo id (a fila repete)
    devolve o gravado, com 200, e completa a geração se ela tiver parado no meio."""
    criado, gravado = criar(url_do_banco(request), novo, usuario)
    response.status_code = 201 if gravado else 200
    return criado


@router.get(
    "/parcelamentos", response_model=list[Parcelamento], operation_id="listar_parcelamentos"
)
def listar_parcelamentos(usuario: UsuarioLogado, request: Request) -> list[Parcelamento]:
    with conectar(url_do_banco(request)) as conn:
        return [para_a_leitura(p) for p in _ler(conn)]


def _tags_do_parcelamento(conn, id: UUID) -> list[UUID]:
    return [
        tag
        for (tag,) in conn.execute(
            "SELECT tag_id FROM parcelamento_tags WHERE parcelamento_id = %s", (id,)
        )
    ]


def parcelas_por_lote(conn, regra: Parcelamento) -> int:
    """Quantas parcelas cabem numa transação, pelas linhas que cada uma mexe (a folga do DSQL é
    a mesma da geração): as partes do parcelamento que entram e as que a parcela tem, que saem,
    porque a de partes próprias pode ter mais que ele, e ele pode não ter mais nenhuma."""
    (gravadas,) = conn.execute(
        "SELECT COALESCE(max(linhas), 0) FROM (SELECT p.lancamento_id, count(*)"
        " + sum((SELECT count(*) FROM parte_categorias c WHERE c.parte_id = p.id)"
        " + (SELECT count(*) FROM parte_tags t WHERE t.parte_id = p.id)) AS linhas"
        " FROM lancamento_partes p JOIN lancamentos l ON l.id = p.lancamento_id"
        " WHERE l.parcelamento_id = %s GROUP BY p.lancamento_id) AS por_parcela",
        (regra.id,),
    ).fetchone()
    return max(
        1,
        LINHAS_POR_LOTE
        // (
            10
            + 2 * (len(regra.categoria_ids) + len(regra.tags))
            + _linhas_das_partes(regra)
            + int(gravadas)
        ),
    )


_Acao = Literal["excluir", "reviver", "atualizar", "pular"]


@dataclass
class _Correcao:
    """O que falta fazer numa parcela para ela ficar como o parcelamento manda: sair, voltar
    (uma que a correção tirou antes), mudar ou sair como pulada (a data nova, no boleto, caiu
    antes de hoje). `valor`, `dia` e `mes` são os de depois."""

    id: UUID
    versao: int
    parcela: int
    acao: _Acao
    mudou: list[str]
    valor: int
    dia: date
    mes: date
    realizada: bool
    valor_antes: int
    dia_antes: date
    # As partes do parcelamento que a parcela passa a ter, divididas pelo valor dela; sem elas, e
    # com "partes" em `mudou`, a parcela só se divide de novo na proporção que já tem (o valor
    # mudou). `partes_a_mao`: a proporção é de uma pessoa, que a mudou só nesta parcela.
    partes: PartesDaParcela | None = None
    partes_a_mao: bool = False

    @property
    def muda_o_cronograma(self) -> bool:
        return self.acao in ("excluir", "pular") or (self.valor, self.dia) != (
            self.valor_antes,
            self.dia_antes,
        )

    @property
    def aviso(self) -> ParcelaQueMuda:
        sai = self.acao == "excluir"
        return ParcelaQueMuda(
            id=self.id,
            parcela=self.parcela,
            valor_centavos=self.valor_antes,
            data=self.dia_antes,
            valor_novo_centavos=None if sai else self.valor,
            data_nova=None if sai else self.dia,
            sai=sai,
        )


# O que vale para as parcelas quando o pedido o traz, menos onde uma pessoa o mudou à mão.
CLASSIFICACAO = frozenset(
    {"descricao", "categoria_ids", "tags", "pessoa", "item_categoria_id", "partes"}
)
# A classificação da compra: as partes, ou a categoria, as tags, a pessoa e o item dela. Quando a
# parcela ou o parcelamento têm partes, ela muda inteira ou fica inteira como está: a parcela não
# fica com partes e categoria própria ao mesmo tempo (ADR 0022).
DA_COMPRA = CLASSIFICACAO - {"descricao"}
# Os campos da parcela que o valor, o número de parcelas e a data do parcelamento dão.
CRONOGRAMA = frozenset({"valor_centavos", "data", "conta_id", "fatura_mes"})


class _NaFatura(NamedTuple):
    """Onde uma parcela do cartão está: o número dela, o titular e o mês da fatura."""

    parcela: int
    titular: UUID
    mes: date
    excluida: bool


def _onde_estao_as_parcelas(conn, id: UUID) -> dict[UUID, _NaFatura]:
    """A fatura de cada parcela do parcelamento que está num cartão, excluídas também."""
    return {
        lancamento_id: _NaFatura(n, titular, mes, excluida)
        for lancamento_id, n, titular, mes, excluida in conn.execute(
            f"SELECT l.id, l.parcela, COALESCE(c.titular_id, c.id),"
            f" {lancamentos.MES_EM_QUE_CONTA}, l.excluido_em IS NOT NULL"
            " FROM lancamentos l JOIN cartoes c ON c.id = l.conta_id"
            " WHERE l.parcelamento_id = %s",
            (id,),
        )
    }


def parcelas_nas_faturas_pagas(conn, id: UUID) -> set[int]:
    """O número das parcelas do parcelamento que estão numa fatura paga pelo pagamento (ADR
    0021): a correção as deixa como estão no valor, na data e na fatura (ticket 171). A da
    fatura importada do Mobills segue a correção, com o aviso das realizadas."""
    linhas = [
        (n, titular, mes)
        for n, titular, mes, excluida in _onde_estao_as_parcelas(conn, id).values()
        if not excluida
    ]
    pagas = {
        titular: {
            f.mes
            for f in cartoes.faturas_do_titular(conn, titular)
            if cartoes.paga_pelo_pagamento(f)
        }
        for titular in {t for _, t, _ in linhas}
    }
    return {n for n, titular, mes in linhas if mes in pagas[titular]}


def _faturas_pagas(conn, conta_ids: set[UUID]) -> dict[UUID, dict[date, bool]]:
    """De cada conta, os meses das faturas pagas e se foi pelo pagamento (`True`, só a correção
    de fatura a muda, ADR 0021) ou se é a importada do Mobills (`False`); fora do cartão, nada."""
    pagas: dict[UUID, dict[date, bool]] = {}
    for conta_id in conta_ids:
        cartao = faturas.ler_cartao(conn, conta_id)
        pagas[conta_id] = (
            {
                f.mes: cartoes.paga_pelo_pagamento(f)
                for f in cartoes.faturas_do_titular(conn, cartao.titular.id)
                if f.situacao == "paga"
            }
            if cartao
            else {}
        )
    return pagas


def _correcoes(
    conn,
    regra: Parcelamento,
    geradas: int,
    classificacao: Classificacao,
    dia_da_correcao: date | None = None,
    mantidas: set[int] | None = None,
    cronograma_pedido: frozenset[str] = frozenset(),
) -> list[_Correcao]:
    """As parcelas que não estão como o parcelamento manda, na ordem do número. A que uma pessoa
    mudou à mão fica como está nos campos que mudou (a conta segura também a data e a fatura), e
    o número dela entra em `mantidas` quando o pedido a mudaria: na classificação pedida, e no
    valor e na data se estão em `cronograma_pedido` (ticket 136). A
    classificação só se refaz no que o pedido trouxe (`classificacao`, cada campo a partir de
    uma parcela), para a descrição corrigida numa parcela só não voltar a cada correção de valor,
    e para a de "esta e as próximas" não chegar às de antes. A parcela que saiu antes, quando o
    parcelamento encolheu, volta se ele crescer de novo (as de depois de `geradas`), com tudo.
    No boleto, nada da correção vira lançamento antes de hoje (ticket 87): a prevista que a data
    nova leva de hoje ou depois para antes sai como pulada (`excluido_pela_regra`), e volta se
    outra correção a trouxer de novo para hoje ou depois. A atrasada (já antes de hoje) segue
    prevista com a data nova; a realizada muda, com a confirmação. O "de hoje ou depois" é do dia
    em que a correção foi pedida (`corrigido_em`), não do dia em que o lote roda: a que para no
    meio termina igual noutro dia (ticket 131)."""
    parcelas = conn.execute(
        f"SELECT id, parcela, data, valor_centavos, descricao, pessoa, situacao,"
        f" excluido_em IS NOT NULL, {lancamentos.VERSAO}, item_categoria_id, mes,"
        " COALESCE(excluido_pela_regra, false), conta_id"
        " FROM lancamentos WHERE parcelamento_id = %s"
        " ORDER BY parcela",
        (regra.id,),
    ).fetchall()
    ids = [linha[0] for linha in parcelas]
    pagas = _faturas_pagas(conn, {linha[12] for linha in parcelas})
    a_mao = lancamentos.campos_a_mao(conn, ids)
    mantidas = set() if mantidas is None else mantidas
    categorias: dict[UUID, set[UUID]] = {}
    for lancamento_id, categoria_id in conn.execute(
        "SELECT lancamento_id, categoria_id FROM lancamento_categorias"
        " WHERE lancamento_id = ANY(%s)",
        (ids,),
    ):
        categorias.setdefault(lancamento_id, set()).add(categoria_id)
    tags: dict[UUID, set[str]] = {}
    for lancamento_id, nome in conn.execute(
        "SELECT lt.lancamento_id, t.nome FROM lancamento_tags lt JOIN tags t ON t.id = lt.tag_id"
        " WHERE lt.lancamento_id = ANY(%s)",
        (ids,),
    ):
        tags.setdefault(lancamento_id, set()).add(nome.casefold())
    partes = lancamentos.ler_partes(conn, ids)
    tags_das_partes = _tags_das_partes(conn, regra.id) if regra.partes else {}
    no_cartao = faturas.ler_cartao(conn, regra.conta_id) is not None
    dia_de_hoje = lancamentos.hoje()
    if dia_da_correcao is None:
        dia_da_correcao = _corrigido_em(conn, regra.id) or dia_de_hoje
    quer = {
        "descricao": regra.descricao,
        "pessoa": regra.pessoa,
        "item_categoria_id": regra.item_categoria_id,
        "categoria_ids": set(regra.categoria_ids),
        "tags": {tag.casefold() for tag in regra.tags},
    }
    feitas = []
    for (
        lancamento_id,
        n,
        dia_antes,
        valor_antes,
        descricao,
        pessoa,
        situacao,
        excluida,
        versao,
        item_categoria_id,
        mes_antes,
        pulada,
        conta_da_parcela,
    ) in parcelas:
        maos = a_mao.get(lancamento_id, set())
        if not excluida and pagas[conta_da_parcela].get(mes_antes):
            # A da fatura paga pelo pagamento fica como está no valor, na data e na fatura, como
            # se uma pessoa os tivesse mudado à mão (tickets 170 e 171).
            maos = maos | CRONOGRAMA
        acao: _Acao = "atualizar"
        if excluida:
            if n > regra.parcelas or not (pulada or geradas < n):
                continue
            acao = "reviver"
        elif n > regra.parcelas:
            # Só valor, data, conta e fatura mudados à mão seguram a parcela que sobra.
            if maos & CRONOGRAMA:
                continue
            acao = "excluir"
        tem = {
            "descricao": descricao,
            "pessoa": pessoa,
            "item_categoria_id": item_categoria_id,
            "categoria_ids": categorias.get(lancamento_id, set()),
            "tags": tags.get(lancamento_id, set()),
        }
        campos = dict.fromkeys(CLASSIFICACAO, 1) if acao == "reviver" else classificacao
        pedidos_aqui = {c for c, desde in campos.items() if n >= desde}
        mudou = [c for c, querido in quer.items() if c in pedidos_aqui and querido != tem[c]]
        valor, dia, mes = valor_antes, dia_antes, mes_antes
        if acao != "excluir":
            pela_regra = valor_da_parcela(regra.valor_total_centavos, regra.parcelas, n)
            no_dia = regra.data if no_cartao else mais_meses(regra.data, n - 1)
            if "valor_centavos" not in maos:
                valor = pela_regra
            elif pela_regra != valor_antes and "valor_centavos" in cronograma_pedido:
                mantidas.add(n)
            if not maos & {"data", "conta_id"}:
                dia = no_dia
            elif no_dia != dia_antes and "data" in cronograma_pedido:
                mantidas.add(n)
            if (dia != dia_antes or acao == "reviver") and not maos & {"fatura_mes", "conta_id"}:
                # Pelo cartão em que a parcela está: o reemitido em "todas" pode ainda não ter
                # chegado a ela (ticket 187).
                mes = lancamentos.mes_em_que_conta(conn, conta_da_parcela, dia, n)
            if valor != valor_antes:
                mudou.append("valor_centavos")
            if dia != dia_antes:
                mudou.append("data")
            # A fatura que o app escolheu de novo conta como mudança do parcelamento (ADR 0011).
            if no_cartao and mes != mes_antes:
                mudou.append("fatura_mes")
        tem_partes = partes.get(lancamento_id, [])
        novas_partes = None
        if "partes" in pedidos_aqui and acao != "excluir":
            novas_partes = partes_da_parcela(regra, tags_das_partes, lancamento_id, valor)
            if novas_partes.sem_ids() != list(map(lancamentos.parte_sem_id, tem_partes)):
                mudou.append("partes")
        da_compra = [c for c in mudou if c in DA_COMPRA]
        if regra.partes or tem_partes:
            # A classificação da compra muda inteira, ou fica inteira se alguém a mudou só aqui.
            presos = da_compra if maos & DA_COMPRA else []
        else:
            presos = [c for c in da_compra if c in maos]
        if "descricao" in mudou and "descricao" in maos:
            presos.append("descricao")
        if presos:
            mantidas.add(n)
            mudou = [c for c in mudou if c not in presos]
        if "partes" not in mudou:
            novas_partes = None
            # Com outro valor, a parcela se divide de novo na proporção que tem (ticket 139).
            if tem_partes and valor != valor_antes and acao != "excluir":
                mudou.append("partes")
        if not no_cartao and dia < dia_de_hoje:
            if acao == "reviver":
                if pulada:
                    continue
                acao = "pular"  # a que o encolher tirou volta, mas já passou
            elif acao == "atualizar" and situacao == "previsto" and dia_antes >= dia_da_correcao:
                acao = "pular"
        if acao != "atualizar" or mudou:
            feitas.append(
                _Correcao(
                    lancamento_id,
                    versao,
                    n,
                    acao,
                    mudou,
                    valor,
                    dia,
                    mes,
                    situacao == "realizado",
                    valor_antes,
                    dia_antes,
                    novas_partes,
                    "partes" in maos,
                )
            )
    return feitas


@dataclass
class CorrecaoGravada:
    """A correção gravada no parcelamento: a classificação a refazer nas parcelas e o número das
    que ficam como estavam em algum campo pedido, porque uma pessoa o mudou só nelas."""

    classificacao: dict[str, int]
    mantidas: set[int]


def gravar_correcao(
    conn,
    id: UUID,
    alteracao: AlteracaoDeParcelamento,
    usuario: str,
    desde: int = 1,
    editada: UUID | None = None,
    tambem_mudam: Sequence[ParcelaQueMuda] = (),
    conferir_os_lotes: bool = True,
) -> CorrecaoGravada:
    """Valida e grava o parcelamento corrigido (recusa antes de gravar, e avisa se uma realizada
    mudaria sem `confirmar_realizadas`); as parcelas são refeitas depois, em lotes. A
    classificação vale a partir da parcela `desde`. Na mudança de uma parcela com alcance (ticket
    136), a `editada` segue o parcelamento nos campos pedidos mesmo que alguém a tenha mudado à
    mão, não entra no aviso nem na contagem, e o aviso leva também as realizadas
    `tambem_mudam`. Sem `conferir_os_lotes`, quem chama já conferiu as regras da fatura paga
    no refazer (o cartão reemitido junto com a data ou o valor, ticket 196)."""
    if not (lidos := _ler(conn, "id = %s", (id,))):
        raise HTTPException(status_code=404, detail="parcelamento não encontrado")
    [atual] = lidos
    (geradas,) = conn.execute("SELECT geradas FROM parcelamentos WHERE id = %s", (id,)).fetchone()
    pedidas = alteracao.model_dump(
        include=alteracao.model_fields_set
        - {"valor_total_centavos", "valor_da_parcela_centavos", "confirmar_realizadas", "partes"}
    )
    if alteracao.partes is not None:
        # Dividir tira a classificação própria do parcelamento; uma parte só a devolve (ADR 0022).
        pedidas |= lancamentos.o_que_as_partes_mudam(alteracao.partes, pedidas)
    if atual.item_categoria_id not in pedidas.get("categoria_ids", [atual.item_categoria_id]):
        pedidas.setdefault("item_categoria_id", None)  # a escolha sai com a categoria dela
    parcelas = pedidas.get("parcelas", atual.parcelas)
    if alteracao.valor_total_centavos:
        total = alteracao.valor_total_centavos
    elif alteracao.valor_da_parcela_centavos:
        total = alteracao.valor_da_parcela_centavos * parcelas
    else:
        total = atual.valor_total_centavos
    if total < parcelas:
        raise recusar("o total não chega a um centavo por parcela")
    try:
        nova = Parcelamento(**(atual.model_dump() | pedidas | {"valor_total_centavos": total}))
    except ValidationError as erro:
        raise recusar("; ".join(e["msg"] for e in erro.errors())) from erro
    conferir_ligacoes(
        conn,
        nova,
        atual.conta_id,
        frozenset(atual.categoria_ids) | {c for p in atual.partes for c in p.categoria_ids},
    )
    lancamentos.conferir_partes_do_parcelamento_com_estorno(
        conn, id, nova.partes, nova.valor_total_centavos, nova.parcelas
    )
    if nova.partes:
        lancamentos.conferir_divisao(
            nova.valor_total_centavos // nova.parcelas, [p.valor_centavos for p in nova.partes]
        )
        if not atual.partes:
            lancamentos.conferir_sem_estorno(
                conn,
                [
                    i
                    for (i,) in conn.execute(
                        "SELECT id FROM lancamentos WHERE parcelamento_id = %s"
                        " AND excluido_em IS NULL",
                        (id,),
                    )
                ],
            )
    nas_pagas = parcelas_nas_faturas_pagas(conn, id)
    if nas_pagas and nova.parcelas < (ultima := max(nas_pagas)):
        # Um "3/2" não faz sentido: a parcela da fatura paga não sai (ticket 171).
        raise recusar(
            f"a parcela {ultima} está numa fatura paga: o parcelamento não fica com menos de"
            f" {ultima} parcelas (para mudá-la, use a correção da fatura)"
        )
    sobram = dict(
        conn.execute(
            "SELECT id, parcela FROM lancamentos WHERE parcelamento_id = %s"
            " AND excluido_em IS NULL AND parcela > %s",
            (id, nova.parcelas),
        ).fetchall()
    )
    a_mao = [
        sobram[lancamento_id]
        for lancamento_id, campos in lancamentos.campos_a_mao(conn, list(sobram)).items()
        if campos & CRONOGRAMA
    ]
    if a_mao:
        raise recusar(
            f"a parcela {max(a_mao)} foi editada à mão: exclua-a antes de tirá-la do parcelamento"
        )
    geradas_depois = min(geradas, nova.parcelas)
    # Junto com o que correções anteriores deixaram pendente: o refazer deste pedido leva tudo.
    classificacao = _juntar(
        dict.fromkeys(CLASSIFICACAO & pedidas.keys(), desde), classificacao_pendente(conn, id)
    )
    if editada:
        _seguir_o_parcelamento(conn, editada, nova, alteracao.model_fields_set | pedidas.keys())
    mantidas: set[int] = set()
    correcoes = _correcoes(
        conn,
        nova,
        geradas_depois,
        classificacao,
        lancamentos.hoje(),
        mantidas,
        _cronograma_pedido(alteracao),
    )
    _conferir_as_divisoes(conn, correcoes)
    # Antes do aviso e de gravar: a parcela com estorno não sai, como na exclusão (ticket 188).
    for t in correcoes:
        if t.acao in ("excluir", "pular"):
            try:
                lancamentos.conferir_sem_estorno(conn, [t.id])
            except HTTPException as recusa:
                raise recusar(f"a parcela {t.parcela}: {recusa.detail}") from recusa
    lancamentos.conferir_o_que_fica_do_estorno_de_todas(
        conn,
        id,
        nova.parcelas,
        nova.valor_total_centavos,
        lambda n: valor_da_parcela(nova.valor_total_centavos, nova.parcelas, n),
    )
    realizadas = [
        *tambem_mudam,
        *(
            t.aviso
            for t in correcoes
            # A que sai pulada sendo realizada já estava excluída (o encolher a tirou): nada muda.
            if t.realizada
            and t.acao not in ("reviver", "pular")
            and t.muda_o_cronograma
            and t.id != editada
        ),
    ]
    if editada:
        (numero,) = conn.execute(
            "SELECT parcela FROM lancamentos WHERE id = %s", (editada,)
        ).fetchone()
        mantidas.discard(numero)
    # Antes do aviso: o pedido que vai ser recusado não pede para confirmar as realizadas.
    if conferir_os_lotes:
        _conferir_os_lotes(conn, nova, correcoes, geradas_depois)
    if realizadas and not alteracao.confirmar_realizadas:
        raise RealizadasMudam(
            AvisoDeRealizadas(
                motivo="a correção muda parcelas que já foram realizadas", parcelas=realizadas
            )
        )
    tags_de_antes = set(_tags_do_parcelamento(conn, id))
    tags = ids_das_tags(conn, nova.tags, usuario, tags_de_antes)
    if not conn.execute(
        "UPDATE parcelamentos SET valor_total_centavos = %s, parcelas = %s, data = %s,"
        " descricao = %s, pessoa = %s, item_categoria_id = %s, geradas = %s, alterado_por = %s,"
        " classificacao_pendente = %s, corrigido_em = %s, alterado_em = now()"
        " WHERE id = %s AND geradas = %s",
        (
            nova.valor_total_centavos,
            nova.parcelas,
            nova.data,
            nova.descricao,
            nova.pessoa,
            nova.item_categoria_id,
            geradas_depois,
            usuario,
            _gravar_classificacao(classificacao),
            # Só a correção de valor, parcelas ou data tira o dia do lançamento (ticket 144).
            lancamentos.hoje() if _muda_o_calendario(atual, nova) else _corrigido_em(conn, id),
            id,
            geradas,
        ),
    ).rowcount:
        raise psycopg.errors.SerializationFailure("o parcelamento mudou durante a correção")
    if set(nova.categoria_ids) != set(atual.categoria_ids):
        conn.execute("DELETE FROM parcelamento_categorias WHERE parcelamento_id = %s", (id,))
        for categoria in nova.categoria_ids:
            conn.execute(
                "INSERT INTO parcelamento_categorias (parcelamento_id, categoria_id)"
                " VALUES (%s, %s)",
                (id, categoria),
            )
    if set(tags) != tags_de_antes:
        conn.execute("DELETE FROM parcelamento_tags WHERE parcelamento_id = %s", (id,))
        for tag in tags:
            conn.execute(
                "INSERT INTO parcelamento_tags (parcelamento_id, tag_id) VALUES (%s, %s)",
                (id, tag),
            )
    if "partes" in pedidas and not lancamentos.iguais("partes", nova.partes, atual.partes):
        _gravar_partes(conn, id, nova.partes, usuario)
    # O estorno de todas as parcelas segue a classificação do parcelamento (ticket 138).
    lancamentos.acompanhar_estornos_do_parcelamento(conn, id)
    return CorrecaoGravada(classificacao, mantidas)


def _conferir_os_lotes(
    conn, regra: Parcelamento, correcoes: list[_Correcao], geradas_depois: int
) -> None:
    """As regras da fatura paga (ADR 0021) em cada lote do refazer e na geração das parcelas
    que faltam, simuladas antes de gravar (`cartoes.conferir_sem_gravar`): a parcela que entraria
    numa fatura paga recusa o pedido inteiro, e não só o lote em que ela cai (ticket 171). As
    que já estão numa fatura paga não mudam (`parcelas_nas_faturas_pagas`)."""
    na_fatura = _onde_estao_as_parcelas(conn, regra.id)
    sinal = 1 if regra.tipo == "despesa" else -1
    por_lote = parcelas_por_lote(conn, regra)
    lotes: list[Counter] = []
    for inicio in range(0, len(correcoes), por_lote):
        lote: Counter = Counter()
        for correcao in correcoes[inicio : inicio + por_lote]:
            if not (antes := na_fatura.get(correcao.id)):
                continue  # fora do cartão
            # Sai da fatura em que está com o valor de antes e entra na nova com o de depois.
            if not antes.excluida:
                lote[antes.titular, antes.mes] -= sinal * correcao.valor_antes
            if correcao.acao in ("atualizar", "reviver"):
                lote[antes.titular, correcao.mes] += sinal * correcao.valor
        lotes.append(lote)
    cartao = faturas.ler_cartao(conn, regra.conta_id)
    if cartao is not None:
        existem = {
            n
            for (n,) in conn.execute(
                "SELECT parcela FROM lancamentos WHERE parcelamento_id = %s", (regra.id,)
            )
        }
        geracao: Counter = Counter()
        for n in range(geradas_depois + 1, regra.parcelas + 1):
            if n not in existem:
                mes = faturas.mes_da_parcela(conn, cartao.titular, regra.data, n)
                geracao[cartao.titular.id, mes] += sinal * valor_da_parcela(
                    regra.valor_total_centavos, regra.parcelas, n
                )
        lotes.append(geracao)
    # A fatura em que a soma não muda (só a classificação mudou) não entra na simulação.
    passos = [{chave: valor for chave, valor in lote.items() if valor} for lote in lotes]
    if any(passos):
        cartoes.conferir_sem_gravar(conn, passos)


def _conferir_as_divisoes(conn, correcoes: list[_Correcao]) -> None:
    """Cada parcela que a correção divide de novo fica com um centavo ou mais por parte, na
    proporção do parcelamento ou na que ela já tem. Conferido antes de gravar: o refazer em lotes
    não volta atrás, e a recusa no meio dele deixaria a correção pela metade."""
    redivididas = [t for t in correcoes if "partes" in t.mudou and t.acao != "excluir"]
    proporcoes = lancamentos.proporcao_das_partes(conn, [t.id for t in redivididas])
    for t in redivididas:
        if t.partes is not None:
            if any(p.valor_centavos <= 0 for p, _ in t.partes.partes):
                raise recusar(lancamentos.SEM_CENTAVO_POR_PARTE)
        else:
            lancamentos.conferir_divisao(t.valor, proporcoes.get(t.id, []))


def _cronograma_pedido(alteracao: AlteracaoDeParcelamento) -> frozenset[str]:
    """O valor e a data das parcelas que a correção pede para refazer."""
    pedidos = alteracao.model_fields_set
    campos = set()
    if pedidos & {"valor_total_centavos", "valor_da_parcela_centavos", "parcelas"}:
        campos.add("valor_centavos")
    if "data" in pedidos:
        campos.add("data")
    return frozenset(campos)


# O campo pedido ao parcelamento e os da parcela que ele refaz.
_CAMPOS_DA_CORRECAO = {
    "valor_total_centavos": ("valor_centavos",),
    "valor_da_parcela_centavos": ("valor_centavos",),
    "parcelas": ("valor_centavos",),
    "data": ("data", "fatura_mes"),
}


def _seguir_o_parcelamento(conn, editada: UUID, regra: Parcelamento, pedidos) -> None:
    """Tira a marca de "alterada à mão" da parcela editada nos campos que o pedido muda: ela
    passa a seguir o parcelamento neles, e a correção a refaz como as outras."""
    campos = [c for p in pedidos for c in _CAMPOS_DA_CORRECAO.get(p, (p,))]
    conn.execute(
        "UPDATE lancamento_campos SET origem = %s"
        " WHERE lancamento_id = %s AND origem IS NULL AND campo = ANY(%s)",
        (origem(regra.descricao), editada, campos),
    )


def _aplicar(
    conn,
    regra: Parcelamento,
    correcao: _Correcao,
    tags: list[UUID],
    usuario: str,
    agora: datetime,
) -> None:
    """Põe uma parcela como o parcelamento manda: sai, volta, muda ou sai como pulada."""
    if correcao.acao in ("excluir", "pular"):
        excluir(conn, correcao.id, None, usuario)
        if correcao.acao == "pular":
            conn.execute(
                "UPDATE lancamentos SET excluido_pela_regra = true WHERE id = %s", (correcao.id,)
            )
        return
    atribuicoes = "valor_centavos = %s, data = %s, mes = %s, alterado_por = %s, alterado_em = %s"
    parametros: tuple = (correcao.valor, correcao.dia, correcao.mes, usuario, agora)
    for campo in ("descricao", "pessoa", "item_categoria_id"):
        if campo in correcao.mudou:
            atribuicoes += f", {campo} = %s"
            parametros += (getattr(regra, campo),)
    if correcao.acao == "reviver":
        atribuicoes += ", excluido_em = NULL, excluido_por = NULL, excluido_pela_regra = false"
    if {"categoria_ids", "fatura_mes"} & set(correcao.mudou) or correcao.acao == "reviver":
        # No mês novo ou com a categoria nova, a parcela fica no item em que estava.
        lancamentos.guardar_item_atual_do_lancamento(conn, correcao.id)
        (item_atual,) = conn.execute(
            "SELECT item_atual_categoria_id FROM lancamentos WHERE id = %s", (correcao.id,)
        ).fetchone()
        atribuicoes += ", item_atual_categoria_id = %s"
        parametros += (item_atual if item_atual in regra.categoria_ids else None,)
    nova = subir_versao(conn, correcao.id, correcao.versao, atribuicoes, parametros)
    # A proporção que uma pessoa deu só a esta parcela continua dela, dividida pelo valor novo.
    da_pessoa = ["partes"] if correcao.partes_a_mao and "partes" in correcao.mudou else []
    registrar_mudancas(
        conn,
        correcao.id,
        [c for c in correcao.mudou if c not in da_pessoa],
        nova,
        usuario,
        agora,
        origem=origem(regra.descricao),
    )
    registrar_mudancas(conn, correcao.id, da_pessoa, nova, usuario, agora)
    if "partes" in correcao.mudou:
        if correcao.partes is not None:
            lancamentos.gravar_partes_por_id(
                conn, correcao.id, correcao.partes.partes, correcao.partes.proporcao
            )
        else:
            lancamentos.redividir_partes(conn, correcao.id, correcao.valor)
    if "categoria_ids" in correcao.mudou:
        gravar_categorias(conn, correcao.id, regra.categoria_ids)
    if "tags" in correcao.mudou:
        conn.execute("DELETE FROM lancamento_tags WHERE lancamento_id = %s", (correcao.id,))
        for tag in tags:
            conn.execute(
                "INSERT INTO lancamento_tags (lancamento_id, tag_id) VALUES (%s, %s)",
                (correcao.id, tag),
            )
    lancamentos.acompanhar_estornos(conn, correcao.id)


def _reajustar_um_lote(conn, id: UUID, usuario: str, classificacao: Classificacao) -> bool:
    """Põe as parcelas de acordo com o parcelamento de hoje, até um lote, e devolve se pode faltar
    alguma. A que já está como ele manda não conta, por isso o lote seguinte sempre anda."""
    if not (lidos := _ler(conn, "id = %s", (id,))):
        return False
    [regra] = lidos
    (geradas,) = conn.execute("SELECT geradas FROM parcelamentos WHERE id = %s", (id,)).fetchone()
    trabalho = _correcoes(conn, regra, geradas, classificacao)
    tags = _tags_do_parcelamento(conn, id)
    agora = datetime.now(UTC)
    por_lote = parcelas_por_lote(conn, regra)
    for correcao in trabalho[:por_lote]:
        _aplicar(conn, regra, correcao, tags, usuario, agora)
    return len(trabalho) > por_lote


_AVISO = {409: {"model": AvisoDeRealizadas, "description": "A correção muda parcelas realizadas"}}


class ParcelamentoCorrigido(Parcelamento):
    # Quantas parcelas ficaram como estavam em algum campo da correção, porque uma pessoa o
    # mudou só nelas (ticket 136).
    parcelas_mantidas: int


def refazer_as_parcelas(url: str | None, id: UUID, usuario: str, classificacao) -> None:
    """Depois de gravada a correção, põe as parcelas de acordo, em lotes, e gera as que faltam."""
    # Import aqui: `automaticos` importa este módulo.
    from app import automaticos

    _refazer_protegido(
        url, id, lambda conn: _reajustar_um_lote(conn, id, usuario, classificacao), classificacao
    )
    # A parcela automática que a data nova já alcançou se realiza agora, como na criação.
    automaticos.realizar_automaticos(url, id)


def _gravar_e_tirar_a_recusa(
    conn, id: UUID, alteracao: AlteracaoDeParcelamento, usuario: str
) -> CorrecaoGravada:
    """A correção nova refaz as parcelas desde o começo: a recusa de antes sai do parcelamento
    (se ela se repetir no refazer, volta)."""
    gravada = gravar_correcao(conn, id, alteracao, usuario)
    tirar_a_recusa(conn, id)
    return gravada


@router.patch(
    "/parcelamentos/{id}",
    response_model=ParcelamentoCorrigido,
    operation_id="alterar_parcelamento",
    responses=_AVISO,
)
def alterar_parcelamento(
    id: UUID, alteracao: AlteracaoDeParcelamento, usuario: UsuarioLogado, request: Request
) -> ParcelamentoCorrigido | JSONResponse:
    """Corrige o parcelamento e põe as parcelas de acordo; a que uma pessoa mudou à mão fica como
    está nos campos que mudou, a de fatura paga fica como está no valor, na data e na fatura, e a
    resposta diz quantas ficaram assim. Encolher para menos parcelas que a última de fatura paga
    ou levar uma parcela para dentro de uma fatura paga recusa o pedido (422) sem gravar nada. Se
    uma parcela realizada mudar ou sair, responde 409 com o aviso e não grava nada até o pedido
    vir com `confirmar_realizadas`. Se parar no meio, repetir o pedido continua."""
    url = url_do_banco(request)
    try:
        mudanca = em_transacao(
            url, lambda conn: _gravar_e_tirar_a_recusa(conn, id, alteracao, usuario)
        )
    except RealizadasMudam as e:
        return JSONResponse(e.aviso.model_dump(mode="json"), status_code=409)
    try:
        refazer_as_parcelas(url, id, usuario, mudanca.classificacao)
    except HTTPException as recusa:
        # Uma fatura foi paga depois da conferência de antes de gravar (ticket 180).
        raise recusar(
            f"{recusa.detail}. A correção foi gravada e as primeiras parcelas mudaram;"
            " as que faltavam ficaram como estavam"
        ) from recusa
    with conectar(url) as conn:
        if not (lidos := _ler(conn, "id = %s", (id,))):
            # Excluído por outra sessão no meio do refazer: as parcelas saíram com ele.
            raise HTTPException(status_code=404, detail="parcelamento não encontrado")
        return ParcelamentoCorrigido(
            **para_a_leitura(lidos[0]).model_dump(), parcelas_mantidas=len(mudanca.mantidas)
        )


def _excluir_um_lote(conn, id: UUID, ids: list[UUID], usuario: str) -> list[UUID]:
    """Exclui, até um lote, as parcelas de `ids` (o que a exclusão decidiu tirar) e devolve as
    que faltam."""
    if not (lidos := _ler(conn, "id = %s", (id,))):
        return []
    por_lote = parcelas_por_lote(conn, lidos[0])
    for lancamento_id in ids[:por_lote]:
        excluir(conn, lancamento_id, None, usuario)
    return ids[por_lote:]


class AvisoDeExclusao(BaseModel):
    """Excluir o parcelamento apagaria parcelas já pagas ou alteradas à mão; nada foi apagado.
    Repetir o pedido com `confirmar_realizadas` apaga. As alteradas à mão também entram nas
    outras contas quando são de fatura paga ou realizadas. As parcelas da fatura paga pelo
    pagamento não saem (ADR 0021): o parcelamento fica, encolhido até a última delas."""

    motivo: str
    # Quantas parcelas saem, de qualquer tipo.
    parcelas: int
    # No cartão, as da fatura paga que saem: só as da importada do Mobills.
    de_fatura_paga: int
    # As realizadas fora da fatura paga: no cartão, as da fatura aberta ou fechada sem
    # pagamento; no boleto, as pagas.
    realizadas: int
    alteradas_a_mao: int
    # As da fatura paga pelo pagamento, que ficam: para tirá-las, o casal corrige a fatura.
    ficam_de_fatura_paga: int


class ExclusaoPedeConfirmacao(Exception):
    """A exclusão pede confirmação: apaga parcelas pagas ou alteradas à mão."""

    def __init__(self, aviso: AvisoDeExclusao):
        self.aviso = aviso


@dataclass
class _Exclusao:
    """O que a exclusão faz, decidido antes do primeiro lote: as parcelas que saem e, quando
    alguma fica na fatura paga pelo pagamento, até qual parcela o parcelamento encolhe e o total
    que sobra."""

    saem: list[UUID]
    aviso: AvisoDeExclusao | None
    # O número da última parcela que fica; `None` quando todas saem e o parcelamento some.
    ultima_que_fica: int | None
    total_que_fica: int


@dataclass
class _ParcelaQueSairia:
    id: UUID
    parcela: int
    valor: int
    conta_id: UUID
    mes: date
    situacao: str
    alterada_a_mao: bool


def _exclusao(conn, id: UUID) -> _Exclusao:
    """Separa as parcelas que ficam (as da fatura paga pelo pagamento, ADR 0021) das que saem, e
    conta para o aviso o que sai de cada tipo e o que fica."""
    linhas = [
        _ParcelaQueSairia(*linha)
        for linha in conn.execute(
            f"SELECT id, parcela, valor_centavos, conta_id, {lancamentos.MES_EM_QUE_CONTA},"
            f" situacao, {lancamentos.ALTERADA_A_MAO}"
            " FROM lancamentos WHERE parcelamento_id = %s AND excluido_em IS NULL"
            " ORDER BY parcela",
            (id,),
        )
    ]
    pagas = _faturas_pagas(conn, {p.conta_id for p in linhas})
    ficam = [p for p in linhas if pagas[p.conta_id].get(p.mes)]
    saem = [p for p in linhas if not pagas[p.conta_id].get(p.mes)]
    # As da fatura paga que saem são as da importada do Mobills.
    de_fatura_paga = sum(1 for p in saem if p.mes in pagas[p.conta_id])
    realizadas = sum(
        1 for p in saem if p.situacao == "realizado" and p.mes not in pagas[p.conta_id]
    )
    alteradas = sum(1 for p in saem if p.alterada_a_mao)
    aviso = None
    if saem and (de_fatura_paga or realizadas or alteradas or ficam):
        aviso = AvisoDeExclusao(
            motivo="isto apaga lançamentos já pagos e pode desconfigurar o histórico",
            parcelas=len(saem),
            de_fatura_paga=de_fatura_paga,
            realizadas=realizadas,
            alteradas_a_mao=alteradas,
            ficam_de_fatura_paga=len(ficam),
        )
    return _Exclusao(
        [p.id for p in saem],
        aviso,
        max((p.parcela for p in ficam), default=None),
        sum(p.valor for p in ficam),
    )


@router.delete(
    "/parcelamentos/{id}",
    status_code=204,
    operation_id="excluir_parcelamento",
    responses={
        409: {
            "model": AvisoDeExclusao,
            "description": "A exclusão apaga parcelas pagas ou alteradas à mão",
        }
    },
)
def excluir_parcelamento(
    id: UUID, usuario: UsuarioLogado, request: Request, confirmar_realizadas: bool = False
) -> Response:
    """Idempotente. Exclui o parcelamento e as parcelas, também as realizadas e as que uma pessoa
    editou à mão (a exclusão de um lançamento é a de sempre: quem o edita depois recebe o aviso de
    excluído), menos as da fatura paga pelo pagamento (ADR 0021, ticket 170): essas ficam, e o
    parcelamento continua, encolhido até a última delas, com o total igual à soma delas e nada
    mais a gerar; a parcela de antes dela que sai fica como excluída uma a uma. Se alguma parcela
    é de fatura paga, realizada ou alterada à mão, responde 409 com quantas de cada tipo saem e
    quantas ficam, e não apaga nada até o pedido vir com `confirmar_realizadas` (ticket 142)."""
    url = url_do_banco(request)

    def fechar(conn) -> _Exclusao:
        lancamentos.conferir_parcelamento_sem_estorno(conn, id)
        plano = _exclusao(conn, id)
        # Antes de fechar o parcelamento: a parcela com estorno impediria a exclusão no meio dela.
        conferir_sem_estorno(conn, plano.saem)
        if not confirmar_realizadas and plano.aviso:
            raise ExclusaoPedeConfirmacao(plano.aviso)
        # Com todas as parcelas dadas por geradas, a tarefa diária não gera novas enquanto as de
        # agora saem, nem depois, no parcelamento que encolheu.
        if plano.ultima_que_fica is None:
            conn.execute("UPDATE parcelamentos SET geradas = parcelas WHERE id = %s", (id,))
        else:
            # A tabela pede duas parcelas ou mais, e o DSQL não tira a restrição (ADR 0014): com
            # só a 1ª de fatura paga, fica um 2x com a 2ª excluída uma a uma. Decidido com o dono
            # no ticket 176: o 2x fica, sem tratamento na tela, como o 5x encolhido sem a 4ª.
            parcelas = max(plano.ultima_que_fica, 2)
            conn.execute(
                "UPDATE parcelamentos SET parcelas = %s, geradas = %s, valor_total_centavos = %s"
                " WHERE id = %s",
                (parcelas, parcelas, plano.total_que_fica, id),
            )
        return plano

    try:
        plano = em_transacao(url, fechar)
    except ExclusaoPedeConfirmacao as e:
        return JSONResponse(e.aviso.model_dump(mode="json"), status_code=409)
    faltam = plano.saem
    while faltam:
        faltam = em_transacao(
            url, lambda conn, lote=faltam: _excluir_um_lote(conn, id, lote, usuario)
        )
    if plano.ultima_que_fica is not None:
        return Response(status_code=204)

    def tirar(conn) -> None:
        _apagar_partes(conn, id)
        conn.execute("DELETE FROM parcelamento_categorias WHERE parcelamento_id = %s", (id,))
        conn.execute("DELETE FROM parcelamento_tags WHERE parcelamento_id = %s", (id,))
        conn.execute("DELETE FROM antecipacoes WHERE parcelamento_id = %s", (id,))
        conn.execute("DELETE FROM parcelamentos WHERE id = %s", (id,))

    em_transacao(url, tirar)
    return Response(status_code=204)


class Antecipacao(BaseModel):
    """O pagamento adiantado das últimas parcelas que ainda não foram pagas."""

    # Quantas parcelas, tiradas do fim.
    parcelas: int = Field(ge=1)
    # O dia do pagamento; sem ele, hoje. Não pode ser futuro.
    data: date | None = None
    # O que foi pago pelas parcelas juntas (o desconto é a diferença); sem o campo, o valor
    # delas. Os centavos que sobram da divisão vão na primeira das antecipadas.
    valor_total_centavos: int | None = Field(default=None, gt=0)
    # Chave de idempotência (por exemplo o id da antecipação gerado no aparelho): repetir o pedido
    # com a mesma chave devolve as parcelas já antecipadas, sem antecipar as K seguintes.
    id: UUID | None = None


class Quitacao(BaseModel):
    """O pagamento de uma vez de tudo o que falta."""

    data: date | None = None
    valor_total_centavos: int | None = Field(default=None, gt=0)


def _antecipar(
    conn,
    id: UUID,
    quantas: int | None,
    data: date | None,
    valor: int | None,
    usuario: str,
    chave: UUID | None = None,
) -> list[UUID]:
    """Realiza as últimas `quantas` parcelas previstas (todas, se `quantas` é `None`) no dia do
    pagamento, com o valor pago dividido entre elas. No cartão, a parcela conta na fatura em
    que foi paga (a que fecha depois do dia), marcada como troca à mão para as datas do
    cartão e a data da compra não a levarem de volta à fatura dela. Com `chave` já usada neste
    parcelamento, devolve as parcelas daquela antecipação sem pagar mais nenhuma (ticket 154)."""
    gravado = conn.execute(
        "SELECT geradas, parcelas FROM parcelamentos WHERE id = %s", (id,)
    ).fetchone()
    if not gravado:
        raise HTTPException(status_code=404, detail="parcelamento não encontrado")
    if chave is not None:
        feita = conn.execute(
            "SELECT lancamento_id, parcelamento_id FROM antecipacoes WHERE id = %s", (chave,)
        ).fetchall()
        if feita:
            if any(parcelamento != id for _, parcelamento in feita):
                raise lancamentos.recusar("a chave já foi usada em outro parcelamento")
            return [lancamento for lancamento, _ in feita]
    (geradas, total) = gravado
    dia = data or lancamentos.hoje()
    if dia > lancamentos.hoje():
        raise lancamentos.recusar("a antecipação é de um pagamento que já aconteceu")
    if geradas < total:
        raise lancamentos.recusar("as parcelas ainda estão sendo geradas")
    previstas = conn.execute(
        f"SELECT id, {lancamentos.VERSAO}, valor_centavos, conta_id, parcela FROM lancamentos"
        " WHERE parcelamento_id = %s AND situacao = 'previsto' AND excluido_em IS NULL"
        " ORDER BY parcela DESC",
        (id,),
    ).fetchall()
    quantas = len(previstas) if quantas is None else quantas
    if not previstas or quantas > len(previstas):
        raise lancamentos.recusar("não há tantas parcelas por pagar")
    escolhidas = previstas[:quantas][::-1]
    devido = sum(linha[2] for linha in escolhidas)
    pago = devido if valor is None else valor
    if pago < quantas:
        raise lancamentos.recusar("o valor não chega a um centavo por parcela")
    momento = datetime.now(UTC)
    for posicao, (lancamento_id, versao, _, conta_id, _) in enumerate(escolhidas, start=1):
        fatura = lancamentos.mes_em_que_conta(conn, conta_id, dia)
        no_cartao = faturas.ler_cartao(conn, conta_id) is not None
        lancamentos.guardar_item_atual_do_lancamento(conn, lancamento_id)
        nova = lancamentos.subir_versao(
            conn,
            lancamento_id,
            versao,
            "situacao = 'realizado', valor_centavos = %s, data = %s, mes = %s,"
            " fatura_a_mao = %s, alterado_por = %s, alterado_em = %s",
            (
                valor_da_parcela(pago, quantas, posicao),
                dia,
                fatura,
                no_cartao,
                usuario,
                momento,
            ),
        )
        campos = ["situacao", "valor_centavos", "data"] + (["fatura_mes"] if no_cartao else [])
        lancamentos.registrar_mudancas(conn, lancamento_id, campos, nova, usuario, momento)
        lancamentos.redividir_partes(conn, lancamento_id, valor_da_parcela(pago, quantas, posicao))
    antecipadas = [linha[0] for linha in escolhidas]
    if chave is not None:
        for lancamento_id in antecipadas:
            conn.execute(
                "INSERT INTO antecipacoes (id, lancamento_id, parcelamento_id) VALUES (%s, %s, %s)",
                (chave, lancamento_id, id),
            )
    return antecipadas


def _responder(url: str | None, antecipadas: list[UUID]) -> list[lancamentos.Lancamento]:
    with conectar(url) as conn:
        return sorted(
            lancamentos.ler_por_ids(conn, antecipadas), key=lambda parcela: parcela.parcela
        )


@router.post(
    "/parcelamentos/{id}/antecipacoes",
    response_model=list[lancamentos.Lancamento],
    operation_id="antecipar_parcelas",
)
def antecipar_parcelas(
    id: UUID, antecipacao: Antecipacao, usuario: UsuarioLogado, request: Request
) -> list[lancamentos.Lancamento]:
    """Paga adiantado as últimas K parcelas por pagar, no dia de hoje ou em outro, pelo valor
    informado (o desconto). Devolve as parcelas antecipadas. Repetir o pedido com o mesmo `id`
    devolve as parcelas já antecipadas, sem antecipar as seguintes (ticket 154)."""
    url = url_do_banco(request)
    antecipadas = em_transacao(
        url,
        cartoes.protegida(
            lambda conn: _antecipar(
                conn,
                id,
                antecipacao.parcelas,
                antecipacao.data,
                antecipacao.valor_total_centavos,
                usuario,
                antecipacao.id,
            )
        ),
    )
    return _responder(url, antecipadas)


@router.post(
    "/parcelamentos/{id}/quitacao",
    response_model=list[lancamentos.Lancamento],
    operation_id="quitar_parcelamento",
)
def quitar_parcelamento(
    id: UUID, quitacao: Quitacao, usuario: UsuarioLogado, request: Request
) -> list[lancamentos.Lancamento]:
    """Paga de uma vez todas as parcelas que faltam. Devolve as parcelas quitadas."""
    url = url_do_banco(request)
    quitadas = em_transacao(
        url,
        cartoes.protegida(
            lambda conn: _antecipar(
                conn, id, None, quitacao.data, quitacao.valor_total_centavos, usuario
            )
        ),
    )
    return _responder(url, quitadas)
