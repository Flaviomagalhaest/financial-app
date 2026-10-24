# Banco de dados na AWS para dois usuários e histórico longo

Origem: ticket [03 - Banco de dados na AWS](../issues/03-banco-de-dados-na-aws.md), do [mapa V1](../map.md).
Data de acesso de todas as fontes: **2026-10-24**. Branch: `research/banco-de-dados-aws` (não mesclada, sem PR).

## Resumo

1. **Todas as opções ficam abaixo do teto de US$ 5/mês nos dois volumes (25 mil e 120 mil lançamentos), exceto o RDS PostgreSQL 24 horas ligado em sa-east-1 (US$ 29,20) e o Aurora Serverless v2 sem pausa (US$ 91 em sa-east-1).** Só DSQL, SQLite em S3 e o DynamoDB (até cerca de US$ 1 em sa-east-1 com 120 mil lançamentos) cabem na meta de US$ 0 a 1.
2. **O volume de dados é irrelevante para o custo.** 25 mil a 120 mil lançamentos ocupam de 13 MB a 61 MB (com índices e tags); o DSQL dá 1 GB de storage grátis por mês e o DynamoDB dá 25 GB. O que custa é o **processamento das consultas de dashboard** (somas por mês e por tag sobre anos), não o armazenamento.
3. **Aurora DSQL é o melhor encaixe**: SQL de verdade (somas e `GROUP BY` no banco), escala a zero sem cobrança parada, custo estimado de **US$ 0** dentro do free tier (100 mil DPU e 1 GB por mês) e, mesmo sem free tier, de US$ 0,07 a US$ 0,29 por mês. Está disponível em **sa-east-1**.
4. **Correção de premissa do ticket:** o DSQL **passou a suportar foreign keys** (nota de versão de 26/08/2026). Continuam valendo: **sem triggers, sem PL/pgSQL**, **no máximo 3.000 linhas alteradas por transação**, 10 MiB de dados por transação, transação de até 5 minutos, conexão de até 60 minutos, **autenticação só por IAM** (token de 15 minutos), concorrência otimista (erro de serialização exige retry) e um único banco por cluster.
5. **DynamoDB** é barato nos requests de escrita, mas **não soma nem agrupa**: toda soma por mês ou tag exige ler todos os itens do período (ou manter agregados pré-calculados pela aplicação). Com 120 mil lançamentos e 40 dashboards por dia, a conta sobe para cerca de US$ 0,68 (us-east-1) a US$ 1,02 (sa-east-1) por mês, e no cenário de 10x mais consultas, até US$ 6,6 a US$ 9,9. O free tier de requests só vale em capacidade **provisionada** (25 WCU e 25 RCU), não em sob demanda.
6. **Aurora Serverless v2 com pausa automática** custa de US$ 3,1 (us-east-1) a US$ 6,9 (sa-east-1) por mês com uso típico, mas **a primeira conexão após a pausa leva cerca de 15 segundos** (fonte oficial) e o mínimo de ociosidade antes de pausar é de 5 minutos. Sem pausa, o piso é de 0,5 ACU 24 horas: US$ 44 (us-east-1) ou US$ 91 (sa-east-1).
7. **RDS PostgreSQL db.t4g.micro (1 GiB de RAM)** custa US$ 14,0 (us-east-1) ou US$ 29,2 (sa-east-1) por mês ligado 24 horas, mais US$ 3,65 se tiver IPv4 público. Uma instância parada é religada sozinha após 7 dias, então não serve para "pausar".
8. **SQLite em S3** custa centavos, mas exige baixar o arquivo inteiro a cada uso e controlar concorrência na aplicação (S3 tem escrita condicional por ETag). **SQLite em EFS** não é recomendado: a documentação do SQLite avisa que travas em sistemas de arquivos de rede já causaram corrupção.
9. **Conta filha no AWS Organizations:** a documentação diz que um plano grátis (Free plan) **sobe sozinho para o plano pago ao entrar no Organizations**. Os créditos continuam valendo, mas **o compartilhamento de créditos vem ligado por padrão** e a atividade que dá os US$ 100 extras expira. Os free tiers "sempre grátis" do DSQL e do DynamoDB são contados **por conta pagadora (management account)**, não por conta filha. Ver [Free tier, créditos e Organizations](#free-tier-créditos-e-organizations).
10. **sa-east-1 é mais cara que us-east-1**: DSQL +25% (DPU) e +36% (storage); DynamoDB +50%; Aurora Serverless v2 +108% por ACU-hora; RDS t4g.micro +112%. Para o volume do casal a diferença absoluta é de centavos no DSQL e no DynamoDB, mas de US$ 3 a US$ 47 por mês nas opções com instância.

## Tabela comparativa

Custo mensal estimado (US$), com as suposições da seção [Suposições](#suposições). "Sem free tier" soma tudo ao preço de lista; "com free tier" aplica as franquias oficiais. Cálculo em [Contas](#contas).

| Opção | 25 mil: sa-east-1 | 25 mil: us-east-1 | 120 mil: sa-east-1 | 120 mil: us-east-1 | Resposta após ocioso | Maior limitação para o app |
|---|---|---|---|---|---|---|
| **Aurora DSQL** | 0,00 com free tier (0,10 sem) | 0,00 com free tier (0,07 sem) | 0,00 com free tier (0,29 sem) | 0,00 com free tier (0,23 sem) | Primeira conexão "mais lenta que o normal"; tempo não publicado | 3.000 linhas por transação, sem triggers/PL/pgSQL, só IAM, retry por conflito |
| **DynamoDB sob demanda** | 0,23 | 0,15 | 1,02 | 0,68 | Sem cold start (serviço de API) | Sem soma/`GROUP BY`; leitura de 1 MB por página de Query; modelagem por padrão de acesso |
| **DynamoDB provisionado (25 WCU/25 RCU grátis)** | cerca de 0,02 (só PITR) | cerca de 0,01 (só PITR) | cerca de 0,03 | cerca de 0,02 | Sem cold start | Mesmo do sob demanda, mais risco de throttling em consultas grandes |
| **Aurora Serverless v2, pausa automática** | 6,40 | 3,11 | 6,90 | 3,46 | Cerca de 15 s (oficial) | Latência de retomada; precisa de VPC ou Data API; mínimo de 5 min ocioso antes de pausar |
| **Aurora Serverless v2, sem pausa (0,5 ACU 24 h)** | 91,40 | 43,91 | 91,90 | 44,26 | Sem espera | Estoura o teto de US$ 5 |
| **RDS PostgreSQL db.t4g.micro, Single-AZ, 20 GiB gp3, 24 h** | 29,20 | 13,98 | 29,20 | 13,98 | Sem espera (instância sempre ligada) | Estoura o teto de US$ 5; 1 GiB de RAM; IPv4 público + US$ 3,65 |
| **SQLite em S3 (referência)** | 0,01 | 0,01 | 0,01 | 0,01 | Baixar o arquivo a cada uso (50 a 100 MB no pior caso) | Concorrência e consistência por conta da aplicação; sem SQL remoto |
| **SQLite em EFS (referência)** | 0,03 + Lambda em VPC | 0,02 + Lambda em VPC | 0,03 + Lambda em VPC | 0,02 + Lambda em VPC | Montagem NFS | Travas de arquivo em NFS podem corromper o banco (aviso do SQLite) |

| Opção | Backup e restauração (fonte oficial) | Python | Disponível em sa-east-1? |
|---|---|---|---|
| Aurora DSQL | AWS Backup: backups completos do cluster, agendados, restauração **sempre para um novo cluster**; **não há PITR citado na documentação**; backup exige cluster ativo | Conector oficial `aurora-dsql-python-connector` (sobre psycopg, psycopg2, asyncpg), gera o token IAM sozinho | Sim, `dsql.sa-east-1.api.aws` |
| DynamoDB | PITR de 1 a 35 dias (padrão 35), granularidade de segundos, restaura para uma nova tabela; AWS Backup também | `boto3` (SDK oficial; não busquei a página própria do boto3, ver Lacunas) | Sim (preço de lista existe) |
| Aurora Serverless v2 | Backup automático contínuo, retenção de 1 a 35 dias (padrão 1), PITR para um novo cluster; backup grátis até 100% do tamanho do cluster | psycopg/psycopg2 com senha, ou token IAM; AWS Python Driver tem plugin de IAM | Sim (PG 18.3, 17.4 e anteriores listados); auto-pause: ver Lacunas |
| RDS PostgreSQL | Backup automático + PITR (logs enviados ao S3 a cada 5 min), restaura para uma nova instância; backup grátis até 100% do storage provisionado | psycopg/psycopg2; token IAM de 15 min; AWS Python Driver com plugin IAM | Sim |
| SQLite em S3/EFS | Versões do objeto no S3, ou cópia do arquivo; não pesquisei versionamento (fora do escopo de "referência") | `sqlite3` da biblioteca padrão | S3 e EFS têm preço em sa-east-1 |

## Suposições

Todas as contas usam as mesmas suposições, para comparar as opções entre si. **São estimativas minhas**, não medições: o número real de consultas só sai depois do ticket 07 (exportar o Mobills).

| Item | Suposição |
|---|---|
| Volume | 25.000 e 120.000 lançamentos, 2 tags por lançamento (média) |
| Tamanho das linhas | Lançamento 250 B; ligação lançamento-tag 40 B (×2); índice por data 60 B; índice por tag 60 B (×2): **510 B por lançamento** no total (tabelas + índices) |
| Tamanho no disco | 25 mil: 12,7 MB; 120 mil: 61 MB. Cobrado como 0,1 GB (DSQL, Aurora) para dar margem a outras tabelas |
| Escritas | 1.200 transações por mês (cerca de 20 lançamentos por dia + edições e itens de planejamento) |
| Consultas pesadas (soma por mês e por tag sobre **todo** o histórico) | 1.200 por mês (cerca de 40 por dia: 2 pessoas × 5 aberturas × 4 gráficos). Pior caso porque varre o histórico inteiro |
| Consultas leves (lista do mês, busca) | 3.000 por mês |
| DSQL: bytes lidos por consulta pesada | 90 B por lançamento (média entre índice por data, 60 B, e por tag, 120 B), com índice cobrindo o valor |
| DSQL: CPU por consulta pesada | 40 ms por 10 mil linhas (**chute**; medir com `EXPLAIN ANALYZE VERBOSE`, que a documentação indica para isso) |
| DynamoDB: bytes lidos por consulta pesada | 150 B por lançamento (item enxuto), leitura **fortemente consistente** (1 RRU por 4 KB), sem agregados pré-calculados |
| DynamoDB: escrita | 1 lançamento + 2 itens de tag, em transação (cobra o dobro): 6 WRU por transação |
| Aurora Serverless v2 | 300 sessões de uso por mês, cada uma mantém o banco acordado por 10 minutos (5 de uso + 5 de ociosidade, o mínimo configurável) = **50 horas por mês** a 0,5 ACU; 25% das leituras das consultas pesadas vão ao disco |
| RDS | db.t4g.micro Single-AZ, 20 GiB gp3 (mínimo do gp3 no RDS PostgreSQL), 730 horas por mês |
| S3/SQLite | arquivo inteiro baixado por consulta; um PUT por escrita |

## Contas

Preços de lista (US$), das listas oficiais de preço em massa da AWS (ver [Fontes](#fontes)).

### Aurora DSQL

| Item | sa-east-1 | us-east-1 |
|---|---|---|
| DPU | US$ 0,00001 por DPU (US$ 10 por milhão) | US$ 0,000008 por DPU (US$ 8 por milhão) |
| Storage | US$ 0,45 por GB-mês | US$ 0,33 por GB-mês |
| Free tier (global) | primeiros 100.000 DPU e 1 GB por mês | idem |
| AWS Backup, storage "warm" | US$ 0,14 por GB-mês | US$ 0,10 por GB-mês |
| AWS Backup, restauração "warm" | US$ 0,028 por GB | US$ 0,02 por GB |

Fórmulas oficiais de DPU (página "How billing works in Aurora DSQL"):

- ReadDPU = max(bytes lidos; 2.048) × 0,00000183105
- WriteDPU = max(bytes escritos; 1.024) × 0,00004883 (cada linha conta no mínimo 128 B)
- ComputeDPU = segundos de CPU
- O exemplo oficial de um `INSERT` de 1 linha dá 0,06175 DPU; um `SELECT` de 5 linhas, 0,00675 DPU.

Conta para 25 mil lançamentos:

- Consulta pesada: leitura = 25.000 × 90 B = 2,25 MB × 0,00000183105 = 4,12 DPU; CPU = 0,04 × 2,5 = 0,10 DPU; **4,22 DPU**.
- 1.200 pesadas × 4,22 = 5.064 DPU; 3.000 leves × 0,03 = 90 DPU; 1.200 escritas × 0,065 = 78 DPU. **Total: 5.232 DPU por mês**.
- Dentro dos 100.000 DPU grátis: **US$ 0**. Sem free tier: 5.232 × US$ 10/mi = US$ 0,052 (sa-east-1) mais 0,1 GB × US$ 0,45 = US$ 0,045: **US$ 0,10**. Em us-east-1: 5.232 × US$ 8/mi = US$ 0,042 + 0,1 × 0,33 = US$ 0,033: **US$ 0,07**.

Conta para 120 mil lançamentos:

- Consulta pesada: 120.000 × 90 B = 10,8 MB × 0,00000183105 = 19,8 DPU; CPU = 0,48 DPU; **20,3 DPU**.
- 1.200 × 20,3 = 24.306 DPU; mais 90 e 78: **24.474 DPU por mês**. Dentro do free tier: **US$ 0**. Sem free tier: sa-east-1 24.474 × US$ 10/mi = US$ 0,245 + 0,1 GB × 0,45 = **US$ 0,29**; us-east-1 US$ 0,196 + 0,033 = **US$ 0,23**.

Estresse (10x mais consultas pesadas, 12.000 por mês): 25 mil = 50,8 mil DPU (ainda no free tier); 120 mil = 243 mil DPU, ou seja, 143 mil acima do grátis = **US$ 1,43** (sa-east-1) ou **US$ 1,15** (us-east-1).

Backup (opcional, AWS Backup): 7 cópias completas de 0,1 GB = 0,7 GB × US$ 0,14 = US$ 0,10 em sa-east-1 (US$ 0,07 em us-east-1). Suposição de 7 backups completos; não verifiquei se o AWS Backup faz cópias incrementais para o DSQL.

### DynamoDB

| Item | sa-east-1 | us-east-1 |
|---|---|---|
| Escrita sob demanda | US$ 0,9375 por milhão de WRU | US$ 0,625 por milhão |
| Leitura sob demanda | US$ 0,1875 por milhão de RRU | US$ 0,125 por milhão |
| Storage (Standard) | primeiros 25 GB grátis; depois US$ 0,375 por GB-mês | primeiros 25 GB grátis; depois US$ 0,25 |
| PITR | US$ 0,30 por GB-mês | US$ 0,20 por GB-mês |
| Provisionado: WCU / RCU | US$ 0,000975 / US$ 0,000195 por hora, depois de 25 WCU e 25 RCU grátis | US$ 0,00065 / US$ 0,00013 por hora |

Conta para 25 mil lançamentos (sob demanda):

- Escrita: 1.200 transações × 3 itens × 2 (transação) = 7.200 WRU × US$ 0,9375/mi = US$ 0,007.
- Consulta pesada: 25.000 × 150 B = 3,75 MB ÷ 4 KB = 916 RRU (fortemente consistente). 1.200 × 916 = 1,10 milhão de RRU; leves: 3.000 × 2 = 6 mil.
- Leitura: 1,105 mi × US$ 0,1875 = US$ 0,207 (sa-east-1) ou × US$ 0,125 = US$ 0,138 (us-east-1).
- PITR: 0,05 GB × US$ 0,30 = US$ 0,015 (sa) ou × 0,20 = US$ 0,010 (us). Storage: abaixo de 25 GB, grátis.
- **Total: US$ 0,23 (sa-east-1) e US$ 0,15 (us-east-1).**

Conta para 120 mil lançamentos: consulta pesada = 18 MB ÷ 4 KB = 4.395 RRU; 1.200 × 4.395 = 5,27 mi RRU; leitura US$ 0,99 (sa) e US$ 0,66 (us); mais escrita US$ 0,007 e PITR US$ 0,027 (sa): **US$ 1,02 (sa-east-1) e US$ 0,68 (us-east-1)**.

Estresse (10x): 25 mil = US$ 2,08 (sa) e US$ 1,39 (us); 120 mil = **US$ 9,92 (sa) e US$ 6,62 (us)**, acima do teto de US$ 5 em ambos.

Capacidade provisionada no free tier (25 WCU e 25 RCU, 25 GB; por região e por conta pagadora): sem cobrança de requests. Mas 25 RCU entregam 25 RRU por segundo; uma consulta pesada de 120 mil lançamentos (4.395 RRU) leva cerca de 3 minutos para ser servida sem throttling, além da capacidade de rajada. O custo ficaria só no PITR (US$ 0,02 a 0,03). Alternativa: guardar agregados mensais por tag atualizados na escrita, o que reduz a leitura em ordens de grandeza (decisão de modelagem, fora desta pesquisa).

### Aurora Serverless v2 (PostgreSQL)

| Item | sa-east-1 | us-east-1 |
|---|---|---|
| ACU-hora (config. Standard) | US$ 0,25 | US$ 0,12 |
| ACU-hora (I/O-Optimized) | US$ 0,33 | US$ 0,16 |
| Storage (Standard) | US$ 0,19 por GB-mês | US$ 0,10 por GB-mês |
| I/O (Standard) | US$ 0,28 por milhão | US$ 0,20 por milhão |
| Backup acima de 100% do cluster | US$ 0,037 por GB-mês | US$ 0,021 por GB-mês |

Conta (pausa automática, 50 horas acordado por mês a 0,5 ACU = 25 ACU-horas):

- Instância: 25 × US$ 0,25 = US$ 6,25 (sa-east-1); 25 × US$ 0,12 = US$ 3,00 (us-east-1).
- Storage: 0,1 GB × US$ 0,19 = US$ 0,02 (sa); US$ 0,01 (us).
- I/O: 25 mil: 12,75 MB ÷ 8 KB × 25% × 1.200 = 0,48 mi de I/O × US$ 0,28 = US$ 0,13 (sa) ou × 0,20 = US$ 0,10 (us). 120 mil: 61 MB ÷ 8 KB × 25% × 1.200 = 2,25 mi × US$ 0,28 = US$ 0,63 (sa) ou US$ 0,45 (us). (Tamanho de página de 8 KB e 25% de acerto no disco são suposições minhas.)
- **Total 25 mil: US$ 6,40 (sa) e US$ 3,11 (us). Total 120 mil: US$ 6,90 (sa) e US$ 3,46 (us).**
- **Sem pausa** (0,5 ACU × 730 h = 365 ACU-horas): US$ 91,25 (sa) ou US$ 43,80 (us), mais storage e I/O: **US$ 91,4 a 91,9 (sa) e US$ 43,9 a 44,3 (us)**.
- A parte de ACU depende só do tempo acordado, não do volume. Se as sessões do casal se juntarem (duas pessoas no mesmo intervalo de 5 min), as horas caem; se forem mais espalhadas (20 sessões por dia, 100 horas), o custo de ACU dobra.

### RDS PostgreSQL

| Item | sa-east-1 | us-east-1 |
|---|---|---|
| db.t4g.micro Single-AZ (2 vCPU, 1 GiB) | US$ 0,034 por hora | US$ 0,016 por hora |
| db.t4g.small Single-AZ | US$ 0,069 por hora | US$ 0,032 por hora |
| db.t3.micro Single-AZ | US$ 0,038 por hora | US$ 0,018 por hora |
| Storage gp3 | US$ 0,219 por GB-mês | US$ 0,115 por GB-mês |
| Backup acima de 100% do storage | US$ 0,095 por GB-mês | não coletei |
| IPv4 público, por hora | US$ 0,005 (≈ US$ 3,65 por mês) | idem |

Conta: sa-east-1: 730 h × US$ 0,034 = US$ 24,82 + 20 GiB × US$ 0,219 = US$ 4,38 = **US$ 29,20**. us-east-1: 730 × 0,016 = US$ 11,68 + 20 × 0,115 = US$ 2,30 = **US$ 13,98**. O preço independe do volume (20 GiB bastam: o banco tem menos de 0,1 GB). Os US$ 120 de crédito cobririam cerca de 4 meses (sa) ou 8,5 meses (us), se o crédito não expirar antes.

### SQLite em S3 e EFS (só referência)

- S3 Standard: US$ 0,0405 por GB-mês (sa-east-1) e US$ 0,023 (us-east-1); PUT US$ 0,007 por mil (sa) e US$ 0,005 (us); GET US$ 0,0056 por 10 mil (sa) e US$ 0,004 (us).
- Conta: 0,05 GB de storage + 1.200 PUT + 4.200 GET = **US$ 0,013 (sa) e US$ 0,009 (us)**, nos dois volumes. Custo de computação (Lambda baixando o arquivo, 13 a 61 MB, a cada acesso) não incluído.
- EFS Standard: US$ 0,57 por GB-mês (sa-east-1) e US$ 0,30 (us-east-1): 0,05 a 0,06 GB = US$ 0,03 (sa) e US$ 0,02 (us). A cobrança de throughput e a Lambda em VPC não foram calculadas.

## Detalhes por opção

### Aurora DSQL

- **Preço e free tier.** DPU e storage, como acima. O free tier é de 100 mil DPU e 1 GB por mês, aplicado automaticamente; segundo a página de preços, "se você tem uma organização no AWS Organizations, isso se aplica por management account" [F3]. Dentro dele, a própria AWS cita "um app de orçamento com algumas centenas de transações por dia" [F3].
- **Tempo após ocioso.** Cluster fica `Idle` e depois `Inactive` (recursos escalados a zero, dados preservados); a primeira conexão "será mais lenta que o normal" e "o tempo para restaurar depende do tamanho do cluster" [F6]. **Quantos segundos: não encontrado na fonte oficial.** Backups só rodam com o cluster `Active` [F6].
- **Limites.** Máx. 3.000 linhas alteradas por transação (qualquer DML, independente de índices), 10 MiB de dados por transação, 5 min por transação, 60 min por conexão, 1 KiB de chave primária/índice, 2 MiB por linha, 1 MiB por coluna não indexada, 24 índices por tabela, 255 colunas, 1.000 tabelas, 10 schemas, 1 banco por cluster, 100 conexões novas por segundo; isolamento fixo em Repeatable Read; collation C; sem tabelas temporárias; sem PL/pgSQL (só funções SQL); sem triggers ("use lógica na aplicação"); `CREATE INDEX ASYNC` no lugar de `CREATE INDEX`; sem `TRUNCATE`; concorrência otimista com erro de serialização (`OC000`) que exige retry [F4, F5, F7]. Tipos: `numeric`, `uuid`, `json` e `jsonb` suportados [F8].
- **Foreign keys: agora suportadas** (nota de versão de 26/08/2026) com `NO ACTION`, `RESTRICT`, `CASCADE`, `SET NULL`, `SET DEFAULT`; custo: leituras extras em toda DML das tabelas envolvidas, e conflito de FK em transações concorrentes vira erro de serialização [F7, F9].
- **Impacto no app.** (a) Importar 25 mil a 120 mil lançamentos: em lotes de até 3.000 linhas por transação, lembrando que a linha de tag também conta (≈ 75 mil a 360 mil linhas = 25 a 120 lotes de 3.000, ou mais lotes menores). Custo da carga única estimado em poucos milhares de DPU. (b) Somas por mês e por tag rodam no banco com SQL comum (`GROUP BY`, `HAVING`, CTE com `WITH` e `OVER (PARTITION BY ...)` constam como suportados) [F10]; índices que cobrem a consulta reduzem os DPU. (c) Sem trigger: "quem alterou por último" e saldos derivados precisam ser feitos na aplicação.
- **Python e autenticação.** Autenticação **somente por IAM**: token com validade padrão de 15 minutos, máximo de 1 semana [F11]. Conector oficial `aurora-dsql-python-connector` (`pip install aurora-dsql-python-connector`) sobre psycopg, psycopg2 e asyncpg, com geração automática do token e descoberta de região [F12].
- **Backup.** Integração com AWS Backup: backups completos, agendamento e retenção, cópia entre regiões e contas; restauração cria sempre um novo cluster [F13]. **PITR do DSQL: não encontrado na fonte oficial** (a página de backup não cita).
- **Região.** `sa-east-1` consta na lista de regiões do DSQL (endpoint `dsql.sa-east-1.api.aws`) [F14] e na lista de preços [F1]. Cluster de região única: 99,99% de disponibilidade citada [F14].

### DynamoDB

- **Preço e free tier.** Acima. O free tier é de **capacidade provisionada** (25 WCU, 25 RCU) na classe Standard, 25 GB, por região e por conta pagadora; sob demanda não tem franquia de requests [F15].
- **Tempo após ocioso.** Não há instância; é uma API. **Medida de latência de primeira chamada: não encontrado na fonte oficial** (nem necessária para este desenho).
- **Limites.** Item de até 400 KB; Query devolve até 1 MB por página; transação de até 100 ações e 4 MB; 20 GSIs por tabela [F16, F17, F18]. A sintaxe de `SELECT` do PartiQL no DynamoDB documentada não tem agregação (`SUM`, `GROUP BY`) nem `JOIN` [F19]; assim, "total por mês e tag" se faz lendo itens e somando na aplicação ou mantendo agregados na escrita. Consulta por tag exige item por par (lançamento, tag) ou GSI com a tag como chave; item com várias tags não indexa cada tag sozinho.
- **Python.** `boto3` (não fetchei página própria; ver Lacunas). Autenticação nativa por IAM, sem tokens de banco.
- **Backup.** PITR de 1 a 35 dias (padrão 35), granularidade de segundos, restaura sempre para uma nova tabela; restauração entre regiões possível [F20, F21].
- **Região.** Preço de lista em sa-east-1 existe [F2].

### Aurora Serverless v2 (PostgreSQL) com pausa automática

- **Pausa.** Mínimo de capacidade 0 ACU liga o auto-pause; ociosidade mínima configurável de 300 s (padrão), máxima de 86.400 s. Pausado, a instância não cobra ACU; storage e demais itens do cluster continuam cobrados [F22].
- **Tempo após ocioso.** "O tempo típico de retomada pode ser de aproximadamente 15 segundos"; a AWS recomenda timeout de conexão acima de 15 s (30 s se parado por mais de um dia) e retry [F22].
- **Versões.** Auto-pause exige Aurora PostgreSQL 16.3, 15.7, 14.12 ou 13.15 ou superior [F22]. A lista de regiões mostra Aurora PostgreSQL serverless em São Paulo a partir da 18.3 e 17.4 para baixo [F23].
- **Limites do app.** Banco PostgreSQL completo (FKs, triggers, PL/pgSQL, extensões) [conhecimento geral do PostgreSQL; não fetchei a lista de extensões]. Em Lambda, exige VPC ou o RDS Data API (US$ 0,35 por milhão de requests em us-east-1; 1 milhão grátis por mês no primeiro ano [F24, F25]; preço de sa-east-1 não coletado).
- **Python.** psycopg/psycopg2; IAM de banco funciona (token de 15 min) e o AWS Python Driver traz o plugin [F26].
- **Backup.** Retenção de 1 a 35 dias (padrão 1 dia, não dá para desligar), PITR contínuo para um novo cluster; AWS Backup também pode gerir [F27, F28]. Backup grátis até 100% do tamanho do cluster [F29].
- **Plano grátis (se a conta ficasse no Free plan):** Aurora PostgreSQL serverless "com até 4 ACUs e 1 GiB de storage por cluster" [F30]. Como a conta filha do Organizations vira plano pago (abaixo), esse limite não deve se aplicar, mas não consegui confirmar o tratamento de uma conta criada dentro de uma Organization.

### RDS PostgreSQL (instância pequena)

- **Free tier.** A página de preços do RDS PostgreSQL ainda descreve "750 horas, 20 GB gp2, 20 GB de backup por um ano" (regra antiga) [F31]; a página de free tier nova diz que o Free plan cobre db.t3.micro e db.t4g.micro, e que quem ativou a conta antes de 15/07/2025 mantém o "Legacy Free Tier" de 12 meses [F30]. Conta nova: **não há 750 horas grátis de 12 meses; vale o plano de créditos**.
- **Tempo após ocioso.** Sem espera, mas a instância cobra 24 horas. Parar a instância evita cobrança de instância, **mas o RDS religa sozinho após 7 dias** [F32].
- **Limites.** PostgreSQL completo. 1 GiB de RAM no t4g.micro [F2]. Instâncias T4g rodam em modo "Unlimited": CPU acima da linha de base cobra US$ 0,075 por vCPU-hora [F31].
- **Python e IAM.** Autenticação IAM de banco com token de 15 min; AWS Python Driver com plugin [F26].
- **Backup.** Backup automático e PITR (logs enviados ao S3 a cada 5 minutos) para uma nova instância; grátis até 100% do storage provisionado [F31, F33]. Retenção máxima e padrão: não confirmados nas páginas lidas.
- **IPv4 público:** US$ 0,005 por hora (≈ US$ 3,65 por mês) [F34]. Atenção: a documentação do RDS tem o recurso "publicly accessible"; se o app for Lambda sem VPC, precisará de IP público ou de NAT (custo extra, não calculado).

### SQLite em S3 ou EFS (referência)

- **S3.** Armazena o arquivo como objeto. S3 tem escrita condicional (`If-Match` com ETag e `If-None-Match`), usável para uma trava otimista [F35]. Cada acesso baixa o arquivo inteiro; escrever é reenviar tudo. Serve para dois usuários, mas falha a "visão consistente" em escritas simultâneas sem essa trava.
- **EFS.** A documentação do SQLite diz que travas e `fsync` em sistemas de arquivos de rede "têm funcionado incorretamente" e que isso "levou à corrupção do banco" [F36]. EFS é NFS: não recomendado.
- **Backup.** Fora do escopo detalhado: versionamento do S3 e cópias do arquivo. Não pesquisado.

## Free tier, créditos e Organizations

Fatos das páginas oficiais, sobre uma conta nova filha de uma conta de governança, com US$ 120 de crédito:

- Contas novas recebem **US$ 100 de crédito** ao criar a conta e podem ganhar **até US$ 100** completando atividades, em qualquer plano; Free plan dura **no máximo 6 meses ou até os créditos acabarem** [F37, F38].
- **"Free account plans will automatically upgrade to paid plan if you join AWS Organizations"** [F38]. Em plano pago, o que passar dos créditos é cobrado a preço normal. Resultado prático: a trava "nunca cobra" do Free plan **não protege** essa conta; o controle de gasto fica com orçamento (AWS Budgets) e com o teto de US$ 5 do dono.
- Sobre o prazo dos créditos, a própria página de FAQ **se contradiz**: "expiram 6 meses depois de criar a conta" (Q6) e "12 meses depois" (Q8, ao migrar para o pago e nos créditos de atividade) [F39]. A página do Aurora diz "até 12 meses" [F30]. **Prazo exato: não confirmado; trate como 6 meses.**
- As atividades que dão os US$ 100 extras **expiram imediatamente ao entrar em uma AWS Organization** [F39]. Se o crédito de US$ 120 do dono tem outra origem (ex.: US$ 100 + US$ 20 de atividades antes de entrar), isso não está claro; **origem do crédito de US$ 120: não consta nas fontes**.
- **Compartilhamento de créditos:** com o compartilhamento ligado (padrão), os créditos vão primeiro para a conta que os possui, mas o restante pode ser aplicado a outras contas da organização [F40]. Isso quer dizer que o gasto da conta de governança pode consumir o crédito se o compartilhamento não for desligado pela conta pagadora (**quem controla é a bill source account**) [F40].
- **Franquias "sempre grátis" são por conta pagadora:** DSQL "se aplica por management account" [F3]; DynamoDB "por região e por conta pagadora" [F15]. Se outras contas da organização usarem DSQL/DynamoDB, dividem as mesmas franquias.
- **Crédito cobre DSQL, DynamoDB, Aurora e RDS:** as páginas oficiais dizem "use credits to access Aurora PostgreSQL / Aurora DSQL / RDS" [F30]. Itens que o crédito não cobre (ex.: Savings Plans, Reserved Instances) [F38].
- Se o crédito fosse a única fonte de pagamento, US$ 120 cobririam: DSQL e DynamoDB por muito mais do que os 6 a 12 meses de validade; RDS t4g.micro em sa-east-1 por cerca de 4 meses.

## Lacunas

- **Tempo de retomada do DSQL** após Idle/Inactive: a documentação só diz "mais lenta que o normal" e que depende do tamanho do cluster. Medir na prática (ticket de protótipo, se houver).
- **PITR no DSQL:** a página de backup só cita AWS Backup (backups completos); não encontrei PITR.
- **CPU real das consultas** (DSQL) e **tamanho real de linha**: usei chutes (40 ms por 10 mil linhas; 250 B por lançamento). O número de lançamentos e o padrão de acesso reais vêm do ticket 07 e de um protótipo. A conta é linear: dobrar as consultas pesadas dobra o DPU e o RRU.
- **Auto-pause (0 ACU) em sa-east-1:** a documentação vincula o recurso à versão do motor, não a regiões; não achei confirmação explícita para São Paulo.
- **Prazo exato dos créditos** (6 ou 12 meses) e **tratamento de contas criadas dentro de Organizations** (se recebem os US$ 100 de cadastro): contradições e omissões nas páginas oficiais.
- **Preços não coletados:** Data API em sa-east-1; throughput elástico do EFS; backup do RDS em us-east-1; retenção padrão e máxima do RDS.
- **boto3 e psycopg:** não consultei a documentação própria do `boto3` nem do `psycopg`; as afirmações sobre eles aqui são do guia da AWS (conector DSQL e driver Python do RDS).
- **Extensões e recursos do PostgreSQL** no Aurora/RDS (ex.: extensões disponíveis em sa-east-1): não pesquisado.
- **SQLite em S3 e EFS:** só custo de armazenamento e requests; sem latência medida nem custo de computação.
- Todos os cálculos são **estimativas mensais, sem imposto** (IOF/impostos brasileiros não considerados).

## Fontes

Todas acessadas em **2026-10-24**. Os preços saem da API pública de lista de preços da AWS (arquivos JSON em massa por serviço), porque as páginas de preço (ex.: [F3]) carregam os valores por JavaScript (`{priceOf!...}`) e o `curl` trouxe só os marcadores. A página [F3] confirma os valores de us-east-1 em seus exemplos (US$ 8 por milhão de DPU e US$ 0,33 por GB-mês). Datas de publicação dos arquivos: DSQL 2026-09-11; DynamoDB 2026-09-11; RDS sa-east-1 2026-10-20; S3 2026-10-15; EFS 2026-09-11; AWS Backup 2026-10-14.

Listas de preço (JSON):

- F1. DSQL: https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AuroraDSQL/current/index.json
- F2. DynamoDB: https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonDynamoDB/current/index.json; RDS/Aurora: https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonRDS/current/sa-east-1/index.json e `.../us-east-1/index.json`; S3: `.../AmazonS3/current/<região>/index.json`; EFS: `.../AmazonEFS/current/index.json`; Backup: `.../AWSBackup/current/index.json` (todas em `https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/`).

Páginas de preço e free tier:

- F3. https://aws.amazon.com/rds/aurora/dsql/pricing/ (DPU, storage, free tier, exemplos, Organizations)
- F15. https://aws.amazon.com/dynamodb/pricing/ (free tier provisionado, exemplos)
- F30. https://aws.amazon.com/rds/free/ e https://aws.amazon.com/rds/aurora/pricing/ (Free plan: Aurora até 4 ACU e 1 GiB; RDS t3/t4g.micro; DSQL sempre grátis; backup Aurora)
- F31. https://aws.amazon.com/rds/postgresql/pricing/ (backup, créditos de CPU, texto legado de 750 h)
- F34. https://aws.amazon.com/vpc/pricing/ (IPv4 público, US$ 0,005 por hora)
- F37/F39. https://aws.amazon.com/free/free-tier-faqs/ (planos, validade dos créditos, atividades, Organizations)
- F38. https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/free-tier-plans.html e https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/free-tier.html (Free plan sobe para pago ao entrar no Organizations; US$ 100 + US$ 100)
- F40. https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/useconsolidatedbilling-credits.html (compartilhamento de créditos em Organizations)

Documentação do Aurora DSQL (`https://docs.aws.amazon.com/aurora-dsql/latest/userguide/`):

- F4. `CHAP_quotas.html` (limites)
- F5. `considerations.html`
- F6. `cluster-lifecycle.html` (Idle, Inactive, primeira conexão lenta, backup exige Active)
- F7. `working-with-postgresql-compatibility-migration-guide.html` (3.000 linhas, sem triggers/PL/pgSQL, OCC, isolamento)
- F8. `working-with-postgresql-compatibility-supported-data-types.html`
- F9. `working-with-foreign-key-constraints.html` e `release-notes.html` (FK desde 26/08/2026)
- F10. `working-with-postgresql-compatibility-supported-sql-features.html`
- F11. `SECTION_authentication-token.html` e `authentication-authorization.html` (token IAM de 15 min)
- F12. `SECTION_program-with-dsql-connector-for-python.html`
- F13. `backup-aurora-dsql.html` (AWS Backup)
- F14. `what-is-aurora-dsql.html` (regiões, incluindo sa-east-1; disponibilidade)
- Fórmulas de DPU e exemplos: `billing-metering.html`

Documentação do DynamoDB (`https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/`):

- F16. `Constraints.html` (item 400 KB)
- F17. `GSI.html` (Query até 1 MB), `ServiceQuotas.html` (20 GSIs)
- F18. `transaction-apis.html` (100 ações, 4 MB)
- F19. `ql-reference.select.html` (sintaxe PartiQL `SELECT`)
- F20. `Point-in-time-recovery.html`
- F21. `Backup-and-Restore.html`
- Unidades de leitura e escrita (4 KB e 1 KB): `read-write-operations.html`

Documentação do Aurora/RDS (`https://docs.aws.amazon.com/AmazonRDS/latest/`):

- F22. `AuroraUserGuide/aurora-serverless-v2-auto-pause.html`
- F23. `AuroraUserGuide/Concepts.Aurora_Fea_Regions_DB-eng.Feature.ServerlessV2.html`
- F24. `AuroraUserGuide/data-api.html`
- F25. Preço do Data API: lista JSON do RDS (us-east-1: US$ 0,00000035 por request)
- F26. `UserGuide/UsingWithRDS.IAMDBAuth.html` (IAM, token de 15 min, AWS Python Driver)
- F27. `AuroraUserGuide/Aurora.Managing.Backups.html`
- F28. `AuroraUserGuide/aurora-pitr.html`
- F29. https://aws.amazon.com/rds/aurora/pricing/ (backup grátis até 100% do cluster)
- F32. `UserGuide/USER_StopInstance.html` (religa após 7 dias)
- F33. `UserGuide/USER_PIT.html` (logs a cada 5 minutos) e `UserGuide/CHAP_Storage.html` (gp3 de 20 a 65.536 GiB)
- Capacidade mínima 0,5 ACU: `AuroraUserGuide/aurora-serverless-v2.setting-capacity.html`

Referência SQLite e S3:

- F35. https://docs.aws.amazon.com/AmazonS3/latest/userguide/conditional-writes.html
- F36. https://www.sqlite.org/useovernet.html
