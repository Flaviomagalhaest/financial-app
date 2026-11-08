# Importador do Mobills: cruzar as parcelas de cartão sem fatura com os PDFs

Type: task
Status: resolved
Blocked by: —
Skills: `implement`, `tdd`; `run` para rodar nos dados reais
Modelo recomendado: Opus
Effort recomendado: medium
Issue: #576
Origem: [ticket 218](218-importador-do-mobills-premissas-que-o-export-real-nao-confirmou.md) (a contagem das parcelas de cartão sem fatura saiu dos XLSX; o cruzamento só pelo valor nos PDFs foi fraco)

## O que construir

Dizer, para cada parcela de parcelamento sem cartão em mês que já tem fatura, se ela está na fatura em PDF do banco. Assim se separa a parcela que ficou na conta por falha da que é de mês futuro ou é pagamento da conta.

Fatos do ticket 218:

- A aba `Parcelamentos sem cartão` tem 134 parcelamentos. Tirando os pagamentos da conta que o dono apontou (Aluguel, Buenos Aires, Imposto de renda/IR, Lavanderia, buffet e decoração do casamento, PECE-Poli, Reembolso vistoria carro, Samuel Fotografia, Seguro residencial, Título de capitalização), sobram 31 parcelamentos com 81 parcelas. `Reembolso celular manu` talvez seja reembolso e não cartão.
- Quase todas as parcelas são de 2026-10 a 2026-12, meses sem fatura fechada: `sem fatura` ali é esperado. O que importa são as de mês já faturado (Apple Watch 2025-06 e outras).
- O nome na fatura não bate com a descrição (`Airbnb` vira `AIRBNB PAGAM*AIRBN01/06`) e valores pequenos coincidem por acaso. O cruzamento tem de usar **valor + mês da fatura + sufixo `NN/MM`**, não só o valor.
- Os textos extraídos dos PDFs (`pdftotext -layout`) ficam fora do repositório, em `C:\Users\flavi\OneDrive\Documents\F\Faturas cartão\_txt\<cartão>\`. Dado real nunca entra no git. O rótulo de mês do Mobills nem sempre é o mês do vencimento (veja o [ticket 220](220-importador-do-mobills-conferir-faturas-pelo-pdf-do-banco.md)).

## Checklist

- [x] Correspondência entre mês da parcela e fatura do PDF, por cartão (reaproveitar a do ticket 220, se já houver)
- [x] Cruzar valor, mês e sufixo `NN/MM` das parcelas de mês faturado com os textos dos PDFs
- [x] Listar as parcelas que ficaram na conta por falha, e as que o PDF confirma no cartão
- [x] Gravar o resultado e o que o dono precisa decidir em `## Answer`

## Answer

Cruzamento feito uma vez, fora do importador, sobre a planilha de revisão da rodada de 2026-11-08 e os textos `-raw` dos 64 PDFs. A parcela `k de N` do mês `M` foi procurada nos PDFs que vencem em `M + 1` (a correspondência do [ticket 220](220-importador-do-mobills-conferir-faturas-pelo-pdf-do-banco.md)), por linha com sufixo `k/N` e valor a até R$ 0,10. O valor do banco difere alguns centavos do do Mobills (Obras 1.832,11 × `GilsonFelixGesso 10/18 1.832,13`), daí a tolerância.

Tirando os pagamentos da conta, sobram os parcelamentos do ticket 218 (mais Buenos aires e Lanvanderia, com grafia que a lista de nomes não pegou):

- **Parcelas de 2026-10 a 2026-12**: estão todas no **The One**. O PDF que vence em 11/2026 confirma a parcela de 2026-10, com o mesmo número e valor, em 28 parcelamentos (Airbnb, Amazon ×3, Blackfriday amazon, Buenos aires, Casacos viagem, Celular manu, Coisas casa, Concerto carro, Cooktop, Creme cabelo, Espelho, Figurinhas, Geladeira, Lanvanderia, Livro sogrinha, Obras apartamento, Panelas, as duas Passagens, Presente, Secador, Shampoo e cremes, Tomadas, Tênis, Tênis manu). Em Lava louça, Mercadolivre e Mochilas o número bate e o valor fica a R$ 0,12–0,20. Elas ficaram sem cartão porque **o export do Mobills do The One para em `202609`**, não por falha: o PDF de 2026-10 já existe. As de 2026-11 e 2026-12 são de mês ainda sem fatura fechada.
- **Apple Watch 1/21 de 2025-06**: a única parcela de mês já exportado que **ficou na conta por falha**. O PDF do Personnalite que vence em 07/2025 tem `MoG 01/21` de R$ 190,60 (o Mobills diz R$ 190,43); as parcelas seguintes estão nas faturas do Personnalite e depois nas do The One.
- **Reembolso celular manu** (R$ 283,00): nenhum PDF tem esse valor, então é da conta.

As decisões do dono (exportar de novo a fatura 2026-10 do The One, escolher o cartão do Apple Watch, confirmar as três de valor próximo) estão no [ticket 222](222-importador-do-mobills-o-que-a-conferencia-pelos-pdfs-deixou-para-o-dono.md).