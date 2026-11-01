# Correção do parcelamento retomada noutro dia e a busca das puladas

Type: task
Status: resolved
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

- [x] Decidir com teste o que vale na retomada (por exemplo, gravar no parcelamento o dia da correção e comparar com ele)
- [x] Só procurar as puladas quando houver alguma (`geradas` maior que o número de lançamentos), sem ler as parcelas do boleto que não pulou nada
- [x] Teste de API em `backend/tests/test_parcelamentos.py`

## Resolução

- Coluna `parcelamentos.corrigido_em` (migration 0056, formato de backup 23): o `_mudar` grava o dia do pedido; `_correcoes` compara a data de antes da prevista com ele, não com o dia do lote. Sem a coluna preenchida (parcelamento antigo), vale hoje.
- `_puladas_que_chegaram` só lê as parcelas quando `geradas` é maior que o número de lançamentos do parcelamento (uma contagem).
- Testes em `backend/tests/test_parcelamentos.py` e `test_restauracao.py` (conversor 22→23).
