# Conferir as regras de estorno e ajuste de fatura escolhidas no ticket 39

Type: grilling
Status: resolved
Blocked by: 39
Skills: `grilling`, `domain-modeling` (HITL: decisões do dono)
Modelo recomendado: Opus
Effort recomendado: medium
Issue: #182
Origem: [ticket 39](39-estorno-ajuste-de-fatura-e-cancelamento.md): a spec e as ADRs [0008](../../../docs/adr/0008-ajuste-de-fatura-fica-na-fatura.md) e [0016](../../../docs/adr/0016-estorno-e-lancamento-que-diminui-ligado-a-compra.md) não dizem o que fazer nestes casos, e o ticket 39 escolheu um comportamento provisório para cada um (já em `backend/app/lancamentos.py`, `backend/app/cartoes.py`, `backend/app/meses.py` e `backend/app/planejamento.py`, com teste)

## O que decidir

Para cada regra abaixo, o dono confirma o comportamento provisório ou pede outro. Mudança vira ticket de implementação; o que ficar vai para o glossário ou para as ADRs.

## Checklist

- [x] **Cancelar é excluir, em qualquer fatura**: a API não exige a fatura aberta. Alternativa: recusar a exclusão de compra de fatura fechada e mandar para o estorno
- [x] **Excluir a compra original deixa o estorno solto**: o estorno continua como crédito (e editável no valor e no cartão, sem checar mais o limite). Alternativa: recusar a exclusão enquanto houver estorno, ou excluir os estornos junto
- [x] **Estorno só em compra no cartão**, nunca em compra de conta, em receita nem em outro estorno
- [x] **Estorno igual à compra em categorias e tags, e imutável nelas**: a API recusa (422) categoria ou tag diferente e a edição delas no estorno. Mudar as categorias ou tags da compra depois não muda as do estorno. Alternativa: o estorno acompanha a compra
- [x] **Soma dos estornos até o valor da compra**; acima disso, 422
- [x] **Estorno em qualquer cartão**, não só no da compra (cartão reemitido); cai na fatura pela data, como uma compra, ou pela troca à mão
- [x] **Estorno de compra com tag ou categoria arquivada**: a categoria vale (vem da compra); a tag arquivada recusa (422 "tag arquivada")
- [x] **Um ajuste por fatura**, valor único que a edição substitui (não uma lista de ajustes), positivo ou negativo, `0` desfaz
- [x] **O total da fatura soma também os previstos** (as parcelas futuras que já estão nela), além dos realizados
- [x] **"Ainda dá para gastar" desconta os ajustes do mês** (soma dos itens menos os ajustes, sem passar de zero); um ajuste negativo (fatura menor que a soma das compras) também entra, e desconta menos
- [x] **Despesas do mês** (`/api/meses/{mes}/totais`): compras e estornos, previstos e realizados, mais os ajustes; receita, transferência e pagamento de fatura ficam de fora. A compra com mais de uma categoria ou tag conta inteira em cada uma
- [x] **Compra com mais de uma categoria**: `totais` a conta inteira em cada categoria e tag, enquanto o planejamento ainda não a conta em item nenhum (ticket 51); as duas leituras discordam até o 51 (o 51 passou a contá-la no item escolhido, ou no único com item; os totais seguem com o valor inteiro em cada categoria, como manda a ADR 0006)
- [x] **A planilha de exportação não leva o ajuste de fatura**: ele não é lançamento, então o total do mês na planilha fica abaixo de `despesas_centavos`. Alternativa: uma linha por ajuste, sem categoria
- [x] **"Ainda dá para gastar" não passa de zero para baixo**: ajuste maior que a soma dos itens mostra 0, sem dizer quanto estourou (o valor está em `ajustes_de_fatura_centavos`)
- [x] **Telas do [ticket 93](93-telas-de-estorno-ajuste-e-cancelamento.md): excluir compra de fatura fechada** sugere o estorno (link "Estornar"), mas deixa "Excluir mesmo assim", porque a API permite. Alternativa: sem o "mesmo assim" (casa com recusar a exclusão no primeiro item)
- [x] **Telas do ticket 93: "Estornar" só aparece na compra que o servidor já tem** (não na compra ainda na fila, em conflito, recusada ou excluída em outro aparelho) e enquanto sobrar valor a estornar
- [x] **Telas do ticket 93: o estorno abre com a descrição "Estorno <descrição da compra>"** e o valor igual ao que resta da compra (não ao valor dela, se já houve estorno); só os cartões ativos aparecem na escolha do cartão, e a compra de cartão arquivado não tem "Estornar"
- [x] **Telas do ticket 93: "Ajustar fatura" pelo valor real** troca o ajuste (valor real menos as compras da fatura, já com os estornos); **pela diferença**, soma ao ajuste que a fatura já tem (a diferença é contra o total que o app mostra). Zerar é informar o total sem ajuste (valor real) ou o oposto do ajuste (diferença); não há botão "remover ajuste"
- [x] **Telas do ticket 93: o resumo da fatura** mostra "Compras" (compras sem os estornos), "Estornos", "Ajuste" e "Total"; os estornos que só estão na fila não entram até subirem


