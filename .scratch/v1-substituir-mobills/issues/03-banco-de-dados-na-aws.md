# Banco de dados na AWS para dois usuários e histórico longo

Type: research
Status: claimed
Blocked by: 13
Skills: `research` (AFK, em sub-agente)
Modelo recomendado: Sonnet
Effort recomendado: medium
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

- [ ] Fontes primárias: páginas de preço e guias oficiais da AWS
- [ ] Custo mensal estimado de cada opção no volume de referência, com a conta mostrada
- [ ] Achados num único Markdown, cada afirmação com a fonte, numa branch `research/banco-de-dados-aws` enviada e sem PR
- [ ] Ponteiro para a branch e resumo do achado neste ticket, em `## Answer`
