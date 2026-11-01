# Juntar tag leva também as tags da recorrência e do parcelamento

Type: task
Status: ready-for-agent
Blocked by: —
Skills: `implement`, `tdd`; apoio: `diagnosing-bugs` para confirmar o caso
Modelo recomendado: Sonnet
Effort recomendado: low
Issue: #361
Origem: [ticket 140](140-partes-na-recorrencia.md): lendo `juntar_tag` (`backend/app/classificacao.py`) para levar as tags das partes da regra

## O que construir

`POST /api/tags/{id}/juntar` move as tags dos lançamentos e das partes (da compra e da regra) para o destino e exclui a origem, mas não toca em `recorrencia_tags` nem em `parcelamento_tags`. A regra fica apontando para a tag excluída: some da leitura da regra (o `JOIN` com `tags` a perde) e os previstos ou parcelas que ela gerar depois levam um `tag_id` que não existe mais. Juntar categoria já leva as das regras; a tag deveria fazer o mesmo.

## Checklist

- [ ] Confirmar o caso com um teste de API (recorrência com a tag, juntar, ler a regra e gerar de novo)
- [ ] `juntar_tag` move `recorrencia_tags` e `parcelamento_tags` para o destino, sem repetir a que já estava lá
- [ ] Testes de API; verificações do projeto e PR para `main`
