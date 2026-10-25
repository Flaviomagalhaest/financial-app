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

- [x] Protótipo descartável numa branch `prototipo/lancamento-rapido`, com dados fictícios
- [ ] Ponteiro para a branch e veredito (a pergunta e o que ela decidiu) em `## Answer`

## Comments

- Protótipo pronto na branch `prototipo/lancamento-rapido` (`.scratch/v1-substituir-mobills/prototipos/10/lancamento-rapido.html`, abre direto no navegador) e publicado como página privada para abrir no celular: https://claude.ai/artifact/1tatyJxeaPWjusymBge8uT. A barra de baixo troca a variante (ou `#A`, `#B`, `#C` no fim do endereço) e o seletor de cima simula a entrada pelo atalho do Android (abre direto o novo lançamento) ou pela abertura do app no iPhone (começa na tela inicial). Falta o veredito do dono e da esposa para o `## Answer`.
  - **A. Valor primeiro**: o valor sai de um teclado na tela; conta e categorias são fileiras de toque logo abaixo; descrição, tags, pessoa, data, parcelado e recorrente ficam numa folha "Detalhes". "Repetir último" aparece enquanto o lançamento está vazio. Contas da semana num aviso da tela inicial.
  - **B. Descrição primeiro**: digita "o que foi" e o histórico sugere a descrição já com categorias, conta, tags e pessoa; o lançamento vira uma frase ("Gastei R$ 231,40 em Mercado, no Nubank cartão, hoje, do casal") em que cada parte se troca com um toque. Favoritos e "repetir último" na tela inicial, com a caixa de descrição no topo.
  - **C. Atalhos e passo a passo**: a tela inicial é contas da semana (confirmar em um toque, "Ajustar" para valor e data) e uma grade de favoritos e "repetir último", que abrem uma folha só com o valor (dois toques). O lançamento do zero é um passo a passo: quanto, em quê, de onde, confere.
  - Nas três: aviso de planejamento com o antes e o depois ("Mercado: 82% → 105%"), contando no mês da fatura para compras no cartão ([ADR 0003](../../../docs/adr/0003-compra-no-cartao-conta-no-mes-da-fatura.md)); com Restaurante + Viagem, as duas com item, vem a última escolha pré-selecionada e troca com um toque ([ADR 0006](../../../docs/adr/0006-varias-categorias-e-um-item-do-planejamento.md)); parcelado (valor total ou da parcela) e recorrente (estimado pede confirmação, fixo pode ser automático) ([ADR 0004](../../../docs/adr/0004-previsto-e-situacao-do-lancamento.md)). O painel "Estado do protótipo" abaixo do celular mostra o rascunho e o que foi salvo.
  - Perguntas para a reação: qual variante é mais rápida no dia a dia; valor primeiro ou descrição primeiro; contas da semana e favoritos na tela inicial ou num aviso; a escolha do item do planejamento no aviso fica clara; o que pegar de cada uma.
