# Medir o custo da proteção da fatura paga

Type: task
Status: ready-for-agent
Blocked by: —
Skills: `implement`, `tdd`; apoio: `run` (medir contra o banco com volume real), `diagnosing-bugs` se a medida mostrar lentidão
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #306
Origem: [ticket 125](125-o-pagamento-quita-a-fatura.md) (31/10). Só verificado nos testes, com poucos dados.

## O que medir

`cartoes.protegida` calcula todas as faturas de todos os cartões titulares antes e depois de cada gravação (lançamento, ação da fila, transferência, datas da fatura): três consultas agrupadas por titular, duas vezes, e uma terceira leitura quando nasce a fatura seguinte. Com o histórico do Mobills (cerca de 11 mil lançamentos, [ticket 07](07-exportar-o-mobills-e-medir-o-historico.md)) e o lote da fila, que protege cada ação numa transação, isso pode pesar no DSQL.

## Checklist

- [ ] Medir o tempo de um lançamento e de um lote de 50 ações com o volume real (`backend/medir_busca.py` é um exemplo de medida)
- [ ] Se pesar: conferir só os titulares que a gravação tocou, ou só as faturas fechadas, mantendo os testes de `backend/tests/test_fatura_paga.py`
- [ ] Registrar o resultado neste ticket
