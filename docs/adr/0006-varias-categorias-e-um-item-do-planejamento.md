---
status: accepted
---

# Várias categorias por lançamento, mas um item do planejamento só

Um lançamento pode ter **várias categorias** (o jantar em Ilhabela é "alimentação" e "viagem"), ao contrário do Mobills, que só permite uma, e a tag fica para rótulos pontuais de projeto ou evento ("novo ap"). Para o planejamento não contar o mesmo dinheiro duas vezes, cada lançamento conta em **no máximo um item do planejamento**: automaticamente quando só uma das categorias dele tem item no mês, e por escolha do casal quando há mais de uma. Nas estatísticas por categoria, o lançamento conta o valor inteiro em cada uma, e o total do mês conta cada lançamento uma vez.

## Considered Options

- **Uma categoria exclusiva por lançamento, com tags livres**: a pizza e o planejamento somariam 100% sem esforço e o histórico do Mobills entraria 1:1, mas "viagem" ou "família" não poderiam estar no mesmo nível de "alimentação". Rejeitada pelo dono, que quer sair justamente dessa limitação do Mobills.
- **Só tags, com uma marcada como principal**: a principal faria o papel de categoria, mas o mesmo nome seria fatia da pizza num lançamento e não seria em outro.
- **Valor inteiro em cada item do planejamento**: simples, mas um jantar em viagem consumiria os dois itens, e a soma do que foi gasto nos itens passaria do que saiu de fato.
- **Ratear o valor entre as categorias**: fecharia as somas em 100%, mas cria valores que não existem ("R$ 100 de viagem nesse jantar"); dividir um lançamento ficou fora da v1.

## Consequences

- Não há pizza por categoria: as visões por categoria e por tag são barras ou listas cuja soma pode passar do total do mês. Se a pizza fizer falta, grupos de categorias com um grupo exclusivo ("natureza do gasto") podem ser acrescentados sem reescrever os lançamentos.
- O lançamento guarda em que item do planejamento conta quando há escolha. Quando a ambiguidade surge depois (item criado no meio do mês, planejamento copiado, categorias editadas), ele fica onde estava e vai para a lista "a escolher".
- Recorrência e parcelamento guardam a escolha do item, e os previstos que geram já nascem com ela.
