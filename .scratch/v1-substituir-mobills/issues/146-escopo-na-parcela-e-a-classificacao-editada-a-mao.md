# Escopo na parcela: preservar ou não a classificação editada à mão

Type: grilling
Status: ready-for-human
Blocked by: —
Skills: `grilling`, `domain-modeling` (HITL: decisão do dono); depois `implement`, `tdd`
Modelo recomendado: Opus
Effort recomendado: medium
Issue: #342
Origem: [ticket 136](136-alcance-da-mudanca-na-parcela.md) e [ticket 142](142-escopo-na-edicao-de-parcela-e-aviso-ao-excluir.md): duas decisões do dono, do mesmo dia, sobre a mesma escolha

## O que decidir

O ticket 136 (Q39 e Q40 do [ticket 94](94-conferir-as-regras-de-estorno-e-ajuste.md)) e o glossário (**Parcela alterada à mão**) dizem que "esta e as próximas", "todas" e a correção do parcelamento **preservam** o campo que uma pessoa mudou só numa parcela, também a descrição, as categorias, as tags, a pessoa e o item, e avisam quantas ficaram como estavam. Assim foi implementado ([ADR 0023](../../../docs/adr/0023-alcance-da-mudanca-na-parcela.md)).

O ticket 142 (Q7 do [ticket 99](99-parcelamento-regras-provisorias.md)) pede o mesmo escopo, mas com a classificação valendo "inclusive parcela editada à mão", e o número de parcelas e o total só no escopo "todas".

O dono decide:

- [ ] A classificação no escopo preserva a parcela editada à mão (como está) ou a sobrescreve (Q7 do 99)?
- [ ] O número de parcelas e o total só mudam pela correção do parcelamento (como está: a tela do parcelamento) ou também pela edição da parcela no escopo "todas"?
- [ ] A parte 1 do ticket 142 sai dele (o 136 a fez) e o 142 fica com o aviso ao excluir o parcelamento?

## Notas

- Se a classificação passar a sobrescrever: em `backend/app/parcelamentos.py`, `_correcoes` deixa de pular a classificação marcada à mão no escopo pedido, e o verbete do glossário muda.
