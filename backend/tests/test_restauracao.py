import io
import json
import zipfile

import psycopg
import pytest

from app import backup as formato
from app.backup import RestauracaoDesfeita, RestauracaoRecusada, gerar_backup, restaurar_backup
from app.migrations import aplicar_migrations
from tests.exemplo_ficticio import trocar_arquivo


def apagar_os_dados(conn: psycopg.Connection) -> None:
    """Deixa o banco fictício como um banco novo: as tabelas das migrations, sem linhas."""
    tabelas = conn.execute(
        "SELECT string_agg(quote_ident(table_name), ', ') FROM information_schema.tables"
        " WHERE table_schema = 'public' AND table_name <> 'controle_de_migrations'"
    ).fetchone()[0]
    conn.execute(f"TRUNCATE {tabelas}")


def trocar_manifesto(backup: bytes, mudar) -> bytes:
    with zipfile.ZipFile(io.BytesIO(backup)) as zip:
        manifesto = json.loads(zip.read("manifesto.json"))
    mudar(manifesto)
    return trocar_arquivo(backup, "manifesto.json", json.dumps(manifesto).encode())


def contar_linhas(conn: psycopg.Connection) -> dict[str, int]:
    return {
        tabela: conn.execute(f'SELECT count(*) FROM "{tabela}"').fetchone()[0]
        for tabela in ("exemplo_contas", "exemplo_lancamentos")
    }


def test_restaurar_num_banco_vazio_e_exportar_de_novo_da_o_mesmo_zip(banco_ficticio):
    backup = gerar_backup(banco_ficticio)
    apagar_os_dados(banco_ficticio)

    restaurar_backup(banco_ficticio, backup)

    assert gerar_backup(banco_ficticio) == backup


def test_ida_e_volta_de_timestamptz_nao_depende_do_fuso_da_sessao(banco_ficticio):
    banco_ficticio.execute("CREATE TABLE eventos (id int PRIMARY KEY, em timestamptz)")
    banco_ficticio.execute("INSERT INTO eventos VALUES (1, '2026-10-28 03:07:00.25-03'), (2, NULL)")
    banco_ficticio.execute("SET TIME ZONE 'America/Sao_Paulo'")
    backup = gerar_backup(banco_ficticio)
    apagar_os_dados(banco_ficticio)
    banco_ficticio.execute("SET TIME ZONE 'Asia/Tokyo'")

    restaurar_backup(banco_ficticio, backup)

    assert gerar_backup(banco_ficticio) == backup


def test_restauracao_grava_a_tabela_referenciada_antes_da_que_aponta_para_ela(banco_ficticio):
    # `a_parcelas` vem antes de `exemplo_lancamentos` na ordem alfabética, mas depende dela.
    banco_ficticio.execute(
        "CREATE TABLE a_parcelas (id int PRIMARY KEY, lancamento_id uuid NOT NULL"
        " REFERENCES exemplo_lancamentos (id))"
    )
    banco_ficticio.execute(
        "INSERT INTO a_parcelas VALUES (1, '00000000-0000-0000-0000-000000000001')"
    )
    backup = gerar_backup(banco_ficticio)
    apagar_os_dados(banco_ficticio)

    restaurar_backup(banco_ficticio, backup)

    assert gerar_backup(banco_ficticio) == backup


def test_restauracao_recusa_banco_com_dados_sem_gravar_nada(banco_ficticio):
    backup = gerar_backup(banco_ficticio)

    with pytest.raises(RestauracaoRecusada, match="dados"):
        restaurar_backup(banco_ficticio, backup)

    assert gerar_backup(banco_ficticio) == backup


@pytest.mark.parametrize("versao", [99, 0, True, "1"])
def test_restauracao_recusa_versao_de_formato_desconhecida(banco_ficticio, versao):
    backup = trocar_manifesto(
        gerar_backup(banco_ficticio), lambda manifesto: manifesto.update(versao_formato=versao)
    )
    apagar_os_dados(banco_ficticio)

    with pytest.raises(RestauracaoRecusada, match=f"versão {versao}"):
        restaurar_backup(banco_ficticio, backup)

    assert contar_linhas(banco_ficticio) == {"exemplo_contas": 0, "exemplo_lancamentos": 0}


@pytest.mark.parametrize(
    "migration_que_o_backup_nao_tem",
    [
        "ALTER TABLE exemplo_contas ADD COLUMN apelido text",
        "ALTER TABLE exemplo_lancamentos DROP COLUMN observacao",
        "CREATE TABLE metas (id int PRIMARY KEY)",
    ],
)
def test_restauracao_recusa_banco_com_esquema_diferente_do_backup(
    banco_ficticio, migration_que_o_backup_nao_tem
):
    backup = gerar_backup(banco_ficticio)
    apagar_os_dados(banco_ficticio)
    banco_ficticio.execute(migration_que_o_backup_nao_tem)

    with pytest.raises(RestauracaoRecusada, match="esquema"):
        restaurar_backup(banco_ficticio, backup)

    assert contar_linhas(banco_ficticio) == {"exemplo_contas": 0, "exemplo_lancamentos": 0}


