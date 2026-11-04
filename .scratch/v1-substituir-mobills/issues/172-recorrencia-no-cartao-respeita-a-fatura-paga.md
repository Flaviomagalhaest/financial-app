# A recorrência no cartão respeita a fatura paga

Type: task
Status: claimed
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

- [ ] A criação cuja ocorrência do dia do lançamento cairia numa fatura paga é recusada antes de gravar (rota 422, fila `recusada`)
- [ ] O reajuste da alteração deixa intocado o atrasado de fatura paga e refaz o resto
- [ ] Conferir que nenhum outro caminho da recorrência (geração diária, realização automática, partes) muda uma fatura paga
- [ ] Testes de API em `backend/tests/test_fatura_paga.py`
