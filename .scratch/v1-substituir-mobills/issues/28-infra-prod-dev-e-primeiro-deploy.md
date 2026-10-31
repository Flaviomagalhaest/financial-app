# Infraestrutura prod e dev e primeiro deploy

Type: task
Status: resolved
Blocked by: 27, 20
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` se mexer na interface
Modelo recomendado: Opus
Effort recomendado: high
Issue: #82
Origem: [spec da v1](../spec.md), etapa 1; histórias de usuário 180, 181, 182

## O que construir

O esqueleto do ticket anterior vai ao ar na AWS em sa-east-1, nas pilhas `prod` e `dev`, e o merge na `main` publica sozinho. É verificável abrindo o endereço do CloudFront e vendo a rota de saúde responder pela Lambda e pelo DSQL.

## Checklist

- [x] CDK em TypeScript com pilhas `prod` e `dev` na mesma conta, cada uma com cluster DSQL, user pool do Cognito e endereço próprios ([ADR 0009](../../../docs/adr/0009-aurora-dsql-em-sao-paulo.md), [ADR 0010](../../../docs/adr/0010-app-na-aws-cloudfront-http-api-e-uma-lambda.md))
- [x] PWA num S3 privado servido pelo CloudFront; `/api/*` no mesmo endereço, sem cache e sem CORS, vai à HTTP API (limite 10 por segundo, rajada de 20) e a uma Lambda arm64 com a API inteira
- [x] A distribuição do CloudFront é protegida contra substituição e remoção, e o endereço nunca muda
- [x] Deploy pelo GitHub Actions com OIDC, sem chave de longa duração; `prod` no merge e `dev` por botão do workflow ou push em branch
- [x] Migrations aplicadas ao DSQL antes da Lambda nova; o `dev` confere o schema contra o DSQL de verdade a cada deploy
- [x] Região e endpoints só em configuração
- [x] Verificações do projeto rodando e PR aberto para `main`

## Answer

No ar em 2026-10-28. O `dev` respondeu pelo CloudFront, pela Lambda e pelo DSQL em `https://d7e2zhq5p4yds.cloudfront.net/api/saude` (`{"status":"ok","migrations":1}`), e uma rota sem token toma 401 do authorizer JWT. O `prod` sai no merge deste PR pelo mesmo workflow, e o teste de fumaça dele aparece no resumo da execução do `Deploy` na `main`.

- **Pilhas** (`infra/`, CDK em TypeScript; conta e região só em `config/aws.json`): `financial-<ambiente>-dados` tem o cluster DSQL e o user pool com o cliente público. `financial-<ambiente>-app` tem a Lambda arm64 python3.14 (FastAPI pelo Mangum), a HTTP API (estágio `$default` com limite de 10 por segundo e rajada de 20; `GET /api/saude` aberta e o resto com JWT do user pool), o S3 privado da PWA com OAC e o CloudFront com `/api/*` sem cache e sem CORS. As duas pilhas ficam separadas para as migrations rodarem depois do banco e antes da Lambda nova.
- **Endereço que não muda**: a distribuição tem ID lógico fixo (`Distribuicao`) e é retida em `prod`. As políticas das pilhas (`infra/politicas/`, aplicadas a cada deploy) recusam substituir ou remover a distribuição, o banco e o user pool. A `prod` tem proteção contra término.
- **Deploy** (`.github/workflows/deploy.yml`): OIDC com a role `financial-app-deploy`, sem chave de longa duração. O push na `main` publica em `prod`; push em outra branch ou o botão publica em `dev`. A ordem é pilha de dados, migrations no DSQL (com token IAM), pilha do app e o teste de fumaça `scripts/conferir-deploy.sh`.
- **Feito à mão uma vez**, com credencial temporária do dono na conta <conta AWS>: `cdk bootstrap` em sa-east-1 e a pilha `financial-github` (provedor OIDC e role). O runbook está em [`docs/aws/README.md`](../../../docs/aws/README.md).
- **Testes**: costuras combinadas com o dono, a API HTTP em processo (inclusive a Lambda chamada com um evento da HTTP API) e o teste de fumaça pós-deploy. O dono dispensou testes de template do CDK; o CI roda typecheck e synth das pilhas.

Pendências gravadas no tracker:

- [ticket 70](70-papel-proprio-da-api-no-dsql.md): a API entra no DSQL como `admin`.
- [ticket 71](71-publicar-em-prod-so-a-partir-da-main.md): a role de deploy aceita qualquer branch.
- Nota no [ticket 30](30-login-no-app.md): conferir que o `Authorization` atravessa o CloudFront.
