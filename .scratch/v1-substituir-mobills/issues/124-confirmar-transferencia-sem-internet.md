# Confirmar transferência prevista sem internet

Type: task
Status: wontfix
Blocked by: —
Skills: `grilling` para o dono decidir se vale; depois `implement`, `tdd`; HITL na decisão
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #286
Origem: [ticket 80](80-transferencia-prevista-atrasada-e-confirmacao.md) (a confirmação da transferência prevista foi feita só com internet, como criar e editar transferência, [ADR 0011](../../../docs/adr/0011-conflitos-e-mudancas-offline.md); o lançamento confirma pela fila, [ticket 83](83-confirmar-previsto-sem-internet-pela-fila.md))

## O que construir

Hoje "Confirmar" e "Ajustar" da transferência nas contas da semana ficam desabilitados sem internet. O dono decide se a confirmação da transferência deve entrar na fila como a do lançamento, e o que isso pede (item `confirmar_transferencia`, o bloco tirando a confirmada, o 409 de ajuste diferente na tela de conflito).

## Checklist

- [x] O dono decide se vale (resposta em `## Answer`)
- [x] Se valer: confirmação da transferência pela fila, com testes de navegador sem internet (não vale: `wontfix`)

## Answer

O dono decidiu (grilling): **não vale**. Fecha como `wontfix`.

- Transferência prevista quase sempre se confirma com o app aberto e com sinal; esperar a internet voltar basta.
- O custo é alto: reabrir o [ADR 0011](../../../docs/adr/0011-sem-internet-so-lancamentos-e-conflito-decidido-a-mao.md) (o aparelho não guarda transferências), uma ação nova em `POST /api/lancamentos/lote`, um item novo na fila e um 409 novo na tela de conflito.
- Fica como está: "Confirmar" e "Ajustar" da transferência ficam desabilitados sem internet, com o aviso no bloco `ContasDaSemana`.
