# Infraestrutura prod e dev e primeiro deploy

Type: task
Status: ready-for-agent
Blocked by: 27, 20
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` se mexer na interface
Modelo recomendado: Opus
Effort recomendado: high
Issue: #82
Origem: [spec da v1](../spec.md), etapa 1; histórias de usuário 180, 181, 182

## O que construir

O esqueleto do ticket anterior vai ao ar na AWS em sa-east-1, nas pilhas `prod` e `dev`, e o merge na `main` publica sozinho. É verificável abrindo o endereço do CloudFront e vendo a rota de saúde responder pela Lambda e pelo DSQL.

## Checklist

- [ ] CDK em TypeScript com pilhas `prod` e `dev` na mesma conta, cada uma com cluster DSQL, user pool do Cognito e endereço próprios ([ADR 0009](../../../docs/adr/0009-aurora-dsql-em-sao-paulo.md), [ADR 0010](../../../docs/adr/0010-app-na-aws-cloudfront-http-api-e-uma-lambda.md))
- [ ] PWA num S3 privado servido pelo CloudFront; `/api/*` no mesmo endereço, sem cache e sem CORS, vai à HTTP API (limite 10 por segundo, rajada de 20) e a uma Lambda arm64 com a API inteira
- [ ] A distribuição do CloudFront é protegida contra substituição e remoção, e o endereço nunca muda
- [ ] Deploy pelo GitHub Actions com OIDC, sem chave de longa duração; `prod` no merge e `dev` por botão do workflow ou push em branch
- [ ] Migrations aplicadas ao DSQL antes da Lambda nova; o `dev` confere o schema contra o DSQL de verdade a cada deploy
- [ ] Região e endpoints só em configuração
- [ ] Verificações do projeto rodando e PR aberto para `main`
