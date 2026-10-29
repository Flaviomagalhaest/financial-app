# Item em que o lançamento conta e lista "a escolher"

Type: task
Status: claimed
Blocked by: 49
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` se mexer na interface
Modelo recomendado: Opus
Effort recomendado: high
Issue: #105
Origem: [spec da v1](../spec.md), etapa 4; histórias de usuário 114, 115, 116, 111

## O que construir

Cada lançamento conta em no máximo um item do planejamento, sem contar o mesmo dinheiro duas vezes ([ADR 0006](../../../docs/adr/0006-varias-categorias-e-um-item-do-planejamento.md)).

## Checklist

- [ ] Conta automaticamente quando só uma das categorias tem item; escolha explícita nunca muda sozinha
- [ ] Ambiguidade que surge depois (item criado no meio do mês, planejamento copiado, categorias editadas) mantém o item atual e entra na lista "a escolher"
- [ ] Recorrência e parcelamento guardam a escolha e os previstos já nascem com ela
- [ ] Testes de API para cada caminho
- [ ] Juntar categorias (`POST /api/categorias/{id}/juntar`) também move as escolhas de item, e a leitura do planejamento (`GET /api/planejamento/{mes}`, ticket 49) passa a contar o lançamento com mais de uma categoria com item no item escolhido; hoje ele não conta em nenhum
- [ ] Verificações do projeto rodando e PR aberto para `main`
