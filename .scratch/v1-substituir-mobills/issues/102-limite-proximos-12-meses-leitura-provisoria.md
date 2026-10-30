# Limite do cartão: o que a lista dos próximos 12 meses mostra

Type: grilling
Status: ready-for-human
Blocked by: —
Skills: `grilling` para o dono decidir; depois `implement`, `tdd` se a leitura mudar; HITL (decisão de produto)
Modelo recomendado: Sonnet
Effort recomendado: low
Issue: #199
Origem: [ticket 56](56-limite-comprometido-do-cartao.md) (revisão: o [ticket 23](23-limite-comprometido-do-cartao.md) diz "a fatura que vence e as parcelas que terminam" e a leitura do 56 é provisória)

## As perguntas

1. **O que "libera" em cada mês.** Hoje (`GET /api/cartoes/{id}/limite`, `backend/app/limite.py`) cada parte do comprometido cai no mês do **vencimento** da fatura em que está: a fatura aberta ou a última fechada (com o saldo anterior) e as parcelas futuras das faturas que vencem no mês. O vencimento que já passou cai no mês de hoje; fatura sem vencimento, no mês dela. Alternativa: mostrar por parcelamento o mês em que a última parcela termina.
2. **Recorrência prevista dentro de fatura já fechada** entra no `a_pagar` dela e, portanto, no comprometido (a fatura soma previstos e realizados). Só acontece se um previsto cair numa fatura fechada; o dono confirma se isso deve sair da conta.
3. **Parcela prevista em fatura fechada** conta na fatura fechada e não aparece em "parcelamentos em andamento", que olha só as faturas não fechadas (só a importada sem datas).

## Checklist

- [ ] O dono responde cada pergunta e a resposta vai para `## Answer`
- [ ] Se uma leitura mudar: teste de API em `backend/tests/test_limite_do_cartao.py` e ajuste em `backend/app/limite.py` e na aba Cartões
