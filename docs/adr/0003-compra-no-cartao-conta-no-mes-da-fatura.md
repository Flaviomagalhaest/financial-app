---
status: accepted
---

# Compra no cartão conta no mês da fatura

Uma compra no cartão de crédito conta no mês da fatura em que cai (o mês do fechamento, ou o anterior se o cartão for configurado assim), e não na data da compra. Isso vale para o planejamento, os dashboards por tag, as comparações entre meses, o resumo do mês e a projeção mês a mês. O casal pensa no cartão como a conta que paga no mês, e quer que o total do mês por tag feche com o que sai do dinheiro do casal naquele mês. Por isso a compra de mercado de 28/03 numa fatura que fecha em 25/04 é "alimentação de abril".

## Considered Options

- **Data da compra (competência)**: o planejamento mediria o consumo do mês corrido, mas o total por tag e o dinheiro que sai no mês viram números diferentes, com o cartão deslocado de um mês. Rejeitada pelo dono.
- **Mês do vencimento**: joga para maio uma fatura que o casal considera de abril, mesmo quando é paga em abril.

## Consequences

- Cada cartão tem exatamente uma fatura por mês, e o mês da fatura é definido quando ela nasce. Mudar as datas de uma fatura ou o dia padrão do cartão não tira a fatura do mês dela.
- O saldo da conta é a única visão que segue o dia do pagamento real, para bater com o extrato.
- Uma compra feita no fim do mês, depois do fechamento, entra no planejamento do mês seguinte, e o aviso na hora de lançar já mostra esse mês.
- Estorno conta na fatura em que aparece, e fatura fechada nunca muda. Uma tag pode ficar negativa num mês.
- A importação do Mobills tem que dar uma fatura com mês da fatura a cada compra antiga no cartão.
