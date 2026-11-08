# Decidir se o custo da proteção da fatura paga no DSQL pesa

Type: decision
Status: claimed
Blocked by: [201](201-conferencia-sem-gravar-usa-savepoint-no-dsql.md)
Skills: `grilling`, `domain-modeling` se virar ADR; HITL (decisão do dono)
Modelo recomendado: Sonnet
Effort recomendado: low
Issue: #521
Origem: [ticket 130](130-medir-a-protecao-da-fatura-paga-no-dsql.md): no DSQL a proteção custa 282 ms por lançamento (444 vs 162) e 7,9 s no lote de 50 (17,5 s vs 9,6 s); a correção do longo não foi medida.

## Checklist

- [ ] Medir a correção do parcelamento longo com `DSQL_TESTE=1 uv run python medir_fatura_paga.py` depois do 201
- [ ] Decidir se pesa; se sim, conferir só os titulares tocados pela gravação, ou só as faturas fechadas, mantendo `backend/tests/test_fatura_paga.py` (vira ticket de implementação)
