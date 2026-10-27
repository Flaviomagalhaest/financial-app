# Estorno, ajuste de fatura e compra cancelada

Type: task
Status: ready-for-agent
Blocked by: 37
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` se mexer na interface
Modelo recomendado: Sonnet
Effort recomendado: high
Issue: #93
Origem: [spec da v1](../spec.md), etapa 2; histórias de usuário 82, 83, 84, 85

## O que construir

O casal acerta uma fatura que não bate: cancela, estorna ou ajusta, sem inventar categoria ([ADR 0008](../../../docs/adr/0008-ajuste-de-fatura-fica-na-fatura.md)).

## Checklist

- [ ] Compra cancelada antes do fechamento some de tudo
- [ ] Estorno ligado ao lançamento original, com as mesmas categorias e tags, na fatura em que aparece, diminuindo o total da tag naquele mês
- [ ] Ajuste de fatura conta no total da fatura, nas despesas do mês, no "ainda dá para gastar" e no fechamento do mês, mas não em categoria, tag nem item do planejamento
- [ ] Testes de API com exemplos concretos
- [ ] Verificações do projeto rodando e PR aberto para `main`
