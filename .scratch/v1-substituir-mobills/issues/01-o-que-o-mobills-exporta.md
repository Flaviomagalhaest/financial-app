# O que o Mobills exporta

Type: research
Status: ready-for-human
Blocked by: 14
Skills: `research` (AFK, em sub-agente)
Modelo recomendado: Sonnet
Effort recomendado: medium
Trello: ari:cloud:trello::card/workspace/598b72bf7efc694a04666f1f/6add2e6b9e6abcd8c135ad24
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

## Answer

Resposta **parcial**. Achados e lacunas na branch `research/mobills-exportacao` (arquivo `.scratch/v1-substituir-mobills/research/mobills-exportacao.md`, commit `e4ef538`), enviada sem PR e sem tag.

A central de ajuda (`ajuda.mobills.com.br`, que redireciona para o Zendesk) responde 403 com o desafio da Cloudflare, então a fonte que descreve a exportação não foi lida. Só o site institucional, o blog oficial e os termos de uso foram lidos.

- **Plano:** indício de que a exportação é do Premium (post oficial do blog); a página de planos não cita exportação. Não confirmado.
- **Formatos:** o blog oficial diz "Excel, PDF ou CSV", sem detalhe técnico. OFX aparece só como formato de importação.
- **Termos de uso:** não citam exportação, backup nem API.
- **Portabilidade:** o aviso de privacidade garante, pela LGPD, o pedido de migração dos dados ao encarregado; formato, prazo e escopo não estão publicados.
- **Não encontrado na fonte oficial:** campos de cada exportação (lançamentos, transferências, contas, cartões e faturas, parcelas, recorrências, planejamento), limite de período, backup completo, API e limitações conhecidas.

Por isso este ticket **não** fecha os que dependem dele ([Categoria única ou só tags](04-categoria-unica-ou-so-tags.md), [Exportar o Mobills e medir o histórico](07-exportar-o-mobills-e-medir-o-historico.md)). A lacuna virou [Ler a central de ajuda do Mobills e fazer uma exportação de teste](14-ler-a-central-de-ajuda-e-exportar-de-teste.md); este ticket volta a andar quando ele fechar.
