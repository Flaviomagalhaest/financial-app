# Importador do Mobills: o que a conferência pelos PDFs deixou para o dono

Type: task
Status: ready-for-human
Blocked by: —
Skills: `run` (HITL: só o dono tem o Mobills e sabe o que aconteceu nas faturas)
Modelo recomendado: Sonnet
Effort recomendado: low
Issue: #577
Origem: [ticket 220](220-importador-do-mobills-conferir-faturas-pelo-pdf-do-banco.md) e [ticket 221](221-importador-do-mobills-cruzar-parcelas-de-cartao-sem-fatura-com-os-pdfs.md) (a conferência pelos PDFs fechou 56 de 63 faturas e achou no cartão quase todas as parcelas sem cartão; o resto depende do dono)

## O que fazer

Rodar o importador com os textos das faturas (o `## Answer` do ticket 220 tem o comando) e decidir:

- **Personnalite 2023-10 e 2023-11**: o importador soma R$ 51,74 e R$ 196,30 a mais que o PDF (que vence em 11/2023 e 12/2023). O texto desses PDFs antigos não sai linha a linha no `-raw`, então a compra que sobra não foi achada sozinha. Conferir no Mobills e no PDF qual lançamento não é dessas faturas.
- **Diferenças de centavos** (Personnalite 2023-09 R$ 0,04, 2024-12 e 2025-01 R$ 0,01, 2025-09 R$ 0,14): arredondamento das parcelas no Mobills. Aceitar ou acertar com `Reajuste de fatura`.
- **The One 2026-10 e VISA 2026-10**: o PDF já existe (vence 11/2026), mas o export do Mobills não tem essas faturas (o The One só tem `202609`). Exportar de novo a fatura 2026-10 dos dois cartões. Isso também tira da aba `Parcelamentos sem cartão` as parcelas de 2026-10 que o ticket 221 achou no PDF do The One.
- **Apple Watch 1/21 de 2025-06**: o PDF do Personnalite que vence em 07/2025 tem `MoG 01/21` de R$ 190,60 (o Mobills diz R$ 190,43, sem cartão). Escolher `Personnalite Black Pontos` em `Cartão (escolha)`.
- **Reembolso celular manu** (R$ 283,00, 1–3 e 5–6 de 6, 2025-10 a 2026-03): nenhum PDF tem esse valor, então é da conta, não do cartão. Deixar em branco.
- **Lava louça 6/21, Mercadolivre 1/3 e Mochilas 2/3** (2026-10): o PDF do The One tem parcela com o mesmo número e valor próximo (`SAMSUNG NO ITAU 06/21` R$ 204,40; `MERCADO*MERCADOLIV01/03` R$ 14,51; `Shopee*BREVANO MAX02/03` R$ 72,20), a mais de R$ 0,10 do Mobills. Confirmar.

## Checklist

- [ ] Personnalite 2023-10 e 2023-11 explicadas
- [ ] Centavos aceitos ou ajustados
- [ ] Faturas 2026-10 do The One e do VISA exportadas de novo
- [ ] `Cartão (escolha)` do Apple Watch preenchido
- [ ] Lava louça, Mercadolivre e Mochilas confirmados
