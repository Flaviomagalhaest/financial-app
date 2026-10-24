# Reconferir as lacunas das pesquisas de plataforma e de banco

Type: research
Status: ready-for-agent
Blocked by: —
Skills: `research` (AFK, em sub-agente); a parte da conta AWS é HITL (o dono confere no console da conta pagadora)
Modelo recomendado: Sonnet
Effort recomendado: medium
Trello: ari:cloud:trello::card/workspace/598b72bf7efc694a04666f1f/6add363148111e003c30056e
Origem: lacunas de [Limites do app web instalável no iPhone e no Android](02-limites-do-app-web-instalavel.md) e [Banco de dados na AWS para dois usuários e histórico longo](03-banco-de-dados-na-aws.md)

## Question

Que pontos das duas pesquisas ficaram sem fonte oficial e ainda pesam em [Plataforma do cliente](08-plataforma-do-cliente.md) e [Banco de dados e região](09-banco-de-dados-e-regiao.md)?

## Checklist

- [ ] Plataforma: efeito de desligar "Abrir como App Web" no iOS 26 sobre a isenção do ITP de 7 dias; se o ITP vale no WKWebView de um app Capacitor; build de release no Expo com conta Apple gratuita; alcance da verificação de desenvolvedores do Android sobre APK direto no Brasil (as páginas oficiais divergem)
- [ ] Banco: tempo de retomada do DSQL em segundos; PITR no DSQL; auto-pause do Aurora Serverless v2 em sa-east-1
- [ ] Conta AWS (HITL): prazo e origem dos US$ 120 de crédito, e se o compartilhamento de créditos está ligado na conta pagadora (a FAQ da AWS se contradiz sobre a validade)
- [ ] Achados num único Markdown, cada afirmação com a fonte, numa branch `research/lacunas-plataforma-e-banco` enviada e sem PR
- [ ] Ponteiro para a branch e resumo em `## Answer`; dizer se algo muda os tickets 08 ou 09
