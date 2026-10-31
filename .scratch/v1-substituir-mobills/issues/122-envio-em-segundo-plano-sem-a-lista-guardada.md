# Envio em segundo plano sem a lista guardada: o enviado some do aparelho

Type: task
Status: resolved
Blocked by: 120
Skills: `diagnosing-bugs`, `tdd`; apoio: `run`
Modelo recomendado: Opus
Effort recomendado: medium
Issue: #271
Origem: [ticket 120](120-testes-sem-internet-intermitentes.md) (31/10). O 120 corrigiu o envio pela tela; o do service worker tem as mesmas brechas.

## O que falta

O envio pelo service worker (`enviarEmSegundoPlano`, `web/src/dados/segundoPlano.ts`, o `sync` do Android quando a rede volta) não tem as duas garantias que o 120 deu ao `enviarAgora`:

- **Sem a lista guardada, não sobe.** O `aplicar` tira o item aceito da fila e só acerta a lista de lançamentos que já está guardada. Sem ela (o aparelho lançou sem internet antes de abrir o Histórico, ticket 90), o lançamento enviado some do aparelho até a próxima leitura com internet. A tela lê a lista antes de enviar e, se não conseguir, não envia; o service worker envia direto.
- **A leitura mais velha não troca a guardada.** O `buscarEGuardar` da tela numera as leituras e só guarda a resposta da que saiu depois da última guardada. O `relerDepoisDaRegra` do service worker guarda direto, e a numeração da tela fica na memória dela, então uma leitura da tela que saiu antes pode chegar depois da do service worker (e vice-versa).

O teste "no Android, o service worker sobe a fila em segundo plano" (`web/e2e/sem-internet.spec.ts`) já dispara o `sync` pelo CDP (`ServiceWorker.dispatchSyncEvent`); dá para partir dele.

## Checklist

- [x] Teste vermelho com o `sync` pelo CDP: lançar sem internet sem a lista guardada, a leitura da lista falha e o lote do service worker passaria
- [x] O service worker lê e guarda a lista antes de enviar quando ela falta e, sem ela, não sobe (o navegador tenta de novo)
- [x] A ordem das leituras vale também entre a tela e o service worker (por exemplo, a numeração guardada no IndexedDB junto da resposta)
- [x] Verificações do projeto rodando e PR aberto para `main`

## Answer

Confirmado com dois testes no `sync` pelo CDP (`web/e2e/sem-internet.spec.ts`), vermelhos no código de antes e verdes depois:

- **"o service worker só sobe com a lista, e o enviado continua no aparelho"**: com a leitura da lista falhando, o service worker antigo subia o lote (`lotes` com 1); com a lista chegando, o enviado sumia do Histórico sem internet. Causa: o `enviarEmSegundoPlano` chamava o `enviarFila` direto, e o `aplicar` só acerta a lista já guardada. Agora ele faz o que o `enviarAgora` faz: com fila e sem lista guardada, lê e guarda a lista e, sem ela, falha (o navegador tenta de novo).
- **"a leitura da lista que a tela pediu antes da do service worker, se chega depois, não troca a guardada"**: a resposta da tela, que saiu antes de outro aparelho lançar, chegava depois da do service worker e apagava o lançamento do outro aparelho da lista guardada. Causa: a numeração das leituras era da memória da tela. Agora as duas usam o `lerEGuardar` (`web/src/dados/armazem.ts`): o número da leitura é a hora em que ela sai (`performance.timeOrigin + performance.now()`, o mesmo relógio para a tela, as abas e o service worker) e vai junto da resposta guardada (`Guardada.leitura`); a resposta não troca uma guardada de leitura que saiu depois. Uma guardada com número "depois de agora" é de antes de o relógio do aparelho voltar e não vale. O `aplicar` mantém o número ao acertar a lista, a Hoje e as contas.

Um contador no IndexedDB foi a primeira tentativa: comum a todos, mas punha uma transação de escrita sobre a fila e as respostas a cada leitura, na frente do salvar.

Dois testes clicavam em "Salvar" e já trocavam de aba; o salvar, ao terminar, abria o Histórico por cima (`parcelamento.spec.ts` "parcelamento recusado...", `sem-internet.spec.ts` "o saldo da conta conta os não enviados...", `contas-da-semana.spec.ts`). Agora eles esperam o Histórico abrir, como o `lancar` faz.
