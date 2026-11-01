# Medir o custo da proteção da fatura paga

Type: task
Status: resolved
Blocked by: —
Skills: `implement`, `tdd`; apoio: `run` (medir contra o banco com volume real), `diagnosing-bugs` se a medida mostrar lentidão
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #306
Origem: [ticket 125](125-o-pagamento-quita-a-fatura.md) (31/10). Só verificado nos testes, com poucos dados.

## O que medir

`cartoes.protegida` calcula todas as faturas de todos os cartões titulares antes e depois de cada gravação (lançamento, ação da fila, transferência, datas da fatura): três consultas agrupadas por titular, duas vezes, e uma terceira leitura quando nasce a fatura seguinte. Com o histórico do Mobills (cerca de 11 mil lançamentos, [ticket 07](07-exportar-o-mobills-e-medir-o-historico.md)) e o lote da fila, que protege cada ação numa transação, isso pode pesar no DSQL.

## Checklist

- [x] Medir o tempo de um lançamento e de um lote de 50 ações com o volume real (`backend/medir_busca.py` é um exemplo de medida)
- [x] Se pesar: conferir só os titulares que a gravação tocou, ou só as faturas fechadas, mantendo os testes de `backend/tests/test_fatura_paga.py`
- [x] Registrar o resultado neste ticket

## Resultado (31/10)

Medido com `backend/medir_fatura_paga.py` num Postgres 16 local (não no DSQL): 11 mil lançamentos de cartão, 2 titulares, 190 faturas, todas as passadas pagas. Mediana de 5 rodadas, com e sem `cartoes.protegida`:

| Cenário | Com proteção | Sem | Custo |
|---|---|---|---|
| 1 lançamento no cartão | 45 ms | 17 ms | 28 ms |
| Lote de 50 ações (cada uma numa transação) | 2,4 s | 0,8 s | 1,6 s |

Uma leitura de todas as faturas (`_todas`) leva 18 ms e faz 7 consultas com 2 titulares (1 + 3 por titular); a proteção lê duas vezes por gravação, então são 14 consultas a mais (21 quando nasce a fatura seguinte). O custo é linear no número de titulares e de meses de histórico.

**Decisão: não otimizar agora.** Em disco local o custo é de uns 30 ms por gravação, imperceptível num lançamento e tolerável num lote. O que pode pesar é a latência por consulta do DSQL (14 idas e voltas por gravação), que esta sessão não consegue medir: virou o [ticket 130](130-medir-a-protecao-da-fatura-paga-no-dsql.md). Se ele mostrar lentidão, o caminho do checklist (só os titulares tocados, ou só as faturas fechadas) fica nele, com `backend/tests/test_fatura_paga.py` como rede.
