"""Importador do Mobills (ADR 0007, ticket 18): XLSX fictícios entram, saem os lançamentos que a
importação grava e a planilha de revisão."""

from datetime import date
from pathlib import Path

import pytest

from app.mobills import AjusteDeFatura, Cartao, Conta, importar
from app.mobills.__main__ import main
from app.mobills.leitura import ArquivoInvalido
from tests.mobills_ficticio import (
    editar_aba,
    escrever_fatura,
    escrever_fatura_pdf,
    escrever_geral,
    ler_aba,
    linha,
)


@pytest.fixture
def pastas(tmp_path: Path) -> tuple[Path, Path, Path]:
    return tmp_path / "geral", tmp_path / "faturas", tmp_path / "revisao.xlsx"


def test_compra_de_cartao_casada_entra_uma_vez_com_a_data_e_o_cartao_da_fatura(pastas):
    geral, faturas, revisao = pastas
    escrever_geral(
        geral,
        "2025-2026.xlsx",
        [
            linha("10/03/2026", "Mercado", -120.35, "Alimentação", tags="novo ap"),
            linha("31/03/2026", "Restaurante", -1080.00, "Alimentação"),
            linha("05/03/2026", "Salário", 5000.00, "Salário"),
        ],
    )
    escrever_fatura(
        faturas, "Nubank", "202603", [("14/02/2026", "Restaurante", "Alimentação", 1080.0)]
    )

    importacao = importar(geral, faturas, revisao)

    restaurante = [x for x in importacao.lancamentos if x.descricao == "Restaurante"]
    assert len(restaurante) == 1
    compra = restaurante[0]
    assert compra.cartao == "Nubank"
    assert compra.data == date(2026, 2, 14)
    assert compra.mes == "2026-03"
    assert compra.tipo == "despesa"
    assert compra.valor_centavos == 108000
    assert compra.situacao == "realizado"
    assert compra.categorias == ["Alimentação"]

    mercado = next(x for x in importacao.lancamentos if x.descricao == "Mercado")
    assert mercado.cartao is None
    assert mercado.data == date(2026, 3, 10)
    assert mercado.tags == ["novo ap"]
    salario = next(x for x in importacao.lancamentos if x.descricao == "Salário")
    assert (salario.tipo, salario.valor_centavos) == ("receita", 500000)
    assert len(importacao.lancamentos) == 3
    assert all(x.fonte == "mobills" and x.pessoa is None for x in importacao.lancamentos)


def test_linhas_iguais_casam_na_ordem_e_a_sobra_da_fatura_entra_so_com_o_que_a_fatura_tem(pastas):
    geral, faturas, revisao = pastas
    escrever_geral(
        geral,
        "geral.xlsx",
        [
            linha("30/09/2025", "Padaria (1/2)", -10.00, "Alimentação", tags="praia"),
            linha("30/09/2025", "Padaria (1/2)", -10.00, "Alimentação", tags="praia"),
        ],
    )
    escrever_fatura(
        faturas,
        "Cartao A",
        "202509",
        [
            ("20/09/2025", "Padaria", "Alimentação", 10.0),
            ("02/09/2025", "Padaria", "Alimentação", 10.0),
            ("11/09/2025", "PADARIA", "Alimentação", 10.0),
        ],
    )

    importacao = importar(geral, faturas, revisao)

    # As 2/2 que o export não trouxe são geradas como previstas; aqui interessam as importadas.
    padarias = sorted(
        (x for x in importacao.lancamentos if x.situacao == "realizado"), key=lambda x: x.data
    )
    assert [x.data.day for x in padarias] == [2, 11, 20]
    assert [x.tags for x in padarias] == [["praia"], ["praia"], []]
    assert [x.parcela for x in padarias] == [(1, 2), (1, 2), None]
    assert {x.cartao for x in padarias} == {"Cartao A"}
    sobra = padarias[2]
    assert (sobra.situacao, sobra.tipo, sobra.valor_centavos) == ("realizado", "despesa", 1000)
    assert sobra.mes == "2025-09"


def test_par_que_so_difere_na_categoria_casa_com_a_do_geral_e_vai_para_a_planilha(pastas):
    geral, faturas, revisao = pastas
    escrever_geral(geral, "geral.xlsx", [linha("31/05/2024", "Farmácia", -45.90, "Saúde")])
    escrever_fatura(faturas, "Cartao A", "202405", [("03/05/2024", "Farmácia", "Outros", 45.90)])

    importacao = importar(geral, faturas, revisao)

    [compra] = importacao.lancamentos
    assert (compra.cartao, compra.data, compra.categorias) == (
        "Cartao A",
        date(2024, 5, 3),
        ["Saúde"],
    )
    assert ler_aba(revisao, "Categoria diferente") == [
        {
            "Pasta do cartão": "Cartao A",
            "Mês": "2024-05",
            "Data da compra": "03/05/2024",
            "Descrição": "Farmácia",
            "Valor": 45.90,
            "Categoria na fatura": "Outros",
            "Categoria no geral (vale esta)": "Saúde",
        }
    ]


def test_par_provavel_entra_separado_ate_o_dono_confirmar_na_planilha(pastas):
    geral, faturas, revisao = pastas
    escrever_geral(
        geral,
        "geral.xlsx",
        [
            linha("31/07/2023", "Posto Shell", -200.00, "Transporte", tags="praia"),
            linha("31/07/2023", "Uber", -30.00, "Transporte"),
        ],
    )
    escrever_fatura(
        faturas,
        "Cartao A",
        "202307",
        [
            ("08/07/2023", "SHELL BOX 123", "Carro", 200.00),
            ("09/07/2023", "Uber trip", "Transporte", 30.00),
            ("10/07/2023", "Uber trip", "Transporte", 30.00),
        ],
    )

    primeira = importar(geral, faturas, revisao)

    assert len(primeira.lancamentos) == 5
    assert ler_aba(revisao, "Pares prováveis") == [
        {
            "Pasta do cartão": "Cartao A",
            "Mês": "2023-07",
            "Data da compra": "08/07/2023",
            "Descrição na fatura": "SHELL BOX 123",
            "Categoria na fatura": "Carro",
            "Valor": 200.00,
            "Data no geral": "31/07/2023",
            "Descrição no geral": "Posto Shell",
            "Categoria no geral": "Transporte",
            "Tags no geral": "praia",
            "Decisão (juntar ou separar)": None,
        }
    ]

    editar_aba(
        revisao,
        "Pares prováveis",
        "Descrição na fatura",
        "SHELL BOX 123",
        "Decisão (juntar ou separar)",
        "juntar",
    )
    segunda = importar(geral, faturas, revisao)

    assert len(segunda.lancamentos) == 4
    posto = next(x for x in segunda.lancamentos if x.valor_centavos == 20000)
    assert (posto.cartao, posto.data, posto.descricao) == (
        "Cartao A",
        date(2023, 7, 8),
        "Posto Shell",
    )
    assert (posto.categorias, posto.tags) == (["Transporte"], ["praia"])
    assert ler_aba(revisao, "Pares prováveis")[0]["Decisão (juntar ou separar)"] == "juntar"


def test_grupo_igual_com_tags_diferentes_no_geral_casa_na_ordem_e_vai_para_a_revisao(pastas):
    geral, faturas, revisao = pastas
    escrever_geral(
        geral,
        "geral.xlsx",
        [
            linha("31/01/2025", "iFood", -50.00, "Alimentação", tags="praia"),
            linha("31/01/2025", "iFood", -50.00, "Alimentação", situacao="Pendente"),
            linha("31/01/2025", "Cinema", -40.00, "Lazer"),
            linha("31/01/2025", "Cinema", -40.00, "Lazer"),
        ],
    )
    escrever_fatura(
        faturas,
        "Cartao A",
        "202501",
        [
            ("15/01/2025", "iFood", "Alimentação", 50.00),
            ("04/01/2025", "iFood", "Alimentação", 50.00),
            ("06/01/2025", "Cinema", "Lazer", 40.00),
            ("07/01/2025", "Cinema", "Lazer", 40.00),
        ],
    )

    importacao = importar(geral, faturas, revisao)

    ifood = sorted(
        (x for x in importacao.lancamentos if x.descricao == "iFood"), key=lambda x: x.data
    )
    assert [(x.data.day, x.tags, x.situacao) for x in ifood] == [
        (4, ["praia"], "realizado"),
        (15, [], "previsto"),
    ]
    assert ler_aba(revisao, "Grupos ambíguos") == [
        {
            "Pasta do cartão": "Cartao A",
            "Mês": "2025-01",
            "Descrição": "iFood",
            "Valor": 50.00,
            "Categoria": "Alimentação",
            "Data da compra": "04/01/2025",
            "Arquivo do geral": "geral.xlsx",
            "Linha no arquivo": 2,
            "Tags no geral": "praia",
            "Situação no geral": "Paga",
            "Resultado": "par",
            "Decisão (descartar ou manter)": None,
        },
        {
            "Pasta do cartão": "Cartao A",
            "Mês": "2025-01",
            "Descrição": "iFood",
            "Valor": 50.00,
            "Categoria": "Alimentação",
            "Data da compra": "15/01/2025",
            "Arquivo do geral": "geral.xlsx",
            "Linha no arquivo": 3,
            "Tags no geral": None,
            "Situação no geral": "Pendente",
            "Resultado": "par",
            "Decisão (descartar ou manter)": None,
        },
    ]


