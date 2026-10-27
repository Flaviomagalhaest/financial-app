# Financial App

App financeiro do casal: API em Python (FastAPI) em `backend/`, app React + TypeScript em `web/`. Spec e tickets em `.scratch/`.

## Pré-requisitos

Python 3.12+ com [uv](https://docs.astral.sh/uv/), Node 22, Postgres 16 (o mesmo do CI).

## Como rodar

```sh
eval "$(scripts/postgres-local.sh)"          # Postgres local sem Docker; exporta DATABASE_URL
(cd backend && uv sync && uv run python -c "from app.migrations import aplicar_migrations as a; import os; a(os.environ['DATABASE_URL'])")
(cd backend && uv run uvicorn app.main:create_app --factory --port 8765)
(cd web && npm ci && npm run dev)            # /api é repassado para a porta 8765
```

## Como testar

```sh
(cd backend && uv run pytest)                # rotas em processo contra o Postgres de DATABASE_URL
(cd web && npm run typecheck && npx playwright test)   # sobe API e app sozinho; o teste desliga a rede
```

O CI (`.github/workflows/ci.yml`) roda lint, testes, o contrato e o build com um Postgres em container.

## Contrato (OpenAPI e tipos)

A FastAPI gera o OpenAPI; `openapi.json` fica versionado e o app gera os tipos dele. Depois de mudar uma rota ou um modelo:

```sh
(cd backend && uv run python gerar_openapi.py)
(cd web && npm run gerar-tipos)
```

O CI falha se `openapi.json` ou `web/src/api/schema.d.ts` estiverem desatualizados.

## Migrations

Arquivos `backend/migrations/NNNN_nome.sql`, um DDL por arquivo, no subconjunto do Aurora DSQL (sem triggers nem PL/pgSQL). `aplicar_migrations` aplica em ordem as que faltam e as registra em `controle_de_migrations`.

## Configuração

Os valores iniciais da spec (3 sugeridos, 5 usos, 24 h, 80% etc.) ficam só em `config/valores-iniciais.json`, lido pela API (`app.config.valores_iniciais`) e importável pelo app.