def test_restauracao_recusa_zip_que_nao_bate_com_o_manifesto_antes_de_gravar(banco_ficticio):
    backup = gerar_backup(banco_ficticio)
    with zipfile.ZipFile(io.BytesIO(backup)) as zip:
        sem_a_ultima = zip.read("exemplo_lancamentos.csv").decode().splitlines(keepends=True)[:-1]
    backup = trocar_arquivo(backup, "exemplo_lancamentos.csv", "".join(sem_a_ultima).encode())
    apagar_os_dados(banco_ficticio)

    with pytest.raises(RestauracaoRecusada, match="exemplo_lancamentos.*manifesto"):
        restaurar_backup(banco_ficticio, backup)

    assert contar_linhas(banco_ficticio) == {"exemplo_contas": 0, "exemplo_lancamentos": 0}


def test_falha_no_meio_da_gravacao_desfaz_os_lotes_ja_gravados(banco_ficticio, monkeypatch):
    # Lotes de uma linha: as contas e os dois primeiros lançamentos já estão gravados quando
    # o terceiro falha.
    monkeypatch.setattr(formato, "LINHAS_POR_LOTE", 1)
    backup = gerar_backup(banco_ficticio)
    with zipfile.ZipFile(io.BytesIO(backup)) as zip:
        csv_de_lancamentos = zip.read("exemplo_lancamentos.csv").decode()
    backup = trocar_arquivo(
        backup,
        "exemplo_lancamentos.csv",
        csv_de_lancamentos.replace('"-120.35"', '"cento e vinte"').encode(),
    )
    apagar_os_dados(banco_ficticio)

    with pytest.raises(RestauracaoDesfeita, match="exemplo_lancamentos"):
        restaurar_backup(banco_ficticio, backup)

    assert contar_linhas(banco_ficticio) == {"exemplo_contas": 0, "exemplo_lancamentos": 0}


def test_restauracao_com_soma_diferente_do_manifesto_e_desfeita(banco_ficticio):
    def mudar_a_soma(manifesto: dict) -> None:
        manifesto["tabelas"]["exemplo_lancamentos"]["somas"]["valor"] = "4870.76"

    backup = trocar_manifesto(gerar_backup(banco_ficticio), mudar_a_soma)
    apagar_os_dados(banco_ficticio)

    with pytest.raises(RestauracaoDesfeita, match="exemplo_lancamentos.*valor"):
        restaurar_backup(banco_ficticio, backup)

    assert contar_linhas(banco_ficticio) == {"exemplo_contas": 0, "exemplo_lancamentos": 0}


def test_restauracao_recusa_tabela_sem_chave_primaria_que_nao_daria_para_desfazer(banco_ficticio):
    banco_ficticio.execute("CREATE TABLE notas (texto text)")
    backup = gerar_backup(banco_ficticio)
    apagar_os_dados(banco_ficticio)

    with pytest.raises(RestauracaoRecusada, match="notas.*chave primária"):
        restaurar_backup(banco_ficticio, backup)


def test_backup_da_versao_1_de_antes_das_tabelas_do_dominio_restaura_convertido(database_url):
    # O que `prod` gravava antes do ticket 32: só o manifesto, sem tabela nenhuma.
    saida = io.BytesIO()
    with zipfile.ZipFile(saida, "w") as zip:
        zip.writestr("manifesto.json", json.dumps({"versao_formato": 1, "tabelas": {}}))
    aplicar_migrations(database_url)

    with psycopg.connect(database_url, autocommit=True) as conn:
        manifesto = restaurar_backup(conn, saida.getvalue())

        assert manifesto["versao_formato"] == formato.VERSAO_FORMATO
        assert {
            tabela: conferido["linhas"] for tabela, conferido in manifesto["tabelas"].items()
        } == {
            "cartoes": 0,
            "categorias": 0,
            "contas": 0,
            "exportacoes": 0,
            "faturas": 0,
            "favoritos": 0,
            "itens_do_planejamento": 0,
            "lancamento_campos": 0,
            "lancamento_categorias": 0,
            "lancamento_tags": 0,
            "lancamentos": 0,
            "modelo_do_planejamento": 0,
            "parcelamento_categorias": 0,
            "parcelamento_tags": 0,
            "parcelamentos": 0,
            "recorrencias": 0,
            "recorrencia_categorias": 0,
            "recorrencia_tags": 0,
            "tags": 0,
            "transferencias": 0,
        }


