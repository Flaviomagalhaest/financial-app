# Testes de navegador conferem a fila vazia pelo aviso, que some antes de a tela ler a fila

Type: task
Status: claimed
Blocked by: —
Skills: `diagnosing-bugs`; apoio: `tdd`, `run`
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #450
Origem: [ticket 178](178-testes-de-navegador-tres-execucoes-verdes-na-main.md), causa do modo de falha do `parcelamento.spec.ts` (antecipação sem internet).

## O problema

`AvisoDaFila` (`web/src/lancamentos/AvisoDaFila.tsx`) não aparece enquanto `useFilaLida` não leu a fila do IndexedDB: o estado começa com `itens: []`. Logo depois de trocar de tela, `expect(page.getByTestId("nao-enviados")).toHaveCount(0)` passa na hora, com o pedido ainda na fila. Com a CPU ocupada (CI), a janela cresce. No 178, com `Emulation.setCPUThrottlingRate` 30 e o primeiro envio sem chegar ao servidor, o teste da antecipação passava a conferência da fila e falhava depois, lendo o servidor antes do reenvio (3 de 3 vermelhos). O 178 corrigiu só esse teste, com a fila lida direto do IndexedDB (`filaDoAparelho` em `web/e2e/parcelamento.spec.ts`).

A mesma conferência aparece 25 vezes em 8 arquivos de `web/e2e/` (`conflito`, `recorrencia`, `recorrencia-mudar`, `janela-do-aparelho`, `sem-internet`, `parcelamento`, `contas-da-semana`, `armazem`). Onde o passo seguinte depende de a fila já ter subido, a falha aparece adiante, com outra cara.

## Checklist

- [ ] Uma conferência comum da fila vazia (IndexedDB, como `filaDoAparelho`, ou o aviso só depois de a tela marcar a fila como lida), num módulo de `web/e2e/`
- [ ] Trocar as 25 ocorrências onde a fila vazia é pré-condição do passo seguinte
- [ ] Prova: com a CPU estrangulada (`Emulation.setCPUThrottlingRate`), um teste que hoje passa a conferência com a fila cheia passa a esperar
