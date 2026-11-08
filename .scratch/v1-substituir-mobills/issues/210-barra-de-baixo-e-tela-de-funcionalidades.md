# Barra de baixo com 2 abas, +, 2 abas e uma tela de funcionalidades (decisão)

Type: prototype
Status: claimed
Blocked by: —
Skills: `grill-with-docs` (`grilling`, `domain-modeling`), `prototype`, `artifact-design`. HITL: o desenho e os nomes são decisão do dono.
Modelo recomendado: Opus
Effort recomendado: high
Issue: #549
Origem: pedido do dono (08/11), com captura do app do banco dele como referência: a barra de baixo do celular tem seis posições (Hoje, Mês, +, Cartões, Histórico, Futuro) e fica desequilibrada. O dono quer 2 abas, o +, 2 abas, e uma tela à parte para as funcionalidades menos usadas, que possa crescer nas próximas versões (planejamento e histórico de viagens, planejamento de investimentos com as características de cada produto etc.).

## Já decidido pelo dono

- **Celular**: a barra de baixo fica Hoje, Mês, +, Cartões e um quinto item que abre uma tela de funcionalidades. Na referência (app do banco), é um botão em destaque à direita que abre uma grade de cartões grandes, cada um com ícone e nome, com uma busca no alto.
- **Histórico** e **Futuro** saem da barra e vão para essa tela.
- **Web (tela larga)**: fica como está, com a barra lateral. As funcionalidades novas entram nela, uma a uma, quando existirem; a tela larga não precisa da tela de funcionalidades.

## Decisões para o dono

- [ ] Nome do quinto item e da tela (ex.: "Mais", "Explorar", "Funcionalidades") e o termo no `GLOSSARY.md`
- [ ] Ícone e destaque do quinto item (botão cheio como na referência, ou igual às outras abas, já que o + é o destaque da barra)
- [ ] O que entra na tela agora: só Histórico e Futuro, ou também Busca, Favoritos, Contas e categorias e Configurações (hoje no menu da conta e na lupa)
- [ ] Busca no alto da tela (como na referência): ela filtra as funcionalidades ou abre a busca de lançamentos? Com poucas opções, faz falta?
- [ ] Dentro de Histórico ou Futuro, qual item da barra fica marcado (o quinto, provavelmente) e como se volta à grade
- [ ] A busca de lançamentos hoje "é da aba Histórico" (`web/src/casca/Casca.tsx`): continua assim ou passa a ser do quinto item
- [ ] Os endereços `#/historico` e `#/futuro` continuam funcionando (favoritos do navegador, atalhos)
- [ ] Protótipo (`prototype`, página publicada como Artifact) da barra nova e da tela de funcionalidades, claro e escuro, aprovado pelo dono; branch `prototipo/210-barra-de-baixo`
- [ ] Decisões gravadas em `## Comments`, termo novo no `GLOSSARY.md` (seção Telas) e o [ticket 211](211-aplicar-a-nova-barra-de-baixo.md) atualizado com o que foi decidido

## Contexto do código

- As abas vêm de `ABAS` em `web/src/casca/rota.ts` e a barra é montada em `web/src/casca/Casca.tsx` (`nav.abas`); a ordem no celular sai do CSS (`.abas a:nth-child(...)` em `web/src/estilo.css`), com a quebra para barra lateral em `@media (min-width: 900px)`.
- `web/e2e/pwa.spec.ts` confere as cinco abas pelo nome.
- O visual atual (direção "Painel de banco", Inter, + no meio) foi decidido no [ticket 204](204-acabamento-visual-do-app.md).
