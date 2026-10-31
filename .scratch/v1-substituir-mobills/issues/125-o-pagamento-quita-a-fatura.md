# O pagamento quita a fatura e passa a sobra para a seguinte

Type: task
Status: resolved
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

- [x] Situação **paga**: fatura fechada com pelo menos um pagamento realizado (o previsto não conta), qualquer que seja o valor. Fatura fechada de total zero sem pagamento fica **fechada**; a importada do Mobills continua paga
- [x] **Saldo anterior** da seguinte = total menos o pago da fatura paga anterior; fatura fechada sem pagamento não passa nada. Continua pulando meses sem fatura. O pagamento lançado depois de a seguinte fechar também passa a sobra para ela
- [x] O total da fatura seguinte (saldo anterior mais compras) bate com o "a pagar" dela; abril paga em parte some da Hoje
- [x] **Fatura paga não recebe mais eventos**: recusar (422, com mensagem para corrigir a fatura) pagamento novo, compra (inclusive a esquecida com data antiga e as parcelas), troca de fatura, estorno e acerto de datas que puxaria compras para uma fatura paga. Decidir com teste o que acontece com a parcela futura de um parcelamento que cairia numa fatura paga (provavelmente nunca, porque a paga já fechou)
- [x] **Pagamento acima do devido é recusado** (422 "o pagamento passa do valor da fatura"); some o caso de `pago_centavos` maior que o total
- [x] **Correção de fatura**: uma operação que muda de uma vez pagamentos, compras, datas e ajuste de uma fatura paga, valida as regras acima no resultado (inclusive o pago não passar do total, por exemplo depois de um estorno) e refaz o saldo anterior da seguinte. Sem estado "reaberta" guardado
- [x] Web: aba Cartões e Hoje mostram a situação e o saldo anterior novos; a tela de correção da fatura paga; as mensagens de recusa aparecem na tela de lançar
- [x] Conferir o efeito na importação do Mobills, no backup/exportação (`backend/app/backup.py`, `exportacao.py`) e na projeção de saldo
- [x] Testes da regra nova no lugar dos do comportamento antigo (ticket 37/38)

## Answer

Feito em 31/10. A regra mora em `backend/app/cartoes.py`: `faturas_do_titular` calcula situação e saldo anterior, e `protegida(trabalho)` envolve a transação de cada gravação, compara as faturas antes e depois e recusa (422) a mudança numa fatura paga por pagamento ("a fatura de MM/AAAA do X está paga: para mudá-la, use a correção da fatura") e o pagamento acima do devido nas faturas que mudaram. Ela vale nas rotas de lançamento, na fila (`/api/lancamentos/lote`), nas transferências, nas datas e no ajuste da fatura, na troca de padrão do cartão e na antecipação e quitação de parcelamento. A correção é `POST /api/cartoes/{id}/faturas/{mes}/correcao` (`backend/app/correcao_de_fatura.py`).

Decisões tomadas no caminho:

- **Parcela futura numa fatura paga**: acontece, quando uma fechada sem pagamento vem antes de uma paga (abril devendo, maio paga, compra esquecida de março em 2x). O parcelamento inteiro é recusado na criação, conferindo o mês de todas as parcelas, porque a geração em lotes não volta atrás (`test_parcela_futura_que_cairia_numa_fatura_paga_recusa_o_parcelamento`).
- **A paga que é a última e deixa saldo**: a fatura do mês seguinte nasce na mesma gravação, senão o saldo anterior não apareceria em lugar nenhum. Havendo uma fatura mais adiante, o saldo pula os meses sem fatura até ela.
- **Pagamento previsto numa fatura paga** também é recusado: ele viraria pagamento novo ao ser confirmado. Editar só a descrição de um pagamento ou de uma compra da paga continua valendo.
- **A correção não reabre a fatura**: precisa de pelo menos um pagamento e recusa um fechamento que a deixaria aberta.
- **Projeção e limite**: a projeção soma o "a pagar" de cada fatura (o saldo anterior conta só na fatura em que está); o limite soma o que cada fechada sem pagamento deve mais o saldo anterior da aberta.
- **Importação, backup e exportação**: não mudam. Eles levam só o gravado (compras, faturas, pagamentos); situação e saldo anterior são calculados. O importador do Mobills não cria pagamento de fatura, e a fatura importada (sem datas) continua paga e recebendo as compras escolhidas à mão. A restauração não passa pela proteção, de propósito.
- **Recusa na tela de lançar**: a tela avisa antes de salvar quando a compra cai numa fatura paga, com link para a correção; a recusa que chega pela fila aparece no "não enviado: motivo" da lista, como as outras.

Pendências: [ticket 126](126-parcelamento-e-recorrencia-na-fatura-paga.md) (excluir ou corrigir parcelamento e a recorrência no cartão ainda mexem numa fatura paga) e [ticket 127](127-medir-o-custo-da-protecao-da-fatura-paga.md) (medir o custo da proteção com o volume real).
