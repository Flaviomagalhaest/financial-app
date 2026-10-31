# Importador do Mobills: gravar com a fonte e refazer apagando só o importado

Type: task
Status: ready-for-human
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

- [ ] Dono decide o refazer; a decisão vai para `## Answer` (e para um ADR novo, se mudar o 0012)
- [x] → [ticket 68](68-importador-do-mobills-parcelamentos-pendentes-e-ajustes.md): Lançamentos no backup com `fonte = 'mobills'` e um único `criado_por` (`mobills`): o "Parece repetido" (ticket 41) só compara `criado_por` diferentes, e a importação não pode disparar avisos em massa
- [x] → ticket 68: A pessoa que o de-para der confere com `app.pessoas.configuradas` (impedimento se não for do casal); sem ela, o lançamento é do conjunto
- [x] → ticket 68: Conta e cartões do cadastro no backup (os arquivados com `arquivado_em`, dias opcionais), cada pasta de fatura ligada ao seu cartão
- [x] → ticket 68: O importador não grava o backup enquanto houver `Importacao.impedimentos`
- [ ] Refazer apaga só o que veio do Mobills e grava de novo
- [ ] Teste: importar, lançar algo pelo app, refazer, e o lançado pelo app continua
- [ ] Verificações do projeto rodando e PR aberto para `main`

## Notas

- Do [ticket 39](39-estorno-ajuste-de-fatura-e-cancelamento.md), atualizado no [ticket 68](68-importador-do-mobills-parcelamentos-pendentes-e-ajustes.md): o backup gerado pelo importador sai na versão atual do formato (`VERSAO_FORMATO`), montado pelo esquema de `backend/app/esquemas_do_formato.json`.
