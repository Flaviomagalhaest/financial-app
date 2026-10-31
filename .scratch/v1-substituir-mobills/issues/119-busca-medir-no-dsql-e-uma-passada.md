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

- [ ] O dono fixa a meta de resposta da busca (sugestão: até 1 s com o histórico inteiro)
- [ ] Rodar `backend/medir_busca.py` contra um DSQL de teste (o script apaga o schema `public`) e anotar os tempos aqui
- [ ] Se passar da meta, juntar totais e página numa consulta só (`WITH ... AS MATERIALIZED`; a versão com funções de janela quase não ganhou, porque perde o top-N do `ORDER BY ... LIMIT`)
- [ ] Verificações do projeto rodando e PR aberto para `main`
