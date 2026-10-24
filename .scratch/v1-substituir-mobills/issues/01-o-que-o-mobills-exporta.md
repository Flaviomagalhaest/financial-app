# O que o Mobills exporta

Type: research
Status: claimed
Blocked by: 13
Skills: `research` (AFK, em sub-agente)
Modelo recomendado: Sonnet
Effort recomendado: medium
Origem: traçado do [mapa V1 que substitui o Mobills](../map.md)

## Question

Que dados o Mobills deixa exportar, por qual caminho e em que formato?

Levantar:

- onde fica a exportação (app, site) e qual plano do Mobills ela exige;
- os formatos (CSV, XLS, OFX, backup do app) e se há limite de período por exportação;
- os campos de cada coisa exportada: lançamentos (data, valor, descrição, conta, categoria e subcategoria, tags, efetivado ou pendente), transferências, contas e saldos, cartões e faturas (data da compra e fatura em que caiu), parcelas (uma linha por parcela? há vínculo entre elas?), recorrências e planejamento;
- se existe API, backup completo ou outra forma de tirar os dados;
- limitações conhecidas (o que não sai na exportação).

Decisões que esperam por isso: [Categoria única ou só tags](04-categoria-unica-ou-so-tags.md), [Exportar o Mobills e medir o histórico](07-exportar-o-mobills-e-medir-o-historico.md) e a importação do Mobills (ainda no "Not yet specified" do mapa).

## Checklist

- [ ] Fontes primárias: central de ajuda e site do Mobills, termos de uso, a própria tela de exportação quando acessível
- [ ] Achados num único Markdown, cada afirmação com a fonte, numa branch `research/mobills-exportacao` enviada e sem PR
- [ ] Ponteiro para a branch e resumo do achado neste ticket, em `## Answer`
