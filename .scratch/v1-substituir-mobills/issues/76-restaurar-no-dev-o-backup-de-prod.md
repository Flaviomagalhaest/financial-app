# Restaurar no dev o backup de prod

Type: task
Status: ready-for-human
Blocked by: 65
Skills: `wizard` para guiar os passos do dono; HITL (credencial AWS do dono, que entra no DSQL como `admin`)
Modelo recomendado: Sonnet
Effort recomendado: low
Issue: #145
Origem: [ticket 65](65-restauracao-em-banco-vazio.md) (a restauração só rodou no Postgres do CI e no local; o checklist pede uma restauração de verdade no `dev` a partir do backup de `prod`, antes da virada e a cada mudança no formato)

## O que fazer

O `scripts/restaurar-backup.sh` (ticket 65) restaura um backup no banco de um ambiente. Com `--esvaziar`, só no `dev`, ele apaga antes os dados do `dev`. Depois de gravar e conferir contagens e somas contra o manifesto, ele exporta de novo e exige o mesmo zip. Esta é a primeira vez que a restauração roda no DSQL. Ainda não rodaram lá com tabelas do domínio: a consulta das chaves estrangeiras no `pg_constraint`, o `AT TIME ZONE 'UTC'` dos `timestamptz`, o `DELETE ... WHERE (chave) IN (SELECT ... LIMIT 1000)` do esvaziar e os lotes do `executemany`.

Os comandos usam a credencial temporária do dono na conta <conta AWS> (sa-east-1). O bucket de cada ambiente é a saída `BucketDoBackup` da pilha `financial-<ambiente>-dados`.

```sh
aws s3 ls s3://<bucket de prod>/diario/ | tail -1
aws s3 cp s3://<bucket de prod>/diario/<data>.zip .
scripts/restaurar-backup.sh dev <data>.zip --esvaziar
```

Esvaziar apaga tudo o que houver no `dev`: os testes feitos lá à mão se perdem.

## Checklist

- [ ] Quando o `prod` tiver o histórico importado do Mobills ([ticket 68](68-importador-do-mobills-parcelamentos-pendentes-e-ajustes.md)) e antes de parar de lançar no Mobills ([ticket 69](69-virada-para-o-app.md)): baixar o backup mais recente de `prod`, restaurar no `dev` com `--esvaziar` e guardar a saída em `## Answer`. Ela lista as linhas por tabela e termina em "exportado de novo: mesmo zip"
- [ ] Abrir o app do `dev` e conferir por amostra que os lançamentos, as contas e os saldos são os de `prod`
- [ ] A cada `VERSAO_FORMATO` novo em `backend/app/backup.py`: restaurar no `dev` um backup de `prod` da versão anterior, para provar o conversor, e anotar a data em `## Answer`
- [ ] Decidir o que fazer se uma restauração em `prod` cair no meio sem conseguir desfazer (a conexão caiu durante o desfazer). O banco fica com parte dos dados, uma nova restauração é recusada por haver dados, e o `--esvaziar` é recusado em `prod`. Opções: liberar o `--esvaziar` em `prod` com confirmação, ou apagar à mão pelo console do DSQL. Se o que ficou é só da importação do Mobills, o `--refazer-importacao` já limpa e grava de novo ([ticket 91](91-importador-do-mobills-gravar-e-refazer.md)); a pergunta fica para os backups com uso pelo app
