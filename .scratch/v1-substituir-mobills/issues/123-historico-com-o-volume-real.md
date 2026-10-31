# Histórico com o volume real: medir a lista inteira na tela

Type: task
Status: resolved
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

- [x] Banco com o volume do histórico real (o gerador ou o importador usado no 112) e um celular mais lento simulado (CPU throttling do Chromium)
- [x] Medir o tempo até o Histórico mostrar a lista, separando a leitura, a gravação no IndexedDB (uma por leitura, em fila) e o render
- [x] Se passar do aceitável, propor o caminho (lista em páginas, janela de meses, virtualização) como decisão do dono (`ready-for-human`), com os números

## Resultado

Passa do aceitável, e o histórico real não cabe: a decisão foi para o [ticket 124](124-historico-sem-a-lista-inteira.md) (`ready-for-human`), com a tabela e os caminhos. Nada mudou no app, então o prazo de 15 s de `lerAListaInteira` (`web/e2e/sem-internet.spec.ts`) fica até o 124 virar implementação.

- **Laço de medida**: `web/e2e/medir-historico.ts` (instruções no topo). Banco do gerador do ticket 112 (`medir_busca.gerar`), Chromium com CPU 4x mais lenta, e o lançamento novo entrando pela API antes do `reload`, como nos testes que falharam. Ele separa a leitura (`GET`, JSON), as gravações e leituras da lista no IndexedDB, as tarefas longas e o trabalho da thread da tela no trace (JS, estilo, layout, pintura, GC).
- **Até mostrar, CPU 4x**: 4,8 s com 1.600 lançamentos, 8,2 s com 3 mil, 16,5 s com 6 mil. Com 11 mil (o histórico real), não terminou em 5 min; com a CPU sem lentidão, 6,3 a 6,9 s. O servidor responde em 0,1 a 0,5 s.
- **Onde vai o tempo**: render e commit do React da lista inteira, depois layout, estilo e GC (perfil de CPU num build sem minificação: em 9 s de recarga com 11 mil, 4,8 s são do React). A gravação no IndexedDB leva de 1 a 3,5 s até o commit. Leitura e JSON pesam pouco.
- **Hipóteses testadas**: (1) releitura em cascata da lista guardada, 54 leituras por abertura. A mudança baixou para 6 leituras, mas quase não mudou o tempo (4,8 → 4,2 s; 16,5 → 17,7 s) e foi desfeita. (2) Render da lista inteira: confirmada, é a maior parte do tempo. (3) Tamanho da resposta: 700 bytes por lançamento, 7,3 MB com o histórico real, acima dos 6 MB da resposta da Lambda. (4) Gravação na fila atrás das leituras: existe (até 3,5 s), mas não é o principal.
- **Medir com o `getByRole` engana**: a primeira versão do laço esperava com `getByRole(...).filter(...)`, que percorre os milhares de itens e dobrava o tempo medido (10 a 14 s com 1.600). Isso explica parte das falhas dos testes de 5 s no banco local cheio.
