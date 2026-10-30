# Tempo limite da rede: valor provisório para o dono confirmar

Type: grilling
Status: ready-for-human
Blocked by: —
Skills: `grilling` para o dono decidir; depois `implement` se o valor mudar; HITL (decisão de produto)
Modelo recomendado: Sonnet
Effort recomendado: low
Issue: #205
Origem: [ticket 82](82-rede-que-nao-responde-e-tempo-limite.md) (o tempo limite das chamadas da camada de dados entrou provisório)

## A pergunta

`tempoLimiteDaRedeSegundos` está em **10 s** (`config/valores-iniciais.json`). Mais curto cai em "sem internet" com 4G lento; mais longo deixa a tela esperando num Wi-Fi sem saída. O mesmo valor vale para leituras e para o lote da fila (também no service worker).

## Checklist

- [ ] O dono confirma ou troca o valor
