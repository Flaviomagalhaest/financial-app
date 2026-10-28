# Login no app

Type: task
Status: resolved
Blocked by: 28
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` se mexer na interface
Modelo recomendado: Opus
Effort recomendado: high
Issue: #84
Origem: [spec da v1](../spec.md), etapa 1; histórias de usuário 4, 5, 6, 7, 8, 9

## O que construir

Cada um do casal entra com e-mail e senha num formulário dentro do app e fica logado por anos; a API aceita só quem tem JWT válido.

## Checklist

- [x] Formulário no app com SRP e cliente público do Cognito, isolado num módulo de login que é o único a conhecer o Cognito
- [x] Refresh token de 10 anos no IndexedDB (nunca em cookie) e token de acesso de 15 minutos; sem internet e com o acesso vencido o app segue usável
- [x] A API depende só de um JWT padrão (emissor e audiência em configuração) e tira a pessoa do token; testes com dois usuários por JWT de teste
- [x] Só os dois usuários existem, sem cadastro público; o dono consegue desconectar todas as sessões de um celular perdido
- [x] Sair da conta com itens não enviados pede confirmação (o aviso só ganha efeito quando a fila existir, [ticket 33](33-lancamento-sem-internet-fila-e-envio.md))
- [x] Verificações do projeto rodando e PR aberto para `main`

## Comments

- 2026-10-28 (ticket 28): o user pool e o cliente público (SRP, acesso de 15 minutos, refresh de 10 anos) já existem em `infra/lib/pilha-dados.ts`, com IDs nas saídas `UserPoolId` e `ClienteDoAppId` da pilha `financial-<ambiente>-dados`. A HTTP API já exige o JWT desse user pool em `ANY /api/{proxy+}` (emissor e audiência), e só `GET /api/saude` fica aberta. Falta conferir, com um token de verdade, que o CloudFront passa o `Authorization` à HTTP API (`CachingDisabled` com `AllViewerExceptHostHeader` em `/api/*`).
- 2026-10-28 (ticket 30): feito. Módulo de login em `web/src/login/` (único que conhece o Cognito: SRP pela `amazon-cognito-identity-js`, renovação e revogação por chamada direta), sessão no IndexedDB `financial-app-login`, acesso renovado com 1 minuto de folga e, sem internet, o app segue logado. A API confere o JWT em `backend/app/login.py` (`JWT_EMISSOR`, `JWT_AUDIENCIA`, chaves no JWKS do emissor; `aud` ou `client_id`, como o authorizer) e tira o usuário do `sub`; rota protegida recebe `usuario: UsuarioLogado`. O token de identidade passou a valer 15 minutos também (nota no ADR 0010). O dono cria os usuários e desconecta sessões com `scripts/usuarios-do-app.sh`. O aviso de sair com não enviados está em `web/src/App.tsx` (`contarNaoEnviados`, hoje 0) e entra no [ticket 33](33-lancamento-sem-internet-fila-e-envio.md). Pendências: login com o Cognito de verdade, o `Authorization` pelo CloudFront e a criação dos usuários no [ticket 72](72-criar-usuarios-e-conferir-o-login-de-verdade.md).
