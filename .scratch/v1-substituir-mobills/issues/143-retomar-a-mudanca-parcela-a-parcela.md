# Retomar a mudança parcela a parcela que parou no meio

Type: task
Status: ready-for-agent
Blocked by: —
Skills: `implement`, `tdd`
Modelo recomendado: Opus
Effort recomendado: medium
Issue: #337
Origem: [ticket 136](136-alcance-da-mudanca-na-parcela.md): a parte da mudança com alcance que vai parcela a parcela (valor e data daqui para frente, conta, fatura) não fica registrada como pendente

## O que construir

O `PATCH /api/parcelas/{id}` muda, na transação da parcela mudada, o parcelamento e o primeiro lote das outras parcelas; as que não cabem vão em transações seguintes. A classificação fica pendente no parcelamento e a tarefa diária a termina se o pedido cair, mas a parte parcela a parcela não: num parcelamento longo (mais de um lote, perto de 80 parcelas), uma queda no meio deixa as últimas como estavam, e repetir o pedido é o único jeito de terminar.

## Checklist

- [ ] Guardar no parcelamento o que falta mudar parcela a parcela (campos, valores e a partir de qual parcela)
- [ ] A tarefa diária termina o que ficou, como faz com a correção (`completar_todos`)
- [ ] Teste de API com o pedido interrompido no meio
