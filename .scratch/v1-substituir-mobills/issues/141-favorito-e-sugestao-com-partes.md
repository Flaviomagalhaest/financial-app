# Favorito e sugestão com partes

Type: task
Status: resolved
Blocked by: 137
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` nas telas
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #329
Origem: [ticket 94](94-conferir-as-regras-de-estorno-e-ajuste.md): decisões do dono sobre estorno, ajuste de fatura e partes da compra

## O que construir

O favorito e a sugestão por descrição passam a levar as partes da compra.

## Checklist

- [x] A identidade do lançamento inclui as partes (descrição, categorias, tags, pessoa e proporção)
- [x] O favorito de compra com partes preenche as partes na proporção do último valor; mudar o valor redivide
- [x] A sugestão por descrição oferece o pacote com partes
- [x] Testes; verificações do projeto e PR para `main`

## Notas

- Decisão Q45 do ticket 94; ADR 0022.
- No merge com o 140, a divisão na proporção do app (`dividirNaProporcao`) passou para `web/src/lancamentos/dinheiro.ts`, junto do `redividir` da recorrência, e a tabela `tabelas-de-teste/redivisao-das-partes.json` prende as duas contas ao servidor.
