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

**Sugerido**:
Lançamento que o casal repete muito (os 3 mais repetidos, a partir de 5 usos) e ainda não é **Favorito**; aparece no grupo "Sugeridos" da Hoje e das configurações, para promover com a ⭐ ou dispensar. O que se dispensa, ou se remove dos favoritos, não volta a ser sugerido. Não é uma **Sugestão**, que vem da descrição.
_Avoid_: favorito automático

**Identidade do favorito**:
O que faz dois lançamentos serem "o mesmo": descrição normalizada, tipo, conta, categorias, tags e pessoa. Conta os usos do **Sugerido** e dá o valor padrão do **Favorito**, que é o valor do último lançamento com essa identidade.

**Sugestão**:
Categorias, tags, conta e pessoa de um lançamento anterior de descrição parecida, oferecidas enquanto se digita a descrição; escolher uma preenche esses campos e mantém o valor já digitado. Vem da **fonte de sugestão**.
_Avoid_: autocompletar, recomendação

**Fonte de sugestão**:
De onde as sugestões vêm; a v1 tem só o histórico de lançamentos do casal, e outras fontes (um modelo, uma IA) podem se somar a ele depois.
_Avoid_: motor de sugestão

### Futuro

**Recorrência**:
Regra que gera um lançamento previsto a cada N semanas ou N meses, com ou sem fim (o salário, a conta de luz, o seguro anual); não é um lançamento. Tem valor fixo (o Spotify) ou estimado (o salário, a luz). Só gera de hoje em diante: com o início no passado, as ocorrências de antes de hoje não viram lançamento (nem atrasado, nem realizado), mas o calendário e as `vezes` seguem contados desde o início; a de hoje, lançada junto com a regra, nasce realizada. A tarefa diária e a mudança da regra também não lançam ocorrência que já passou. A regra que termina antes de hoje é recusada.
_Avoid_: repetição, despesa fixa, gasto fixo, assinatura

**Ocorrência**:
Cada vez em que uma recorrência acontece, numerada desde o início (1ª, 2ª...), com a data contada do início e nunca da anterior (o dia 31 passa por 30/11 e volta a 31/12); cada uma gera um previsto, e a que o casal pulou (excluída) não volta. A que o fim ou o horizonte tirou volta quando o fim sai ou o horizonte chega a ela: `geradas` recua até antes dela, e só o excluído marcado como da regra (`excluido_pela_regra`) é trazido de volta; o que o casal pulou nunca volta, esteja o número antes ou depois do fim.
_Avoid_: instância, repetição

**Daqui para frente**:
Mudança de uma recorrência a partir de uma ocorrência: a regra passa a valer assim e os previstos dessa ocorrência em diante são refeitos, menos os alterados à mão. O passado e o realizado ficam. Mudar o calendário (a cada quantos, o dia) remarca o início da regra naquela ocorrência, que mantém o número. Nada vira lançamento antes de hoje: o previsto que a data nova leva de hoje ou depois para antes sai, marcado como da regra, e volta se outra mudança o trouxer para hoje ou depois. O atrasado não vira automático.
_Avoid_: a partir de agora, mudar tudo

**Encerrar**:
Dar fim a uma recorrência numa data ou depois de N vezes: os previstos depois do fim saem, também os alterados à mão, e o realizado fica. Excluir a recorrência é diferente: tira a regra e os previstos de hoje em diante, e o atrasado fica.
_Avoid_: cancelar, parar

**Alterado à mão**:
Previsto de uma recorrência que uma pessoa editou (qualquer campo): uma mudança "daqui para frente" não o sobrescreve, nem o mês pulado volta. Mudar só um mês é editar o previsto; pular um mês é excluí-lo.
_Avoid_: customizado, manual

**Horizonte**:
Até onde a recorrência gera previstos: 24 meses à frente de hoje, estendido todo dia pela tarefa diária. Reagendar para menos frequente tira os previstos que passam dele, e a tarefa diária os traz quando ele chega.
_Avoid_: janela, limite

**Tarefa diária**:
Rotina do servidor que roda logo depois da meia-noite de São Paulo: estende o horizonte das recorrências e completa os parcelamentos, realiza os automáticos do dia e desfaz as edições em lote que pararam no meio. Rodar de novo no mesmo dia não muda nada.
_Avoid_: job, cron, rotina noturna

**Parcelamento**:
Compra ou dívida dividida em N parcelas; não é um lançamento, gera um lançamento para cada parcela. No boleto com a data no passado, as parcelas de antes de hoje são puladas (`parcelas_puladas` na resposta; não é a parcela que o casal excluiu): não viram lançamento, mas contam na numeração e no total, e a de hoje nasce realizada; o boleto que já venceu inteiro é recusado. A correção também pula a prevista que leva para antes de hoje (essa existe excluída, marcada como da regra, e volta se outra correção a trouxer para hoje ou depois). O cartão gera todas.
_Avoid_: compra parcelada, financiamento

