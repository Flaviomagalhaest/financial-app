# Sem internet de verdade: rede que não responde e tempo limite

Type: task
Status: ready-for-agent
Blocked by: —
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #156
Origem: [ticket 33](33-lancamento-sem-internet-fila-e-envio.md) (revisão: o "precisa de internet" usa `navigator.onLine`, que diz "online" num Wi-Fi sem saída, como o do subsolo do mercado, e as chamadas da camada de dados não têm tempo limite: uma resposta que nunca chega segura a fila e a leitura)

## O que construir

A camada de dados (`web/src/dados/`) decide "sem internet" também pela última chamada que falhou ou demorou, não só pelo `navigator.onLine`, e toda chamada dela (leituras, lote da fila, também no service worker) tem um tempo limite. Sem resposta no tempo, a leitura mostra a resposta guardada com "atualizado às" e o envio fica para a próxima vez, como sem rede.

## Checklist

- [ ] Tempo limite nas chamadas de `web/src/dados/` (tela e `segundoPlano.ts`); o valor é provisório: entra em `config/valores-iniciais.json` e o dono confirma
- [ ] Estado de conexão que junta `navigator.onLine` e a última falha, usado pelo "precisa de internet" (`useConexao`)
- [ ] Teste de navegador com uma rota que nunca responde: a tela mostra a resposta guardada e o lançamento fica não enviado até a rede voltar
- [ ] Verificações do projeto rodando e PR aberto para `main`
