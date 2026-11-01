# Favorito e sugestão com partes

Type: task
Status: ready-for-agent
Blocked by: 137
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` nas telas
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #329
Origem: [ticket 94](94-conferir-as-regras-de-estorno-e-ajuste.md): decisões do dono sobre estorno, ajuste de fatura e partes da compra

## O que construir

O favorito e a sugestão por descrição passam a levar as partes da compra.

## Checklist

- [ ] A identidade do lançamento inclui as partes (descrição, categorias, tags, pessoa e proporção)
- [ ] O favorito de compra com partes preenche as partes na proporção do último valor; mudar o valor redivide
- [ ] A sugestão por descrição oferece o pacote com partes
- [ ] Testes; verificações do projeto e PR para `main`

## Notas

- Decisão Q45 do ticket 94; ADR 0022.
- O 140 trouxe a conta da proporção: `redividir` em `backend/app/partes.py` e em `web/src/lancamentos/dinheiro.ts`, presas por `tabelas-de-teste/redivisao-das-partes.json`. O favorito pode dividir as partes pelo valor com ela.
