# Conferir as regras de fatura escolhidas no ticket 37

Type: grilling
Status: resolved
Blocked by: 37
Skills: `grilling`, `domain-modeling` (HITL: decisões do dono)
Modelo recomendado: Opus
Effort recomendado: medium
Issue: #165
Origem: [ticket 37](37-cartoes-e-faturas.md) e [ticket 38](38-pagamento-de-fatura.md) (o 37 com o [77](77-ligar-o-csv-de-planilha-ao-esquema-real.md), feito com ele): a spec e a [ADR 0003](../../../docs/adr/0003-compra-no-cartao-conta-no-mes-da-fatura.md) não dizem o que fazer nestes casos, e o ticket 37 escolheu um comportamento provisório para cada um (já em `backend/app/cartoes.py` e `backend/app/faturas.py`, com teste)

## O que decidir

Para cada regra abaixo, o dono confirma o comportamento provisório ou pede outro. Mudança vira ticket de implementação; o que ficar vai para o glossário ou para a ADR 0003.

## Decisões (31/10)

Grilling com o dono. Confirmadas como estão no código todas as regras abaixo, menos três, que mudam no [ticket 125](125-o-pagamento-quita-a-fatura.md) ([ADR 0021](../../../docs/adr/0021-o-pagamento-quita-a-fatura.md)):

- **Pagamento a mais**: não vira crédito; o app recusa o pagamento acima do devido (o casal nunca paga a mais de propósito).
- **Situação "paga" e saldo anterior**: o primeiro pagamento realizado de uma fatura fechada a deixa paga, qualquer que seja o valor, e a sobra (total menos o pago) vira saldo anterior da seguinte, em qualquer dia em que o pagamento for lançado. Sem pagamento a fatura continua fechada e devendo, e não passa saldo.
- **Pagar a seguinte com o saldo anterior dentro**: deixa de existir o caso de abril "fechada" e devendo depois de maio pago: abril já ficou paga quando recebeu o pagamento dela.

Novas: fatura paga não recebe mais pagamento, compra, troca, estorno nem acerto de datas (o app recusa e manda corrigir a fatura); a **correção de fatura** muda tudo de uma vez ao salvar e a fatura continua paga.

A ADR 0003 trocou "fatura fechada nunca muda" por "mudar o dia padrão nunca mexe em fatura fechada", com a compra esquecida caindo na fatura fechada da data dela se ela não estiver paga, e deixou explícito que o vencimento não decide o mês. Glossário: **Mês da fatura**, **Fatura paga**, **Correção de fatura**, **Saldo anterior**.

## Checklist

- [x] **Mudar o dia padrão sobrescreve as datas acertadas à mão** nas faturas abertas e futuras (a fatura do feriado volta para o novo padrão). Alternativa: manter as datas editadas à mão
- [x] **Fatura fechada recebe compra lançada depois**: a compra esquecida, lançada com a data antiga, cai na fatura fechada daquela data, porque o banco já a cobrou ali. "Fatura fechada nunca muda" vale só para a mudança do dia padrão
- [x] **Acertar as datas de uma fatura fechada** (o feriado só foi notado depois do fechamento) traz para ela as compras das abertas que agora cabem nela; as compras dela que ficariam de fora não saem
- [x] **Mudar o dia padrão para antes de hoje fecha a fatura atual na hora**: fecha em 25, hoje é 20/04 e o novo dia é 15 → a fatura de abril passa a fechar em 15/04 (já fechada), e as compras de 15/04 a 20/04 vão para maio. Alternativa: o novo dia vale a partir da fatura seguinte
- [x] **Trocar a regra "mês anterior ao fechamento"** recalcula as datas das faturas abertas pelo novo mês do fechamento, sem mudar o mês delas
- [x] **Vencimento padrão** cai no mês do fechamento se o dia vier depois do fechamento, senão no mês seguinte (fecha 25, vence 5 → 05 do mês seguinte; fecha 3, vence 10 → dia 10 do mesmo mês)
- [x] **Troca de fatura sem volta**: não há "voltar para a fatura que o app escolheria"; trocar para a fatura certa continua marcado como à mão (só trocar de cartão desfaz a marca)
- [x] **Trocar para a fatura que o app já escolheu não marca a troca**: o pedido não muda nada, então a próxima mudança de data escolhe a fatura de novo. Alternativa: marcar como à mão mesmo assim
- [x] **Cartão sem dia de fechamento** (os inativos do histórico) recusa a compra sem a fatura escolhida
- [x] **CSV de planilha** ([ticket 77](77-ligar-o-csv-de-planilha-ao-esquema-real.md), feito com o 37): a transferência sai numa linha só ("Corrente → Poupança", valor sem sinal), os nomes das colunas ficam sem acento (`descricao`, `situacao`) e a coluna `fonte` (importado do Mobills ou app) fica de fora. Alternativas: duas linhas por transferência (saída e entrada), cabeçalho com acento, coluna `fonte`
- [x] **Fatura fechada no próprio dia do fechamento** (`situacao: fechada` a partir dele), como a compra desse dia, que já vai para a seguinte
- [x] **Pagamento a mais que o devido** ([ticket 38](38-pagamento-de-fatura.md)): o excesso não vira crédito; o saldo anterior da fatura seguinte fica em zero e a fatura mostra `pago_centavos` maior que o total. Alternativa: saldo anterior negativo (crédito que abate a fatura seguinte)
- [x] **Só a fatura fechada passa o saldo anterior**: enquanto a fatura não fecha ela ainda recebe compras, então o que falta pagar dela não aparece na seguinte. Alternativa: mostrar uma estimativa na seguinte
- [x] **Saldo anterior pula meses sem fatura**: a fatura de um mês sem compra não nasce, e o que sobrou passa para a próxima fatura que existir
- [x] **Só pagamento realizado conta como pago**; o previsto (data futura) não quita nem mexe no saldo da conta
- [x] **Situação "paga"**: fatura fechada com o devido (saldo anterior mais compras) maior que zero e nada a pagar; fatura fechada de total zero fica "fechada"
- [x] **Pagar a fatura seguinte com o saldo anterior dentro**: o pagamento quita só a fatura que ele aponta. Pagar o total da fatura de maio (saldo anterior de abril mais compras) com `fatura_mes` de maio deixa abril "fechada" e devendo, sem contar em dobro. Alternativa: o pagamento abate primeiro a fatura mais antiga em aberto
