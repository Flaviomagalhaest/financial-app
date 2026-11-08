# Decidir se o custo da proteção da fatura paga no DSQL pesa

Type: decision
Status: resolved
Blocked by: —
Skills: `grilling`, `domain-modeling` se virar ADR; HITL (decisão do dono)
Modelo recomendado: Sonnet
Effort recomendado: low
Issue: #521
Origem: [ticket 130](130-medir-a-protecao-da-fatura-paga-no-dsql.md): no DSQL a proteção custa 282 ms por lançamento (444 vs 162) e 7,9 s no lote de 50 (17,5 s vs 9,6 s); a correção do longo não foi medida.

## Checklist

- [ ] (movido para o [ticket 206](206-medir-a-correcao-do-longo-no-dsql.md), bloqueado pelo 203) Medir a correção do parcelamento longo com `DSQL_TESTE=1 uv run python medir_fatura_paga.py` depois do 201
- [x] Decidir se pesa: **decisão do dono (08/11): pesa só no lote**. Lançamento avulso (282 ms a mais) fica como está; o lote (7,9 s a mais, 17,5 s no total, perto do limite de ~30 s do HTTP API) vira o [ticket 205](205-lote-confere-so-os-titulares-tocados.md)