**Parcela**:
Lançamento que é uma das N partes de um parcelamento (ex.: 3/10). No cartão, todas têm a data da compra e a parcela n cai n − 1 faturas depois da fatura da compra; fora dele (o boleto), a parcela n vence n − 1 meses depois da primeira.
_Avoid_: prestação

**Parcela alterada à mão**:
O "alterado à mão" da parcela: valor, data, conta ou fatura que uma pessoa mudou, realizada ou não (a API a marca com `alterada_a_mao`). A correção do parcelamento a preserva nessas quatro coisas; a descrição, as categorias, as tags, a pessoa e o item valem para todas as parcelas.

**Correção do parcelamento**:
Mudança do valor, do número de parcelas ou da data de um parcelamento, que gera as parcelas de novo, também as realizadas: quando uma realizada vai mudar ou sair, a API avisa e só muda com a confirmação. Só o número de parcelas mantém o total. A parcela excluída uma a uma não volta; a que sai porque o parcelamento encolheu volta se ele crescer de novo. No boleto, nada da correção vira lançamento antes de hoje: a prevista que a data nova leva de hoje ou depois para antes sai como pulada (conta em `parcelas_puladas`), sem realizar a automática; a pulada que a data nova põe em hoje ou depois nasce; a atrasada (que já estava antes de hoje) segue prevista com a data nova.
_Avoid_: regerar, recalcular o parcelamento

**Antecipação**:
Pagamento adiantado das últimas parcelas de um parcelamento que ainda não foram pagas, no dia de hoje ou em outro, por um valor editável (o desconto é a diferença para o valor das parcelas). As parcelas viram realizadas na data do pagamento, e no cartão contam na fatura em que foi paga, por troca à mão. **Quitação** é a antecipação de todas as parcelas que faltam.
_Avoid_: adiantamento, amortização

**Automático**:
Recorrência de valor fixo ou parcelamento cujos previstos viram realizados sozinhos na data, sem confirmação; a parcela no cartão, que tem a data da compra, vira realizada quando entra na fatura aberta (a fatura de antes fechou).
_Avoid_: débito automático, efetivação automática

**Confirmação**:
O ato de alguém do casal dizer que um previsto aconteceu, ajustando valor, data ou conta se precisar; o previsto vira realizado.
_Avoid_: efetivação, baixa

**Atrasado**:
Previsto que pede confirmação e cuja data já passou sem ela; continua previsto até ser confirmado ou excluído.
_Avoid_: vencido, pendente

**Hoje**:
A aba que o casal vê ao abrir o app: quanto ainda dá para gastar no mês, o que está a escolher, as contas da semana e as atrasadas, a fatura que vence e os itens em destaque, mais os avisos de não enviados e de conflitos. Vem de uma leitura só.
_Avoid_: início, painel

**Fatura que vence**:
Fatura fechada, ainda com saldo a pagar, que vence nos próximos 7 dias ou já venceu; aparece na Hoje.

**Item em destaque**:
Item do planejamento do mês que já usou 80% ou mais do planejado (realizado mais previsto), inclusive o que estourou; aparece na Hoje.
_Avoid_: perto do limite

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

**Escolha do item**:
A categoria, entre as do lançamento, cujo item do planejamento o casal escolheu para ele contar quando duas ou mais têm item no mês. Vale em qualquer mês em que essa categoria tem item, nunca muda sozinha e sai quando a categoria sai do lançamento; a recorrência e o parcelamento a guardam, e seus lançamentos já nascem com ela.
_Avoid_: item principal, categoria principal

**A escolher**:
A lista dos lançamentos do mês com duas ou mais categorias com item e sem escolha do item que valha. O lançamento que já contava sozinho num item quando a ambiguidade surgiu (item criado no meio do mês, categorias editadas, outro mês) continua nele até o casal escolher.
_Avoid_: pendentes, sem item

**Aviso de planejamento**:
O que a tela de lançar mostra a cada toque: o item em que o lançamento conta, com a porcentagem do planejado antes e depois dele e quanto ainda dá para gastar ou quanto passa; "conta só no total do mês" quando nenhuma categoria tem item; no cartão, a fatura em que a compra cai. Roda no aparelho, também sem internet, e já conta os lançamentos não enviados.
_Avoid_: alerta de orçamento, previsão do item

**Modelo padrão do planejamento**:
Conjunto de itens (categoria e valor) que o casal mantém nas configurações e aplica a um mês vazio para não começar o planejamento do zero; vale para qualquer mês e não é um mês. Não é um **Favorito**, que é um lançamento-modelo.
_Avoid_: modelo (sozinho), template

