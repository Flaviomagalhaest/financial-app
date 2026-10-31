# Confirmar transferência prevista sem internet

Type: task
Status: ready-for-human
Blocked by: —
Skills: `grilling` para o dono decidir se vale; depois `implement`, `tdd`; HITL na decisão
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #286
Origem: [ticket 80](80-transferencia-prevista-atrasada-e-confirmacao.md) (a confirmação da transferência prevista foi feita só com internet, como criar e editar transferência, [ADR 0011](../../../docs/adr/0011-conflitos-e-mudancas-offline.md); o lançamento confirma pela fila, [ticket 83](83-confirmar-previsto-sem-internet-pela-fila.md))

## O que construir

Hoje "Confirmar" e "Ajustar" da transferência nas contas da semana ficam desabilitados sem internet. O dono decide se a confirmação da transferência deve entrar na fila como a do lançamento, e o que isso pede (item `confirmar_transferencia`, o bloco tirando a confirmada, o 409 de ajuste diferente na tela de conflito).

## Checklist

- [ ] O dono decide se vale (resposta em `## Answer`)
- [ ] Se valer: confirmação da transferência pela fila, com testes de navegador sem internet
