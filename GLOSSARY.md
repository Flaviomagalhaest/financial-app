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

**Categoria arquivada**:
Categoria que o casal tirou das opções de lançamento novo sem apagá-la: os lançamentos que já a têm a mantêm, e ela pode ser desarquivada.

**Juntar (categoria ou tag)**:
Passar todos os lançamentos de uma categoria (ou tag) para outra do mesmo tipo e excluir a primeira; o lançamento que já tinha as duas fica com uma só.
_Avoid_: mesclar, unir

**Tag**:
Rótulo pontual que marca os lançamentos de um projeto ou evento (ex.: "novo ap", a reforma do apartamento novo); um lançamento pode ter nenhuma ou várias, e tag não entra no planejamento.
_Avoid_: etiqueta, marcador

A tag também pode ser arquivada, como a categoria; excluir categoria ou tag só é possível sem lançamentos.

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

**Modelo padrão do planejamento**:
Conjunto de itens (categoria e valor) que o casal mantém nas configurações e aplica a um mês vazio para não começar o planejamento do zero; vale para qualquer mês e não é um mês. Não é um **Favorito**, que é um lançamento-modelo.
_Avoid_: modelo (sozinho), template

### Consulta

**Filtro salvo**:
Busca que o casal guarda com nome: os critérios (texto e filtros), a ordenação e o período, relativo ("este mês") ou fixo; é do casal inteiro. Não é um **Favorito**, que é um lançamento-modelo.
_Avoid_: busca salva, visão

**Edição em lote**:
Mudança de categorias e tags de vários lançamentos de uma vez, a partir do resultado de uma busca; mostra uma prévia, aplica tudo ou nada e pode ser desfeita por 30 dias. Uma compra parcelada conta como uma só.
_Avoid_: edição em massa, ação em massa

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

**Conta arquivada**:
Conta que o casal tirou das opções (não recebe lançamento nem transferência novos) sem perder o histórico; o saldo e os lançamentos antigos continuam, e desarquivar a devolve.
_Avoid_: conta excluída, conta inativa

**Limite**:
Teto de compras de um cartão, informado pelo casal e editável; é opcional, e o cartão adicional divide o limite do titular.
_Avoid_: crédito, saldo do cartão

**Comprometido**:
Parte do limite de um cartão já ocupada: as compras da fatura aberta, as faturas fechadas ainda não pagas (com o saldo anterior) e as parcelas futuras dos parcelamentos. Recorrência não conta, porque só o que já foi comprado ocupa o limite.
_Avoid_: usado, gasto do cartão

**Disponível**:
O limite menos o comprometido; pagar a fatura, receber um estorno, pagar uma parcela e antecipar ou quitar parcelas o aumentam.
_Avoid_: limite restante, saldo do cartão

**Pagamento de fatura**:
Transferência de uma conta para um cartão que quita a fatura; não conta como saída nem tem categoria, porque as compras da fatura já são lançamentos.

### Exportação

**Backup**:
Arquivo `.zip` com um CSV por tabela e um manifesto com a versão do formato, que contém todos os dados do casal e refaz o banco; é gerado todo dia e a pedido.
_Avoid_: dump, snapshot

**Exportação**:
Arquivo que o app gera a pedido de um dos dois: o backup completo ou o CSV de lançamentos para abrir numa planilha.
_Avoid_: download, relatório

**Restauração**:
Carga de um backup num banco vazio, tudo ou nada (em lotes que se desfazem se algo falhar), conferida contra o manifesto, que recusa banco com dados e versão de formato desconhecida; é também o caminho da carga do histórico do Mobills.
_Avoid_: importação do backup, merge

### Importação do Mobills

**Virada**:
O dia em que o casal para de lançar no Mobills e passa a lançar só no app; a última importação do histórico do Mobills acontece nele, e antes dele a importação pode ser refeita quantas vezes for preciso.
_Avoid_: migração, corte, go-live

### Sem internet

**Não enviado**:
Lançamento, ou mudança num lançamento, feito no aparelho que ainda não chegou ao servidor; já conta no que o próprio aparelho mostra, mas a outra pessoa só o vê depois do envio.
_Avoid_: pendente, offline, na fila, não sincronizado

**Conflito**:
Mudança não enviada feita sobre um lançamento que outra pessoa (ou uma regra) mudou depois nos mesmos campos; fica esperando que quem a fez escolha, campo a campo, qual versão fica.
_Avoid_: colisão, divergência

**Parece repetido**:
Aviso, para quem não o criou, de um lançamento que chegou depois de outro da outra pessoa com o mesmo valor, a mesma conta e data a até 1 dia; o casal escolhe "Manter os dois" ou "Excluir este".
_Avoid_: duplicado, duplicata

**Fonte do lançamento**:
De onde o lançamento veio: o "app" ou o "importado do Mobills".
_Avoid_: autoria (é quem criou ou alterou)

**Versão do lançamento**:
Número que sobe a cada mudança aceita num lançamento; cada campo guarda a versão em que mudou por último, e uma mudança diz sobre qual versão foi feita, para o servidor saber o que o outro lado mudou depois dela.
_Avoid_: revisão, timestamp

**Exclusão vence a edição**:
Regra do conflito: a edição que chega depois que o outro lado excluiu o lançamento é descartada, com o aviso de quem excluiu e o botão "Lançar de novo", que cria outro lançamento com a mudança. O lançamento excluído fica no banco só com a marca de exclusão, sem aparecer em lugar nenhum.
_Avoid_: lixeira, restaurar, ressuscitar
