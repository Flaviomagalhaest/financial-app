# Projeção de saldo: confirmar as regras provisórias

Type: grilling
Status: ready-for-human
Blocked by: —
Skills: `grilling` para o dono decidir; depois `implement`, `tdd` se uma regra mudar; HITL (decisão de produto)
Modelo recomendado: Sonnet
Effort recomendado: low
Issue: #214
Origem: [ticket 58](58-aba-futuro-e-projecao-de-saldo.md) (a spec e o [ticket 11](11-dashboards-e-fechamento-do-mes.md) dizem as duas linhas, mas não estes casos; o 58 decidiu sozinho e deixou para o dono confirmar)

## As perguntas

A leitura é `GET /api/futuro` (`backend/app/projecao.py`), com os testes em `backend/tests/test_projecao.py`.

1. **Item de transferência fora da linha com o planejamento.** A linha desconta o que falta só dos itens de categoria de **despesa**. O item de transferência (guardar na reserva) fica de fora, porque move dinheiro entre duas contas e a soma delas não muda. O item de receita, se existir, também fica de fora. Alternativa: descontar o de transferência quando a conta de destino não for do casal (hoje não existe esse caso).
2. **Ajuste de fatura come o que falta do planejamento.** O ajuste já sai na fatura do mês. Como no "ainda dá para gastar", ele também diminui o que falta dos itens, para não sair duas vezes. Alternativa: descontar o que falta dos itens inteiro.
3. **Mês futuro sem planejamento não desconta nada.** Hoje só conta o planejamento que o casal criou para o mês. Alternativa: usar o modelo padrão nos meses que ainda não têm planejamento, para a linha não subir de repente depois do último mês planejado.
4. **O passado começa na abertura de cada conta.** No fim de cada mês que passou, entra na soma só a conta já aberta naquele dia (sem abertura, desde sempre). O mês em que nenhuma estava aberta fica sem ponto. Uma conta nova com saldo de abertura faz a linha subir no mês da abertura.
5. **Pagamento de fatura previsto não conta.** A fatura sai inteira no mês dela (história 136), e o que já foi pago dela (o pagamento realizado) já está no saldo de hoje. O pagamento previsto é ignorado, para não sair duas vezes.
6. **Doze meses para trás e doze adiante**, a partir do mês atual (`MESES_PARA_TRAS` e `MESES_A_FRENTE`). O protótipo tinha 11 para trás e 6 linhas na tabela.

## Checklist

- [ ] O dono responde cada pergunta e a resposta vai para `## Answer`
- [ ] Se uma regra mudar: teste de API em `backend/tests/test_projecao.py` e ajuste em `backend/app/projecao.py` (ou em `planejamento.a_lancar_nas_despesas`)
