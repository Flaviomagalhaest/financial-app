# Dashboards e fechamento do mês

Type: prototype
Status: ready-for-human
Blocked by: 04, 06
Skills: `prototype` (HITL: o dono e a esposa reagem); apoio: `dataviz`, `run`
Modelo recomendado: Opus
Effort recomendado: medium
Trello: ari:cloud:trello::card/workspace/598b72bf7efc694a04666f1f/6add2e723e7baad19280d769
Origem: traçado do [mapa V1 que substitui o Mobills](../map.md)

## Question

Quais visões a v1 mostra, e como?

Protótipo de UI com variações para: o mês atual (realizado, planejado e previsto, com o cartão numa linha que abre as compras); o fechamento do mês; a evolução em 12 meses e ao longo dos anos; a comparação com o mesmo mês do ano anterior; as visões por categoria, por tag e por pessoa; a lista "a escolher" do planejamento; a projeção de saldo.

Pelo [ticket 04](04-categoria-unica-ou-so-tags.md), um lançamento pode ter várias categorias e conta o valor inteiro em cada uma: as visões por categoria e por tag são barras ou listas, sem pizza, e o total do mês conta cada lançamento uma vez. O protótipo deve mostrar se a pizza faz falta; se fizer, a saída prevista são grupos de categorias com um grupo exclusivo ("natureza do gasto") ([ADR 0006](../../../docs/adr/0006-varias-categorias-e-um-item-do-planejamento.md)).

## Checklist

- [ ] Protótipo descartável numa branch `prototipo/dashboards`, com dados fictícios (nunca os reais do Mobills)
- [ ] Ponteiro para a branch e veredito (a pergunta e o que ela decidiu) em `## Answer`
