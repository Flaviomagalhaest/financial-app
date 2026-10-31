# Envio em segundo plano sem a lista guardada: o enviado some do aparelho

Type: task
Status: ready-for-agent
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

- [ ] Teste vermelho com o `sync` pelo CDP: lançar sem internet sem a lista guardada, a leitura da lista falha e o lote do service worker passaria
- [ ] O service worker lê e guarda a lista antes de enviar quando ela falta e, sem ela, não sobe (o navegador tenta de novo)
- [ ] A ordem das leituras vale também entre a tela e o service worker (por exemplo, a numeração guardada no IndexedDB junto da resposta)
- [ ] Verificações do projeto rodando e PR aberto para `main`
