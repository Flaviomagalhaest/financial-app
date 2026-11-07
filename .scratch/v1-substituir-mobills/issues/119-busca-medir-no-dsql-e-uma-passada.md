# Busca: medir no Aurora DSQL real e ler a página numa passada só

Type: task
Status: resolved
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
- [x] 3ª medição com `--explicar`: o comando que lê os 50 lançamentos da página levou 2,9 s no período 2024 e 1,0 s na última página. Causa no gerador, não no app: as 20 mil parcelas tinham a mesma conta e o mesmo valor, e o `_REPETIDO_DE` (por linha lida, pelo índice `conta_id, valor_centavos`) varria cerca de 20 mil entradas. O gerador agora espalha conta e valor das parcelas
- [x] Totais e página saem de uma consulta só (`WITH base AS MATERIALIZED`): uma passada em vez de duas. No Postgres local (120 mil): sem filtro 0,25 s, texto 0,33 s, categoria + tag 0,69 s
- [x] 4ª medição no DSQL (consulta única, parcelas espalhadas, 120 mil lançamentos, rodada pelo dono): sem filtro 1ª página 0,63 s; última página 0,93 s; texto 0,68 a 0,70 s; período 2024 0,71 s; valor 100 a 200 0,54 s; texto + período + situação 0,68 s; categoria + tag 0,88 s; **ordem por valor 1,22 s** (acima da meta de 1 s). Os outros nove cenários cumprem a meta; a última página (0,93 s) e categoria + tag (0,88 s) têm pouca folga
- [x] O dono aceita a ordem por valor em 1,22 s (decidido na sessão do ticket): é a ordem menos usada e o resto da meta está cumprido
- [x] Juntar totais e página numa consulta só (`WITH ... AS MATERIALIZED`; a versão com funções de janela quase não ganhou, porque perde o top-N do `ORDER BY ... LIMIT`)
- [x] Verificações do projeto rodando e PR aberto para `main` (PR 511)

## Resolução

Meta de 1 s com 120 mil lançamentos no DSQL: cumprida em nove dos dez cenários medidos; a ordem por valor ficou em 1,22 s e foi aceita pelo dono. Correções: a data da linha vem de um `LEFT JOIN` em `parcelamentos` (era uma subconsulta por lançamento, 14 s) e totais e página saem de uma consulta só (`WITH base AS MATERIALIZED`).

Fica sem folga: a última página (0,93 s) e categoria + tag (0,88 s). Se o histórico crescer ou a busca ficar lenta, rodar `uv run python medir_busca.py --explicar` num DSQL de teste (o script apaga as tabelas do schema `public`) e olhar o plano.
