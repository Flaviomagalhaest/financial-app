# Deploy de prod quebrado pela migration 0066

Status: resolved
Blocked by: —
Skills: `diagnosing-bugs`, `tdd`
Modelo recomendado: Sonnet
Effort recomendado: low
Issue: #463
Origem: pedido do dono: "corrija o deploy da main que está quebrado". Todo merge na `main` desde o 141 terminava com o Deploy vermelho.

## Problema

O passo "Migrations e papéis no DSQL" do deploy de prod falhava com `FeatureNotSupported: ALTER TABLE ADD COLUMN with constraint not supported` em `0066_favoritos_partes.sql`. O arquivo nasceu como `ADD COLUMN ... partes text` e, quatro minutos depois, na revisão do 141, virou `... text NOT NULL DEFAULT '[]'`. O dev aplicou a primeira versão (por isso os deploys de branch passavam); o prod nunca aplicou nenhuma, e o DSQL recusa coluna com restrição.

## Resolução

- [x] `0066` voltou a `ADD COLUMN IF NOT EXISTS partes text` (a forma que o dev já tem). O código já trata o `NULL` (`json.loads(partes) if partes else []`) e o backup restaura `"[]"` para backup antigo
- [x] `backend/tests/test_migrations_dsql.py` falha se alguma migration usar `ADD COLUMN` com `NOT NULL`, `DEFAULT`, `CHECK`, `UNIQUE`, `REFERENCES`, `PRIMARY KEY` ou `GENERATED` (conferido: falha com a 0066 antiga)
- [ ] Do dono: depois do merge, conferir que o Deploy da `main` ficou verde e que as migrations 0066 a 0079 entraram no prod
