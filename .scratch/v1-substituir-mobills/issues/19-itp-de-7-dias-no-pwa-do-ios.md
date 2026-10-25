# Testar o ITP de 7 dias no PWA instalado do iOS

Type: prototype
Status: ready-for-human
Blocked by: —
Skills: `prototype`; apoio: `run`; HITL (precisa de iPhone real e de 8 dias sem abrir o app)
Modelo recomendado: Sonnet
Effort recomendado: low
Trello: ari:cloud:trello::card/workspace/598b72bf7efc694a04666f1f/6ade4d888eb7d598f1549f10
Origem: item dividido do [ticket 17](17-medir-retomada-e-confirmar-pontos-no-prototipo.md) para o 17 fechar em um dia; não bloqueia o [18](18-comparativo-de-banco-e-regiao.md) nem o [09](09-banco-de-dados-e-regiao.md)

## Question

O ITP de 7 dias do Safari apaga `localStorage`, IndexedDB e Cache API de um PWA instalado no iOS 26 que fica 8 dias sem ser aberto, e de uma aba comum do Safari?

## Checklist

- [ ] Seguir `prototipos/19/roteiro-itp.md` num iPhone real: aba do Safari e PWA instalado, 8 dias sem abrir
- [ ] Resultado em `## Answer`; dizer se o app precisa tratar perda de dados locais (nova sessão, fila offline) ou se basta o servidor como fonte da verdade, e se muda [Plataforma do cliente](08-plataforma-do-cliente.md)

## Comments

- Se o app guardar tudo no servidor e só pedir novo login, a perda local é aceitável e este ticket pode virar `wontfix`.
