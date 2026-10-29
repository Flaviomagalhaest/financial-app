# Conferir as regras de estorno e ajuste de fatura escolhidas no ticket 39

Type: grilling
Status: ready-for-human
Blocked by: 39
Skills: `grilling`, `domain-modeling` (HITL: decisões do dono)
Modelo recomendado: Opus
Effort recomendado: medium
Issue: #182
Origem: [ticket 39](39-estorno-ajuste-de-fatura-e-cancelamento.md): a spec e as ADRs [0008](../../../docs/adr/0008-ajuste-de-fatura-fica-na-fatura.md) e [0016](../../../docs/adr/0016-estorno-e-lancamento-que-diminui-ligado-a-compra.md) não dizem o que fazer nestes casos, e o ticket 39 escolheu um comportamento provisório para cada um (já em `backend/app/lancamentos.py`, `backend/app/cartoes.py`, `backend/app/meses.py` e `backend/app/planejamento.py`, com teste)

## O que decidir

Para cada regra abaixo, o dono confirma o comportamento provisório ou pede outro. Mudança vira ticket de implementação; o que ficar vai para o glossário ou para as ADRs.

## Checklist

- [ ] **Cancelar é excluir, em qualquer fatura**: a API não exige a fatura aberta. Alternativa: recusar a exclusão de compra de fatura fechada e mandar para o estorno
- [ ] **Excluir a compra original deixa o estorno solto**: o estorno continua como crédito (e editável no valor e no cartão, sem checar mais o limite). Alternativa: recusar a exclusão enquanto houver estorno, ou excluir os estornos junto
- [ ] **Estorno só em compra no cartão**, nunca em compra de conta, em receita nem em outro estorno
- [ ] **Estorno igual à compra em categorias e tags, e imutável nelas**: a API recusa (422) categoria ou tag diferente e a edição delas no estorno. Mudar as categorias ou tags da compra depois não muda as do estorno. Alternativa: o estorno acompanha a compra
- [ ] **Soma dos estornos até o valor da compra**; acima disso, 422
- [ ] **Estorno em qualquer cartão**, não só no da compra (cartão reemitido); cai na fatura pela data, como uma compra, ou pela troca à mão
- [ ] **Estorno de compra com tag ou categoria arquivada**: a categoria vale (vem da compra); a tag arquivada recusa (422 "tag arquivada")
- [ ] **Um ajuste por fatura**, valor único que a edição substitui (não uma lista de ajustes), positivo ou negativo, `0` desfaz
- [ ] **O total da fatura soma também os previstos** (as parcelas futuras que já estão nela), além dos realizados
- [ ] **"Ainda dá para gastar" desconta os ajustes do mês** (soma dos itens menos os ajustes, sem passar de zero); um ajuste negativo (fatura menor que a soma das compras) também entra, e desconta menos
- [ ] **Despesas do mês** (`/api/meses/{mes}/totais`): compras e estornos, previstos e realizados, mais os ajustes; receita, transferência e pagamento de fatura ficam de fora. A compra com mais de uma categoria ou tag conta inteira em cada uma
- [ ] **Compra com mais de uma categoria**: `totais` a conta inteira em cada categoria e tag, enquanto o planejamento ainda não a conta em item nenhum (ticket 51); as duas leituras discordam até o 51 (o 51 passou a contá-la no item escolhido, ou no único com item; os totais seguem com o valor inteiro em cada categoria, como manda a ADR 0006)
- [ ] **A planilha de exportação não leva o ajuste de fatura**: ele não é lançamento, então o total do mês na planilha fica abaixo de `despesas_centavos`. Alternativa: uma linha por ajuste, sem categoria
- [ ] **"Ainda dá para gastar" não passa de zero para baixo**: ajuste maior que a soma dos itens mostra 0, sem dizer quanto estourou (o valor está em `ajustes_de_fatura_centavos`)
