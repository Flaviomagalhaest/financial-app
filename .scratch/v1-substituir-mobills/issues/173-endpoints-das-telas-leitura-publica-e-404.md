# Endpoints das telas: leitura pública e 404 do parcelamento inexistente

Type: task
Status: claimed
Blocked by: —
Skills: `implement`, `tdd`
Modelo recomendado: Sonnet
Effort recomendado: low
Issue: #417
Origem: revisão do [ticket 165](165-telas-que-filtram-a-lista-leem-do-servidor.md) (PR #404), pontos que ficaram sem resolver.

## O que construir

`backend/app/lancamentos_das_telas.py` (fatura, Mês e parcelamento) faz duas coisas que a revisão apontou:

- importa `_todos` de `app.lancamentos`, que é privado, e `MES_EM_QUE_CONTA`. Dar a `_todos` um nome público (por exemplo `listar_lancamentos`) em `lancamentos.py`, usar o nome novo no módulo das telas e nos demais importadores, e conferir que a leitura só devolve lançamentos do casal (o escopo que `_todos` já aplica).
- `GET /api/parcelamentos/{id}/lancamentos` devolve 200 com lista vazia para um id que não existe, e o teste `test_parcelamento_que_nao_existe_devolve_lista_vazia` fixa isso. O aparelho guarda esse "vazio" como resposta válida da tela. Passar a devolver 404, como o resto da API faz com id inexistente, e o aparelho não guardar a resposta de erro (a tela do parcelamento já mostra "Parcelamento não encontrado").

## Checklist

- [ ] `_todos` com nome público; ninguém mais importa o privado
- [ ] 404 para parcelamento inexistente, com o teste do backend trocado
- [ ] Teste de navegador: a tela de um parcelamento que não existe diz "Parcelamento não encontrado" e não guarda lista vazia
- [ ] `openapi.json` e `web/src/api/schema.d.ts` regenerados