def test_no_grupo_ambiguo_a_fatura_casa_com_a_paga_e_a_pendente_duplicada_e_descartada(pastas):
    geral, faturas, revisao = pastas
    escrever_geral(
        geral,
        "geral.xlsx",
        [
            # A previsão de recorrência do Mobills vem antes da paga no export.
            linha("30/09/2024", "Youtube", -24.90, "Assinaturas", situacao="Pendente"),
            linha("27/09/2024", "Youtube", -24.90, "Assinaturas"),
            # A fatura repete a compra na mesma data: uma compra só.
            linha("30/09/2024", "Remédio", -138.74, "Saúde"),
            linha("30/09/2024", "Remédio", -138.74, "Saúde", situacao="Pendente"),
        ],
    )
    escrever_fatura(
        faturas,
        "Cartao A",
        "202409",
        [
            ("01/09/2024", "Youtube", "Assinaturas", 24.90),
            ("26/08/2024", "Remédio", "Saúde", 138.74),
            ("26/08/2024", "Remédio", "Saúde", 138.74),
        ],
    )

    importacao = importar(geral, faturas, revisao)

    assert sorted(
        ((x.descricao, x.cartao, x.situacao, x.data) for x in importacao.lancamentos), key=repr
    ) == [
        ("Remédio", "Cartao A", "realizado", date(2024, 8, 26)),
        ("Youtube", "Cartao A", "realizado", date(2024, 9, 1)),
    ]
    assert [
        (x["Descrição"], x["Data da compra"], x["Situação no geral"], x["Resultado"])
        for x in ler_aba(revisao, "Grupos ambíguos")
    ] == [
        ("Remédio", "26/08/2024", "Paga", "par"),
        ("Remédio", "26/08/2024", "Pendente", "descartada"),
        ("Youtube", "01/09/2024", "Paga", "par"),
        ("Youtube", None, "Pendente", "descartada"),
    ]

    # Duas compras de verdade: o dono manda manter, e a decisão fica na rodada seguinte.
    editar_aba(
        revisao,
        "Grupos ambíguos",
        "Descrição",
        "Remédio",
        "Decisão (descartar ou manter)",
        "manter",
    )
    importar(geral, faturas, revisao)
    importacao = importar(geral, faturas, revisao)

    remedios = [x for x in importacao.lancamentos if x.descricao == "Remédio"]
    assert sorted((x.cartao, x.situacao) for x in remedios) == [
        ("Cartao A", "previsto"),
        ("Cartao A", "realizado"),
    ]
    assert [
        (x["Situação no geral"], x["Resultado"], x["Decisão (descartar ou manter)"])
        for x in ler_aba(revisao, "Grupos ambíguos")
        if x["Descrição"] == "Remédio"
    ] == [("Paga", "par", "manter"), ("Pendente", "par", "manter")]


def test_cadastro_da_conta_e_dos_cartoes_nasce_proposto_e_o_dono_liga_cada_pasta(pastas):
    geral, faturas, revisao = pastas
    escrever_geral(geral, "geral.xlsx", [linha("31/08/2026", "Livro", -60.00, "Educação")])
    escrever_fatura(
        faturas, "Cartao Antigo", "202607", [("02/07/2026", "Café", "Alimentação", 9.0)]
    )
    escrever_fatura(faturas, "Cartao Novo", "202608", [("12/08/2026", "Livro", "Educação", 60.0)])

    primeira = importar(geral, faturas, revisao)

    assert ler_aba(revisao, "Conta") == [
        {"Nome": "Carteira", "Tipo (corrente, poupanca ou carteira)": "corrente"}
    ]
    assert ler_aba(revisao, "Cartões") == [
        {
            "Pasta": "Cartao Antigo",
            "Cartão": "Cartao Antigo",
            "Primeira fatura": "2026-07",
            "Última fatura": "2026-07",
            "Arquivado (sim ou não)": "sim",
            "Dia do fechamento": None,
            "Dia do vencimento": None,
        },
        {
            "Pasta": "Cartao Novo",
            "Cartão": "Cartao Novo",
            "Primeira fatura": "2026-08",
            "Última fatura": "2026-08",
            "Arquivado (sim ou não)": "não",
            "Dia do fechamento": None,
            "Dia do vencimento": None,
        },
    ]
    assert primeira.impedimentos == [
        "Cartões: 'Cartao Novo' está ativo e sem os dias de fechamento e vencimento"
    ]

    editar_aba(revisao, "Conta", "Nome", "Carteira", "Nome", "Conta do casal")
    editar_aba(revisao, "Cartões", "Pasta", "Cartao Novo", "Cartão", "Visa do casal")
    editar_aba(revisao, "Cartões", "Pasta", "Cartao Novo", "Dia do fechamento", 25)
    editar_aba(revisao, "Cartões", "Pasta", "Cartao Novo", "Dia do vencimento", 5)
    segunda = importar(geral, faturas, revisao)

    assert segunda.impedimentos == []
    assert segunda.conta == Conta(nome="Conta do casal", tipo="corrente")
    assert segunda.cartoes == [
        Cartao(
            pasta="Cartao Antigo",
            nome="Cartao Antigo",
            arquivado=True,
            fechamento=None,
            vencimento=None,
        ),
        Cartao(
            pasta="Cartao Novo", nome="Visa do casal", arquivado=False, fechamento=25, vencimento=5
        ),
    ]
    livro = next(x for x in segunda.lancamentos if x.descricao == "Livro")
    assert livro.cartao == "Visa do casal"
    assert ler_aba(revisao, "Cartões")[1]["Cartão"] == "Visa do casal"


def de_para(revisao: Path) -> dict[tuple, dict]:
    return {
        (x["Tipo"], x["No Mobills"], x["Nome no Mobills"]): {
            "Lançamentos": x["Lançamentos"],
            "Papel": x["Papel (categoria, tag, pessoa ou descartar)"],
            "Nome no app": x["Nome no app"],
        }
        for x in ler_aba(revisao, "De-para")
    }


