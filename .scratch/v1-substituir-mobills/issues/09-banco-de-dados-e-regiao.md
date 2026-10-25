# Banco de dados e região

Type: grilling
Status: open
Blocked by: 03, 07, 18
Skills: `grilling` e `domain-modeling` (HITL: precisa do dono)
Modelo recomendado: Opus
Effort recomendado: high
Trello: ari:cloud:trello::card/workspace/598b72bf7efc694a04666f1f/6add2e711921473942463622
Origem: traçado do [mapa V1 que substitui o Mobills](../map.md)

## Question

Qual banco guarda os dados do app e em que região da AWS?

Os números lado a lado vêm do [Comparativo lado a lado de banco e região](18-comparativo-de-banco-e-regiao.md). Decidir com os custos e limitações de [Banco de dados na AWS para dois usuários e histórico longo](03-banco-de-dados-na-aws.md) e com o volume real de [Exportar o Mobills e medir o histórico](07-exportar-o-mobills-e-medir-o-historico.md). Inclui: como o histórico longo é organizado para os dashboards de vários anos continuarem rápidos; retenção e backup; São Paulo ou Virgínia.

## Checklist

- [ ] Reconfirmar na lista oficial de regiões que o DSQL existe em sa-east-1 (a pesquisa do [ticket 03](03-banco-de-dados-na-aws.md) diz que sim, `dsql.sa-east-1.api.aws`; a SCP da organização é que o bloqueia lá)
- [ ] Latência real do Brasil para us-east-2 (RTT estimado em 120–150 ms contra 10–30 ms de sa-east-1): o número vem do [ticket 17](17-medir-retomada-e-confirmar-pontos-no-prototipo.md) (`rtt_tcp_ms`); aqui se decide se consultas em lote e cache no cliente bastam
- [ ] Confirmar no console o prazo do plano gratuito (6 meses ou fim dos créditos) e se o DSQL tem franquia mensal própria
- [ ] Conta fora de SCP: descobrir se a conta atual (255235818791) é gerenciada por outra organização (AWS Organizations, SCP `p-hfwxkmnx` nega DSQL e RDS em sa-east-1); se for, decidir entre pedir a liberação ao administrador ou usar uma conta própria independente. Atualizar o plano gratuito não remove SCP. A liberação (ou a conta própria) é pré-requisito do [ticket 17](17-medir-retomada-e-confirmar-pontos-no-prototipo.md), que passou a exigir a medição em sa-east-1. Antes de atualizar, conferir em Billing > Credits o saldo e a validade dos créditos (de memória, créditos não usados continuam valendo após passar ao plano pago)
- [ ] Comparar o custo de us-east-2 e sa-east-1 para o banco escolhido (preços de São Paulo costumam ser bem mais altos) e quanto isso encurta os créditos
- [ ] Decisão registrada em `## Answer`
- [ ] ADR em `docs/adr/` (banco é escolha com lock-in)

## Comments

- Estratégia do dono: a conta gratuita está em us-east-2; ao fim dos créditos ou em cerca de 6 meses pode migrar para sa-east-1. Avaliação: o volume é pequeno (2 usuários), então dump/restore basta; os riscos são a latência do Brasil, o DSQL talvez não existir em sa-east-1, recursos presos à região (pool de usuários do Cognito não migra entre regiões; S3, segredos e IAM também) e, se o app tiver mais usuários um dia, a LGPD para dados fora do Brasil (uso exclusivamente pessoal fica fora da lei).
- Para a migração custar pouco: região e endpoint só em configuração (sem ARN nem hostname no código); migrations versionadas no repositório; `pg_dump` ou exportação periódica guardada fora da AWS; schema no subconjunto que o DSQL aceita (sair dele para o Aurora é fácil, o inverso não); evitar acoplar a autenticação ao Cognito, se possível.
- A SCP da organização negou DSQL e RDS em sa-east-1 e liberou us-east-2 (veja o [ticket 17](17-medir-retomada-e-confirmar-pontos-no-prototipo.md)); isso não prova que o DSQL não exista em sa-east-1.
