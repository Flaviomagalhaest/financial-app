# Finanças do casal

App de finanças pessoais do Flávio e da esposa: registra o dinheiro que entra e sai, os compromissos futuros e o planejamento do mês.

## Language

### Lançamentos

**Lançamento**:
Registro de um valor que entra ou sai do dinheiro do casal, ou que vai entrar ou sair, com data, descrição e tags.
_Avoid_: transação, movimentação

**Despesa**:
Lançamento de dinheiro que sai.
_Avoid_: gasto, custo, saída

**Receita**:
Lançamento de dinheiro que entra.
_Avoid_: entrada, ganho

**Previsto**:
Situação do lançamento que ainda não aconteceu (a parcela que vem, o salário do mês que vem); não mexe no saldo da conta.
_Avoid_: pendente, agendado, compromisso

**Realizado**:
Situação do lançamento que já aconteceu; só ele mexe no saldo da conta.
_Avoid_: efetivado, pago, confirmado

**Tag**:
Rótulo livre que classifica um lançamento; um lançamento pode ter várias ao mesmo tempo (ex.: "família" e "alimentação").
_Avoid_: etiqueta, marcador

**Tag de pessoa**:
Tag com o nome do Flávio ou da esposa, que diz de quem é o lançamento; cada lançamento tem no máximo uma.
_Avoid_: dono, responsável, quem gastou

**Conjunto**:
Lançamento sem tag de pessoa: é do casal (mercado, internet, gasolina, rendimento da poupança do casal).
_Avoid_: compartilhado, comum

### Futuro

**Recorrência**:
Regra que gera um lançamento previsto a cada N semanas ou N meses, com ou sem fim (o salário, a conta de luz, o seguro anual); não é um lançamento.
_Avoid_: repetição, fixo, assinatura

### Planejamento

**Planejamento**:
O quanto o casal se propõe a gastar num mês, item a item; não é lançamento e não mexe em saldo.
_Avoid_: orçamento, meta

**Item do planejamento**:
Uma linha do planejamento do mês, com um valor (ex.: R$ 1.000 em alimentação), comparada com os lançamentos realizados e previstos do mês.
_Avoid_: teto, limite, meta

### Contas e cartões

**Fatura**:
As compras de um cartão entre dois fechamentos, pagas de uma vez no vencimento.

**Fechamento**:
Data em que a fatura deixa de receber compras; uma compra feita no próprio dia do fechamento já vai para a fatura seguinte. Cada fatura tem o seu, que nasce do dia de fechamento padrão do cartão.

**Vencimento**:
Data limite para pagar a fatura. Cada fatura tem o seu, que nasce do dia de vencimento padrão do cartão.
_Avoid_: data de pagamento (o pagamento pode ser feito antes ou depois)

**Mês da fatura**:
Mês em que a fatura e cada compra dela contam no planejamento, nas tags e no resumo: o mês do fechamento, ou o anterior se o cartão for configurado assim. Cada cartão tem uma fatura por mês.
_Avoid_: competência, mês de referência

**Saldo anterior**:
Parte de uma fatura que não foi paga e passa para a fatura seguinte; não é compra nova e não conta de novo.
_Avoid_: rotativo (o rotativo é o crédito que gera juros sobre o saldo anterior)

**Estorno**:
Crédito de uma compra devolvida, que aparece numa fatura posterior ligado à compra original e com as mesmas tags.
_Avoid_: reembolso, devolução

**Transferência**:
Dinheiro que passa de uma conta do casal para outra; não é entrada nem saída do dinheiro do casal.

**Pagamento de fatura**:
Transferência de uma conta para um cartão que quita a fatura; não conta como saída, porque as compras da fatura já são lançamentos.
