# Ajuste de fatura na planilha e "passou" no ainda dá para gastar

Type: task
Status: ready-for-agent
Blocked by: —
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` nas telas
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #322
Origem: [ticket 94](94-conferir-as-regras-de-estorno-e-ajuste.md): decisões do dono sobre estorno, ajuste de fatura e partes da compra

## O que construir

A planilha de exportação passa a fechar com o total do mês do app, e o "ainda dá para gastar" diz quanto estourou em vez de parar em zero.

## Checklist

- [ ] Planilha (CSV de lançamentos): uma linha por ajuste de fatura diferente de zero, "Ajuste de fatura <cartão> <mês>", sem categoria, no mês da fatura
- [ ] "Ainda dá para gastar" negativo mostra "passou R$ X" (na Hoje e na aba Mês), no lugar de 0
- [ ] Testes; verificações do projeto e PR para `main`

## Notas

- Decisões Q13 e Q18 do ticket 94.
- O backup (zip de CSVs) não muda: o ajuste já vai na tabela `faturas`.
