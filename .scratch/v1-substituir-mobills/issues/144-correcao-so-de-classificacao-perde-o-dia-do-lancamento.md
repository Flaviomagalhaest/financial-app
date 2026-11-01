# Correção só de classificação faz o parcelamento perder o dia do lançamento

Type: task
Status: claimed
Blocked by: —
Skills: `implement`, `tdd`
Modelo recomendado: Sonnet
Effort recomendado: low
Issue: #331
Origem: revisão (Spec) do [ticket 132](132-edicao-em-lote-perde-o-dia-do-lancamento.md)

## O problema

O ticket 132 diz que o parcelamento continua "o que o casal lançou" até uma correção de valor, de parcelas ou de data. O código olha `corrigido_em`, e o PATCH grava esse campo em qualquer correção, inclusive na que só muda descrição, pessoa ou categoria. Se o casal faz uma correção assim enquanto a geração de um boleto lançado ontem está parada, a parcela do dia do lançamento é pulada. O caso é raro.

## Checklist

- [ ] O dia do lançamento só deixa de valer quando a correção muda valor, parcelas ou data. Conferir antes se `corrigido_em` também serve ao refazer de uma correção que parou no meio (ticket 131).
- [ ] Teste: boleto lançado ontem com a geração parada, correção só da descrição, tarefa diária: a parcela de ontem nasce realizada.
