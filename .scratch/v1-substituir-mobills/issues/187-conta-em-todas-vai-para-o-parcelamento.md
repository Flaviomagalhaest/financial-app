# A conta mudada em "todas" vai para o parcelamento

Type: task
Status: ready-for-agent
Blocked by: —
Skills: `implement`, `tdd`
Modelo recomendado: Opus
Effort recomendado: medium
Issue: #468
Origem: [ticket 144](144-valor-e-data-daqui-para-frente-no-parcelamento.md): decisões do dono Q2 a Q5 ([ADR 0023](../../../docs/adr/0023-alcance-da-mudanca-na-parcela.md))

## O que construir

Hoje, a conta mudada numa parcela com o alcance "todas" vai parcela a parcela, à mão em cada uma, e o parcelamento fica com a conta antiga. Com a conta nova do mesmo tipo da antiga (cartão para cartão, conta para conta; o caso é o cartão reemitido), o `conta_id` do parcelamento passa a ser o novo, e as parcelas mudam sem a marca de "alterada à mão" na conta. Assim a tela do parcelamento mostra o cartão certo, e a parcela que nasce quando ele cresce já vem com a conta nova.

## Checklist

- [ ] `PATCH /api/parcelas/{id}` com `alcance: todas` e conta nova do mesmo tipo: grava a conta no parcelamento e muda as parcelas sem marcá-las na conta; a fatura de cada uma segue o fechamento do cartão novo, como hoje
- [ ] As parcelas em fatura paga e as que tinham a conta mudada à mão ficam como estão e contam em `parcelas_mantidas`
- [ ] A troca de tipo (cartão para conta, ou o contrário) e a conta em "esta e as próximas" seguem como hoje: à mão em cada parcela, sem mudar o parcelamento
- [ ] Se o pedido cai no meio, o `mudanca_pendente` e a tarefa diária terminam a mudança sem marcar as parcelas (ticket 145); a conta do parcelamento só muda junto com a gravação do pedido, sem ficar meio a meio
- [ ] Teste: cartão reemitido em "todas", depois a correção do parcelamento aumenta o número de parcelas; a parcela nova nasce no cartão novo e as outras não aparecem como alteradas à mão
- [ ] Teste: troca de cartão para conta em "todas" mantém o comportamento de hoje
- [ ] Verificações do projeto e PR para `main`

## Notas

- Sem migration para as marcas de conta que o "todas" deixou antes: o banco não diz de que alcance veio a marca (decisão Q4).
- A correção do parcelamento continua sem o campo da conta (decisão Q5).
- O valor e a data "daqui para frente" ficam como estão, sem trecho no parcelamento (decisão Q1).