def test_backup_da_versao_2_restaura_convertido_com_as_contas_sem_abertura(database_url):
    # O que `prod` gravava antes do ticket 36: contas sem saldo de abertura nem arquivamento e
    # nenhuma tabela de transferências.
    conta = "6f8e2d9a-1b7c-4c53-9a0e-3d5b7f1a2c40"
    contas = f"id,nome,tipo,criado_por,criado_em\n{conta},Corrente,corrente,flavio,2026-10-01 10:00:00+00\n"
    manifesto = {
        "versao_formato": 2,
        "tabelas": {
            "contas": {"linhas": 1, "somas": {}},
            "categorias": {"linhas": 0, "somas": {}},
            "lancamentos": {"linhas": 0, "somas": {"valor_centavos": "0"}},
            "lancamento_categorias": {"linhas": 0, "somas": {}},
        },
    }
    cabecalhos = {
        "categorias": "id,nome,tipo,criado_por,criado_em",
        "lancamentos": "id,tipo,situacao,valor_centavos,data,descricao,conta_id,criado_por,"
        "criado_em,alterado_por,alterado_em",
        "lancamento_categorias": "lancamento_id,categoria_id",
    }
    saida = io.BytesIO()
    with zipfile.ZipFile(saida, "w") as zip:
        zip.writestr("manifesto.json", json.dumps(manifesto))
        zip.writestr("contas.csv", contas)
        for tabela, cabecalho in cabecalhos.items():
            zip.writestr(f"{tabela}.csv", cabecalho + "\n")
    aplicar_migrations(database_url)

    with psycopg.connect(database_url, autocommit=True) as conn:
        restaurado = restaurar_backup(conn, saida.getvalue())

        assert restaurado["versao_formato"] == formato.VERSAO_FORMATO
        assert restaurado["tabelas"]["transferencias"]["linhas"] == 0
        assert conn.execute(
            "SELECT nome, saldo_abertura_centavos, data_abertura, arquivada_em FROM contas"
        ).fetchall() == [("Corrente", None, None, None)]


def test_backup_da_versao_4_sem_categoria_arquivada_restaura_com_todas_ativas(database_url):
    # O que `prod` gravava antes do ticket 74: `categorias` sem a coluna `arquivada_em`.
    aplicar_migrations(database_url)
    with psycopg.connect(database_url, autocommit=True) as conn:
        conn.execute(
            "INSERT INTO categorias (id, nome, tipo, criado_por)"
            " VALUES ('00000000-0000-0000-0000-000000000001', 'Mercado', 'despesa', 'flavio')"
        )
        atual = gerar_backup(conn)
        conn.execute("DELETE FROM categorias")
    antigo = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(atual)) as origem, zipfile.ZipFile(antigo, "w") as destino:
        for nome in origem.namelist():
            conteudo = origem.read(nome)
            if nome == "categorias.csv":
                conteudo = (
                    b"id,nome,tipo,criado_por,criado_em\n"
                    + b"\n".join(
                        b",".join(linha.split(b",")[:5])
                        for linha in conteudo.split(b"\n")[1:]
                        if linha
                    )
                    + b"\n"
                )
            if nome == "manifesto.json":
                manifesto = json.loads(conteudo)
                manifesto["versao_formato"] = 4
                conteudo = json.dumps(manifesto).encode()
            destino.writestr(nome, conteudo)

    with psycopg.connect(database_url, autocommit=True) as conn:
        manifesto = restaurar_backup(conn, antigo.getvalue())

        assert manifesto["versao_formato"] == formato.VERSAO_FORMATO
        assert conn.execute("SELECT nome, arquivada_em FROM categorias").fetchall() == [
            ("Mercado", None)
        ]


def test_backup_da_versao_6_sem_versao_nem_marca_de_exclusao_restaura_com_tudo_ativo(database_url):
    # O que `prod` gravava antes do ticket 34: lançamentos sem versão, sem marca de exclusão e sem
    # a versão de cada campo.
    aplicar_migrations(database_url)
    with psycopg.connect(database_url, autocommit=True) as conn:
        conn.execute(
            "INSERT INTO lancamentos (id, tipo, situacao, valor_centavos, data, conta_id,"
            " criado_por, alterado_por) VALUES ('00000000-0000-0000-0000-000000000001',"
            " 'despesa', 'realizado', 1000, '2026-10-02', '00000000-0000-0000-0000-000000000002',"
            " 'flavio', 'flavio')"
        )
        atual = gerar_backup(conn)
        conn.execute("DELETE FROM lancamentos")
    antigo = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(atual)) as origem, zipfile.ZipFile(antigo, "w") as destino:
        for nome in origem.namelist():
            conteudo = origem.read(nome)
            if nome in ("lancamento_campos.csv", "cartoes.csv", "faturas.csv"):
                continue
            if nome == "lancamentos.csv":
                conteudo = b"\n".join(
                    # As 2 últimas são as da versão 17 (ticket 51), as 2 antes delas, da 16
                    # (ticket 46), a antes, da 14 (ticket 39), as 2 antes, da 12 (ticket 37), as 3
                    # antes, da 11 (ticket 44), as 3 antes, da 9, e as 3 antes, da 7.
                    b",".join(linha.split(b",")[:-17])
                    for linha in conteudo.split(b"\n")
                )
            if nome == "manifesto.json":
                manifesto = json.loads(conteudo)
                manifesto["versao_formato"] = 6
                for tabela in ("lancamento_campos", "cartoes", "faturas"):
                    del manifesto["tabelas"][tabela]
                manifesto["tabelas"]["lancamentos"]["somas"] = {"valor_centavos": "1000"}
                conteudo = json.dumps(manifesto).encode()
            destino.writestr(nome, conteudo)

    with psycopg.connect(database_url, autocommit=True) as conn:
        manifesto = restaurar_backup(conn, antigo.getvalue())

        assert manifesto["versao_formato"] == formato.VERSAO_FORMATO
        assert conn.execute(
            "SELECT valor_centavos, versao, excluido_em FROM lancamentos"
        ).fetchall() == [(1000, None, None)]