## Answer

O dono conferiu as regras com `grilling` e `domain-modeling` (Q1 a Q46, na sessão de 01/11/2026). Ficou assim:

**Confirmado como está:**
- **Cancelar é excluir.** Vale na fatura aberta ou fechada, nunca na paga. A compra devolvida não se cancela: recebe um estorno.
- **Estornos:**
  - estorno só em compra no cartão;
  - a soma dos estornos vai até o valor da compra;
  - o estorno pode ir para qualquer cartão.
- **Ajuste de fatura:** um ajuste por fatura, e "Ajustar fatura" pelo valor real ou pela diferença.
- **Totais:**
  - o total da fatura soma também os previstos;
  - "ainda dá para gastar" desconta os ajustes;
  - "despesas do mês" fica como está, e a compra com várias categorias conta inteira nos totais (o 51 já resolveu o planejamento).
- **Telas do 93:**
  - "Excluir mesmo assim" na fatura fechada;
  - "Estornar" só na compra do servidor e enquanto sobrar valor;
  - o estorno preenchido como "Estorno <compra>", com o valor que resta;
  - o resumo da fatura.

**Mudou (tickets novos):**
- **[133](133-estorno-acompanha-a-compra.md)** (Q2, Q4, Q7, Q22, Q24):
  - as categorias e tags do estorno acompanham as da compra, inclusive as arquivadas;
  - a compra com estorno não pode ser excluída. "Excluir" fica ativo e explica por quê;
  - "Estornar" passa a aparecer na compra de cartão arquivado.
- **[134](134-ajuste-na-planilha-e-passou-no-ainda-da.md)** (Q13, Q18): a planilha ganha uma linha por ajuste de fatura, e "ainda dá para gastar" mostra "passou R$ X".
- **[135](135-estorno-avulso.md)** (Q15, Q25, Q26): **estorno avulso**, um crédito na fatura sem compra ligada. Categoria, tags e pessoa são opcionais.
- **[136](136-alcance-da-mudanca-na-parcela.md)** (Q39, Q40): **alcance da mudança na parcela** ("Só esta", "Esta e as próximas", "Todas"), para qualquer campo, sem sobrescrever o que foi alterado à mão.
- **Partes da compra** ([ADR 0022](../../../docs/adr/0022-partes-da-compra.md)), na v1:
  - [137](137-partes-da-compra.md): partes na compra à vista;
  - [138](138-estorno-de-parte-e-de-todas-as-parcelas.md): estorno de uma parte e de todas as parcelas;
  - [139](139-partes-na-compra-parcelada.md): partes na compra parcelada (proporção, centavos na maior parte);
  - [140](140-partes-na-recorrencia.md): partes na recorrência;
  - [141](141-favorito-e-sugestao-com-partes.md): favorito e sugestão com partes.

**Glossário:**
- termos novos: **Estorno avulso**, **Parte da compra** e **Alcance da mudança na parcela**;
- termos revistos: **Compra cancelada**, **Estorno** e **Parcela alterada à mão**.

A [ADR 0016](../../../docs/adr/0016-estorno-e-lancamento-que-diminui-ligado-a-compra.md) ganhou um adendo.
