# Medir a proteção da fatura paga no DSQL

Type: task
Status: ready-for-human
Blocked by: —
Skills: `run` (medir contra o DSQL), `diagnosing-bugs` se pesar; HITL (precisa de acesso ao DSQL)
Modelo recomendado: Sonnet
Effort recomendado: low
Issue: #308
Origem: [ticket 127](127-medir-o-custo-da-protecao-da-fatura-paga.md): a medida foi num Postgres local; a latência por consulta do DSQL não entrou.

## O que medir

`cartoes.protegida` faz 14 consultas a mais por gravação (7 por leitura de todas as faturas, 2 titulares), 28 ms no Postgres local. No DSQL cada consulta custa uma ida e volta de rede.

## Checklist

- [ ] Rodar `backend/medir_fatura_paga.py` contra um banco DSQL de teste (ele apaga o schema `public`) e registrar o lançamento e o lote de 50 aqui
- [ ] Se pesar: conferir só os titulares tocados pela gravação, ou só as faturas fechadas, mantendo `backend/tests/test_fatura_paga.py`
