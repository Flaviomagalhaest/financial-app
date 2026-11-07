# Conferência sem gravar usa SAVEPOINT, que o DSQL não suporta

Type: bug
Status: claimed
Blocked by: —
Skills: `diagnosing-bugs`, `tdd`, `implement`
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #519
Origem: [ticket 130](130-medir-a-protecao-da-fatura-paga-no-dsql.md): ao medir no DSQL, a correção do parcelamento longo falhou com `FeatureNotSupported: unsupported transaction statement: SAVEPOINT`.

## Problema

`cartoes.conferir_sem_gravar` (`backend/app/cartoes.py`) abre `with conn.transaction():` dentro da transação de `em_transacao` e termina com `raise psycopg.Rollback()`. Dentro de uma transação, o psycopg faz isso com `SAVEPOINT`, que o DSQL recusa. Chamadores: `parcelamentos._conferir_os_lotes` (correção de parcelamento, ticket 180) e `mudanca_na_parcela.py:241`. Provável falha em produção em toda correção que passe por aí; o Postgres local e o CI não mostram.

## Checklist

- [ ] Teste que reproduz sem depender de DSQL (ex.: conexão que recusa `SAVEPOINT`)
- [ ] Conferir sem savepoint (por ex. calcular em memória, ou transação própria numa conexão que dá `ROLLBACK`)
- [ ] Revisar os outros `conn.transaction()` aninhados (`backup.py`, `exportacao.py`, `restauracao.py`) quanto ao DSQL
- [ ] Rodar `medir_fatura_paga.py` com `DSQL_TESTE=1` e completar o ticket 130