def test_de_para_propoe_o_mesmo_papel_e_aplica_o_que_o_dono_editou(pastas, monkeypatch):
    monkeypatch.setenv("PESSOAS", '{"flavio": "Flávio", "fulano": "Fulano"}')
    geral, faturas, revisao = pastas
    escrever_geral(
        geral,
        "geral.xlsx",
        [
            linha("02/01/2026", "Pousada", -900.00, "Hospedagem", tags="ilhabela"),
            linha("03/01/2026", "Jantar", -150.00, "Alimentação", tags="viagem"),
            linha("04/01/2026", "Sofá", -2000.00, "Casa", tags="novo ap"),
            linha("05/01/2026", "Mercado", -300.00, "Alimentação", tags="fulano"),
            linha("06/01/2026", "Reembolso", 150.00, "Alimentação"),
        ],
    )
    escrever_fatura(faturas, "Cartao A", "202601", [])

    importar(geral, faturas, revisao)

    papel = "Papel (categoria, tag, pessoa ou descartar)"
    assert de_para(revisao) == {
        ("despesa", "Categoria", "Alimentação"): {
            "Lançamentos": 2,
            "Papel": "categoria",
            "Nome no app": "Alimentação",
        },
        ("despesa", "Categoria", "Casa"): {
            "Lançamentos": 1,
            "Papel": "categoria",
            "Nome no app": "Casa",
        },
        ("despesa", "Categoria", "Hospedagem"): {
            "Lançamentos": 1,
            "Papel": "categoria",
            "Nome no app": "Hospedagem",
        },
        ("despesa", "Tag", "fulano"): {"Lançamentos": 1, "Papel": "tag", "Nome no app": "fulano"},
        ("despesa", "Tag", "ilhabela"): {
            "Lançamentos": 1,
            "Papel": "categoria",
            "Nome no app": "Viagem",
        },
        ("despesa", "Tag", "novo ap"): {"Lançamentos": 1, "Papel": "tag", "Nome no app": "novo ap"},
        ("despesa", "Tag", "viagem"): {
            "Lançamentos": 1,
            "Papel": "categoria",
            "Nome no app": "Viagem",
        },
        ("receita", "Categoria", "Alimentação"): {
            "Lançamentos": 1,
            "Papel": "categoria",
            "Nome no app": "Alimentação",
        },
    }

    editar_aba(revisao, "De-para", "Nome no Mobills", "fulano", papel, "pessoa")
    editar_aba(revisao, "De-para", "Nome no Mobills", "fulano", "Nome no app", "Fulano")
    editar_aba(revisao, "De-para", "Nome no Mobills", "Casa", papel, "tag")
    editar_aba(revisao, "De-para", "Nome no Mobills", "Hospedagem", papel, "descartar")
    importacao = importar(geral, faturas, revisao)

    por_descricao = {x.descricao: x for x in importacao.lancamentos}
    assert (por_descricao["Pousada"].categorias, por_descricao["Pousada"].tags) == (["Viagem"], [])
    assert por_descricao["Jantar"].categorias == ["Alimentação", "Viagem"]
    assert (por_descricao["Sofá"].categorias, por_descricao["Sofá"].tags) == (
        [],
        ["Casa", "novo ap"],
    )
    assert (por_descricao["Mercado"].pessoa, por_descricao["Mercado"].tags) == ("Fulano", [])
    assert por_descricao["Reembolso"].categorias == ["Alimentação"]
    assert [x for x in importacao.impedimentos if x.startswith("De-para")] == [
        "De-para: 1 lançamento ficou sem categoria"
    ]
    assert de_para(revisao)[("despesa", "Tag", "fulano")]["Papel"] == "pessoa"

    # A pessoa precisa ser uma das duas da configuração PESSOAS.
    editar_aba(revisao, "De-para", "Nome no Mobills", "fulano", "Nome no app", "Beltrano")
    assert (
        "De-para: a pessoa 'Beltrano' não é do casal (a configuração PESSOAS tem Flávio,"
        " Fulano)" in importar(geral, faturas, revisao).impedimentos
    )


def test_parcelas_viram_parcelamentos_e_a_sequencia_quebrada_vai_para_a_revisao(pastas):
    geral, faturas, revisao = pastas
    escrever_geral(
        geral,
        "geral.xlsx",
        [
            # Começou antes do histórico: a 4/6 no primeiro mês não é quebra.
            linha("28/02/2019", "Geladeira (4/6)", -500.00, "Casa"),
            linha("31/03/2019", "Geladeira (5/6)", -500.01, "Casa"),
            linha("30/04/2019", "Geladeira (6/6)", -500.00, "Casa"),
            # Falta a 2/3 em abril.
            linha("31/03/2019", "Curso (1/3)", -100.00, "Educação"),
            linha("31/05/2019", "Curso (3/3)", -100.00, "Educação"),
            # Segue depois do último mês do export: não é quebra.
            linha("30/04/2019", "Celular (1/10)", -200.00, "Eletrônicos"),
            linha("31/05/2019", "Celular (2/10)", -200.00, "Eletrônicos"),
        ],
    )
    escrever_fatura(
        faturas,
        "Cartao A",
        "201903",
        [("10/02/2019", "Geladeira", "Casa", 500.01), ("20/03/2019", "Curso", "Educação", 100.0)],
    )

    importacao = importar(geral, faturas, revisao)

    assert [
        (p.descricao, [x.parcela for x in p.lancamentos]) for p in importacao.parcelamentos
    ] == [
        ("Celular", [(n, 10) for n in range(1, 11)]),
        ("Curso", [(1, 3)]),
        ("Curso", [(3, 3)]),
        ("Geladeira", [(4, 6), (5, 6), (6, 6)]),
    ]
    assert ler_aba(revisao, "Parcelas quebradas") == [
        {
            "Descrição": "Curso",
            "Valor": 100.00,
            "Parcelas": "1 de 3",
            "Primeiro mês": "2019-03",
            "Último mês": "2019-03",
            "Cartão": "Cartao A",
            "Motivo": "falta a parcela 2 depois de 2019-03",
            "Decisão (avulsas, parcelamento ou descartar duplicada)": None,
        },
        {
            "Descrição": "Curso",
            "Valor": 100.00,
            "Parcelas": "3 de 3",
            "Primeiro mês": "2019-05",
            "Último mês": "2019-05",
            "Cartão": None,
            "Motivo": "falta a parcela 2 antes de 2019-05",
            "Decisão (avulsas, parcelamento ou descartar duplicada)": None,
        },
    ]
    sem_cartao = ler_aba(revisao, "Parcelamentos sem cartão")
    assert [(x["Descrição"], x["Parcelas"]) for x in sem_cartao] == [
        ("Celular", "1 a 10 de 10"),
        ("Curso", "3 de 3"),
    ]

    editar_aba(
        revisao, "Parcelamentos sem cartão", "Descrição", "Celular", "Cartão (escolha)", "Cartao A"
    )
    importacao = importar(geral, faturas, revisao)

    celular = next(p for p in importacao.parcelamentos if p.descricao == "Celular")
    assert {x.cartao for x in celular.lancamentos} == {"Cartao A"}
    assert {x.cartao for x in importacao.lancamentos if x.descricao == "Celular"} == {"Cartao A"}
    assert ler_aba(revisao, "Parcelamentos sem cartão")[0]["Cartão (escolha)"] == "Cartao A"


def test_conferencia_mes_a_mes_e_faturas_com_a_coluna_do_mobills_mantida(pastas):
    geral, faturas, revisao = pastas
    escrever_geral(
        geral,
        "geral.xlsx",
        [
            linha("05/01/2024", "Salário", 3000.00, "Salário"),
            linha("31/01/2024", "Mercado", -250.00, "Alimentação"),
            linha("31/01/2024", "Reajuste", -0.02, "Reajuste de fatura"),
            linha("10/01/2024", "Aluguel", -1500.00, "Casa", situacao="Pendente"),
            linha("31/03/2024", "Padaria", -20.00, "Alimentação"),
        ],
    )
    escrever_fatura(
        faturas,
        "Cartao A",
        "202401",
        [
            ("03/01/2024", "Mercado", "Alimentação", 250.00),
            ("29/01/2024", "Reajuste", "Reajuste de fatura", 0.02),
            ("15/01/2024", "Esquecido", "Outros", 35.50),
            ("16/01/2024", "Estorno loja", "Outros", -10.00),
        ],
    )
    escrever_fatura(faturas, "Cartao A", "202402", [])

    importacao = importar(geral, faturas, revisao)

    assert not any(x.descricao == "Reajuste" for x in importacao.lancamentos)
    assert importacao.ajustes == [
        AjusteDeFatura(cartao="Cartao A", mes="2024-01", valor_centavos=2)
    ]
    conferencia = ler_aba(revisao, "Conferência")
    assert [x["Mês"] for x in conferencia] == ["2024-01", "2024-02", "2024-03"]
    janeiro = conferencia[0]
    assert janeiro == {
        "Mês": "2024-01",
        "Receitas": 3010.00,
        "Despesas": 285.50,
        "Ajustes de fatura": 0.02,
        "Resultado": 2724.48,
        "Mobills": None,
        "Diferença": None,
        "Por quê": "2 linhas de fatura sem par (-25,50); 1 pendente avulso descartado (1.500,00)",
    }
    assert conferencia[1]["Resultado"] == 0
    assert conferencia[2]["Despesas"] == 20.00
    assert ler_aba(revisao, "Faturas") == [
        {
            "Cartão": "Cartao A",
            "Mês": "2024-01",
            "Compras": 275.50,
            "Ajuste de fatura": 0.02,
            "Total": 275.52,
            "Mobills": None,
            "Diferença": None,
            "Por quê": None,
        },
        {
            "Cartão": "Cartao A",
            "Mês": "2024-02",
            "Compras": 0,
            "Ajuste de fatura": 0,
            "Total": 0,
            "Mobills": None,
            "Diferença": None,
            "Por quê": None,
        },
    ]

    editar_aba(revisao, "Conferência", "Mês", "2024-01", "Mobills", 2749.98)
    editar_aba(revisao, "Faturas", "Mês", "2024-01", "Mobills", 250.02)
    importar(geral, faturas, revisao)

    janeiro = ler_aba(revisao, "Conferência")[0]
    assert (janeiro["Mobills"], janeiro["Diferença"]) == (2749.98, -25.50)
    fatura = ler_aba(revisao, "Faturas")[0]
    assert (fatura["Mobills"], fatura["Diferença"]) == (250.02, 25.50)


