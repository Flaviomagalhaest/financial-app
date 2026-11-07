# Parcelamento que encolhe para uma só parcela de fatura paga

Type: task
Status: resolved
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

- [x] Decisão do dono gravada aqui (e em ADR, se for refazer a tabela)
- [x] Implementar o que for decidido, com teste de API em `backend/tests/test_fatura_paga.py` (hoje o caso está em `test_parcelamentos.py`, no teste da confirmação da exclusão)
- [x] Conferir o `GLOSSARY.md` (**Exclusão do parcelamento**)

## Decisão (dono, 07/11)

- **Fica o 2x provisório** no banco: sem migration, sem coluna nova e sem refazer a tabela, então sem ADR. O caso é raro, o parcelamento já terminou, e nenhum valor ou fatura sai errado (a parcela da fatura paga fica intocada e a 2ª, excluída uma a uma, não volta). Descartados: a coluna com o número "de verdade" (todo leitor de `parcelas` teria de olhar para ela), refazer a tabela (risco nos dados de `prod` e no backup, como pesou a ADR 0014) e desligar a parcela como compra avulsa (já descartado no 126).
- **A tela não trata o caso**: lista, busca e tela do parcelamento mostram "2x", e a parcela "1/2". É o mesmo estado do encolhido 1, 2, 3 e 5, que aparece como "5x" sem a 4ª.
- **A correção segue a regra de qualquer encolhido**: parte de 2, não vai a 1x (`ge=2`), e a 3x ou mais gera as novas sem trazer de volta a 2ª nem mexer na da fatura paga.

## Resolução

- Teste de API em `backend/tests/test_fatura_paga.py` (`test_so_a_primeira_de_fatura_paga_fica_um_2x_sem_a_segunda_que_nao_volta_na_correcao`): exclusão, 2x com o total da 1ª, correção para 1x recusada e para 3x gerando só a 3ª. O teste da confirmação em `test_parcelamentos.py` deixou de conferir o 2x.
- Comentário em `excluir_parcelamento` (`backend/app/parcelamentos.py`) aponta a decisão.
- `GLOSSARY.md` (**Exclusão do parcelamento**) já bate: o 2x é detalhe de implementação e não entra nele.
- Nenhuma pendência nova.
