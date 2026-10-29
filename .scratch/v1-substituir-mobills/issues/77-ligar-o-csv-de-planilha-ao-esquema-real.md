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

**Atenção à ordem**: enquanto faltar alguma das tabelas de `TABELAS_DA_PLANILHA`, `ler_lancamentos` devolve só o cabeçalho; assim que a última existir, ela levanta `NotImplementedError` e `POST /api/exportacoes` com `planilha` responde 500. Este ticket precisa entrar antes ou junto com a última tabela (quem mesclar a última dos tickets 36, 37, 40 e 41 faz este junto).

Decidir aqui também a grafia dos nomes das colunas (hoje sem acento: `descricao`, `situacao`) e as datas em `AAAA-MM-DD` do [ticket 25](25-exportacao.md).

## Checklist

- [ ] Teste na costura `POST /api/exportacoes` com `formato: planilha`, num banco com lançamentos, categorias, tags, conta e cartão de exemplo fictício: o CSV traz nomes, não ids
- [ ] Lançamento de cartão traz o cartão e a fatura; lançamento de conta traz a conta e fatura vazia; transferência e pagamento de fatura têm o destino claro (decidir com o dono se precisar)
- [ ] Lançamento com várias categorias e tags sai numa linha só, separados por ` | `
- [ ] Lançamentos excluídos ou de outra origem não somem do CSV (todo o histórico), inclusive os "importado do Mobills"
- [ ] O lançamento com a marca de exclusão (`excluido_em`, ticket 34) fica fora da planilha, como em todas as leituras; o item acima fala do histórico, não do que o casal excluiu
- [ ] A coluna `pessoa` sai pelo nome (o `lancamentos.pessoa` guarda o `sub`; os nomes vêm de `PESSOAS`, `app/pessoas.py`), vazia para o conjunto, e `criado_por` e `alterado_por` também saem pelo nome; `fonte` (ticket 41) pode ser uma coluna a mais se o dono quiser distinguir o importado
- [ ] A consulta lê na mesma transação `REPEATABLE READ` de `exportar`
- [ ] Remover `TABELAS_DA_PLANILHA` e o ramo que devolve lista vazia quando faltam tabelas
- [ ] Verificações do projeto rodando e PR aberto para `main`
