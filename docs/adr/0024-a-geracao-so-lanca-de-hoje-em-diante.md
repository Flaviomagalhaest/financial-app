---
status: accepted
---

# A geração de recorrência e de boleto só lança de hoje em diante

Recorrência e boleto parcelado com início no passado não geram lançamento para o que veio antes do dia do lançamento: nem previsto atrasado, nem realizado. O calendário, a numeração e o total seguem contados desde o início, então as `vezes` e o valor do parcelamento não mudam. Isso altera a [ADR 0004](0004-previsto-e-situacao-do-lancamento.md) num ponto: o passado não vira previsto nem realizado sozinho; quem quiser o histórico lança à mão (ticket 87, `## Answer`; ticket 125).

- A ocorrência do dia do lançamento nasce realizada só na criação, e só se for de valor estimado ou automática. A de valor fixo que não é automática nasce prevista (ticket 129).
- Gerada depois (tarefa diária, mudança da regra), a estimada de hoje nasce prevista e pede confirmação.
- Recorrência ou boleto que terminam inteiros antes de hoje são recusados (422); registrar o histórico é lançar à mão.
- No boleto, as parcelas de antes são **anteriores** (`parcelas_anteriores`); "pulada" é só o que o casal excluiu.
- A correção do boleto (ticket 126) segue a regra: a prevista que a data nova leva para antes de hoje sai como anterior, sem realizar a automática; a atrasada que já estava antes de hoje muda de data e segue prevista; a realizada que muda de data para o passado pede a confirmação de sempre; o previsto atrasado de uma recorrência que vira automática segue esperando o casal.

## Considered Options

- **Lançar o passado como atrasado ou realizado**: enche a aba Hoje de contas que o casal nunca vai confirmar e mexe no saldo sem ninguém ter pago nada.
- **Aceitar o boleto inteiro no passado como registro sem parcelas**: não muda o caixa nem o planejamento; ficou a recusa.
- **Recusar mover a parcela realizada e tirar a atrasada como pulada na correção**: trava a correção de um erro de data e perde um compromisso que ainda existe.
