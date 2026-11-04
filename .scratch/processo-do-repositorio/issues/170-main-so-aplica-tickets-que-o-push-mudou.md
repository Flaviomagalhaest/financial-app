# Main só aplica ao projeto os tickets que o push mudou

Type: task
Status: claimed
Blocked by: —
Skills: `writing-for-agents` (AGENTS.md), `tdd` (teste do script com `gh` falso)
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #416
Origem: pedido do dono (04/11): o "Sincronizar projeto" da `main` moveu um card de DOING/FINISHED para TODO enquanto outra branch ainda esperava o merge do PR.

## Regra

1. A sessão que começa um ticket empurra o `claimed` primeiro (passo zero); a branch move o card para DOING.
2. A `main` não desfaz isso: a cada push, aplica o estado completo (coluna, issue aberta/fechada, rótulo `blocked`) só aos tickets que **aquele push mudou** (`git diff $ANTES HEAD`). O ticket que o merge não tocou, e que a `main` ainda lê como aberto, não é mexido.
3. No merge da branch (ticket `resolved`), o card vai para FINISHED e a issue fecha.
4. Nos demais tickets a `main` só faz o que não regride: pôr no projeto o que falta e tirar as issues órfãs. Nunca move coluna.
5. Dependentes via `Blocked by` dos tickets mudados são reavaliados só entre BLOCKED e a coluna do status, sem tirar ninguém de DOING/FINISHED.
6. A varredura completa vira modo manual (`workflow_dispatch` com `--tudo`), para acertar desvios. `reivindicado()` sai.

## Checklist

- [x] `scripts/sincronizar-projeto.sh`: a `main` com `--tirar-sem-ticket` e lista de tickets mudados; modo `--tudo` para a varredura completa; remover `reivindicado()`
- [x] Workflow: na `main`, calcular `$ANTES` e a lista de tickets mudados; `workflow_dispatch` com `--tudo`
- [x] AGENTS.md: a regra em "Como atualizar" e o claim como passo zero
- [x] Testado com `gh` falso: merge de outro ticket não mexe no DOING; merge do ticket `resolved` leva a FINISHED e fecha a issue; dependente sai de BLOCKED; `--tudo` acerta tudo
- [ ] PR aberto para `main`, sem conflito e com checks verdes

## Notas

Limite conhecido: branch abandonada deixa o card em DOING até correção à mão ou `--tudo`. Sessão que não empurra o `claimed` não aparece para nenhum script.
