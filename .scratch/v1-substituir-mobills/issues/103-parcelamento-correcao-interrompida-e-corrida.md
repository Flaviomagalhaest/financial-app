# Parcelamento: correção interrompida e corrida com a tarefa diária

Type: task
Status: ready-for-agent
Blocked by: —
Skills: `implement`, `tdd`
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #203
Origem: [ticket 47](47-parcelamento-editar-regerar-excluir.md) (revisão com sub-agentes: pontos que o 47 deixou como estão)

## O que construir

A correção do parcelamento (`PATCH /api/parcelamentos/{id}`) refaz as parcelas em lotes de uma transação, como a recorrência. Hoje, se ela parar no meio ou esbarrar na tarefa diária, o conserto depende de repetir o pedido, e uma corrida rara perde parcelas.

## Checklist

- [ ] **Correção que parou no meio**: o `_mudar` grava o parcelamento novo (`parcelas`, `geradas`) numa transação e o refazer das parcelas vem depois. Se o refazer cai no meio (timeout da Lambda, queda), as parcelas de antes ficam como estavam até alguém repetir o pedido, e a tarefa diária só completa a geração (`completar_todos`: `geradas < parcelas`). Fazer a tarefa diária também refazer as parcelas que destoam do parcelamento (`_correcoes`), ou gravar a intenção para o refazer continuar. Repetir o pedido sem `confirmar_realizadas` volta a dar 409, mesmo com a mudança já gravada: decidir se o aviso deve olhar o que falta e não o parcelamento inteiro
- [ ] **Corrida ao crescer**: ao crescer, o `_mudar` deixa `geradas < parcelas` e o refazer revive as parcelas que a correção tirou antes (excluídas com número depois de `geradas`). Se a tarefa diária rodar `_gerar_um_lote` entre as duas, `geradas` avança e o `INSERT ... ON CONFLICT DO NOTHING` pula as excluídas: elas ficam excluídas para sempre. Reviver também em `_gerar_um_lote` ou serializar as duas
- [ ] **Exclusão concorrente**: `gerar_as_parcelas` já para quando o parcelamento some no meio; conferir `_reajustar_um_lote` e `automaticos` com um `DELETE` no meio, e testar
- [ ] Linhas por transação na primeira correção no cartão: `_correcoes` cria as faturas que faltam (até uma por parcela, 420) numa transação só, fora da conta de `_por_lote`; abaixo dos 3.000 do DSQL, mas conferir no DSQL ([ticket 35](35-teste-nos-dois-celulares.md))
- [ ] Testes de API
- [ ] Verificações do projeto rodando e PR aberto para `main`
