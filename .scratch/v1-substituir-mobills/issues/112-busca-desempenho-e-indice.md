# Busca: medir com o histórico desde 2019 e decidir o índice

Type: task
Status: ready-for-agent
Blocked by: 59
Skills: `implement`, `tdd`; apoio: `research` para o que o DSQL aceita de índice
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #230
Origem: [ticket 59](59-busca.md); o [ticket 24](24-busca-e-filtros-salvos.md) deixou "o índice de busca no servidor" para a spec, e a spec não o fixou

## O que construir

A busca (`POST /api/busca`, `backend/app/busca.py`) só foi exercitada com os poucos lançamentos dos testes. O texto livre compara `lower(translate(descricao, ...)) LIKE '%texto%'`, que não usa índice, e cada pedido roda a consulta duas vezes (os totais e a página), com subconsultas por lançamento (categorias, tags, data do parcelamento). Com o histórico do Mobills desde 2019 no Aurora DSQL, isso precisa ser medido.

## Checklist

- [ ] Gerar um banco com o volume do histórico real (o importador do Mobills ou um gerador fictício com a mesma ordem de grandeza) e medir a busca sem filtro, com texto, com filtros e na última página
- [ ] Se passar da meta de resposta das telas, propor o índice (ou coluna normalizada da descrição) que o DSQL aceita (`CREATE INDEX ASYNC`, sem extensão `pg_trgm`/`unaccent`) e registrar a decisão
- [ ] Testes de API seguem passando
- [ ] Verificações do projeto rodando e PR aberto para `main`