def test_backup_da_versao_7_sem_itens_do_planejamento_restaura_com_o_planejamento_vazio(
    database_url,
):
    # O que `prod` gravava antes do ticket 49: nenhuma tabela de itens do planejamento.
    aplicar_migrations(database_url)
    with psycopg.connect(database_url, autocommit=True) as conn:
        atual = gerar_backup(conn)
    antigo = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(atual)) as origem, zipfile.ZipFile(antigo, "w") as destino:
        for nome in origem.namelist():
            if nome == "itens_do_planejamento.csv":
                continue
            conteudo = origem.read(nome)
            if nome == "manifesto.json":
                manifesto = json.loads(conteudo)
                manifesto["versao_formato"] = 7
                del manifesto["tabelas"]["itens_do_planejamento"]
                conteudo = json.dumps(manifesto).encode()
            destino.writestr(nome, conteudo)

    with psycopg.connect(database_url, autocommit=True) as conn:
        manifesto = restaurar_backup(conn, antigo.getvalue())

        assert manifesto["versao_formato"] == formato.VERSAO_FORMATO
        assert manifesto["tabelas"]["itens_do_planejamento"]["linhas"] == 0
        assert conn.execute("SELECT count(*) FROM itens_do_planejamento").fetchone() == (0,)


def test_backup_da_versao_8_sem_pessoa_nem_fonte_restaura_do_conjunto_e_do_app(database_url):
    # O que `prod` gravava antes do ticket 41: lançamentos sem pessoa, sem fonte e sem conferência.
    aplicar_migrations(database_url)
    with psycopg.connect(database_url, autocommit=True) as conn:
        conn.execute(
            "INSERT INTO lancamentos (id, tipo, situacao, valor_centavos, data, conta_id,"
            " criado_por, alterado_por, versao) VALUES ('00000000-0000-0000-0000-000000000001',"
            " 'despesa', 'realizado', 1000, '2026-10-02', '00000000-0000-0000-0000-000000000002',"
            " 'flavio', 'flavio', 1)"
        )
        atual = gerar_backup(conn)
        conn.execute("DELETE FROM lancamentos")
    antigo = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(atual)) as origem, zipfile.ZipFile(antigo, "w") as destino:
        for nome in origem.namelist():
            conteudo = origem.read(nome)
            if nome in ("cartoes.csv", "faturas.csv"):
                continue
            if nome == "lancamentos.csv":
                conteudo = b"\n".join(
                    # Sem as 3 da versão 9, as 3 da 11 (ticket 44), as 2 da 12 (ticket 37), a da 14
                    # (ticket 39), as 2 da 16 (ticket 46) e as 2 da 17 (ticket 51).
                    b",".join(linha.split(b",")[:-14])
                    for linha in conteudo.split(b"\n")
                )
            if nome == "manifesto.json":
                manifesto = json.loads(conteudo)
                manifesto["versao_formato"] = 8
                del manifesto["tabelas"]["cartoes"], manifesto["tabelas"]["faturas"]
                conteudo = json.dumps(manifesto).encode()
            destino.writestr(nome, conteudo)

    with psycopg.connect(database_url, autocommit=True) as conn:
        manifesto = restaurar_backup(conn, antigo.getvalue())

        assert manifesto["versao_formato"] == formato.VERSAO_FORMATO
        assert conn.execute(
            "SELECT valor_centavos, pessoa, fonte, repetido_mantido_em FROM lancamentos"
        ).fetchall() == [(1000, None, None, None)]


def test_backup_da_versao_9_sem_modelo_do_planejamento_restaura_com_o_modelo_vazio(database_url):
    # O que `prod` gravava antes do ticket 50: nenhuma tabela do modelo padrão.
    aplicar_migrations(database_url)
    with psycopg.connect(database_url, autocommit=True) as conn:
        atual = gerar_backup(conn)
    antigo = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(atual)) as origem, zipfile.ZipFile(antigo, "w") as destino:
        for nome in origem.namelist():
            if nome == "modelo_do_planejamento.csv":
                continue
            conteudo = origem.read(nome)
            if nome == "manifesto.json":
                manifesto = json.loads(conteudo)
                manifesto["versao_formato"] = 9
                del manifesto["tabelas"]["modelo_do_planejamento"]
                conteudo = json.dumps(manifesto).encode()
            destino.writestr(nome, conteudo)

    with psycopg.connect(database_url, autocommit=True) as conn:
        manifesto = restaurar_backup(conn, antigo.getvalue())

        assert manifesto["versao_formato"] == formato.VERSAO_FORMATO
        assert manifesto["tabelas"]["modelo_do_planejamento"]["linhas"] == 0
        assert conn.execute("SELECT count(*) FROM modelo_do_planejamento").fetchone() == (0,)


