# Busca: medir no Aurora DSQL real e ler a página numa passada só

Type: task
Status: ready-for-human
Blocked by: 112
Skills: `run`, `implement`; HITL (precisa do DSQL do dono)
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #256
Origem: [ticket 112](112-busca-desempenho-e-indice.md) (a medição foi num Postgres 16 local, não no DSQL)

## O que construir

O [ticket 112](112-busca-desempenho-e-indice.md) mediu a busca com 120 mil lançamentos num Postgres local: de 0,6 s (texto) a 1,7 s (período + texto + situação), das quais cerca de metade em cada uma das duas passadas sobre o histórico (totais e página). Não existe meta de resposta escrita no mapa nem na spec, e o DSQL não foi medido.

## Checklist

- [x] O dono fixa a meta de resposta da busca: até 1 s com o histórico inteiro (decidido na sessão do ticket)
- [x] `backend/medir_busca.py` ajustado para o DSQL: gera em lotes de 2.500 linhas (limite de 3.000 por transação, ADR 0009) e conecta por `DSQL_ENDPOINT` (token IAM). Conferido num Postgres local; `DROP SCHEMA public CASCADE` e `ANALYZE` no DSQL só se confirmam na primeira execução
- [x] Rodar `backend/medir_busca.py` contra um DSQL de teste (o script apaga o schema `public`) e anotar os tempos aqui. Passo a passo: criar cluster de teste em `sa-east-1`; `export AWS_REGION=sa-east-1 DSQL_ENDPOINT=<endpoint>`; `cd backend && uv sync && uv run python medir_busca.py`; apagar o cluster depois. Atenção ao cenário "categoria + tag", o mais lento no Postgres local com 24 mil lançamentos (cerca de 0,6 s)
- [x] 1ª medição no DSQL (120 mil lançamentos, rodada pelo dono): sem filtro 14,5 s; período 2024 23,1 s; texto + período + situação 20,0 s; valor 14,0 s; ordem por valor 13,9 s; texto 1,2 a 1,5 s; categoria + tag 1,6 s. Estourou a meta (1 s) em tudo, menos nos de texto
- [x] Causa: `_data_da_linha` era uma subconsulta correlacionada em `parcelamentos` por lançamento (no `SELECT` e em cada filtro de período), cerca de 70 µs cada no DSQL, 100 mil vezes por passada. Trocada por um `LEFT JOIN` (hash join). No Postgres local, sem filtro foi de 1,7 s para 0,36 s e período 2024 para 0,14 s
- [x] 2ª medição no DSQL, com o join (a busca ficou cerca de 14 vezes mais rápida): sem filtro 1ª página 1,0 s; última página 2,3 s; texto 1,2 a 1,3 s; período 2024 3,9 s; valor 1,0 s; ordem por valor 1,0 s; texto + período + situação 1,3 s; categoria + tag 1,6 s. Ler `lancamentos` inteiro custa 220 ms por passada no DSQL (o piso), então as duas passadas já dão cerca de 1 s. Os totais do período levam 0,34 s, logo os outros 3,5 s estão na página ou nos comandos depois dela
- [ ] Rodar de novo com `--explicar` (agora mostra o tempo de cada comando e o plano da página) e anotar aqui; com isso decidir a consulta única (uma passada só tira cerca de 0,5 s) e o que fazer com período, última página e categoria + tag
- [ ] Se passar da meta, juntar totais e página numa consulta só (`WITH ... AS MATERIALIZED`; a versão com funções de janela quase não ganhou, porque perde o top-N do `ORDER BY ... LIMIT`)
- [ ] Verificações do projeto rodando e PR aberto para `main`
