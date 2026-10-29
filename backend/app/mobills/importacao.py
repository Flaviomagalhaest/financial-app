"""O resultado da importação: o que seria gravado, cada compra de cartão uma vez só."""

from dataclasses import dataclass, field, replace
from datetime import date
from pathlib import Path

from app.mobills import conferencia, de_para, parcelas
from app.mobills import revisao as planilha
from app.mobills.conferencia import AjusteDeFatura
from app.mobills.cruzamento import Cruzamento, cruzar
from app.mobills.leitura import (
    LinhaDeFatura,
    LinhaDoGeral,
    ler_faturas,
    ler_geral,
    pastas_de_fatura,
)

# A fonte do lançamento importado (ticket 41): `lancamentos.fonte`, que no app fica `NULL`.
FONTE = "mobills"
TIPOS_DE_CONTA = ("corrente", "poupanca", "carteira")


@dataclass(frozen=True)
class Conta:
    """A conta única do Mobills, que o dono cadastra antes de importar (o export não a traz)."""

    nome: str
    tipo: str


@dataclass(frozen=True)
class Cartao:
    """Um cartão do cadastro, ligado a uma pasta de faturas. O arquivado tem os dias opcionais."""

    pasta: str
    nome: str
    arquivado: bool
    fechamento: int | None
    vencimento: int | None


@dataclass(frozen=True)
class Lancamento:
    tipo: str  # 'despesa' ou 'receita'
    situacao: str  # 'realizado' ou 'previsto'
    valor_centavos: int
    data: date  # no cartão, a data da compra
    mes: str  # em que conta: o mês da fatura no cartão, o da data no resto
    descricao: str
    categorias: list[str]
    tags: list[str]
    cartao: str | None  # o nome do cadastro; sem cartão, entra na conta
    parcela: tuple[int, int] | None
    pessoa: str | None = None  # sem pessoa é do conjunto
    fonte: str = FONTE


@dataclass
class Importacao:
    conta: Conta
    cartoes: list[Cartao]
    lancamentos: list[Lancamento] = field(default_factory=list)
    cruzamento: Cruzamento = field(default_factory=Cruzamento)
    parcelamentos: list[parcelas.Parcelamento] = field(default_factory=list)
    ajustes: list[AjusteDeFatura] = field(default_factory=list)
    # O que impede gravar: a planilha precisa de mais uma edição do dono.
    impedimentos: list[str] = field(default_factory=list)


def importar(geral: Path, faturas: Path, revisao: Path) -> Importacao:
    """Lê os exports e a planilha de revisão da rodada anterior (se houver), cruza e reescreve a
    planilha com as decisões do dono mantidas."""
    linhas_do_geral = ler_geral(geral)
    linhas_de_fatura = ler_faturas(faturas)
    pastas = pastas_de_fatura(faturas)
    decisoes = planilha.ler_decisoes(revisao)
    impedimentos: list[str] = []
    conta = _conta(decisoes, linhas_do_geral, impedimentos)
    cartoes = _cartoes(decisoes, pastas, impedimentos)
    nomes = {c.pasta: c.nome for c in cartoes}
    cruzamento = cruzar(linhas_do_geral, linhas_de_fatura, decisoes.provaveis)
    importacao = Importacao(conta, cartoes, cruzamento=cruzamento, impedimentos=impedimentos)
    importacao.lancamentos, importacao.ajustes = conferencia.separar_ajustes(
        _lancamentos(cruzamento, nomes)
    )
    contagem = de_para.contar(importacao.lancamentos)
    regras = _regras(decisoes, contagem, impedimentos)
    importacao.lancamentos = [de_para.aplicar(x, regras) for x in importacao.lancamentos]
    sem_categoria = sum(1 for x in importacao.lancamentos if not x.categorias)
    if sem_categoria:
        plural = "lançamento ficou" if sem_categoria == 1 else "lançamentos ficaram"
        impedimentos.append(f"De-para: {sem_categoria} {plural} sem categoria")

    # As parcelas vêm do geral: a sequência é conferida dentro do período dele.
    meses_do_geral = [x.mes for x in linhas_do_geral]
    ultimo_mes = max(meses_do_geral, default="")
    importacao.parcelamentos = parcelas.reagrupar(
        importacao.lancamentos, min(meses_do_geral, default=""), ultimo_mes
    )
    escolhidos = _cartao_dos_parcelamentos(importacao, decisoes)
    _parcelas_futuras_no_cartao(importacao, pastas)

    # A Conferência vai até a virada: o último mês com lançamento já pago no Mobills.
    ultimo_realizado = max(
        (x.mes for x in linhas_do_geral if _situacao(x.situacao) == "realizado"),
        default=ultimo_mes,
    )
    linhas_dos_meses = conferencia.meses(
        importacao.lancamentos,
        importacao.ajustes,
        cruzamento,
        min(meses_do_geral + [x.mes for x in linhas_de_fatura], default=""),
        ultimo_realizado,
    )
    linhas_das_faturas = conferencia.faturas(
        importacao.lancamentos,
        importacao.ajustes,
        {nomes[pasta]: lista for pasta, lista in pastas.items()},
    )
    planilha.escrever_planilha(
        revisao,
        {
            "Conta": planilha.aba_conta(conta),
            "Cartões": planilha.aba_cartoes(cartoes, pastas),
            "De-para": planilha.aba_de_para(contagem, regras),
            "Pares prováveis": planilha.aba_pares_provaveis(cruzamento),
            "Grupos ambíguos": planilha.aba_grupos_ambiguos(cruzamento),
            "Categoria diferente": planilha.aba_categoria_diferente(cruzamento),
            "Parcelas quebradas": planilha.aba_parcelas_quebradas(importacao.parcelamentos),
            "Parcelamentos sem cartão": planilha.aba_parcelamentos_sem_cartao(
                importacao.parcelamentos, escolhidos
            ),
            "Conferência": planilha.aba_conferencia(linhas_dos_meses, decisoes.mobills_por_mes),
            "Faturas": planilha.aba_faturas(linhas_das_faturas, decisoes.mobills_por_fatura),
        },
    )
    return importacao


