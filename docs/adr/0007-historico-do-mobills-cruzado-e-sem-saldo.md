---
status: accepted
---

# O histórico do Mobills entra pelo cruzamento do geral com as faturas e não mexe no saldo

O Mobills exporta as compras de cartão duas vezes: no export geral, sem cartão e na data do vencimento, mas com tags, `(n/total)` e situação; e nas faturas por cartão e mês, com o cartão e a data da compra, mas sem o resto. A importação casa cada linha de fatura com o seu par no geral (mês, descrição sem `(n/total)`, valor e categoria; 97,7% casaram) e grava a compra **uma vez só**, juntando o que cada lado tem. O que não casa vai para uma planilha de revisão. O histórico importado serve às estatísticas, ao planejamento e às comparações, mas **não mexe no saldo**: o saldo de cada conta parte de um saldo de abertura que o casal informa, porque o Mobills tinha uma conta só e o casal não registrava nele investimentos nem transferências.

## Considered Options

- **Geral + export "só cartão", com a data da compra digitada à mão** nas parceladas e na fatura vigente: marca o cartão, mas exige o input manual que o dono queria evitar e perde a data real no resto do histórico.
- **Só o geral**: todo o cartão ficaria na data do vencimento e sem cartão, e a visão de cartão do histórico não existiria.
- **Saldo reconstruído pela soma dos lançamentos**: daria um número sem sentido, porque o histórico não tem saldo inicial, investimentos nem transferências.

## Consequences

- Cada compra antiga no cartão ganha uma fatura com o mês da fatura do rótulo `AAAAMM` do arquivo (o mesmo mês do geral), já fechada e paga, sem datas de fechamento e vencimento e sem pagamento de fatura.
- A importação pode ser refeita até a virada. Na virada, o casal exporta o geral pela web (o celular não exporta previstos) e as faturas que faltam, incluindo a aberta.
- O total de cada mês importado é conferido pelo dono contra o total que o Mobills mostra, numa aba de conferência da planilha de revisão.
