import json
from pathlib import Path

import psycopg

from app.backup import CONVERSORES, FORA_DO_BACKUP, VERSAO_FORMATO
from app.migrations import aplicar_migrations

ESQUEMAS = Path(__file__).parent / "esquemas_do_formato.json"


def test_migrations_que_mudam_as_tabelas_sobem_a_versao_do_formato(database_url: str):
    # Mudar o esquema exige subir `versao_formato` e manter um conversor da versão anterior
    # (ADR 0012); sem isso, um backup antigo restauraria errado ou seria recusado sem motivo.
    aplicar_migrations(database_url)
    with psycopg.connect(database_url) as conn:
        esquema: dict[str, dict[str, str]] = {}
        for tabela, coluna, tipo in conn.execute(
            "SELECT table_name, column_name, data_type FROM information_schema.columns"
            " WHERE table_schema = 'public' ORDER BY table_name, ordinal_position"
        ):
            if tabela not in FORA_DO_BACKUP:
                esquema.setdefault(tabela, {})[coluna] = tipo
    esquemas = json.loads(ESQUEMAS.read_text())

    assert esquemas.get(str(VERSAO_FORMATO)) == esquema, (
        "as migrations mudaram as tabelas do backup: suba VERSAO_FORMATO em app/backup.py,"
        " escreva em CONVERSORES o conversor da versão anterior, com um teste que restaura um"
        f" backup dela, e grave o esquema novo em {ESQUEMAS.name}"
    )
    assert sorted(CONVERSORES) == list(range(1, VERSAO_FORMATO))
    assert sorted(map(int, esquemas)) == list(range(1, VERSAO_FORMATO + 1))
