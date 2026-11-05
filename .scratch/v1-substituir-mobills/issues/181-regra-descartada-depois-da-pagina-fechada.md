# Regra descartada depois da página fechada no meio do envio

Type: task
Status: resolved
Blocked by: —
Skills: `diagnosing-bugs`, `tdd`; apoio: `run`
Modelo recomendado: Opus
Effort recomendado: medium
Issue: #444
Origem: [ticket 173](173-criar-com-a-pagina-fechada-no-meio-do-envio.md). Hipótese lida no código, nunca reproduzida.

## O problema

O ticket 173 mostrou que, com a aba fechada (ou o app morto pelo sistema) com o lote no caminho, `marcarSemResposta` (`web/src/dados/fila.ts`) não roda: na recarga o navegador derruba o pedido e a página ainda vê a falha, mas com a aba fechada não. O criar do lançamento passou a guardar o que leva antes de sair (`guardarOEnviado`), mas a regra (`criar_recorrencia`, `criar_parcelamento`, `antecipar_parcelas`, `alterar_recorrencia`) só recebe `talvezNoServidor` na falha. Ao reabrir, ela segue descartável (`podeDescartar`, `web/src/dados/index.ts`), e descartar tira da fila uma regra que talvez já tenha gerado os previstos ou as parcelas no servidor.

## Para reproduzir

Em `web/e2e/resposta-perdida.spec.ts`, como no caso `"aba fechada"` do ticket 173: crie a recorrência com o lote deixado chegar ao servidor (`rota.fetch()`) e sem resposta, feche a aba, abra outra com a fila presa por `segurarAFila` e veja se "Descartar" aparece e se os previstos ficam no servidor.

## Checklist

- [x] Teste de navegador: regra com a aba fechada no meio do envio, e ao reabrir ela não se descarta (ou o descarte a tira do servidor)
- [x] A marca da regra continua só valendo quando a rede existe (`navigator.onLine`), como hoje

## Resolução

Reproduzido: com a aba fechada no meio do envio, a recorrência já estava no servidor e, ao reabrir, "Descartar" aparecia. A hipótese do ticket se confirmou: sem a falha vista pela página, `marcarSemResposta` não roda e a regra fica sem `talvezNoServidor`.

Antes de o lote sair, `guardarOEnviado` (`web/src/dados/fila.ts`) grava na regra quem a mandou (`enviadaPor`, um id de cada página ou service worker), só com `navigator.onLine`. `talvezGravada` vale para a regra sem resposta e para a que saiu de outro remetente: quem envia segura a trava da fila, então a marca de outro que ficou na fila é de um envio que fechou no caminho. Essa regra não se descarta (`podeDescartar`), a exclusão da recorrência sobe como `excluir_recorrencia`, e o próximo envio a marca com `talvezNoServidor`. A que saiu desta página e espera a resposta segue descartável, como no teste "a recorrência descartada no meio do envio". Sem rede, a falha limpa a marca e a regra continua descartável.

Testes em `web/e2e/resposta-perdida.spec.ts`: "a recorrência criada com a aba fechada no meio do envio (com rede / sem rede), ao reabrir". O primeiro estava vermelho antes da correção. Os outros tipos de regra (`criar_parcelamento`, `antecipar_parcelas`, `alterar_recorrencia`) usam o mesmo caminho, mas o teste de navegador cobre só a recorrência.

A falha de "a recorrência de um lançamento fora da janela do aparelho..." (`recorrencia-mudar.spec.ts`, `Response has been disposed`) também acontece na `main` e é a do [ticket 183](../../processo-do-repositorio/issues/183-rotas-abertas-no-fim-do-teste.md).
