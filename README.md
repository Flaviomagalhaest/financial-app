# Financial App

App financeiro do casal: API em Python (FastAPI) em `backend/`, app React + TypeScript em `web/`, infraestrutura AWS (CDK em TypeScript) em `infra/`. Spec e tickets em `.scratch/`.

## Pré-requisitos

Python 3.14 (o runtime da Lambda; `backend/.python-version`) com [uv](https://docs.astral.sh/uv/), Node 22, Postgres 16 (o mesmo do CI).

## Como rodar

```sh
eval "$(scripts/postgres-local.sh)"          # Postgres local sem Docker; exporta DATABASE_URL
(cd web && npm ci && node e2e/cognito-falso.ts)   # login de mentira na porta 9230 (veja Login)
(cd backend && uv sync && uv run python -m app.migrations)
(cd backend && JWT_EMISSOR=http://127.0.0.1:9230/sa-east-1_teste JWT_AUDIENCIA=cliente-de-teste \
  uv run uvicorn app.main:create_app --factory --port 8765)
(cd web && VITE_COGNITO_USER_POOL_ID=sa-east-1_teste VITE_COGNITO_CLIENTE_ID=cliente-de-teste \
  VITE_COGNITO_ENDPOINT=http://127.0.0.1:9230/ npm run dev)   # /api é repassado para a porta 8765
```

Com o Cognito falso, `flavio@teste.com` e `esposa@teste.com` entram com qualquer senha.

## Login

O app entra no Cognito por um formulário próprio (SRP, cliente público), e só o módulo `web/src/login/` conhece o Cognito. A sessão fica no IndexedDB do aparelho, nunca em cookie: refresh token de 10 anos e token de acesso de 15 minutos, renovado quando vence; sem internet, o app segue logado com o acesso vencido. A API só confere um JWT padrão, com emissor e audiência em `JWT_EMISSOR` e `JWT_AUDIENCIA` (chaves em `<emissor>/.well-known/jwks.json`), e tira o usuário do `sub`. Rota nova protegida recebe `usuario: UsuarioLogado` (`app/login.py`).

O app lê o user pool no build: `VITE_COGNITO_USER_POOL_ID`, `VITE_COGNITO_CLIENTE_ID` e, só para o falso, `VITE_COGNITO_ENDPOINT`. O deploy preenche os dois primeiros com as saídas da pilha de dados.

Não há cadastro público: o dono cria os dois usuários, já com a senha definitiva, e desconecta todas as sessões de um celular perdido (o acesso já emitido vence em até 15 minutos):

```sh
scripts/usuarios-do-app.sh criar prod <email>
scripts/usuarios-do-app.sh desconectar prod <email>
scripts/usuarios-do-app.sh listar prod
```

## Como testar

```sh
(cd backend && uv run pytest)                # rotas em processo contra o Postgres de DATABASE_URL
(cd web && npm run typecheck && npx playwright test)   # sobe Cognito falso, API e app; o teste desliga a rede
```

O CI (`.github/workflows/ci.yml`) roda lint, testes, o contrato e o build com um Postgres em container.

## Lançamentos

`backend/app/lancamentos.py` tem contas, categorias e lançamentos simples (valor em centavos inteiros, uma ou mais categorias, id UUID gerado no aparelho). No app, `#/novo` lança, `#/historico` lista, edita e exclui, e `#/contas-e-categorias` cria conta e cria, renomeia e arquiva categoria.

`backend/app/transferencias.py` registra a transferência entre duas contas ([ADR 0014](docs/adr/0014-transferencia-em-tabela-propria.md)). A conta guarda o saldo de abertura (valor e data) e pode ser arquivada (`PUT /api/contas/{id}`); `GET /api/contas` devolve `saldo_centavos` (abertura mais os realizados depois da data) e esconde as arquivadas, salvo com `?arquivadas=true`. Só a API existe: as telas são do ticket 74.

## Contrato (OpenAPI e tipos)

A FastAPI gera o OpenAPI; `openapi.json` fica versionado e o app gera os tipos dele. Depois de mudar uma rota ou um modelo:

```sh
(cd backend && uv run python gerar_openapi.py)
(cd web && npm run gerar-tipos)
```

O CI falha se `openapi.json` ou `web/src/api/schema.d.ts` estiverem desatualizados.

## Migrations

Arquivos `backend/migrations/NNNN_nome.sql`, um DDL por arquivo, no subconjunto do Aurora DSQL (sem triggers nem PL/pgSQL). `aplicar_migrations` aplica em ordem as que faltam e as registra em `controle_de_migrations`.

## Configuração

Os valores iniciais da spec (3 sugeridos, 5 usos, 24 h, 80% etc.) ficam só em `config/valores-iniciais.json`, lido pela API (`app.config.valores_iniciais`) e importável pelo app.

## Deploy

O workflow `.github/workflows/deploy.yml` publica pelo GitHub Actions com OIDC (role `financial-app-deploy`, sem chave de longa duração): o merge na `main` publica em `prod`; push em outra branch, ou o botão "Run workflow", publica em `dev`. Conta e região ficam só em `config/aws.json`.

Cada ambiente tem duas pilhas: `financial-<ambiente>-dados` (cluster Aurora DSQL, user pool do Cognito e o bucket do backup) e `financial-<ambiente>-app` (Lambda arm64 com a API, HTTP API com limite de 10 por segundo e rajada de 20, PWA num S3 privado, o CloudFront, que leva `/api/*` à HTTP API sem cache, e a Lambda do backup diário). O deploy segue esta ordem: pilha de dados, migrations e papéis (`api` e `backup`) no DSQL, build da PWA com o user pool do ambiente, pilha do app (no `dev`, com um backup de verdade, veja abaixo) e o teste de fumaça (`scripts/conferir-deploy.sh <endereço>`), que exige `/api/saude` ok com todas as migrations e `/api/eu` recusado sem token. As políticas das pilhas (`infra/politicas/`) proíbem substituir ou remover a distribuição, o banco, o user pool e o bucket do backup, porque a PWA instalada fica presa ao endereço do CloudFront e o bucket guarda os backups travados.

Backup diário (ADR 0012): às 03:07 de São Paulo, o EventBridge Scheduler chama a Lambda `app.backup_diario.handler`, que entra no DSQL com o papel `backup` (só `SELECT`), gera o zip numa transação só, confere as contagens do zip contra o banco e grava `diario/AAAA-MM-DD.zip` no bucket `BucketDoBackup` (saída da pilha de dados). O bucket tem versões e Object Lock em compliance por 90 dias em `prod` (1 dia no `dev`), e o ciclo de vida apaga as versões depois do prazo. Um e-mail chega pelo tópico `Avisos` se a Lambda falhar ou se passarem 26 horas sem backup concluído (métrica `FinancialApp/BackupsConcluidos`). No `dev`, cada deploy com código novo também roda um backup (Trigger do CDK) e falha se ele falhar. Para baixar um backup: `aws s3 cp s3://<bucket>/diario/AAAA-MM-DD.zip .`; as versões de um mesmo dia aparecem em `aws s3api list-object-versions --bucket <bucket> --prefix diario/`. O bucket fica na conta mesmo se a pilha for apagada: com objetos travados o CloudFormation não o apaga, e ele se esvazia pelo ciclo de vida.

Exportar tudo (ADR 0012): a tela Configurações do app (só com internet) chama `POST /api/exportacoes` com `{"formato": "backup"}` (zip de CSVs, o mesmo gerador do backup diário) ou `{"formato": "planilha"}` (CSV de lançamentos com `;`, vírgula decimal e UTF-8 com BOM). A API grava o arquivo em `exportacoes/` no bucket `BucketDeExportacoes` (variável `EXPORTACOES_BUCKET`), sem Object Lock e com expiração de 7 dias, devolve uma URL assinada de 5 minutos e registra quem pediu na tabela `exportacoes`. Enquanto as tabelas de lançamentos não existem, a planilha sai só com o cabeçalho (ticket 77).

Restauração (ADR 0012): `scripts/restaurar-backup.sh <prod|dev> <arquivo.zip>` grava um backup no banco do ambiente com a credencial do dono (`app.restauracao`, entra no DSQL como `admin`). Ela só roda num banco vazio e com as mesmas tabelas do backup (as migrations aplicadas), recusa versão de formato desconhecida e converte as antigas (`CONVERSORES` em `app/backup.py`). Grava em lotes de 1.000 linhas, porque o DSQL limita as linhas por transação; se um lote falhar ou as contagens e somas do banco não baterem com o manifesto, apaga o que gravou e o banco volta a ficar vazio. No fim, exporta de novo e exige o mesmo zip. O ensaio no `dev` com o backup de `prod`, antes da virada e a cada mudança no formato, leva `--esvaziar`, que apaga os dados do `dev` antes (recusado em `prod`). Uma migration que muda as tabelas faz o teste `test_formato_do_backup.py` falhar até `VERSAO_FORMATO` subir, com o conversor da versão anterior e o esquema novo em `backend/tests/esquemas_do_formato.json`.

Alarmes de custo e de erros (e-mail do dono em `config/aws.json`, `emailDoDono`): a pilha `financial-orcamento` (da conta, não de um ambiente) cria o orçamento mensal sem créditos com alertas em US$ 1 (real), US$ 5 (previsão) e US$ 5 (real); ela é publicada à mão, como a `financial-github` (`cd infra && npx cdk deploy financial-orcamento`). Cada pilha do app tem um alarme de mais de 5 respostas 5xx por dia na HTTP API e os dois do backup, avisando pelo mesmo tópico SNS e e-mail. Depois do primeiro deploy, o dono confirma a inscrição do SNS que chega por e-mail. `npm test` em `infra/` confere os dois.

Para conferir as pilhas localmente:

```sh
scripts/empacotar-lambda.sh                  # pacote da Lambda em build/lambda (arm64, python3.14)
(cd web && npm run build)
(cd infra && npm ci && npm run typecheck && npm run synth)
```
