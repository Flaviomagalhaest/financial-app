# Filtros salvos

Type: task
Status: resolved
Blocked by: 59
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` se mexer na interface
Modelo recomendado: Sonnet
Effort recomendado: low
Issue: #114
Origem: [spec da v1](../spec.md), etapa 5; histórias de usuário 146

## O que construir

O casal repete buscas frequentes com um toque.

## Checklist

- [x] Salvar com nome, critérios, ordenação e período relativo ("este mês") ou fixo, compartilhado com a outra pessoa
- [x] Renomear e excluir; só com internet
- [x] Testes de API
- [x] Verificações do projeto rodando e PR aberto para `main`

## Notas da implementação

- **API** (`backend/app/filtros_salvos.py`, testes em `backend/tests/test_filtros_salvos.py`): `GET/POST /api/filtros-salvos`, `PUT /api/filtros-salvos/{id}` (renomear) e `DELETE`. Guarda os critérios da busca, a ordem e o período relativo (`este_mes`, `mes_passado`, `este_ano`, `ultimos_30_dias`) ou o fixo (os dois dias nos critérios). O relativo é resolvido a cada leitura e vem no `pedido`, pronto para o `POST /api/busca`. É do casal inteiro; nome ordenado sem distinguir maiúsculas; reenviar o id é idempotente. Tabela `filtros_salvos` (migration 0050) e backup na versão 19 (backup antigo entra sem filtros).
- **Tela**: `web/src/busca/FiltrosSalvos.tsx`, na busca: fileira de filtros salvos (tocar aplica), "Salvar esta busca" com nome e período, renomear e excluir. Só com internet (ADR 0011); a lista fica guardada para leitura sem internet. Teste de navegador em `web/e2e/filtros-salvos.spec.ts`.
- **Fora do ticket**: o `removerFavorito` usa `recusaDe`, que trata `data` vazio (o 204) como recusa; aqui o `DELETE` usa `response.ok`. Vale conferir o dos favoritos.
