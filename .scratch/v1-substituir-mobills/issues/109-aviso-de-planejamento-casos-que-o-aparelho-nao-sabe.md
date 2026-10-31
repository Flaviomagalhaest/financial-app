# Aviso de planejamento: casos que o aparelho ainda não sabe

Type: task
Status: resolved
Blocked by: —
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` se mexer na interface
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #209
Origem: [ticket 52](52-aviso-de-planejamento-ao-lancar.md): casos que o aviso de planejamento deixou de fora ou trata de forma aproximada, achados na implementação e na revisão

## O que construir

O aviso de planejamento (`web/src/dados/aviso.ts`, `useAvisoDePlanejamento` em `web/src/dados/index.ts`, `web/src/lancamentos/AvisoDePlanejamento.tsx`) acertando também estes casos, com teste de tabela ou de navegador para cada um.

## Checklist

- [x] **Criar enviado sem resposta**: o item da fila com `talvezNoServidor` pode já estar no servidor. Se o planejamento guardado foi lido depois de ele chegar, o aviso o conta duas vezes até a fila sair. Hoje `contagensNoAparelho` soma todo item da fila sobre o planejamento guardado — `tentadoEm` na fila e `semContarDeNovo`: planejamento lido depois do envio já traz o criar, e a fila só troca a versão enviada pela do aparelho
- [x] **Cartão arquivado num lançamento não enviado**: `GET /api/cartoes` não traz os arquivados. A compra não enviada num cartão arquivado conta, no aparelho, pelo mês da data, e não pela fatura — o aviso lê `/api/cartoes?arquivados=true`, buscado também ao abrir, com as faturas dos titulares arquivados
- [x] **Mês sem planejamento guardado**: ao abrir, o app guarda o planejamento do mês anterior, deste e do próximo. O previsto com data mais longe, lançado sem internet, mostra "o planejamento de <mês> não está no aparelho". Decidir se basta ou se o aparelho guarda mais meses — decisão: basta. O aparelho segue guardando anterior, atual e próximo; o aviso já diz que o planejamento do mês não está no aparelho, e guardar mais meses custaria mais chamadas a cada abertura por um caso raro
- [x] **Receita**: os textos do item de receita ("Faltam R$ X para o planejado", "R$ X acima do planejado", "Chega ao planejado") não têm teste — `oQueSobra` foi para `aviso.ts` e tem teste de tabela em `web/e2e/aviso.spec.ts`
- [x] **Transferência com categoria** conta no planejamento (história 67), mas a tela de transferência (`TelaDeTransferencia.tsx`) não mostra o aviso. Ela grava direto na API e já precisa de internet — `TelaDeTransferencia` mostra o aviso com a categoria escolhida; teste de navegador em `aviso-de-planejamento.spec.ts`
- [ ] Verificações do projeto rodando e PR aberto para `main`
