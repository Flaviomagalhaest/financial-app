# Fluxo de lançamento rápido

Type: prototype
Status: claimed
Blocked by: 04, 05
Skills: `prototype` (HITL: o dono e a esposa reagem); apoio: `run`
Modelo recomendado: Opus
Effort recomendado: medium
Trello: ari:cloud:trello::card/workspace/598b72bf7efc694a04666f1f/6add2e71c067b15ef2365140
Origem: traçado do [mapa V1 que substitui o Mobills](../map.md)

## Question

Como é a jornada de registrar um lançamento em poucos segundos no celular?

Protótipo de UI com variações bem diferentes entre si, para o dono e a esposa reagirem: ordem dos campos (valor primeiro?); escolha de conta ou cartão; categorias (uma ou mais), tags e pessoa; sugestão automática de categorias e tags pela descrição; favoritos e "repetir último"; aviso de planejamento ("Alimentação: 82% do planejado") e a escolha do item do planejamento quando duas categorias do lançamento têm item, pré-selecionada e trocável com um toque, conforme o [ticket 04](04-categoria-unica-ou-so-tags.md); lançamento parcelado e recorrente. Inclui a confirmação de um previsto pelas contas da semana, em um toque, com valor e data preenchidos e editáveis (o salário), conforme o [ticket 05](05-ciclo-de-vida-do-lancamento-futuro.md).

O app é uma PWA ([ticket 08](08-plataforma-do-cliente.md)): no Android, o toque longo no ícone abre direto o novo lançamento; no iPhone não há atalho, então a jornada começa ao abrir o app.

## Checklist

- [ ] Protótipo descartável numa branch `prototipo/lancamento-rapido`, com dados fictícios
- [ ] Ponteiro para a branch e veredito (a pergunta e o que ela decidiu) em `## Answer`
