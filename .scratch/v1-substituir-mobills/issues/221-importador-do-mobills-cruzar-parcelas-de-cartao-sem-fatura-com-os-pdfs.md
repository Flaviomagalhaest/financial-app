# Importador do Mobills: cruzar as parcelas de cartão sem fatura com os PDFs

Type: task
Status: ready-for-agent
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

- [ ] Correspondência entre mês da parcela e fatura do PDF, por cartão (reaproveitar a do ticket 220, se já houver)
- [ ] Cruzar valor, mês e sufixo `NN/MM` das parcelas de mês faturado com os textos dos PDFs
- [ ] Listar as parcelas que ficaram na conta por falha, e as que o PDF confirma no cartão
- [ ] Gravar o resultado e o que o dono precisa decidir em `## Answer`