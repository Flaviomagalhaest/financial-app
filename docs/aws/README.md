# Conta AWS 255235818791

## SCP `p-q0eemrzp`

`scp-p-q0eemrzp.json` é a cópia da SCP `AdvancedModeRegionRestrictionSecurityControlPolicy`, na raiz da organização (obtida em 2026-10-28 com `aws organizations describe-policy --policy-id p-q0eemrzp --query Policy.Content`, na conta de gerência).

O bloco `RegionFloor` libera `sa-east-1` (São Paulo). **Reaplicar a SCP sem `sa-east-1` derruba o app**: o Aurora DSQL, a Lambda, o S3 do backup e o login ficam todos em São Paulo (ADR 0009 e 0010).

Ela fica fora da infraestrutura como código, porque o repositório do app não deve ter credencial da conta de gerência. Se ela mudar na AWS, atualize a cópia.

## Deploy pelo GitHub Actions

Feito uma vez à mão, em 2026-10-28, com credencial temporária da conta:

1. `npx aws-cdk bootstrap aws://255235818791/sa-east-1` (pilha `CDKToolkit`).
2. `cd infra && npm ci && npx cdk deploy financial-github`: provedor OIDC do GitHub e a role `financial-app-deploy`. A role confia em qualquer branch deste repositório, no formato novo do `sub` (`repo:Flaviomagalhaest@14982168/financial-app@1432589902:ref:refs/heads/*`), assume as roles do bootstrap do CDK e entra no DSQL como `admin` para as migrations.

Daí em diante, todo deploy sai pelo `.github/workflows/deploy.yml`. Refaça os dois passos só se a pilha `CDKToolkit` ou a `financial-github` sumirem.

O `dev` é descartável: `cd infra && npx cdk destroy financial-dev-app financial-dev-dados` (o próximo push recria, com endereço novo). A `prod` tem proteção contra término e guarda banco, user pool e distribuição mesmo se a pilha for apagada.