def test_grupo_com_dois_cartoes_casa_pela_data_da_compra_e_cada_linha_diz_o_seu_cartao(pastas):
    geral, faturas, revisao = pastas
    escrever_geral(
        geral,
        "geral.xlsx",
        [
            linha("31/10/2025", "Amazon", -99.90, "Compras", tags="praia"),
            linha("31/10/2025", "Amazon", -99.90, "Compras"),
        ],
    )
    escrever_fatura(faturas, "Cartao A", "202510", [("20/10/2025", "Amazon", "Compras", 99.90)])
    escrever_fatura(faturas, "Cartao B", "202510", [("05/10/2025", "Amazon", "Compras", 99.90)])

    importacao = importar(geral, faturas, revisao)

    por_cartao = {x.cartao: x for x in importacao.lancamentos}
    assert (por_cartao["Cartao B"].data.day, por_cartao["Cartao B"].tags) == (5, ["praia"])
    assert (por_cartao["Cartao A"].data.day, por_cartao["Cartao A"].tags) == (20, [])
    ambiguos = ler_aba(revisao, "Grupos ambíguos")
    assert [(x["Pasta do cartão"], x["Data da compra"]) for x in ambiguos] == [
        ("Cartao B", "05/10/2025"),
        ("Cartao A", "20/10/2025"),
    ]


def test_conferencia_vai_ate_o_ultimo_mes_pago_e_explica_o_reajuste_sem_par(pastas):
    geral, faturas, revisao = pastas
    escrever_geral(
        geral,
        "geral.xlsx",
        [
            linha("31/05/2026", "Mercado", -100.00, "Alimentação"),
            linha("10/06/2026", "Luz", -90.00, "Casa", situacao="Pendente"),
            linha("10/09/2026", "Luz", -90.00, "Casa", situacao="Pendente"),
        ],
    )
    escrever_fatura(
        faturas,
        "Cartao A",
        "202605",
        [
            ("02/05/2026", "Mercado", "Alimentação", 100.00),
            ("30/05/2026", "Reajuste", "Reajuste de fatura", 0.03),
        ],
    )

    importar(geral, faturas, revisao)

    conferencia = ler_aba(revisao, "Conferência")
    assert [x["Mês"] for x in conferencia] == ["2026-05"]
    assert conferencia[0]["Ajustes de fatura"] == 0.03
    assert conferencia[0]["Por quê"] == "1 linha de fatura sem par (-0,03)"


def test_parcela_repetida_no_mes_e_quebra_e_a_futura_herda_o_cartao_e_a_data_da_compra(pastas):
    geral, faturas, revisao = pastas
    escrever_geral(
        geral,
        "geral.xlsx",
        [
            linha("31/07/2026", "Sofá (1/3)", -400.00, "Casa"),
            linha("31/08/2026", "Sofá (2/3)", -400.00, "Casa", situacao="Pendente"),
            linha("30/09/2026", "Sofá (3/3)", -400.00, "Casa", situacao="Pendente"),
            linha("31/07/2026", "Curso (2/5)", -50.00, "Educação"),
            linha("31/07/2026", "Curso (2/5)", -50.00, "Educação"),
        ],
    )
    escrever_fatura(faturas, "Cartao A", "202607", [("14/07/2026", "Sofá", "Casa", 400.00)])

    importacao = importar(geral, faturas, revisao)

    sofa = next(p for p in importacao.parcelamentos if p.descricao == "Sofá")
    assert [(x.cartao, x.data, x.mes) for x in sofa.lancamentos] == [
        ("Cartao A", date(2026, 7, 14), "2026-07"),
        ("Cartao A", date(2026, 7, 14), "2026-08"),
        ("Cartao A", date(2026, 7, 14), "2026-09"),
    ]
    assert [x["Mês"] for x in ler_aba(revisao, "Faturas")] == ["2026-07", "2026-08", "2026-09"]
    assert [x["Motivo"] for x in ler_aba(revisao, "Parcelas quebradas")] == [
        "falta a parcela 3 depois de 2026-07; duas parcelas 2 de 5 em 2026-07",
        "falta a parcela 3 depois de 2026-07; duas parcelas 2 de 5 em 2026-07",
    ]


def test_planilha_editada_com_erro_vira_impedimento_e_nao_some(pastas):
    geral, faturas, revisao = pastas
    escrever_geral(geral, "geral.xlsx", [linha("31/03/2026", "Mercado", -10.00, "Alimentação")])
    escrever_fatura(faturas, "Cartao A", "202603", [])
    escrever_fatura(faturas, "Cartao B", "202603", [])
    importar(geral, faturas, revisao)
    papel = "Papel (categoria, tag, pessoa ou descartar)"
    editar_aba(
        revisao, "Conta", "Nome", "Carteira", "Tipo (corrente, poupanca ou carteira)", "banco"
    )
    editar_aba(revisao, "Cartões", "Pasta", "Cartao A", "Dia do fechamento", "dia 5")
    editar_aba(revisao, "Cartões", "Pasta", "Cartao A", "Dia do vencimento", 12)
    editar_aba(revisao, "Cartões", "Pasta", "Cartao B", "Cartão", "Cartao A")
    editar_aba(revisao, "Cartões", "Pasta", "Cartao B", "Arquivado (sim ou não)", "sim")
    editar_aba(revisao, "De-para", "Nome no Mobills", "Alimentação", papel, "rótulo")
    editar_aba(revisao, "Conferência", "Mês", "2026-03", "Mobills", "-1.234,56")

    importacao = importar(geral, faturas, revisao)

    assert importacao.impedimentos == [
        "Conta: tipo 'banco' não é corrente, poupanca, carteira",
        "Cartões: 'Cartao A' tem o dia 'dia 5', fora de 1 a 31",
        "Cartões: 'Cartao A' está ativo e sem os dias de fechamento e vencimento",
        "Cartões: duas pastas ligadas ao mesmo cartão 'Cartao A'",
        "De-para: 'Alimentação' tem papel 'rótulo', que não existe",
    ]
    assert ler_aba(revisao, "Conferência")[0]["Mobills"] == -1234.56
    assert ler_aba(revisao, "Cartões")[0]["Dia do vencimento"] == 12

    editar_aba(revisao, "Conferência", "Mês", "2026-03", "Mobills", "mil")
    with pytest.raises(ArquivoInvalido, match="coluna Mobills"):
        importar(geral, faturas, revisao)


def test_fatura_sem_rotulo_no_nome_e_valor_que_nao_e_numero_sao_recusados(pastas):
    geral, faturas, revisao = pastas
    escrever_geral(geral, "geral.xlsx", [linha("31/03/2026", "Mercado", -10.00, "Alimentação")])
    fatura = escrever_fatura(faturas, "Cartao A", "202603", [])
    fatura.rename(fatura.with_name("Cartao A_-_marco.xlsx"))
    with pytest.raises(ArquivoInvalido, match="falta o rótulo AAAAMM"):
        importar(geral, faturas, revisao)

    fatura.with_name("Cartao A_-_marco.xlsx").unlink()
    escrever_fatura(faturas, "Cartao A", "202603", [("02/03/2026", "Mercado", "Alimentação", 10.0)])
    escrever_geral(geral, "geral.xlsx", [linha("31/03/2026", "Mercado", "dez", "Alimentação")])
    with pytest.raises(ArquivoInvalido, match="geral.xlsx: valor que não é número"):
        importar(geral, faturas, revisao)


