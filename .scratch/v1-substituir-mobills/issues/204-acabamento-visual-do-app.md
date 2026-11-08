# Acabamento visual do app: links, barra lateral, tipografia e espaçamento

Type: task
Status: claimed
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

- [ ] Grilling com o dono: referência visual, o que incomoda mais, escopo da primeira rodada (rodada 1 respondida em 08/11; faltam Q1, Q2, Q6 e Q7, que o dono quer ver no protótipo)
- [ ] Protótipo (`prototype`) da casca e de duas telas, aprovado pelo dono
- [ ] Estilo de link e de barra lateral corrigidos na web e no celular
- [ ] Tipografia, espaçamento, botões e cartões em tokens no `estilo.css`
- [ ] Revisão tela a tela com capturas antes e depois; specs e verificações do projeto verdes; PR para `main`

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
