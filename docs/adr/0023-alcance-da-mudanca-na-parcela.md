---
status: accepted
---

# O alcance da mudança na parcela leva ao parcelamento o que ele guarda, e o resto vai à mão em cada parcela

Ao mudar uma parcela, a pessoa escolhe "Só esta", "Esta e as próximas" ou "Todas (inclusive as já realizadas)" (ticket 136, decisões Q39 e Q40 do ticket 94). "Só esta" é a edição comum do lançamento: vai pela fila, vale sem internet e deixa a parcela **alterada à mão** naquele campo. Os outros dois mudam o parcelamento e precisam de internet, como a correção dele ([ADR 0011](0011-sem-internet-so-lancamentos-e-conflito-decidido-a-mao.md)), pela rota `PATCH /api/parcelas/{id}`. O parcelamento guarda uma descrição, uma classificação, um valor total e uma data, e não um trecho: por isso a descrição, as categorias, as tags, a pessoa e o item vão para ele, valendo a partir da parcela mudada ou desde a 1ª, e em "todas" o valor e a data viram a correção do valor da parcela e da data. O valor e a data só daqui para frente, a conta e a fatura vão parcela a parcela, como mudança à mão em cada uma. Assim a correção seguinte e a tarefa diária não desfazem o que o casal pediu. Nas outras parcelas, o campo que uma pessoa mudou só nela fica como está, e a resposta diz quantas ficaram assim; a parcela mudada segue o pedido mesmo que tenha sido mudada à mão antes.

## Considered Options

- **"Esta e as próximas" e "todas" pela fila, como a mudança da recorrência ([ADR 0020](0020-mudanca-da-recorrencia-vai-pela-fila.md))**: o aparelho teria de mostrar as parcelas mudadas sem repetir as regras do parcelamento, e o pedido levaria o aviso das realizadas para depois do envio. Ficou com a internet, como a correção do parcelamento (ticket 98); "só esta" já cobre a mudança feita na hora de pagar.
- **Gravar no parcelamento um trecho (valor e data a partir da parcela N)**: o valor e a data "daqui para frente" seguiriam a regra, e a parcela nova de um crescer viria com eles. Muda o cálculo de todas as correções e da geração; fica para o dono decidir (ticket 144).
- **Mudar as outras parcelas sem marca e sem mudar o parcelamento**: a tarefa diária, que põe as parcelas como o parcelamento manda, desfaria o valor e a data no dia seguinte.

## Consequences

- A marca de "alterada à mão" passa a ser por campo, e a correção do parcelamento também preserva a descrição, as categorias, as tags, a pessoa e o item que uma pessoa mudou numa parcela só (antes, só valor, data, conta e fatura). A conta mudada à mão segura também a data e a fatura. Só o valor, a data, a conta e a fatura mudados à mão impedem o parcelamento de encolher e tirar a parcela.
- A edição em lote leva o parcelamento inteiro e grava as parcelas com a origem dele: não as marca como alteradas à mão. A migration 0059 tira a marca que o lote de antes deixou.
- A parcela com uma mudança ainda na fila ou em conflito não pergunta o alcance: a mudança dela é "só esta", como antes.
- A mudança de uma realizada que não é a parcela mudada (valor, data, conta ou fatura) pede a mesma confirmação da correção.
- O conflito da versão, nos dois alcances que mudam o parcelamento, recusa o pedido (422) em vez de abrir a tela de conflito: a pessoa está com internet, confere e muda de novo.
- A conta mudada em "todas" não muda a do parcelamento, e a mudança parcela a parcela que para no meio não é retomada pela tarefa diária (tickets 144 e 145).