def test_parcelas_que_faltam_depois_do_export_sao_geradas_como_previstas(pastas):
    geral, faturas, revisao = pastas
    escrever_geral(
        geral,
        "geral.xlsx",
        [
            linha("31/07/2026", "TV (1/4)", -300.00, "Casa", tags="novo ap"),
            linha("31/08/2026", "TV (2/4)", -300.00, "Casa", situacao="Pendente", tags="novo ap"),
            # Boleto: a parcela n vence n - 1 meses depois da 1ª, que veio antes do histórico.
            linha("10/07/2026", "Faculdade (5/7)", -800.00, "Educação"),
            linha("10/08/2026", "Faculdade (6/7)", -800.00, "Educação", situacao="Pendente"),
            # A sequência acaba antes do último mês: quebrada, nada é gerado.
            linha("31/07/2026", "Curso (1/3)", -100.00, "Educação"),
            # Completa: nada falta.
            linha("31/07/2026", "Fone (2/2)", -50.00, "Eletrônicos"),
        ],
    )
    escrever_fatura(faturas, "Cartao A", "202607", [("14/07/2026", "TV", "Casa", 300.00)])

    importacao = importar(geral, faturas, revisao)

    tv = next(p for p in importacao.parcelamentos if p.descricao == "TV")
    assert [
        (x.parcela, x.situacao, x.cartao, x.data, x.mes, x.valor_centavos, x.tags)
        for x in tv.lancamentos
    ] == [
        ((1, 4), "realizado", "Cartao A", date(2026, 7, 14), "2026-07", 30000, ["novo ap"]),
        ((2, 4), "previsto", "Cartao A", date(2026, 7, 14), "2026-08", 30000, ["novo ap"]),
        ((3, 4), "previsto", "Cartao A", date(2026, 7, 14), "2026-09", 30000, ["novo ap"]),
        ((4, 4), "previsto", "Cartao A", date(2026, 7, 14), "2026-10", 30000, ["novo ap"]),
    ]
    faculdade = next(p for p in importacao.parcelamentos if p.descricao == "Faculdade")
    assert [(x.parcela, x.situacao, x.data, x.mes) for x in faculdade.lancamentos] == [
        ((5, 7), "realizado", date(2026, 7, 10), "2026-07"),
        ((6, 7), "previsto", date(2026, 8, 10), "2026-08"),
        ((7, 7), "previsto", date(2026, 9, 10), "2026-09"),
    ]
    assert [x.parcela for x in importacao.lancamentos if x.descricao == "Curso"] == [(1, 3)]
    assert [x.parcela for x in importacao.lancamentos if x.descricao == "Fone"] == [(2, 2)]
    geradas = [x for x in importacao.lancamentos if x.parcela in {(3, 4), (4, 4), (7, 7)}]
    assert len(geradas) == 3
    assert all(x.fonte == "mobills" and x.categorias for x in geradas)


def test_pendente_avulso_do_mes_do_export_ou_antes_e_descartado_e_o_de_depois_fica_previsto(pastas):
    geral, faturas, revisao = pastas
    escrever_geral(
        geral,
        "geral.xlsx",
        [
            linha("05/04/2026", "Salário", 5000.00, "Salário"),
            linha("10/04/2026", "Luz", -90.00, "Casa", situacao="Pendente"),
            linha("05/05/2026", "Salário", 5000.00, "Salário"),
            linha("10/05/2026", "Luz", -95.00, "Casa", situacao="Pendente"),
            linha("20/05/2026", "Freela", 300.00, "Trabalho", situacao="Pendente"),
            linha("10/06/2026", "Luz", -100.00, "Casa", situacao="Pendente"),
            # A parcela pendente não é avulso: fica, mesmo no mês do export.
            linha("31/05/2026", "Sofá (2/2)", -400.00, "Casa", situacao="Pendente"),
        ],
    )
    escrever_fatura(faturas, "Cartao A", "202605", [])

    importacao = importar(geral, faturas, revisao)

    assert sorted((x.descricao, x.mes, x.situacao) for x in importacao.lancamentos) == [
        ("Luz", "2026-06", "previsto"),
        ("Salário", "2026-04", "realizado"),
        ("Salário", "2026-05", "realizado"),
        ("Sofá", "2026-05", "previsto"),
    ]
    conferencia = {x["Mês"]: x for x in ler_aba(revisao, "Conferência")}
    assert conferencia["2026-04"]["Despesas"] == 0
    assert conferencia["2026-04"]["Por quê"] == "1 pendente avulso descartado (90,00)"
    assert conferencia["2026-05"]["Por quê"] == "2 pendentes avulsos descartados (-205,00)"


def test_reajuste_so_do_geral_espera_o_dono_escolher_o_cartao_da_fatura(pastas):
    geral, faturas, revisao = pastas
    escrever_geral(
        geral,
        "geral.xlsx",
        [
            linha("31/05/2026", "Mercado", -100.00, "Alimentação"),
            linha("31/05/2026", "Reajuste", -0.03, "Reajuste de fatura"),
        ],
    )
    escrever_fatura(faturas, "Cartao A", "202605", [])

    importacao = importar(geral, faturas, revisao)

    assert importacao.ajustes == [AjusteDeFatura(cartao=None, mes="2026-05", valor_centavos=3)]
    assert ler_aba(revisao, "Ajustes sem cartão") == [
        {"Mês": "2026-05", "Valor": 0.03, "Cartão (escolha)": None}
    ]
    assert "Ajustes sem cartão: o de 0,03 em 2026-05 está sem o cartão" in importacao.impedimentos

    editar_aba(revisao, "Ajustes sem cartão", "Mês", "2026-05", "Cartão (escolha)", "Cartao A")
    importacao = importar(geral, faturas, revisao)

    assert importacao.ajustes == [
        AjusteDeFatura(cartao="Cartao A", mes="2026-05", valor_centavos=3)
    ]
    assert not [x for x in importacao.impedimentos if x.startswith("Ajustes")]
    assert ler_aba(revisao, "Ajustes sem cartão")[0]["Cartão (escolha)"] == "Cartao A"
    assert ler_aba(revisao, "Faturas")[0]["Ajuste de fatura"] == 0.03

    editar_aba(revisao, "Ajustes sem cartão", "Mês", "2026-05", "Cartão (escolha)", "Outro")
    assert (
        "Ajustes sem cartão: o de 0,03 em 2026-05 tem o cartão 'Outro', que não está na aba"
        " Cartões" in importar(geral, faturas, revisao).impedimentos
    )


def test_cartao_arquivado_ignora_as_faturas_depois_da_ultima_que_o_dono_marcou(pastas):
    geral, faturas, revisao = pastas
    escrever_geral(
        geral,
        "geral.xlsx",
        [
            linha("30/04/2026", "Spotify", -21.90, "Assinaturas"),
            # A previsão que o Mobills deixou no cartão cancelado, e a cobrança de verdade no B.
            linha("09/05/2026", "Spotify", -21.90, "Assinaturas", situacao="Pendente"),
            linha("30/05/2026", "Spotify", -23.90, "Assinaturas"),
        ],
    )
    escrever_fatura(faturas, "Cartao A", "202604", [("17/04/2026", "Spotify", "Assinaturas", 21.9)])
    escrever_fatura(faturas, "Cartao A", "202605", [("17/05/2026", "Spotify", "Assinaturas", 21.9)])
    escrever_fatura(faturas, "Cartao B", "202605", [("17/05/2026", "Spotify", "Assinaturas", 23.9)])

    primeira = importar(geral, faturas, revisao)

    assert sorted((x.cartao, x.mes) for x in primeira.lancamentos) == [
        ("Cartao A", "2026-04"),
        ("Cartao A", "2026-05"),
        ("Cartao B", "2026-05"),
    ]
    assert ler_aba(revisao, "Cartões")[0]["Última fatura"] == "2026-05"

    editar_aba(revisao, "Cartões", "Pasta", "Cartao A", "Última fatura", "2026-04")
    editar_aba(revisao, "Cartões", "Pasta", "Cartao A", "Arquivado (sim ou não)", "sim")
    editar_aba(revisao, "Cartões", "Pasta", "Cartao B", "Dia do fechamento", 27)
    editar_aba(revisao, "Cartões", "Pasta", "Cartao B", "Dia do vencimento", 3)
    importar(geral, faturas, revisao)
    segunda = importar(geral, faturas, revisao)

    assert segunda.impedimentos == []
    assert sorted((x.cartao, x.mes, x.situacao) for x in segunda.lancamentos) == [
        ("Cartao A", "2026-04", "realizado"),
        ("Cartao B", "2026-05", "realizado"),
    ]
    assert segunda.meses_das_faturas["Cartao A"] == ["2026-04"]
    assert ler_aba(revisao, "Cartões")[0]["Última fatura"] == "2026-04"
    assert [(x["Cartão"], x["Mês"]) for x in ler_aba(revisao, "Faturas")] == [
        ("Cartao A", "2026-04"),
        ("Cartao B", "2026-05"),
    ]


