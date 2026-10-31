# O pagamento quita a fatura e passa a sobra para a seguinte

Type: task
Status: ready-for-agent
Blocked by: —
Skills: `implement`, `tdd`; apoio: `run` (ver a Hoje e a aba Cartões com uma fatura paga em parte)
Modelo recomendado: Opus
Effort recomendado: medium
Issue: #298
Origem: [ticket 89](89-conferir-as-regras-de-fatura.md) (31/10): o dono trocou as regras provisórias do ticket 37/38 sobre pagamento, situação "paga" e pagamento a mais. A decisão está na [ADR 0021](../../../docs/adr/0021-o-pagamento-quita-a-fatura.md) e no glossário (**Fatura paga**, **Correção de fatura**, **Saldo anterior**).

## O que muda

Hoje (`backend/app/cartoes.py`, `faturas_do_titular`) a fatura só fica "paga" quando o pago cobre o devido (saldo anterior mais compras), e a sobra de uma fatura fechada passa como saldo anterior para a seguinte mesmo sem pagamento. Pagar o total de maio com o saldo de abril dentro deixa abril "fechada" e devendo, e `faturas_que_vencem_ate` a mostra vencida na Hoje para sempre.

Exemplo da regra nova: abril fecha com R$ 1.000. Em 02/05 o casal paga R$ 600 apontando para abril: abril fica **paga** e maio nasce com R$ 400 de saldo anterior. Sem nenhum pagamento, abril fica **fechada**, devendo R$ 1.000 e vencida na Hoje, e maio não recebe saldo anterior.

## Checklist

- [ ] Situação **paga**: fatura fechada com pelo menos um pagamento realizado (o previsto não conta), qualquer que seja o valor. Fatura fechada de total zero sem pagamento fica **fechada**; a importada do Mobills continua paga
- [ ] **Saldo anterior** da seguinte = total menos o pago da fatura paga anterior; fatura fechada sem pagamento não passa nada. Continua pulando meses sem fatura. O pagamento lançado depois de a seguinte fechar também passa a sobra para ela
- [ ] O total da fatura seguinte (saldo anterior mais compras) bate com o "a pagar" dela; abril paga em parte some da Hoje
- [ ] **Fatura paga não recebe mais eventos**: recusar (422, com mensagem para corrigir a fatura) pagamento novo, compra (inclusive a esquecida com data antiga e as parcelas), troca de fatura, estorno e acerto de datas que puxaria compras para uma fatura paga. Decidir com teste o que acontece com a parcela futura de um parcelamento que cairia numa fatura paga (provavelmente nunca, porque a paga já fechou)
- [ ] **Pagamento acima do devido é recusado** (422 "o pagamento passa do valor da fatura"); some o caso de `pago_centavos` maior que o total
- [ ] **Correção de fatura**: uma operação que muda de uma vez pagamentos, compras, datas e ajuste de uma fatura paga, valida as regras acima no resultado (inclusive o pago não passar do total, por exemplo depois de um estorno) e refaz o saldo anterior da seguinte. Sem estado "reaberta" guardado
- [ ] Web: aba Cartões e Hoje mostram a situação e o saldo anterior novos; a tela de correção da fatura paga; as mensagens de recusa aparecem na tela de lançar
- [ ] Conferir o efeito na importação do Mobills, no backup/exportação (`backend/app/backup.py`, `exportacao.py`) e na projeção de saldo
- [ ] Testes da regra nova no lugar dos do comportamento antigo (ticket 37/38)
