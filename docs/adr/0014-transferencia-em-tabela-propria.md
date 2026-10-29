---
status: accepted
---

# A transferência fica numa tabela própria, não no tipo do lançamento

A **transferência** (dinheiro de uma conta do casal para outra) tem duas contas, e o lançamento tem uma. Ela vive na tabela `transferencias`, com a API `/api/transferencias`, em vez de ser um terceiro valor de `lancamentos.tipo`. O saldo da conta soma os lançamentos e as transferências realizados depois da data do **saldo de abertura**.

## Considered Options

- **Terceiro tipo em `lancamentos` com `conta_destino_id`**: um só lugar para listar e buscar, mas o `CHECK` de `tipo` e o `valor_centavos > 0` já existem na tabela criada pelo ticket 32, e o DSQL não altera nem remove restrições (ADR 0009). Refazer a tabela exigiria copiar os dados em `prod` e quebraria o backup.
- **Dois lançamentos ligados (saída e entrada)**: reaproveita a tabela, mas a edição de um precisa mexer no outro, a exclusão pode deixar um órfão, e cada um contaria como despesa e receita nas somas.

## Consequences

- As somas de despesa e receita (planejamento, estatísticas, resumo da busca) não precisam excluir transferências: elas nem estão na tabela.
- Busca, histórico, edição em lote e o CSV de planilha terão de juntar as duas tabelas para mostrar a transferência (tickets 24, 57 e 59).
- O pagamento de fatura (ticket 38) é uma transferência de uma conta para um cartão e parte desta tabela: o cartão fica em `conta_destino_id` (como a compra guarda o cartão em `conta_id`, ADR 0015) e a coluna `fatura_mes` diz a fatura que ele quita. Não tem categoria, e o saldo do cartão nunca entra em `contas`.
- A categoria da transferência é uma só e opcional, da lista de transferência; não há tabela de associação.
- Reverter é migrar as linhas para um tipo novo em `lancamentos`, o que o DSQL só permite criando outra tabela.
