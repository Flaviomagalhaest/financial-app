---
status: accepted
---

# A busca filtra o período pela data da compra; o mês da fatura é um filtro à parte

O [ADR 0003](0003-compra-no-cartao-conta-no-mes-da-fatura.md) manda a compra no cartão contar no **mês da fatura** no planejamento, nas tags, no resumo e na projeção. Na **busca**, o filtro de período usa a **data da compra**: "março" traz o que foi comprado em março, qualquer que seja a fatura. O mês da fatura aparece em cada linha e tem filtro próprio, **Fatura** (cartão e mês), que é o que os atalhos do Mês e dos Cartões usam. Compra parcelada é uma linha com o valor total; no filtro Fatura, cada parcela é uma linha.

## Considered Options

- **Período pelo mês da fatura, como no resto do app**: os totais batem com a aba Mês, mas "o que comprei em março" traz compras de fevereiro, e o dono achou isso contraintuitivo na hora de procurar.
- **Dois filtros de período (data da compra e mês da fatura)**: cobre tudo, mas pesa na tela de um casal que só quer achar um lançamento.

## Consequences

- O total de uma busca por período não bate com o da aba Mês; a tela diz isso em uma linha fixa. Com o filtro Fatura os números batem.
- A compra parcelada conta pelo valor total, uma vez, fora do filtro Fatura.
- Reverter exige mudar a semântica dos filtros salvos já criados.
