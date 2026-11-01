---
status: accepted
---

# A compra que junta coisas diferentes se divide em partes

Uma compra só às vezes junta coisas de categorias e pessoas diferentes (no Mercado Livre, R$ 500 de roupa da esposa, R$ 250 de fone do Flávio e R$ 250 de cortina do casal). Pela [ADR 0006](0006-varias-categorias-e-um-item-do-planejamento.md), a compra com várias categorias conta inteira em cada uma, o que infla os totais. Na v1 a despesa (à vista, parcelada ou recorrente, no cartão ou na conta) pode ter **partes**: duas ou mais, cada uma com descrição, valor, categorias, tags, pessoa e item do planejamento próprios, somando o valor da compra. A compra continua uma linha só na fatura e no extrato, que é como o banco a mostra, e o estorno pode ser de uma parte. Na parcelada e na recorrente, as partes são uma proporção: cada parcela ou ocorrência se divide por elas, os centavos do arredondamento vão para a maior parte (a primeira, no empate), e o que vale é o valor da parcela ou da ocorrência. Decidido no [ticket 94](../../.scratch/v1-substituir-mobills/issues/94-conferir-as-regras-de-estorno-e-ajuste.md).

## Considered Options

- **Lançar uma compra por pedaço** (o caminho de antes): a fatura mostra três linhas onde o banco mostra uma, e conferir a fatura fica mais difícil.
- **Várias categorias na mesma compra** (ADR 0006): conta o valor inteiro em cada categoria e não diz de quem é cada pedaço.
- **Partes só na compra à vista**: rejeitada pelo dono; a compra parcelada e a recorrente também juntam coisas diferentes.

## Consequences

- Quem soma por categoria, tag, pessoa ou item do planejamento lê a parte, não a compra; quem soma a fatura, o mês e o saldo lê a compra.
- Na fila sem internet, as partes são um campo só no conflito: quem decide escolhe a lista inteira de um lado.
- A planilha de exportação sai com uma linha por parte; o backup ganha uma versão nova. A importação do Mobills não cria partes.
- O favorito e a sugestão levam as partes, na proporção; o aviso de planejamento mostra uma linha por parte.
- Na compra parcelada (ticket 139), o parcelamento guarda as partes com o valor de cada uma como proporção, e cada parcela recebe as partes dele divididas pelo valor dela, guardando a proporção de onde vieram: a parcela que muda de valor (à mão, na confirmação, na antecipação ou na correção) se divide de novo por ela, sem carregar o arredondamento da divisão anterior. Mudar as partes de uma parcela segue o alcance da [ADR 0023](0023-alcance-da-mudanca-na-parcela.md): "só esta" dá à parcela partes próprias, e as partes, a categoria, as tags, a pessoa e o item mudam juntos ou ficam juntos como estão, para a parcela nunca ter partes e classificação própria ao mesmo tempo.