def test_backup_da_versao_10_sem_recorrencias_restaura_com_os_lancamentos_avulsos(database_url):
    # O que `prod` gravava antes do ticket 44: sem as tabelas das recorrências e sem a ligação do
    # lançamento à regra.
    aplicar_migrations(database_url)
    with psycopg.connect(database_url, autocommit=True) as conn:
        conn.execute(
            "INSERT INTO lancamentos (id, tipo, situacao, valor_centavos, data, conta_id,"
            " criado_por, alterado_por, versao) VALUES ('00000000-0000-0000-0000-000000000001',"
            " 'despesa', 'previsto', 1000, '2026-11-02', '00000000-0000-0000-0000-000000000002',"
            " 'flavio', 'flavio', 1)"
        )
        atual = gerar_backup(conn)
        conn.execute("DELETE FROM lancamentos")
    da_versao_11 = {"recorrencias", "recorrencia_categorias", "recorrencia_tags"}
    da_versao_12 = {"cartoes", "faturas"}
    antigo = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(atual)) as origem, zipfile.ZipFile(antigo, "w") as destino:
        for nome in origem.namelist():
            conteudo = origem.read(nome)
            if nome.removesuffix(".csv") in da_versao_11 | da_versao_12:
                continue
            if nome == "lancamentos.csv":
                # Sem as 3 da versão 11, as 2 da 12 (ticket 37), a da 14 (ticket 39), as 2 da 16
                # (ticket 46) e as 2 da 17 (ticket 51), que vêm depois.
                conteudo = b"\n".join(
                    b",".join(linha.split(b",")[:-11]) for linha in conteudo.split(b"\n")
                )
            if nome == "manifesto.json":
                manifesto = json.loads(conteudo)
                manifesto["versao_formato"] = 10
                for tabela in da_versao_11 | da_versao_12:
                    del manifesto["tabelas"][tabela]
                del manifesto["tabelas"]["lancamentos"]["somas"]["ocorrencia"]
                conteudo = json.dumps(manifesto).encode()
            destino.writestr(nome, conteudo)

    with psycopg.connect(database_url, autocommit=True) as conn:
        manifesto = restaurar_backup(conn, antigo.getvalue())

        assert manifesto["versao_formato"] == formato.VERSAO_FORMATO
        assert conn.execute(
            "SELECT valor_centavos, recorrencia_id, ocorrencia, automatico FROM lancamentos"
        ).fetchall() == [(1000, None, None, None)]
        assert conn.execute("SELECT count(*) FROM recorrencias").fetchone() == (0,)


def test_backup_da_versao_11_sem_cartoes_restaura_cada_lancamento_no_mes_da_data(database_url):
    # O que `prod` gravava antes do ticket 37: sem cartões nem faturas, e o lançamento sem o mês
    # em que conta. Antes dos cartões todo lançamento era de conta, e conta no mês da data.
    aplicar_migrations(database_url)
    with psycopg.connect(database_url, autocommit=True) as conn:
        conn.execute(
            "INSERT INTO lancamentos (id, tipo, situacao, valor_centavos, data, conta_id,"
            " criado_por, alterado_por, versao) VALUES ('00000000-0000-0000-0000-000000000001',"
            " 'despesa', 'realizado', 1000, '2026-03-28', '00000000-0000-0000-0000-000000000002',"
            " 'flavio', 'flavio', 1)"
        )
        atual = gerar_backup(conn)
        conn.execute("DELETE FROM lancamentos")
    antigo = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(atual)) as origem, zipfile.ZipFile(antigo, "w") as destino:
        for nome in origem.namelist():
            conteudo = origem.read(nome)
            if nome in ("cartoes.csv", "faturas.csv"):
                continue
            if nome == "lancamentos.csv":
                # Sem as 2 da versão 12, a da 14 (ticket 39) e as 2 da 16 (ticket 46), que vêm
                # depois.
                conteudo = b"\n".join(
                    b",".join(linha.split(b",")[:-8]) for linha in conteudo.split(b"\n")
                )
            if nome == "manifesto.json":
                manifesto = json.loads(conteudo)
                manifesto["versao_formato"] = 11
                del manifesto["tabelas"]["cartoes"], manifesto["tabelas"]["faturas"]
                conteudo = json.dumps(manifesto).encode()
            destino.writestr(nome, conteudo)

    with psycopg.connect(database_url, autocommit=True) as conn:
        manifesto = restaurar_backup(conn, antigo.getvalue())

        assert manifesto["versao_formato"] == formato.VERSAO_FORMATO
        assert conn.execute("SELECT mes::text, fatura_a_mao FROM lancamentos").fetchall() == [
            ("2026-03-01", None)
        ]
        assert conn.execute("SELECT count(*) FROM cartoes").fetchone() == (0,)


