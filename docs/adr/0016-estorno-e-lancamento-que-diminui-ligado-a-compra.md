---
status: accepted
---

# O estorno é um lançamento de despesa que diminui, ligado à compra original

O estorno (crédito de uma compra devolvida) é uma linha de `lancamentos` com `tipo` `despesa` e a coluna `estorno_de` apontando para a compra original. O valor fica positivo, como em toda despesa, e quem soma despesas trata o estorno com sinal contrário: a fatura, o mês, a categoria, a tag e o item do planejamento descontam o que ele devolve, no mês da fatura em que ele aparece. Ele leva as mesmas categorias e tags da compra, vai para um cartão, e a soma dos estornos de uma compra não passa do valor dela. O ajuste de fatura, que não é lançamento, segue a [ADR 0008](0008-ajuste-de-fatura-fica-na-fatura.md): uma coluna `ajuste_centavos` na tabela `faturas`.

## Considered Options

- **`tipo` `receita` com a categoria da compra**: a regra "categoria de despesa num lançamento de despesa" impediria as mesmas categorias, e o estorno apareceria em receitas e na sobra do mês como se fosse dinheiro novo.
- **Valor negativo na despesa**: a coluna tem `CHECK (valor_centavos > 0)`, e o DSQL não altera restrições (ADR 0009); trocar a restrição pediria refazer a tabela e quebraria o backup, como na ADR 0014.
- **Tabela própria de estornos**: todo lugar que lista ou soma lançamentos (fila do aparelho, busca, planilha, planejamento) teria de juntar duas tabelas.

## Consequences

- Toda soma de despesa precisa do sinal: `VALOR_COM_SINAL` em `app/lancamentos.py` serve às somas do cartão e do mês, e o planejamento tem o seu `CASE`. Quem criar uma soma nova de despesa trata `estorno_de`.
- O saldo da conta não muda, porque o estorno só existe no cartão e o saldo do cartão não é de uma conta.
- A planilha exporta o estorno com o sinal contrário ao da compra (crédito).
- O backup sobe para a versão 14 (`estorno_de` no lançamento e `ajuste_centavos` na fatura).
