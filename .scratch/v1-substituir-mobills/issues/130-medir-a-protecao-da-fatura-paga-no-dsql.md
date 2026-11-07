# Medir a proteção da fatura paga no DSQL

Type: task
Status: resolved
Blocked by: —
Skills: `run` (medir contra o DSQL), `diagnosing-bugs` se pesar; HITL (precisa de acesso ao DSQL)
Modelo recomendado: Sonnet
Effort recomendado: low
Issue: #308
Origem: [ticket 127](127-medir-o-custo-da-protecao-da-fatura-paga.md): a medida foi num Postgres local; a latência por consulta do DSQL não entrou.

## O que medir

`cartoes.protegida` faz 14 consultas a mais por gravação (7 por leitura de todas as faturas, 2 titulares), 28 ms no Postgres local. No DSQL cada consulta custa uma ida e volta de rede.

## Checklist

- [x] Rodar `backend/medir_fatura_paga.py` contra um banco DSQL de teste (ele apaga o schema `public`) e registrar o lançamento, o lote de 50 e a correção do parcelamento longo (ticket 180) aqui
- [x] (movido para o [ticket 202](202-decidir-o-custo-da-protecao-no-dsql.md)) Se pesar: conferir só os titulares tocados pela gravação, ou só as faturas fechadas, mantendo `backend/tests/test_fatura_paga.py`

## Medida no DSQL (sa-east-1, feita pelo dono, 11000 lançamentos de cartão, 190 faturas, 2 titulares)

| operação | com proteção | sem | custo |
|---|---|---|---|
| leitura de todas as faturas | 146 ms | — | — |
| lançamento | 444 ms | 162 ms | 282 ms |
| lote de 50 ações | 17456 ms | 9595 ms | 7861 ms (~157 ms por ação) |
| correção do parcelamento longo | não medida | | |

A correção do longo falhou: `SAVEPOINT` não suportado no DSQL, bug do app aberto no [ticket 201](201-conferencia-sem-gravar-usa-savepoint-no-dsql.md). Para medir, rodar de novo depois do 201.

Para o script rodar no DSQL: `DSQL_TESTE=1` (ele apaga as tabelas em vez do schema `public`).

## Pendências

Lançamento e lote medidos; a correção do longo e a decisão sobre o custo estão no [ticket 202](202-decidir-o-custo-da-protecao-no-dsql.md), bloqueado pelo [201](201-conferencia-sem-gravar-usa-savepoint-no-dsql.md).
