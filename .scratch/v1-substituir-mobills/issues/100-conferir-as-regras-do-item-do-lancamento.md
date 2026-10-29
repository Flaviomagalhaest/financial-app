# Conferir as regras do item do lançamento escolhidas no ticket 51

Type: grilling
Status: ready-for-human
Blocked by: 51
Skills: `grilling`, `domain-modeling` (HITL: decisões do dono)
Modelo recomendado: Opus
Effort recomendado: medium
Issue: #194
Origem: [ticket 51](51-item-do-lancamento-e-a-escolher.md): a spec, o [ticket 04](04-categoria-unica-ou-so-tags.md) e a [ADR 0006](../../../docs/adr/0006-varias-categorias-e-um-item-do-planejamento.md) não dizem o que fazer nestes casos, e o ticket 51 escolheu um comportamento provisório para cada um (já em `backend/app/item_em_que_conta.py`, `backend/app/lancamentos.py`, `backend/app/recorrencias.py` e `backend/app/classificacao.py`, com teste em `backend/tests/test_item_do_lancamento.py`)

## O que decidir

- [ ] **Escolha sem item no mês.** O lançamento escolheu Viagem, mas o mês não tem item de Viagem (o planejamento foi copiado sem ele, ou o item foi excluído). Hoje ele conta sozinho na única outra categoria com item; com duas ou mais, entra em "a escolher" sem item. A escolha continua guardada e volta a valer quando a Viagem tem item. Fica assim, ou o lançamento não conta em nada enquanto o item da escolha faltar?
- [ ] **Voltar ao automático.** Não há como desfazer uma escolha explícita para o lançamento voltar a contar sozinho: dá para trocar a escolha, ou ela sai quando a categoria dela sai do lançamento. Precisa de "deixar o app escolher"?
- [ ] **Estorno.** O estorno nasce com a escolha da compra ou, sem ela, com o item em que a compra contava sozinha, para diminuir o mesmo item. Mudar a escolha da compra depois não muda a do estorno. Fica assim?
- [ ] **Regras na junção de categorias.** Juntar categorias passou a mover também as categorias das recorrências e dos parcelamentos (antes elas ficavam com a categoria apagada, e a recorrência gerava previstos com ela). Confirmar.
- [ ] **Recorrência mudada "daqui para frente".** A escolha nova vale para os previstos que ninguém alterou à mão (como os outros campos da regra, ticket 45), e tirar a categoria escolhida da regra tira a escolha. Confirmar.
- [ ] Gravar as decisões (ADR 0006 ou nova) e abrir os tickets de mudança que saírem delas
