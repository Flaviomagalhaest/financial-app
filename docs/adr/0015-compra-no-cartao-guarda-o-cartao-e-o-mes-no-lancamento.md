---
status: accepted
---

# A compra no cartão guarda o cartão em `conta_id` e o mês em que conta no próprio lançamento

A compra no cartão é uma linha de `lancamentos` como as outras: `conta_id` guarda o cartão (a conta ou o cartão, como na fileira de toque do lançamento rápido), e o lançamento grava o **mês em que conta** (`mes`), que no cartão é o **mês da fatura**. A fatura é a do cartão titular nesse mês, numa tabela `faturas` com chave `(cartao_id, mes)`: não há id de fatura no lançamento. A troca de fatura é só mudar o mês, com a marca `fatura_a_mao` para a escolha não ser refeita depois.

## Considered Options

- **Coluna `cartao_id` e `conta_id` vazio no cartão**: deixaria claro de que tipo é cada lançamento, mas `conta_id` nasceu `NOT NULL` no ticket 32, e o DSQL não altera nem remove restrições (ADR 0009); refazer a tabela exigiria copiar os dados e quebraria o backup, como na ADR 0014.
- **`fatura_id` no lançamento, com id próprio da fatura**: mais um id para o aparelho conhecer sem internet, e "uma fatura por cartão por mês" precisaria de um índice único a mais para duas compras ao mesmo tempo não criarem duas faturas do mesmo mês. Com a chave `(cartao_id, mes)`, a regra vale pela própria chave primária, e a fatura nasce com `INSERT ... ON CONFLICT DO NOTHING`.

## Consequences

- O saldo da conta não muda: ele soma `l.conta_id = c.id`, e o id de um cartão nunca é o de uma conta.
- Quem lê lançamentos descobre o cartão pela tabela `cartoes` (a API devolve `fatura_mes` só no cartão). Busca, planilha e somas por mês juntam `cartoes` quando precisam do nome.
- O mês da fatura e o mês em que a compra conta são o mesmo valor, gravado uma vez; mudar as datas de uma fatura nunca tira a fatura do mês dela.
- O adicional guarda o próprio id em `conta_id`, e a fatura é a do titular (`COALESCE(titular_id, id)`).
