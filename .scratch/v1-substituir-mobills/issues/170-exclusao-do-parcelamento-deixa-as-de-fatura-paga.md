# A exclusão do parcelamento deixa as parcelas de fatura paga

Type: task
Status: resolved
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

- [x] A exclusão apaga só as parcelas fora da fatura paga pelo pagamento e encolhe o parcelamento até a última parcela de fatura paga (parcelas e total), sem gerar mais nada; a parcela do meio que não está em fatura paga sai como excluída uma a uma
- [x] Sem nenhuma parcela de fatura paga, a exclusão continua igual a hoje (o parcelamento some)
- [x] O aviso de exclusão (`AvisoDeExclusao`) diz quantas parcelas de fatura paga **ficam**, com a mensagem para corrigir a fatura se quiser tirá-las; a tela mostra esse aviso
- [x] A parcela da fatura importada do Mobills segue saindo com o aviso, como hoje
- [x] A exclusão em lotes não fica pela metade: o que fica é decidido antes do primeiro lote
- [x] Testes de API em `backend/tests/test_fatura_paga.py`
- [x] Conferir se o `GLOSSARY.md` (**Exclusão do parcelamento**) bate com o que foi feito

## Resolução

- A exclusão decide tudo numa transação antes do primeiro lote (`_exclusao`): as parcelas da fatura paga pelo pagamento ficam, o parcelamento encolhe até a última delas (`parcelas = geradas`, total = soma delas) e só as outras saem, em lotes.
- A correção do parcelamento (também a da tarefa diária) deixa como está a parcela da fatura paga pelo pagamento: sem isso, o encolhido com uma parcela do meio excluída (1, 2, 3 e 5) dividiria de novo o total pelas cinco e mudaria as faturas pagas. É o primeiro item do [ticket 171](171-correcao-do-parcelamento-nao-mexe-na-fatura-paga.md), sem a contagem em `parcelas_mantidas`, que fica com ele.
- O aviso traz `ficam_de_fatura_paga`; sem nada a sair (excluir de novo o encolhido), a exclusão não pergunta e responde 204.
- Pendências: [ticket 176](176-parcelamento-que-encolhe-para-uma-parcela.md) (só a 1ª de fatura paga: a tabela recusa 1x, fica um 2x provisório) e [ticket 177](177-antecipacao-sem-internet-intermitente.md) (teste de navegador intermitente visto nesta sessão).
- `GLOSSARY.md` (**Exclusão do parcelamento**) já descrevia o comportamento.