def test_dono_decide_a_sequencia_quebrada_parcelamento_ou_duplicada_e_a_decisao_fica(pastas):
    geral, faturas, revisao = pastas
    coluna = "Decisão (avulsas, parcelamento ou descartar duplicada)"
    escrever_geral(
        geral,
        "geral.xlsx",
        [
            linha("31/03/2019", "Mercado", -10.00, "Alimentação"),
            # Lançada a partir da 2ª e sem a 3ª: quebrada nos dois lados.
            linha("30/04/2019", "Curso (2/3)", -100.00, "Educação"),
            # A 1ª veio duas vezes.
            linha("31/03/2019", "Fone (1/2)", -50.00, "Eletrônicos"),
            linha("31/03/2019", "Fone (1/2)", -50.00, "Eletrônicos"),
            linha("30/04/2019", "Fone (2/2)", -50.00, "Eletrônicos"),
            linha("30/06/2019", "Mercado", -10.00, "Alimentação"),
        ],
    )
    faturas.mkdir()

    primeira = importar(geral, faturas, revisao)

    assert not any(p.do_app for p in primeira.parcelamentos if p.descricao in ("Curso", "Fone"))
    assert [
        (x["Descrição"], x["Parcelas"], x[coluna]) for x in ler_aba(revisao, "Parcelas quebradas")
    ] == [
        ("Curso", "2 de 3", None),
        ("Fone", "1 a 2 de 2", None),
        ("Fone", "1 de 2", None),
    ]

    editar_aba(revisao, "Parcelas quebradas", "Descrição", "Curso", coluna, "parcelamento")
    editar_aba(revisao, "Parcelas quebradas", "Parcelas", "1 de 2", coluna, "descartar duplicada")
    importar(geral, faturas, revisao)
    segunda = importar(geral, faturas, revisao)

    curso = next(p for p in segunda.parcelamentos if p.descricao == "Curso")
    assert curso.do_app
    assert curso.anteriores == 1
    assert [(x.parcela, x.mes, x.situacao) for x in curso.lancamentos] == [
        ((2, 3), "2019-04", "realizado"),
        # Antes do último mês pago (2019-06): o banco cobrou (ticket 219).
        ((3, 3), "2019-05", "realizado"),
    ]
    fone = [p for p in segunda.parcelamentos if p.descricao == "Fone"]
    assert [(p.do_app, [x.parcela for x in p.lancamentos]) for p in fone] == [
        (True, [(1, 2), (2, 2)])
    ]
    assert sum(1 for x in segunda.lancamentos if x.descricao == "Fone") == 2
    # A aba continua mostrando as sequências da forma como o export as traz, com a decisão.
    assert [
        (x["Descrição"], x["Parcelas"], x[coluna]) for x in ler_aba(revisao, "Parcelas quebradas")
    ] == [
        ("Curso", "2 de 3", "parcelamento"),
        ("Fone", "1 a 2 de 2", "descartar duplicada"),
        ("Fone", "1 de 2", "descartar duplicada"),
    ]


def test_os_dois_pedacos_aceitos_da_mesma_compra_nao_geram_parcela_em_dobro(pastas):
    geral, faturas, revisao = pastas
    coluna = "Decisão (avulsas, parcelamento ou descartar duplicada)"
    escrever_geral(
        geral,
        "geral.xlsx",
        [
            linha("31/03/2019", "Curso (1/5)", -100.00, "Educação"),
            linha("30/04/2019", "Curso (2/5)", -100.00, "Educação"),
            linha("30/06/2019", "Curso (4/5)", -100.00, "Educação"),
            linha("31/07/2019", "Curso (5/5)", -100.00, "Educação"),
            linha("30/09/2019", "Mercado", -10.00, "Alimentação"),
        ],
    )
    faturas.mkdir()
    importar(geral, faturas, revisao)
    editar_aba(revisao, "Parcelas quebradas", "Parcelas", "1 a 2 de 5", coluna, "parcelamento")
    editar_aba(revisao, "Parcelas quebradas", "Parcelas", "4 a 5 de 5", coluna, "parcelamento")

    importacao = importar(geral, faturas, revisao)

    curso = sorted(x.parcela for x in importacao.lancamentos if x.descricao == "Curso")
    assert curso == [(1, 5), (2, 5), (3, 5), (4, 5), (5, 5)]


def test_decisao_digitada_errado_nas_abas_de_revisao_impede_gravar(pastas):
    geral, faturas, revisao = pastas
    escrever_geral(
        geral,
        "geral.xlsx",
        [
            linha("30/09/2024", "Youtube", -24.90, "Assinaturas", situacao="Pendente"),
            linha("27/09/2024", "Youtube", -24.90, "Assinaturas"),
            linha("30/09/2024", "Curso (2/3)", -100.00, "Educação"),
            linha("31/12/2024", "Mercado", -10.00, "Alimentação"),
        ],
    )
    escrever_fatura(faturas, "Cartao A", "202409", [("01/09/2024", "Youtube", "Assinaturas", 24.9)])
    importar(geral, faturas, revisao)
    editar_aba(
        revisao,
        "Grupos ambíguos",
        "Descrição",
        "Youtube",
        "Decisão (descartar ou manter)",
        "manetr",
    )
    editar_aba(
        revisao,
        "Parcelas quebradas",
        "Descrição",
        "Curso",
        "Decisão (avulsas, parcelamento ou descartar duplicada)",
        "parcelado",
    )

    importacao = importar(geral, faturas, revisao)

    assert [x for x in importacao.impedimentos if "decisão" in x] == [
        "Grupos ambíguos: 'Youtube' de 2024-09 tem a decisão 'manetr', fora de descartar ou manter",
        (
            "Parcelas quebradas: 'Curso' tem a decisão 'parcelado',"
            " fora de avulsas, parcelamento ou descartar duplicada"
        ),
    ]
    # A decisão errada continua na planilha para o dono corrigir.
    assert (
        ler_aba(revisao, "Parcelas quebradas")[0][
            "Decisão (avulsas, parcelamento ou descartar duplicada)"
        ]
        == "parcelado"
    )


def test_transacao_ignorada_no_mobills_fica_de_fora_e_a_conferencia_do_mes_fecha(pastas):
    # As duas transações que o dono ignorou no Mobills (ticket 215); o export as traz como pagas.
    geral, faturas, revisao = pastas
    escrever_geral(
        geral,
        "geral.xlsx",
        [
            linha("05/11/2022", "Salário", 1000.00, "Salário"),
            linha("28/11/2022", "Passagem Ester ", -50.00, "Ester"),
            linha("28/11/2022", "Passagem Ester", -50.00, "Ester"),
            linha("08/07/2024", "Sem parar", -230.47, "Mãe estorno"),
            linha("08/07/2024", "Sem parar", -40.00, "Carro"),
        ],
    )
    faturas.mkdir()

    importacao = importar(geral, faturas, revisao)

    assert sorted((x.descricao.strip(), x.valor_centavos) for x in importacao.lancamentos) == [
        ("Passagem Ester", 5000),
        ("Salário", 100000),
        ("Sem parar", 4000),
    ]
    assert importacao.avisos == []
    editar_aba(revisao, "Conferência", "Mês", "2022-11", "Mobills", 950.00)
    importar(geral, faturas, revisao)
    novembro = next(x for x in ler_aba(revisao, "Conferência") if x["Mês"] == "2022-11")
    assert (novembro["Resultado"], novembro["Diferença"]) == (950.00, 0)
    assert not novembro["Por quê"]


def test_transacao_ignorada_que_o_export_nao_traz_so_vira_aviso(pastas):
    geral, faturas, revisao = pastas
    escrever_geral(geral, "geral.xlsx", [linha("28/11/2022", "Passagem Ester", -60.00, "Ester")])
    faturas.mkdir()

    importacao = importar(geral, faturas, revisao)

    assert len(importacao.lancamentos) == 1
    assert importacao.impedimentos == []
    assert importacao.avisos == [
        "ignorada não achada no geral: 'Sem parar' de 08/07/2024 na Carteira (230,47)",
        "ignorada não achada no geral: 'Passagem Ester' de 28/11/2022 na Carteira (50,00)",
    ]


