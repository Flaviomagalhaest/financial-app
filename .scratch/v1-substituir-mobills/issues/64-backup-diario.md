# Gerador de backup e backup diário

Type: task
Status: resolved
Blocked by: 28
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` se mexer na interface
Modelo recomendado: Opus
Effort recomendado: high
Issue: #118
Origem: [spec da v1](../spec.md), etapa 7; histórias de usuário 157, 159, 160

## O que construir

Os dados passam a ter cópia diária que nem o root apaga. **Deve ser ligado antes de o casal lançar de verdade** ([ADR 0012](../../../docs/adr/0012-exportacao-unica-zip-de-csvs-e-restauracao-so-em-banco-vazio.md)).

## Checklist

- [x] Gerador que só lê o banco e produz um zip com um CSV por tabela, ids originais e `manifesto.json` (`versao_formato`, contagens e somas)
- [x] EventBridge diário grava o zip num S3 com versões e Object Lock em compliance por 90 dias, e confere as contagens do zip contra o banco
- [x] Regra de ciclo de vida que apaga as versões depois dos 90 dias (a documentação é ambígua sobre apagar versões após o Object Lock em compliance: confira na AWS, com o bucket criado, que a regra de fato as expira; veja o [ticket 20](20-configurar-o-acesso-a-conta-aws.md)); a conferência na AWS depende de dias passarem e foi para o [ticket 73](73-conferir-o-ciclo-de-vida-e-os-alarmes-do-backup.md)
- [x] E-mail se o backup falhar ou não rodar em 26 horas
- [x] Teste de API do gerador com o exemplo fictício
- [x] Verificações do projeto rodando e PR aberto para `main`

## Answer

Pronto em 2026-10-28 e conferido no `dev`: o deploy desta branch rodou um backup de verdade no DSQL e o gravou no bucket com Object Lock.

- **Gerador** (`backend/app/backup.py`): `gerar_backup(conn)` lê todas as tabelas do schema `public`, menos `controle_de_migrations`, e devolve um zip com:
  - um CSV por tabela, com os ids originais, em ordem de chave primária;
  - cada valor no texto do Postgres; `NULL` sai como campo vazio sem aspas e o texto vazio sai entre aspas;
  - o `manifesto.json` com `versao_formato` (1) e, por tabela, `linhas` e as `somas` das colunas inteiras e `numeric`.

  O zip não leva a hora da geração, então o mesmo banco dá o mesmo zip byte a byte (é o que a ida e volta do ticket 65 exige). Como ainda não existe nenhuma tabela do domínio, o gerador descobre as tabelas sozinho, e os testes usam um exemplo fictício (`backend/tests/exemplo_ficticio.py`). `conferir_backup(conn, zip)` compara as tabelas e as contagens do zip e do manifesto com o banco e levanta `BackupDivergente` se não baterem.
- **Backup diário** (`backend/app/backup_diario.py`, outra Lambda do mesmo pacote): o EventBridge Scheduler a chama às 03:07 de São Paulo, com duas novas tentativas. Ela entra no DSQL com o papel `backup`, que tem só `SELECT` e é criado e ligado à role dela pelo deploy, no molde do papel `api` do ticket 70. Gera e confere o zip numa mesma transação `REPEATABLE READ` só de leitura, grava `diario/AAAA-MM-DD.zip` com checksum SHA-256 (exigido pelo Object Lock) e publica a métrica `FinancialApp/BackupsConcluidos` no formato EMF. A role só tem `s3:PutObject` em `diario/*`.
- **Bucket** (pilha de dados, ID lógico `Backup`, protegido pela política da pilha e retido se a pilha sair): versões e Object Lock em compliance, 90 dias em `prod` e 1 dia no `dev` (decisão do dono, para o bucket do `dev` não ficar preso e para a conferência do ciclo de vida sair em poucos dias). O ciclo de vida em `diario/` põe o marcador de exclusão quando o prazo vence, apaga a versão antiga no dia seguinte e limpa os marcadores que ficam sem versão.
- **Alarmes** (no tópico `Avisos` do ticket 29, que manda e-mail ao `emailDoDono` de `config/aws.json`):
  - `BackupFalhou`: um erro da Lambda numa hora;
  - `BackupAtrasado`: 25 horas cheias sem a métrica, o que dispara até 26 horas depois do último backup; falta de dado conta como atraso.

  O dono tinha escolhido uma variável do repositório para o e-mail, mas o ticket 29 já pôs o endereço em `config/aws.json` com o mesmo tópico, então ficou um tópico só, com uma confirmação de inscrição só.
- **No `dev`**, cada deploy com código novo roda um backup (`Trigger` do CDK), e o deploy falha se o backup falhar. Em `prod` isso não acontece, para um backup quebrado não travar o deploy de uma correção; lá vale o alarme.
- **Testes** (costuras combinadas com o dono):
  - o gerador com o exemplo fictício: CSV por tabela, `NULL` diferente de vazio, manifesto, zip idêntico, papel só de leitura igual ao dono;
  - a conferência: aceita o próprio backup e recusa um zip com linha faltando;
  - o backup diário com S3 falso: chave, checksum e a métrica do alarme;
  - o papel `backup` na conexão ao DSQL.

  A infra ficou sem teste de template próprio e foi verificada por typecheck, synth e o deploy no `dev`. O teste de template do ticket 29 passou a receber o `ambiente`.
- **Mudança de rumo na revisão**: com só `SELECT`, o `information_schema` esconde as chaves primárias, e o backup sairia em outra ordem. A chave agora vem do `pg_catalog`, e um teste cobre isso.

Pendências gravadas no tracker:

- [ticket 73](73-conferir-o-ciclo-de-vida-e-os-alarmes-do-backup.md) (HITL): conferir na AWS que o ciclo de vida apaga as versões depois da trava (no `dev` a partir de 2026-11-01; em `prod` depois de 92 dias), o primeiro backup de `prod` e o e-mail dos alarmes.
- Notas no [ticket 65](65-restauracao-em-banco-vazio.md): o fuso da sessão no texto de `timestamptz`; as consultas ao catálogo ainda não rodaram no DSQL com tabelas do domínio; a guarda que obriga subir `versao_formato`.
- Nota no [ticket 66](66-exportar-tudo-e-csv-de-planilha.md): as exportações a pedido precisam de outro bucket (a retenção vale para o bucket inteiro) e da mesma transação.

