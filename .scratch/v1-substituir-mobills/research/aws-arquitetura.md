# Fatos da arquitetura na AWS (sa-east-1, dois usuários)

Origem: ticket [12 - Como o app roda na AWS](../issues/12-como-o-app-roda-na-aws.md), do [mapa V1](../map.md); contexto no [ADR 0009](../../../docs/adr/0009-aurora-dsql-em-sao-paulo.md).
Data de acesso de todas as fontes: **2026-10-25**. Branch: `research/aws-arquitetura` (não mesclada, sem PR).

Esta nota só levanta fatos. A escolha da arquitetura é do ticket 12 (grilling com o dono).

## Resumo

1. **Tudo o que foi perguntado existe em sa-east-1**: Cognito (Lite e Essentials, managed login), API Gateway HTTP API com authorizer JWT, URL de função do Lambda, Lambda arm64, Python 3.14, EventBridge Scheduler, S3 Object Lock e OAC do CloudFront. Budgets é global (endpoint único em us-east-1), mas o recurso `AWS::Budgets::Budget` está na especificação do CloudFormation de sa-east-1, então pode ir na mesma stack [A1, A3, A4, A20].
2. **Premissas que se confirmam**: authorizer JWT em sa-east-1; Cognito Lite/Essentials com 10.000 MAU grátis por mês, sem prazo; refresh token de até 3.650 dias (10 anos) [A6, A7, A9].
3. **Premissas que não se confirmam ou mudam:**
   - **Requisição recusada pelo authorizer JWT (401) cobrada ou não: não confirmado.** Nenhuma página oficial diz que a HTTP API deixa de cobrar requisições não autorizadas. A FAQ só dá essa isenção para mensagens de **WebSocket API** e diz que a cobrança é por "API calls received" [A11]. Trate como **cobrada** (US$ 1,59 por milhão em sa-east-1).
   - **App da Tela de Início do iPhone e redirecionamento OAuth para outra origem: não "quebra" sempre, mas é incerto.** A Apple diz que, no iOS, link para fora do escopo do app abre numa Safari View Controller dentro do app, que login OAuth em domínio de terceiro "continua no web app" **por heurística**, e que `window.open` sempre abre dentro do app [A30]. Há relatos de terceiros de login que fica preso na folha do Safari [A33]. Não há documento da Apple que garanta o retorno com o armazenamento do app. O login dentro do próprio app (SDK do Cognito, sem redirecionamento) evita a questão inteira.
   - **SCP: o limite agora é 10.240 caracteres e até 10 SCPs por raiz, OU ou conta** (era 5.120 e 5), desde 15/05/2026 [A27, A28]. A SCP `p-q0eemrzp` (5.094 caracteres) tem folga de mais de 5 mil caracteres; não é preciso dividi-la.
