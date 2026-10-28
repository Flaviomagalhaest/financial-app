# Categorias e tags: várias por lançamento e manutenção

Type: task
Status: resolved
Blocked by: 32
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` se mexer na interface
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #94
Origem: [spec da v1](../spec.md), etapa 2; histórias de usuário 14, 21, 152, 153, 154, 155, 156

## O que construir

O lançamento tem uma ou mais categorias e nenhuma ou várias tags, e o casal mantém essas listas ([ADR 0006](../../../docs/adr/0006-varias-categorias-e-um-item-do-planejamento.md)).

## Checklist

- [x] Listas planas de categorias separadas para despesa, receita e transferência; despesa e receita exigem ao menos uma categoria
- [x] Tags criáveis no próprio lançamento
- [x] Renomear reflete em todo o histórico; juntar move lançamentos, itens do planejamento e escolhas de item (quando existirem); arquivar tira das opções; excluir só sem lançamentos
- [x] Testes de API para cada operação
- [ ] Verificações do projeto rodando e PR aberto para `main`