### Consulta

**Busca**:
Tela única que acha lançamentos e transferências em todo o histórico, por texto livre na descrição e filtros combinados (entre filtros é E, dentro de um filtro OU). O período usa a **data da compra**, não o **mês da fatura** (ADR 0013); fora do **filtro Fatura**, o **parcelamento** é uma linha só. Abre pela lupa, de qualquer aba.
_Avoid_: pesquisa, consulta (que é o nome da etapa)

**Filtro Fatura**:
Filtro da **busca** pelo **mês da fatura** de um cartão, com as compras dos adicionais; sem cartão, pelo mês em que cada lançamento conta, como na aba Mês. Com ele, cada **parcela** é uma linha e os números batem com a aba Mês e com a fatura. É o que os atalhos "Ver os lançamentos" do Mês e dos Cartões abrem.
_Avoid_: filtro por competência

**Filtro salvo**:
Busca que o casal guarda com nome: os critérios (texto e filtros), a ordenação e o período, relativo ("este mês") ou fixo; é do casal inteiro. Não é um **Favorito**, que é um lançamento-modelo.
_Avoid_: busca salva, visão

**Edição em lote**:
Mudança de categorias e tags de vários lançamentos de uma vez, a partir do resultado de uma busca; mostra uma prévia, aplica tudo ou nada e pode ser desfeita por 30 dias. Uma compra parcelada conta como uma só.
_Avoid_: edição em massa, ação em massa

**Evolução**:
O que a aba Histórico mostra: uma métrica por vez (despesas, receitas, sobra ou uma categoria) em 12 meses contra os 12 meses anteriores, por ano desde o primeiro lançamento ou no mesmo mês de cada ano. Conta só o realizado.
_Avoid_: tendência, série histórica

**Fechamento do mês**:
Resumo de um mês que já passou: receitas, despesas, sobra, o que foi guardado, os itens do planejamento que passaram do planejado e a comparação com o mês anterior e com o mesmo mês do ano anterior. Não confundir com o **fechamento** da fatura.
_Avoid_: balanço, extrato do mês

**Projeção de saldo**:
Estimativa da soma das contas no fim de cada mês que vem, em duas linhas: o saldo de hoje mais os previstos, com cada fatura descontada no mês dela, e a mesma linha descontando o que ainda falta de cada item do planejamento. No passado, mostra o saldo realizado no fim de cada mês, desde a abertura das contas.
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
Mês em que a fatura e cada compra dela contam no planejamento, nas categorias, nas tags e no resumo: o mês do fechamento, ou o anterior se o cartão for configurado assim, nunca o do vencimento (a fatura que fecha em 25/04 e vence em 05/05 é de abril). Cada cartão tem uma fatura por mês.
_Avoid_: competência, mês de referência

**Fatura aberta**:
Fatura cujo fechamento ainda não chegou: a atual e as futuras. A partir do dia do fechamento ela é **fechada**, e mudar o dia padrão do cartão não mexe mais nas datas nem nas compras dela.
_Avoid_: fatura atual, fatura em aberto (que é a não paga)

**Troca de fatura**:
Escolha à mão da fatura de uma compra no cartão, no lugar da que o app escolheu pela data da compra, para quando o banco lança a compra com atraso. A troca fica mesmo se a data da compra ou o dia padrão do cartão mudarem; trocar de cartão a desfaz.
_Avoid_: mover a compra, transferir a compra

**Cartão adicional**:
Cartão ligado a um titular, para outra pessoa usar; não tem dias padrão, regra do mês nem limite próprios, e as compras dele caem na fatura do titular.
_Avoid_: cartão dependente, segunda via

**Fatura paga**:
Fatura fechada que recebeu um pagamento, de qualquer valor. O que faltou pagar passa para a fatura seguinte como saldo anterior. Daí em diante ela não recebe mais pagamento, compra, troca de fatura nem estorno; só muda pela correção de fatura ([ADR 0021](docs/adr/0021-o-pagamento-quita-a-fatura.md)).
_Avoid_: fatura quitada, paga em parte

**Correção de fatura**:
Edição de uma fatura paga para consertar um erro (pagamentos, compras, datas, ajuste), que vale toda de uma vez ao salvar; a fatura continua paga e o saldo anterior que passou para a seguinte é refeito.
_Avoid_: reabrir a fatura, fatura reaberta

**Saldo anterior**:
O que faltou pagar de uma fatura paga (o total menos o pago), que passa para a fatura seguinte quando o pagamento é lançado, em qualquer dia; não é compra nova e não conta de novo. Fatura fechada sem pagamento não passa nada: continua devendo.
_Avoid_: rotativo (o rotativo é o crédito que gera juros sobre o saldo anterior)

