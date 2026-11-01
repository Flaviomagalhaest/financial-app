# Correção só de classificação faz o parcelamento perder o dia do lançamento

Type: task
Status: resolved
Blocked by: —
Skills: `implement`, `tdd`
Modelo recomendado: Sonnet
Effort recomendado: low
Issue: #331
Origem: revisão (Spec) do [ticket 132](132-edicao-em-lote-perde-o-dia-do-lancamento.md)

## O problema

O ticket 132 diz que o parcelamento continua "o que o casal lançou" até uma correção de valor, de parcelas ou de data. O código olha `corrigido_em`, e o PATCH grava esse campo em qualquer correção, inclusive na que só muda descrição, pessoa ou categoria. Se o casal faz uma correção assim enquanto a geração de um boleto lançado ontem está parada, a parcela do dia do lançamento é pulada. O caso é raro.

## Checklist

- [x] O dia do lançamento só deixa de valer quando a correção muda valor, parcelas ou data. Conferir antes se `corrigido_em` também serve ao refazer de uma correção que parou no meio (ticket 131).
- [x] Teste: boleto lançado ontem com a geração parada, correção só da descrição, tarefa diária: a parcela de ontem nasce realizada.

## Resolução

`gravar_correcao` só grava `corrigido_em` quando a correção muda valor, parcelas ou data (`_muda_o_calendario`); nas outras (descrição, pessoa, categoria, tags) mantém o valor anterior. Manter o anterior, e não zerar, preserva o dia do pedido que o refazer da correção parada lê (ticket 131); sem correção anterior ele segue vazio e o refazer usa o dia da retomada, inofensivo porque o calendário não mudou. Teste: `test_corrigir_so_a_descricao_nao_tira_a_parcela_do_dia_do_lancamento`.
