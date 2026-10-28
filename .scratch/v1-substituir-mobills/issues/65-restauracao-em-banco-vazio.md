# Restauração em banco vazio

Type: task
Status: resolved
Blocked by: 64
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` se mexer na interface
Modelo recomendado: Opus
Effort recomendado: high
Issue: #119
Origem: [spec da v1](../spec.md), etapa 7; histórias de usuário 161, 162

## O que construir

O dono refaz o banco a partir de um backup com confiança.

## Checklist

- [x] Restaura tudo ou nada, só em banco vazio, e confere contagens e somas contra o manifesto; recusa banco com dados e versão de formato desconhecida
- [x] Conversores das versões antigas do formato (o encadeamento em `CONVERSORES`; ainda não existe versão antiga, e a guarda do formato obriga o primeiro conversor junto com a primeira migration que mudar as tabelas)
- [x] Teste de ida e volta no CI: restaurar o backup fictício, exportar de novo e exigir zip idêntico; restaurar versão antiga (fica para o primeiro conversor: a guarda pede um teste que restaura um backup da versão anterior)
- [x] Restauração de verdade no `dev` a partir do backup de `prod`, antes da virada e a cada mudança no formato: o comando ficou pronto e roda contra o Postgres local; rodar no DSQL depende da credencial do dono e de o `prod` ter dados, e foi para o [ticket 76](76-restaurar-no-dev-o-backup-de-prod.md)
- [x] Verificações do projeto rodando e PR aberto para `main`

## Answer

Pronto em 2026-10-28 e conferido no Postgres local e no do CI. Ainda não rodou no DSQL: isso ficou com o dono, no [ticket 76](76-restaurar-no-dev-o-backup-de-prod.md).

- **Restauração** (`restaurar_backup(conn, zip)` em `backend/app/backup.py`, ao lado do gerador). Antes de gravar a primeira linha, ela confere tudo o que dá para conferir e recusa (`RestauracaoRecusada`) sem gravar nada quando:
  - a versão do formato é desconhecida (maior que a atual, sem conversor ou que não é número);
  - os CSVs e o manifesto têm tabelas ou contagens diferentes;
  - o esquema do banco não é o do backup (tabelas e colunas);
  - alguma tabela não tem chave primária, sem a qual o desfazer não apaga em lotes;
  - o banco já tem dados.
- **Tudo ou nada no DSQL** (decisão do dono nesta sessão). O DSQL aceita até 3.000 linhas e 10 MiB por transação, e por isso:
  - a restauração grava em lotes de até 1.000 linhas ou 4 MiB de texto, cada um na sua transação, na ordem das chaves estrangeiras;
  - depois de gravar, confere no banco as contagens e as somas (comparadas como número) contra o manifesto;
  - se um lote falhar (inclusive no conflito da concorrência otimista, que chega no COMMIT) ou o banco não bater com o manifesto, `esvaziar_banco` apaga tudo em lotes pela chave primária, de trás para a frente, e a restauração levanta `RestauracaoDesfeita`.

  O ADR 0012 e o glossário registram que o tudo ou nada vale para o resultado, não para uma transação só.
- **Conversores**: `CONVERSORES[N]` leva o manifesto e as tabelas da versão N para a N+1, e a restauração os encadeia. O teste `test_formato_do_backup.py` compara o esquema das migrations com o esquema gravado da versão atual em `backend/tests/esquemas_do_formato.json`. A versão 1 é o banco sem tabelas do domínio. Uma migration que mude as tabelas faz o teste falhar até alguém subir `VERSAO_FORMATO`, escrever o conversor da versão anterior com um teste que restaura um backup dela e gravar o esquema novo. O teste compara só o nome e o tipo das colunas: mudar precisão, nulidade ou chave não pede versão nova.
- **`timestamptz` sem depender do fuso**: o gerador passou a escrever esse tipo sempre em UTC (`... AT TIME ZONE 'UTC'` mais `+00`). Os backups já gravados não mudam, porque nenhum tem coluna desse tipo.
- **Comando do dono** (`scripts/restaurar-backup.sh <prod|dev> <zip> [--esvaziar]`, que chama `python -m app.restauracao`):
  - acha o endpoint do DSQL pela pilha `financial-<ambiente>-dados` e para se ele vier vazio;
  - entra como `admin`, restaura, exporta de novo e exige o mesmo zip;
  - `--esvaziar` apaga antes os dados do banco e é recusado fora do `dev`.

  Foi conferido contra o Postgres local nos quatro casos: banco com dados recusado, `--esvaziar` recusado fora do `dev`, `--esvaziar` no `dev` e banco já vazio.
- **Testes** (costuras combinadas com o dono): a ida e volta com zip idêntico, com `timestamptz` entre sessões de fusos diferentes e com a ordem das chaves estrangeiras; as recusas (banco com dados, versão desconhecida, esquema diferente, zip que não bate com o manifesto, tabela sem chave); o desfazer de uma falha no meio e de uma soma diferente do manifesto; e a guarda do formato.

Pendências gravadas no tracker:

- [ticket 76](76-restaurar-no-dev-o-backup-de-prod.md) (HITL): a restauração de verdade no `dev` com o backup de `prod`, antes da virada e a cada versão nova do formato; a primeira execução das consultas no DSQL; e a decisão sobre o que fazer se uma restauração em `prod` cair sem conseguir desfazer. O [ticket 69](69-virada-para-o-app.md) passou a depender dele.
- A primeira migration com tabelas (a de `exportacoes` do ticket 66, ou as do domínio do ticket 32, o que entrar primeiro na `main`) vai fazer a guarda do formato falhar, de propósito: ela sobe para a versão 2 com o conversor da 1. É a guarda que cobra isso, não um ticket.

## Comments

- 2026-10-28 (do [ticket 64](64-backup-diario.md)): o gerador está em `backend/app/backup.py` (`gerar_backup`, `conferir_backup`, `VERSAO_FORMATO = 1`). Ele descobre as tabelas do schema `public` sozinho (fora `controle_de_migrations`), escreve cada valor como `::text` do Postgres, `NULL` como campo vazio sem aspas e todo o resto entre aspas (`csv.QUOTE_NOTNULL`), em ordem de chave primária, e o manifesto traz por tabela `linhas` e `somas` das colunas inteiras e `numeric`. Pontos para a restauração:
  - o `::text` de `timestamptz` depende do `TimeZone` da sessão: fixe o mesmo fuso na geração e na restauração, ou a ida e volta não dá zip idêntico entre sessões com fusos diferentes;
  - as consultas ao `pg_catalog` (`pg_constraint` com `unnest ... WITH ORDINALITY`) e ao `information_schema` só rodaram no DSQL com o banco sem tabelas do domínio; a restauração de verdade no `dev` deste checklist é a primeira a exercitá-las com tabelas;
  - falta uma guarda que obrigue subir `versao_formato` quando uma migration muda as tabelas (o ADR 0012 pede); o gerador aceita qualquer esquema.
