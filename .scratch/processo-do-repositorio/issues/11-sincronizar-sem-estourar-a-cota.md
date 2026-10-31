# Sincronizar o projeto sem estourar a cota GraphQL

Type: task
Status: resolved
Blocked by: —
Skills: `diagnosing-bugs`; sem HITL além da revisão do PR
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #241
Origem: pedido do dono (31/10): o "Sincronizar projeto" da `main` falhou com `GraphQL: API rate limit exceeded for user ID 14982168` (run 41153733274), depois de uma sequência de merges.

## Problema

Na `main`, cada push sincronizava os ~130 tickets, e cada ticket chamava o `gh` quatro vezes, mudasse algo ou não: `project item-add`, `project item-edit`, `issue close`/`reopen` e `issue edit` do rótulo `blocked`. Cada comando faz consultas antes da mutação: eram por volta de mil chamadas GraphQL por rodada, de 6 a 12 minutos cada. A cota GraphQL (5.000 pontos por hora) é do usuário dono do `PROJECT_TOKEN`, somando todos os tokens dele. Quatro merges em meia hora (#240, #226, #232, #228), mais as rodadas das branches, a esgotaram.

## Checklist

- [x] Ler o projeto inteiro de uma vez (uma consulta paginada, 100 itens por página) com a coluna, o estado e os rótulos de cada issue
- [x] Mudar só o que difere: entrar no projeto, coluna, abrir/fechar, rótulo `blocked`
- [x] Abrir, fechar e o rótulo pela API REST, que tem cota à parte
- [x] `--dry-run` e a lista de tickets como argumento continuam iguais
- [x] Testado com um `gh` falso: diferenças plantadas viram só as mutações esperadas; projeto em dia, uma consulta e nenhuma mutação
- [x] PR aberto para `main`

## Resolução

`scripts/sincronizar-projeto.sh` lê o projeto com `gh api graphql --paginate` e compara com a coluna que cada ticket pede (as regras de `coluna()` e `bloqueado()` não mudaram). Com o projeto em dia, a sincronização completa custa uma consulta por página (umas duas, a ~2 pontos cada). Cada diferença custa uma mutação GraphQL (entrar no projeto, coluna) ou uma chamada REST (estado, rótulo). A saída lista o que mudou em cada ticket e o total.

A primeira rodada contra a API de verdade é a do push desta branch, que sincroniza este ticket; a da `main` vem no merge.
