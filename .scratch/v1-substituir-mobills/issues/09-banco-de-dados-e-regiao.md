# Banco de dados e região

Type: grilling
Status: resolved
Blocked by: —
Skills: `grilling` e `domain-modeling` (HITL: precisa do dono)
Modelo recomendado: Opus
Effort recomendado: high
Issue: #27
Origem: traçado do [mapa V1 que substitui o Mobills](../map.md)

## Question

Qual banco guarda os dados do app e em que região da AWS?

Decidir com os custos e limitações de [Banco de dados na AWS para dois usuários e histórico longo](03-banco-de-dados-na-aws.md) e com o volume real de [Exportar o Mobills e medir o histórico](07-exportar-o-mobills-e-medir-o-historico.md). Inclui: como o histórico longo é organizado para os dashboards de vários anos continuarem rápidos; retenção e backup; São Paulo ou Virgínia.

## Checklist

- [x] Confirmar na lista oficial de regiões se o DSQL existe em sa-east-1 (se não existir, "migrar para sa-east-1" é trocar de banco, não só de região)
- [x] Medir a latência real do Brasil para us-east-2 (RTT estimado em 120–150 ms contra 10–30 ms de sa-east-1) e decidir se consultas em lote e cache no cliente bastam
- [x] Confirmar no console o prazo do plano gratuito (6 meses ou fim dos créditos) e se o DSQL tem franquia mensal própria
- [x] Decisão registrada em `## Answer`
- [x] ADR em `docs/adr/` (banco é escolha com lock-in)

## Answer

Decidido com o dono em 2026-10-25. [ADR 0009](../../../docs/adr/0009-aurora-dsql-em-sao-paulo.md).

**Banco: Aurora DSQL.** É a única opção com SQL (somas e `GROUP BY` no banco) e custo perto de zero: US$ 0 na franquia de 100 mil DPU e 1 GB por mês, que nenhum outro projeto da organização usa, e US$ 0,10 a 0,29 por mês sem ela, em sa-east-1. O DynamoDB não soma nem agrupa e dividiria a franquia com o outro projeto; o Aurora Serverless v2 com pausa custa US$ 3 a 7 por mês e leva 15 s ou mais para voltar. A escolha é revista se o [ticket 17](17-medir-retomada-e-confirmar-pontos-no-prototipo.md) medir mais de 5 s na primeira conexão depois do cluster parado.

**Região: sa-east-1 (São Paulo), o app inteiro numa região só.** API, banco, bucket do backup, hospedagem e login ficam em sa-east-1; em us-east-1 só os serviços globais (IAM, Budgets e o certificado do CloudFront, se houver), que a SCP da organização já libera. O app não nasce em us-east-2 para depois migrar: isso evita refazer o pool de usuários, buckets e segredos. A diferença de preço do DSQL para us-east-1 é de centavos, os créditos valem em qualquer região e a latência fica em 10 a 30 ms. LGPD não se aplica: uso só pessoal, de 2 pessoas ([ADR 0002](../../../docs/adr/0002-app-fechado-para-dois-usuarios.md)).

**Histórico longo:** uma tabela de lançamentos, sem agregados pré-calculados nem particionamento na v1. Cada lançamento grava o mês em que conta (o **mês da fatura** para compra no cartão, [ADR 0003](../../../docs/adr/0003-compra-no-cartao-conta-no-mes-da-fatura.md)), com índices por esse mês, por data e por conta. Com cerca de 11 mil linhas hoje e 120 mil no pior caso em 30 anos, somas de vários anos leem dezenas de milhares de linhas com índice. Se um dashboard passar de 1 s no servidor, entra um agregado mensal.

**Latência:** cada tela faz uma chamada à API, que devolve tudo em lote, com cache no aparelho e lançamentos na fila offline ([ADR 0005](../../../docs/adr/0005-app-web-instalavel-em-vez-de-app-nativo.md)); a API fica na mesma região do banco. Com sa-east-1 a medição de casa deixou de ser necessária; o critério registrado é revisar a região acima de 250 ms de ida e volta.

**Retenção:** todo o histórico, para sempre. Nada é apagado nem arquivado; os dashboards de vários anos leem a mesma tabela.

