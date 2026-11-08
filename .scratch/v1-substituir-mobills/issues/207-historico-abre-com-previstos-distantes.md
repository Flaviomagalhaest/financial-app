# Histórico abre com lançamentos previstos de dois anos à frente

Type: task
Status: ready-for-agent
Blocked by: —
Skills: `grilling`; apoio: `implement`, `tdd`. HITL: a ordem e o recorte da lista são decisão do dono.
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #535
Origem: [ticket 204](204-acabamento-visual-do-app.md). Nas capturas da base de teste (08/11), com quatro recorrências ativas (Spotify, Netflix, salário, aluguel), a lista do Histórico começa em 11/2028: todos os previstos dos próximos dois anos vêm antes do que aconteceu hoje, e a página tem cerca de 134 mil pixels de altura no celular.

## Problema

A lista em ordem de data decrescente põe o futuro no topo. Quem abre o Histórico procura o que já aconteceu, e os previstos distantes empurram isso para longe. Não é visual (o ticket 204 não muda regra de negócio), é decisão de produto.

## Decisões do dono (08/11)

- [x] Previstos no Histórico: **nenhum**. Ficam no Mês (barra e Ranking, só leitura), na Busca e no Futuro. O previsto atrasado (data até hoje) e o que está na fila (não enviado, recusado, conflito, exclusão) continuam na lista.
- [x] A lista começa em hoje, só o passado.
- [x] Pagina por mês com "carregar mais" (já existe: `useHistoricoMesAMes`; só falta tirar o "futuro vem todo na frente").

## O que falta

Implementação testada e descartada nesta sessão: em `web/src/lancamentos/useHistoricoMesAMes.ts`, filtrar `lancamentos` por `situacao !== "previsto" || data <= hoje() || naoEnviado || recusa || conflito || exclusao` antes de `porMes`, e trocar `futuros + MESES_DE_INICIO + alemDosDeInicio` por `MESES_DE_INICIO + alemDosDeInicio`. Mais um spec novo em `web/e2e/historico-mes-a-mes.spec.ts` (previsto distante fora, atrasado e realizado dentro). Isso passa, mas **quebra 12 specs** que chegam à recorrência e conferem os previstos pelo Histórico: `recorrencia-mudar.spec.ts` (8) e `partes-na-recorrencia.spec.ts` (4). Eles precisam passar a abrir a regra por Contas e categorias (`RecorrenciasAtivas`, link `#/recorrencia/<id>`) e conferir os previstos pela API ou pela Busca.

Atenção ao caminho de gestão: sem os previstos no Histórico, o ⋯ de Recorrência/Parcelamento some da linha futura. A recorrência ainda abre por Contas e categorias; o **parcelamento** e o **previsto avulso** só têm a Busca (que tem Editar, sem ⋯ de Parcelamento). Decidir se a Busca ganha o ⋯ (ou se o parcelamento ganha entrada própria) antes de mesclar.

- [ ] Implementar o filtro e o spec novo
- [ ] Reescrever os 12 specs acima
- [ ] Dar à Busca o caminho para Parcelamento (ou criar ticket próprio)
- [ ] Specs e verificações verdes; PR para `main`
