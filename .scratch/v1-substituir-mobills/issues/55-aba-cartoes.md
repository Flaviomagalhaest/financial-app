# Aba Cartões

Type: task
Status: resolved
Blocked by: 37
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` se mexer na interface
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #109
Origem: [spec da v1](../spec.md), etapa 5; histórias de usuário 129, 130

## O que construir

O casal vê o que deve em cada cartão e confere a fatura com o app do banco.

## Checklist

- [x] Uma linha por cartão com a fatura atual, a próxima e a anterior e a situação (aberta, fechada ou paga)
- [x] Detalhe da fatura com as compras agrupadas por dia e filtro por categoria e tag; atalho "ver os lançamentos" (por ora leva ao histórico; liga à busca no ticket 59)
- [x] Testes de API e de navegador
- [x] Lê `GET /api/cartoes` e `GET /api/cartoes/{id}/faturas` (ticket 37); a fatura atual é a primeira `aberta`. Os totais por fatura já vêm da API (`total_centavos`, `a_pagar_centavos`); o detalhe agrupa os lançamentos pelo `mes` e pelo cartão (com os adicionais)
- [x] Verificações do projeto rodando e PR aberto para `main`
