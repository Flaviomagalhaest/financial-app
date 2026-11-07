# Atrasado da recorrência que a mudança levaria para dentro de uma fatura paga

Type: grilling
Status: claimed
Blocked by: —
Skills: `grilling` e `domain-modeling` (HITL: o dono decide entre pular e recusar); apoio: `implement`, `tdd`
Modelo recomendado: Opus
Effort recomendado: low
Issue: #428
Origem: revisão (Spec) do [ticket 172](172-recorrencia-no-cartao-respeita-a-fatura-paga.md)

## A pergunta

O [ticket 126](126-parcelamento-e-recorrencia-na-fatura-paga.md) decidiu que, na alteração da recorrência no cartão, o atrasado **de** fatura paga fica como está. Não decidiu o atrasado de uma fatura fechada sem pagamento que a data nova levaria **para dentro** de uma fatura paga (ex.: abril paga, maio fechada sem pagamento, e a mudança de calendário põe a de 20/05 em 22/04).

O 172 escolheu, provisoriamente, **pular** esse atrasado: ele fica inteiro como está (data, valor, descrição, categorias), como o de fatura paga, e o resto é refeito (`_reajustar_um_lote` em `backend/app/recorrencias.py`; teste `test_alterar_a_recorrencia_nao_leva_o_atrasado_para_dentro_da_fatura_paga`). Está no `GLOSSARY.md` (**Daqui para frente**) e na ADR 0021.

A alternativa é a da correção do parcelamento: **recusar o pedido inteiro antes de gravar a regra** (422 na rota, `recusada` na fila), simulando os lotes.

## Checklist

- [ ] Decidir com o dono: pular (como hoje) ou recusar com 422
- [ ] Se for recusar, implementar com teste em `backend/tests/test_fatura_paga.py` e atualizar `GLOSSARY.md` e ADR 0021
