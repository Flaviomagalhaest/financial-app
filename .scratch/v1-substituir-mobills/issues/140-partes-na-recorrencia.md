# Partes na recorrência

Type: task
Status: ready-for-agent
Blocked by: 137
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` nas telas
Modelo recomendado: Opus
Effort recomendado: high
Issue: #328
Origem: [ticket 94](94-conferir-as-regras-de-estorno-e-ajuste.md): decisões do dono sobre estorno, ajuste de fatura e partes da compra

## O que construir

A despesa recorrente pode ter partes (ex.: um combo de celular e internet numa conta só), guardadas na regra como proporção.

## Checklist

- [ ] Cada ocorrência se divide pelas partes na proporção; centavos para a maior parte; o valor estimado do mês se redivide
- [ ] Mudar as partes: "só este" (editar o previsto) ou "daqui para frente", que não sobrescreve o previsto editado; a mudança vai pela fila (ADR 0020)
- [ ] O estorno é de uma parte de uma ocorrência
- [ ] Testes de API e de navegador; verificações do projeto e PR para `main`

## Notas

- Decisões Q38 e Q43 do ticket 94; ADR 0022.
