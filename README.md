# Financial App

App financeiro do casal: API em Python (FastAPI) em `backend/`, app React + TypeScript em `web/`, infraestrutura AWS (CDK em TypeScript) em `infra/`. Spec e tickets em `.scratch/`.

## Pré-requisitos

Python 3.14 (o runtime da Lambda; `backend/.python-version`) com [uv](https://docs.astral.sh/uv/), Node 22, Postgres 16 (o mesmo do CI).

## Como rodar

```sh
eval "$(scripts/postgres-local.sh)"          # Postgres local sem Docker; exporta DATABASE_URL
(cd web && npm ci && node e2e/cognito-falso.ts)   # login de mentira na porta 9230 (veja Login)
(cd backend && uv sync && uv run python -m app.migrations)
(cd backend && JWT_EMISSOR=http://127.0.0.1:9230/sa-east-1_teste JWT_AUDIENCIA=cliente-de-teste \
  uv run uvicorn app.main:create_app --factory --port 8765)
(cd web && VITE_COGNITO_USER_POOL_ID=sa-east-1_teste VITE_COGNITO_CLIENTE_ID=cliente-de-teste \
  VITE_COGNITO_ENDPOINT=http://127.0.0.1:9230/ npm run dev)   # /api é repassado para a porta 8765
```

Com o Cognito falso, `flavio@teste.com` e `esposa@teste.com` entram com qualquer senha.

## Login

O app entra no Cognito por um formulário próprio (SRP, cliente público), e só o módulo `web/src/login/` conhece o Cognito. A sessão fica no IndexedDB do aparelho, nunca em cookie: refresh token de 10 anos e token de acesso de 15 minutos, renovado quando vence; sem internet, o app segue logado com o acesso vencido. A API só confere um JWT padrão, com emissor e audiência em `JWT_EMISSOR` e `JWT_AUDIENCIA` (chaves em `<emissor>/.well-known/jwks.json`), e tira o usuário do `sub`. Rota nova protegida recebe `usuario: UsuarioLogado` (`app/login.py`).

O app lê o user pool no build: `VITE_COGNITO_USER_POOL_ID`, `VITE_COGNITO_CLIENTE_ID` e, só para o falso, `VITE_COGNITO_ENDPOINT`. O deploy preenche os dois primeiros com as saídas da pilha de dados.

Não há cadastro público: o dono cria os dois usuários, já com a senha definitiva, e desconecta todas as sessões de um celular perdido (o acesso já emitido vence em até 15 minutos):

```sh
scripts/usuarios-do-app.sh criar prod <email>
scripts/usuarios-do-app.sh desconectar prod <email>
scripts/usuarios-do-app.sh listar prod
```

## Como testar

```sh
(cd backend && uv run pytest)                # rotas em processo contra o Postgres de DATABASE_URL
(cd web && npm run typecheck && npx playwright test)   # sobe Cognito falso, API e app; o teste desliga a rede
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

## Deploy

O workflow `.github/workflows/deploy.yml` publica pelo GitHub Actions com OIDC (role `financial-app-deploy`, sem chave de longa duração): o merge na `main` publica em `prod`; push em outra branch, ou o botão "Run workflow", publica em `dev`. Conta e região ficam só em `config/aws.json`.

Cada ambiente tem duas pilhas: `financial-<ambiente>-dados` (cluster Aurora DSQL e user pool do Cognito) e `financial-<ambiente>-app` (Lambda arm64 com a API, HTTP API com limite de 10 por segundo e rajada de 20, PWA num S3 privado e o CloudFront, que leva `/api/*` à HTTP API sem cache). O deploy segue esta ordem: pilha de dados, migrations no DSQL, build da PWA com o user pool do ambiente, pilha do app e o teste de fumaça (`scripts/conferir-deploy.sh <endereço>`), que exige `/api/saude` ok com todas as migrations e `/api/eu` recusado sem token. As políticas das pilhas (`infra/politicas/`) proíbem substituir ou remover a distribuição, o banco e o user pool, porque a PWA instalada fica presa ao endereço do CloudFront.

Para conferir as pilhas localmente:

```sh
scripts/empacotar-lambda.sh                  # pacote da Lambda em build/lambda (arm64, python3.14)
(cd web && npm run build)
(cd infra && npm ci && npm run typecheck && npm run synth)
```