def _lancamentos(cruzamento: Cruzamento, nomes: dict[str, str]) -> list[Lancamento]:
    """Cada compra de cartão uma vez só, com os nomes ainda do Mobills."""
    lancamentos = [_do_cartao(par.fatura, par.geral, nomes) for par in cruzamento.pares]
    lancamentos += [_so_da_fatura(linha, nomes) for linha in cruzamento.fatura_sem_par]
    lancamentos += [_do_geral(linha) for linha in cruzamento.geral_sem_par]
    for provavel in cruzamento.provaveis:
        if provavel.decisao is None:
            lancamentos.append(_so_da_fatura(provavel.fatura, nomes))
            lancamentos.append(_do_geral(provavel.geral))
    return lancamentos


def _conta(
    decisoes: planilha.Decisoes, geral: list[LinhaDoGeral], impedimentos: list[str]
) -> Conta:
    """Na primeira rodada, a proposta é o nome que o geral dá à conta (`Carteira`)."""
    if decisoes.conta is None:
        nome = next((x.conta for x in geral if x.conta), "Conta do Mobills")
        return Conta(nome=nome, tipo="corrente")
    nome, tipo = decisoes.conta
    if not nome:
        impedimentos.append("Conta: falta o nome")
    if tipo not in TIPOS_DE_CONTA:
        impedimentos.append(f"Conta: tipo {tipo!r} não é {', '.join(TIPOS_DE_CONTA)}")
    return Conta(nome=nome, tipo=tipo)


def _cartoes(
    decisoes: planilha.Decisoes, pastas: dict[str, list[str]], impedimentos: list[str]
) -> list[Cartao]:
    """Um cartão por pasta de faturas. Na primeira rodada, o nome é o da pasta e fica arquivado
    o cartão sem a fatura do último mês exportado."""
    ultimo_mes = max((meses[-1] for meses in pastas.values() if meses), default="")
    cartoes = []
    for pasta, meses in pastas.items():
        editado = decisoes.cartoes.get(pasta)
        if editado is None:
            arquivado = not meses or meses[-1] < ultimo_mes
            cartao = Cartao(pasta, pasta, arquivado, fechamento=None, vencimento=None)
        else:
            cartao = Cartao(pasta, **editado)
            # O dia que não é número fica de fora do cadastro; o impedimento abaixo o mostra.
            invalidos = [d for d in (cartao.fechamento, cartao.vencimento) if isinstance(d, str)]
            for dia in invalidos:
                impedimentos.append(f"Cartões: {cartao.nome!r} tem o dia {dia!r}, fora de 1 a 31")
            if invalidos:
                cartao = replace(
                    cartao,
                    fechamento=None if isinstance(cartao.fechamento, str) else cartao.fechamento,
                    vencimento=None if isinstance(cartao.vencimento, str) else cartao.vencimento,
                )
        if not cartao.nome:
            impedimentos.append(f"Cartões: a pasta {pasta!r} está sem o nome do cartão")
        for dia in (cartao.fechamento, cartao.vencimento):
            if dia is not None and not (isinstance(dia, int) and 1 <= dia <= 31):
                impedimentos.append(f"Cartões: {cartao.nome!r} tem o dia {dia!r}, fora de 1 a 31")
        if not cartao.arquivado and (cartao.fechamento is None or cartao.vencimento is None):
            impedimentos.append(
                f"Cartões: {cartao.nome!r} está ativo e sem os dias de fechamento e vencimento"
            )
        cartoes.append(cartao)
    nomes = [c.nome for c in cartoes]
    for repetido in sorted({n for n in nomes if nomes.count(n) > 1}):
        impedimentos.append(f"Cartões: duas pastas ligadas ao mesmo cartão {repetido!r}")
    return cartoes


