# Finanças do casal

App de finanças pessoais do Flávio e da esposa: registra o dinheiro que entra e sai, os compromissos futuros e o planejamento do mês.

## Language

### Lançamentos

**Lançamento**:
Registro de um valor que entra ou sai do dinheiro do casal, ou que vai entrar ou sair, com data, descrição, categorias e tags.
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

**Categoria**:
Classificação permanente de um lançamento, de uma lista plana que o casal mantém, separada para despesas, receitas e transferências (ex.: "alimentação", "viagem"); toda despesa e receita tem uma ou mais, a transferência pode ter, e é sobre elas que funcionam o planejamento e as estatísticas.
_Avoid_: subcategoria, grupo

**Tag**:
Rótulo pontual que marca os lançamentos de um projeto ou evento (ex.: "novo ap", a reforma do apartamento novo); um lançamento pode ter nenhuma ou várias, e tag não entra no planejamento.
_Avoid_: etiqueta, marcador

**Pessoa**:
O Flávio ou a esposa, quando o lançamento é de um deles; cada lançamento tem no máximo uma.
_Avoid_: tag de pessoa, dono, responsável, quem gastou

**Conjunto**:
Lançamento sem pessoa: é do casal (mercado, internet, gasolina, rendimento da poupança do casal).
_Avoid_: compartilhado, comum

**Favorito**:
Lançamento-modelo que o casal marca (ou aceita dos sugeridos, os mais usados) para registrar de novo com um toque: preenche conta, categorias, tags, pessoa e o último valor, que é só o padrão e se confirma ao salvar. Aparece numa fileira acima do teclado do novo lançamento e numa grade na tela inicial.
_Avoid_: atalho, modelo

**Sugestão**:
Categorias, tags, conta e pessoa de um lançamento anterior de descrição parecida, oferecidas enquanto se digita a descrição; escolher uma preenche esses campos e mantém o valor já digitado. Vem da **fonte de sugestão**.
_Avoid_: autocompletar, recomendação

**Fonte de sugestão**:
De onde as sugestões vêm; a v1 tem só o histórico de lançamentos do casal, e outras fontes (um modelo, uma IA) podem se somar a ele depois.
_Avoid_: motor de sugestão

### Futuro

**Recorrência**:
Regra que gera um lançamento previsto a cada N semanas ou N meses, com ou sem fim (o salário, a conta de luz, o seguro anual); não é um lançamento. Tem valor fixo (o Spotify) ou estimado (o salário, a luz).
_Avoid_: repetição, despesa fixa, gasto fixo, assinatura

**Parcelamento**:
Compra ou dívida dividida em N parcelas; não é um lançamento, gera um lançamento para cada parcela.
_Avoid_: compra parcelada, financiamento

**Parcela**:
Lançamento que é uma das N partes de um parcelamento (ex.: 3/10).
_Avoid_: prestação

**Automático**:
Recorrência de valor fixo ou parcelamento cujos previstos viram realizados sozinhos na data, sem confirmação.
_Avoid_: débito automático, efetivação automática

**Confirmação**:
O ato de alguém do casal dizer que um previsto aconteceu, ajustando valor, data ou conta se precisar; o previsto vira realizado.
_Avoid_: efetivação, baixa

**Atrasado**:
Previsto que pede confirmação e cuja data já passou sem ela; continua previsto até ser confirmado ou excluído.
_Avoid_: vencido, pendente

**Contas da semana**:
Lista dos previstos que pedem confirmação, atrasados ou com data nos próximos 7 dias, despesas e receitas.
_Avoid_: agenda, a pagar

### Planejamento

**Planejamento**:
O quanto o casal se propõe a gastar ou guardar num mês, item a item; não é lançamento e não mexe em saldo.
_Avoid_: orçamento, meta

**Item do planejamento**:
Uma linha do planejamento do mês, de uma única categoria e com um valor (ex.: R$ 1.000 em alimentação), comparada com os lançamentos realizados e previstos do mês que contam nele; cada lançamento conta em no máximo um item, mesmo tendo várias categorias.
_Avoid_: teto, limite, meta

### Consulta

**Fechamento do mês**:
Resumo de um mês que já passou: receitas, despesas, sobra, o que foi guardado, os itens do planejamento que passaram do planejado e a comparação com o mês anterior e com o mesmo mês do ano anterior. Não confundir com o **fechamento** da fatura.
_Avoid_: balanço, extrato do mês

**Projeção de saldo**:
Estimativa da soma das contas no fim de cada mês que vem, em duas linhas: o saldo de hoje mais os previstos, e a mesma linha descontando o que ainda falta de cada item do planejamento.
_Avoid_: previsão de saldo, fluxo de caixa

### Contas e cartões

**Fatura**:
As compras de um cartão entre dois fechamentos, pagas de uma vez no vencimento.

**Fechamento**:
Data em que a fatura deixa de receber compras; uma compra feita no próprio dia do fechamento já vai para a fatura seguinte. Cada fatura tem o seu, que nasce do dia de fechamento padrão do cartão.

**Vencimento**:
Data limite para pagar a fatura. Cada fatura tem o seu, que nasce do dia de vencimento padrão do cartão.
_Avoid_: data de pagamento (o pagamento pode ser feito antes ou depois)

**Data da compra**:
Dia em que a compra no cartão foi feita; numa parcela, é o dia da compra do parcelamento, o mesmo em todas as parcelas. Não decide em que mês a compra conta: quem decide é o mês da fatura.
_Avoid_: data da fatura, data do lançamento

**Mês da fatura**:
Mês em que a fatura e cada compra dela contam no planejamento, nas categorias, nas tags e no resumo: o mês do fechamento, ou o anterior se o cartão for configurado assim. Cada cartão tem uma fatura por mês.
_Avoid_: competência, mês de referência

**Saldo anterior**:
Parte de uma fatura que não foi paga e passa para a fatura seguinte; não é compra nova e não conta de novo.
_Avoid_: rotativo (o rotativo é o crédito que gera juros sobre o saldo anterior)

**Estorno**:
Crédito de uma compra devolvida, que aparece numa fatura posterior ligado à compra original e com as mesmas categorias e tags.
_Avoid_: reembolso, devolução

**Transferência**:
Dinheiro que passa de uma conta do casal para outra; não é entrada nem saída do dinheiro do casal, mas pode ter categoria e contar no planejamento (ex.: guardar na reserva).

**Ajuste de fatura**:
Diferença entre a soma das compras lançadas numa fatura e o valor real dela (uma compra esquecida ou lançada errada), guardada na própria fatura; não é lançamento, conta no total da fatura e nas despesas do mês, mas não em categoria, tag nem item do planejamento.
_Avoid_: reajuste, arredondamento, diferença de fatura

**Saldo de abertura**:
Valor de uma conta numa data, informado pelo casal, a partir do qual o saldo é calculado; só os realizados depois dessa data mexem no saldo, e o que veio antes serve às estatísticas.
_Avoid_: saldo inicial, saldo importado

**Pagamento de fatura**:
Transferência de uma conta para um cartão que quita a fatura; não conta como saída nem tem categoria, porque as compras da fatura já são lançamentos.

### Importação do Mobills

**Virada**:
O dia em que o casal para de lançar no Mobills e passa a lançar só no app; a última importação do histórico do Mobills acontece nele, e antes dele a importação pode ser refeita quantas vezes for preciso.
_Avoid_: migração, corte, go-live
