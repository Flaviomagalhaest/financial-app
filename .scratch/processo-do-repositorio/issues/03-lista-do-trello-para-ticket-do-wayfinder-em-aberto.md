# Lista do Trello para ticket do wayfinder em aberto

Status: ready-for-human
Blocked by: —
Skills: `writing-for-agents` (se a regra do `AGENTS.md` mudar)
Modelo recomendado: Sonnet
Effort recomendado: low
Trello: ari:cloud:trello::card/workspace/598b72bf7efc694a04666f1f/6add2ecafe9d913e232d5cb4
Origem: traçado do mapa [V1 que substitui o Mobills](../../v1-substituir-mobills/map.md)

## Problema

Os tickets do wayfinder não levam papel de triage (a skill proíbe `ready-for-agent` e afins): o `Status:` deles é `open` até alguém reservar (`claimed`) e `resolved` ao fechar. O mapeamento de listas do `AGENTS.md` não cobre `open`.

No traçado, a sessão usou: `open` sem bloqueio vai para TODO; `open` com bloqueio vai para BLOCKED. A alternativa seria mandar os tickets HITL em aberto para WAITING, já que dependem do dono.

## Checklist

- [ ] Dono decide a lista de `open` (TODO para todos, ou WAITING para os HITL)
- [ ] Regra registrada no `AGENTS.md`, na seção "Trello espelha o tracker"
- [ ] Cards da V1 movidos, se a decisão mudar a lista atual
