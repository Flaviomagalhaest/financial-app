# Tentar de novo no erro de serialização do DSQL

Type: task
Status: open
Blocked by: 32
Skills: `implement`, `tdd`
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #141
Origem: revisão do [ticket 32](32-lancamento-simples-online.md): o [ADR 0009](../../../docs/adr/0009-aurora-dsql-em-sao-paulo.md) manda tratar o erro de serialização da concorrência otimista tentando de novo, e as rotas de `backend/app/lancamentos.py` ainda viram 500 nesse erro

## O que construir

As rotas que escrevem repetem a transação inteira algumas vezes quando o banco devolve erro de serialização (SQLSTATE 40001), antes de responder erro.

## Checklist

- [ ] Ponto único de repetição (por exemplo em `app/banco.py`) usado pelas rotas de escrita
- [ ] Teste que força o erro de serialização e confere que a rota termina bem na segunda tentativa
- [ ] Verificações do projeto rodando e PR aberto para `main`
