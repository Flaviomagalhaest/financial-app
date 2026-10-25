# Como o app roda na AWS

Type: grilling
Status: resolved
Blocked by: 08, 09
Skills: `grilling` e `domain-modeling` (HITL: precisa do dono); apoio: `research` se surgir fato a confirmar
Modelo recomendado: Opus
Effort recomendado: high
Issue: #30
Origem: traçado do [mapa V1 que substitui o Mobills](../map.md)

## Question

Qual arquitetura na AWS cumpre o custo-alvo do mapa?

Cobrir: login (como os dois entram e continuam logados); API em Python (Lambda com API Gateway ou URL de função); hospedagem do app; contrato entre o app e a API (o app não é em Python); infraestrutura como código (CDK, SAM ou Terraform); ambientes (só produção ou também desenvolvimento); backup e restauração; alerta de orçamento; configuração da conta filha da organização.

## Checklist

- [x] Decisão registrada em `## Answer`
- [x] ADR em `docs/adr/` para as escolhas com lock-in

## Answer

Decidido com o dono em 2026-10-25. [ADR 0010](../../../docs/adr/0010-app-na-aws-cloudfront-http-api-e-uma-lambda.md). Fatos (preços, limites, disponibilidade em sa-east-1), com fonte de cada um, na branch `research/aws-arquitetura` (`.scratch/v1-substituir-mobills/research/aws-arquitetura.md`).

**Tudo em sa-east-1**, sem servidor ligado, como o [ADR 0009](../../../docs/adr/0009-aurora-dsql-em-sao-paulo.md) pediu. Nada precisa de us-east-1: sem domínio próprio, o CloudFront não precisa de certificado, e o orçamento é criado pela própria pilha de sa-east-1.

**Hospedagem do app:** a PWA fica num S3 privado em sa-east-1, servida pelo CloudFront (OAC) no endereço padrão `dxxxx.cloudfront.net`, com HTTPS de graça e dentro da franquia sempre grátis (1 TB e 10 milhões de pedidos). A PWA instalada fica presa a esse endereço: recriar a distribuição obriga os dois a reinstalar o app e perde a fila offline, então ela é protegida contra substituição e remoção na pilha.

**API em Python:** o CloudFront manda `/api/*` (mesmo endereço do app, sem CORS e sem preflight; sem cache, passando o `Authorization`) para uma **API Gateway HTTP API**. Ela confere o JWT do Cognito (JWT authorizer) e limita a taxa no stage (10 por segundo, rajada de 20), antes de chamar **uma Lambda com a API inteira**: FastAPI com um adaptador, arm64, python3.14, a Lambda clássica (não as Web Functions), logs por 30 dias. Uma função só porque, com dois usuários, uma por rota deixaria quase toda chamada fria; todas as rotas usam a mesma permissão no DSQL, e o mesmo código roda local com `uvicorn`. Nenhum segredo: o DSQL entra por IAM e o Cognito usa um cliente público, então sem Secrets Manager. A HTTP API custa US$ 1,59 por milhão em sa-east-1 (uns US$ 0,03 por mês); a URL de função seria grátis, mas sem barrar o pedido sem login antes da Lambda. Chamadas recusadas por falta de login contam como cobradas (a AWS não diz o contrário).

**Contrato entre o app e a API** (pendência do [ADR 0001](../../../docs/adr/0001-backend-em-python.md)): código primeiro. A FastAPI gera o OpenAPI a partir dos modelos Pydantic, e o arquivo fica versionado no repositório; o app gera os tipos TypeScript a partir dele (`openapi-typescript`), e o CI falha se o arquivo gerado estiver desatualizado.

**Login:** user pool do Cognito em sa-east-1 (plano Essentials ou Lite, 10 mil usuários ativos por mês de graça, divididos com a organização), sem cadastro público; os 2 usuários são criados à mão pelo dono. O login é um formulário dentro do app que fala direto com o Cognito (SRP, cliente público sem secret), isolado num módulo; sem redirecionamento, porque no app da Tela de Início do iPhone o login em outra origem pode ficar preso numa janela do Safari. A API depende só do JWT (emissor e audiência em configuração): trocar de provedor é recriar 2 usuários e mudar a configuração. Só senha na v1; TOTP fica como opção para depois, e passkey não, porque fica presa ao endereço do CloudFront.

**Como continuam logados:** refresh token de 10 anos, sem a rotação do Cognito (ela não estende a sessão), guardado no IndexedDB do app instalado e nunca em cookie (no iPhone, cookie de JavaScript dura no máximo 7 dias). O login é feito dentro do app já instalado, porque instalar não leva o armazenamento do Safari. Token de acesso de 15 minutos. Sem internet, o app mostra o cache e guarda a fila; o token só é renovado quando a internet volta. Celular perdido: `AdminUserGlobalSignOut`, num runbook; o token de acesso já emitido vale até expirar, porque o JWT authorizer não vê a revogação.

**Infraestrutura como código:** AWS CDK em TypeScript, numa pasta `infra/`, com um bootstrap em sa-east-1 (bucket e repositório ECR vazio, centavos). O orçamento e os alarmes entram no mesmo código.

**Ambientes:** `prod` e `dev` como duas pilhas do mesmo código, na mesma conta, cada uma com seu cluster DSQL (dividem a franquia), user pool e endereço. O `dev` testa as migrations no subconjunto real do DSQL e é descartável.

