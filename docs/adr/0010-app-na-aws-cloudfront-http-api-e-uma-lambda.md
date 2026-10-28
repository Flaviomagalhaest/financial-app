---
status: accepted
---

# App na AWS: CloudFront, HTTP API e uma Lambda, com login do Cognito no app

O app roda em sa-east-1 sem servidor ligado. A PWA fica num S3 privado servido pelo CloudFront no endereço padrão `dxxxx.cloudfront.net`. O mesmo endereço leva `/api/*` a uma API Gateway HTTP API, que confere o JWT do Cognito e chama **uma Lambda** com a API inteira (FastAPI). O login é um formulário dentro do app que fala direto com um user pool do Cognito, sem redirecionamento. A infraestrutura é código CDK em TypeScript, com as pilhas `prod` e `dev` na mesma conta. Tudo cabe nas franquias (fora o DSQL, de US$ 0,01 a 0,06 por mês), e a API depende só de um JWT padrão, não do Cognito.

## Considered Options

- **URL de função da Lambda em vez da HTTP API**: grátis, mas a Lambda conferiria o JWT no código e o único limite de taxa seria a concorrência reservada. A HTTP API custa US$ 1,59 por milhão de chamadas e barra o pedido sem login antes da Lambda.
- **CloudFront direto na URL de função, com OAC**: o app teria de mandar o SHA-256 do corpo em todo POST e PUT.
- **Uma Lambda por rota**: cada tela acordaria uma função fria; com dois usuários, quase toda chamada.
- **Login gerenciado do Cognito, com redirecionamento**: no app da Tela de Início do iPhone, o login em outra origem pode ficar preso numa janela do Safari.
- **Login próprio na API**: sem amarra, mas é código de segurança escrito por nós.
- **Passkey ou TOTP**: a passkey fica presa ao endereço do CloudFront e morre se a distribuição for recriada; o TOTP é um passo a mais num login que acontece raramente.
- **SAM ou Terraform**: o SAM é prolixo para CloudFront e Cognito; o Terraform exige um bucket de estado e uma ferramenta a mais.
- **Contrato escrito à mão (`openapi.yaml`)**: mais trabalho a cada mudança.

## Consequences

- **A PWA instalada fica presa ao endereço do CloudFront.** Recriar a distribuição muda o endereço, e os dois reinstalam o app e perdem a fila offline. A distribuição é protegida contra substituição e remoção na pilha.
- **Contrato** (pendência do [ADR 0001](0001-backend-em-python.md)): a FastAPI gera o OpenAPI, versionado no repositório; o app gera os tipos TypeScript a partir dele, e o CI falha se estiverem desatualizados.
- **Sessão**: refresh token de 10 anos, sem rotação (a do Cognito não estende a sessão), guardado no IndexedDB do app instalado e nunca em cookie. Token de acesso de 15 minutos: é o tempo que um celular perdido continua acessando a API depois de `AdminUserGlobalSignOut`, porque o authorizer JWT não vê a revogação. O login é feito dentro do app já instalado, porque instalar não leva o armazenamento do Safari. O token de identidade também vale 15 minutos, porque a API aceita qualquer JWT do cliente do app (`aud` ou `client_id`, como o authorizer).
- **Amarra ao Cognito**: fica só no módulo de login do app e na lista de usuários. Trocar de provedor é recriar 2 usuários e mudar emissor e audiência na configuração.
- **Mesmo endereço para app e API**: sem CORS e sem preflight; `/api/*` passa pelo CloudFront sem cache.
- A HTTP API tem limite de taxa no stage (10 por segundo, rajada de 20), para segurar o custo se o endereço for atacado; chamadas recusadas por falta de login contam como cobradas.
- Nenhum segredo: o DSQL entra por IAM e o Cognito usa um cliente público.
- O backup diário é outra Lambda do mesmo pacote, chamada pelo EventBridge Scheduler, e grava num S3 com versões e Object Lock em compliance por 90 dias. O cálculo pesado de ciência de dados, quando existir, pode virar outra Lambda.
- As migrations são arquivos SQL numerados, um DDL por arquivo (limite do DSQL), aplicados pelo job de deploy antes da Lambda nova. Cada migration é compatível com a versão anterior da Lambda.
- O deploy sai pelo GitHub Actions com OIDC, sem chave de longa duração: o merge na `main` publica em `prod`. A política de confiança usa o formato novo do `sub` do GitHub, que este repositório já usa.
- A SCP da organização fica fora da infraestrutura como código, porque o repositório do app não deve ter credencial da conta de gerência.
