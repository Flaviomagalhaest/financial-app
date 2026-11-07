# Aba aberta numa versão anterior do app depois de uma versão nova

Type: task
Status: resolved
Blocked by: —
Skills: `grilling` (HITL: decisão do dono sobre recarregar sozinho ou avisar); depois `implement`, `tdd`; apoio: `run`
Modelo recomendado: Opus
Effort recomendado: medium
Issue: #403
Origem: revisão do [ticket 164](164-guardar-lancamento-por-lancamento-e-reler-so-o-que-mudou.md) (eixo Spec).

## O problema

O service worker novo assume na hora (`skipWaiting` e `clients.claim` em `web/service-worker.js`), mas a aba que já estava aberta segue rodando o JavaScript da versão anterior até alguém recarregar. Nada no app recarrega a aba nem avisa que há versão nova: não há `controllerchange` nem `onversionchange`.

O ticket 164 subiu o banco do aparelho (`financial-app-dados`) para a versão 2. Quando um contexto com o código novo abre o banco, a aba que ainda tem o código antigo pede a versão 1 e recebe `VersionError` em toda leitura e gravação do armazém: ela não mostra o guardado, não lança sem internet e não envia a fila, até ser recarregada. A fila guardada não se perde, porque a próxima abertura com o código novo a lê. O mesmo vale para qualquer mudança futura do banco, e, fora do banco, para uma aba velha conversando com uma API que mudou.

## A decisão (dono)

- Recarregar a aba sozinho quando o service worker novo assume (`controllerchange`), com o risco de perder o que está sendo digitado numa tela de lançamento aberta;
- ou mostrar "Nova versão: recarregar" e deixar a pessoa escolher, recarregando sozinho só quando não há nada aberto para editar;
- e, nos dois casos, se a aba velha que recebe `VersionError` também deve recarregar (a versão nova do banco só existe com o código novo).

## Decisão do dono (2026-11-07, `grilling`)

- **A aba recarrega sempre, sozinha**, quando o service worker de uma versão nova assume (`controllerchange`), mesmo com uma tela de lançamento aberta: o que estiver sendo digitado se perde. Sem aviso "Nova versão".
- **O `VersionError` do banco do aparelho recarrega do mesmo jeito**: ele prova que o código da aba é mais antigo que o banco.
- **A primeira instalação não recarrega**: o `controllerchange` de uma página que não tinha controlador não conta.
- **No máximo uma recarga pelo `VersionError` a cada 10 s** (marca em `sessionStorage`): um banco mais novo que o código servido (deploy que volta atrás) não vira laço; a aba segue com o erro, sem aviso novo. A recarga pelo `controllerchange` não passa pela marca: cada troca de controlador acontece uma vez, e a marca engoliria a troca que viesse logo depois de uma recarga pelo banco (revisão Spec).

As abas que já rodam o código anterior a este ticket não têm o ouvinte: a primeira publicação dele não as recarrega, e a recarga sozinha vale a partir da publicação seguinte.

Implementado em `web/src/dados/novaVersao.ts` (ligado em `web/src/main.tsx` e na abertura do banco em `web/src/dados/armazem.ts`; dentro do service worker, nada recarrega). Testes em `web/e2e/nova-versao.spec.ts`: a versão nova do service worker é simulada trocando um caractere da versão no `dist/service-worker.js` servido, e o código novo do banco, pedindo a versão 3 em vez da 2 nas abas carregadas depois de publicado.

## Checklist

- [x] Decisão do dono registrada aqui
- [x] Teste de navegador: aba aberta com a versão anterior, versão nova instalada noutra aba, e a aba anterior volta a ler e lançar
