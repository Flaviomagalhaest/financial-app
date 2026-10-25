# Comparativo lado a lado de banco e região

Type: research
Status: ready-for-agent
Blocked by: 16, 17
Skills: `research` (consolidação, sem pesquisa nova); apoio: `artifact-design` se o dono quiser o comparativo como página
Modelo recomendado: Sonnet
Effort recomendado: medium
Trello: ari:cloud:trello::card/workspace/598b72bf7efc694a04666f1f/6ade116150ef0475fc1be632
Origem: pedido do dono na sessão do [ticket 17](17-medir-retomada-e-confirmar-pontos-no-prototipo.md): concentrar testes e custos num comparativo para decidir o banco e a região em [Banco de dados e região](09-banco-de-dados-e-regiao.md)

## Question

Qual banco e qual região (us-east-2 ou sa-east-1) vencem quando custo, retomada, latência, limitações e backup ficam lado a lado, cada número com sua origem?

## Checklist

- [ ] Um único arquivo `.scratch/v1-substituir-mobills/research/comparativo-banco-e-regiao.md`, com colunas Aurora DSQL, Aurora Serverless v2 com pausa e DynamoDB (RDS e SQLite só como referência), cada uma em us-east-2 e sa-east-1
- [ ] Linhas: custo mensal a 25 mil e a 120 mil lançamentos (de [03](03-banco-de-dados-na-aws.md)); retomada em segundos (de [17](17-medir-retomada-e-confirmar-pontos-no-prototipo.md)); latência Brasil–região medida (item do [09](09-banco-de-dados-e-regiao.md)); limitações; backup e restauração; disponibilidade na região; efeito da SCP; crédito e franquias da conta (de [16](16-conferir-credito-e-compartilhamento-na-conta-aws.md))
- [ ] Cada célula marcada como medida, estimada (com a premissa) ou lacuna aberta, com a fonte ou o ticket de origem
- [ ] Resumo no topo: o que cada região custa a mais e o que compra em latência; o que ainda falta medir
- [ ] Resultado em `## Answer`; dizer o que muda em [Banco de dados e região](09-banco-de-dados-e-regiao.md)

## Comments

- Valores já levantados em [03](03-banco-de-dados-na-aws.md) (branch `research/banco-de-dados-aws`): DSQL 0,10 / 0,29 (sa-east-1) e 0,07 / 0,23 (us-east-1) sem free tier; Aurora v2 com pausa 6,40 / 6,90 (sa-east-1) e 3,11 / 3,46 (us-east-1); RDS t4g.micro 29,20 e 13,98; DynamoDB 0,23 / 1,02 e 0,15 / 0,68. O DSQL consta como disponível em sa-east-1 nessa pesquisa, mas a SCP da organização nega DSQL e RDS lá; us-east-2 está liberada.
- Entradas que ainda não existem: os números de [17](17-medir-retomada-e-confirmar-pontos-no-prototipo.md) (script e roteiro prontos em `../prototipos/17/`, falta o dono rodar), o crédito de [16](16-conferir-credito-e-compartilhamento-na-conta-aws.md) e a latência Brasil–us-east-2, que sai das mesmas execuções do [17](17-medir-retomada-e-confirmar-pontos-no-prototipo.md) (`rtt_tcp_ms`).
- Os preços do arquivo de [03](03-banco-de-dados-na-aws.md) são de 2026-10-24; reconferir na API de preços da AWS antes de fechar.