def _regras(
    decisoes: planilha.Decisoes, contagem, impedimentos: list[str]
) -> dict[de_para.Chave, de_para.Regra]:
    """A regra de cada nome em uso: a do dono, se válida, ou a proposta."""
    regras = {}
    for chave in sorted(contagem):
        regra = de_para.proposta(chave)
        editada = decisoes.de_para.get(chave)
        if editada is not None:
            papel, nome = editada
            if papel not in de_para.PAPEIS:
                impedimentos.append(f"De-para: {chave[2]!r} tem papel {papel!r}, que não existe")
            elif not nome and papel != "descartar":
                impedimentos.append(f"De-para: {chave[2]!r} está sem o nome no app")
            else:
                regra = de_para.Regra(papel, nome)
        regras[chave] = regra
    return regras


def _cartao_dos_parcelamentos(importacao: Importacao, decisoes: planilha.Decisoes) -> dict:
    """Põe no cartão que o dono escolheu as parcelas do parcelamento que nenhuma fatura trouxe.
    Devolve a escolha de cada parcelamento sem cartão, para a planilha."""
    nomes = {c.nome for c in importacao.cartoes}
    trocados = {}
    escolhidos = {}
    for parcelamento in importacao.parcelamentos:
        if parcelamento.cartao is not None:
            continue
        chave = planilha.chave_do_parcelamento(parcelamento)
        cartao = decisoes.cartao_dos_parcelamentos.get(chave)
        if not cartao:
            continue
        escolhidos[chave] = cartao
        if cartao not in nomes:
            importacao.impedimentos.append(
                f"Parcelamentos sem cartão: {parcelamento.descricao!r} tem o cartão {cartao!r},"
                " que não está na aba Cartões"
            )
            continue
        novas = [replace(x, cartao=cartao) for x in parcelamento.lancamentos]
        trocados.update({id(velha): nova for velha, nova in zip(parcelamento.lancamentos, novas)})
        parcelamento.lancamentos = novas
    importacao.lancamentos = [trocados.get(id(x), x) for x in importacao.lancamentos]
    return escolhidos


def _parcelas_futuras_no_cartao(importacao: Importacao, pastas: dict[str, list[str]]) -> None:
    """A parcela do geral que ainda não tem fatura (depois da última fatura do cartão) herda o
    cartão e a data da compra das parcelas já casadas do mesmo parcelamento."""
    ultima_fatura = {c.nome: max(pastas[c.pasta], default="") for c in importacao.cartoes}
    trocados = {}
    for parcelamento in importacao.parcelamentos:
        casada = next((x for x in parcelamento.lancamentos if x.cartao), None)
        if casada is None:
            continue
        novas = []
        for parcela in parcelamento.lancamentos:
            if parcela.cartao is None and parcela.mes > ultima_fatura.get(casada.cartao, ""):
                nova = replace(parcela, cartao=casada.cartao, data=casada.data)
                trocados[id(parcela)] = nova
                parcela = nova
            novas.append(parcela)
        parcelamento.lancamentos = novas
    importacao.lancamentos = [trocados.get(id(x), x) for x in importacao.lancamentos]


def _tipo(valor_no_geral: int) -> str:
    return "despesa" if valor_no_geral < 0 else "receita"


def _situacao(situacao_no_mobills: str) -> str:
    return "previsto" if situacao_no_mobills.casefold() == "pendente" else "realizado"


def _do_geral(linha: LinhaDoGeral) -> Lancamento:
    return Lancamento(
        tipo=_tipo(linha.valor_centavos),
        situacao=_situacao(linha.situacao),
        valor_centavos=abs(linha.valor_centavos),
        data=linha.data,
        mes=linha.mes,
        descricao=linha.descricao,
        categorias=[linha.categoria],
        tags=list(linha.tags),
        cartao=None,
        parcela=linha.parcela,
    )


def _do_cartao(fatura: LinhaDeFatura, par: LinhaDoGeral, nomes: dict[str, str]) -> Lancamento:
    return Lancamento(
        tipo=_tipo(par.valor_centavos),
        situacao=_situacao(par.situacao),
        valor_centavos=abs(par.valor_centavos),
        data=fatura.data,
        mes=fatura.mes,
        descricao=par.descricao,
        categorias=[par.categoria],
        tags=list(par.tags),
        cartao=nomes[fatura.pasta],
        parcela=par.parcela,
    )


def _so_da_fatura(fatura: LinhaDeFatura, nomes: dict[str, str]) -> Lancamento:
    """A linha de fatura sem par entra só com o que a fatura tem: realizada e sem tags."""
    return Lancamento(
        tipo="despesa" if fatura.valor_centavos > 0 else "receita",
        situacao="realizado",
        valor_centavos=abs(fatura.valor_centavos),
        data=fatura.data,
        mes=fatura.mes,
        descricao=fatura.descricao,
        categorias=[fatura.categoria],
        tags=[],
        cartao=nomes[fatura.pasta],
        parcela=None,
    )
