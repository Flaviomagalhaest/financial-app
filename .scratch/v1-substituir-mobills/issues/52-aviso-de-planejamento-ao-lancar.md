# Aviso de planejamento ao lançar

Type: task
Status: ready-for-agent
Blocked by: 51, 42
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` se mexer na interface
Modelo recomendado: Opus
Effort recomendado: high
Issue: #106
Origem: [spec da v1](../spec.md), etapa 4; histórias de usuário 25, 26, 27, 28, 29

## O que construir

A cada toque na tela de lançar, o casal vê o efeito no planejamento ("Mercado: 82% → 105% do planejado de out/26"), inclusive sem internet.

## Checklist

- [ ] Cálculo puro sobre os totais do mês e o lançamento em edição, compartilhado entre servidor e app e testado por tabela; sem internet roda sobre o cache e a fila
- [ ] Mostra quanto ainda dá para gastar ou quanto passa; em compra no cartão, a fatura e o mês que conta; "conta só no total do mês" quando nenhuma categoria tem item
- [ ] Com duas ou mais categorias com item, "Conta no planejamento em:" com a última escolha para aquele conjunto, trocável com um toque
- [ ] Sem internet, os totais vêm de `web/src/dados/` (ticket 33): a resposta guardada com a fila por cima, como `useLancamentos` faz com a lista
- [ ] Testes de tabela e de navegador
- [ ] Verificações do projeto rodando e PR aberto para `main`
