# Criar o secret PROJECT_TOKEN do workflow que sincroniza o projeto

Status: resolved
Blocked by: —
Skills: nenhuma; HITL (o dono cria o token e o secret no GitHub)
Modelo recomendado: Sonnet
Effort recomendado: low
Issue: #45
Origem: [ticket 06](06-configurar-o-projeto-do-github.md); o dono não tem o `gh` instalado, então o `scripts/sincronizar-projeto.sh` roda no GitHub Actions (`.github/workflows/sincronizar-projeto.yml`)

## Problema

O `GITHUB_TOKEN` do Actions não alcança projetos de usuário. O workflow precisa de um token pessoal no secret `PROJECT_TOKEN`; sem ele, o job falha com uma mensagem apontando este ticket.

## Checklist

- [x] Criar um PAT clássico em https://github.com/settings/tokens com os escopos `project` e `repo` (ou fine-grained com Projects: read/write e Issues: read/write neste repositório)
- [x] Guardar como secret `PROJECT_TOKEN` em Settings → Secrets and variables → Actions do repositório
- [x] Depois do merge, rodar o workflow "Sincronizar projeto" em Actions (Run workflow) e conferir o kanban
- [x] Se o job falhar por coluna inexistente, conferir os nomes das opções do campo Status: `TODO`, `WAITING`, `DOING`, `BLOCKED`, `FINISHED`

## Answer

O dono criou o token e o secret `PROJECT_TOKEN`. O workflow "Sincronizar projeto" roda com sucesso desde a rodada manual de 2026-10-25 (run 2) e em todos os pushes seguintes, na `main` e nas branches (depois do [ticket 08](08-sincronizar-projeto-em-qualquer-branch.md)); as colunas existem com os nomes certos.
