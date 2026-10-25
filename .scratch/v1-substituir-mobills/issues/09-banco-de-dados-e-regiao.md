# Banco de dados e região

Type: grilling
Status: open
Blocked by: 03, 07
Skills: `grilling` e `domain-modeling` (HITL: precisa do dono)
Modelo recomendado: Opus
Effort recomendado: high
Issue: #27
Origem: traçado do [mapa V1 que substitui o Mobills](../map.md)

## Question

Qual banco guarda os dados do app e em que região da AWS?

Decidir com os custos e limitações de [Banco de dados na AWS para dois usuários e histórico longo](03-banco-de-dados-na-aws.md) e com o volume real de [Exportar o Mobills e medir o histórico](07-exportar-o-mobills-e-medir-o-historico.md). Inclui: como o histórico longo é organizado para os dashboards de vários anos continuarem rápidos; retenção e backup; São Paulo ou Virgínia.

## Checklist

- [ ] Confirmar na lista oficial de regiões se o DSQL existe em sa-east-1 (se não existir, "migrar para sa-east-1" é trocar de banco, não só de região)
- [ ] Medir a latência real do Brasil para us-east-2 (RTT estimado em 120–150 ms contra 10–30 ms de sa-east-1) e decidir se consultas em lote e cache no cliente bastam
- [ ] Confirmar no console o prazo do plano gratuito (6 meses ou fim dos créditos) e se o DSQL tem franquia mensal própria
- [ ] Decisão registrada em `## Answer`
- [ ] ADR em `docs/adr/` (banco é escolha com lock-in)

## Comments

- Estratégia do dono: a conta gratuita está em us-east-2; ao fim dos créditos ou em cerca de 6 meses pode migrar para sa-east-1. Avaliação: o volume é pequeno (2 usuários), então dump/restore basta; os riscos são a latência do Brasil, o DSQL talvez não existir em sa-east-1, recursos presos à região (pool de usuários do Cognito não migra entre regiões; S3, segredos e IAM também) e, se o app tiver mais usuários um dia, a LGPD para dados fora do Brasil (uso exclusivamente pessoal fica fora da lei).
- Para a migração custar pouco: região e endpoint só em configuração (sem ARN nem hostname no código); migrations versionadas no repositório; `pg_dump` ou exportação periódica guardada fora da AWS; schema no subconjunto que o DSQL aceita (sair dele para o Aurora é fácil, o inverso não); evitar acoplar a autenticação ao Cognito, se possível.
- A SCP da organização negou DSQL e RDS em sa-east-1 e liberou us-east-2 (veja o [ticket 17](17-medir-retomada-e-confirmar-pontos-no-prototipo.md)); isso não prova que o DSQL não exista em sa-east-1.
