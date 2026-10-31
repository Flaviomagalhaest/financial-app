# Ligar as pessoas do casal ao ambiente (PESSOAS)

Type: task
Status: ready-for-human
Blocked by: —
Skills: `wizard` (HITL: só o dono sabe o `sub` de cada usuário no Cognito); apoio: `implement`
Modelo recomendado: Sonnet
Effort recomendado: low
Issue: #161
Origem: [ticket 41](41-pessoa-autoria-e-parece-repetido.md): o token de acesso do Cognito não traz nome, então a API aprende quem é quem pela variável `PESSOAS` (`app/pessoas.py`), um JSON `{"<sub>": "<nome>"}`; sem ela, `GET /api/pessoas` volta vazio, o seletor de pessoa só mostra "Conjunto" e os avisos dizem "a outra pessoa"

## O que construir

Dar à Lambda de `dev` e de `prod` a variável `PESSOAS` com o `sub` e o nome de cada um dos dois usuários, para o app mostrar "Flávio" e o nome da esposa em vez de "a outra pessoa".

## Checklist

- [ ] Descobrir o `sub` de cada usuário em cada ambiente (`scripts/usuarios-do-app.sh listar` mostra e-mail e status; o `sub` sai de `aws cognito-idp admin-get-user`) e decidir os nomes que aparecem no app
- [x] Passar `PESSOAS` para a Lambda em `infra/lib/pilha-app.ts` (`environment`), sem pôr os `sub` reais no repositório se o dono preferir (parâmetro da pilha ou variável do deploy) e documentar no README
- [ ] Conferir no app de `dev`: o seletor de pessoa mostra os dois nomes, a tela de conflito diz "O de <nome>" e o menu ⋯ > Informações mostra quem criou
- [ ] Verificações do projeto rodando e PR aberto para `main`
