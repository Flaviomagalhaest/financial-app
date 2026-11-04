# A exclusão do parcelamento deixa as parcelas de fatura paga

Type: task
Status: claimed
Blocked by: —
Skills: `implement`, `tdd`
Modelo recomendado: Opus
Effort recomendado: medium
Issue: #410
Origem: decisão do dono no [ticket 126](126-parcelamento-e-recorrencia-na-fatura-paga.md) (respostas Q1, Q6 e Q8 e o caso de canto)

## O que construir

Hoje, com a confirmação do [ticket 142](142-escopo-na-edicao-de-parcela-e-aviso-ao-excluir.md), excluir o parcelamento apaga também as parcelas de fatura paga, fora da proteção da [ADR 0021](../../../docs/adr/0021-o-pagamento-quita-a-fatura.md). Isso muda a fatura paga, o saldo anterior que ela passou, e pode deixar o pagamento acima do devido.

Exemplo: 10x no cartão, com as parcelas 1 a 3 em faturas pagas. Excluir o parcelamento apaga as parcelas 4 a 10 (as realizadas de fatura não paga, com a confirmação, como já acontece). As parcelas 1 a 3 ficam como estão, e o parcelamento continua existindo, **encolhido** para 3 parcelas, com o total igual à soma delas e nada mais gerado. Na lista, ele aparece como um 3x já terminado. Para tirar essas parcelas, o casal usa a correção de fatura.

Caso de canto: as parcelas 1, 2, 3 e 5 estão em faturas pagas e a 4 numa fatura fechada sem pagamento. O parcelamento encolhe até a **última parcela de fatura paga** (5), e a 4 sai como "excluída uma a uma", então não volta.

Só vale para a fatura paga pelo pagamento (`paga_pelo_pagamento`). A parcela da fatura importada do Mobills continua saindo, com o aviso e a confirmação.

## Checklist

- [ ] A exclusão apaga só as parcelas fora da fatura paga pelo pagamento e encolhe o parcelamento até a última parcela de fatura paga (parcelas e total), sem gerar mais nada; a parcela do meio que não está em fatura paga sai como excluída uma a uma
- [ ] Sem nenhuma parcela de fatura paga, a exclusão continua igual a hoje (o parcelamento some)
- [ ] O aviso de exclusão (`AvisoDeExclusao`) diz quantas parcelas de fatura paga **ficam**, com a mensagem para corrigir a fatura se quiser tirá-las; a tela mostra esse aviso
- [ ] A parcela da fatura importada do Mobills segue saindo com o aviso, como hoje
- [ ] A exclusão em lotes não fica pela metade: o que fica é decidido antes do primeiro lote
- [ ] Testes de API em `backend/tests/test_fatura_paga.py`
- [ ] Conferir se o `GLOSSARY.md` (**Exclusão do parcelamento**) bate com o que foi feito
