# Publicar em prod só a partir da main

Type: task
Status: ready-for-human
Blocked by: 28
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

## Checklist

- [ ] Decisão do dono registrada em `## Answer`
- [ ] Se mudar, a pilha `financial-github` republicada pelo dono e o deploy de `dev` e de `prod` conferidos pelo teste de fumaça
