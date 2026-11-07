# Simulação da correção do parcelamento usa SAVEPOINT, que o DSQL não suporta

Type: bug
Status: ready-for-agent
Blocked by: —
Skills: `diagnosing-bugs`, `tdd`, `implement`
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #527
Origem: [ticket 201](201-conferencia-sem-gravar-usa-savepoint-no-dsql.md): ao tirar o SAVEPOINT de `cartoes.conferir_sem_gravar`, sobrou o mesmo padrão em `backend/app/mudanca_na_parcela.py` (`simular_no_cartao_novo`: `with conn.transaction():` ... `raise psycopg.Rollback()`), que roda dentro da transação de `em_transacao` e vira SAVEPOINT.

## Problema

A simulação do cartão novo grava a correção inteira e desfaz com `Rollback`. No DSQL, `SAVEPOINT` é recusado (`FeatureNotSupported`). Postgres local e CI não mostram.

## Checklist

- [ ] Teste que reproduz sem DSQL (conexão que recusa `SAVEPOINT`)
- [ ] Simular sem savepoint (calcular sem gravar, ou conexão própria com `ROLLBACK`)
- [ ] Conferir se `backup.py` (`_gravar`, `esvaziar_banco`), `restauracao.py` e `exportacao.py` abrem `conn.transaction()` com transação já aberta (leitura antes, sem autocommit), o que também vira SAVEPOINT
