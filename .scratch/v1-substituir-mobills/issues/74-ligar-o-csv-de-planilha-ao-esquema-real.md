# Ligar o CSV de planilha ao esquema real

Type: task
Status: ready-for-agent
Blocked by: 32, 36, 37, 40, 41
Skills: `implement`, `tdd`
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #143
Origem: [ticket 66](66-exportar-tudo-e-csv-de-planilha.md): o `POST /api/exportacoes` e o formato do CSV de planilha estão prontos, mas as tabelas de lançamentos, contas, cartões, faturas, categorias e tags ainda não existem, então `ler_lancamentos` (`backend/app/exportacao.py`) devolve nenhuma linha e a planilha sai só com o cabeçalho

## O que fazer

Escrever a consulta de `ler_lancamentos` contra o esquema real, com os nomes no lugar dos ids, e trocar o `NotImplementedError` que hoje a protege. Colunas e formato já fixados em `COLUNAS_DA_PLANILHA` e `formatar_planilha`, vindos do [ticket 25](25-exportacao.md): data, descrição, valor, conta ou cartão, fatura, categorias (` | `), tags, pessoa, situação (previsto ou efetivado), quem criou e quem alterou por último. Sem filtro por período; valor em reais com ponto (o formatador troca por vírgula).

## Checklist

- [ ] Teste na costura `POST /api/exportacoes` com `formato: planilha`, num banco com lançamentos, categorias, tags, conta e cartão de exemplo fictício: o CSV traz nomes, não ids
- [ ] Lançamento de cartão traz o cartão e a fatura; lançamento de conta traz a conta e fatura vazia; transferência e pagamento de fatura têm o destino claro (decidir com o dono se precisar)
- [ ] Lançamento com várias categorias e tags sai numa linha só, separados por ` | `
- [ ] Lançamentos excluídos ou de outra origem não somem do CSV (todo o histórico), inclusive os "importado do Mobills"
- [ ] A consulta lê na mesma transação `REPEATABLE READ` de `exportar`
- [ ] Remover `TABELAS_DA_PLANILHA` e o ramo que devolve lista vazia quando faltam tabelas
- [ ] Verificações do projeto rodando e PR aberto para `main`
