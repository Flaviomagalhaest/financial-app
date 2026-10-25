# Categoria única ou só tags

Type: grilling
Status: resolved
Blocked by: —
Skills: `grilling` e `domain-modeling` (HITL: precisa do dono)
Modelo recomendado: Opus
Effort recomendado: high
Trello: ari:cloud:trello::card/workspace/598b72bf7efc694a04666f1f/6add2e6d50ea91b1cf63692c
Origem: traçado do [mapa V1 que substitui o Mobills](../map.md)

## Question

Além das tags, cada lançamento tem uma classificação exclusiva (uma categoria, com ou sem subcategoria)?

O dono quer várias tags num mesmo lançamento ("família" e "alimentação" ao mesmo tempo), e o planejamento fala em "R$ 1.000 em alimentação". Decidir:

- sobre o que o planejamento incide: tags, uma categoria exclusiva ou os dois;
- como gráficos de proporção (pizza) e totais somam quando um lançamento tem várias tags, sem passar de 100%;
- se as tags têm grupos ou hierarquia;
- como as categorias e subcategorias do Mobills entram aqui (viram tags? viram categorias?), usando o achado de [O que o Mobills exporta](01-o-que-o-mobills-exporta.md).

## Checklist

- [x] Decisão registrada em `## Answer`
- [x] `GLOSSARY.md` atualizado com os termos resolvidos
- [x] ADR em `docs/adr/` se a decisão for difícil de reverter, surpreendente e fruto de um trade-off real

## Answer

Nem categoria única nem só tags: cada lançamento tem **várias categorias**, e a tag vira um rótulo **pontual**. O dono quer sair da limitação do Mobills (uma categoria por lançamento): "viagem" passa a ser categoria, ao lado de "alimentação". O que garante que o planejamento não conte em dobro é a regra de que cada lançamento conta em no máximo um item do planejamento. Registrado em [ADR 0006](../../../docs/adr/0006-varias-categorias-e-um-item-do-planejamento.md); termos novos ou mudados no [glossário](../../../GLOSSARY.md): **Categoria**, **Tag**, **Pessoa**, **Conjunto**, **Item do planejamento**, **Planejamento**, **Transferência** e **Pagamento de fatura**.

- **Categoria**: lista plana mantida pelo casal, uma para despesa, uma para receita e uma para transferência, sem subcategoria, grupos ou hierarquia. Toda despesa e receita tem **uma ou mais**; a transferência pode ter (opcional, ex.: "corrente → poupança, Reserva"); o pagamento de fatura nunca tem. Renomear vale para todo o histórico; juntar uma categoria em outra move os lançamentos, os itens do planejamento e as escolhas de item; arquivar tira das opções de novo lançamento e mantém o histórico; excluir só sem lançamentos. O mesmo vale para tags.
- **Tag**: rótulo pontual de um projeto ou evento ("novo ap", a reforma do apartamento novo), nenhuma ou várias por lançamento, plana. Não entra no planejamento.
- **Pessoa**: deixa de ser "tag de pessoa" e vira um campo próprio (o Flávio, a esposa ou nenhuma, que é o conjunto), no máximo uma por lançamento.
- **Estatísticas**: por categoria e por tag, um lançamento conta o **valor inteiro em cada uma**, sem rateio. Por isso não há pizza por categoria nem por tag: são barras ou listas cuja soma pode passar do total do mês, e o total do mês conta cada lançamento uma vez. Se a pizza fizer falta no [protótipo de dashboards](11-dashboards-e-fechamento-do-mes.md), a saída é acrescentar grupos de categorias com um grupo exclusivo ("natureza do gasto"), sem reescrever os lançamentos.
- **Planejamento**: o planejamento passa a ser o quanto o casal se propõe a gastar **ou guardar** no mês. Cada item é de **uma única categoria** (nunca de tag, combinação de categorias ou pessoa), e cada lançamento conta em **no máximo um item**:
  - se só uma das categorias dele tem item no mês, conta nela sem perguntar;
  - se nenhuma tem, não conta em item nenhum, só no total do mês;
  - se duas ou mais têm, o dono escolhe: a escolha vem pré-selecionada com a última feita para aquele conjunto de categorias, troca-se com um toque sem travar o lançamento rápido, e dá para editar depois;
  - se a ambiguidade surge depois (item criado no meio do mês, planejamento copiado, categorias do lançamento editadas), o lançamento continua no item em que estava e entra na lista **"a escolher"** da tela do planejamento; uma escolha explícita nunca muda sozinha;
  - recorrência e parcelamento guardam a escolha, e cada previsto que geram já nasce com ela; mudar a escolha na regra vale daqui para frente ([ADR 0004](../../../docs/adr/0004-previsto-e-situacao-do-lancamento.md));
  - o aviso na hora de lançar mostra o item em que o lançamento conta;
  - o "quanto ainda posso gastar" do mês conta cada lançamento uma vez.
- **Importação do Mobills**: um de-para revisado pelo dono decide se cada nome de `Categoria` e de `Tags` do Mobills vira categoria, vira tag ou é descartado. Por padrão, `Categoria` vira categoria e `Tags` vira tag, com o mesmo nome. Das tags vistas, "viagem" e "ilhabela" viram a categoria Viagem e "novo ap" continua tag. Como cada lançamento do Mobills tem uma categoria só, nenhum lançamento importado precisa de escolha de item. O formato do de-para fica no [ticket 18](18-importacao-do-mobills-cartao-e-datas.md).

Fora da v1: dividir o valor de um lançamento entre categorias ou itens (já estava no mapa); planejamento por tag, por combinação de categorias ou por pessoa.

## Comments

- Com o [ticket 01](01-o-que-o-mobills-exporta.md) resolvido: o Mobills exporta uma `Categoria` por lançamento, `Subcategoria` vazia em todas as linhas de teste e `Tags` como texto livre (uma por linha nas amostras: `novo ap`, `ilhabela`, `viagem`). Na amostra, 18 a 25 categorias por período e 3 tags no total. Ou seja, o histórico chega com categoria exclusiva e quase sem tags.
