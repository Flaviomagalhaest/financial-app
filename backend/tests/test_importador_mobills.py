"""Importador do Mobills (ADR 0007, ticket 18): XLSX fictícios entram, saem os lançamentos que a
importação grava e a planilha de revisão."""

from datetime import date
from pathlib import Path

import pytest

from app.mobills import AjusteDeFatura, Cartao, Conta, importar
from app.mobills.leitura import ArquivoInvalido
from tests.mobills_ficticio import editar_aba, escrever_fatura, escrever_geral, ler_aba, linha


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

    padarias = sorted(importacao.lancamentos, key=lambda x: x.data)
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
        },
    ]


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


def test_de_para_propoe_o_mesmo_papel_e_aplica_o_que_o_dono_editou(pastas):
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
        ("Celular", [(1, 10), (2, 10)]),
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
        },
        {
            "Descrição": "Curso",
            "Valor": 100.00,
            "Parcelas": "3 de 3",
            "Primeiro mês": "2019-05",
            "Último mês": "2019-05",
            "Cartão": None,
            "Motivo": "falta a parcela 2 antes de 2019-05",
        },
    ]
    sem_cartao = ler_aba(revisao, "Parcelamentos sem cartão")
    assert [(x["Descrição"], x["Parcelas"]) for x in sem_cartao] == [
        ("Celular", "1 a 2 de 10"),
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
        "Despesas": 1785.50,
        "Ajustes de fatura": 0.02,
        "Resultado": 1224.48,
        "Mobills": None,
        "Diferença": None,
        "Por quê": "2 linhas de fatura sem par (-25,50)",
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
        },
        {
            "Cartão": "Cartao A",
            "Mês": "2024-02",
            "Compras": 0,
            "Ajuste de fatura": 0,
            "Total": 0,
            "Mobills": None,
            "Diferença": None,
        },
    ]

    editar_aba(revisao, "Conferência", "Mês", "2024-01", "Mobills", 1249.98)
    editar_aba(revisao, "Faturas", "Mês", "2024-01", "Mobills", 250.02)
    importar(geral, faturas, revisao)

    janeiro = ler_aba(revisao, "Conferência")[0]
    assert (janeiro["Mobills"], janeiro["Diferença"]) == (1249.98, -25.50)
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
