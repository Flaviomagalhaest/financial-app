# Publicar em prod só a partir da main

Type: task
Status: done
Blocked by: —
Skills: `grilling` para decidir com o dono; apoio: `implement`, `wizard`; HITL (republicar a pilha `financial-github` pede credencial do dono)
Modelo recomendado: Sonnet
Effort recomendado: low
Issue: #128
Origem: revisão do [ticket 28](28-infra-prod-dev-e-primeiro-deploy.md)

## Question

A role `financial-app-deploy` (`infra/lib/pilha-github.ts`) confia em qualquer branch deste repositório (`...:ref:refs/heads/*`), porque o `dev` sai por push em qualquer branch. Ela assume as roles do bootstrap do CDK, que publicam com AdministratorAccess, e entra como `admin` em qualquer cluster DSQL da conta. Só a expressão do `.github/workflows/deploy.yml` manda o push da `main` para `prod`: uma branch que mude o workflow consegue publicar em `prod`. Hoje só o dono faz push, então o risco é baixo. Vale separar?

Opções a decidir:

- **Deixar como está**: um push só, só o dono publica.
- **Duas roles**: `prod` confiando só em `ref:refs/heads/main` e `dev` em qualquer branch. As duas ainda assumem as mesmas roles do bootstrap, então a separação precisa de um bootstrap com política de execução restrita ou de um qualificador por ambiente.
- **Ambiente `prod` do GitHub** com regra de branch só `main` e o `sub` terminando em `:environment:prod`.

## Answer

Decisão: **GitHub Environment `prod` com duas roles IAM** (opção B2 + duas roles).

- `financial-app-deploy-prod` — confia só em `sub` terminando em `:environment:prod` (StringEquals); usada pelo job que declara `environment: prod` no workflow.
- `financial-app-deploy-dev` — confia em qualquer branch (`ref:refs/heads/*`); usada por todos os outros deploys.
- Sem proteções extras no environment (revisores, wait timer) por ora.

O workflow já usa `environment: prod` no job quando `$AMBIENTE == prod`, e a ARN da role vira `financial-app-deploy-$AMBIENTE`.

Pendências pós-código (requerem credencial do dono):
1. Criar o GitHub Environment `prod` no repositório com regra de branch `main` only.
2. Republicar a pilha `financial-github` na AWS para criar as duas novas roles e remover a antiga.
3. Conferir deploy de `dev` e de `prod` com o teste de fumaça.

## Checklist

- [x] Decisão do dono registrada em `## Answer`
- [ ] GitHub Environment `prod` criado com branch protection `main` only (dono, UI do repositório)
- [ ] Pilha `financial-github` republicada pelo dono (credencial humana)
- [ ] Deploy de `dev` e de `prod` conferidos pelo teste de fumaça
