# Acabamento visual do app: links, barra lateral, tipografia e espaçamento

Type: task
Status: resolved
Blocked by: —
Skills: `prototype`, `grilling`, `artifact-design`; apoio: `implement`, `run`. HITL: o visual depende de decisão do dono.
Modelo recomendado: Opus
Effort recomendado: high
Issue: #531
Origem: relato do dono (07/11), com capturas da web e do celular: a tela parece inacabada, com textos que parecem hiperlinks e sem formatação, e a web "quebrada". Nenhum ticket do mapa cobre a aparência: o [ticket 31](31-pwa-instalavel-e-casca-das-telas.md) entregou só a casca funcional.

## O problema

Achados em `web/src/estilo.css` (folha única de ~1300 linhas):

- Não há regra para `a`, só para `a.botao`: "Configurações", "Contas e categorias", "Modelo padrão" ficam com o azul/roxo e o sublinhado padrão do navegador, fora da paleta do app.
- Na tela larga, `.abas` tem `height: 100dvh` e as abas se distribuem pela altura inteira: "Hoje", "Mês", "Cartões", "Histórico" e "Futuro" ficam espalhadas e o bloco de "Hoje" parece vazio.
- Sem sistema de tipografia, espaçamento, botões e cartões; cada tela se vira com regras soltas.
- Fora do CSS, mas visto nas capturas: a web mostrava "Sem conexão" e o celular "API no ar". Verificar se era só a API indisponível naquele momento; se não for, abrir ticket à parte.

## O que construir

Decidir com o dono a direção visual (protótipo) e aplicar: estilo de link, barra lateral da tela larga, escala de tipografia e espaçamento, botões e cartões comuns, revisão tela a tela (Hoje, Mês, Cartões, Histórico, Futuro, Configurações, Contas e categorias, lançamento). Sem mudar regra de negócio.

## Checklist

