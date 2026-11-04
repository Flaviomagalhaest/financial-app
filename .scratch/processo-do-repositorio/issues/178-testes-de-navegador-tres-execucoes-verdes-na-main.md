# Testes de navegador: três execuções verdes na main e as próximas falhas com trace

Type: task
Status: claimed
Blocked by: 15
Skills: `diagnosing-bugs`; apoio: `run`
Modelo recomendado: Opus
Effort recomendado: medium
Issue: #440
Origem: o que o [ticket 15](15-testes-de-navegador-instaveis-no-ci.md) não pôde fechar na branch: a verificação na `main` só vem depois do merge, e um modo de falha antigo ficou sem causa.

## O que fazer

Depois do merge do 15, rodar o `verificar` da `main` três vezes seguidas (workflow `CI`, "Re-run all jobs" no último push da `main`, sem mudar nada). Cada falha deixa trace e vídeo no artefato `testes-com-navegador` da execução: baixar, abrir com `npx playwright show-trace`, achar a causa e consertar (sem `retries` nem pular o teste).

Modo de falha ainda sem causa: `parcelamento.spec.ts:445` nos CIs da `main` de 02/11 (execuções 41467481476 e 41469168507) terminava com a antecipação não aplicada (as 5 parcelas seguintes ainda previstas, de R$ 100,00) e a fila vazia. O 15 não o reproduziu: 25 repetições sozinho e com a CPU saturada, leitura da fila atrasada, e a corrida que achou (a rede cair antes de as parcelas chegarem) falha em outro ponto. Parte da causa daquela época era a releitura que marcava a rede como sem resposta, corrigida no 165.

## Checklist

- [ ] Três execuções seguidas do `verificar` verdes na `main`
- [ ] Cada falha que aparecer: causa achada pelo trace do artefato e consertada, ou registrada aqui com o trace
- [ ] `parcelamento.spec.ts:445` com a antecipação não aplicada: causa achada, ou nenhuma ocorrência nas execuções acima

## Diagnóstico do `parcelamento.spec.ts` (antecipação não aplicada)

- O log da execução 41467481476 mostra o teste passando por `chaves.length > 0` e pela fila vazia, e falhando na leitura do servidor: as 5 parcelas seguintes ainda `previsto`, `versao: 1`. O lote com a antecipação chegou à rota do teste, mas nada foi gravado.
- A conferência da fila vazia era `getByTestId("nao-enviados")` com contagem 0. O `AvisoDaFila` não aparece antes de `useFilaLida` ler o IndexedDB (começa com `itens: []`), então a conferência passa na hora, logo depois do clique em "Hoje", com a antecipação ainda na fila. Qualquer primeiro envio que não grava (recusa, 401, pedido que não chega ao servidor) vira então a falha do CI, no ponto seguinte.
- Laço: o primeiro envio abortado sem chegar ao servidor, o reenvio atrasado 8 s e `Emulation.setCPUThrottlingRate` 30 no clique em "Hoje": 3 de 3 vermelhos, com o sintoma do CI (`Expected length: 3`, `Received length: 5`). Sem estrangular a CPU, 3 de 3 verdes (a janela é curta); com a CPU estrangulada e o envio original, 3 de 3 verdes (o primeiro envio grava).
- Correção: a fila vazia é conferida no IndexedDB (`filaDoAparelho`), e a resposta do servidor ao envio perdido vai na mensagem das asserções. Com as mesmas injeções, 3 de 3 verdes; sem elas, o teste 10 de 10 e o arquivo inteiro 16 de 16.
- O que faz o primeiro envio não gravar nos CIs de 02/11 ficou sem causa: o código daquela época mudou (165, 174), e o 15 não o reproduziu. Se voltar, a falha para na conferência da fila, com o pedido (e a recusa, se houver) e a resposta do servidor na mensagem.
- A mesma conferência pelo aviso aparece em outros 7 arquivos: [ticket 182](182-fila-vazia-conferida-pelo-aviso-nos-testes.md).

## Execuções da `main`

Desde o merge do 15 (PR #439), as execuções do `verificar` na `main` foram verdes: 446 (41773153844), 447 (41774862545) e 449 (41821249937, tentativa 1). Re-execuções da 449, sem mudar nada:

- tentativa 2: verde (15:12 UTC)

## Falha no CI do PR #451 (execução 41854192551)

- `parcelamento.spec.ts`, "a tela do parcelamento mostra a mudança nas parcelas que uma recusa parou no meio": `apiResponse.json: Response has been disposed`.
- Trace do artefato: a asserção do teste passou; das duas leituras de `/api/parcelamentos` que a rota pegou (tela e service worker), uma foi atendida e a outra ainda estava no handler quando o contexto fechou, descartando a resposta antes do `json()`.
- Laço: um pedido extra pego pela rota no fim do teste, 20 ms ou 60 ms entre o `fetch` e o `json`: o erro do CI 3 de 3. Correção: `unrouteAll({ behavior: "wait" })` no fim do teste; com a mesma injeção, 3 de 3 verdes, e o arquivo 16 de 16.
- O mesmo padrão em outros arquivos: [ticket 183](183-rotas-abertas-no-fim-do-teste.md).
