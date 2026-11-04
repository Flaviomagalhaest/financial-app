# A correção do parcelamento não mexe na fatura paga

Type: task
Status: resolved
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

- [x] A parcela de fatura paga fica intocada (valor, data e fatura), conta em `parcelas_mantidas` e fica fora do aviso de realizadas
- [x] Encolher abaixo da última parcela de fatura paga dá 422, com a mensagem
- [x] A parcela que entraria numa fatura paga recusa o pedido inteiro antes de gravar (422), também quando isso acontece só num lote seguinte
- [x] A mudança com alcance ("esta e as próximas", "todas") segue as mesmas regras; conferir se já segue
- [x] A tela mostra as recusas e a contagem de mantidas
- [x] Testes de API em `backend/tests/test_fatura_paga.py`
- [x] Conferir se o `GLOSSARY.md` (**Correção do parcelamento**) bate com o que foi feito

## Answer

Feito em 04/11.

- **A parcela de fatura paga fica intocada.** `parcelamentos.parcelas_nas_faturas_pagas` acha as parcelas que estão numa fatura paga pelo pagamento (`cartoes.paga_pelo_pagamento`; a importada do Mobills fica de fora e segue a correção, com o aviso). `_correcoes` trata essas parcelas como alteradas à mão no valor, na data, na conta e na fatura: elas contam em `parcelas_mantidas` e ficam fora do aviso. A classificação (descrição, categorias, tags...) continua sendo corrigida nelas, porque não muda a fatura.
- **Encolher abaixo da última parcela de fatura paga** é recusado em `gravar_correcao` (422): "a parcela N está numa fatura paga: o parcelamento não fica com menos de N parcelas (para mudá-la, use a correção da fatura)".
- **Entrar numa fatura paga** recusa o pedido inteiro antes de gravar. `_conferir_os_lotes` simula, com `cartoes.conferir_sem_gravar`, cada lote do refazer e, no fim, a geração das parcelas que faltam. A recusa vem antes do aviso das realizadas, para o pedido que vai ser recusado não pedir confirmação.
- **Mudança com alcance.** "Todas" com valor ou data passa pela correção e segue a mesma regra. Em "esta e as próximas" e na conta ou fatura de "todas", `mudanca_na_parcela._falta` deixa a parcela de fatura paga como está, também a de uma fatura paga no meio da mudança. Antes, essa parcela recusava o pedido. Os testes do ticket 149 sobre a recusa num lote seguinte e a recusa gravada no parcelamento passaram a usar uma parcela que **entraria** numa fatura paga.
- **Tela.** Ela já mostrava a recusa (`motivo`) e a contagem. A frase das mantidas agora diz "alguém as mudou à mão ou elas estão numa fatura paga", e as dicas da tela do parcelamento e da parcela também falam da fatura paga.
- **Testes.** Testes de API em `backend/tests/test_fatura_paga.py`; o `GLOSSARY.md` (**Correção do parcelamento**) foi detalhado.

Pendência: [ticket 176](176-fatura-paga-no-meio-do-refazer-da-correcao.md). A fatura paga entre a gravação e um lote seguinte do refazer ainda recebe a parcela que a correção leva para ela.
