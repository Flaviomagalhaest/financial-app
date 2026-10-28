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
            "categorias": 0,
            "contas": 0,
            "lancamento_categorias": 0,
            "lancamentos": 0,
        }
