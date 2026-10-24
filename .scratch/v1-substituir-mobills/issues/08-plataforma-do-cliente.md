# Plataforma do cliente

Type: grilling
Status: open
Blocked by: 02
Skills: `grilling` e `domain-modeling` (HITL: precisa do dono)
Modelo recomendado: Opus
Effort recomendado: high
Origem: traçado do [mapa V1 que substitui o Mobills](../map.md)

## Question

Com o que o app chega à web, ao Android e ao iPhone?

- app web instalável (PWA);
- Expo (React Native com saída web), que o dono já usa em outro repositório;
- app web empacotado com Capacitor.

Pesar: loja de apps não é requisito; funcionar sem internet e ter atalho na tela inicial são; gráficos e dashboards; custo (Apple Developer); manutenção por uma pessoa; uma só base de código para os três. Usar o achado de [Limites do app web instalável no iPhone e no Android](02-limites-do-app-web-instalavel.md).

## Checklist

- [ ] Decisão registrada em `## Answer`
- [ ] ADR em `docs/adr/` se a decisão for difícil de reverter, surpreendente e fruto de um trade-off real
