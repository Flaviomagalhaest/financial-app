# Ligar o CSV de planilha ao esquema real

Type: task
Status: ready-for-agent
Blocked by: 36, 37, 40, 41
Skills: `implement`, `tdd`
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #143
Origem: [ticket 66](66-exportar-tudo-e-csv-de-planilha.md): o `POST /api/exportacoes` e o formato do CSV de planilha estão prontos, mas só existem as tabelas `contas`, `categorias`, `lancamentos` e `lancamento_categorias` (ticket 32); cartões, faturas e tags ainda não, então `ler_lancamentos` (`backend/app/exportacao.py`) devolve nenhuma linha e a planilha sai só com o cabeçalho

## O que fazer

Escrever a consulta de `ler_lancamentos` contra o esquema real, com os nomes no lugar dos ids, e trocar o `NotImplementedError` que hoje a protege. Colunas e formato já fixados em `COLUNAS_DA_PLANILHA` e `formatar_planilha`, vindos do [ticket 25](25-exportacao.md): data, descrição, valor, conta ou cartão, fatura, categorias (` | `), tags, pessoa, situação (previsto ou efetivado), quem criou e quem alterou por último. Sem filtro por período; valor em reais com ponto (o formatador troca por vírgula).

**Atenção à ordem**: as tabelas já existem todas (o ticket 37 trouxe `cartoes` e `faturas`, e o lançamento no cartão guarda o cartão em `conta_id`, [ADR 0015](../../../docs/adr/0015-compra-no-cartao-guarda-o-cartao-e-o-mes-no-lancamento.md)); a guarda de `ler_lancamentos` agora espera a coluna `lancamentos.pessoa` do ticket 41. Enquanto ela faltar, a planilha sai só com o cabeçalho; assim que existir, `ler_lancamentos` levanta `NotImplementedError` e `POST /api/exportacoes` com `planilha` responde 500. Este ticket entra junto com o 41.

Decidir aqui também a grafia dos nomes das colunas (hoje sem acento: `descricao`, `situacao`) e as datas em `AAAA-MM-DD` do [ticket 25](25-exportacao.md).

## Checklist

- [ ] Teste na costura `POST /api/exportacoes` com `formato: planilha`, num banco com lançamentos, categorias, tags, conta e cartão de exemplo fictício: o CSV traz nomes, não ids
- [ ] Lançamento de cartão traz o cartão e a fatura; lançamento de conta traz a conta e fatura vazia; transferência e pagamento de fatura têm o destino claro (decidir com o dono se precisar)
- [ ] Lançamento com várias categorias e tags sai numa linha só, separados por ` | `
- [ ] Lançamentos excluídos ou de outra origem não somem do CSV (todo o histórico), inclusive os "importado do Mobills"
- [ ] O lançamento com a marca de exclusão (`excluido_em`, ticket 34) fica fora da planilha, como em todas as leituras; o item acima fala do histórico, não do que o casal excluiu
- [ ] A consulta lê na mesma transação `REPEATABLE READ` de `exportar`
- [ ] Remover a guarda da coluna `pessoa` e o ramo que devolve lista vazia
- [ ] Verificações do projeto rodando e PR aberto para `main`
