# Papel próprio da API no DSQL, sem admin

Type: task
Status: claimed
Blocked by: 28
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #127
Origem: revisão do [ticket 28](28-infra-prod-dev-e-primeiro-deploy.md) (débito técnico)

## O que construir

A Lambda da API entra no Aurora DSQL como `admin` (`generate_db_connect_admin_auth_token` em `backend/app/banco.py` e `dsql:DbConnectAdmin` em `infra/lib/pilha-app.ts`). Ela passa a entrar com um papel próprio do banco, ligado à role IAM da Lambda, só com leitura e escrita nas tabelas do app. O `admin` fica para o job de deploy, que aplica as migrations.

## Checklist

- [x] Papel do banco para a API (`CREATE ROLE ... WITH LOGIN` e `AWS IAM GRANT` para a role da Lambda de cada ambiente), criado pelo deploy sem ARN fixo no repositório
- [x] Permissões nas tabelas que continuam valendo para as migrations seguintes (conferir o que o DSQL aceita: `GRANT` por tabela, `ALTER DEFAULT PRIVILEGES`)
- [x] Lambda com `dsql:DbConnect` e `generate_db_connect_auth_token`, sem `DbConnectAdmin`
- [ ] Conferido no `dev` pelo teste de fumaça (`scripts/conferir-deploy.sh`)
- [ ] Verificações do projeto rodando e PR aberto para `main`