- [x] Grilling com o dono: referência visual, o que incomoda mais, escopo da primeira rodada (três rodadas, em `## Comments`)
- [x] Protótipo (`prototype`) da casca e de duas telas, aprovado pelo dono (branch `prototipo/204-acabamento-visual`)
- [x] Estilo de link e de barra lateral corrigidos na web e no celular
- [x] Tipografia, espaçamento, botões e cartões em tokens no `estilo.css`
- [x] Revisão tela a tela com capturas antes e depois (https://claude.ai/artifact/K6BX5MWp5ZJt35VQRCGkqG); specs e verificações do projeto verdes; PR para `main`

## Comments

### 08/11: grilling, rodada 1

Decidido com o dono:

- **Tema**: claro e escuro automáticos, pela preferência do sistema, os dois validados no protótipo; sem botão de troca nesta rodada.
- **Prioridade**: (1) links com cara de hiperlink, (2) barra lateral espalhada na web, (3) topo poluído, (4) ritmo de espaçamento, cartões e botões.
- **Links de navegação no meio das telas** ("Contas e categorias", "Modelo padrão", "Configurações", "Favoritos") viram linhas de menu com seta ›; links dentro de frases ficam na cor de destaque, sublinhados só no hover/foco.
- **Escopo**: um PR com os tokens, a casca, os links, o topo e uma passada de CSS e marcação em todas as telas do ticket; mudança maior numa tela (reorganizar conteúdo, gráficos novos) vira ticket à parte.
- **Protótipo**: página HTML publicada como Artifact, com a casca, Hoje e Mês.

Em aberto, para o dono escolher no protótipo: direção visual (Q1), fonte (Q2), topo (Q6) e ícones das abas (Q7). Protótipo: https://claude.ai/artifact/Cdtk9HdMjMpn1TWcc9ymAQ (direções A sóbrio com cartões, B minimalista plano, C painel de banco, D denso; fontes sistema, Inter, Manrope, IBM Plex Sans, Nunito Sans, Source Sans 3; topo atual, enxuto, título da tela, avatar; abas só texto, contorno, ativa preenchida, só ícone, com botão +).

Fatos levantados:

- "Sem conexão" × "API no ar": sem diferença de código entre web e celular; o indicador trata qualquer falha como "Sem conexão" e só verifica ao abrir. Virou o [ticket 205](205-indicador-da-api-sem-conexao-enganoso.md).
- Capturas "antes" de todas as telas (celular e larga) feitas sobre a base local; problemas visuais vistos, que entram neste ticket: no celular, Mês tem 601 px de largura (o `<span class="oculto">` do cabeçalho da tabela de itens escapa do `.rolagem` sem `position: relative`, `web/src/mes/TelaDoMes.tsx:164`); barras de progresso de Hoje no azul do navegador; nenhuma aba ativa em Novo lançamento; fileiras de chips cortadas sem indicação de rolagem; botões de ação repetidos em cada linha (Histórico, Contas e categorias, fatura); eixo do gráfico do Futuro repete os meses sem o ano; tabela "Próximos meses" sem sinal de rolagem lateral; fatura com o resumo em lista de rótulo e valor muito alta.
- Fora do visual, viraram ticket: [206](206-sugeridos-contam-parcelas-como-usos.md) (Sugeridos conta parcelas como usos) e [207](207-historico-abre-com-previstos-distantes.md) (Histórico abre com previstos de dois anos à frente).

### 08/11: grilling, rodada 2

Escolhido no protótipo: **direção C · Painel de banco**, fonte **Inter** (baixada com o app, para funcionar offline), topo **avatar com menu** e abas **com botão +**.

Decidido em seguida:

- **Faixa verde**: no celular, o topo verde aparece em todas as telas; a faixa com o número principal fica só em Hoje (ainda dá para gastar), Mês (despesas × planejamento), Cartões (limite usado) e Fatura (total e situação). As outras telas têm topo verde e conteúdo em cartões.
- **Menu do avatar**: e-mail, Configurações, Contas e categorias, Favoritos e Sair; sem engrenagem. Na tela larga o avatar também fica no topo, sem nada no pé da barra lateral.
- **Botão +**: abre direto o Novo lançamento, aparece em todas as abas e some dentro do lançamento; na tela larga é o botão "Novo lançamento" no alto da barra lateral.
- **Ações por linha**: tocar na linha abre o item, e um botão ⋯ reúne as outras ações (Histórico, Contas e categorias, Fatura, itens do Mês). Só as ações de confirmar (Confirmar/Ajustar nas contas da semana) ficam visíveis.
- **Aprovação final** no protótipo atualizado (Hoje e Mês) antes de implementar.

Em aberto: Q11, atalhos da faixa em Hoje. O dono pediu para ver as opções; o protótipo (versão 2) mostra redondos (Favoritos, Fatura, Contas e categorias), pílulas com informação, os do 1º protótipo e sem atalhos.

### 08/11: grilling, rodada 3

Q11: **pílulas com informação** na faixa de Hoje, com uma opção em Configurações para desligar (aí a faixa fica sem atalhos). Hoje já tem a grade de Favoritos (`web/src/hoje/GradeDeFavoritos.tsx`), então o protótipo (versão 3) compara a escolha com "pílulas com os favoritos" (cada favorito vira pílula e a grade sai). Em aberto: Q17 a Q20 (onde guardar a preferência, o controle em Configurações, qual das duas pílulas, o dado da pílula de contas).

Respostas (todas aceitas):

- **Q17**: a preferência dos atalhos fica **neste aparelho** (armazenamento do navegador/PWA), sem backend. Sincronizar entre aparelhos, se um dia quiser, é outro ticket.
- **Q18**: Configurações ganha a seção **"Tela Hoje"** com o interruptor **"Atalhos na faixa verde"**, ligado por padrão.
- **Q19**: **pílulas com os favoritos**: cada favorito é uma pílula na faixa (título e valor; tocar abre o lançamento preenchido), seguida de "Fatura" (valor, cartão e vencimento da fatura que vence; sem fatura, "Cartões") e "Contas e categorias". A grade de Favoritos sai do corpo de Hoje enquanto os atalhos estiverem ligados e volta quando desligados.
- **Q20**: a pílula de contas mostra **"N contas"**.

Protótipo aprovado nesta forma (versão 3). Próximo passo: implementar.

### 08/11: implementação

- Casca: topo verde no celular (branco na tela larga) com a lupa e o menu da conta; abas com ícones de linha; botão + no meio da barra (no alto da lateral na tela larga), que some nas telas de lançar.
- Inter embutida no build (`web/src/fontes/`, licença OFL), cacheada pelo service worker com o resto da casca.
- Faixa verde em Hoje (ainda dá para gastar, trilho e atalhos), Mês (navegação e despesas × planejamento; no mês passado, o fechamento), Cartões (limite usado de cada cartão) e Fatura (total, vencimento, a pagar). O resto em cartões.
- Atalhos da faixa: favoritos, fatura que vence (ou cartões) e contas; interruptor "Atalhos na faixa verde" em Configurações › Tela Hoje, guardado no aparelho (`web/src/hoje/atalhosDaFaixa.ts`). Teste: `web/e2e/atalhos-da-faixa.spec.ts`.
- Menu da linha (⋯) em Histórico, Fatura, itens do Mês e Contas e categorias; tocar na linha abre o item. Os testes e2e abrem o ⋯ antes da ação.
- Corrigidos da lista das capturas: Mês com 601 px no celular, barras de progresso azuis, fileiras de fichas sem sinal de rolagem (somem na borda enquanto há mais), eixo do Futuro sem o ano (e rótulos sobrepostos no celular), tabela sem sinal de rolagem lateral (sombra na borda).
- Por decisão (Q14), Novo lançamento não marca aba: o + some lá dentro.
- Sobras registradas no [ticket 208](208-acabamento-visual-sobras.md). Vocabulário novo no `GLOSSARY.md` (Telas).
- Verificações: `tsc` e build limpos; a suíte e2e inteira (333 testes) rodou num banco limpo: 331 passaram e as 2 falhas (o ⋯ de uma linha arquivada ficava embaixo da linha seguinte) foram corrigidas e passam.
