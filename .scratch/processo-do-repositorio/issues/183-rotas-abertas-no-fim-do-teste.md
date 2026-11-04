# Rotas dos testes de navegador que leem do servidor ficam abertas quando o teste acaba

Type: task
Status: claimed
Blocked by: —
Skills: `diagnosing-bugs`; apoio: `tdd`, `run`
Modelo recomendado: Sonnet
Effort recomendado: low
Issue: #453
Origem: [ticket 178](178-testes-de-navegador-tres-execucoes-verdes-na-main.md), falha do CI do PR #451 (`parcelamento.spec.ts`, "a tela do parcelamento mostra a mudança nas parcelas que uma recusa parou no meio").

## O problema

Uma rota (`page.route` ou `context.route`) com `await rota.fetch()` e depois `resposta.json()` falha com `apiResponse.json: Response has been disposed` quando uma leitura ainda está no handler no fim do teste: o fechamento do contexto descarta a resposta. A tela e o service worker leem a mesma lista, então uma das leituras pode chegar depois de a asserção passar. No 178, esse teste foi corrigido com `await page.context().unrouteAll({ behavior: "wait" })` no fim (prova: um pedido extra no handler com 20 ms entre o `fetch` e o `json` dava o erro do CI, 3 de 3; com o `unrouteAll`, 3 de 3 verdes).

Arquivos com `rota.fetch()` e sem `unrouteAll` no teste: `cartoes-cadastro`, `conflito`, `aviso-de-planejamento`, `lancamentos`, `contas-da-semana`, `armazem`, `resposta-perdida` (e conferir os de `recorrencia`, `recorrencia-mudar`, `sem-internet` e `parcelamento`, que têm `unrouteAll` em parte dos testes).

## Checklist

- [ ] Em cada teste com rota que busca do servidor, `unrouteAll({ behavior: "wait" })` no fim (ou um ajudante comum)
- [ ] Prova com a injeção do 178 num dos testes trocados: vermelho sem a mudança, verde com ela
