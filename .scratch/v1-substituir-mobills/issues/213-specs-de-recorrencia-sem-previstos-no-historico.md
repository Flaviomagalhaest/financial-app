# Specs de recorrência não dependem dos previstos no Histórico

Type: task
Status: ready-for-agent
Blocked by: —
Skills: `implement`, `tdd`, `run`
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #559
Origem: [ticket 207](207-historico-abre-com-previstos-distantes.md): o dono decidiu tirar os previstos futuros do Histórico, e 12 specs chegam à recorrência e conferem os previstos por ele.

## Problema

`web/e2e/recorrencia-mudar.spec.ts` (8 specs) e `web/e2e/partes-na-recorrencia.spec.ts` (4) abrem a regra pelo ⋯ de uma linha de previsto no Histórico e contam os previstos ali. Quando o 207 filtrar o futuro, eles quebram. Dá para reescrevê-los antes, sem mudar o comportamento do app.

## Checklist

- [ ] Abrir a regra por Contas e categorias (`RecorrenciasAtivas`, link `#/recorrencia/<id>`) em vez do ⋯ da linha
- [ ] Conferir os previstos pela API (`/api/lancamentos`, como `previstosNoServidor`) ou pela Busca, não pela lista do Histórico
- [ ] Os 12 specs verdes contra o Histórico de hoje (antes do 207)
- [ ] PR para `main`
