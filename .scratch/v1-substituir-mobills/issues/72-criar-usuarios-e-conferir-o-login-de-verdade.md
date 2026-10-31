# Criar os usuários e conferir o login de verdade

Type: task
Status: resolved
Blocked by: 30
Skills: `wizard` para guiar os passos do dono; apoio: `run` para ver funcionando; HITL (credencial AWS e senhas do dono, celular de verdade)
Modelo recomendado: Sonnet
Effort recomendado: low
Issue: #130
Origem: [ticket 30](30-login-no-app.md) (código só verificado contra o Cognito falso dos testes) e nota do [ticket 28](28-infra-prod-dev-e-primeiro-deploy.md) sobre o `Authorization` no CloudFront

## O que fazer

O login do ticket 30 foi testado contra o Cognito falso (`web/e2e/cognito-falso.ts`), que não confere a senha nem roda o SRP do lado do servidor. Falta ver, no `dev` e depois no `prod`, o login com o Cognito de verdade e um token real passando pelo CloudFront até a API.

Assistente pronto: `scripts/conferir-login-real.sh dev` guia os passos do dono (cria os usuários, confere o login errado/certo, "API no ar" e o desconectar); `scripts/conferir-login-real.sh prod` repete a criação no prod. O dono roda com a credencial AWS dele; os itens abaixo só são marcados depois da execução.

## Checklist

- [x] Dono cria os dois usuários no `dev` com `scripts/usuarios-do-app.sh criar dev <email>` e confere com `listar dev` que só eles existem
- [x] Login pelo formulário no endereço do `dev`, com a senha certa (entra) e com uma errada ("E-mail ou senha incorretos."): confirma o SRP contra o Cognito
- [x] Com o login feito, a tela mostra "API no ar": o CloudFront passa o `Authorization` à HTTP API (`/api/*` com `AllViewerExceptHostHeader`) e a Lambda confere o JWT pelo JWKS do user pool
- [x] `scripts/usuarios-do-app.sh desconectar dev <email>` e, depois de até 15 minutos, o app pede o login de novo com "Sua sessão foi encerrada. Entre de novo."
- [x] Repetir a criação dos dois usuários no `prod` depois do merge do ticket 30
- [x] Se algo falhar, abrir ticket com o que foi visto

## Resultado

O dono rodou `scripts/conferir-login-real.sh` no `dev` e no `prod` e informou que terminaram com sucesso (criação dos usuários, login com senha certa, "API no ar" e desconectar). Nenhuma falha a registrar.
