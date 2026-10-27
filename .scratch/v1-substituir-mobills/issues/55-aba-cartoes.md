# Aba Cartões

Type: task
Status: ready-for-agent
Blocked by: 37
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` se mexer na interface
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #109
Origem: [spec da v1](../spec.md), etapa 5; histórias de usuário 129, 130

## O que construir

O casal vê o que deve em cada cartão e confere a fatura com o app do banco.

## Checklist

- [ ] Uma linha por cartão com a fatura atual, a próxima e a anterior e a situação (aberta, fechada ou paga)
- [ ] Detalhe da fatura com as compras agrupadas por dia e filtro por categoria e tag; atalho "ver os lançamentos" (liga à busca quando ela existir)
- [ ] Testes de API e de navegador
- [ ] Verificações do projeto rodando e PR aberto para `main`