def test_linha_de_fatura_que_repete_data_valor_e_cartao_de_uma_casada_so_some_com_decisao(pastas):
    geral, faturas, revisao = pastas
    escrever_geral(geral, "geral.xlsx", [linha("10/03/2026", "Mercado", -100.00, "Alimentação")])
    escrever_fatura(
        faturas,
        "Cartao A",
        "202603",
        [
            ("05/03/2026", "Mercado", "Alimentação", 100.00),
            # O Mobills duplicou a compra, com outra descrição e categoria.
            ("05/03/2026", "Compra no mercado", "Outros", 100.00),
            # Outra data: é outra compra, não é repetida.
            ("06/03/2026", "Padaria", "Alimentação", 100.00),
        ],
    )

    primeira = importar(geral, faturas, revisao)

    assert len(primeira.lancamentos) == 3
    assert ler_aba(revisao, "Faturas repetidas") == [
        {
            "Pasta do cartão": "Cartao A",
            "Mês": "2026-03",
            "Data da compra": "05/03/2026",
            "Descrição": "Compra no mercado",
            "Categoria": "Outros",
            "Valor": 100.00,
            "Descrição da linha casada": "Mercado",
            "Categoria da linha casada": "Alimentação",
            "Decisão (descartar ou manter)": None,
        }
    ]

    # Em branco, ou `manter`, a compra continua (podem ser duas compras iguais de verdade).
    editar_aba(
        revisao, "Faturas repetidas", "Descrição", "Compra no mercado",
        "Decisão (descartar ou manter)", "manter",
    )  # fmt: skip
    assert len(importar(geral, faturas, revisao).lancamentos) == 3

    editar_aba(
        revisao, "Faturas repetidas", "Descrição", "Compra no mercado",
        "Decisão (descartar ou manter)", "descartar",
    )  # fmt: skip
    importar(geral, faturas, revisao)
    segunda = importar(geral, faturas, revisao)

    assert sorted(x.descricao for x in segunda.lancamentos) == ["Mercado", "Padaria"]
    repetidas = ler_aba(revisao, "Faturas repetidas")
    assert [x["Decisão (descartar ou manter)"] for x in repetidas] == ["descartar"]
    assert ler_aba(revisao, "Faturas")[0]["Total"] == 200.00
    assert ler_aba(revisao, "Faturas")[0]["Por quê"] == (
        "1 linha duplicada pelo Mobills descartada (100,00)"
    )
    assert (
        "1 linha duplicada pelo Mobills descartada (100,00)"
        in (ler_aba(revisao, "Conferência")[0]["Por quê"])
    )

    editar_aba(
        revisao, "Faturas repetidas", "Descrição", "Compra no mercado",
        "Decisão (descartar ou manter)", "talvez",
    )  # fmt: skip
    assert (
        "Faturas repetidas: 'Compra no mercado' de Cartao A em 2026-03 tem a decisão 'talvez',"
        " fora de descartar ou manter"
    ) in importar(geral, faturas, revisao).impedimentos


# Texto de fatura como o `pdftotext` tira do PDF do Itaú (ticket 220): o layout de colunas e o raw.
FATURA_PDF_EM_COLUNAS = """\
                              Vencimento: 03/05/2024          +                         120,58
                                 Emissão: 27/04/2024
                    Previsão prox. Fechamento: 27/05/2024    = Total desta fatura          120,58
"""
FATURA_PDF_RAW = """\
Vencimento: 01/04/2024
Emissão: 25/03/2024
Total da fatura anterior 22.392,72
Lançamentos atuais 1.234,50
Total desta fatura 1.234,50
Total para próximas faturas 9.524,86
"""


def test_total_da_fatura_em_pdf_preenche_a_coluna_do_mobills_pelo_mes_antes_do_vencimento(
    pastas, tmp_path
):
    geral, faturas, revisao = pastas
    pdfs = tmp_path / "faturas-pdf"
    escrever_geral(geral, "geral.xlsx", [linha("31/03/2024", "Padaria", -20.00, "Alimentação")])
    escrever_fatura(faturas, "Cartao A", "202403", [("10/03/2024", "Loja", "Outros", 1234.50)])
    escrever_fatura(faturas, "Cartao A", "202404", [("10/04/2024", "Loja", "Outros", 100.00)])
    escrever_fatura(faturas, "Cartao B", "202404", [("10/04/2024", "Bar", "Outros", 10.00)])
    # O PDF que vence em abril é a fatura que o Mobills chama de 2024-03.
    escrever_fatura_pdf(pdfs, "Cartao A", "abril.txt", FATURA_PDF_RAW)
    # O texto em colunas sai do pdftotext em Latin-1.
    escrever_fatura_pdf(pdfs, "Cartao A", "maio.txt", FATURA_PDF_EM_COLUNAS, "latin-1")

    importacao = importar(geral, faturas, revisao, faturas_pdf=pdfs)

    linhas = {(x["Cartão"], x["Mês"]): x for x in ler_aba(revisao, "Faturas")}
    marco, abril = linhas["Cartao A", "2024-03"], linhas["Cartao A", "2024-04"]
    assert (marco["Mobills"], marco["Diferença"]) == (1234.50, 0)
    assert (abril["Mobills"], abril["Diferença"]) == (120.58, -20.58)
    # Cartão sem PDF fica com a coluna em branco, sem aviso.
    assert linhas["Cartao B", "2024-04"]["Mobills"] is None
    assert not [x for x in importacao.avisos if "fatura em texto" in x]

    # O valor que o dono digitou vale mais que o do PDF, com aviso da diferença.
    editar_aba(revisao, "Faturas", "Mês", "2024-03", "Mobills", 1200.00)
    segunda = importar(geral, faturas, revisao, faturas_pdf=pdfs)
    assert ler_aba(revisao, "Faturas")[0]["Mobills"] == 1200.00
    assert [x for x in segunda.avisos if x.startswith("Faturas:")] == [
        (
            "Faturas: Cartao A 2024-03 tem 1.200,00 na coluna Mobills e o PDF diz 1.234,50;"
            " apague a célula para usar o do PDF"
        )
    ]


def test_texto_de_fatura_sem_vencimento_ou_sem_total_vira_aviso(pastas, tmp_path):
    geral, faturas, revisao = pastas
    pdfs = tmp_path / "faturas-pdf"
    escrever_geral(geral, "geral.xlsx", [linha("31/03/2024", "Padaria", -20.00, "Alimentação")])
    escrever_fatura(faturas, "Cartao A", "202403", [])
    escrever_fatura_pdf(pdfs, "Cartao A", "sem-total.txt", "Vencimento: 01/04/2024\n")
    escrever_fatura_pdf(pdfs, "Cartao A", "a.txt", FATURA_PDF_RAW)
    escrever_fatura_pdf(pdfs, "Cartao A", "b.txt", FATURA_PDF_RAW)
    escrever_fatura_pdf(pdfs, "Cartao Errado", "c.txt", FATURA_PDF_RAW)

    importacao = importar(geral, faturas, revisao, faturas_pdf=pdfs)

    assert [x for x in importacao.avisos if "em texto" in x] == [
        "fatura em texto Cartao A/b.txt repete o mês 2024-03 de Cartao A/a.txt",
        "fatura em texto Cartao A/sem-total.txt sem vencimento ou sem 'Total desta fatura'",
        "faturas em texto de Cartao Errado: nenhum cartão com esse nome",
    ]
    assert ler_aba(revisao, "Faturas")[0]["Mobills"] == 1234.50


def test_linha_de_comando_le_as_faturas_em_texto_e_recusa_pasta_que_nao_existe(
    pastas, tmp_path, capsys
):
    geral, faturas, revisao = pastas
    pdfs = tmp_path / "faturas-pdf"
    escrever_geral(geral, "geral.xlsx", [linha("31/03/2024", "Padaria", -20.00, "Alimentação")])
    escrever_fatura(faturas, "Cartao A", "202403", [])
    escrever_fatura_pdf(pdfs, "Cartao A", "abril.txt", FATURA_PDF_RAW)

    main([str(geral), str(faturas), str(revisao), "--faturas-pdf", str(pdfs)])

    assert ler_aba(revisao, "Faturas")[0]["Mobills"] == 1234.50
    with pytest.raises(SystemExit):
        main([str(geral), str(faturas), str(revisao), "--faturas-pdf", str(tmp_path / "nada")])
    assert "não é uma pasta" in capsys.readouterr().err


def test_fatura_em_texto_que_vence_em_janeiro_e_a_de_dezembro_do_ano_anterior(pastas, tmp_path):
    geral, faturas, revisao = pastas
    pdfs = tmp_path / "faturas-pdf"
    escrever_geral(geral, "geral.xlsx", [linha("31/12/2023", "Padaria", -20.00, "Alimentação")])
    escrever_fatura(faturas, "Cartao A", "202312", [])
    escrever_fatura_pdf(
        pdfs, "Cartao A", "janeiro.txt", FATURA_PDF_RAW.replace("01/04/2024", "01/01/2024")
    )

    importar(geral, faturas, revisao, faturas_pdf=pdfs)

    assert ler_aba(revisao, "Faturas")[0]["Mobills"] == 1234.50


def test_parcela_do_meio_com_outro_valor_continua_a_mesma_compra(pastas):
    geral, faturas, revisao = pastas
    escrever_geral(
        geral,
        "geral.xlsx",
        [
            linha("31/03/2019", "Sofá (1/3)", -300.00, "Casa"),
            # O Mobills mudou o valor da 2ª: continua sendo a mesma compra (ticket 219).
            linha("30/04/2019", "Sofá (2/3)", -312.50, "Casa"),
            linha("31/05/2019", "Sofá (3/3)", -300.00, "Casa"),
        ],
    )
    faturas.mkdir()

    importacao = importar(geral, faturas, revisao)

    assert [
        (p.descricao, [(x.parcela, x.valor_centavos) for x in p.lancamentos], p.quebra)
        for p in importacao.parcelamentos
    ] == [("Sofá", [((1, 3), 30000), ((2, 3), 31250), ((3, 3), 30000)], None)]
    assert ler_aba(revisao, "Parcelas quebradas") == []


