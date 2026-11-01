# Importador do Mobills: gravar com a fonte e refazer apagando só o importado

Type: task
Status: resolved
Blocked by: 68
Skills: `grilling` (HITL: o dono decide como o refazer convive com a restauração só em banco vazio do ADR 0012); depois `implement`, `tdd`
Modelo recomendado: Opus
Effort recomendado: high
Issue: #173
Origem: [ticket 67](67-importador-do-mobills-cruzamento-e-revisao.md) (o esquema não tinha cartões, faturas, pessoa nem fonte quando o importador foi feito; o dono dividiu o escopo: o 67 entrega a leitura, o cruzamento e a planilha, com o resultado em memória)

## O que construir

O importador já devolve a `Importacao` (`backend/app/mobills/`): a conta e os cartões do cadastro, cada lançamento com `fonte = "mobills"`, o cartão pelo nome, a pessoa do de-para (sem ela é do conjunto), os parcelamentos e os ajustes de fatura. O [ticket 68](68-importador-do-mobills-parcelamentos-pendentes-e-ajustes.md) faz disso um backup válido (`--backup`, que a restauração grava num banco vazio). Falta gravar no banco de verdade e poder **refazer** até a virada, apagando só o que veio do Mobills.

## A pergunta (HITL)

O [ADR 0012](../../../docs/adr/0012-exportacao-unica-zip-de-csvs-e-restauracao-so-em-banco-vazio.md) diz que a carga do Mobills é o backup gravado pela restauração, e que a restauração **só roda em banco vazio**. O ticket 18 e a história 170 dizem que refazer "apaga só o que tem autoria importado do Mobills". As duas coisas só convivem enquanto o banco tem só o importado. Opções:

- **Refazer = esvaziar e restaurar**: vale enquanto o casal não lança no app (antes da virada); o `--esvaziar` hoje é só do `dev`.
- **Apagar `fonte = 'mobills'` (e o cadastro que veio da importação) e restaurar só essas linhas** num banco não vazio: abre uma exceção no ADR 0012, que recusou a "carga do Mobills com gravação própria".
- Outra que o dono propuser.

## Checklist

- [x] Dono decide o refazer; a decisão vai para `## Answer` (e para um ADR novo, se mudar o 0012): refazer = esvaziar e restaurar, sem ADR novo
- [x] → [ticket 68](68-importador-do-mobills-parcelamentos-pendentes-e-ajustes.md): Lançamentos no backup com `fonte = 'mobills'` e um único `criado_por` (`mobills`): o "Parece repetido" (ticket 41) só compara `criado_por` diferentes, e a importação não pode disparar avisos em massa
- [x] → ticket 68: A pessoa que o de-para der confere com `app.pessoas.configuradas` (impedimento se não for do casal); sem ela, o lançamento é do conjunto
- [x] → ticket 68: Conta e cartões do cadastro no backup (os arquivados com `arquivado_em`, dias opcionais), cada pasta de fatura ligada ao seu cartão
- [x] → ticket 68: O importador não grava o backup enquanto houver `Importacao.impedimentos`
- [x] Refazer apaga só o que veio do Mobills e grava de novo: `--refazer-importacao` troca um banco que só tem o importado e recusa o que tem uso pelo app
- [x] Teste: importar, lançar algo pelo app, refazer: recusado, e o lançado pelo app continua; importar e refazer: o banco tem o importado novo
- [x] Verificações do projeto rodando e PR aberto para `main`

## Answer

Decidido com o dono (`grilling`):

- **Refazer = esvaziar e restaurar.** Até a [virada](../../../GLOSSARY.md), o `prod` só guarda o que veio do Mobills: o casal lança no Mobills, e os testes de verdade ficam no `dev`. O [ADR 0012](../../../docs/adr/0012-exportacao-unica-zip-de-csvs-e-restauracao-so-em-banco-vazio.md) continua valendo (a restauração só grava num banco vazio; o refazer esvazia antes), sem ADR novo e sem um segundo caminho de gravação.
- **Trava no código, sem passar por cima.** O refazer recusa, sem apagar nada, se alguma linha do banco tiver `criado_por`, `alterado_por`, `excluido_por` ou `desfeita_por` diferente de `mobills`. As colunas são achadas pelo sufixo `_por`, em todas as tabelas, então uma tabela nova entra na trava sozinha. As tabelas sem autoria (faturas, ligações, `exportacoes`) não contam. A recusa diz em que tabelas há uso pelo app. A tarefa diária não dispara a trava: a parcela automática realizada leva a autoria do parcelamento (`mobills`). Se o caso aparecer depois da virada, o caminho é o console do DSQL, como no [ticket 76](76-restaurar-no-dev-o-backup-de-prod.md).
- **O zip novo também tem de ser só do importador**, pela mesma regra: um backup comum não entra pelo refazer, só num banco vazio.
- **A preparação da virada se perde e não é levada adiante** (seria mesclar, o que o ADR 0012 recusou): saldo de abertura, limite e titular do cartão, datas das faturas. Pela ordem do [ticket 69](69-virada-para-o-app.md), eles vêm depois da importação final. A saída avisa o que havia (`informe de novo: ...`). Conta como informada a fatura com datas que não são as do zip novo nem as padrão do cartão: as padrão são as que a importação dá às faturas das parcelas futuras, e o export seguinte traz esse mês sem datas. Escapa do aviso a data que o dono der igual à padrão, o que a ordem do ticket 69 deixa para depois da importação final.
- **O cadastro mudado no app também se perde, sem aviso.** Contas, cartões, categorias e tags só têm `criado_por`: renomear, mudar os dias do cartão ou arquivar pelo app não muda a autoria, a trava não vê, e o refazer volta ao que o zip traz. Até a virada, nome, dias e arquivamento se acertam na planilha de revisão (abas Conta, Cartões e De-para).
- **Comando**: `scripts/restaurar-backup.sh <prod|dev> <importado.zip> --refazer-importacao`, em qualquer ambiente. Ele confere o zip sem gravar (versão, manifesto, esquema, chaves), aplica a trava ao zip e ao banco, esvazia e restaura; depois exporta de novo e exige o mesmo zip, como a restauração. O `--esvaziar` continua só do `dev`, e os dois não se juntam. Se a gravação falhar no meio, ela se desfaz como na restauração, e o banco fica vazio: basta rodar de novo. Também uma restauração da importação que caiu no meio em `prod` se limpa assim, porque o que sobrou é só do Mobills.

Código: `refazer_importacao` em `backend/app/backup.py` (a restauração foi dividida em `_preparar`, que confere sem gravar, e `_gravar`), a autoria `IMPORTADO_DO_MOBILLS` também em `app/backup.py` (o `app.restauracao` roda sem as dependências de dev, e o pacote `app.mobills` lê planilhas) e a opção em `backend/app/restauracao.py`. Testes em `backend/tests/test_backup_do_importador.py`.

## Notas

- Do [ticket 39](39-estorno-ajuste-de-fatura-e-cancelamento.md), atualizado no [ticket 68](68-importador-do-mobills-parcelamentos-pendentes-e-ajustes.md): o backup gerado pelo importador sai na versão atual do formato (`VERSAO_FORMATO`), montado pelo esquema de `backend/app/esquemas_do_formato.json`.
