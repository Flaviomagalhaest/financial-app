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

## Regras conferidas com o dono (ticket 100)

Os casos que esta decisão não cobria e que o ticket 51 resolveu de forma provisória ficam como estão:

- **Escolha sem item no mês**: a escolha continua guardada e volta a valer no mês em que a categoria dela tem item. Enquanto falta o item, o lançamento conta sozinho na única outra categoria com item, ou fica "a escolher" quando há duas ou mais. Ele não deixa de contar no planejamento.
- **Sem "deixar o app escolher"**: a escolha só muda trocando por outra, ou sai quando a categoria dela sai do lançamento. Com duas ou mais categorias com item não há automático possível, e com uma só a escolha não pesa.
- **Estorno**: conta sempre no item em que a compra (ou a parte) conta agora, e acompanha quando a escolha da compra muda (ticket 133, ADR 0016).
- **Junção de categorias**: leva junto as categorias e a escolha das recorrências e dos parcelamentos.
- **Recorrência mudada "daqui para frente"**: a escolha nova vale para os previstos que ninguém alterou à mão, como os outros campos da regra; tirar a categoria escolhida da regra tira a escolha.
- **Lançamento novo sem escolha anterior para o conjunto**: nada vem marcado e, sem toque do casal, ele é salvo "a escolher". O app não promove a primeira categoria tocada a escolha, porque a escolha nunca muda sozinha.
- **"Aquele conjunto"**: a última escolha proposta vem do lançamento mudado mais recentemente (em qualquer campo) que tem, entre as categorias com item no mês, exatamente as mesmas do lançamento novo; categorias sem item não entram no conjunto.
- **Edição**: editar um lançamento "a escolher" sem mexer no item o mantém lá; a última escolha só é proposta no lançamento novo.
