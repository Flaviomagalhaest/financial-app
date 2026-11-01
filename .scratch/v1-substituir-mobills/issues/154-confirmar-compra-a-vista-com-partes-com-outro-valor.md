# Confirmar a compra à vista com partes com outro valor

Type: task
Status: ready-for-human
Blocked by: —
Skills: `grilling` (HITL: decisão do dono); depois `implement`, `tdd`
Modelo recomendado: Sonnet
Effort recomendado: low
Issue: #364
Origem: [ticket 139](139-partes-na-compra-parcelada.md): a parcela com partes confirmada com outro valor se redivide na proporção; a compra à vista prevista com partes (ticket 137) não

## O que decidir

Confirmar uma compra à vista prevista com partes com um ajuste de valor (`POST /api/lancamentos/{id}/confirmar` com `valor_centavos`) grava o valor novo e deixa as partes como estavam, que deixam de somar o valor da compra (ADR 0022). A parcela já se divide de novo na proporção (ticket 139). Para a compra à vista, o dono escolhe:

- dividir de novo as partes na proporção, como a parcela; ou
- recusar o ajuste de valor (422) e mandar editar as partes; ou
- a diferença na última parte, como a tela de lançar faz com "o que falta da compra".

## Checklist

- [ ] Dono decide a regra
- [ ] Implementar com teste de API (e de navegador, se a tela de "Ajustar" mudar); verificações do projeto e PR para `main`
