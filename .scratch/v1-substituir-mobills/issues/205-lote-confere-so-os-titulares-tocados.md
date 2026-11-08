# Lote de ações confere só os titulares tocados pela gravação

Type: task
Status: ready-for-agent
Blocked by: —
Skills: `implement`, `tdd`; apoio: `run`
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #536
Origem: [ticket 202](202-decidir-o-custo-da-protecao-no-dsql.md): decisão do dono (08/11): o custo da proteção da fatura paga pesa só no lote (17,5 s contra 9,6 s no DSQL, perto do limite de ~30 s do HTTP API); o lançamento avulso (444 ms contra 162 ms) fica como está.

## O que construir

`cartoes.protegida` lê todas as faturas dos 2 titulares em cada ação do lote (~157 ms por ação no DSQL). No caminho do lote (`backend/app/lote.py`), conferir só os titulares tocados pela gravação. Se não bastar, conferir só as faturas fechadas. O lançamento avulso não muda.

## Checklist

- [ ] Teste que fixa o comportamento: lote que toca fatura paga continua recusado (`backend/tests/test_fatura_paga.py` segue verde)
- [ ] Conferir só os titulares tocados no lote
- [ ] Medir de novo com `DSQL_TESTE=1 uv run python medir_fatura_paga.py` (HITL: precisa de acesso ao DSQL); meta: lote de 50 bem abaixo dos 17,5 s
