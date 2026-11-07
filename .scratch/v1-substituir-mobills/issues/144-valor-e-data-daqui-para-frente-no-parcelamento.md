# Valor e data "daqui para frente" e conta no parcelamento

Type: grilling
Status: resolved
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

- [x] O dono decide: fica como está, ou o parcelamento guarda o trecho e a conta
- [x] Se mudar: ticket de implementação e revisão da ADR 0023

## Notas

- Hoje a correção do parcelamento e a tarefa diária preservam essas parcelas porque estão marcadas à mão; sem a marca, o trecho precisa estar no parcelamento, senão a tarefa diária desfaz.

## Answer

Decisões do dono (grilling de 2026-11-07), gravadas na [ADR 0023](../../../docs/adr/0023-alcance-da-mudanca-na-parcela.md) e no `GLOSSARY.md` (**Alcance da mudança na parcela**):

- **Q1, valor e data daqui para frente**: ficam como estão. O parcelamento não guarda trecho, e as parcelas a partir da N seguem marcadas à mão. O caso que o trecho resolveria (mudar o valor daqui para frente e depois aumentar o número de parcelas) é raro, e o trecho mexeria em todas as correções e na geração.
- **Q2, conta em "todas"**: a conta nova vai para o parcelamento, e as parcelas mudam sem a marca.
- **Q3, troca de tipo**: só vale com a conta nova do mesmo tipo (cartão para cartão, conta para conta). A troca de tipo segue à mão em cada parcela, sem mudar o parcelamento, para não trocar a regra das datas.
- **Q4, marcas antigas**: ficam, sem migration; o banco não diz de que alcance veio a marca.
- **Q5, correção do parcelamento**: continua sem o campo da conta; o "todas" numa parcela é o caminho.

Implementação: [187](187-conta-em-todas-vai-para-o-parcelamento.md).
