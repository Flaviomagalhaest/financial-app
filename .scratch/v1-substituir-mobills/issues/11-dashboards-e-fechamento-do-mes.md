# Dashboards e fechamento do mês

Type: prototype
Status: resolved
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
- [x] O dono e a esposa navegam as três variações e respondem às perguntas do `README.md` do protótipo
- [x] Ponteiro para a branch e veredito (a pergunta e o que ela decidiu) em `## Answer`

## Answer

A v1 usa a **variação B (app com abas)**, com a **comparação mês a mês da variação A** trazida para a aba Mês. A pizza não faz falta, e a projeção de saldo mostra duas linhas. O protótipo é a fonte primária: branch `prototipo/dashboards`, pasta `.scratch/v1-substituir-mobills/prototipos/11/` (`dashboards.html#B`; a versão com a comparação é o commit `89b5b32`). As variações A (painel numa página só) e C (planilha do ano) ficaram de fora.

- **Hoje**: "ainda dá para gastar" em destaque (a soma do que falta em cada item do planejamento, sem compensar um item estourado com a sobra de outro), depois a lista "a escolher", os atrasados, a fatura do cartão que vence e os itens que passaram de 80% do planejado.
- **Mês**, com navegação mês a mês:
  - no mês atual, uma barra das despesas contra o planejado (realizado, previsto e o que está livre) e as receitas recebidas e previstas;
  - num mês passado, o **fechamento do mês** em texto corrido: receitas, despesas, sobra e quanto ela é das receitas, o que foi guardado, os itens que passaram do planejado e a variação contra o mês anterior e contra o mesmo mês do ano passado;
  - a lista "a escolher" e a tabela dos itens do planejamento (realizado, previsto, planejado e %);
  - a **comparação** por categoria: o valor do mês e a variação contra o mês anterior e contra o mesmo mês do ano passado, com os valores antigos ao tocar na linha; a linha de total conta cada lançamento uma vez;
  - o ranking por categoria, por tag ou por pessoa, que abre os lançamentos numa folha.
- **Cartões**: a fatura de cada cartão numa linha (a atual, a próxima e a anterior), com a situação (aberta, fechada ou paga); ao tocar, as compras agrupadas por dia, com filtro por categoria e por tag.
- **Histórico**: uma métrica por vez (despesas, receitas, sobra ou uma categoria), em 12 meses contra os 12 anteriores, por ano desde 2019 ou o mesmo mês em cada ano, mais os dois comparativos do mês atual.
- **Futuro**: a projeção de saldo e uma tabela dos próximos meses.
- **Pizza**: não faz falta. Por categoria e por tag ficam só barras e listas, e não entra o grupo exclusivo "natureza do gasto"; o [ADR 0006](../../../docs/adr/0006-varias-categorias-e-um-item-do-planejamento.md) vale como está.
- **Projeção de saldo**: a soma das contas no fim de cada mês, com o realizado no passado e **duas linhas** daqui para frente: (1) o saldo de hoje mais os previstos (recorrências e parcelas); (2) a mesma linha descontando, em cada mês, o que ainda falta de cada item do planejamento (o planejado menos o realizado e o previsto, quando positivo). O protótipo simplificou o cartão pelo mês da fatura; na v1 o saldo segue o pagamento da fatura, como manda o [ADR 0003](../../../docs/adr/0003-compra-no-cartao-conta-no-mes-da-fatura.md).

Termos novos no [glossário](../../../GLOSSARY.md): **Fechamento do mês** (para não confundir com o fechamento da fatura) e **Projeção de saldo**.

## Comments

**2026-10-25, protótipo pronto para a reação do casal.** Branch `prototipo/dashboards`, pasta `.scratch/v1-substituir-mobills/prototipos/11/`: `dashboards.html` (abre com dois cliques) e `README.md` (como abrir e o que observar). Também publicado como página privada do dono: https://claude.ai/artifact/9V4EcQKeNwRnguNraGRpDd (`#A`, `#B`, `#C` no fim do endereço).

Três variações, trocadas pela barra preta no rodapé:

- **A, Painel do mês:** uma página rolando, com fechamento (meses passados), resumo, itens do planejamento, "a escolher", cartões numa linha que abre as compras, barras por categoria, tag e pessoa, comparação com o mês anterior e com o mesmo mês do ano passado, 12 meses, anos e projeção de saldo.
- **B, App com abas:** Hoje ("ainda dá para gastar", a escolher, atrasados, fatura), Mês (fechamento em texto corrido, itens, ranking com os lançamentos numa folha), Cartões, Histórico (uma métrica por vez) e Futuro.
- **C, Planilha do ano:** categorias, tags, pessoas ou cartões por 12 meses mais 3 futuros (ou por ano, 2019 a 2026), células coloridas contra o planejado e lançamentos ao clicar.

A e B têm o experimento da pizza por natureza do gasto (grupo exclusivo); C não tem pizza. A projeção mostra duas regras lado a lado ("só com os previstos" e "previstos + planejamento"), porque a regra ainda está em aberto no mapa.

Falta: o dono e a esposa reagirem; depois, o veredito (variação escolhida ou mistura, se a pizza faz falta, regra da projeção) vai em `## Answer`.

**2026-10-25, reação do casal.** Gostaram da variação B, mas sentiram falta do comparativo mês a mês da A. A comparação entrou na aba Mês da B, numa versão compacta que cabe no celular (commit `89b5b32` da branch do protótipo). A pizza por natureza não faz falta; a projeção fica com as duas linhas. Veredito em `## Answer`.

