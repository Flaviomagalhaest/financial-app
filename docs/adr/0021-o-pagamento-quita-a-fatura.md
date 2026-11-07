---
status: accepted
---

# O pagamento quita a fatura e passa a sobra para a seguinte

Um pagamento realizado para uma fatura fechada a deixa paga, qualquer que seja o valor: o que faltou (o total menos o pago) vira saldo anterior da fatura seguinte, em qualquer dia em que o pagamento for lançado, mesmo com a seguinte já fechada. Daí em diante a fatura paga não recebe mais pagamento, compra, troca de fatura nem estorno; só muda pela correção de fatura, que salva tudo de uma vez e refaz o saldo anterior da seguinte. O casal sempre paga a fatura com um evento, nunca de forma automática, e pensa na dívida restante como valor do mês seguinte, como no boleto do banco. Pagar a mais que o devido nunca acontece de propósito, então o app recusa, e não existe saldo anterior negativo.

## Considered Options

- **A sobra fica na fatura e a seguinte só mostra o saldo** (o comportamento do ticket 37): pagar o total de maio, com o saldo de abril dentro, deixava abril devendo e vencida na Hoje para sempre.
- **O pagamento abate primeiro a fatura mais antiga em aberto**: o pagamento apontado para maio mexeria em abril.
- **A sobra passa no vencimento**: até lá a fatura ainda receberia pagamentos. Rejeitada pelo dono: o pagamento é o evento que encerra a fatura.

## Consequences

- Fatura fechada sem nenhum pagamento continua fechada, devendo e vencida na Hoje, e não passa saldo anterior; as compras novas vão para a seguinte pela data do fechamento, como sempre.
- Fatura fechada de total zero fica fechada, não paga.
- Compra esquecida, troca, estorno ou acerto de datas que cairia numa fatura paga é recusado com aviso para corrigir a fatura.
- O parcelamento e a recorrência no cartão também não mudam uma fatura paga pelo pagamento (ticket 126). Como gravam em vários lotes, a regra é decidida antes do primeiro lote, para não ficar pela metade:
  - **excluir o parcelamento** deixa as parcelas de fatura paga, e ele continua existindo, encolhido até a última delas;
  - **corrigir o parcelamento** deixa intocada a parcela de fatura paga, recusa encolher abaixo da última delas e recusa levar uma parcela para dentro de uma fatura paga. A fatura paga depois dessa conferência, com o refazer em lotes no meio, para a correção no lote que levaria uma parcela para dentro dela: as que faltavam ficam como estavam e a recusa fica gravada no parcelamento (ticket 180);
  - **criar uma recorrência** cuja ocorrência do dia do lançamento (ou outra que nasce antes de hoje, num calendário curto) cairia numa fatura paga é recusado (paga a fatura depois da criação, entre os lotes da geração, a ocorrência de antes de hoje dela passa sem virar lançamento, ticket 179, e fica como **ocorrência pulada pela fatura paga** num aviso na regra, que só informa a data, o cartão e o mês da fatura até o casal dispensá-lo; ela não volta, e o casal a lança à mão se precisar, ticket 192), e **alterá-la** deixa como está o atrasado de fatura paga e, por enquanto, o atrasado que a data nova levaria para dentro de uma (ticket 178).

  A fatura importada do Mobills fica de fora, como no resto da proteção.
