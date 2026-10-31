# Histórico com o volume real: medir a lista inteira na tela

Type: task
Status: claimed
Blocked by: —
Skills: `diagnosing-bugs` (ramo de desempenho: medir antes); apoio: `run`
Modelo recomendado: Opus
Effort recomendado: medium
Issue: #272
Origem: [ticket 120](120-testes-sem-internet-intermitentes.md) (31/10). Num banco local com duas rodadas da suíte (uns 1.600 lançamentos do usuário de teste, com parcelamentos de 300 parcelas), o Histórico levou 6,1 s para mostrar um lançamento novo depois do `reload`, e os testes de `pessoa-e-repetido.spec.ts` e `favoritos.spec.ts`, que esperam 5 s, falharam.

## O que medir

O app lê a lista inteira (`GET /api/lancamentos`, sem página) e o Histórico desenha todos os itens. O [ticket 112](112-busca-desempenho-e-indice.md) mediu o servidor com o histórico desde 2019 (11 mil lançamentos, o volume do Mobills), mas não o aparelho: o JSON inteiro, o IndexedDB guardando a lista a cada leitura e a tela com milhares de itens.

No CI, o teste "a rede volta, mas a lista não chega antes do envio" (`web/e2e/sem-internet.spec.ts`) passou de 5 s pelo mesmo motivo. Cada leitura da lista grava ela inteira de novo, e as gravações vão uma de cada vez. O envio espera a dele, e a leitura do Histórico sem internet espera atrás delas. O teste ganhou 15 s nessas duas checagens (`lerAListaInteira`); se a medida levar a uma mudança, o prazo dele volta ao padrão.

## Checklist

- [ ] Banco com o volume do histórico real (o gerador ou o importador usado no 112) e um celular mais lento simulado (CPU throttling do Chromium)
- [ ] Medir o tempo até o Histórico mostrar a lista, separando a leitura, a gravação no IndexedDB (uma por leitura, em fila) e o render
- [ ] Se passar do aceitável, propor o caminho (lista em páginas, janela de meses, virtualização) como decisão do dono (`ready-for-human`), com os números
