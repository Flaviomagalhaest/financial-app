# Partes na compra parcelada

Type: task
Status: claimed
Blocked by: 136, 137
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` nas telas
Modelo recomendado: Opus
Effort recomendado: high
Issue: #327
Origem: [ticket 94](94-conferir-as-regras-de-estorno-e-ajuste.md): decisões do dono sobre estorno, ajuste de fatura e partes da compra

## O que construir

A compra parcelada pode ter partes, guardadas como proporção e aplicadas a cada parcela.

## Checklist

- [ ] Cada parcela se divide pelas partes na proporção do total; os centavos vão para a maior parte (a primeira, no empate); o valor da parcela é o que vale
- [ ] Parcela com valor editado à mão se redivide na mesma proporção
- [ ] Mudar as partes numa parcela usa o alcance do ticket 136: "só esta" dá partes próprias à parcela; "esta e as próximas" e "todas" preservam as alteradas à mão
- [ ] Correção do parcelamento redivide as parcelas pelas partes
- [ ] Testes de API e de navegador; verificações do projeto e PR para `main`

## Notas

- Decisões Q27, Q33 a Q36 (revistas pela Q39) do ticket 94; ADR 0022.
