# Simulação da correção do parcelamento usa SAVEPOINT, que o DSQL não suporta

Type: bug
Status: resolved
Blocked by: —
Skills: `diagnosing-bugs`, `tdd`, `implement`
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #527
Origem: [ticket 201](201-conferencia-sem-gravar-usa-savepoint-no-dsql.md): ao tirar o SAVEPOINT de `cartoes.conferir_sem_gravar`, sobrou o mesmo padrão em `backend/app/mudanca_na_parcela.py` (`simular_no_cartao_novo`: `with conn.transaction():` ... `raise psycopg.Rollback()`), que roda dentro da transação de `em_transacao` e vira SAVEPOINT.

## Problema

A simulação do cartão novo grava a correção inteira e desfaz com `Rollback`. No DSQL, `SAVEPOINT` é recusado (`FeatureNotSupported`). Postgres local e CI não mostram.

## Checklist

- [x] Teste que reproduz sem DSQL (conexão que recusa `SAVEPOINT`): `test_simular_o_cartao_novo_nao_usa_savepoint_e_nao_deixa_rastro`
- [x] Simular sem savepoint: `gravar_correcao(so_conferir=True)` para antes de gravar o parcelamento, e `_desfazer_o_cartao_novo` devolve o que `_por_no_cartao_novo` mudou (conta do parcelamento, `conta_id`/`mes` das parcelas, marcas `conta_id`/`fatura_mes`)
- [x] (nenhum vira SAVEPOINT: `restauracao.py` usa conexão `autocommit=True`, então `_gravar`/`esvaziar_banco` abrem BEGIN; `exportacao.py` e `backup_diario.py` abrem `transaction()` como primeira operação da conexão, sem leitura antes) Conferir se `backup.py` (`_gravar`, `esvaziar_banco`), `restauracao.py` e `exportacao.py` abrem `conn.transaction()` com transação já aberta (leitura antes, sem autocommit), o que também vira SAVEPOINT
