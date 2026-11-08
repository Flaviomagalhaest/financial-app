# Histórico abre com lançamentos previstos de dois anos à frente

Type: task
Status: claimed
Blocked by: —
Skills: `grilling`; apoio: `implement`, `tdd`. HITL: a ordem e o recorte da lista são decisão do dono.
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #535
Origem: [ticket 204](204-acabamento-visual-do-app.md). Nas capturas da base de teste (08/11), com quatro recorrências ativas (Spotify, Netflix, salário, aluguel), a lista do Histórico começa em 11/2028: todos os previstos dos próximos dois anos vêm antes do que aconteceu hoje, e a página tem cerca de 134 mil pixels de altura no celular.

## Problema

A lista em ordem de data decrescente põe o futuro no topo. Quem abre o Histórico procura o que já aconteceu, e os previstos distantes empurram isso para longe. Não é visual (o ticket 204 não muda regra de negócio), é decisão de produto.

## Decisões para o dono

- [ ] O Histórico mostra previstos? Todos, só os do mês, ou nenhum (ficam no Futuro)?
- [ ] Onde a lista começa: hoje, com o futuro acima e recolhido, ou só o passado?
- [ ] A lista carrega tudo ou pagina por mês?
- [ ] Implementar o que for decidido; specs e verificações verdes; PR para `main`