def test_duas_compras_iguais_em_paralelo_continuam_separadas_pelo_valor(pastas):
    geral, faturas, revisao = pastas
    escrever_geral(
        geral,
        "geral.xlsx",
        [
            linha("31/03/2019", "Passagem (1/3)", -100.00, "Viagem"),
            linha("31/03/2019", "Passagem (1/3)", -250.00, "Viagem"),
            # Na ordem do export a de 250 vem antes: o valor mais perto decide.
            linha("30/04/2019", "Passagem (2/3)", -250.00, "Viagem"),
            linha("30/04/2019", "Passagem (2/3)", -100.03, "Viagem"),
            linha("31/05/2019", "Passagem (3/3)", -100.00, "Viagem"),
            linha("31/05/2019", "Passagem (3/3)", -250.00, "Viagem"),
        ],
    )
    faturas.mkdir()

    importacao = importar(geral, faturas, revisao)

    assert sorted([x.valor_centavos for x in p.lancamentos] for p in importacao.parcelamentos) == [
        [10000, 10003, 10000],
        [25000, 25000, 25000],
    ]
    # Com outro valor não é parcela repetida: as duas compras não vão para a revisão.
    assert ler_aba(revisao, "Parcelas quebradas") == []


def test_linha_sem_sufixo_no_mes_do_buraco_vira_a_parcela_que_falta(pastas):
    geral, faturas, revisao = pastas
    escrever_geral(
        geral,
        "geral.xlsx",
        [
            linha("31/08/2024", "Televisão (12/21)", -250.00, "Casa"),
            # O Mobills tirou o sufixo da 13ª: o mês e o valor dizem que é ela (ticket 219).
            linha("30/09/2024", "Televisão", -250.01, "Casa"),
            linha("31/10/2024", "Televisão (14/21)", -250.00, "Casa"),
            linha("31/08/2024", "Robô aspirador (8/10)", -90.00, "Casa"),
            # Sem sufixo e com outro valor: continua avulsa.
            linha("30/09/2024", "Robô aspirador", -45.00, "Casa"),
            linha("31/10/2024", "Robô aspirador (10/10)", -90.00, "Casa"),
        ],
    )
    faturas.mkdir()

    importacao = importar(geral, faturas, revisao)

    tv = next(p for p in importacao.parcelamentos if p.descricao == "Televisão")
    assert [(x.parcela, x.mes, x.valor_centavos) for x in tv.lancamentos[:3]] == [
        ((12, 21), "2024-08", 25000),
        ((13, 21), "2024-09", 25001),
        ((14, 21), "2024-10", 25000),
    ]
    assert tv.quebra is None
    assert [x.parcela for x in importacao.lancamentos if x.descricao == "Televisão"][:3] == [
        (12, 21),
        (13, 21),
        (14, 21),
    ]
    robo = [p for p in importacao.parcelamentos if p.descricao == "Robô aspirador"]
    assert [[x.parcela for x in p.lancamentos] for p in robo] == [[(8, 10)], [(10, 10)]]
    assert [
        (x.parcela, x.valor_centavos)
        for x in importacao.lancamentos
        if x.descricao == "Robô aspirador" and x.mes == "2024-09"
    ] == [(None, 4500)]


def test_linha_sem_sufixo_antes_da_primeira_parcela_que_veio_vira_a_anterior(pastas):
    geral, faturas, revisao = pastas
    escrever_geral(
        geral,
        "geral.xlsx",
        [
            linha("28/02/2019", "Mercado", -30.00, "Alimentação"),
            linha("31/03/2019", "Sofá", -400.00, "Casa"),
            linha("30/04/2019", "Sofá (2/3)", -400.00, "Casa"),
            linha("31/05/2019", "Sofá (3/3)", -400.00, "Casa"),
        ],
    )
    faturas.mkdir()

    importacao = importar(geral, faturas, revisao)

    assert [
        ([(x.parcela, x.mes) for x in p.lancamentos], p.quebra) for p in importacao.parcelamentos
    ] == [([((1, 3), "2019-03"), ((2, 3), "2019-04"), ((3, 3), "2019-05")], None)]


def test_parcela_gerada_da_sequencia_aceita_entra_realizada_ate_o_ultimo_mes_pago(pastas):
    geral, faturas, revisao = pastas
    coluna = "Decisão (avulsas, parcelamento ou descartar duplicada)"
    escrever_geral(
        geral,
        "geral.xlsx",
        [
            linha("31/03/2019", "Curso (1/4)", -100.00, "Educação"),
            linha("31/05/2019", "Mercado", -10.00, "Alimentação"),
            linha("31/07/2019", "Mercado", -10.00, "Alimentação", situacao="Pendente"),
        ],
    )
    faturas.mkdir()
    importar(geral, faturas, revisao)
    editar_aba(revisao, "Parcelas quebradas", "Descrição", "Curso", coluna, "parcelamento")

    importacao = importar(geral, faturas, revisao)

    # O último mês pago é 2019-05: até ele o banco cobrou (ticket 219); depois, prevista.
    curso = next(p for p in importacao.parcelamentos if p.descricao == "Curso")
    assert [(x.parcela, x.mes, x.situacao) for x in curso.lancamentos] == [
        ((1, 4), "2019-03", "realizado"),
        ((2, 4), "2019-04", "realizado"),
        ((3, 4), "2019-05", "realizado"),
        ((4, 4), "2019-06", "previsto"),
    ]


def test_buraco_sem_sufixo_em_compras_paralelas_junta_cada_uma_com_a_sua(pastas):
    geral, faturas, revisao = pastas
    escrever_geral(
        geral,
        "geral.xlsx",
        [
            linha("31/03/2019", "Passagem (1/3)", -250.00, "Viagem"),
            linha("31/03/2019", "Passagem (1/3)", -100.00, "Viagem"),
            linha("30/04/2019", "Passagem", -250.00, "Viagem"),
            linha("30/04/2019", "Passagem", -100.00, "Viagem"),
            linha("31/05/2019", "Passagem (3/3)", -100.00, "Viagem"),
            linha("31/05/2019", "Passagem (3/3)", -250.00, "Viagem"),
        ],
    )
    faturas.mkdir()

    importacao = importar(geral, faturas, revisao)

    assert sorted([x.valor_centavos for x in p.lancamentos] for p in importacao.parcelamentos) == [
        [10000, 10000, 10000],
        [25000, 25000, 25000],
    ]


def test_buraco_sem_sufixo_com_o_valor_da_parcela_seguinte_junta_os_dois_pedacos(pastas):
    geral, faturas, revisao = pastas
    escrever_geral(
        geral,
        "geral.xlsx",
        [
            linha("31/03/2019", "Sofá (1/3)", -100.00, "Casa"),
            # O valor mudou a partir da 2ª, que veio sem sufixo.
            linha("30/04/2019", "Sofá", -120.00, "Casa"),
            linha("31/05/2019", "Sofá (3/3)", -120.00, "Casa"),
        ],
    )
    faturas.mkdir()

    importacao = importar(geral, faturas, revisao)

    assert [([x.parcela for x in p.lancamentos], p.quebra) for p in importacao.parcelamentos] == [
        ([(1, 3), (2, 3), (3, 3)], None)
    ]


def test_descartar_duplicada_nao_tira_a_parcela_da_compra_paralela_de_outro_valor(pastas):
    geral, faturas, revisao = pastas
    coluna = "Decisão (avulsas, parcelamento ou descartar duplicada)"
    escrever_geral(
        geral,
        "geral.xlsx",
        [
            linha("31/03/2019", "Fone (1/2)", -50.00, "Eletrônicos"),
            linha("31/03/2019", "Fone (1/2)", -50.00, "Eletrônicos"),
            linha("31/03/2019", "Fone (1/2)", -80.00, "Eletrônicos"),
            linha("30/04/2019", "Fone (2/2)", -50.00, "Eletrônicos"),
            linha("30/04/2019", "Fone (2/2)", -80.00, "Eletrônicos"),
        ],
    )
    faturas.mkdir()
    importar(geral, faturas, revisao)
    editar_aba(revisao, "Parcelas quebradas", "Parcelas", "1 de 2", coluna, "descartar duplicada")

    importacao = importar(geral, faturas, revisao)

    assert sorted(
        (x.parcela, x.valor_centavos) for x in importacao.lancamentos if x.descricao == "Fone"
    ) == [((1, 2), 5000), ((1, 2), 8000), ((2, 2), 5000), ((2, 2), 8000)]
