# Coluna do projeto para ticket do wayfinder em aberto

Status: ready-for-human
Blocked by: —
Skills: `writing-for-agents` (se a regra do `AGENTS.md` mudar)
Modelo recomendado: Sonnet
Effort recomendado: low
Issue: #40
Origem: traçado do mapa [V1 que substitui o Mobills](../../v1-substituir-mobills/map.md)

## Problema

Os tickets do wayfinder não levam papel de triage (a skill proíbe `ready-for-agent` e afins): o `Status:` deles é `open` até alguém reservar (`claimed`) e `resolved` ao fechar. O mapeamento de colunas do `AGENTS.md` assume `open` → TODO (padrão adotado na migração para o GitHub Projects) até o dono decidir.

No traçado, a sessão usou: `open` sem bloqueio vai para TODO; `open` com bloqueio vai para BLOCKED. A alternativa seria mandar os tickets HITL em aberto para WAITING, já que dependem do dono.

## Checklist

- [ ] Dono decide a coluna de `open` (TODO para todos, ou WAITING para os HITL)
- [ ] Regra registrada no `AGENTS.md`, na seção "GitHub Projects espelha o tracker"
- [ ] Issues da V1 movidas no projeto, se a decisão mudar a lista atual
