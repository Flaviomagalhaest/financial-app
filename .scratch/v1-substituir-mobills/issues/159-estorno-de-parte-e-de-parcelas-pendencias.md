# Estorno de parte e de todas as parcelas: decisões em aberto

Type: decision
Status: resolved
Blocked by: —
Skills: `grilling`, `domain-modeling` (HITL: decisão do dono)
Modelo recomendado: Opus
Effort recomendado: medium
Issue: #357
Origem: [ticket 138](138-estorno-de-parte-e-de-todas-as-parcelas.md): o que a implementação escolheu por conta própria e o que a spec não cobria

## O que decidir

O 138 entregou o estorno de uma parte e o de todas as parcelas com estes comportamentos provisórios:

- **Dividir uma compra que já tem estorno**: o estorno antigo fica ligado à compra inteira (sem parte), guarda a classificação que tinha e não acompanha mais as partes; conta contra o valor da compra, não contra o de uma parte. Alternativa: pedir à pessoa a parte de cada estorno ao dividir, ou recusar de novo.
- **Juntar ou tirar parte com estorno**: a API recusa tirar uma parte que tem estorno, encolhê-la abaixo do estornado e juntar as partes enquanto houver estorno de parte (o dono exclui o estorno antes).
- **Estorno de todas e a parte do parcelamento**: o estorno de todas as parcelas de uma *parte* do parcelamento (`estorno_parte_id` com `estorno_parcelamento_id`) é recusado até o [139](139-partes-na-compra-parcelada.md) criar as partes da compra parcelada.
- **Item do planejamento do estorno de todas**: conta no item do mês em que aparece pela regra do estorno avulso (a categoria que tem item, sem escolha do casal), não no item de cada parcela.
- **Parcelamento com estorno de todas**: só a exclusão do parcelamento foi travada. Corrigir o parcelamento para um total menor que o estornado, ou excluir uma parcela, não é recusado; junta-se ao [148](148-parcela-com-estorno-quando-a-regra-a-tira.md).
- **Pessoa do estorno de parte**: a tela preenche com a pessoa da parte, mas o servidor não a copia nem a acompanha (como no estorno de compra).

## Checklist

- [x] Decidir cada caso acima
- [x] Gravar na ADR 0016 (adendo) e no glossário
- [x] Abrir o ticket de implementação, com teste de API

## Resolução

Decidido com o dono (adendo do ticket 159 na [ADR 0016](../../../docs/adr/0016-estorno-e-lancamento-que-diminui-ligado-a-compra.md) e verbete **Estorno** do glossário):

- **Dividir uma compra com estorno**: fica como está (o estorno antigo fica no todo, com a classificação e a pessoa que tinha).
- **Juntar ou tirar parte com estorno**: continua recusado; exclui-se o estorno antes.
- **Estorno de todas de uma parte do parcelamento**: já resolvido pelo [160](160-estorno-de-todas-de-uma-parte-do-parcelamento.md).
- **Item do estorno de todas**: segue a escolha de item do parcelamento, como o de uma parte. Implementação no [189](189-item-e-pessoa-do-estorno-acompanham-a-compra.md).
- **Parcelamento com estorno de todas**: a correção ou a exclusão de parcela que deixaria o total abaixo do já estornado é recusada (422) antes de gravar. Implementação junto do [188](188-regras-que-tiram-parcela-ou-ocorrencia-com-estorno.md).
- **Pessoa do estorno**: acompanha a da compra, da parte ou do parcelamento, como as categorias e tags; o avulso guarda a dada. Implementação no [189](189-item-e-pessoa-do-estorno-acompanham-a-compra.md).