def test_backup_da_versao_12_sem_o_mes_da_fatura_na_transferencia_restaura_sem_fatura(
    database_url,
):
    # O que `prod` gravava antes do ticket 38: nenhuma transferência ia para um cartão.
    aplicar_migrations(database_url)
    with psycopg.connect(database_url, autocommit=True) as conn:
        conn.execute(
            "INSERT INTO transferencias (id, situacao, valor_centavos, data, conta_origem_id,"
            " conta_destino_id, criado_por, alterado_por)"
            " VALUES ('00000000-0000-0000-0000-000000000001', 'realizado', 3000, '2026-03-28',"
            " '00000000-0000-0000-0000-000000000002', '00000000-0000-0000-0000-000000000003',"
            " 'flavio', 'flavio')"
        )
        atual = gerar_backup(conn)
        conn.execute("DELETE FROM transferencias")
    antigo = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(atual)) as origem, zipfile.ZipFile(antigo, "w") as destino:
        for nome in origem.namelist():
            conteudo = origem.read(nome)
            if nome == "transferencias.csv":
                conteudo = b"\n".join(
                    b",".join(linha.split(b",")[:-1]) for linha in conteudo.split(b"\n")
                )
            if nome == "manifesto.json":
                manifesto = json.loads(conteudo)
                manifesto["versao_formato"] = 12
                conteudo = json.dumps(manifesto).encode()
            destino.writestr(nome, conteudo)

    with psycopg.connect(database_url, autocommit=True) as conn:
        manifesto = restaurar_backup(conn, antigo.getvalue())

        assert manifesto["versao_formato"] == formato.VERSAO_FORMATO
        assert conn.execute("SELECT valor_centavos, fatura_mes FROM transferencias").fetchall() == [
            (3000, None)
        ]


def test_backup_da_versao_13_sem_estorno_nem_ajuste_restaura_com_os_dois_vazios(database_url):
    # O que `prod` gravava antes do ticket 39: o lançamento sem a ligação ao original (estorno)
    # e a fatura sem ajuste.
    aplicar_migrations(database_url)
    with psycopg.connect(database_url, autocommit=True) as conn:
        conn.execute(
            "INSERT INTO lancamentos (id, tipo, situacao, valor_centavos, data, conta_id,"
            " criado_por, alterado_por, versao) VALUES ('00000000-0000-0000-0000-000000000001',"
            " 'despesa', 'realizado', 1000, '2026-03-28', '00000000-0000-0000-0000-000000000002',"
            " 'flavio', 'flavio', 1)"
        )
        conn.execute(
            "INSERT INTO faturas (cartao_id, mes, fechamento, vencimento) VALUES"
            " ('00000000-0000-0000-0000-000000000003', '2026-04-01', '2026-04-25', '2026-05-05')"
        )
        atual = gerar_backup(conn)
        conn.execute("DELETE FROM lancamentos")
        conn.execute("DELETE FROM faturas")
    antigo = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(atual)) as origem, zipfile.ZipFile(antigo, "w") as destino:
        for nome in origem.namelist():
            conteudo = origem.read(nome)
            if nome in ("lancamentos.csv", "faturas.csv"):
                # Na planilha dos lançamentos, a da versão 14 vem antes das 2 da 16 (ticket 46) e
                # das 2 da 17 (ticket 51).
                cortar = 6 if nome == "lancamentos.csv" else 1
                conteudo = b"\n".join(
                    b",".join(linha.split(b",")[:-cortar]) for linha in conteudo.split(b"\n")
                )
            if nome == "manifesto.json":
                manifesto = json.loads(conteudo)
                manifesto["versao_formato"] = 13
                del manifesto["tabelas"]["faturas"]["somas"]["ajuste_centavos"]
                conteudo = json.dumps(manifesto).encode()
            destino.writestr(nome, conteudo)

    with psycopg.connect(database_url, autocommit=True) as conn:
        manifesto = restaurar_backup(conn, antigo.getvalue())

        assert manifesto["versao_formato"] == formato.VERSAO_FORMATO
        assert conn.execute("SELECT valor_centavos, estorno_de FROM lancamentos").fetchall() == [
            (1000, None)
        ]
        assert conn.execute("SELECT mes::text, ajuste_centavos FROM faturas").fetchall() == [
            ("2026-04-01", None)
        ]


def test_backup_da_versao_14_sem_item_na_recorrencia_restaura_com_o_calendario_do_inicio(
    database_url,
):
    # O que `prod` gravava antes do ticket 45: a recorrência sem o item do planejamento e sem a
    # ocorrência em que o calendário começa (a 1ª).
    aplicar_migrations(database_url)
    with psycopg.connect(database_url, autocommit=True) as conn:
        conn.execute(
            "INSERT INTO recorrencias (id, tipo, valor_centavos, tipo_do_valor, automatico,"
            " conta_id, inicio, a_cada, unidade, geradas, criado_por, alterado_por)"
            " VALUES ('00000000-0000-0000-0000-000000000001', 'despesa', 1000, 'fixo', false,"
            " '00000000-0000-0000-0000-000000000002', '2026-11-02', 1, 'meses', 0, 'flavio',"
            " 'flavio')"
        )
        atual = gerar_backup(conn)
        conn.execute("DELETE FROM recorrencias")
    antigo = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(atual)) as origem, zipfile.ZipFile(antigo, "w") as destino:
        for nome in origem.namelist():
            conteudo = origem.read(nome)
            if nome == "recorrencias.csv":
                # Sem as 2 colunas da versão 15 (item e ocorrência do início), as últimas.
                conteudo = b"\n".join(
                    b",".join(linha.split(b",")[:-2]) for linha in conteudo.split(b"\n")
                )
            if nome == "manifesto.json":
                manifesto = json.loads(conteudo)
                manifesto["versao_formato"] = 14
                del manifesto["tabelas"]["recorrencias"]["somas"]["ocorrencia_do_inicio"]
                conteudo = json.dumps(manifesto).encode()
            destino.writestr(nome, conteudo)

    with psycopg.connect(database_url, autocommit=True) as conn:
        manifesto = restaurar_backup(conn, antigo.getvalue())

        assert manifesto["versao_formato"] == formato.VERSAO_FORMATO
        assert conn.execute(
            "SELECT valor_centavos, item_id, ocorrencia_do_inicio FROM recorrencias"
        ).fetchall() == [(1000, None, None)]


