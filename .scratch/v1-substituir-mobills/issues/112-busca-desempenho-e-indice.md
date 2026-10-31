# Busca: medir com o histórico desde 2019 e decidir o índice

Type: task
Status: resolved
Blocked by: 59
Skills: `implement`, `tdd`; apoio: `research` para o que o DSQL aceita de índice
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #230
Origem: [ticket 59](59-busca.md); o [ticket 24](24-busca-e-filtros-salvos.md) deixou "o índice de busca no servidor" para a spec, e a spec não o fixou

## O que construir

A busca (`POST /api/busca`, `backend/app/busca.py`) só foi exercitada com os poucos lançamentos dos testes. O texto livre compara `lower(translate(descricao, ...)) LIKE '%texto%'`, que não usa índice, e cada pedido roda a consulta duas vezes (os totais e a página), com subconsultas por lançamento (categorias, tags, data do parcelamento). Com o histórico do Mobills desde 2019 no Aurora DSQL, isso precisa ser medido.

## Checklist

- [x] Gerar um banco com o volume do histórico real (o importador do Mobills ou um gerador fictício com a mesma ordem de grandeza) e medir a busca sem filtro, com texto, com filtros e na última página
- [x] Se passar da meta de resposta das telas, propor o índice (ou coluna normalizada da descrição) que o DSQL aceita (`CREATE INDEX ASYNC`, sem extensão `pg_trgm`/`unaccent`) e registrar a decisão
- [x] Testes de API seguem passando
- [x] Verificações do projeto rodando e PR aberto para `main`

## Resultado

Medido com `backend/medir_busca.py` (120 mil lançamentos desde 2019: 100 mil avulsos, 4 mil parcelamentos de 5 parcelas, 4 contas, 40 categorias, 15 tags; 95% com `fonte = 'mobills'`) em Postgres 16 local, mediana de 5 execuções. **Não é o DSQL**: ver [ticket 119](119-busca-medir-no-dsql-e-uma-passada.md).

| Cenário | Antes | Depois |
|---|---|---|
| sem filtro, 1ª página | 1,07 s | 1,13 s |
| sem filtro, última página | 1,87 s | 1,13 s |
| texto | 0,6 s | 0,6 s |
| período 2024 | 1,57 s | 1,56 s |
| texto + período + situação | 1,62 s | 1,68 s |
| categoria + tag | 0,74 s | 0,03 s |

- **Índice de texto: descartado.** O filtro é `LIKE '%texto%'` (no meio da palavra); coluna normalizada com btree só ajudaria prefixo, e o DSQL não tem `pg_trgm`. Ler as 120 mil linhas é inerente, e os totais precisam delas de qualquer forma.
- **O gargalo real era outro**: `_REPETIDO_DE` ("Parece repetido", em `app/lancamentos.py`) varre `lancamentos` para cada lançamento lido que não veio do Mobills, e toda leitura de lista paga isso (busca, Mês, Histórico). Migration `0051_lancamentos_por_conta_e_valor.sql` (`CREATE INDEX ASYNC` em `conta_id, valor_centavos`) derrubou a última página e a categoria + tag.
- Sobra a agregação do histórico inteiro, rodada duas vezes (totais e página). Uma versão com funções de janela quase não ganhou e foi descartada; o resto vai para o [ticket 119](119-busca-medir-no-dsql-e-uma-passada.md).
