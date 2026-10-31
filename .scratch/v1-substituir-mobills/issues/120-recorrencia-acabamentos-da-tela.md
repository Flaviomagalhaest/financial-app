# Recorrência: acabamentos da tela da recorrência

Type: task
Status: ready-for-agent
Blocked by: 96
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #262
Origem: [ticket 96](96-recorrencia-mudar-pela-tela-e-sem-internet.md) (o que a tela `#/recorrencia/<lançamento>` deixou de fora e a revisão dela)

## O que construir

A tela da recorrência (`web/src/lancamentos/TelaDaRecorrencia.tsx`) muda "daqui para frente" descrição, valor, fixo ou estimado, automático, conta, categorias, tags, pessoa e calendário pela fila (`alterar_recorrencia`). Faltam duas coisas da história 90 ("em qualquer campo") que a tela de lançamento já tem, e a revisão do 96 apontou a repetição com a tela do parcelamento.

## Checklist

- [ ] Escolha do item do planejamento (`item_categoria_id` na `AlteracaoDeRecorrencia`): a tela não pergunta; repetir o `AvisoDePlanejamento` da tela de lançamento (`useAvisoDePlanejamento` em `web/src/dados/index.ts`), como o [ticket 118](118-parcelamento-acabamentos-da-tela-de-correcao.md) faz no parcelamento
- [ ] Criar tag nova na mudança "daqui para frente": hoje ela só marca e desmarca as tags que já existem
- [ ] Os seletores de categorias, tags e pessoa e o `mesmos` estão repetidos em `TelaDaRecorrencia.tsx` e `TelaDoParcelamento.tsx`: juntar num componente só se o 118 mexer nos mesmos seletores
- [ ] Testes de navegador em `web/e2e/recorrencia-mudar.spec.ts`
- [ ] Verificações do projeto rodando e PR aberto para `main`
