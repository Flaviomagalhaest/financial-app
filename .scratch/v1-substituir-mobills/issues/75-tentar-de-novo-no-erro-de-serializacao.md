# Tentar de novo no erro de serialização do DSQL

Type: task
Status: resolved
Blocked by: 32
Skills: `implement`, `tdd`
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #141
Origem: revisão do [ticket 32](32-lancamento-simples-online.md): o [ADR 0009](../../../docs/adr/0009-aurora-dsql-em-sao-paulo.md) manda tratar o erro de serialização da concorrência otimista tentando de novo, e as rotas de `backend/app/lancamentos.py` ainda viram 500 nesse erro

## O que construir

As rotas que escrevem repetem a transação inteira algumas vezes quando o banco devolve erro de serialização (SQLSTATE 40001), antes de responder erro.

## Checklist

- [x] Ponto único de repetição (por exemplo em `app/banco.py`) usado pelas rotas de escrita
- [x] Teste que força o erro de serialização e confere que a rota termina bem na segunda tentativa
- [ ] Verificações do projeto rodando e PR aberto para `main`

## Notas da implementação

- `app.banco.em_transacao` refaz a transação inteira em conexão nova, até `TENTATIVAS_NA_SERIALIZACAO = 5` (valor provisório, sem espera entre tentativas) e usado por criar conta, criar categoria, criar/editar/excluir lançamento. Leituras seguem com `conectar`.
- Esgotadas as tentativas, a API responde 503 com `Retry-After: 1` (antes seria 500). Código e espera são escolhas minhas; o dono confirma ou muda.
- Só o POST de lançamento tem teste de retry; as outras rotas passam pelo mesmo ponto único.
