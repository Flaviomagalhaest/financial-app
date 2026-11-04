# Parcelamento e recorrência que mexem numa fatura paga

Type: grilling
Status: resolved
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

- [x] Decidir, com o dono, a regra de cada caminho acima
- [x] Implementar com teste na API (`backend/tests/test_fatura_paga.py`): passou para os tickets [170](170-exclusao-do-parcelamento-deixa-as-de-fatura-paga.md), [171](171-correcao-do-parcelamento-nao-mexe-na-fatura-paga.md) e [172](172-recorrencia-no-cartao-respeita-a-fatura-paga.md)
- [x] Registrar a decisão na ADR 0021 ou numa nova, se mudar o que ela diz

## Answer

Decidido com o dono em 04/11. A regra vale para a fatura paga pelo pagamento. A parcela e o previsto da fatura importada do Mobills seguem como hoje, com o aviso e a confirmação, que é o mesmo critério de `cartoes.protegida`. A decisão está nas Consequences da [ADR 0021](../../../docs/adr/0021-o-pagamento-quita-a-fatura.md), sem ADR nova.

- **Excluir o parcelamento**: as parcelas de fatura paga ficam, e o resto sai. As realizadas de fatura não paga saem com a confirmação do [ticket 142](142-escopo-na-edicao-de-parcela-e-aviso-ao-excluir.md). O parcelamento continua existindo, **encolhido até a última parcela de fatura paga**, com o total igual à soma das parcelas que ficaram, e não gera mais nada. A parcela antes dela que não está numa fatura paga sai como excluída uma a uma (as faturas pagas nem sempre são as primeiras: pode haver uma fechada sem pagamento antes de uma paga). O aviso do 142 diz quantas ficam e que, para tirá-las, é preciso corrigir a fatura. Foram descartados: recusar a exclusão inteira, porque o casal não teria como se livrar do resto; apagar tudo, porque a fatura paga mudaria e o pagamento passaria do devido; e desligar as parcelas como compras avulsas, porque seria um conceito novo.
- **Corrigir o parcelamento**:
  - a parcela de fatura paga **fica intocada**, como a alterada à mão: conta em `parcelas_mantidas`, não pede confirmação e não recebe a diferença do valor;
  - encolher para menos parcelas que a última de fatura paga é **recusado** (422), porque um "3/2" não faz sentido;
  - levar uma parcela **para dentro** de uma fatura paga recusa o pedido inteiro antes do primeiro lote (422), simulando os lotes como a mudança com alcance já faz ([ticket 149](149-recusa-da-mudanca-parcela-a-parcela-nao-prevista.md)).
- **Recorrência no cartão**:
  - a criação cuja ocorrência do dia do lançamento cairia numa fatura paga é **recusada** antes de gravar (422 na rota, `recusada` na fila);
  - na alteração, o **atrasado** de fatura paga fica como está, e o resto é refeito;
  - a exclusão não muda, porque só tira previstos de hoje em diante.

Implementação nos tickets [170](170-exclusao-do-parcelamento-deixa-as-de-fatura-paga.md) (exclusão), [171](171-correcao-do-parcelamento-nao-mexe-na-fatura-paga.md) (correção) e [172](172-recorrencia-no-cartao-respeita-a-fatura-paga.md) (recorrência), que não bloqueiam um ao outro. Nenhum ticket foi aberto para os dois arquivos com o número 126: o dono fechou como `wontfix` a renumeração dos números repetidos ([processo 09](../../processo-do-repositorio/issues/09-numero-de-ticket-repetido.md)).
