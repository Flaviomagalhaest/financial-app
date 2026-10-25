# Migrar a governança dos tickets do Trello para o GitHub Projects

Status: resolved
Blocked by: —
Skills: `writing-for-agents`
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #42
Origem: pedido do dono: sair do Trello e usar o projeto https://github.com/users/Flaviomagalhaest/projects/3

## Problema

Os tickets eram espelhados num quadro do Trello. O dono criou um projeto do GitHub e quer o mesmo kanban lá.

## Answer

- Cada ticket de `.scratch/` ganhou uma issue (`Issue: #N` no lugar de `Trello:`); as fechadas nasceram fechadas, `wontfix` como `not planned`.
- Colunas iguais às do Trello: TODO, WAITING, DOING, BLOCKED, FINISHED (regra no `AGENTS.md`, seção "GitHub Projects espelha o tracker").
- `scripts/sincronizar-projeto.sh` calcula a coluna de cada ticket e a aplica no projeto.
- `docs/agents/issue-tracker.md` e `AGENTS.md` deixaram de citar o Trello.
- Tickets 01, 02 e 04 deste processo viraram `wontfix` (etiquetas do Trello e tags `merged/*` não existem mais).
- Pendência: o ambiente da sessão não tinha acesso à API de Projects (o conector do GitHub só cria issues), então a configuração do projeto e a colocação das issues nas colunas ficou no [ticket 06](06-configurar-o-projeto-do-github.md).

## Checklist

- [x] Issues criadas para os 26 tickets existentes
- [x] Regras do `AGENTS.md` e do `issue-tracker.md` atualizadas
- [x] Script de sincronização
- [x] Pendência registrada no ticket 06
