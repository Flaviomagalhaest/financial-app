# Edição em lote e desfazer

Type: task
Status: claimed
Blocked by: 59, 51
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` se mexer na interface
Modelo recomendado: Opus
Effort recomendado: high
Issue: #115
Origem: [spec da v1](../spec.md), etapa 5; histórias de usuário 147, 148, 149, 150, 151

## O que construir

O casal acerta o histórico importado trocando categorias e tags de muitos lançamentos de uma vez.

## Checklist

- [ ] Marcar lançamentos ou todos do resultado; acrescentar, remover, trocar ou substituir categorias e tags; selecionar parcelada seleciona o parcelamento todo, com a contagem
- [ ] Prévia (quantos mudam, os 5 primeiros antes e depois, quantos já estão como pedido, quantos trocam de item do planejamento); tudo ou nada; recusa lote que deixaria despesa ou receita sem categoria
- [ ] Desfazer por 30 dias, pulando e avisando o que outra pessoa mudou depois; só com internet
- [ ] Testes de API
- [ ] Verificações do projeto rodando e PR aberto para `main`