def test_backup_da_versao_15_sem_parcelamentos_restaura_com_os_lancamentos_avulsos(database_url):
    # O que `prod` gravava antes do ticket 46: sem as tabelas dos parcelamentos e sem a ligação
    # da parcela ao parcelamento.
    aplicar_migrations(database_url)
    with psycopg.connect(database_url, autocommit=True) as conn:
        conn.execute(
            "INSERT INTO lancamentos (id, tipo, situacao, valor_centavos, data, conta_id,"
            " criado_por, alterado_por, versao, mes) VALUES"
            " ('00000000-0000-0000-0000-000000000001', 'despesa', 'previsto', 1000, '2026-11-02',"
            " '00000000-0000-0000-0000-000000000002', 'flavio', 'flavio', 1, '2026-11-01')"
        )
        atual = gerar_backup(conn)
        conn.execute("DELETE FROM lancamentos")
    da_versao_16 = {"parcelamentos", "parcelamento_categorias", "parcelamento_tags"}
    antigo = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(atual)) as origem, zipfile.ZipFile(antigo, "w") as destino:
        for nome in origem.namelist():
            conteudo = origem.read(nome)
            if nome.removesuffix(".csv") in da_versao_16:
                continue
            if nome == "lancamentos.csv":
                # As 2 da versão 16 vêm antes das 2 da 17 (ticket 51).
                conteudo = b"\n".join(
                    b",".join(linha.split(b",")[:-5]) for linha in conteudo.split(b"\n")
                )
            if nome == "manifesto.json":
                manifesto = json.loads(conteudo)
                manifesto["versao_formato"] = 15
                for tabela in da_versao_16:
                    del manifesto["tabelas"][tabela]
                del manifesto["tabelas"]["lancamentos"]["somas"]["parcela"]
                conteudo = json.dumps(manifesto).encode()
            destino.writestr(nome, conteudo)

    with psycopg.connect(database_url, autocommit=True) as conn:
        manifesto = restaurar_backup(conn, antigo.getvalue())

        assert manifesto["versao_formato"] == formato.VERSAO_FORMATO
        assert conn.execute(
            "SELECT valor_centavos, mes::text, parcelamento_id, parcela FROM lancamentos"
        ).fetchall() == [(1000, "2026-11-01", None, None)]
        assert conn.execute("SELECT count(*) FROM parcelamentos").fetchone() == (0,)


def test_backup_da_versao_16_sem_escolha_de_item_restaura_sem_escolha(database_url):
    # O que `prod` gravava antes do ticket 51: o lançamento e o parcelamento sem a categoria do
    # item do planejamento em que contam.
    aplicar_migrations(database_url)
    with psycopg.connect(database_url, autocommit=True) as conn:
        conn.execute(
            "INSERT INTO lancamentos (id, tipo, situacao, valor_centavos, data, conta_id,"
            " criado_por, alterado_por, versao) VALUES ('00000000-0000-0000-0000-000000000001',"
            " 'despesa', 'realizado', 1000, '2026-03-28', '00000000-0000-0000-0000-000000000002',"
            " 'flavio', 'flavio', 1)"
        )
        conn.execute(
            "INSERT INTO parcelamentos (id, valor_total_centavos, parcelas, data, automatico,"
            " conta_id, geradas, criado_por, alterado_por) VALUES"
            " ('00000000-0000-0000-0000-000000000003', 5000, 2, '2026-04-10', false,"
            " '00000000-0000-0000-0000-000000000002', 0, 'flavio', 'flavio')"
        )
        atual = gerar_backup(conn)
        conn.execute("DELETE FROM lancamentos")
        conn.execute("DELETE FROM parcelamentos")
    antigo = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(atual)) as origem, zipfile.ZipFile(antigo, "w") as destino:
        for nome in origem.namelist():
            conteudo = origem.read(nome)
            cortar = {"lancamentos.csv": 3, "parcelamentos.csv": 1}.get(nome)
            if cortar:
                conteudo = b"\n".join(
                    b",".join(linha.split(b",")[:-cortar]) for linha in conteudo.split(b"\n")
                )
            if nome == "manifesto.json":
                manifesto = json.loads(conteudo)
                manifesto["versao_formato"] = 16
                conteudo = json.dumps(manifesto).encode()
            destino.writestr(nome, conteudo)

    with psycopg.connect(database_url, autocommit=True) as conn:
        manifesto = restaurar_backup(conn, antigo.getvalue())

        assert manifesto["versao_formato"] == formato.VERSAO_FORMATO
        assert conn.execute(
            "SELECT valor_centavos, item_categoria_id, item_atual_categoria_id FROM lancamentos"
        ).fetchall() == [(1000, None, None)]
        assert conn.execute(
            "SELECT valor_total_centavos, item_categoria_id FROM parcelamentos"
        ).fetchall() == [(5000, None)]


