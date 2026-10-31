# Parcelamento e recorrência que mexem numa fatura paga

Type: grilling
Status: ready-for-human
Blocked by: —
Skills: `grilling` e `domain-modeling` (HITL: o dono decide o que acontece com as parcelas e os previstos numa fatura paga); apoio: `implement`, `tdd`
Modelo recomendado: Opus
Effort recomendado: medium
Issue: #305
Origem: [ticket 125](125-o-pagamento-quita-a-fatura.md) (31/10). A revisão do 125 achou caminhos que ainda mudam uma fatura paga sem passar pela proteção (`cartoes.protegida`), que vale para lançamentos, fila, transferências, datas e ajuste da fatura, criação, antecipação e quitação de parcelamento ([ADR 0021](../../../docs/adr/0021-o-pagamento-quita-a-fatura.md)).

## A pergunta

Esses caminhos gravam em várias transações (lotes, pelo limite de linhas do DSQL), então recusar no meio deixaria a regra pela metade. O que fazer com a parcela ou o previsto que está, ou cairia, numa fatura paga?

- **Excluir o parcelamento** (`excluir_parcelamento`): exclui todas as parcelas, inclusive as realizadas de uma fatura paga.
- **Corrigir o parcelamento** (`alterar_parcelamento`, com `confirmar_realizadas`): muda valor e data de parcelas realizadas numa fatura paga.
- **Recorrência no cartão** (criar com início no passado, alterar, excluir; também pela fila): gera ou refaz previstos em faturas passadas, e o previsto conta nas compras da fatura.

Opções a discutir: recusar o pedido inteiro antes do primeiro lote (conferindo os meses, como a criação do parcelamento já faz); deixar intocadas as parcelas e previstos de fatura paga (como a correção já deixa as alteradas à mão); ou mandar o casal para a correção de fatura.

## Checklist

- [ ] Decidir, com o dono, a regra de cada caminho acima
- [ ] Implementar com teste na API (`backend/tests/test_fatura_paga.py`)
- [ ] Registrar a decisão na ADR 0021 ou numa nova, se mudar o que ela diz
