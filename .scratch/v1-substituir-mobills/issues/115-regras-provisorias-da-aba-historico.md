# Conferir as regras provisórias da aba Histórico

Type: grilling
Status: resolved
Blocked by: 57
Skills: `grilling` para o dono decidir; depois `implement`, `tdd` se uma regra mudar; HITL (decisão de produto)
Modelo recomendado: Sonnet
Effort recomendado: low
Issue: #227
Origem: [ticket 57](57-aba-historico.md): a spec (história 134) não diz o que fazer nestes casos, e o 57 escolheu um comportamento provisório para cada um (em `backend/app/historico.py`, com teste em `backend/tests/test_aba_historico.py`)

## As perguntas

1. **Só o realizado.** Hoje a evolução soma só o realizado (o previsto não confirmado de um mês passado fica de fora), como o fechamento do mês, e o mês atual vai até hoje. Alternativa: somar também o previsto, como a comparação e o ranking da aba Mês.
2. **Mês atual e cartão.** A compra no cartão de hoje, que conta na fatura do mês que vem, só aparece na evolução quando esse mês chega; o ajuste de fatura do mês atual entra inteiro. Manter?
3. **Ano corrente e "mesmo mês" ainda não chegado.** O ano corrente aparece como "(até agora)", sem projetar o resto; no "mesmo mês", um mês que ainda não chegou neste ano aparece zerado, sem aviso.
4. **"12 contra os 12 anteriores"** foi lido como cada mês contra o mesmo mês um ano antes, e o total contra o total dos 12 anteriores. Era isso?
5. **Categorias arquivadas** aparecem na escolha da categoria (para ver a evolução desde 2019). Manter?

## Checklist

- [x] O dono responde cada pergunta e a resposta vai para `## Answer`
- [x] Se uma regra mudar: teste de API em `backend/tests/test_aba_historico.py`, ajuste em `backend/app/historico.py` e na tela; o README (seção Planejamento) acompanha

## Answer

1. Manter só o realizado.
2. Manter (cartão conta no mês da fatura; ajuste do mês atual entra inteiro).
3. Projetar o ano corrente: `por_ano` ganhou `previsto_centavos` (previsto de hoje até dezembro, sem ajuste de fatura); a tela mostra "(até agora; com o previsto até dezembro, R$ X)". Os 12 meses e o "mesmo mês" seguem só realizado (o mês futuro do "mesmo mês" continua zerado; fica como está).
4. Sim, cada mês contra o mesmo mês um ano antes, total contra total.
5. Manter as categorias arquivadas na escolha.