def test_backup_da_versao_17_sem_favoritos_restaura_sem_favoritos(database_url):
    # O que `prod` gravava antes do ticket 62: nenhuma tabela de favoritos.
    aplicar_migrations(database_url)
    with psycopg.connect(database_url, autocommit=True) as conn:
        conn.execute(
            "INSERT INTO lancamentos (id, tipo, situacao, valor_centavos, data, conta_id,"
            " criado_por, alterado_por, versao) VALUES ('00000000-0000-0000-0000-000000000001',"
            " 'despesa', 'realizado', 1000, '2026-03-28', '00000000-0000-0000-0000-000000000002',"
            " 'flavio', 'flavio', 1)"
        )
        atual = gerar_backup(conn)
        conn.execute("DELETE FROM lancamentos")
    antigo = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(atual)) as origem, zipfile.ZipFile(antigo, "w") as destino:
        for nome in origem.namelist():
            conteudo = origem.read(nome)
            if nome == "favoritos.csv":
                continue
            if nome == "lancamentos.csv":
                conteudo = b"\n".join(
                    b",".join(linha.split(b",")[:-1]) for linha in conteudo.split(b"\n")
                )
            if nome == "manifesto.json":
                manifesto = json.loads(conteudo)
                manifesto["versao_formato"] = 17
                del manifesto["tabelas"]["favoritos"]
                conteudo = json.dumps(manifesto).encode()
            destino.writestr(nome, conteudo)

    with psycopg.connect(database_url, autocommit=True) as conn:
        manifesto = restaurar_backup(conn, antigo.getvalue())

        assert manifesto["versao_formato"] == formato.VERSAO_FORMATO
        assert conn.execute("SELECT valor_centavos FROM lancamentos").fetchall() == [(1000,)]
        assert conn.execute("SELECT count(*) FROM favoritos").fetchone() == (0,)


def test_backup_da_versao_18_sem_marca_da_regra_restaura_com_a_exclusao_de_pessoa(database_url):
    # O que `prod` gravava antes do ticket 110: nenhuma exclusão era marcada como da regra.
    aplicar_migrations(database_url)
    with psycopg.connect(database_url, autocommit=True) as conn:
        conn.execute(
            "INSERT INTO lancamentos (id, tipo, situacao, valor_centavos, data, conta_id,"
            " criado_por, alterado_por, versao, excluido_em, excluido_por) VALUES"
            " ('00000000-0000-0000-0000-000000000001', 'despesa', 'previsto', 1000,"
            " '2026-03-28', '00000000-0000-0000-0000-000000000002', 'flavio', 'flavio', 2,"
            " now(), 'flavio')"
        )
        atual = gerar_backup(conn)
        conn.execute("DELETE FROM lancamentos")
    antigo = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(atual)) as origem, zipfile.ZipFile(antigo, "w") as destino:
        for nome in origem.namelist():
            conteudo = origem.read(nome)
            if nome == "lancamentos.csv":
                conteudo = b"\n".join(
                    b",".join(linha.split(b",")[:-1]) for linha in conteudo.split(b"\n")
                )
            if nome == "manifesto.json":
                manifesto = json.loads(conteudo)
                manifesto["versao_formato"] = 18
                conteudo = json.dumps(manifesto).encode()
            destino.writestr(nome, conteudo)

    with psycopg.connect(database_url, autocommit=True) as conn:
        manifesto = restaurar_backup(conn, antigo.getvalue())

        assert manifesto["versao_formato"] == formato.VERSAO_FORMATO
        assert conn.execute("SELECT excluido_pela_regra FROM lancamentos").fetchall() == [(False,)]


def test_os_favoritos_e_os_dispensados_voltam_do_backup_com_a_ordem(database_url):
    aplicar_migrations(database_url)
    with psycopg.connect(database_url, autocommit=True) as conn:
        for id, estado, ordem in [("1", "favorito", 2), ("2", "dispensado", None)]:
            conn.execute(
                "INSERT INTO favoritos (id, estado, identidade, descricao, tipo, conta_id,"
                " categoria_ids, tags, pessoa, valor_centavos, ordem, criado_por) VALUES"
                " (%s, %s, %s, 'Café', 'despesa', '00000000-0000-0000-0000-000000000002',"
                " '[]', '[\"Rotina\"]', 'flavio', 1200, %s, 'flavio')",
                (f"00000000-0000-0000-0000-00000000000{id}", estado, f"id{id}", ordem),
            )
        backup = gerar_backup(conn)
        conn.execute("DELETE FROM favoritos")

    with psycopg.connect(database_url, autocommit=True) as conn:
        restaurar_backup(conn, backup)

        assert conn.execute(
            "SELECT estado, ordem, tags, valor_centavos FROM favoritos ORDER BY id"
        ).fetchall() == [
            ("favorito", 2, '["Rotina"]', 1200),
            ("dispensado", None, '["Rotina"]', 1200),
        ]
