# O que fazer quando a regra tira uma parcela ou ocorrência que tem estorno

Type: decision
Status: ready-for-human
Blocked by: —
Skills: `grilling`, `domain-modeling` (HITL: decisão do dono)
Modelo recomendado: Opus
Effort recomendado: medium
Issue: #334
Origem: [ticket 133](133-estorno-acompanha-a-compra.md): a compra com estorno não se exclui, e `lancamentos.excluir` vale para todo chamador; a revisão achou os que a spec do 133 não cobre

## O que decidir

`lancamentos.excluir` recusa (422 "a compra tem estorno; exclua o estorno antes") a compra com estorno, e isso vale também quando quem exclui é uma regra, não a pessoa. O 133 fechou só `DELETE /api/parcelamentos/{id}`: recusa antes de mexer em qualquer parcela. Ficam sem decisão:

- **Parcelamento que diminui** (menos parcelas, `_aplicar` com `excluir` ou `pular` em `app/parcelamentos.py`) e **reajuste** que tira parcelas: se uma parcela retirada tem estorno, o lote levanta 422 no meio do reajuste, e a tarefa diária pode parar nele.
- **Recorrência** (`recorrencias._reajustar_um_lote` e `excluir_regra`): o mesmo, para a ocorrência com estorno.
- **Correção de fatura** (`compras_excluidas`): excluir a compra e o estorno na mesma correção só funciona se o estorno vier antes na lista; senão a correção inteira volta 422 (é tudo ou nada, então sem estado pela metade).
- Dado antigo: estorno que já estava desalinhado da compra (de antes do 133) só se acerta quando a compra mudar; backups antigos restauram assim.

Alternativas: a parcela com estorno fica (a regra a pula e avisa), a regra exclui o estorno junto, ou o reajuste é recusado antes de começar. Decisão do dono; depois vira ticket de implementação.

## Checklist

- [ ] Decidir o comportamento de cada caso acima
- [ ] Gravar na ADR 0016 (adendo) e no glossário
- [ ] Abrir o ticket de implementação, com teste de API
