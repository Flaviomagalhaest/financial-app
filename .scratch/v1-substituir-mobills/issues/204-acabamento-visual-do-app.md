# Acabamento visual do app: links, barra lateral, tipografia e espaçamento

Type: task
Status: ready-for-human
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

- [ ] Grilling com o dono: referência visual, o que incomoda mais, escopo da primeira rodada
- [ ] Protótipo (`prototype`) da casca e de duas telas, aprovado pelo dono
- [ ] Estilo de link e de barra lateral corrigidos na web e no celular
- [ ] Tipografia, espaçamento, botões e cartões em tokens no `estilo.css`
- [ ] Revisão tela a tela com capturas antes e depois; specs e verificações do projeto verdes; PR para `main`
