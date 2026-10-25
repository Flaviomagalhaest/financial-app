# Como o app roda na AWS

Type: grilling
Status: open
Blocked by: 08, 09
Skills: `grilling` e `domain-modeling` (HITL: precisa do dono); apoio: `research` se surgir fato a confirmar
Modelo recomendado: Opus
Effort recomendado: high
Issue: #30
Origem: traçado do [mapa V1 que substitui o Mobills](../map.md)

## Question

Qual arquitetura na AWS cumpre o custo-alvo do mapa?

Cobrir: login (como os dois entram e continuam logados); API em Python (Lambda com API Gateway ou URL de função); hospedagem do app; contrato entre o app e a API (o app não é em Python); infraestrutura como código (CDK, SAM ou Terraform); ambientes (só produção ou também desenvolvimento); backup e restauração; alerta de orçamento; configuração da conta filha da organização.

## Checklist

- [ ] Decisão registrada em `## Answer`
- [ ] ADR em `docs/adr/` para as escolhas com lock-in
