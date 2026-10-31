---
status: accepted
---

# O aviso de planejamento repete no aparelho as regras do servidor, só para mostrar

O aviso de planejamento ao lançar precisa funcionar sem internet e contar os lançamentos não enviados. Por isso, o aparelho calcula onde o lançamento conta, em que fatura cai a compra no cartão e a porcentagem do item, repetindo as regras do servidor (`onde_conta`, `escolher_fatura` e `mes_da_parcela`, `percentual`). O cálculo usa o planejamento e as faturas que o aparelho guardou. Ele só mostra: quem grava a fatura, o mês e o item do lançamento continua sendo o servidor, como na [ADR 0011](0011-sem-internet-so-lancamentos-e-conflito-decidido-a-mao.md). As regras repetidas têm uma tabela de casos em `tabelas-de-teste/`, que o pytest roda no servidor e o Playwright roda no código do app. Mudar uma regra no servidor pede mudar a tabela e o app no mesmo PR. A decisão foi tomada no ticket 52, que deixou a escolha para o agente.

## Considered Options

- **Mostrar o mês da compra no cartão só depois do envio**: era o caminho mais fiel à ADR 0011. Mas, sem internet, justamente a compra no cartão (a do dia 28, que conta no mês seguinte) ficaria sem aviso, e o não enviado não teria mês para entrar no planejamento do aparelho.
- **Uma rota de prévia no servidor**: daria a resposta exata, mas só com internet. Sem internet, o aviso precisaria do cálculo no aparelho do mesmo jeito.

## Consequences

- A ADR 0011 continua valendo para gravar: sem internet o aparelho só mexe em lançamentos, e a fatura e o mês que valem são os do servidor. O que esta ADR abre é repetir as regras no aparelho para mostrar, não para decidir.
- Com o fechamento de uma fatura acertado à mão e ainda não guardado no aparelho, o aviso sem internet pode mostrar outra fatura. O app guarda as faturas dos cartões e o planejamento do mês anterior, deste e do próximo ao abrir, para isso ser raro.
- A porcentagem arredonda o meio para o par, como o `round` do Python, e o app repete isso para mostrar o mesmo número que o servidor.
- Para achar a fatura de uma compra não enviada, o aparelho lê também os cartões arquivados (`/api/cartoes?arquivados=true`): a compra feita antes do arquivamento segue contando pela fatura, não pelo mês da data.
