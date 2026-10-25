# Medir a retomada do banco e confirmar pontos que as fontes não cobrem

Type: prototype
Status: ready-for-human
Blocked by: —
Skills: `prototype`; apoio: `run`; HITL (precisa de um cluster na conta AWS do dono e de iPhone/Android reais)
Modelo recomendado: Sonnet
Effort recomendado: medium
Trello: ari:cloud:trello::card/workspace/598b72bf7efc694a04666f1f/6add3e0067e047c256a82146
Origem: lacunas remanescentes de [Reconferir as lacunas das pesquisas de plataforma e de banco](15-reconferir-lacunas-das-pesquisas.md) (achados na branch `research/lacunas-plataforma-e-banco`)

## Question

O que só uma medição ou um teste real responde, porque a fonte oficial não diz?

## Checklist

- [ ] Pré-requisito: poder criar um cluster DSQL em sa-east-1, o que a SCP da organização nega hoje (administrador libera DSQL na região, ou o dono usa uma conta fora dela; decisão no item de SCP do [ticket 09](09-banco-de-dados-e-regiao.md)). Sem isso o item seguinte não roda
- [ ] Segundos da primeira conexão no DSQL (`MEDIR_REGIAO=sa-east-1 python3 prototipos/17/medir_retomada.py dsql <endpoint>`) em **sa-east-1**: linha de base com o banco quente, depois de 2 h e depois de uma noite sem conexões. Cada execução também grava `rtt_tcp_ms`, a latência da sua máquina até a região; subtraída de `segundos_conexao`, isola a retomada
- [ ] Repetir a mesma série em us-east-2 (a região hoje liberada), para comparar as duas regiões lado a lado no [ticket 18](18-comparativo-de-banco-e-regiao.md)
- [ ] Latência de rede do Brasil até as duas regiões: o `rtt_tcp_ms` das execuções acima (rode de uma rede no Brasil, a mesma que você usa no dia a dia). Entrega o item de latência do [ticket 09](09-banco-de-dados-e-regiao.md)
- [ ] Efeito de desligar "Abrir como App Web" no iOS 26 sobre os dados do PWA, seguindo `prototipos/17/roteiro-ios.md`
- [ ] Números no formato `motor,regiao,ocioso,segundos_conexao,segundos_select,rtt_tcp_ms` em `## Answer`, para o [18](18-comparativo-de-banco-e-regiao.md) consumir; dizer se muda [Plataforma do cliente](08-plataforma-do-cliente.md) ou [Banco de dados e região](09-banco-de-dados-e-regiao.md)

A medição em sa-east-1 é obrigatória (decidido com o dono); us-east-2 deixa de ser só aproximação e vira a região de comparação.

Fora do escopo (decidido com o dono): o auto-pause do Aurora Serverless v2 (custa mais e retoma em ~15 s segundo a doc; só volta se o DSQL cair), o plano B Capacitor/WKWebView (o [ticket 08](08-plataforma-do-cliente.md) escolheu PWA) e a espera de 24 h. O ITP de 7 dias foi para o [ticket 19](19-itp-de-7-dias-no-pwa-do-ios.md), que não bloqueia este.

## Comments

- Sessão na nuvem: as variáveis `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY` do ambiente são placeholders do proxy (o STS devolve `InvalidClientTokenId`), então nada foi medido. Ficaram preparados, em `../prototipos/17/`, o script `medir_retomada.py` (DSQL e Aurora Serverless v2, sa-east-1, imprime uma linha CSV por medição) e o `roteiro-ios.md` (iOS 26: "Abrir como App Web" e ITP de 7 dias). O dono roda ambos e preenche `## Answer`; o ticket continua `ready-for-human`.
- Segunda tentativa, com credenciais temporárias reais (conta 255235818791, role `AccountFullAccessRole`): o STS funcionou, mas uma service control policy da organização (`p-hfwxkmnx`) nega `dsql:CreateCluster`, `dsql:TagResource`, `dsql:ListClusters` e `rds:DescribeDBClusters` em sa-east-1. Nenhum recurso foi criado e as credenciais foram apagadas da sessão. Para medir, é preciso uma conta fora dessa SCP (ou a SCP liberar DSQL/RDS em sa-east-1) e credenciais com validade maior que a espera de 24 h do teste.
- Terceira tentativa, em us-east-2 (a região das credenciais): o DSQL foi criado e ficou ACTIVE, mas a conexão PostgreSQL (porta 5432) expirou após 120 s, porque a sessão na nuvem só sai pelo proxy HTTPS. O cluster foi apagado em seguida; nenhuma medição saiu. A medição precisa rodar de uma máquina do dono com acesso à porta 5432. us-east-2 não é a região do ticket (sa-east-1), e a SCP só liberou us-east-2.
- (Substituída pela decisão mais abaixo.) Decisão do dono: medir em us-east-2 é aceitável como aproximação do tempo de retomada, que depende pouco da região; a latência de rede do Brasil é outro número e fica no [ticket 09](09-banco-de-dados-e-regiao.md). Vale rodar também em sa-east-1 se a conta e o serviço permitirem, antes de uma eventual migração para lá.
- Escopo reduzido a pedido do dono: só DSQL (linha de base, 2 h e uma noite) e o teste de "Abrir como App Web"; o ITP de 7 dias (8+ dias de espera) virou o [ticket 19](19-itp-de-7-dias-no-pwa-do-ios.md), para este fechar em um dia e desbloquear o [18](18-comparativo-de-banco-e-regiao.md).
- Atualizado após o [ticket 09](09-banco-de-dados-e-regiao.md) ganhar as pendências de SCP, de custo por região e de latência: o script passou a gravar a latência TCP (`rtt_tcp_ms`), de modo que as mesmas execuções do DSQL entregam a retomada e a latência Brasil–us-east-2. A pesquisa do [ticket 03](03-banco-de-dados-na-aws.md) diz que o DSQL existe em sa-east-1; o que impede a medição lá é a SCP.
- Decisão do dono: a medição em sa-east-1 passa a ser obrigatória. Enquanto a SCP bloquear o DSQL lá, o ticket não fecha; o pré-requisito (liberação pelo administrador ou conta fora da organização) é trabalho do dono e está no [ticket 09](09-banco-de-dados-e-regiao.md).
- O [ticket 08](08-plataforma-do-cliente.md) escolheu PWA, sem app nativo: saíram deste ticket o build de release do Expo com conta Apple gratuita e o alcance do sideload de APK no Brasil, que só pesavam em Expo ou Capacitor fora da loja.
