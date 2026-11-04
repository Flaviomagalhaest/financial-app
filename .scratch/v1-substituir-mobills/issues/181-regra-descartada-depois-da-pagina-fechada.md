# Regra descartada depois da página fechada no meio do envio

Type: task
Status: claimed
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

- [ ] Teste de navegador: regra com a aba fechada no meio do envio, e ao reabrir ela não se descarta (ou o descarte a tira do servidor)
- [ ] A marca da regra continua só valendo quando a rede existe (`navigator.onLine`), como hoje
