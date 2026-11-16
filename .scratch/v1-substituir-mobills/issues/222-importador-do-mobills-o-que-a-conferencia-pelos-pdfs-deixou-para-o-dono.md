# Importador do Mobills: o que a conferência pelos PDFs deixou para o dono

Type: task
Status: claimed
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

- [x] Personnalite 2023-10 e 2023-11 explicadas (dono, 15/11: PDF vale; `descartar` em Faturas repetidas para Amaciante 32,99, Pão 18,75, Mercado 46,68 e Coisas de cozinha 149,62; as duas faturas fecham ao centavo)
- [ ] Centavos aceitos ou ajustados
- [ ] Faturas 2026-10 do The One (feita, 15/11) e do VISA exportadas de novo (VISA falta)
- [x] Apple Watch, Mercadolivre e Reembolso celular manu: ficam em branco (dono, 15/11). A parcela 1 do Apple Watch (R$ 190,60) já está na fatura 2025-06 do Personnalite; o R$ 190,43 do geral é o mesmo lançamento, e escolher o cartão contaria duas vezes. Parcelas 2 a 21 no The One (upgrade do Personnalite)
- [x] Lava louça e Mochilas já não aparecem em Parcelamentos sem cartão; Mercadolivre fica em branco

## Levantamento do agente (2026-11-15)

Importador rodado nos exports reais com `--faturas-pdf`: 6.412 lançamentos, 4.627 de 4.741 linhas casadas (97,6%). Diferenças da aba `Faturas` (importador − PDF): Personnalite 2023-09 0,04; 2023-10 51,74; 2023-11 196,30; 2024-12 −0,01; 2025-01 −0,01; 2025-09 −0,14; The One 2026-10 sem fatura no export.

- **Personnalite 2023-10** (PDF de 11/2023): `Amaciante` R$ 32,99 (24/10/2023) não aparece no PDF, e `Padaria` e `Pão` (22/10, R$ 18,75 cada) aparecem uma vez só no PDF. Hipótese: Amaciante + uma das duas de R$ 18,75 = 51,74. Confirmar no Mobills.
- **Personnalite 2023-11** (PDF de 12/2023): todos os valores existem no PDF, então não há lançamento ausente. Única soma de 1 a 3 lançamentos que dá 196,30: `Mercado/Alimentação` R$ 46,68 (19/11) + `Coisas de cozinha` R$ 149,62 (25/10); este último não está no PDF de 11/2023. Hipótese fraca, confirmar no Mobills.
- **Parcelamentos sem cartão** (aba, 47 linhas): `Apple Watch` 190,43 1/21 2025-06; `Mercadolivre` 14,63 1 a 3 de 3 (2026-10 a 2026-12); `Reembolso celular manu` 283,00 (1–3 e 5–6 de 6). Lava louça e Mochilas já não aparecem nessa aba na rodada atual: conferir no Mobills.
