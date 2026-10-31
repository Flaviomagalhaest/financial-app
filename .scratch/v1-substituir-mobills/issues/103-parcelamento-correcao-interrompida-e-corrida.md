# Parcelamento: correção interrompida e corrida com a tarefa diária

Type: task
Status: resolved
Blocked by: —
Skills: `implement`, `tdd`
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #203
Origem: [ticket 47](47-parcelamento-editar-regerar-excluir.md) (revisão com sub-agentes: pontos que o 47 deixou como estão)

## O que construir

A correção do parcelamento (`PATCH /api/parcelamentos/{id}`) refaz as parcelas em lotes de uma transação, como a recorrência. Hoje, se ela parar no meio ou esbarrar na tarefa diária, o conserto depende de repetir o pedido, e uma corrida rara perde parcelas.

## Checklist

- [x] **Correção que parou no meio**: o `_mudar` grava o parcelamento novo (`parcelas`, `geradas`) numa transação e o refazer das parcelas vem depois. Se o refazer cai no meio (timeout da Lambda, queda), as parcelas de antes ficam como estavam até alguém repetir o pedido, e a tarefa diária só completa a geração (`completar_todos`: `geradas < parcelas`). Fazer a tarefa diária também refazer as parcelas que destoam do parcelamento (`_correcoes`), ou gravar a intenção para o refazer continuar. Repetir o pedido sem `confirmar_realizadas` volta a dar 409, mesmo com a mudança já gravada: decidir se o aviso deve olhar o que falta e não o parcelamento inteiro
- [x] **Corrida ao crescer**: ao crescer, o `_mudar` deixa `geradas < parcelas` e o refazer revive as parcelas que a correção tirou antes (excluídas com número depois de `geradas`). Se a tarefa diária rodar `_gerar_um_lote` entre as duas, `geradas` avança e o `INSERT ... ON CONFLICT DO NOTHING` pula as excluídas: elas ficam excluídas para sempre. Reviver também em `_gerar_um_lote` ou serializar as duas
- [x] **Exclusão concorrente**: `gerar_as_parcelas` já para quando o parcelamento some no meio; conferir `_reajustar_um_lote` e `automaticos` com um `DELETE` no meio, e testar
- [ ] (fica no [ticket 35](35-teste-nos-dois-celulares.md), que já lista a conferência; só no DSQL) Linhas por transação na primeira correção no cartão: `_correcoes` cria as faturas que faltam (até uma por parcela, 420) numa transação só, fora da conta de `_por_lote`; abaixo dos 3.000 do DSQL, mas conferir no DSQL ([ticket 35](35-teste-nos-dois-celulares.md))
- [x] Testes de API
- [x] Verificações do projeto rodando e PR aberto para `main`

## Comments

Decisões da implementação:

- **Correção que parou no meio**: `completar_todos` (tarefa diária) agora também refaz as parcelas que destoam do parcelamento (`_correcoes`, em lotes, como o PATCH), além de gerar as que faltam. Só o cronograma (valor, data, fatura, as que saem e as que voltam) é refeito: a classificação (descrição, categorias, tags, pessoa, item) que o pedido trouxe não fica gravada, então uma correção só de classificação interrompida se completa repetindo o pedido. Parcela editada à mão continua intocada.
- **Aviso de realizadas ao repetir o pedido**: já olha o que falta refazer (compara com as parcelas de hoje), não o parcelamento inteiro; ele só volta se uma realizada ainda não mudou, e a tarefa diária a muda sem pedir de novo, porque a mudança só é gravada depois da confirmação. Coberto por teste.
- **Corrida ao crescer**: `_gerar_um_lote` revive as parcelas excluídas pela correção que cabem no lote antes do `INSERT ... ON CONFLICT DO NOTHING`.
- **Exclusão concorrente**: `_reajustar_um_lote` e `_gerar_um_lote` já paravam com o parcelamento sumido e `_realizar` (automáticos) confere o previsto na própria transação; o que quebrava era o fim do PATCH (`IndexError` → 500), que agora responde 404.
