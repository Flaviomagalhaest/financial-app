# Medir a correção do parcelamento longo no DSQL

Type: task
Status: claimed
Blocked by: [203](203-simulacao-da-correcao-usa-savepoint-no-dsql.md)
Skills: `run`; HITL (precisa de acesso ao DSQL)
Modelo recomendado: Sonnet
Effort recomendado: low
Issue: #537
Origem: [ticket 202](202-decidir-o-custo-da-protecao-no-dsql.md): a decisão foi tomada sem essa medida; a correção do longo ainda não foi medida no DSQL.

## Checklist

- [ ] Rodar `DSQL_TESTE=1 uv run python medir_fatura_paga.py` depois do 203 e registrar aqui a correção do parcelamento longo, com e sem proteção
- [ ] Se pesar, abrir ticket de implementação (mesma ideia do 205)
