# Lista do Trello para ticket do wayfinder em aberto

Status: done
Blocked by: —
Skills: `writing-for-agents` (se a regra do `AGENTS.md` mudar)
Modelo recomendado: Sonnet
Effort recomendado: low
Origem: traçado do mapa [V1 que substitui o Mobills](../../v1-substituir-mobills/map.md)

## Problema

Os tickets do wayfinder não levam papel de triage (a skill proíbe `ready-for-agent` e afins): o `Status:` deles é `open` até alguém reservar (`claimed`) e `resolved` ao fechar. O mapeamento de listas do `AGENTS.md` não cobre `open`.

No traçado, a sessão usou: `open` sem bloqueio vai para TODO; `open` com bloqueio vai para BLOCKED. A alternativa seria mandar os tickets HITL em aberto para WAITING, já que dependem do dono.

## Checklist

- [x] Dono decide a lista de `open` (TODO para todos, ou WAITING para os HITL)
- [x] Regra registrada no `AGENTS.md`, na seção "Trello espelha o tracker"
- [x] Cards da V1 movidos, se a decisão mudar a lista atual

## Answer

O dono decidiu: todo ticket `open` do wayfinder vai para TODO, inclusive os que esperam o dono. Os que têm `Blocked by` aberto vão para BLOCKED. Regra registrada em `AGENTS.md`, na seção "Trello espelha o tracker". Os cards da V1 já estavam nessas listas, então nenhum foi movido.
