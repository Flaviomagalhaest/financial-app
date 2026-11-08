# Importador do Mobills: conferir o total de cada fatura pelo PDF do banco

Type: task
Status: claimed
Blocked by: —
Skills: `grilling` (HITL: o dono diz como a coluna do PDF entra na aba `Faturas` e o que fazer com cartão sem PDF), `prototype` para ler os PDFs de um banco; depois `implement`, `tdd`
Modelo recomendado: Opus
Effort recomendado: medium
Issue: #570
Origem: [ticket 216](216-importador-do-mobills-decisao-para-grupos-ambiguos-e-parcelas-quebradas.md) (o dono tem os PDFs das faturas, que são o documento-verdade do valor pago; Q11 e Q14 do grilling mandam a conferência pelo PDF para um ticket à parte)

## O que construir

O dono guarda os PDFs das faturas fora do repositório (`C:\Users\flavi\OneDrive\Documents\F\Faturas cartão\`, uma pasta por cartão; dado real nunca entra no git). Hoje a aba `Faturas` compara o total do importador com um valor digitado pelo dono. A ideia é ler o total do PDF.

Fatos levantados no ticket 216:

- 64 PDFs: Credicard 18 (2025–26), Personnalite 38 (2023-08 a 2026-09), The One 2, VISA 6. Itaucard, Platinum e Samsung não têm PDF.
- 49 são protegidos por senha. O agente não usa senha: o dono extrai o texto (`pdftotext -layout -upw ...`) e o agente lê o `.txt`.
- O texto sai com `pdftotext -layout`; o total está em linhas como `Total desta fatura 120,58` e o vencimento em `Vencimento: 03/05/2026`.
- **O rótulo `AAAAMM` do Mobills não é o mês do vencimento em todo cartão**: no Credicard o PDF que vence em 05/2026 tem as compras de abril e casa com o `2026-04` do Mobills (fecha dia 27, vence dia 3); no Personnalite o vencimento é dia 1 e o mês coincide. Precisa de uma correspondência por cartão.

## Checklist

- [ ] Decisões do dono: onde o total do PDF entra (coluna na aba `Faturas`?), como o importador acha os PDFs (texto já extraído?) e o que fazer com cartão sem PDF
- [ ] Correspondência entre o rótulo do Mobills e o vencimento do PDF, por cartão
- [ ] Teste com um PDF fictício (texto) por layout de banco
- [ ] Rodar nos PDFs reais e gravar as faturas que não fecham
