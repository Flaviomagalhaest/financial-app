# Confirmar com outro valor a compra à vista com partes

Type: task
Status: resolved
Blocked by: —
Skills: `grilling` (HITL: o dono escolhe como as partes se acertam), depois `implement`, `tdd`; apoio: `run` para ver funcionando
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #368
Origem: [ticket 140](140-partes-na-recorrencia.md): a revisão viu que `confirmar` (`backend/app/lancamentos.py`) não mexe nas partes da compra à vista; o [ticket 139](139-partes-na-compra-parcelada.md) achou a mesma pendência (a parcela com partes confirmada com outro valor já se redivide na proporção; a compra à vista não)

## O que decidir

A compra à vista com partes que ainda é prevista (data futura) pode ser confirmada com outro valor (`POST /api/lancamentos/{id}/confirmar`, também pela fila). Hoje o valor muda e as partes ficam como estavam, sem somar o valor da compra, contra a ADR 0022. Na ocorrência da recorrência, o 140 divide as partes de novo na proporção, porque lá as partes são proporção. Na compra à vista, as partes são valores, e a correção de fatura do 151 põe a diferença na última parte.

## Checklist

- [x] O dono escolhe: a diferença vai na última parte (como a correção de fatura e a tela de lançar), divide na proporção (como a recorrência e a parcela) ou recusa o ajuste de valor (422) e manda editar as partes
- [x] `confirmar` acerta as partes da compra à vista; o aparelho mostra igual enquanto a confirmação não sobe (`enfileirarConfirmar` em `web/src/dados/fila.ts`)
- [x] Testes de API e de navegador; verificações do projeto e PR para `main`

## Decisão (dono)

Recusar o ajuste de valor (422, "a compra com partes não confirma com outro valor: edite as partes") e mandar editar as partes. Vale só para a compra à vista com partes; a parcela e a ocorrência seguem redividindo na proporção. Na tela "Contas da semana" o botão "Confirmar com ajuste" fica desligado com outro valor, e a fila não redivide mais as partes da compra à vista.
