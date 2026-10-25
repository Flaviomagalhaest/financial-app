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

- [x] Protótipo descartável numa branch `prototipo/dashboards`, com dados fictícios (nunca os reais do Mobills)
- [ ] O dono e a esposa navegam as três variações e respondem às perguntas do `README.md` do protótipo
- [ ] Ponteiro para a branch e veredito (a pergunta e o que ela decidiu) em `## Answer`

## Comments

**2026-10-25, protótipo pronto para a reação do casal.** Branch `prototipo/dashboards`, pasta `.scratch/v1-substituir-mobills/prototipos/11/`: `dashboards.html` (abre com dois cliques) e `README.md` (como abrir e o que observar). Também publicado como página privada do dono: https://claude.ai/artifact/9V4EcQKeNwRnguNraGRpDd (`#A`, `#B`, `#C` no fim do endereço).

Três variações, trocadas pela barra preta no rodapé:

- **A, Painel do mês:** uma página rolando, com fechamento (meses passados), resumo, itens do planejamento, "a escolher", cartões numa linha que abre as compras, barras por categoria, tag e pessoa, comparação com o mês anterior e com o mesmo mês do ano passado, 12 meses, anos e projeção de saldo.
- **B, App com abas:** Hoje ("ainda dá para gastar", a escolher, atrasados, fatura), Mês (fechamento em texto corrido, itens, ranking com os lançamentos numa folha), Cartões, Histórico (uma métrica por vez) e Futuro.
- **C, Planilha do ano:** categorias, tags, pessoas ou cartões por 12 meses mais 3 futuros (ou por ano, 2019 a 2026), células coloridas contra o planejado e lançamentos ao clicar.

A e B têm o experimento da pizza por natureza do gasto (grupo exclusivo); C não tem pizza. A projeção mostra duas regras lado a lado ("só com os previstos" e "previstos + planejamento"), porque a regra ainda está em aberto no mapa.

Falta: o dono e a esposa reagirem; depois, o veredito (variação escolhida ou mistura, se a pizza faz falta, regra da projeção) vai em `## Answer`.

