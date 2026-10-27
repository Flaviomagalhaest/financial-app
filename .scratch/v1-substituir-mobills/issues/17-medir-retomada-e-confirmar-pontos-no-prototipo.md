# Medir a retomada do banco e confirmar pontos que as fontes não cobrem

Type: prototype
Status: ready-for-human
Blocked by: —
Skills: `prototype`; apoio: `run`; HITL (precisa de um cluster na conta AWS do dono e de iPhone/Android reais)
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #35
Origem: lacunas remanescentes de [Reconferir as lacunas das pesquisas de plataforma e de banco](15-reconferir-lacunas-das-pesquisas.md) (achados na branch `research/lacunas-plataforma-e-banco`)

## Question

O que só uma medição ou um teste real responde, porque a fonte oficial não diz?

## Checklist

- [x] DSQL medido (ver `## Answer`). [ ] Aurora: segundos da primeira conexão no DSQL após Idle/Inactive, e o auto-pause (0 ACU) do Aurora Serverless v2 em sa-east-1 (a doc não lista por região; retomada documentada de ~15 s, 30 s+ após 24 h pausado)
- [ ] Efeito real de desligar "Abrir como App Web" no iOS 26 sobre a perda de dados do PWA, e se o ITP de 7 dias atinge conteúdo local num WKWebView de Capacitor (o plano B da [Plataforma do cliente](08-plataforma-do-cliente.md))
- [ ] Resultado em `## Answer`; dizer se muda [Plataforma do cliente](08-plataforma-do-cliente.md) ou [Banco de dados e região](09-banco-de-dados-e-regiao.md)

## Answer

Resultado parcial, medido pelo dono em 2026-10-27 com `medir_retomada.py`, cluster DSQL em sa-east-1, da máquina dele (segundos de conexão e de `select 1`; a conexão inclui gerar o token IAM):

| Motor | Ocioso | Conexão (s) | `select 1` (s) |
|---|---|---|---|
| dsql | quente | 0,70 | 0,03 |
| dsql | 30 min | 0,70 | 0,02 |
| dsql | 24 h | 1,06 | 0,02 |

- **DSQL não tem retomada perceptível**: a primeira conexão depois de 24 h sem uso levou 1,06 s, contra 0,70 s com o banco quente. Fica bem abaixo do gatilho de 5 s, então o [ticket 09](09-banco-de-dados-e-regiao.md) **não é reaberto** e a escolha do DSQL se mantém. Não mudou nada em [Banco de dados e região](09-banco-de-dados-e-regiao.md).
- A rodada de 2 h não foi feita; não é necessária, dado que 30 min e 24 h ficaram iguais dentro de ~0,4 s.
- **Não medidos**: auto-pause do Aurora Serverless v2 (só serve de comparação; o DSQL foi o escolhido) e os testes de iOS 26 (`roteiro-ios.md`: "Abrir como App Web" e ITP de 7 dias). Como o [ticket 08](08-plataforma-do-cliente.md) escolheu PWA, o item de iOS segue pendente com o dono e pode mudar aquela decisão se o PWA perder dados.

## Comments

- Sessão na nuvem: as variáveis `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY` do ambiente são placeholders do proxy (o STS devolve `InvalidClientTokenId`), então nada foi medido. Ficaram preparados, em `../prototipos/17/`, o script `medir_retomada.py` (DSQL e Aurora Serverless v2, sa-east-1, imprime uma linha CSV por medição) e o `roteiro-ios.md` (iOS 26: "Abrir como App Web" e ITP de 7 dias). O dono roda ambos e preenche `## Answer`; o ticket continua `ready-for-human`.
- Segunda tentativa, com credenciais temporárias reais (conta 255235818791, role `AccountFullAccessRole`): o STS funcionou, mas uma service control policy da organização (`p-hfwxkmnx`) nega `dsql:CreateCluster`, `dsql:TagResource`, `dsql:ListClusters` e `rds:DescribeDBClusters` em sa-east-1. Nenhum recurso foi criado e as credenciais foram apagadas da sessão. Para medir, é preciso uma conta fora dessa SCP (ou a SCP liberar DSQL/RDS em sa-east-1) e credenciais com validade maior que a espera de 24 h do teste.
- Terceira tentativa, em us-east-2 (a região das credenciais): o DSQL foi criado e ficou ACTIVE, mas a conexão PostgreSQL (porta 5432) expirou após 120 s, porque a sessão na nuvem só sai pelo proxy HTTPS. O cluster foi apagado em seguida; nenhuma medição saiu. A medição precisa rodar de uma máquina do dono com acesso à porta 5432. us-east-2 não é a região do ticket (sa-east-1), e a SCP só liberou us-east-2.
- Decisão do dono: medir em us-east-2 é aceitável como aproximação do tempo de retomada, que depende pouco da região; a latência de rede do Brasil é outro número e fica no [ticket 09](09-banco-de-dados-e-regiao.md). Vale rodar também em sa-east-1 se a conta e o serviço permitirem, antes de uma eventual migração para lá.
- O [ticket 08](08-plataforma-do-cliente.md) escolheu PWA, sem app nativo: saíram deste ticket o build de release do Expo com conta Apple gratuita e o alcance do sideload de APK no Brasil, que só pesavam em Expo ou Capacitor fora da loja.
- 2026-10-25, no [ticket 09](09-banco-de-dados-e-regiao.md): a SCP da organização passou a liberar sa-east-1 (`dsql:ListClusters` respondeu `{"clusters": []}` com o usuário IAM `financial-cli`), e o app vai rodar em sa-east-1. A medição de retomada do DSQL pode rodar lá, da máquina do dono, que alcança a porta 5432. Se a primeira conexão depois do cluster parado passar de 5 s, o ticket 09 é reaberto para rever o DSQL.