**Backup:** uma tarefa agendada diária gera a exportação completa no formato do próprio app (a mesma função "exportar tudo" do mapa; a conexão acorda o cluster) e grava num bucket S3 em sa-east-1, com versionamento, retenção de 90 dias e Object Lock nas versões. Restaurar é importar a exportação num banco novo; a perda máxima é de 1 dia. Sem AWS Backup na v1 (não tem PITR no DSQL, exige o cluster ativo e restaura num cluster novo). O backup fica na mesma conta, e esse risco é aceito na v1; a cópia fora da AWS ficou para depois da v1 (Out of scope do mapa). O formato da exportação segue no tópico "Exportação" do mapa.

**Portabilidade (vale para todo o código):** região e endpoint só em configuração, sem ARN nem hostname no código; migrations versionadas no repositório; schema dentro do subconjunto do DSQL (sem triggers, sem PL/pgSQL, até 3.000 linhas e 10 MiB por transação, então a importação do Mobills grava em lotes); o app trata o erro de serialização da concorrência otimista tentando de novo. A autenticação sem amarra ao Cognito fica no [ticket 12](12-como-o-app-roda-na-aws.md).

Fatos do checklist:

- **DSQL em sa-east-1:** existe, endpoint `dsql.sa-east-1.api.aws` ([tabela oficial de regiões](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/what-is-aurora-dsql.html), lida em 2026-10-25). sa-east-1 não entra em nenhum conjunto multi-região do DSQL, o que não afeta um cluster de uma região.
- **Latência:** a AWS não publica tabela oficial; um medidor de terceiros ([economize.cloud](https://www.economize.cloud/resources/aws/latency/sa-east-1-vs-us-east-2/)) dá cerca de 125 ms entre sa-east-1 e us-east-2. Não foi medido da casa do dono, porque a escolha de sa-east-1 tirou a pergunta do caminho.
- **Plano gratuito:** créditos de US$ 119,98 até 12/04/2027 ([ticket 16](16-conferir-credito-e-compartilhamento-na-conta-aws.md)); a franquia do DSQL (100 mil DPU e 1 GB por mês, por conta pagadora) é "sempre grátis" e continua depois dessa data.

## Comments

- Estratégia do dono: a conta gratuita está em us-east-2; ao fim dos créditos ou em cerca de 6 meses pode migrar para sa-east-1. Avaliação: o volume é pequeno (2 usuários), então dump/restore basta; os riscos são a latência do Brasil, o DSQL talvez não existir em sa-east-1, recursos presos à região (pool de usuários do Cognito não migra entre regiões; S3, segredos e IAM também) e, se o app tiver mais usuários um dia, a LGPD para dados fora do Brasil (uso exclusivamente pessoal fica fora da lei).
- Para a migração custar pouco: região e endpoint só em configuração (sem ARN nem hostname no código); migrations versionadas no repositório; `pg_dump` ou exportação periódica guardada fora da AWS; schema no subconjunto que o DSQL aceita (sair dele para o Aurora é fácil, o inverso não); evitar acoplar a autenticação ao Cognito, se possível.
- A SCP da organização negou DSQL e RDS em sa-east-1 e liberou us-east-2 (veja o [ticket 17](17-medir-retomada-e-confirmar-pontos-no-prototipo.md)); isso não prova que o DSQL não exista em sa-east-1.
- O [ticket 07](07-exportar-o-mobills-e-medir-o-historico.md) está resolvido: o histórico real tem cerca de 11 mil linhas em 7 anos e 8 meses (6.283 transações e 4.742 compras de cartão, com sobreposição de cerca de 80% das despesas), na ordem de poucos MB. O volume não pesa na escolha do banco.
- Grilling de 2026-10-25: o dono decidiu começar em sa-east-1 em vez de us-east-2. Teste com o usuário IAM `financial-cli` (conta 255235818791): `dsql:ListClusters` funcionou em us-east-2 e foi negado em sa-east-1 por `explicit deny` da SCP `p-q0eemrzp` (`AdvancedModeRegionRestrictionSecurityControlPolicy`, não gerida pela AWS, anexada à raiz `r-tip7` da organização `o-izrh6ws8cc`, management account 867703356372). O bloco `RegionFloor` negava tudo, exceto Bedrock, fora de us-east-1, us-east-2 e us-west-2; em us-east-1 só passam os serviços globais. O dono acrescentou `sa-east-1` ao `RegionFloor` com `update-policy`, e o `ListClusters` em sa-east-1 passou a responder `{"clusters": []}`. A mudança vale para todas as contas da organização. A origem da SCP é desconhecida (talvez um assistente de configuração, que pode reaplicar a versão dele) e ela está perto do limite de 5.120 caracteres (5.094 depois da mudança); ambos ficam no [ticket 12](12-como-o-app-roda-na-aws.md), que cobre a configuração da conta.
