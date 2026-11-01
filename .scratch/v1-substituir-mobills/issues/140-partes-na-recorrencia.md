# Partes na recorrência

Type: task
Status: ready-for-human
Blocked by: 137
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` nas telas; agora HITL: o dono confirma a mudança de escopo abaixo
Modelo recomendado: Opus
Effort recomendado: high
Issue: #328
Origem: [ticket 94](94-conferir-as-regras-de-estorno-e-ajuste.md): decisões do dono sobre estorno, ajuste de fatura e partes da compra

## O que construir

A despesa recorrente pode ter partes (ex.: um combo de celular e internet numa conta só), guardadas na regra como proporção.

## Checklist

- [x] Cada ocorrência se divide pelas partes na proporção; centavos para a maior parte; o valor estimado do mês se redivide
- [x] Mudar as partes: "só este" (editar o previsto) ou "daqui para frente", que não sobrescreve o previsto editado; a mudança vai pela fila (ADR 0020)
- [ ] O estorno é de uma parte de uma ocorrência: passou para o [138](138-estorno-de-parte-e-de-todas-as-parcelas.md), que faz o estorno de uma parte para toda compra com partes; a ocorrência tem as partes dela, como a compra à vista, e a trava do 137 vale até lá (falta o dono confirmar a mudança de escopo)
- [x] Testes de API e de navegador; verificações do projeto e PR para `main`

## Notas

- Decisões Q38 e Q43 do ticket 94; ADR 0022.

## O que decidir

O que o checklist pedia está feito, menos o estorno de uma parte de uma ocorrência. Confirmar que ele fica no [138](138-estorno-de-parte-e-de-todas-as-parcelas.md), que faz o estorno de uma parte para toda compra com partes: a ocorrência da recorrência tem as partes dela, como a compra à vista, e o mesmo mecanismo serve às duas. Com o sim, este ticket vai para `resolved`; com o não, ele volta para `ready-for-agent`, bloqueado pelo 138.

## Answer

Feito na API, na fila, no backup e nas telas.

- **Modelo**: a regra guarda as partes no valor dela, em `regra_partes`, `regra_parte_categorias` e `regra_parte_tags` (migrations 0066 a 0069, `backend/app/partes_da_regra.py`; o parcelamento do 139 pode usar as mesmas tabelas pelo id). A regra com partes não tem categoria, tag, pessoa nem item próprios, e as partes somam o valor dela (senão 422), só na despesa. Backup na versão 28 do formato, com conversor da 27.
- **Ocorrências**: cada previsto nasce com as partes dele (`lancamento_partes`, id derivado do previsto e da parte da regra), e as somas por categoria, tag, pessoa e item leem as partes, como na compra à vista do 137.
- **Proporção**: `redividir` (`backend/app/partes.py` e `web/src/lancamentos/dinheiro.ts`, presas por `tabelas-de-teste/redivisao-das-partes.json`). Cada parte fica com a parte inteira da conta, e os centavos que sobram vão para a maior (a primeira, no empate). A parte que ficaria sem centavo recusa (422). Mudar o valor do previsto, confirmá-lo com outro valor, corrigi-lo na fatura paga (o formulário do 151 manda as partes na proporção, e não com a diferença na última) ou mudar o valor da regra "daqui para frente" divide as partes de novo.
- **Mudar as partes**:
  - "Só este" é editar o previsto ("Mudar só este mês"): na tela, mudar só o valor redivide as partes, e mexer nelas vale o digitado.
  - "Daqui para frente", na tela da recorrência, divide, muda ou junta as partes da regra (tirar a penúltima devolve a classificação da que ficou). O reajuste refaz os previstos e deixa como está o que alguém mudou à mão.
  - A mudança vai pela fila (ADR 0020) com as partes em `antes`, e dividir ou juntar leva também a classificação própria da regra: se a outra pessoa mudou as partes ou a categoria depois, ela volta recusada ("a regra mudou depois (partes)" ou "(categorias)"). O aparelho mostra a regra com a mudança por cima, também com o valor novo redividido.
  - O previsto que o fim tirou volta com as partes da regra de hoje. Juntar categoria ou tag leva as das partes da regra.
- **Estorno**: a ocorrência é uma compra com partes como a à vista, com as partes dela, e o estorno de uma parte dela é do 138, que ganhou a linha no checklist. Até lá, a trava do 137 recusa o estorno, e um teste a prende.
- **Limites**: a regra guarda as partes no valor dela, então mudanças de valor sucessivas sem mexer nas partes acumulam o arredondamento de cada redivisão (um centavo por vez, na maior). Confirmar com outro valor uma compra **à vista** com partes ainda deixa as partes sem somar o valor; foi para o [154](154-confirmar-compra-a-vista-com-partes.md), com decisão do dono.

Pendências: [153](153-juntar-tag-nas-regras.md) (juntar tag não leva as tags da recorrência nem do parcelamento, defeito anterior achado aqui) e [154](154-confirmar-compra-a-vista-com-partes.md) (confirmar com outro valor a compra à vista com partes). Notas nos tickets [138](138-estorno-de-parte-e-de-todas-as-parcelas.md) e [141](141-favorito-e-sugestao-com-partes.md).