4. **Rotação de refresh token não estende a sessão**: cada novo refresh token vale só o que restava do original. Com rotação ligada, o usuário entra de novo ao fim do `RefreshTokenValidity`, mesmo usando o app todo dia [A7].
5. **Revogar token não derruba o access token no authorizer JWT**: a documentação do Cognito diz que tokens revogados continuam válidos para quem só verifica assinatura e expiração, que é o que o authorizer JWT faz. O access token revogado vale até expirar (padrão 1 hora, máximo 1 dia) [A10, A12].
6. **Passkey e domínio `*.cloudfront.net`**: `cloudfront.net` está na Public Suffix List, então o RP ID só pode ser o domínio inteiro da distribuição (`dxxxx.cloudfront.net`), nunca `cloudfront.net` [A8, A31]. **[inferência]** Recriar a distribuição muda o domínio e invalida todas as passkeys.
7. **CloudFront com OAC na frente de URL de função**: o cliente precisa mandar o SHA-256 do corpo em `x-amz-content-sha256` em todo POST e PUT; o Lambda não aceita payload sem assinatura [A14].
8. **Custo estimado da infraestrutura (sem o DSQL): de US$ 0,01 a US$ 0,25 por mês**, quase tudo no backup em S3 e nas requisições da HTTP API. Ver [Ordem de grandeza](#ordem-de-grandeza-do-custo).
9. **Free tier da HTTP API é de 12 meses, não "sempre grátis"**; Lambda, CloudFront, Cognito, EventBridge e CloudWatch são "sempre grátis"; Secrets Manager é só teste curto [A2, A5]. Para conta criada depois de 15/07/2025, a documentação só cita "sempre grátis", testes curtos e créditos; se a conta filha tem os 12 meses da HTTP API é **não confirmado** [A21].
10. **Ação no GitHub Actions por OIDC dispensa chave de longa duração**, mas este repositório (criado em 2026-10-24) usa o **formato novo e imutável do `sub`**: `repo:Flaviomagalhaest@14982168/financial-app@1432589902:ref:refs/heads/main`. Política de confiança escrita no formato antigo não vai casar [A25, A26].

## Tabela: premissas do pedido

| Premissa | Resultado | Confiança | Fonte |
|---|---|---|---|
| HTTP API com authorizer JWT existe em sa-east-1 | **Confirmada**: endpoint `execute-api.sa-east-1`, preço `SAE1-ApiGatewayHttpRequest`, recurso `AWS::ApiGatewayV2::Authorizer` na especificação de sa-east-1; a documentação do authorizer não tem ressalva de região | Alta | A1, A3, A4, A12 |
| Cognito Essentials com 10 mil MAU grátis | **Confirmada**: 10.000 MAU por mês, por conta **ou por organização**, somando Lite e Essentials; não expira; Plus não tem free tier | Alta | A6, A1 |
| Refresh token até 3.650 dias | **Confirmada**: de 60 minutos a 10 anos; API aceita até 315.360.000 s | Alta | A7, A9 |
| Requisição não autorizada na HTTP API não é cobrada | **Não confirmado**; a isenção oficial é só de WebSocket | Média (de que é cobrada) | A11 |
| App da Tela de Início do iOS quebra com redirecionamento OAuth para outra origem | **Parcial**: fora do escopo abre Safari View Controller; OAuth fica no app "por heurística"; `window.open` fica sempre no app | Média | A30, A32, A33 |

## 1. Disponibilidade em sa-east-1

| Serviço ou recurso | Em sa-east-1? | Evidência | Confiança |
|---|---|---|---|
| Cognito user pools | Sim | Endpoint `cognito-idp.sa-east-1.amazonaws.com` [A3] | Alta |
| Cognito Lite e Essentials | Sim | Preços `SAE1-CognitoLiteMAU` e `SAE1-CognitoEssentialsMAU` na lista de sa-east-1 [A1] | Alta |
| Managed login (páginas hospedadas novas) | Sim | Recurso do plano Essentials/Plus; a documentação não tem ressalva de região [A13]; `AWS::Cognito::ManagedLoginBranding` na especificação do CloudFormation de sa-east-1 [A20]; `auth.sa-east-1.amazoncognito.com` na Public Suffix List [A31] | Alta |
| API Gateway HTTP API + authorizer JWT | Sim | Endpoint `execute-api.sa-east-1` [A3]; preço HTTP API em sa-east-1 [A1]; `AWS::ApiGatewayV2::Authorizer` em sa-east-1 [A20] | Alta |
| URL de função do Lambda | Sim (indireto) | A documentação diz que "não está em todas as regiões" e manda ver a tabela regional [A15]; o anúncio de 2022 diz "todas as regiões comerciais onde o Lambda existe, exceto China" [A16]; `lambda-url.sa-east-1.on.aws` está na Public Suffix List (inserido pela AWS) [A31]; `AWS::Lambda::Url` na especificação de sa-east-1 [A20] | Alta |
| Lambda arm64 (Graviton) | Sim | Preço `SAE1-Lambda-GB-Second-ARM` [A1]; anúncio de 2022 incluiu São Paulo [A17] | Alta |
| Runtime Python mais novo em GA | **Python 3.14** (`python3.14`, Amazon Linux 2023, descontinuação em 30/06/2029). Python 3.15 está em **prévia pública** (sem SLA, não usar em produção) | Tabela de runtimes [A18] | Alta |
| EventBridge Scheduler | Sim | Endpoint `scheduler.sa-east-1.amazonaws.com` [A3]; preço `SAE1-ScheduledInvocation` [A1] | Alta |
| S3 Object Lock | Sim | Recurso de bucket de uso geral sem ressalva de região na documentação [A23] | Alta |
| AWS Budgets | Global | Endpoint `budgets.amazonaws.com` (região us-east-1) [A3]; `AWS::Budgets::Budget` e `AWS::Budgets::BudgetsAction` na especificação de sa-east-1 [A20] | Alta |
| OAC do CloudFront para S3 | Sim | "Todos os buckets S3 em todas as regiões" [A14]; CloudFront é global | Alta |
| OAC do CloudFront para URL de função | Sim | Documentação própria [A14]; CDK tem `FunctionUrlOrigin.withOriginAccessControl` [A22] | Alta |

Achado lateral: a AWS lançou **Lambda Web Functions** (cobradas por requisição, CPU ativa e memória **pelo tempo em que o ambiente fica ligado**, inclusive entre requisições) e **Lambda MicroVMs**; o Lambda clássico agora se chama "Event Functions" [A5]. Há preço de Web Functions em sa-east-1 (`SAE1-Lambda-Web-Request-ARM`, US$ 0,30 por milhão) [A1]. **[inferência]** Para tráfego de dois usuários, a memória cobrada entre requisições tende a pesar mais que nas Event Functions; não pesquisei o free tier nem o tempo de vida do ambiente.

## 2. Preços em sa-east-1

Preços de lista da API pública de preços (JSON) [A1], conferidos com as páginas de preço [A2, A5].

| Item | sa-east-1 | Free tier | Tipo de free tier | Fonte |
|---|---|---|---|---|
| HTTP API, requisições | US$ 1,59 por milhão (até 300 milhões); us-east-1: US$ 1,00 | 1 milhão de chamadas por mês | **12 meses**, só cliente novo | A1, A2 |
| REST API (referência) | US$ 4,25 por milhão | 1 milhão por mês | 12 meses | A1, A2 |
| Lambda, requisições | US$ 0,20 por milhão (x86 e arm) | 1 milhão por mês | Sempre grátis (global) | A1, A5 |
| Lambda, duração | US$ 0,0000166667 por GB-s (x86); **US$ 0,0000133334 por GB-s (arm)** | 400.000 GB-s por mês | Sempre grátis (global) | A1, A5 |
| S3 Standard, armazenamento | US$ 0,0405 por GB-mês (primeiros 50 TB) | 5 GB (12 meses, cliente novo) | 12 meses | A1, A5 |
| S3, PUT/LIST | US$ 0,007 por mil | idem | | A1 |
| S3, GET | US$ 0,00056 por mil | idem | | A1 |
| CloudFront pago por uso | | **1 TB de saída e 10 milhões de requisições por mês** | Sempre grátis | A1, A19 |
| CloudFront plano fixo "Free" | US$ 0 por mês | 1 milhão de requisições, 100 GB, 5 GB de S3 incluídos; WAF com 5 regras; sem cobrança de excedente | Plano | A19 |
| Cognito Lite | US$ 0,0055 por MAU acima do free tier | 10.000 MAU (somado com Essentials) | Sempre grátis, por conta ou organização | A1, A6 |
| Cognito Essentials | US$ 0,015 por MAU acima do free tier | 10.000 MAU (somado com Lite) | Sempre grátis, por conta ou organização | A1, A6 |
| Cognito Plus | US$ 0,020 por MAU | nenhum | | A1, A6 |
| EventBridge Scheduler | US$ 1,70 por milhão de invocações (sa-east-1) | **14 milhões de invocações por mês**, somadas em todas as regiões | Sempre grátis | A1, A5 |
| CloudWatch Logs, ingestão (Standard) | **US$ 0,90 por GB** | 5 GB por mês (ingestão, arquivo e varredura do Logs Insights) | Sempre grátis | A1, A5 |
| CloudWatch Logs, armazenamento | US$ 0,0408 por GB-mês | dentro dos 5 GB | | A1 |
| Secrets Manager | **US$ 0,40 por segredo por mês** + US$ 0,05 por 10 mil chamadas | só teste curto | Teste | A1, A2 |
| AWS Budgets | Grátis (monitorar e alertar) | 2 orçamentos com ação grátis por mês; depois US$ 0,10 por dia cada | | A1, A24 |
| Budgets Reports | US$ 0,01 por relatório enviado | | | A1, A24 |

Observações:

- A página do Cognito diz que o free tier "não expira no fim dos 12 meses" e vale para clientes novos e antigos, por conta **ou por organização** [A6]. Como no DSQL, outras contas da organização podem dividir os 10 mil MAU.
- O tipo de cada free tier vem do diretório que alimenta a página aws.amazon.com/free [A2]: Lambda, CloudFront, Cognito, EventBridge e CloudWatch são `always-free`; API Gateway e S3 são `12monthsfree`; Secrets Manager e Budgets são `trial`.
- **[inferência]** Com autenticação no DSQL só por IAM (ADR 0009), não há senha de banco a guardar; o Secrets Manager só entraria se surgir outro segredo (US$ 0,40 por mês cada, 40% da meta de US$ 1).

## 3. HTTP API: cobrança de 401 e limitação de taxa

- **Requisição recusada pelo authorizer JWT: não confirmado se é cobrada.** A FAQ diz que a cobrança é "por milhão de chamadas de API" e, para HTTP e REST, "você paga só pelas chamadas que recebe". A única isenção explícita é: "se mensagens na conexão WebSocket falham na autenticação ou autorização, elas não contam" [A11]. A página de preços não fala de autorização [A2]. Uma resposta no re:Post sobre REST API diz que requisições não autorizadas não são cobradas, mas não é fonte primária e o site recusou o acesso (403 do CloudFront) nesta sessão. **Planeje como cobrada.**
- **Como o authorizer JWT recusa**: verifica `kid`, `iss`, `aud` (ou `client_id` se não houver `aud`; é o caso do access token do Cognito), `exp`, `nbf`, `iat` e escopos da rota; qualquer falha nega a requisição. A chave pública do `jwks_uri` fica em cache até 2 horas [A12].
- **Limitação de taxa na HTTP API** [A12b]:
  - limite da conta por região (taxa e rajada, token bucket), aumentável por suporte;
  - limite por **estágio** (rota padrão do estágio) e por **rota**, via `update-stage --route-settings` (`ThrottlingBurstLimit`, `ThrottlingRateLimit`); não pode passar do limite da conta;
  - acima do limite, resposta 429; os limites são "metas de melhor esforço", não tetos garantidos.
- **O que a HTTP API não tem** (tem só a REST API): chaves de API, limite por cliente, plano de uso, **AWS WAF**, cache, validação de requisição [A12c].
- **URL de função sem API Gateway**: a única limitação de taxa é a concorrência reservada (RPS máximo = 10 × concorrência reservada; acima disso, 429) [A15]. Só dá para reservar até "concorrência não reservada da conta menos 100" [A15b]; a cota padrão documentada é 1.000 [A15c]. **[inferência]** Se a conta nova tiver cota menor que 100, não dá para reservar concorrência; conferir no Service Quotas.

## 4. Cognito

**Validade do refresh token.** De 60 minutos a 10 anos; padrão 30 dias [A7]. Na API, `RefreshTokenValidity` vai até 315.360.000 segundos (3.650 dias) [A9]. Access e ID token: até 86.400 s (1 dia), padrão 1 hora [A9].

**Rotação de refresh token.** Disponível nos planos **Essentials e Plus** (não no Lite) [A6b, A7b]. Configurada por app client (`RefreshTokenRotation`), desligada por padrão, carência de até 60 s para o token antigo [A7]. Pontos que importam:

- A rotação **não estende a janela**: o novo refresh token vale só o tempo que restava do original; ao fim do `RefreshTokenValidity` o usuário entra de novo [A7].
- Com rotação ligada, o fluxo `REFRESH_TOKEN_AUTH` deixa de funcionar; é preciso usar `GetTokensFromRefreshToken` [A7].
- **[inferência a partir de A34]** Se o refresh token ficar em **cookie**, o iOS 17.2+ copia o cookie do Safari para o app instalado ao "Adicionar à Tela de Início"; com rotação e detecção de reuso, Safari e app passam a disputar o mesmo token (bug WebKit 325412, aberto em 27/09/2026, sem resposta da Apple). Não pesquisei se a rotação do Cognito revoga a família inteira quando um token antigo é reusado fora da carência.

**Passkeys (WebAuthn).** Planos Essentials e Plus; só no fluxo de escolha (`USER_AUTH`); até 20 passkeys por usuário; só registra depois de entrar uma vez [A8]. O RP ID:

- padrão: domínio personalizado do user pool; sem domínio personalizado, o **domínio de prefixo** (`<prefixo>.auth.sa-east-1.amazoncognito.com`) [A8];
- pode ser qualquer domínio **fora da Public Suffix List**, configurado em `WebAuthnConfiguration.RelyingPartyId` ("domínio de terceiro", para apps que autenticam pelo SDK sem as páginas hospedadas) [A8];
- `cloudfront.net` está na Public Suffix List (inserido pela Amazon) [A31]; então o RP ID do app pode ser `dxxxx.cloudfront.net`, mas não `cloudfront.net`;
- mudar o RP ID obriga todos a registrar de novo [A8].

**[inferência]** Duas consequências: (a) passkey registrada nas páginas hospedadas (RP ID do domínio de prefixo do Cognito) não serve para login pelo SDK dentro do app em `dxxxx.cloudfront.net`, e vice-versa; escolher um dos dois caminhos; (b) recriar a distribuição do CloudFront troca o domínio e invalida as passkeys com RP ID nele. Há um bug WebKit aberto (291258) em que o pedido de Face ID do WebAuthn aparece em outro app da Tela de Início [A35].

**USER_SRP_AUTH e USER_PASSWORD_AUTH em cliente público.** Cliente público = sem segredo, roda no navegador [A10b]. O `SECRET_HASH` só é exigido "se o app client tem segredo" [A9b]. Os dois fluxos são ativados no app client (`ALLOW_USER_SRP_AUTH`, `ALLOW_USER_PASSWORD_AUTH`); sem configuração, o cliente aceita `ALLOW_REFRESH_TOKEN_AUTH`, `ALLOW_USER_SRP_AUTH` e `ALLOW_CUSTOM_AUTH` [A9, A13b]. Login, senha, SRP e refresh valem em todos os planos, inclusive Lite [A6b]. Confiança alta.

**AdminCreateUser com cadastro próprio desligado.** Sem "self-registration", usuário novo só nasce por API administrativa com credencial IAM (ou federação) [A13c]. O usuário criado recebe senha temporária e fica em `FORCE_CHANGE_PASSWORD` até responder ao desafio `NEW_PASSWORD_REQUIRED`; `AdminSetUserPassword` com `Permanent=true` confirma sem esse passo [A13c]. Confiança alta.

**Revogação.** `AdminUserGlobalSignOut` (IAM, lado servidor) e `GlobalSignOut` (pelo próprio usuário) revogam todos os refresh, ID e access tokens do usuário; `RevokeToken` e o endpoint de revogação revogam um refresh token e os tokens filhos [A10]. A revogação vem ligada por padrão em app client novo. **Tokens revogados continuam válidos para qualquer biblioteca que só verifique assinatura e expiração** [A10]; o authorizer JWT da HTTP API faz exatamente isso [A12]. Confiança alta.

**E-mail padrão do Cognito.** Remetente `no-reply@verificationemail.com`; **50 e-mails por dia por conta AWS** (`COGNITO_DEFAULT`); para mais, usar SES [A13d]. Para dois usuários criados à mão, basta.

## 5. App da Tela de Início do iPhone e OAuth em outra origem

Fontes da Apple/WebKit:

- **Fora do escopo abre Safari View Controller**: "nos web apps da Tela de Início no iOS, links fora do escopo abrem em Safari View Controller"; o escopo padrão é o host da página usada para criar o app [A30] (WWDC23, sessão 10120).
- **OAuth "por heurística"**: "Autenticação por OAuth em domínio de terceiro continua abrindo no seu web app. Isso é feito por heurística. Se o seu fluxo OAuth abrir no navegador padrão, mande feedback." E: "**links carregados por `window.open` sempre abrem no web app, qualquer que seja o escopo**" [A30]. O trecho está na parte sobre web apps no Mac, logo após a frase sobre o iOS; **não confirmado** que a heurística vale igual no iPhone.
- **Correção no Safari 17.2**: "páginas de login às vezes abriam no Safari em vez do web app" (113520837) [A32].
- **Cookies e armazenamento**: no iOS 17.2+, "Adicionar à Tela de Início" copia os **cookies** do Safari para o app; **nenhum outro armazenamento** (localStorage, IndexedDB) é copiado; depois disso, nada mais é compartilhado [A32]. Cookies escritos por JavaScript têm validade máxima de 7 dias também no app da Tela de Início; cookies de servidor e o armazenamento HTML do domínio principal não são apagados (engenheiro da Apple no bug WebKit 237350) [A36].
- **Bug WebKit 250651** (aberto): janela aberta a partir do app com link externo herda `display-mode: standalone`; engenheiro da Apple confirma que o sistema cria uma web view secundária com o manifesto do app [A37].

Relatos de terceiros (não oficiais):

- Login com Google num app da Tela de Início abre o redirecionamento numa folha do Safari; o cookie PKCE gravado no app não chega no retorno, a primeira tentativa falha e a sessão fica presa na folha [A33].

**Resposta.** O redirecionamento na mesma janela para o domínio do Cognito **pode** abrir numa Safari View Controller com armazenamento separado, e o retorno ao app não é garantido por documento da Apple. A própria Apple oferece duas saídas: `window.open` (fica no app) ou não sair do app. **[inferência]** Login pelo SDK do Cognito dentro do app (SRP, senha ou passkey com RP ID `dxxxx.cloudfront.net`) não navega para outra origem e não depende da heurística. Confiança: média. Teste em aparelho real recomendado (ticket 17, se o dono quiser).

## 6. CloudFront + URL de função com OAC

- **Obrigatório**: "Se você usa PUT ou POST com a URL de função, os usuários precisam calcular o SHA-256 do corpo e enviar o hash no cabeçalho `x-amz-content-sha256` ao mandar a requisição ao CloudFront. **O Lambda não aceita payload sem assinatura**" [A14].
- A URL precisa de `AuthType = AWS_IAM`; a política da URL só pode ser editada pela CLI (não pelo console) [A14].
- Lambda Web Functions usam outra configuração de OAC [A14]; não pesquisei se a exigência do hash vale para elas.
- **[inferência]** No navegador, isso significa calcular `crypto.subtle.digest('SHA-256', corpo)` em todo POST/PUT/PATCH do app; a HTTP API não tem essa exigência.

## 7. AWS Budgets e Cost Anomaly Detection

- **Custo**: monitorar e alertar é grátis; os **2 primeiros orçamentos com ação** são grátis por mês, depois **US$ 0,10 por dia** por orçamento com ação; relatório por e-mail US$ 0,01 cada [A1, A24].
- **Excluir créditos e reembolsos**: orçamento de custo pode incluir ou excluir créditos, reembolsos, impostos, suporte etc. [A24b]. No CloudFormation, `CostTypes.IncludeCredit` e `CostTypes.IncludeRefund` têm **padrão `true`**; é preciso pôr `false` para o crédito não esconder o uso [A20b]. O recurso também tem `FilterExpression` e `Metrics` (sem descrição na página) [A20c]. No console, o filtro "Charge type" tem "Credit" e "Refund" [A24c].
- **Alertas**: até 10 e-mails e 1 tópico SNS por alerta; alerta de valor real sai uma vez por período; dados de cobrança atualizam ao menos uma vez por dia [A24b].
- **CloudFormation/CDK em sa-east-1**: `AWS::Budgets::Budget`, `AWS::Budgets::BudgetsAction`, `AWS::CE::AnomalyMonitor` e `AWS::CE::AnomalySubscription` estão na especificação de recursos do CloudFormation de **sa-east-1** (versão 269.0.0) [A20]. Confiança alta para "pode ir numa stack em sa-east-1".
- **Cost Anomaly Detection**: "disponível sem custo adicional" [A29]. Alertas: até 10 e-mails ou 1 SNS por assinatura [A29b].

## 8. CDK bootstrap e Terraform

**O que a stack `CDKToolkit` cria** (template versão 32, branch `main` do `aws-cdk-cli`, commit `0c223c4`) [A38, A39]:

| Recurso | Detalhe | Custo |
|---|---|---|
| Bucket S3 `cdk-<qualifier>-assets-<conta>-<região>` | Versionado; versões antigas expiram em 30 dias; multipart incompleto em 1 dia; SSE-KMS com chave gerenciada pela AWS (padrão) | Armazenamento dos artefatos (zip do Lambda), US$ 0,0405 por GB-mês |
| Repositório ECR | Imagens imutáveis; imagens sem tag expiram em 365 dias | Só se houver imagem Docker (não é o caso de zip) |
| Chave KMS própria | **Só** com `--bootstrap-customer-key`; o padrão atual é sem chave, para evitar a cobrança | US$ 0 no padrão |
| Papéis e políticas IAM (deploy, lookup, publicação de arquivos e imagens, execução do CloudFormation) | | Grátis |
| Parâmetro SSM `/cdk-bootstrap/<qualifier>/version` | | Grátis (parâmetro padrão) |

**[inferência]** Custo do bootstrap: centavos por mês (alguns MB de zip do Lambda no bucket).

**Uma stack só em sa-east-1 sem domínio próprio**: dá. O certificado ACM em us-east-1 só é exigido para domínio próprio no CloudFront [A40]; Lambda@Edge e WAF do CloudFront também exigiriam us-east-1, mas não estão na lista [A22]. A distribuição CloudFront, o OAC (S3 e URL de função), o Cognito, a HTTP API, o Lambda, o Scheduler, o S3 e o Budget estão todos na especificação do CloudFormation de sa-east-1 [A20]. Confiança alta.

**Terraform, backend S3**: travamento nativo por arquivo no S3 com `use_lockfile = true` (padrão `false`); o travamento por DynamoDB está **descontinuado** e "será removido numa versão menor futura" [A41] (documentação "latest", que lista até a v1.17.x).

## 9. GitHub Actions por OIDC

- Confirmado: OIDC permite o workflow acessar a AWS "sem guardar credenciais como segredos de longa duração" [A25]. Provedor `https://token.actions.githubusercontent.com`, audiência `sts.amazonaws.com`, permissão `id-token: write` no job, condição em `token.actions.githubusercontent.com:sub` na política de confiança [A25].
- **Formato do `sub` mudou**: repositórios criados **depois de 15/07/2026** usam `repo:DONO@ID-DONO/REPO@ID-REPO:ref:refs/heads/BRANCH` [A26]. Este repositório foi criado em **2026-10-24** (`gh api`), dono id `14982168`, repo id `1432589902`. A condição para a `main` fica `repo:Flaviomagalhaest@14982168/financial-app@1432589902:ref:refs/heads/main`. Com ambiente do GitHub, o `sub` passa a terminar em `:environment:<nome>` [A25].
- Impressão digital (thumbprint): a AWS valida o certificado do provedor pela própria lista de CAs confiáveis e só usa a impressão digital como recurso de reserva [A42].

## 10. S3 Object Lock

- **Governança**: ninguém apaga nem sobrescreve a versão, exceto quem tem `s3:BypassGovernanceRetention` e manda `x-amz-bypass-governance-retention:true` [A23].
- **Conformidade**: ninguém apaga, **nem o root**; o modo não muda e o prazo não encurta; o único jeito de apagar antes é **encerrar a conta AWS** [A23].
- **Bucket existente**: dá para ligar Object Lock em bucket existente (console, CLI, SDK, REST), desde que esteja versionado [A23b].
- **Irreversível**: depois de ligado, não dá para desligar o Object Lock nem suspender o versionamento [A23b].
- **Retenção padrão do bucket**: em dias ou anos; cada nova versão ganha "Retain Until Date" = criação + prazo; retenção explícita na versão vence a padrão; trava protege a versão, mas não impede novas versões nem marcadores de exclusão [A23].
- **Ciclo de vida**: "o S3 não toma nenhuma ação sobre versões não atuais de objetos com configuração de Object Lock" [A43]. **Não confirmado** se a expiração por ciclo de vida apaga a versão depois que a retenção vence; o texto é ambíguo.
- Buckets com Object Lock não podem ser destino de logs de acesso do servidor [A23b].

## 11. SCP

- **Tamanho máximo de uma SCP: 10.240 caracteres** (não mais 5.120). **Até 10 SCPs** anexadas à raiz, a cada OU e a cada conta (não mais 5); mínimo de 1 por entidade. Limites rígidos [A27].
- Mudança anunciada em **15/05/2026**, automática para todas as organizações [A28].
- Espaços em branco: o console remove os excedentes antes de contar; SDK e CLI gravam o texto como enviado [A27].
- RCP continua com 5.120 caracteres e 5 por entidade [A27].
- Algumas páginas antigas (referência do CloudFormation, artigo do Knowledge Center) ainda mostram 5.120 e 5; vale a página de cotas e o anúncio.

## Ordem de grandeza do custo

**Suposições** (minhas, não medidas): 6.000 requisições à API por mês (as 5.400 consultas e escritas da [nota do banco](banco-de-dados-aws.md#suposições) mais renovações de token); Lambda arm64 com 512 MB e 300 ms por requisição; 50 MB de log por mês; backup diário de 2 a 12 MB compactado, guardado 90 dias; 2 MAU no Cognito; um alerta de Budgets sem ação.

| Item | Conta | US$ por mês |
|---|---|---|
| HTTP API (sem free tier) | 6.000 × 1,59 / 1.000.000 | 0,01 |
| Lambda | 6.000 req e 900 GB-s, dentro do sempre grátis | 0,00 |
| Cognito Essentials | 2 MAU, dentro dos 10 mil | 0,00 |
| CloudFront (pago por uso) | dentro de 1 TB e 10 milhões | 0,00 |
| S3 do app (estático) | alguns MB | < 0,01 |
| S3 do backup | 90 × (2 a 12 MB) = 0,18 a 1,08 GB × 0,0405 + 30 PUT | 0,01 a 0,04 |
| EventBridge Scheduler | 30 invocações | 0,00 |
| CloudWatch Logs | 0,05 GB, dentro dos 5 GB | 0,00 |
| Budgets e Cost Anomaly Detection | | 0,00 |
| Bucket do CDK bootstrap | alguns MB | < 0,01 |
| **Total (sem DSQL)** | | **cerca de 0,01 a 0,06** |

Cenários piores: backup sem compressão (61 MB por dia × 90 = 5,5 GB) leva o S3 do backup a US$ 0,22; um Secrets Manager somaria US$ 0,40. Mesmo assim o total fica em cerca de US$ 0,25 sem segredo, dentro da meta de US$ 0 a 1.

## Lacunas

- **Cobrança de 401 na HTTP API**: nenhuma fonte oficial. Dá para medir: chamar a API sem token algumas mil vezes e olhar o uso `ApiGatewayHttpRequest` no Cost Explorer no dia seguinte.
- **OAuth com redirecionamento no app da Tela de Início do iPhone (iOS 26)**: a fonte oficial é de 2023 e mistura Mac e iOS; testar em aparelho.
- **Rotação de refresh token no Cognito**: comportamento quando um token antigo é reusado depois da carência (revoga a família ou só recusa?) não pesquisado.
- **Cota de concorrência do Lambda em conta nova**: a documentação dá 1.000 como padrão; conferir no Service Quotas da conta filha.
- **Free tier de 12 meses da HTTP API e do S3 na conta filha** (criada depois de 15/07/2025 e dentro de uma organização): a documentação atual só fala em "sempre grátis", testes e créditos.
- **Lambda Web Functions**: preço por memória ligada, free tier, OAC; só citadas.
- **Expiração por ciclo de vida de versões com Object Lock vencido**: texto ambíguo.
- **re:Post**: bloqueado nesta sessão (403); nenhuma afirmação desta nota depende dele.
- Preços sem imposto (IOF e impostos brasileiros não considerados).

## Fontes

Todas acessadas em **2026-10-25**.

Listas de preço e free tier:

- A1. API pública de preços da AWS (JSON), `https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/<serviço>/current/sa-east-1/index.json` para `AmazonApiGateway` (publicado em 2026-10-13), `AWSLambda` (2026-10-22), `AmazonS3` (2026-10-15), `AmazonCognito` (2026-10-20), `AWSEvents` (2026-09-24), `AmazonCloudWatch` (2026-10-07), `AWSSecretsManager` (2026-09-11); e `.../current/index.json` para `AmazonCloudFront` (2026-10-19), `CloudFrontPlans` (2026-09-11) e `AWSBudgets` (2026-09-11). HTTP API em us-east-1: `.../AmazonApiGateway/current/us-east-1/index.json`.
- A2. https://aws.amazon.com/api-gateway/pricing/ (free tier de 12 meses); https://aws.amazon.com/secrets-manager/pricing/; diretório da página de free tier, `https://aws.amazon.com/api/dirs/items/search?item.directoryId=free-tier-products` (marcas `always-free`, `12monthsfree`, `trial`).
- A5. https://aws.amazon.com/lambda/pricing/ (Event, Web Functions, MicroVMs; 1 milhão de requisições e 400.000 GB-s); https://aws.amazon.com/eventbridge/pricing/ (Scheduler, 14 milhões); https://aws.amazon.com/cloudwatch/pricing/ (5 GB de logs).
- A6. https://aws.amazon.com/cognito/pricing/ (planos, free tier de 10.000 MAU por conta ou organização, tabela de recursos por plano: A6b "Support for refresh token rotation" em Essentials e Plus).
- A19. https://aws.amazon.com/cloudfront/pricing/ (planos fixos) e https://aws.amazon.com/cloudfront/pricing/pay-as-you-go/ (sempre grátis: 1 TB e 10 milhões).
- A21. https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/free-tier.html (planos Free/Paid, "sempre grátis" e testes curtos).
- A24. https://aws.amazon.com/aws-cost-management/aws-budgets/pricing/; A24b. https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-best-practices.html; A24c. https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-create-filters.html.

Regiões e especificação do CloudFormation:

- A3. https://docs.aws.amazon.com/general/latest/gr/apigateway.html, `.../gr/cognito_identity.html`, `.../gr/lambda-service.html`, `.../gr/eventbridgescheduler.html`, `.../gr/billing.html` (Budgets).
- A4. Tabela regional de serviços, `https://api.regional-table.region-services.aws.a2z.com/index.json` (nível de serviço; versão da fonte 2025-11-13).
- A20. Especificação de recursos do CloudFormation de sa-east-1, `https://d3c9jyj3w509b0.cloudfront.net/latest/gzip/CloudFormationResourceSpecification.json` (versão 269.0.0; URL listada em https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/cfn-resource-specification.html). A20b. https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-properties-budgets-budget-costtypes.html; A20c. `.../aws-properties-budgets-budget-budgetdata.html`; `.../aws-resource-budgets-budget.html`.

Cognito (`https://docs.aws.amazon.com/cognito/latest/developerguide/`):

- A6b. `cognito-sign-in-feature-plans.html` (recursos por plano).
- A7. `amazon-cognito-user-pools-using-the-refresh-token.html` (10 anos, rotação, janela fixa). A7b. https://aws.amazon.com/about-aws/whats-new/2025/04/amazon-cognito-refresh-token-rotation/ (Essentials ou Plus).
- A8. `amazon-cognito-user-pools-authentication-flow-methods.html` (senha, SRP, passkeys, RP ID, PSL).
- A9. https://docs.aws.amazon.com/cognito-user-identity-pools/latest/APIReference/API_CreateUserPoolClient.html (faixas de validade, fluxos padrão, `RefreshTokenRotation`). A9b. `.../APIReference/API_InitiateAuth.html` (`SECRET_HASH` só com segredo).
- A10. `token-revocation.html`. A10b. `user-pool-settings-client-apps.html` (cliente público e confidencial).
- A13. `cognito-user-pools-managed-login.html`. A13b. ver A8. A13c. `how-to-create-user-accounts.html`. A13d. `user-pool-email.html` e `quotas.html` (50 e-mails por dia).

API Gateway e Lambda:

- A11. https://aws.amazon.com/api-gateway/faqs/ (cobrança; isenção só para WebSocket).
- A12. https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-jwt-authorizer.html. A12b. `.../http-api-throttling.html`. A12c. `.../http-api-vs-rest.html`; cotas em `.../http-api-quotas.html`.
- A14. https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-restricting-access-to-lambda.html e `.../private-content-restricting-access-to-s3.html`.
- A15. https://docs.aws.amazon.com/lambda/latest/dg/urls-configuration.html. A15b. `.../configuration-concurrency.html`. A15c. `.../gettingstarted-limits.html`.
- A16. https://aws.amazon.com/blogs/aws/announcing-aws-lambda-function-urls-built-in-https-endpoints-for-single-function-microservices/ (via busca; não aberto diretamente) e https://aws.amazon.com/about-aws/whats-new/2022/04/aws-lambda-function-urls-built-in-https-endpoints/.
- A17. https://aws.amazon.com/about-aws/whats-new/2022/10/aws-lambda-functions-graviton2-12-regions/ (via busca) e https://docs.aws.amazon.com/lambda/latest/dg/foundation-arch.html.
- A18. https://docs.aws.amazon.com/lambda/latest/dg/lambda-runtimes.html.

CloudFront, CDK, Terraform, S3:

- A22. https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_cloudfront-readme.html e `.../aws-cdk-lib.aws_cloudfront_origins-readme.html`.
- A23. https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock.html. A23b. `.../object-lock-configure.html`.
- A38. https://docs.aws.amazon.com/cdk/v2/guide/bootstrapping.html e `.../bootstrapping-env.html` (chave KMS fora do padrão).
- A39. https://github.com/aws/aws-cdk-cli/blob/main/packages/aws-cdk/lib/api/bootstrap/bootstrap-template.yaml (commit `0c223c4489c176ccf0cfb68919750d4aabdcbaae`).
- A40. https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/cnames-and-https-requirements.html (certificado em us-east-1).
- A41. https://developer.hashicorp.com/terraform/language/backend/s3.
- A43. https://docs.aws.amazon.com/AmazonS3/latest/userguide/lifecycle-expire-general-considerations.html.
- A19b. https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/flat-rate-pricing-plan.html (planos fixos: 3 planos Free por conta, recursos não suportados).

GitHub e IAM:

- A25. https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-aws.
- A26. https://docs.github.com/en/actions/reference/security/oidc (sub imutável desde 15/07/2026). Data de criação e IDs do repositório: `gh api repos/Flaviomagalhaest/financial-app`.
- A42. https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_providers_create_oidc.html.

Organizations e custos:

- A27. https://docs.aws.amazon.com/organizations/latest/userguide/orgs_reference_limits.html.
- A28. https://aws.amazon.com/about-aws/whats-new/2026/05/aws-organizations-increased-scp-quotas/ (publicado em 15/05/2026).
- A29. https://docs.aws.amazon.com/prescriptive-guidance/latest/aws-startup-security-baseline/acct-16.html ("sem custo adicional"). A29b. https://aws.amazon.com/aws-cost-management/aws-cost-anomaly-detection/faqs/. A página https://aws.amazon.com/aws-cost-management/aws-cost-anomaly-detection/pricing/ deu 404.

Apple, WebKit e Public Suffix List:

- A30. https://developer.apple.com/videos/play/wwdc2023/10120/ (transcrição: escopo, Safari View Controller, OAuth por heurística, `window.open`).
- A31. https://publicsuffix.org/list/public_suffix_list.dat (versão 2026-10-22, commit `8437e52`: `cloudfront.net`, `auth.sa-east-1.amazoncognito.com`, `lambda-url.sa-east-1.on.aws`, `execute-api.sa-east-1.amazonaws.com`).
- A32. https://webkit.org/blog/14787/webkit-features-in-safari-17-2/ (cópia de cookies no iOS 17.2; correção de login abrindo no Safari).
- A33. https://github.com/Naijei1/FlashCardApp/pull/19 (relato de terceiro; via busca, não aberto).
- A34. https://bugs.webkit.org/show_bug.cgi?id=325412 (cookies copiados x rotação de refresh token; aberto em 2026-09-27).
- A35. https://bugs.webkit.org/show_bug.cgi?id=291258 (prompt de WebAuthn em outro web app).
- A36. https://bugs.webkit.org/show_bug.cgi?id=237350 (cookies de JavaScript limitados a 7 dias; resposta de John Wilander, Apple).
- A37. https://bugs.webkit.org/show_bug.cgi?id=250651 (`display-mode` em janela aberta pelo app; resposta de David Quesada, Apple).
