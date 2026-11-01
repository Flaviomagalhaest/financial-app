# Valor e data "daqui para frente" e conta no parcelamento

Type: grilling
Status: ready-for-human
Blocked by: —
Skills: `grilling`, `domain-modeling` (HITL: decisão do dono); depois `implement`, `tdd`
Modelo recomendado: Opus
Effort recomendado: medium
Issue: #336
Origem: [ticket 136](136-alcance-da-mudanca-na-parcela.md): o parcelamento guarda um valor total e uma data, não um trecho ([ADR 0023](../../../docs/adr/0023-alcance-da-mudanca-na-parcela.md))

## O que decidir

No ticket 136, "esta e as próximas" no valor ou na data, e a conta em qualquer alcance, vão parcela a parcela como mudança à mão em cada uma. Funciona, mas:

- as parcelas mudadas aparecem como "alterada à mão", embora a pessoa tenha mudado "esta e as próximas";
- a parcela que nasce quando o parcelamento cresce vem com o valor, a data e a conta antigos do parcelamento;
- a conta mudada em "todas" (o cartão reemitido) não muda a do parcelamento.

O dono decide se fica assim ou se o parcelamento passa a guardar um trecho (valor e data a partir da parcela N) e a conta nova.

## Checklist

- [ ] O dono decide: fica como está, ou o parcelamento guarda o trecho e a conta
- [ ] Se mudar: ticket de implementação e revisão da ADR 0023

## Notas

- Hoje a correção do parcelamento e a tarefa diária preservam essas parcelas porque estão marcadas à mão; sem a marca, o trecho precisa estar no parcelamento, senão a tarefa diária desfaz.
