# Correção do parcelamento retomada noutro dia e a busca das puladas

Type: task
Status: claimed
Blocked by: —
Skills: `implement`, `tdd`
Modelo recomendado: Sonnet
Effort recomendado: low
Issue: #311
Origem: revisão (Spec) do [ticket 126](126-correcao-com-parcelas-puladas.md)

## O problema

1. **A correção que para no meio depende do dia da retomada.** `_correcoes` (`backend/app/parcelamentos.py`) decide se a prevista sai como pulada comparando a data de antes com hoje (`dia_antes >= hoje`) a cada lote. Se a correção parar no meio e a tarefa diária (`completar_todos`) a retomar no dia seguinte, a parcela que era de ontem não sai pulada: fica prevista atrasada. O resultado muda conforme o dia em que a correção termina.
2. **A busca das puladas lê todas as parcelas do boleto.** `_puladas_que_chegaram` lê todos os lançamentos do parcelamento a cada lote da geração, e `_falta_conserto` faz a mesma leitura para todo boleto, todos os dias. Não é um erro, mas custa leituras no DSQL.

## Checklist

- [ ] Decidir com teste o que vale na retomada (por exemplo, gravar no parcelamento o dia da correção e comparar com ele)
- [ ] Só procurar as puladas quando houver alguma (`geradas` maior que o número de lançamentos), sem ler as parcelas do boleto que não pulou nada
- [ ] Teste de API em `backend/tests/test_parcelamentos.py`
