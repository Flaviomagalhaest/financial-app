# Banco de dados e região

Type: grilling
Status: open
Blocked by: 03, 07
Skills: `grilling` e `domain-modeling` (HITL: precisa do dono)
Modelo recomendado: Opus
Effort recomendado: high
Origem: traçado do [mapa V1 que substitui o Mobills](../map.md)

## Question

Qual banco guarda os dados do app e em que região da AWS?

Decidir com os custos e limitações de [Banco de dados na AWS para dois usuários e histórico longo](03-banco-de-dados-na-aws.md) e com o volume real de [Exportar o Mobills e medir o histórico](07-exportar-o-mobills-e-medir-o-historico.md). Inclui: como o histórico longo é organizado para os dashboards de vários anos continuarem rápidos; retenção e backup; São Paulo ou Virgínia.

## Checklist

- [ ] Decisão registrada em `## Answer`
- [ ] ADR em `docs/adr/` (banco é escolha com lock-in)
