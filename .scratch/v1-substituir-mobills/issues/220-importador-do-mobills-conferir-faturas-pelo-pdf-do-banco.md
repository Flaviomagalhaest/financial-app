# Importador do Mobills: conferir o total de cada fatura pelo PDF do banco

Type: task
Status: resolved
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

- [x] Decisões do dono: onde o total do PDF entra (coluna na aba `Faturas`?), como o importador acha os PDFs (texto já extraído?) e o que fazer com cartão sem PDF
- [x] Correspondência entre o rótulo do Mobills e o vencimento do PDF, por cartão
- [x] Teste com um PDF fictício (texto) por layout de banco
- [x] Rodar nos PDFs reais e gravar as faturas que não fecham

## Answer

**Decisões do dono (2026-11-08):**

- O total do PDF **preenche a coluna `Mobills`** da aba `Faturas` quando ela está em branco; sem colunas novas. O valor que o dono digitar vale mais que o do PDF.
- O importador lê **os `.txt` já extraídos**, pela opção `--faturas-pdf <pasta>`; não abre PDF nem usa senha.
- As subpastas dos textos têm **o nome do cartão no Mobills** (`Credicard Black`, `Personnalite Black Pontos`, `The One`, `VISA Infinite`). As pastas de `_txt` foram renomeadas assim; as dos PDFs ficaram como estavam.
- Fatura sem PDF fica com a coluna em branco, sem aviso.

**Correspondência**: nos quatro cartões o rótulo `AAAAMM` do Mobills é **o mês anterior ao do vencimento** do PDF. Dos 64 PDFs, 62 têm a fatura exportada pelo Mobills (o The One e o VISA de 2026-10 não têm); por esse mês, 56 delas fecham ao centavo, contra 0 a 3 por cartão pelo próprio mês do vencimento. O Personnalite também segue essa regra (vence dia 1, e o PDF de 06/2025 é o `2025-05`), diferente do que o ticket supunha.

**Extração**: o texto tem de sair com `pdftotext -raw -enc UTF-8`. No `-layout` o valor de outra coluna cai na linha do total (o VISA de 06/2026 saía `0,00` em vez de `129,55`). Os `.txt` de `_txt` foram refeitos em `-raw`. Texto sem vencimento ou sem `Total desta fatura`, dois textos para o mesmo mês e subpasta sem cartão com esse nome viram aviso. O total do PDF fica gravado na coluna e volta como digitado na rodada seguinte: quando ele difere do texto atual (texto refeito ou valor digitado pelo dono), sai um aviso, e para usar o do PDF basta apagar a célula.

```
uv run python -m app.mobills <geral> <faturas> <revisao.xlsx> --faturas-pdf "C:\Users\flavi\OneDrive\Documents\F\Faturas cartão\_txt"
```

**Rodada nos dados reais**: 56 das 62 faturas exportadas com PDF fecham ao centavo. A aba também mostra o The One 2026-10, que só existe por causa dos parcelamentos. As que não fecham (importador − PDF):

| Cartão | Mês | Diferença |
|---|---|---|
| Personnalite | 2023-09 | 0,04 |
| Personnalite | 2023-10 | 51,74 |
| Personnalite | 2023-11 | 196,30 |
| Personnalite | 2024-12 | −0,01 |
| Personnalite | 2025-01 | −0,01 |
| Personnalite | 2025-09 | −0,14 |
| The One | 2026-10 | −19.636,04 (o Mobills não exportou esta fatura) |

O que o dono precisa fazer com elas está no [ticket 222](222-importador-do-mobills-o-que-a-conferencia-pelos-pdfs-deixou-para-o-dono.md).
