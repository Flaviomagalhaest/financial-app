# Conferência sem gravar usa SAVEPOINT, que o DSQL não suporta

Type: bug
Status: resolved
Blocked by: —
Skills: `diagnosing-bugs`, `tdd`, `implement`
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #519
Origem: [ticket 130](130-medir-a-protecao-da-fatura-paga-no-dsql.md): ao medir no DSQL, a correção do parcelamento longo falhou com `FeatureNotSupported: unsupported transaction statement: SAVEPOINT`.

## Problema

`cartoes.conferir_sem_gravar` (`backend/app/cartoes.py`) abre `with conn.transaction():` dentro da transação de `em_transacao` e termina com `raise psycopg.Rollback()`. Dentro de uma transação, o psycopg faz isso com `SAVEPOINT`, que o DSQL recusa. Chamadores: `parcelamentos._conferir_os_lotes` (correção de parcelamento, ticket 180) e `mudanca_na_parcela.py:241`. Provável falha em produção em toda correção que passe por aí; o Postgres local e o CI não mostram.

## Checklist

- [x] Teste que reproduz sem depender de DSQL (ex.: conexão que recusa `SAVEPOINT`)
- [x] Conferir sem savepoint: a simulação usa faturas virtuais (`faturas_a_mais` em `faturas_do_titular`), nada é gravado
- [x] (lido; pendência no [ticket 203](203-simulacao-da-correcao-usa-savepoint-no-dsql.md)) Revisar os outros `conn.transaction()` aninhados (`backup.py`, `exportacao.py`, `restauracao.py`) quanto ao DSQL
- [ ] (precisa do DSQL e do dono) Rodar `medir_fatura_paga.py` com `DSQL_TESTE=1` e completar o ticket 130
