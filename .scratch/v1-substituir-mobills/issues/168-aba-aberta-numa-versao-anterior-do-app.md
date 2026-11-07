# Aba aberta numa versão anterior do app depois de uma versão nova

Type: task
Status: claimed
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

## Checklist

- [ ] Decisão do dono registrada aqui
- [ ] Teste de navegador: aba aberta com a versão anterior, versão nova instalada noutra aba, e a aba anterior volta a ler e lançar