**Deploy:** GitHub Actions com OIDC, sem chave de longa duração; a role na conta filha confia só neste repositório, no formato novo do `sub` do GitHub (`repo:Flaviomagalhaest@14982168/financial-app@1432589902:ref:refs/heads/main`). O merge na `main` publica em `prod`; o `dev` sai pelo botão do workflow ou por push numa branch.

**Migrations:** arquivos SQL numerados no repositório, um DDL por arquivo (o DSQL aceita um DDL por transação e não mistura DDL com dados), aplicados por um executor simples que guarda a última versão aplicada numa tabela. Rodam no job de deploy, com token IAM da role do OIDC, antes de atualizar a Lambda; primeiro no `dev`, em `prod` só no merge da `main`. Cada migration é compatível com a versão anterior da Lambda (acrescentar antes, remover depois).

**Backup e restauração:** o EventBridge Scheduler chama, uma vez por dia, uma Lambda de backup do mesmo pacote, que grava a exportação completa num S3 em sa-east-1 com versões e Object Lock em **compliance** por 90 dias (nem o root apaga antes). Um teste no CI faz exportar → importar num banco vazio → comparar; além disso, uma restauração de verdade no `dev` a partir do backup de `prod`, antes da virada e a cada mudança no formato da exportação.

**Alerta de orçamento:** um orçamento mensal na conta filha, com `IncludeCredit` e `IncludeRefund` desligados (senão os créditos escondem o gasto até 12/04/2027), e alertas por e-mail para `flaviomagalhaest@gmail.com`: gasto real acima de US$ 1, previsão do mês acima de US$ 5 e gasto real acima de US$ 5. Sem ação automática.

**Alertas de operação:** alarmes do CloudWatch, por SNS para o mesmo e-mail, quando o backup diário falha, quando nenhum backup novo aparece em 26 horas e quando a API devolve erros 5xx acima de um limite por dia. Dentro das franquias (10 alarmes, 1.000 e-mails).

**Configuração da conta filha:** o usuário IAM `financial-cli` vira o acesso humano do dono, com MFA obrigatório, e a chave de acesso dele é desativada depois do [ticket 17](17-medir-retomada-e-confirmar-pontos-no-prototipo.md); o root ganha MFA e fica guardado; sem Identity Center. A SCP `p-q0eemrzp` fica à mão, com uma cópia do JSON em `docs/aws/` e um passo no runbook (reaplicá-la sem sa-east-1 derruba o app); ela não vira infraestrutura como código porque o repositório não deve ter credencial da conta de gerência. O limite das SCPs subiu para 10.240 caracteres e 10 por entidade em 15/05/2026, então ela não precisa ser dividida. Esses passos estão no [ticket 20](20-configurar-o-acesso-a-conta-aws.md).

**Custo estimado:** fora o DSQL, de US$ 0,01 a 0,06 por mês (até uns US$ 0,25 no pior caso), quase tudo nas chamadas da HTTP API e no S3 do backup. Com o DSQL na franquia, o total fica abaixo de US$ 0,10 no uso normal, dentro do custo-alvo de US$ 0 a 1.

Pendências gravadas no tracker: [ticket 20](20-configurar-o-acesso-a-conta-aws.md) (MFA, chave do `financial-cli`, cópia da SCP, cota de concorrência do Lambda e expiração das versões do backup com Object Lock).

## Comments

- O [ticket 09](09-banco-de-dados-e-regiao.md) decidiu ([ADR 0009](../../../docs/adr/0009-aurora-dsql-em-sao-paulo.md)): Aurora DSQL em sa-east-1, com o app inteiro nessa região (API, bucket do backup, hospedagem, login); em us-east-1 só os serviços globais (IAM, Budgets, certificado do CloudFront). Todo serviço escolhido aqui precisa existir em sa-east-1. O backup é uma tarefa agendada diária que grava a exportação completa num S3 com versões, 90 dias e Object Lock; região e endpoint só em configuração; autenticação no DSQL só por IAM (a API usa uma role, nunca chave de usuário).
- Configuração da conta filha: a SCP `p-q0eemrzp` (`AdvancedModeRegionRestrictionSecurityControlPolicy`, na raiz da organização) teve `sa-east-1` acrescentado ao bloco `RegionFloor` em 2026-10-25. A origem dela é desconhecida (pode ser um assistente que a reaplica sem São Paulo). Ela tem 5.094 caracteres; o limite era 5.120, mas a AWS o subiu para 10.240 (e até 10 SCPs por entidade) em 15/05/2026, então não é preciso dividi-la. Decidido aqui: fica à mão, com cópia no repositório ([ticket 20](20-configurar-o-acesso-a-conta-aws.md)).
- O usuário IAM `financial-cli` (chave de acesso de longa duração) foi criado para testes a partir da máquina do dono; a chave é desativada quando os testes do [ticket 17](17-medir-retomada-e-confirmar-pontos-no-prototipo.md) acabarem, pelo [ticket 20](20-configurar-o-acesso-a-conta-aws.md).
- Pesquisa de fatos de 2026-10-25 na branch `research/aws-arquitetura`. Lacunas que não mudam a decisão: se a HTTP API cobra chamadas recusadas por falta de login (contadas como cobradas); login com redirecionamento no iPhone (evitado pelo login no app); se a conta filha tem os 12 meses grátis da HTTP API.
