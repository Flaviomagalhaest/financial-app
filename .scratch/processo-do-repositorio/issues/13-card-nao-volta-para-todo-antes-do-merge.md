# Sincronizar: o card não volta para TODO enquanto o PR não é mesclado

Type: task
Status: ready-for-agent
Blocked by: —
Skills: `implement`, `writing-for-agents` (AGENTS.md)
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #420
Origem: pergunta do dono (04/11): "Por que o ticket voltou para TODO?", sobre o [ticket 165 da V1](../../v1-substituir-mobills/issues/165-telas-que-filtram-a-lista-leem-do-servidor.md).

## O que acontece

A sessão troca o `Status:` para `claimed` no começo e para `resolved` no fim, os dois na branch. A `main` só lê o ticket depois do merge do PR. Enquanto o PR está aberto, cada merge de outro PR na `main` roda `scripts/sincronizar-projeto.sh` completo e recalcula todos os cards pela `main`, onde o ticket ainda está `ready-for-agent`: coluna TODO.

O freio que existe (`reivindicado`) só mantém o card em DOING se alguma branch remota ainda tem o ticket em `claimed`. No 165 a branch passou a `resolved` (no commit `bfd867e`) antes do merge e os PRs #405, #408 e #409 entraram na `main` no meio: o freio deixou de valer e o card pôde voltar de DOING para TODO. (Não foi possível ver a coluna na sessão, sem `gh` autenticado; a causa vem da leitura do script.)

## O que construir

Fazer o freio valer também para o ticket que uma branch remota já deu como `resolved`, `done` ou `wontfix`: a `main` mantém a coluna em que o card está (DOING ou FINISHED) em vez de devolver a TODO/WAITING, até o merge do PR trazer o `Status:` para a `main`. A alternativa, mandar a sessão deixar `claimed` até o merge, perde o `resolved` no tracker e o `claimed` fica mentindo depois do trabalho feito; por isso o script.

## Checklist

- [ ] `reivindicado` (ou função irmã) considera `resolved|done|wontfix` numa branch remota fora da `main`
- [ ] Testado com um `gh` falso: ticket `resolved` só numa branch fica em FINISHED/DOING após a rodada completa da `main`; ticket sem branch nenhuma ainda volta a TODO
- [ ] `AGENTS.md`: a regra, em "Como atualizar", junto do que já diz sobre o `claimed`
- [ ] PR aberto para `main`
