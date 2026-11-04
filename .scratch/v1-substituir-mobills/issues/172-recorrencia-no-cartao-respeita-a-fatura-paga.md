# A recorrência no cartão respeita a fatura paga

Type: task
Status: resolved
Blocked by: —
Skills: `implement`, `tdd`
Modelo recomendado: Opus
Effort recomendado: medium
Issue: #412
Origem: decisão do dono no [ticket 126](126-parcelamento-e-recorrencia-na-fatura-paga.md) (respostas Q4, Q5 e Q6)

## O que construir

A recorrência no cartão não passa pela proteção da [ADR 0021](../../../docs/adr/0021-o-pagamento-quita-a-fatura.md), nem na rota nem na fila. A geração não cria nada antes de hoje (tickets 87 e 125), mas há duas exceções:

- **Criação com o dia do lançamento no passado** (fila sem internet): a ocorrência desse dia nasce realizada e pode cair numa fatura paga. Nesse caso, a criação é **recusada antes de gravar**: 422 na rota e `recusada` na fila, como o parcelamento já faz.
- **Atrasado em fatura paga**: um previsto não confirmado, numa fatura que fechou e foi paga, conta nas compras dela. Na alteração da regra, o reajuste **não mexe nele** (pula, como pula o alterado à mão), e o resto é refeito.

A exclusão da recorrência não muda: ela só tira previstos de hoje em diante, que não estão em fatura paga. Só vale para a fatura paga pelo pagamento; a importada do Mobills segue como hoje.

## Checklist

- [x] A criação cuja ocorrência do dia do lançamento cairia numa fatura paga é recusada antes de gravar (rota 422, fila `recusada`)
- [x] O reajuste da alteração deixa intocado o atrasado de fatura paga e refaz o resto
- [x] Conferir que nenhum outro caminho da recorrência (geração diária, realização automática, partes) muda uma fatura paga
- [x] Testes de API em `backend/tests/test_fatura_paga.py`

## Answer

- **Criação**: `_conferir_as_faturas_do_passado` recusa, antes de gravar a regra, a recorrência no cartão com alguma ocorrência entre o dia do lançamento e ontem (a do dia do lançamento e, num calendário curto, as seguintes, que nascem atrasadas) que cairia numa fatura paga pelo pagamento: 422 na rota, `recusada` na fila. A importada do Mobills fica de fora (`cartoes.meses_pagos`, pelo mesmo critério de `paga_pelo_pagamento`).
- **Alteração**: o reajuste pula o atrasado de fatura paga (pelo `mes` gravado) antes de qualquer outra regra, inclusive a retirada pelo fim, e o resto é refeito. Também pula o atrasado que a data nova levaria para dentro de uma fatura paga: escolha provisória, para o dono confirmar no [ticket 178](178-atrasado-levado-para-dentro-da-fatura-paga.md).
- **Outros caminhos conferidos**: a geração diária e a da mudança só criam de hoje em diante (fatura ainda aberta); a realização automática só muda a `situacao`, que não muda o total da fatura; as partes só mudam pelo reajuste, que pula o atrasado; a exclusão só tira de hoje em diante. Fica de fora o reenvio da criação depois de um pagamento entre os lotes da geração: [ticket 179](179-reenvio-da-recorrencia-depois-do-pagamento.md).
