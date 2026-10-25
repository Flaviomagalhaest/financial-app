# Banco de dados na AWS para dois usuários e histórico longo

Type: research
Status: resolved
Blocked by: —
Skills: `research` (AFK, em sub-agente)
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #21
Origem: traçado do [mapa V1 que substitui o Mobills](../map.md)

## Question

Qual o custo mensal real e quais as limitações de cada opção de banco na AWS para o volume do casal?

Opções: Aurora DSQL, DynamoDB, Aurora Serverless v2 (com pausa automática), RDS PostgreSQL em instância pequena e, só como referência, SQLite guardado em S3 ou EFS.

Para cada uma, levantar:

- preço por uso e por armazenamento, e o que o free tier cobre numa conta nova (regras de julho de 2025 em diante) que é filha de uma conta de governança no AWS Organizations, com US$ 120 de crédito;
- tempo para responder depois de um período parado;
- limites que afetam o app (ex.: no DSQL, sem foreign keys nem triggers e até 3.000 linhas por transação; no DynamoDB, consultas por tag e somas por período);
- suporte a Python (driver, autenticação por IAM);
- backup e restauração (PITR, AWS Backup);
- disponibilidade em São Paulo (sa-east-1) e diferença de preço para Virgínia (us-east-1).

Volume de referência, até [Exportar o Mobills e medir o histórico](07-exportar-o-mobills-e-medir-o-historico.md) trazer o número real: de 25 mil (7 anos) a 120 mil (30 anos) lançamentos. Padrão de consulta dos dashboards: somas por mês e por tag sobre anos de histórico.

Decisão que espera por isso: [Banco de dados e região](09-banco-de-dados-e-regiao.md).

## Checklist

- [x] Fontes primárias: páginas de preço e guias oficiais da AWS
- [x] Custo mensal estimado de cada opção no volume de referência, com a conta mostrada
- [x] Achados num único Markdown, cada afirmação com a fonte, numa branch `research/banco-de-dados-aws` enviada e sem PR
- [x] Ponteiro para a branch e resumo do achado neste ticket, em `## Answer`

## Answer

Achados completos na branch `research/banco-de-dados-aws` (arquivo `.scratch/v1-substituir-mobills/research/banco-de-dados-aws.md`, commit `85c69f7`), enviada sem PR e sem tag. Preços lidos da API pública de preços da AWS (as páginas de preço carregam os valores por JavaScript); docs e FAQ lidos direto da AWS, em 2026-10-24. As premissas de consumo são do pesquisador; os preços são oficiais.

Custo mensal estimado (US$), com 25 mil / 120 mil lançamentos:

- **Aurora DSQL:** 0 no free tier; sem ele, 0,10 / 0,29 (sa-east-1) e 0,07 / 0,23 (us-east-1).
- **DynamoDB sob demanda:** 0,23 / 1,02 (sa-east-1) e 0,15 / 0,68 (us-east-1). Não soma nem agrupa: somas por tag e período leem os itens ou exigem agregados mantidos na escrita. Com 10x mais consultas pesadas passa do teto de US$ 5 em 120 mil.
- **Aurora Serverless v2 com pausa:** 6,40 / 6,90 (sa-east-1) e 3,11 / 3,46 (us-east-1); retoma em cerca de 15 s. Sem pausa: 91 (sa-east-1) e 44 (us-east-1).
- **RDS PostgreSQL db.t4g.micro:** 29,20 (sa-east-1) e 13,98 (us-east-1), independente do volume.
- **SQLite em S3:** cerca de 0,01; em EFS, cerca de 0,03, mas não recomendado (travas em NFS).

Pontos que mudam a decisão:

- O volume é pequeno (13 a 61 MB); o custo vem das consultas de dashboard.
- **O ticket estava desatualizado:** o DSQL passou a suportar foreign keys (nota de versão de 26/08/2026). Continuam: sem triggers, 3.000 linhas e 10 MiB por transação, só IAM, concorrência otimista. Há conector Python oficial; backup só pelo AWS Backup (PITR não encontrado).
- **Conta filha no Organizations:** o Free plan sobe sozinho para o plano pago ao entrar na Organization (a trava de "nunca cobra" não vale); o compartilhamento de créditos vem ligado por padrão; as franquias do DSQL e do DynamoDB contam por management account; a FAQ se contradiz sobre a validade dos créditos.
- sa-east-1 é mais cara que us-east-1 (DSQL +25% em DPU e +36% em storage; DynamoDB +50%; Aurora ACU +108%; RDS +112%).

Lacunas (detalhadas no arquivo da branch): tempo de retomada do DSQL em segundos, PITR no DSQL, auto-pause em sa-east-1, origem e prazo dos US$ 120 de crédito, tamanho real das linhas e CPU real das consultas (dependem do ticket 07 e de protótipo). Seguem em [Reconferir as lacunas das pesquisas de plataforma e de banco](15-reconferir-lacunas-das-pesquisas.md).
