# Parcelamento que encolhe para uma só parcela de fatura paga

Type: task
Status: ready-for-human
Blocked by: —
Skills: `grilling`, `domain-modeling` (HITL: decisão do dono); depois `implement`, `tdd`
Modelo recomendado: Opus
Effort recomendado: medium
Issue: #434
Origem: [ticket 170](170-exclusao-do-parcelamento-deixa-as-de-fatura-paga.md): a exclusão encolhe o parcelamento até a última parcela de fatura paga, mas a tabela `parcelamentos` tem `CHECK (parcelas > 1)` e o DSQL não altera nem remove restrições ([ADR 0014](../../../docs/adr/0014-transferencia-em-tabela-propria.md)).

## O que decidir

Quando só a 1ª parcela está numa fatura paga pelo pagamento, o encolhido seria um 1x, que a tabela recusa. Valor provisório do 170: o parcelamento fica como **2x**, com o total igual ao da 1ª parcela e a 2ª excluída uma a uma (não volta, nada mais é gerado). A parcela que ficou não muda de valor (a correção não mexe na parcela da fatura paga). Na lista, porém, ele aparece como "2x" com uma parcela só, e uma correção futura do número de parcelas parte de 2.

Opções a considerar com o dono:

- manter o 2x provisório (e talvez a tela mostrar "1 de 2, a 2ª excluída");
- aceitar o 1x: refazer a tabela sem a restrição (cópia dos dados em `prod`, cuidado com o backup, como pesou a ADR 0014), ou guardar o número "de verdade" noutra coluna;
- outra forma (por exemplo, o parcelamento de uma parcela só vira algo à parte), lembrando que o 126 descartou "desligar as parcelas como compras avulsas".

## Checklist

- [ ] Decisão do dono gravada aqui (e em ADR, se for refazer a tabela)
- [ ] Implementar o que for decidido, com teste de API em `backend/tests/test_fatura_paga.py` (hoje o caso está em `test_parcelamentos.py`, no teste da confirmação da exclusão)
- [ ] Conferir o `GLOSSARY.md` (**Exclusão do parcelamento**)