**Estorno**:
Crédito de uma compra devolvida, que aparece numa fatura posterior ligado à compra original e com as mesmas categorias e tags. Diminui o total da fatura, do mês, da categoria, da tag e do item do planejamento em que aparece ([ADR 0016](docs/adr/0016-estorno-e-lancamento-que-diminui-ligado-a-compra.md)).
_Avoid_: reembolso, devolução

**Compra cancelada**:
Compra no cartão que o casal desfaz antes do fechamento da fatura: é excluída e some de tudo (fatura, mês, categoria, tag e planejamento). Depois do fechamento, o caminho é o estorno.
_Avoid_: compra estornada (estorno é o crédito que aparece numa fatura posterior)

**Transferência**:
Dinheiro que passa de uma conta do casal para outra; não é entrada nem saída do dinheiro do casal, mas pode ter categoria e contar no planejamento (ex.: guardar na reserva).

**Ajuste de fatura**:
Diferença entre a soma das compras lançadas numa fatura e o valor real dela (uma compra esquecida ou lançada errada), guardada na própria fatura; não é lançamento, conta no total da fatura e nas despesas do mês, mas não em categoria, tag nem item do planejamento. Na tela, o casal informa o valor real da fatura (o ajuste é o que falta para o total chegar nele) ou a diferença para o total que o app mostra (soma ao ajuste que a fatura já tem).
_Avoid_: reajuste, arredondamento, diferença de fatura

**Saldo de abertura**:
Valor de uma conta numa data, informado pelo casal, a partir do qual o saldo é calculado; só os realizados depois dessa data mexem no saldo, e o que veio antes serve às estatísticas.
_Avoid_: saldo inicial, saldo importado

**Conta arquivada**:
Conta que o casal tirou das opções (não recebe lançamento nem transferência novos) sem perder o histórico; o saldo e os lançamentos antigos continuam, e desarquivar a devolve.
_Avoid_: conta excluída, conta inativa

**Cartão arquivado**:
Cartão que o casal tirou das opções de novo lançamento sem perder o histórico; as compras antigas continuam nele e na fatura delas, e desarquivar o devolve.
_Avoid_: cartão cancelado, cartão inativo

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
Transferência de uma conta para um cartão que quita a fatura; não conta como saída nem tem categoria, porque as compras da fatura já são lançamentos. Pode ser feito antes do vencimento ou com a fatura aberta (adiantar), e mexe só no saldo da conta, no dia do pagamento real. Se for menor que o devido, o que faltou é o **saldo anterior** da fatura seguinte. A fatura fechada e quitada é **paga**.

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

**Planilha de revisão**:
A planilha que o importador do Mobills escreve a cada rodada com o que ele não decide sozinho (a conta e os cartões, o de-para, os pares prováveis, as parcelas) e as abas Conferência e Faturas; o dono a edita e roda de novo, e o que ele editou vale na rodada seguinte.
_Avoid_: relatório, planilha de importação

**Fatura importada**:
Fatura que veio do export de faturas do Mobills: nasce com o mês da fatura do rótulo do arquivo, sem fechamento nem vencimento, e conta como fechada e paga sem pagamento de fatura. Dar as datas a ela (na virada, à que ainda está aberta) a faz seguir as regras das outras faturas.
_Avoid_: fatura antiga, fatura do histórico

**Pendente avulso**:
Pendente do Mobills que não é parcela: a ocorrência de uma recorrência de lá, sem a regra. Os do mês do export (o último mês com lançamento pago no geral) e de antes ficam fora da importação; os de depois entram como previstos avulsos, que o casal apaga quando cadastrar a recorrência no app. O pendente que casou com uma linha de fatura não é avulso: a fatura prova que a compra existiu.
_Avoid_: recorrência importada

**Par provável**:
Uma linha de fatura e uma do geral que sobraram do cruzamento no mesmo mês e são as únicas com aquele valor; viram uma compra só quando o dono as junta na planilha de revisão, e até lá cada uma entra sozinha.
_Avoid_: par duvidoso, casamento parcial

### Sem internet

**Não enviado**:
Lançamento, ou mudança num lançamento, feito no aparelho que ainda não chegou ao servidor; já conta no que o próprio aparelho mostra, mas a outra pessoa só o vê depois do envio. A recorrência e o parcelamento novos e a mudança de uma recorrência também ficam não enviados, cada um como um pedido só.
_Avoid_: pendente, offline, na fila, não sincronizado

**Conflito**:
Mudança não enviada feita sobre um lançamento que outra pessoa (ou uma regra) mudou depois nos mesmos campos; fica esperando que quem a fez escolha, campo a campo, qual versão fica. A mudança não enviada de uma recorrência não vira conflito: o servidor a recusa com o motivo, e quem a fez a refaz sobre a regra nova (ADR 0020).
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
