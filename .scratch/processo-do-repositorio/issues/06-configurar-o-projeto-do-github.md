# Configurar o projeto do GitHub (colunas, auto-add e coluna de cada issue)

Status: resolved
Blocked by: —
Skills: nenhuma; HITL (o dono configura o projeto na interface do GitHub e roda o script com o `gh` dele)
Modelo recomendado: Sonnet
Effort recomendado: low
Issue: #43
Origem: [ticket 05](05-migrar-governanca-do-trello-para-github.md); a sessão não tinha acesso à API de GitHub Projects

## Problema

O projeto veio do template Kanban (colunas Backlog/Ready/In progress/In review/Done). As issues existem, mas só entram no projeto e nas colunas com a configuração e o script abaixo.

## Checklist

- [x] No projeto, renomear/criar as opções do campo **Status** para: `TODO`, `WAITING`, `DOING`, `BLOCKED`, `FINISHED` (nessa ordem, como no Trello)
- [x] Em Settings → Workflows, ativar "Auto-add to project" com o filtro `repo:Flaviomagalhaest/financial-app is:issue` e ligar o projeto ao repositório (aba Projects do repo)
- [x] Em Workflows, "Item closed" → `FINISHED` e "Item reopened" → `TODO`; desligar "Item added to project" → Backlog, se existir
- [x] Sincronizar o projeto: pelo workflow (ticket 07) ou, com o `gh` instalado, `gh auth refresh -s project` e `scripts/sincronizar-projeto.sh`
- [x] Conferir o kanban: 6 em WAITING, 2 em BLOCKED (09 e 12 da V1), os demais em FINISHED
- [x] Remover o quadro do Trello, se não for mais necessário

## Answer

O dono configurou o campo Status, os workflows do projeto e rodou a sincronização; conferiu o kanban e removeu o quadro do Trello. A sessão que fechou o ticket não conseguiu acessar o projeto (token do `gh` inválido), então esta conferência é do dono, não da sessão.
