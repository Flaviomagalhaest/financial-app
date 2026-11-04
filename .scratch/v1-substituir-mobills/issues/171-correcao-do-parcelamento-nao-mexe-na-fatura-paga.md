# A correção do parcelamento não mexe na fatura paga

Type: task
Status: claimed
Blocked by: —
Skills: `implement`, `tdd`
Modelo recomendado: Opus
Effort recomendado: medium
Issue: #411
Origem: decisão do dono no [ticket 126](126-parcelamento-e-recorrencia-na-fatura-paga.md) (respostas Q2, Q3, Q6, Q9, Q10 e Q11 e o caso de canto)

## O que construir

Hoje a correção do parcelamento no cartão, com `confirmar_realizadas`, muda o valor e a data das realizadas de fatura paga. Uma data nova para trás também pode levar uma parcela para dentro de uma fatura paga. As duas coisas ficam fora da proteção da [ADR 0021](../../../docs/adr/0021-o-pagamento-quita-a-fatura.md).

O que fica valendo, só para a fatura paga pelo pagamento (a importada do Mobills segue como hoje):

- **A parcela que está numa fatura paga fica intocada**, como a alterada à mão: entra em `parcelas_mantidas`, não entra no aviso de `confirmar_realizadas` e não pede confirmação. O resto é corrigido normalmente. Exemplo: um total que passa de 1.000 para 1.200 em 10x, com as parcelas 1 a 3 pagas a 100. As outras sete vão para 120 e a diferença não é compensada (a soma fica em 1.140).
- **Encolher para menos parcelas que a última de fatura paga é recusado** (422): com as parcelas 1 a 3 pagas, corrigir para 2x é recusado. O mínimo é o número da última parcela de fatura paga, mesmo que alguma parcela antes dela não esteja paga.
- **A correção que levaria uma parcela para dentro de uma fatura paga recusa o pedido inteiro antes do primeiro lote** (422, nada gravado), com o aviso para corrigir a fatura. A simulação lote a lote é a da mudança com alcance (`cartoes.conferir_sem_gravar`, [ticket 149](149-recusa-da-mudanca-parcela-a-parcela-nao-prevista.md)).

## Checklist

- [ ] A parcela de fatura paga fica intocada (valor, data e fatura), conta em `parcelas_mantidas` e fica fora do aviso de realizadas
- [ ] Encolher abaixo da última parcela de fatura paga dá 422, com a mensagem
- [ ] A parcela que entraria numa fatura paga recusa o pedido inteiro antes de gravar (422), também quando isso acontece só num lote seguinte
- [ ] A mudança com alcance ("esta e as próximas", "todas") segue as mesmas regras; conferir se já segue
- [ ] A tela mostra as recusas e a contagem de mantidas
- [ ] Testes de API em `backend/tests/test_fatura_paga.py`
- [ ] Conferir se o `GLOSSARY.md` (**Correção do parcelamento**) bate com o que foi feito
