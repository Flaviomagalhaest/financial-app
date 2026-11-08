# Medir a correção do parcelamento longo no DSQL

Type: task
Status: ready-for-human
Blocked by: [203](203-simulacao-da-correcao-usa-savepoint-no-dsql.md)
Skills: `run`; HITL (precisa de acesso ao DSQL)
Modelo recomendado: Sonnet
Effort recomendado: low
Issue: #537
Origem: [ticket 202](202-decidir-o-custo-da-protecao-no-dsql.md): a decisão foi tomada sem essa medida; a correção do longo ainda não foi medida no DSQL.

## Checklist

- [ ] Rodar `DSQL_TESTE=1 uv run python medir_fatura_paga.py` depois do 203 e registrar aqui a correção do parcelamento longo, com e sem proteção
- [ ] Se pesar, abrir ticket de implementação (mesma ideia do 205)

## Nota (sessão na nuvem)

Tentativa sem sucesso: a sessão não tem `aws` CLI, região nem `DATABASE_URL` de um DSQL de teste, só chaves AWS soltas. O script apaga as tabelas do banco, então não foi apontado para um cluster não confirmado como de teste. O dono precisa rodar `DSQL_TESTE=1 DATABASE_URL=... uv run python medir_fatura_paga.py` num DSQL de teste (ou dar à sessão o endpoint e a região dele) e registrar o resultado aqui.
