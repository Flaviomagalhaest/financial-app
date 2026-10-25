# Criar o secret PROJECT_TOKEN do workflow que sincroniza o projeto

Status: ready-for-human
Blocked by: —
Skills: nenhuma; HITL (o dono cria o token e o secret no GitHub)
Modelo recomendado: Sonnet
Effort recomendado: low
Issue: #45
Origem: [ticket 06](06-configurar-o-projeto-do-github.md); o dono não tem o `gh` instalado, então o `scripts/sincronizar-projeto.sh` roda no GitHub Actions (`.github/workflows/sincronizar-projeto.yml`)

## Problema

O `GITHUB_TOKEN` do Actions não alcança projetos de usuário. O workflow precisa de um token pessoal no secret `PROJECT_TOKEN`; sem ele, o job falha com uma mensagem apontando este ticket.

## Checklist

- [ ] Criar um PAT clássico em https://github.com/settings/tokens com os escopos `project` e `repo` (ou fine-grained com Projects: read/write e Issues: read/write neste repositório)
- [ ] Guardar como secret `PROJECT_TOKEN` em Settings → Secrets and variables → Actions do repositório
- [ ] Depois do merge, rodar o workflow "Sincronizar projeto" em Actions (Run workflow) e conferir o kanban
- [ ] Se o job falhar por coluna inexistente, conferir os nomes das opções do campo Status: `TODO`, `WAITING`, `DOING`, `BLOCKED`, `FINISHED`
