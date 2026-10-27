# Spec: V1 que substitui o Mobills

Status: ready-for-agent
Origem: [mapa "V1 que substitui o Mobills"](map.md) (todas as decisões de produto, modelo de dados e arquitetura); vocabulário em [GLOSSARY.md](../../GLOSSARY.md); decisões difíceis de reverter em `docs/adr/` (0001 a 0013)

## Problem Statement

O casal (o Flávio e a esposa) registra a vida financeira no Mobills desde 2019 e quer largá-lo. O Mobills só aceita uma categoria por lançamento, mistura a compra no cartão com a data do vencimento, não separa de quem é cada lançamento, não dá ao casal uma visão clara de "quanto ainda dá para gastar" no mês, e o histórico de quase oito anos (cerca de 11 mil linhas) fica preso nele, sem backup em arquivo nem API.

O casal precisa de um app próprio, só dos dois, que funcione no iPhone, no Android e no computador, em que lançar uma despesa no caixa do mercado leve poucos segundos, inclusive sem internet; que trate o cartão de crédito como o casal pensa nele (a compra conta no mês da fatura); que mostre o planejamento do mês item a item, os compromissos futuros e a projeção do saldo; que traga todo o histórico do Mobills; e que custe perto de zero na AWS, com os dados guardados com segurança para sempre.

## Solution

Um app web instalável (PWA) em React + TypeScript, instalado na Tela de Início dos dois celulares e aberto no navegador do computador, com uma API em Python (FastAPI) numa Lambda, banco Aurora DSQL e login do Cognito, tudo em sa-east-1 e dentro do custo-alvo de US$ 0 a 1 por mês.

Do ponto de vista do casal:

- **Lançar é rápido**: o valor primeiro, num teclado na tela; conta e categorias logo abaixo, com um toque; o resto (descrição com sugestão, tags, pessoa, data, parcelado, recorrente) numa folha opcional. Favoritos e "repetir último" preenchem tudo. No Android, o toque longo no ícone abre direto o novo lançamento. Sem internet, o lançamento fica no aparelho como **não enviado** e sobe sozinho depois.
- **O cartão funciona como na cabeça do casal**: cada compra cai na fatura certa pelo fechamento, conta no **mês da fatura** e aparece na aba Cartões numa linha que abre as compras. Limite **comprometido** e **disponível** aparecem discretos.
- **O futuro está no app**: parcelas, salários, seguros e dívidas são lançamentos **previstos**, gerados por **recorrências** e **parcelamentos**, que viram **realizados** por **confirmação** (ou sozinhos, quando **automáticos**). As **contas da semana** lembram o que confirmar.
- **O mês tem planejamento**: itens por categoria ("R$ 1.000 em alimentação"), copiados do mês anterior ou de um modelo padrão, com "ainda dá para gastar" em destaque e o aviso no momento de lançar ("Mercado: 82% → 105%").
- **Consultar é fácil**: abas Hoje, Mês, Cartões, Histórico e Futuro; fechamento do mês em texto corrido; comparação com o mês anterior, com o mesmo mês do ano passado e ao longo dos anos desde 2019; **projeção de saldo**; busca em todo o histórico com **filtros salvos** e **edição em lote** de categorias e tags.
- **Os dados estão seguros**: backup diário automático num S3 com Object Lock, "exportar tudo" a qualquer momento e o histórico do Mobills importado por um cruzamento revisado pelo dono.

A v1 é entregue em etapas (veja Implementation Decisions); a primeira instala o app nos dois celulares e testa o sem internet de verdade antes de construir em cima dele. A v1 está pronta no dia da **virada**: quando o casal para de lançar no Mobills.

## User Stories

### Acesso e instalação

1. Como alguém do casal, quero instalar o app na Tela de Início do iPhone pelo Compartilhar, para usá-lo como um app sem precisar de loja nem de Mac.
2. Como alguém do casal, quero instalar o app no Android pelo Chrome, para ter um ícone na tela inicial como qualquer app.
3. Como alguém do casal, quero abrir o mesmo app no navegador do computador, com layout para tela larga, para consultar e organizar com mais espaço.
4. Como alguém do casal, quero entrar com e-mail e senha num formulário dentro do próprio app, sem ser levado para outra página, para não ficar preso numa janela do Safari no iPhone.
5. Como alguém do casal, quero continuar logado por anos depois de entrar uma vez, para nunca ter de digitar a senha no caixa do mercado.
6. Como alguém do casal, quero continuar usando o app sem internet mesmo com o acesso expirado, para que o login nunca trave um lançamento.
7. Como dono, quero desconectar um celular perdido de todas as sessões, para que ninguém continue acessando os dados.
8. Como alguém do casal, quero ser avisado se tentar sair da conta com lançamentos não enviados, para não apagar sem querer o que ainda não subiu.
9. Como dono, quero que só eu e minha esposa existamos como usuários, sem cadastro público, para que ninguém mais entre no app.

### Lançamento rápido

10. Como alguém do casal, quero que a tela de novo lançamento abra com o valor em destaque e um teclado numérico próprio, para digitar o valor antes de qualquer outra coisa.
11. Como alguém do casal, quero que os dígitos entrem pelos centavos, com teclas `00` e apagar, para digitar valores sem procurar a vírgula.
12. Como alguém do casal, quero trocar entre despesa e receita no topo da tela, para lançar os dois com a mesma jornada.
13. Como alguém do casal, quero escolher a conta ou o cartão numa fileira de toque logo abaixo do valor, para escolher com um dedo só.
14. Como alguém do casal, quero escolher uma ou mais categorias numa fileira de toque, para classificar o jantar em Ilhabela como "alimentação" e "viagem" ao mesmo tempo.
15. Como alguém do casal, quero que "Salvar" só fique liberado com valor e pelo menos uma categoria, para nunca deixar uma despesa ou receita sem categoria.
16. Como alguém do casal, quero abrir uma folha de detalhes opcional com descrição, tags, pessoa, data e "Repete?", para completar o lançamento só quando precisar.
17. Como alguém do casal, quero ver o resumo dos detalhes numa linha embaixo do valor, para conferir o que preenchi sem abrir a folha.
18. Como alguém do casal, quero escolher a data entre hoje, ontem ou outra, para lançar o que esqueci de registrar no dia.
19. Como alguém do casal, quero que um lançamento com data futura nasça previsto e um com data de hoje ou do passado nasça realizado, podendo trocar à mão, para registrar o IPVA do mês que vem ou uma conta que devo e ainda não paguei.
20. Como alguém do casal, quero marcar a pessoa do lançamento (o Flávio, a esposa ou nenhuma, que é o conjunto), para saber de quem é cada lançamento sem usar tag.
21. Como alguém do casal, quero pôr nenhuma ou várias tags e criar uma tag nova no próprio lançamento, para marcar projetos como "novo ap".
22. Como alguém do casal, quero que "repetir último" apareça enquanto o lançamento está vazio, para registrar de novo o mesmo lançamento com um toque.
23. Como usuário de Android, quero que o toque longo no ícone mostre "Novo lançamento" e abra direto a tela de lançar, para registrar sem passar pela tela inicial.
24. Como usuário de iPhone, quero um botão "+ Novo lançamento" na tela inicial do app, para lançar rápido mesmo sem atalho no ícone.
25. Como alguém do casal, quero ver na mesma tela, a cada toque, o aviso de planejamento com o antes e o depois ("Mercado: 82% → 105% do planejado de out/26"), para saber o efeito do lançamento antes de salvar.
26. Como alguém do casal, quero que o aviso diga quanto ainda dá para gastar no item ou quanto passa, para decidir na hora.
27. Como alguém do casal, quero que o aviso de uma compra no cartão mostre a fatura em que ela cai e o mês que conta, para entender por que uma compra do dia 28 conta no mês seguinte.
28. Como alguém do casal, quero que o aviso diga que o lançamento conta só no total do mês quando nenhuma das categorias tem item, para não achar que ele sumiu do planejamento.
29. Como alguém do casal, quero que, com duas ou mais categorias com item no mês, o aviso mostre "Conta no planejamento em:" com a última escolha para aquele conjunto já marcada, trocável com um toque, para não contar o mesmo dinheiro duas vezes sem travar o lançamento.

### Favoritos e sugestões

30. Como alguém do casal, quero ver meus favoritos numa fileira acima do teclado do novo lançamento, ao lado do "repetir último", para lançar o café de sempre com um toque.
31. Como alguém do casal, quero ver os mesmos favoritos numa grade na tela inicial, para lançar direto ao abrir o app, inclusive no iPhone.
32. Como alguém do casal, quero que tocar num favorito abra o novo lançamento já preenchido com conta, categorias, tags, pessoa e o último valor usado, para só conferir e salvar.
33. Como alguém do casal, quero que o valor do favorito seja só o padrão, editável pelo teclado, e que "Salvar" seja a confirmação, para nunca lançar um valor errado sem ver.
34. Como alguém do casal, quero que o valor padrão do favorito seja o do último lançamento feito com ele, para acompanhar a mudança de preço.
35. Como alguém do casal, quero marcar um lançamento como favorito com a ⭐, e ver o app oferecer "Favoritar" depois de salvar, para criar favoritos sem ir às configurações.
36. Como alguém do casal, quero ver num grupo "Sugeridos" os 3 lançamentos mais repetidos que ainda não são favoritos (a partir de 5 usos), para promovê-los com um toque na ⭐ ou dispensá-los.
37. Como alguém do casal, quero reordenar e remover favoritos nas configurações, para manter a lista do jeito que uso.
38. Como alguém do casal, quero ver, a partir da 2ª letra da descrição, até 3 sugestões vindas de lançamentos anteriores do casal, para não escolher categorias e tags toda vez.
39. Como alguém do casal, quero que escolher uma sugestão preencha categorias, tags, conta e pessoa e mantenha o valor já digitado, para não perder o que já fiz.
40. Como alguém do casal, quero que as sugestões venham de descrição igual, depois de "começa com" e depois de palavra que começa com o que digitei, da mais recente para a mais antiga, para que a primeira seja quase sempre a certa.
41. Como alguém do casal, quero que corrigir as categorias de um lançamento torne essa a sugestão mais recente daquela descrição, para que o app aprenda sem configuração.
42. Como alguém do casal, quero que as sugestões funcionem sem internet, para lançar no subsolo do mercado.
43. Como alguém do casal, quero que o histórico do Mobills já alimente as sugestões desde o primeiro dia, para não começar do zero.

### Sem internet e sincronização

44. Como alguém do casal, quero criar, editar, excluir e confirmar lançamentos sem internet, para que a falta de sinal nunca me impeça de registrar.
45. Como alguém do casal, quero lançar parcelado e recorrente sem internet, como um pedido só, para registrar a geladeira em 10x no próprio caixa.
46. Como alguém do casal, quero ver o lançamento não enviado nas listas com ⏳ e já contando no saldo e no aviso de planejamento do meu aparelho, para não perder a noção do mês.
47. Como alguém do casal, quero ver na tela Hoje quantos lançamentos estão não enviados, para saber se preciso abrir o app com internet.
48. Como alguém do casal, quero que o aviso de não enviado fique em destaque depois de 24 h, para lembrar de enviar.
49. Como alguém do casal, quero que a fila suba sozinha quando a internet voltar (no iPhone, ao abrir ou voltar para o app; no Android, também em segundo plano), e um botão "Enviar agora", para não precisar pensar em sincronização.
50. Como alguém do casal, quero que reenviar a fila nunca duplique um lançamento, para confiar no botão mesmo com a internet caindo no meio.
51. Como alguém do casal, quero que um lançamento recusado pelo servidor (o cartão foi arquivado, por exemplo) fique marcado "não enviado: <motivo>" para corrigir ou descartar, sem travar o resto da fila.
52. Como alguém do casal, quero que as telas já abertas mostrem a última resposta com "atualizado às 14:32" sem internet, para consultar o que já tinha visto.
53. Como alguém do casal, quero que planejamento, contas, cartões, categorias, tags, favoritos e regras apareçam com o botão desativado e "precisa de internet", para entender por que não dá para mudar agora.
54. Como alguém do casal, quero que, se nós dois mudarmos campos diferentes do mesmo lançamento, as duas mudanças fiquem, para que ninguém perca o que fez.
55. Como alguém do casal, quero que, se eu mudar um campo que a outra pessoa (ou uma regra) mudou depois, minha mudança vire um conflito marcado com "⚠ conflito", para decidir em vez de perder algo em silêncio.
56. Como alguém do casal, quero decidir o conflito numa tela só com os campos divergentes ("o seu: R$ 320" × "o da Fulana, às 14:32: R$ 230"), campo a campo, ou descartar minha mudança, para resolver em segundos.
57. Como alguém do casal, quero que, enquanto o conflito espera, meu aparelho mostre a versão do servidor, para que os dois celulares mostrem o mesmo número.
58. Como alguém do casal, quero que editar algo que a outra pessoa excluiu descarte a edição com aviso e "Lançar de novo", para não ressuscitar sem querer um lançamento.
59. Como alguém do casal, quero ser perguntado antes de excluir um lançamento que a outra pessoa mudou depois de mim, para não apagar a correção dela.
60. Como alguém do casal, quero que a tela de conflito diga quando a mudança veio do próprio app ("a recorrência Luz, alterada pela Fulana"), para entender de onde veio.
61. Como alguém do casal, quero ver "Parece repetido" quando chega um lançamento da outra pessoa com o mesmo valor, a mesma conta ou cartão e data a até 1 dia, com "Manter os dois" ou "Excluir este", para não lançarmos duas vezes o mesmo mercado.
62. Como alguém do casal, quero ver no menu ⋯ > Informações quem criou e quem alterou por último cada lançamento, e quando (a hora da ação no aparelho), para saber quem mexeu sem poluir a lista.

### Contas, transferências e saldo

63. Como alguém do casal, quero cadastrar contas com saldo (corrente, poupança, carteira), para acompanhar o dinheiro de cada uma.
64. Como alguém do casal, quero informar o saldo de abertura de uma conta numa data, para que o saldo bata com o extrato a partir dali.
65. Como alguém do casal, quero que só os realizados depois do saldo de abertura mexam no saldo da conta, para que o histórico importado sirva às estatísticas sem bagunçar o saldo.
66. Como alguém do casal, quero registrar uma transferência de uma conta para outra, com categoria opcional (ex.: "Reserva"), para guardar dinheiro sem contar como despesa.
67. Como alguém do casal, quero que uma transferência com categoria possa contar no planejamento, para planejar o quanto guardar no mês.
68. Como alguém do casal, quero arquivar uma conta que não uso mais, para tirá-la das opções sem perder o histórico.

### Cartões e faturas

69. Como alguém do casal, quero cadastrar vários cartões com dia de fechamento e de vencimento padrão e limite opcional, para que o app saiba em que fatura cada compra cai.
70. Como alguém do casal, quero cadastrar um cartão adicional ligado ao titular, que divide o limite dele, para registrar as compras do adicional sem confundir as contas.
71. Como alguém do casal, quero configurar um cartão para contar no "mês anterior ao fechamento", para cartões que fecham nos primeiros dias do mês.
72. Como alguém do casal, quero que a compra no cartão caia na fatura certa pela data da compra e pelo fechamento, e que uma compra no próprio dia do fechamento vá para a fatura seguinte, para não fazer essa conta de cabeça.
73. Como alguém do casal, quero trocar a fatura de uma compra à mão, para quando o banco lança a compra com atraso.
74. Como alguém do casal, quero que cada fatura tenha fechamento e vencimento próprios, que nascem do padrão e podem ser editados, para acertar um fechamento que escorregou por feriado.
75. Como alguém do casal, quero que mudar o dia padrão do cartão valha só para as faturas abertas e futuras e redistribua as compras delas, para que uma fatura fechada nunca mude.
76. Como alguém do casal, quero que a compra no cartão conte no mês da fatura no planejamento, nas categorias, nas tags, no resumo e na projeção, para que o total do mês feche com o que sai do nosso dinheiro naquele mês.
77. Como alguém do casal, quero que o saldo da conta caia no dia do pagamento real da fatura, para bater com o extrato do banco.
78. Como alguém do casal, quero registrar o pagamento de fatura como uma transferência da conta para o cartão, sem categoria, para que as compras não contem duas vezes.
79. Como alguém do casal, quero pagar uma fatura em parte e ver o que faltou ir para a fatura seguinte como saldo anterior, que não conta de novo no planejamento nem nas tags, para registrar um mês apertado sem distorcer os números.
80. Como alguém do casal, quero lançar juros, IOF e multa do rotativo como lançamentos novos na fatura seguinte, para ver quanto o atraso custou.
81. Como alguém do casal, quero pagar a fatura antes do vencimento ou adiantar com ela aberta, mexendo só no saldo da conta, para que o mês da fatura não mude.
82. Como alguém do casal, quero que uma compra cancelada antes do fechamento suma de tudo, para não sobrar nada dela.
83. Como alguém do casal, quero registrar um estorno ligado à compra original, com as mesmas categorias e tags, na fatura em que aparece, para que ele diminua o total dessa tag naquele mês.
84. Como alguém do casal, quero registrar um ajuste de fatura quando a soma das compras não bate com o valor real, para que o total da fatura e as despesas do mês fiquem certos sem inventar uma categoria.
85. Como alguém do casal, quero que o ajuste de fatura conte no total da fatura, nas despesas do mês, no "ainda dá para gastar" e no fechamento do mês, mas não em categoria, tag nem item do planejamento, para não fingir que sei o que foi comprado.
86. Como alguém do casal, quero arquivar um cartão inativo, para tirá-lo das opções de novo lançamento e manter o histórico dele.

### Compromissos futuros

87. Como alguém do casal, quero criar uma recorrência a cada N semanas ou N meses (anual = 12 meses), sem fim, até uma data ou por N vezes, para registrar o salário, a luz e o seguro anual uma vez só.
88. Como alguém do casal, quero que a recorrência tenha valor fixo (o Spotify) ou estimado (o salário, a luz), para que o app saiba o que confirmar.
89. Como alguém do casal, quero que dia 31 em mês curto caia no último dia do mês, para não perder a ocorrência de fevereiro.
90. Como alguém do casal, quero mudar uma recorrência "daqui para frente" em qualquer campo, para acompanhar um reajuste sem mexer no passado.
91. Como alguém do casal, quero mudar só um mês de uma recorrência, e que esse previsto não seja sobrescrito por uma mudança posterior "daqui para frente", para registrar uma conta de luz atípica.
92. Como alguém do casal, quero pular um mês de uma recorrência, para quando uma cobrança não acontece.
93. Como alguém do casal, quero encerrar ou excluir uma recorrência, sumindo com os previstos depois da data de fim, para cancelar uma assinatura.
94. Como alguém do casal, quero que mudar uma recorrência nunca reescreva um realizado dela, para que o passado seja sempre o que aconteceu.
95. Como alguém do casal, quero lançar uma compra ou dívida em N parcelas, informando o valor total ou o da parcela, com os centavos que sobram na 1ª, para registrar compras com e sem juros.
96. Como alguém do casal, quero que cada parcela seja um lançamento (3/10) e a compra parcelada não seja, para que o valor inteiro nunca estoure o planejamento de um mês.
97. Como alguém do casal, quero que cada parcela no cartão conte no mês da fatura em que cai, para que o planejamento de cada mês receba só a sua parte.
98. Como alguém do casal, quero lançar uma dívida em boleto como parcelamento fora do cartão, para acompanhar empréstimos e acordos.
99. Como alguém do casal, quero antecipar K parcelas (tiradas do fim), com a data de hoje ou outra e o valor editável para o desconto, para registrar uma antecipação com abatimento.
100. Como alguém do casal, quero quitar o restante de um parcelamento de uma vez, para registrar a quitação.
101. Como alguém do casal, quero editar descrição, tags ou pessoa de um parcelamento e ver a mudança em todas as parcelas, inclusive as realizadas, para corrigir a classificação de uma vez.
102. Como alguém do casal, quero corrigir valor, número de parcelas ou data de um parcelamento e ver as parcelas geradas de novo, com aviso quando uma realizada vai mudar, para corrigir um erro de digitação.
103. Como alguém do casal, quero editar uma parcela só, que fica marcada como alterada à mão, para registrar uma parcela diferente.
104. Como alguém do casal, quero excluir um parcelamento inteiro, para desfazer um lançamento feito por engano.
105. Como alguém do casal, quero que previstos peçam confirmação por padrão, e que recorrência de valor fixo e parcelamento possam ser automáticos (o parcelamento no cartão já nasce automático), para confirmar só o que varia.
106. Como alguém do casal, quero que recorrência de valor estimado sempre peça confirmação, para que o saldo nunca mostre uma estimativa como real.
107. Como alguém do casal, quero confirmar um previsto ajustando valor, data ou conta, para registrar o que de fato aconteceu.
108. Como alguém do casal, quero que um previsto com data passada sem confirmação fique atrasado, contando na projeção e no "ainda dá para gastar" até ser confirmado ou excluído, para que nada some sozinho.
109. Como alguém do casal, quero ver na tela inicial "3 contas da semana para confirmar", com os atrasados e os previstos dos próximos 7 dias (despesas e receitas), em ordem de data, para não esquecer nenhuma conta.
110. Como alguém do casal, quero confirmar cada conta da semana com um toque ("Confirmar") ou ajustar valor e data antes ("Ajustar"), para dar baixa no salário que veio diferente.
111. Como alguém do casal, quero que recorrência e parcelamento guardem a escolha do item do planejamento e que os previstos já nasçam com ela, para não escolher de novo a cada mês.

### Planejamento

112. Como alguém do casal, quero criar o planejamento do mês com itens, cada um de uma categoria e com um valor, para dizer quanto pretendemos gastar ou guardar em cada coisa.
113. Como alguém do casal, quero copiar o planejamento do mês anterior ou de um modelo padrão, para não montar tudo do zero todo mês.
114. Como alguém do casal, quero que cada lançamento conte em no máximo um item do planejamento, automaticamente quando só uma das categorias tem item, para que o planejamento nunca conte o mesmo dinheiro duas vezes.
115. Como alguém do casal, quero que um lançamento cuja ambiguidade surgiu depois (item criado no meio do mês, planejamento copiado, categorias editadas) continue no item em que estava e entre na lista "a escolher", para decidir com calma.
116. Como alguém do casal, quero que uma escolha explícita de item nunca mude sozinha, para confiar no que escolhi.
117. Como alguém do casal, quero ver, por item, o realizado, o previsto, o planejado e a porcentagem, para saber como está cada um.
118. Como alguém do casal, quero ver "ainda dá para gastar" como a soma do que falta em cada item, sem compensar um item estourado com a sobra de outro, para não me enganar.
119. Como alguém do casal, quero que o "ainda dá para gastar" de um item seja o planejado menos o realizado e o previsto do mês, para contar o que já está comprometido.

### Consulta e dashboards

120. Como alguém do casal, quero que a aba Hoje mostre "ainda dá para gastar" em destaque, a lista "a escolher", os atrasados, a fatura que vence e os itens acima de 80% do planejado, para ver o essencial ao abrir o app.
121. Como alguém do casal, quero que a aba Hoje mostre os avisos de não enviados e de conflitos, para agir neles.
122. Como alguém do casal, quero navegar mês a mês na aba Mês, para ver qualquer mês do histórico.
123. Como alguém do casal, quero ver no mês atual uma barra das despesas contra o planejado (realizado, previsto e livre) e as receitas recebidas e previstas, para saber como o mês está indo.
124. Como alguém do casal, quero ver num mês passado o fechamento do mês em texto corrido (receitas, despesas, sobra e quanto ela é das receitas, o que foi guardado, os itens que passaram do planejado e a variação contra o mês anterior e o mesmo mês do ano passado), para entender o mês sem ler tabelas.
125. Como alguém do casal, quero ver a comparação por categoria com o mês anterior e com o mesmo mês do ano passado, com os valores antigos ao tocar na linha, para ver o que mudou.
126. Como alguém do casal, quero que a linha de total conte cada lançamento uma vez, mesmo com várias categorias, para que o total feche com o que saiu.
127. Como alguém do casal, quero um ranking por categoria, por tag ou por pessoa, que abre os lançamentos numa folha, para descobrir para onde foi o dinheiro.
128. Como alguém do casal, quero que as visões por categoria e por tag sejam barras e listas, sem pizza, para não fingir que as fatias somam 100%.
129. Como alguém do casal, quero ver na aba Cartões a fatura atual, a próxima e a anterior de cada cartão numa linha, com a situação (aberta, fechada ou paga), para saber o que devo.
130. Como alguém do casal, quero tocar numa fatura e ver as compras agrupadas por dia, com filtro por categoria e por tag, para conferir a fatura com o app do banco.
131. Como alguém do casal, quero ver na linha do cartão uma barra com o comprometido e o disponível, quando o limite foi informado, para saber quanto ainda cabe.
132. Como alguém do casal, quero ver no detalhe do cartão as três partes do comprometido, os parcelamentos em andamento com o que falta e o fim previsto, e quanto se libera em cada um dos próximos 12 meses, para planejar uma compra grande.
133. Como alguém do casal, quero que recorrências no cartão não contem no comprometido, para que o número siga o que o banco ocupa.
134. Como alguém do casal, quero ver na aba Histórico uma métrica por vez (despesas, receitas, sobra ou uma categoria) em 12 meses contra os 12 anteriores, por ano desde 2019 ou o mesmo mês em cada ano, para ver a evolução de longo prazo.
135. Como alguém do casal, quero ver na aba Futuro a projeção de saldo com o realizado no passado e duas linhas daqui para frente (só com os previstos, e descontando o que ainda falta do planejamento), mais uma tabela dos próximos meses, para saber se vamos fechar no azul.
136. Como alguém do casal, quero que a projeção desconte a fatura no mês dela, para que o saldo projetado do fim de abril já desconte a fatura de abril.

### Busca, filtros salvos e edição em lote

137. Como alguém do casal, quero uma busca com texto livre e filtros combinados (descrição, valor mínimo e máximo, categorias, tags, sem categoria, sem tag, conta, cartão, fatura, pessoa, período, situação e tipo), acessível pela lupa em qualquer aba, para achar qualquer lançamento desde 2019.
138. Como alguém do casal, quero que o período da busca use a data da compra no cartão, para que "março" traga o que comprei em março.
139. Como alguém do casal, quero filtrar por Fatura (cartão e mês da fatura) e ver os números baterem com a aba Mês, para conferir uma fatura.
140. Como alguém do casal, quero uma linha fixa avisando que o período é por data da compra e a aba Mês conta pelo mês da fatura, para não estranhar totais diferentes.
141. Como alguém do casal, quero que a compra parcelada apareça como uma linha com a data da compra, o valor total e as parcelas, que abre as parcelas, e que com o filtro Fatura cada parcela seja uma linha, para ver a compra inteira ou só o que cai na fatura.
142. Como alguém do casal, quero ver no topo da busca a quantidade, o total de despesas, o de receitas e o saldo, com previstos à parte e transferências fora, para resumir o resultado.
143. Como alguém do casal, quero ordenar por mais recente ou por valor, com a lista paginada e sem teto, para percorrer resultados grandes.
144. Como alguém do casal, quero que os atalhos "ver os lançamentos" do Mês e dos Cartões abram a busca já filtrada, para ir do número aos lançamentos.
145. Como alguém do casal, quero ver, sem internet, só o que o aparelho já guarda, com o aviso "resultado parcial, sem internet", para não achar que um lançamento sumiu.
146. Como alguém do casal, quero salvar uma busca com nome, critérios, ordenação e período relativo ("este mês") ou fixo, compartilhada com a outra pessoa, para repetir buscas frequentes.
147. Como alguém do casal, quero marcar lançamentos no resultado (ou todos) e acrescentar, remover, trocar ou substituir categorias e tags de uma vez, para acertar o histórico importado.
148. Como alguém do casal, quero ver uma prévia antes de aplicar a edição em lote (quantos mudam, os 5 primeiros antes e depois, quantos já estão como pedido e quantos trocam de item do planejamento), para não fazer uma besteira em massa.
149. Como alguém do casal, quero que selecionar uma compra parcelada selecione o parcelamento todo, com a contagem "12 compras (58 lançamentos)", para não deixar parcelas com classificação diferente.
150. Como alguém do casal, quero que a edição em lote seja tudo ou nada e que um lote que deixaria despesa ou receita sem categoria seja recusado, para nunca ficar pela metade.
151. Como alguém do casal, quero desfazer uma edição em lote por 30 dias, pulando o que a outra pessoa mudou depois e avisando quais, para voltar atrás sem desfazer o trabalho dela.

### Categorias, tags e configurações

152. Como alguém do casal, quero manter listas planas de categorias, separadas para despesa, receita e transferência, para classificar do nosso jeito.
153. Como alguém do casal, quero renomear uma categoria ou tag e ver o nome novo em todo o histórico, para corrigir nomes.
154. Como alguém do casal, quero juntar uma categoria em outra, movendo os lançamentos, os itens do planejamento e as escolhas de item, para limpar categorias repetidas.
155. Como alguém do casal, quero arquivar uma categoria ou tag, tirando-a das opções e mantendo o histórico, para encerrar um projeto como "novo ap".
156. Como alguém do casal, quero excluir uma categoria ou tag só quando ela não tem lançamentos, para nunca perder classificação do histórico.

### Exportação e backup

157. Como alguém do casal, quero exportar tudo como backup (zip de CSVs) ou como CSV de lançamentos para planilha, a qualquer momento, para ter os dados nas mãos.
158. Como alguém do casal, quero que o CSV de planilha abra direto no Excel e no Google Planilhas em português (separador `;`, vírgula decimal, UTF-8 com BOM), com nomes no lugar dos ids, para analisar sem converter nada.
159. Como dono, quero um backup completo automático todo dia, guardado por 90 dias num S3 com Object Lock que nem o root apaga, para perder no máximo um dia de dados.
160. Como dono, quero receber um e-mail se o backup falhar ou não rodar em 26 horas, para nunca descobrir tarde demais que estou sem backup.
161. Como dono, quero restaurar um backup num banco vazio, tudo ou nada, conferindo contagens e somas contra o manifesto, para refazer o banco com confiança.
162. Como dono, quero que a restauração recuse um banco com dados e uma versão de formato desconhecida, para nunca duplicar nem corromper dados.
163. Como dono, quero que cada exportação a pedido fique registrada (quem e quando), para saber quem tirou os dados.

### Importação do Mobills e virada

164. Como dono, quero cadastrar a conta e os 7 cartões e ligar cada pasta de fatura do Mobills a um cartão antes de importar, para que cada compra antiga caia no cartão certo.
165. Como dono, quero rodar o importador localmente sobre os exports do Mobills, sem que os dados reais entrem no repositório, para manter os dados do casal privados.
166. Como dono, quero que o importador cruze o export geral com as faturas e grave cada compra de cartão uma vez só, com a data real da compra e o cartão da fatura, e as tags, a parcela e a situação do geral, para ter o histórico completo sem digitar datas.
167. Como dono, quero uma planilha de revisão com o de-para de categorias e tags (com contagem e papel proposto), os pares prováveis, os grupos ambíguos, as sequências de parcela quebradas e os parcelamentos sem cartão, para decidir o que o importador não consegue.
168. Como dono, quero uma aba Conferência com uma linha por mês (receitas, despesas e ajustes de fatura no mês da fatura), uma coluna para eu preencher com o total do Mobills, a diferença e o porquê, para provar que nada se perdeu.
169. Como dono, quero uma aba Faturas com o total de cada fatura, para comparar com a tela de faturas do Mobills.
170. Como dono, quero editar a planilha e rodar a importação de novo quantas vezes quiser, apagando só o que veio do Mobills, para acertar os detalhes até a virada.
171. Como dono, quero que cada `Reajuste de fatura` do Mobills vire o ajuste de fatura da fatura dele, para que os totais fechem.
172. Como dono, quero que as faturas importadas nasçam com o mês da fatura do rótulo do arquivo, fechadas e pagas, sem datas e sem pagamento de fatura, para que o histórico de cartão exista sem inventar dados.
173. Como dono, quero que parcelas do Mobills sejam reagrupadas em parcelamentos e que as parcelas futuras que faltam sejam geradas como previstas, para que o comprometido e a projeção já saiam certos.
174. Como dono, quero que pendentes que não são parcela entrem como previstos avulsos quando forem de meses seguintes ao export, e sejam descartados quando forem do mês do export ou anteriores, para cadastrar as recorrências no app depois sem duplicar.
175. Como dono, quero que tudo o que foi importado entre como conjunto e com autoria "importado do Mobills", para distinguir do que lançarmos no app.
176. Como dono, quero que os 5 cartões inativos fiquem arquivados, para não poluir as opções de novo lançamento.
177. Como dono, no dia da virada, quero exportar o geral pela web e as faturas que faltam (incluindo a aberta), rodar a importação final, conferir, informar o saldo de abertura e o limite de cada cartão e confirmar quais faturas estão pagas, para começar a usar só o app.

### Operação e custo

178. Como dono, quero receber e-mail quando o gasto real passar de US$ 1, a previsão do mês passar de US$ 5 ou o gasto real passar de US$ 5, sem que os créditos escondam o gasto, para nunca ter surpresa na conta da AWS.
179. Como dono, quero receber e-mail quando a API devolver erros 5xx acima de um limite por dia, para saber de um problema antes de minha esposa.
180. Como dono, quero que o merge na `main` publique em `prod` pelo GitHub Actions com OIDC, sem chave de longa duração, para publicar sem guardar credenciais.
181. Como dono, quero uma pilha `dev` descartável na mesma conta, publicada pelo botão do workflow ou por push numa branch, para testar migrations no DSQL de verdade antes de `prod`.
182. Como dono, quero que o endereço do app nunca mude, para que nenhum de nós precise reinstalar o app e perder a fila offline.

## Implementation Decisions

### Etapas da v1

A v1 é entregue em etapas, cada uma usável sozinha; `/to-tickets` fatia cada etapa em tickets.

0. **Conta pronta**: o ticket [Configurar o acesso à conta AWS](issues/20-configurar-o-acesso-a-conta-aws.md) (HITL) é feito antes do primeiro deploy.
1. **Esqueleto que roda nos dois celulares**: infraestrutura (`prod` e `dev`), login, migrations, PWA instalável e lançamento simples (conta, categorias, valor, data, descrição) criado, editado e excluído com e sem internet, com fila, ⏳ e conflito. Termina com o teste manual nos dois celulares: instalar, lançar sem internet, enviar a fila e provocar um conflito de verdade ([ADR 0005](../../docs/adr/0005-app-web-instalavel-em-vez-de-app-nativo.md)). Se a PWA decepcionar aqui, o plano B (Capacitor) é discutido antes de seguir.
2. **Lançamentos completos e cartões**: tipos (despesa, receita, transferência, pagamento de fatura), contas com saldo de abertura, cartões, faturas, mês da fatura, ajuste de fatura, estorno, saldo anterior, categorias e tags (renomear, juntar, arquivar), pessoa, a jornada completa do lançamento rápido e o menu ⋯ > Informações.
3. **Futuro**: previsto e realizado, recorrência, parcelamento, automático, confirmação, atrasado, contas da semana, antecipação e quitação.
4. **Planejamento**: itens, cópia do mês anterior e do modelo padrão, item em que cada lançamento conta, lista "a escolher", "ainda dá para gastar" e aviso ao lançar.
5. **Consulta**: abas Hoje, Mês, Cartões, Histórico e Futuro, fechamento do mês, comparações, projeção de saldo, limite comprometido, busca, filtros salvos e edição em lote.
6. **Agilidade**: favoritos e sugestão.
7. **Dados e virada**: backup diário, "exportar tudo", restauração, importador do Mobills, planilha de revisão e virada. O backup diário pode ser antecipado para qualquer etapa anterior, e precisa estar ligado antes de o casal passar a lançar de verdade.

### Arquitetura (já decidida nos ADRs 0001, 0005, 0009, 0010)

- PWA em React + TypeScript num S3 privado servido pelo CloudFront no endereço padrão; a distribuição é protegida contra substituição e remoção.
- `/api/*` no mesmo endereço vai, sem cache e sem CORS, a uma API Gateway HTTP API com JWT authorizer e limite de taxa (10 por segundo, rajada de 20), que chama **uma Lambda** com a API inteira (FastAPI, arm64, python3.14).
- Aurora DSQL em sa-east-1, autenticação por IAM, sem segredos; schema no subconjunto do DSQL (sem triggers nem PL/pgSQL; até 3.000 linhas e 10 MiB por transação; concorrência otimista com nova tentativa no erro de serialização).
- Login do Cognito por formulário no app (SRP, cliente público), isolado num módulo do app; a API depende só de um JWT padrão (emissor e audiência em configuração) e tira a pessoa do token. Refresh token de 10 anos no IndexedDB, nunca em cookie; token de acesso de 15 minutos.
- CDK em TypeScript, pilhas `prod` e `dev` na mesma conta, cada uma com cluster DSQL, user pool e endereço próprios; orçamento e alarmes no mesmo código. A SCP da organização fica fora do código.
- Deploy pelo GitHub Actions com OIDC; migrations são arquivos SQL numerados, um DDL por arquivo, aplicados antes da Lambda nova, cada uma compatível com a versão anterior da Lambda.
- Região e endpoints só em configuração.

### Contrato entre o app e a API

- Código primeiro: a FastAPI gera o OpenAPI a partir dos modelos Pydantic; o arquivo fica versionado; o app gera os tipos TypeScript dele, e o CI falha se o arquivo gerado estiver desatualizado.
- **Uma leitura por tela**: cada tela (Hoje, Mês de um mês, Cartões, detalhe de fatura, detalhe de cartão, Histórico de uma métrica, Futuro, planejamento de um mês, contas da semana) tem uma chamada que devolve tudo o que ela mostra, em lote, já somado no servidor. O app guarda a última resposta de cada tela para mostrar sem internet.
- **Um pacote para lançar**: uma chamada devolve o que o aparelho precisa para lançar sem internet: contas, cartões e faturas abertas, categorias, tags, favoritos, último lançamento, planejamento do mês com os totais e o índice de sugestão.
- **Envio da fila em lote**: uma chamada recebe as ações de lançamento na ordem em que foram feitas (criar, editar, excluir, confirmar, criar parcelado, criar recorrente) e devolve um resultado por ação: aceita, conflito (com os campos divergentes, o valor do outro lado, quem e quando, e se veio de uma regra), recusada (com o motivo) ou descartada por exclusão. Ações recusadas ou em conflito não impedem as seguintes.
- As demais mudanças (planejamento, contas, cartões, faturas, categorias, tags, favoritos, regras "daqui para frente", filtros salvos, edição em lote, exportação) são chamadas comuns, só com internet.
- `POST /api/exportacoes` gera o backup ou o CSV e devolve uma URL assinada de 5 minutos ([ADR 0012](../../docs/adr/0012-exportacao-unica-zip-de-csvs-e-restauracao-so-em-banco-vazio.md)).

### Módulos do backend

Cada módulo esconde as regras do seu assunto atrás de uma interface pequena; as rotas da FastAPI só traduzem HTTP para esses módulos.

- **Lançamentos**: criar, editar, excluir e confirmar, um a um ou pelo lote da fila. Guarda, por campo, a versão em que ele mudou por último, e decide aceitar, mesclar campos diferentes, aceitar mudança idêntica, recusar como conflito ou descartar por exclusão ([ADR 0011](../../docs/adr/0011-sem-internet-so-lancamentos-e-conflito-decidido-a-mao.md)). Identidade do lançamento gerada no aparelho (UUID), de modo que reenviar não duplica. Grava quem criou e quem alterou por último, com a hora da ação no aparelho. Detecta o "Parece repetido" (mesmo valor, mesma conta ou cartão, data a até 1 dia, outra pessoa).
- **Contas e cartões**: contas, saldo de abertura e saldo (só realizados depois da data de abertura; no cartão, o saldo da conta segue o pagamento de fatura). Cartões (titular e adicional), dias padrão, regra do mês da fatura, limite opcional. Faturas: uma por cartão por mês, criada quando a primeira compra ou parcela precisa dela; escolha da fatura pela data da compra e pelo fechamento; troca manual; datas editáveis; mudança do dia padrão redistribui só abertas e futuras; fatura fechada nunca muda. Saldo anterior, pagamento parcial, ajuste de fatura, estorno ligado à compra. Comprometido e disponível ([ticket 23](issues/23-limite-comprometido-do-cartao.md)).
- **Regras do futuro**: recorrência e parcelamento geram lançamentos previstos; mudanças daqui para frente, só um mês, pular, encerrar, excluir; antecipar e quitar; regeração das parcelas com aviso; previstos alterados à mão preservados; automático na data. Recorrência sem fim gera previstos até um horizonte (valor inicial: 24 meses à frente), estendido por uma tarefa diária, a mesma que realiza os automáticos.
- **Planejamento**: itens por mês e categoria, modelo padrão, cópia; item em que cada lançamento conta (automático, escolha explícita, lista "a escolher"); "ainda dá para gastar" por item e do mês; o aviso de planejamento (antes e depois) como cálculo puro sobre os totais do mês e o lançamento em edição, para que o app o repita sobre o cache e a fila sem internet.
- **Classificação**: categorias (por tipo), tags e pessoa; renomear, juntar, arquivar, excluir sem lançamentos.
- **Consultas**: as leituras por tela (Hoje, Mês, fechamento do mês, comparações, ranking, Cartões, Histórico, Futuro e projeção de saldo), feitas com somas no banco sobre a tabela de lançamentos.
- **Busca**: filtros combinados, período pela data da compra e filtro Fatura ([ADR 0013](../../docs/adr/0013-busca-por-data-da-compra-e-fatura-a-parte.md)), agrupamento por compra parcelada, totais, paginação. Filtros salvos do casal.
- **Edição em lote**: prévia, aplicação tudo ou nada, registro de desfazer por 30 dias que pula o que outra pessoa mudou depois.
- **Favoritos**: marcados, sugeridos (3 mais repetidos com 5 usos ou mais, ainda não favoritos), dispensados, ordem, último valor.
- **Sugestão**: um contrato de **fonte de sugestão** (entrada: a descrição e o contexto do lançamento; saída: lista de pacotes de categorias, tags, conta e pessoa, cada um com sua origem). A v1 entrega só a fonte "histórico", que no servidor produz o índice de descrições e pacotes levado ao aparelho no pacote para lançar; o casamento (igual, começa com, palavra que começa com; sem acento e sem maiúscula; sem `(n/total)`) roda no aparelho. Uma fonte futura roda só no servidor, dentro da conta AWS, fora do caminho crítico, e o histórico local continua como plano B ([ticket 22](issues/22-sugestao-automatica-de-categorias-e-tags.md)).
- **Exportação e restauração**: um gerador que só lê o banco e produz o backup (zip com um CSV por tabela, ids originais e `manifesto.json` com `versao_formato`, contagens e somas) ou o CSV de planilha; a restauração em banco vazio, tudo ou nada, conferida contra o manifesto, com conversores das versões antigas; registro das exportações a pedido. Chamado pelo EventBridge (backup diário, que confere as contagens do zip contra o banco), por `POST /api/exportacoes` e pelo importador do Mobills.
- **Importador do Mobills**: script do backend rodado localmente pelo dono. Lê os XLSX do export geral e das faturas e a planilha de revisão editada; casa as faturas com o geral, reagrupa parcelamentos, aplica o de-para e as regras de pendentes e de `Reajuste de fatura`; escreve a planilha de revisão (de-para, pendências, Conferência, Faturas) e um **backup válido**, que a restauração grava ([ADR 0007](../../docs/adr/0007-historico-do-mobills-cruzado-e-sem-saldo.md), [ADR 0012](../../docs/adr/0012-exportacao-unica-zip-de-csvs-e-restauracao-so-em-banco-vazio.md)). Refazer a importação antes da virada apaga só o que tem autoria "importado do Mobills".

### Módulos do app

- **Camada de dados do aparelho**: o único ponto por onde as telas leem e mudam dados. Esconde o cache das telas, o pacote para lançar, a fila de não enviados, o envio em lote (ao abrir, ao voltar ao app, pelo botão e, no Android, em segundo plano), as marcas ⏳, "não enviado: <motivo>" e "⚠ conflito", e o índice de sugestão. Aplica a fila sobre o cache para que o não enviado já conte no saldo e no aviso do próprio aparelho, e mostra a versão do servidor enquanto um conflito espera.
- **Módulo de login**: o único lugar que conhece o Cognito; guarda e renova os tokens.
- **Telas**: lançamento rápido, tela inicial (favoritos, contas da semana, avisos), as cinco abas, busca, conflito, configurações (contas, cartões, categorias, tags, favoritos, modelo de planejamento). Layout de celular e de tela larga na mesma base.
- **Manifesto da PWA** com o atalho "Novo lançamento" (`shortcuts`), que no Android aparece no toque longo do ícone.

### Modelo de dados (decisões de schema)

- Uma tabela de lançamentos para todo o histórico, sem agregados nem partições; cada lançamento grava o **mês em que conta** (o mês da fatura no cartão, a data no resto), com índices por esse mês, por data e por conta ([ADR 0009](../../docs/adr/0009-aurora-dsql-em-sao-paulo.md)). Agregado mensal só entra se um dashboard passar de 1 s no servidor.
- O lançamento guarda: identidade gerada no aparelho, tipo (despesa, receita, transferência, pagamento de fatura), situação (previsto ou realizado), valor em centavos inteiros, data, data da compra (no cartão), conta de origem e de destino (transferência) ou cartão e fatura, descrição, pessoa (ou conjunto), item do planejamento em que conta e se a escolha foi explícita, regra de origem (recorrência ou parcelamento) com número da parcela e marca de alterado à mão, ligação ao lançamento original (estorno), autoria e horários de criação e da última alteração, e a versão por campo.
- Categorias e tags ligadas ao lançamento por tabelas de associação; despesa e receita exigem ao menos uma categoria.
- Tabelas próprias para contas (com saldo de abertura e data), cartões (titular ou adicional, dias padrão, regra do mês, limite), faturas (cartão, mês da fatura, datas, situação, ajuste de fatura, saldo anterior), recorrências, parcelamentos, planejamento e itens, modelo de planejamento, favoritos, filtros salvos, lotes de edição (para o desfazer), registro de exportações e controle de migrations.
- Origem do lançamento: "app" ou "importado do Mobills".

### Valores iniciais, a ajustar com o uso

Ficam em configuração do código, num lugar só: 3 sugeridos e 5 usos (favoritos); 2 letras e 3 sugestões (sugestão); 24 h (aviso de não enviado); 1 dia ("Parece repetido"); 30 dias (desfazer a edição em lote); 80% (itens em destaque na Hoje); 24 meses (horizonte da recorrência sem fim); 7 dias (contas da semana).

## Testing Decisions

Um bom teste confere o que o casal vê ou o que a API promete, nunca como o código faz por dentro: entra pela costura, sai pela costura, e sobrevive a qualquer reescrita do interior. Regras de domínio são testadas com exemplos concretos do glossário e dos tickets (a compra de 28/03 numa fatura que fecha em 25/04 é "alimentação de abril"; o jantar em Ilhabela conta em um item só). Dado real do Mobills nunca vai a teste nem ao CI: só arquivos fictícios versionados.

O repositório ainda não tem código, então não há prior art de testes; o único código existente é o script do protótipo do [ticket 17](issues/17-medir-retomada-e-confirmar-pontos-no-prototipo.md), que não serve de modelo.

Costuras confirmadas antes de escrever a spec:

- **API HTTP** (a costura principal): testes que chamam as rotas da FastAPI em processo, com dois usuários autenticados por JWT de teste, contra um **Postgres em container** com as mesmas migrations do DSQL. Cobrem todas as regras do servidor: fatura e mês da fatura, saldo e saldo de abertura, estorno, saldo anterior, ajuste de fatura, comprometido, recorrência, parcelamento, antecipação, automático, item do planejamento e "a escolher", "ainda dá para gastar", leituras por tela, fechamento do mês, comparações, projeção, busca, filtros salvos, edição em lote e desfazer, favoritos, índice de sugestão, lote da fila com conflito, mescla de campos, exclusão que vence, idempotência do reenvio e "Parece repetido". O aviso de planejamento, por ser um cálculo puro compartilhado com o app, ganha testes de tabela próprios.
- **PWA no navegador**: testes com navegador automatizado sobre o app servido localmente e a API local, com a rede desligada e religada pelo próprio teste e dois contextos de navegador fazendo o papel do casal. Cobrem: lançar sem internet (simples, parcelado e recorrente), ⏳ e contagem na Hoje, o não enviado já contando no aviso, envio da fila sem duplicar, recusa com motivo, conflito decidido campo a campo, exclusão que vence com "Lançar de novo", "Parece repetido", sugestão sem internet, favoritos e "repetir último", e telas em cache com "atualizado às".
- **Importador do Mobills**: arquivos XLSX fictícios (geral e faturas) e uma planilha de revisão editada entram; saem a planilha de revisão e um backup. Os testes conferem o cruzamento, os pares prováveis, os grupos ambíguos, os parcelamentos reagrupados e gerados, os pendentes descartados e avulsos, os ajustes de fatura, a Conferência mês a mês e que o backup gerado restaura.
- **Ida e volta do backup** (já decidida no [ADR 0012](../../docs/adr/0012-exportacao-unica-zip-de-csvs-e-restauracao-so-em-banco-vazio.md)): restaurar um backup de exemplo fictício num banco vazio, exportar de novo e exigir zip idêntico; restaurar um backup de versão antiga para provar os conversores; restauração recusada em banco com dados e em versão desconhecida.

Também no CI:

- O contrato: o OpenAPI gerado e os tipos do app precisam estar em dia.
- As migrations, conferidas contra o subconjunto do DSQL de verdade pela pilha `dev` a cada deploy (o Postgres do CI aceita coisas que o DSQL não aceita); antes da virada e a cada mudança no formato da exportação, uma restauração de verdade no `dev` a partir do backup de `prod`.

Fora do CI, manual e HITL: o teste da etapa 1 nos dois celulares (instalar, lançar sem internet, enviar a fila, provocar um conflito) e o ticket [Verificar o download da exportação no iPhone](issues/26-verificar-o-download-da-exportacao-no-iphone.md), depois que o "exportar tudo" existir.

## Out of Scope

Tudo o que está em "Out of scope" no [mapa](map.md), entre eles:

- Importar extrato ou fatura (OFX/CSV), Open Finance e conferência da fatura em lote a partir do arquivo do banco: na v1 o lançamento é manual.
- Leitura do QR code da nota fiscal, foto de recibo, anexo de comprovante, lançamento por voz ou texto livre com IA.
- Metas, caixinhas, patrimônio e investimentos (o saldo é o das contas); comparações corrigidas pela inflação; notificações.
- Divisão de despesas do casal ("quem deve a quem"); dividir um lançamento em partes; ratear o valor entre categorias; planejamento por tag, por combinação de categorias ou por pessoa; pizza e grupos de categorias.
- Dívida com juros calculada pelo app (Price ou SAC); sobra do planejamento que passa para o mês seguinte; recorrência por dia útil e calendário de feriados; estimativa que aprende com o último valor confirmado.
- Histórico completo de alterações de um lançamento (basta quem criou e quem alterou por último); lixeira.
- Cópia do backup fora da AWS.
- Sugestão por modelo ou IA (só o encaixe da fonte de sugestão entra); tolerância a erro de digitação e botão "nunca sugerir isso".
- Sem internet: planejamento, contas, cartões, categorias, tags, favoritos, regras, busca completa e edição em lote.
- Na edição em lote: mudar pessoa, conta, valor, data ou situação. No CSV de planilha: filtro por período.
- Cadastro público, multi-inquilino, loja de apps, Apple Developer, domínio próprio, TOTP e passkey.

## Further Notes

- **Pendências abertas do mapa**, que não travam a spec: [Configurar o acesso à conta AWS](issues/20-configurar-o-acesso-a-conta-aws.md) é a etapa 0 (HITL, do dono); [Verificar o download da exportação no iPhone](issues/26-verificar-o-download-da-exportacao-no-iphone.md) roda na etapa 7, e se falhar o plano B é decidido lá (tela de download própria, link por e-mail ou o backup do S3).
- **Protótipos como fonte primária da interface**: lançamento rápido na branch `prototipo/lancamento-rapido` (variante A), favoritos em `prototipo/favoritos` (variante C) e dashboards em `prototipo/dashboards` (variação B com a comparação da A). A tela de configurações dos favoritos e a tela de conflito não foram prototipadas.
- **Preenchido pela spec, sem decisão explícita do casal** (revisar no primeiro ticket que tocar o assunto): o horizonte de 24 meses da recorrência sem fim; o formato do modelo padrão de planejamento (um conjunto de itens com valor, editável nas configurações); as compras do cartão adicional caírem na fatura do titular (o limite dividido já estava decidido); valores em centavos inteiros.
- **Avisos que reabrem decisões**: se o PWA no iPhone perder dados locais ou o iOS limpar o app depois de dias sem abrir, retomar a investigação pelo roteiro do protótipo do ticket 17; se a primeira conexão ao DSQL depois do cluster parado passar de 5 s, rever o [ADR 0009](../../docs/adr/0009-aurora-dsql-em-sao-paulo.md); se um dashboard passar de 1 s no servidor, entra um agregado mensal.
- **Custo**: fora o DSQL, US$ 0,01 a 0,06 por mês; com o DSQL na franquia, abaixo de US$ 0,10, dentro do alvo de US$ 0 a 1 e do teto de US$ 5. Créditos de US$ 119,98 até 12/04/2027, divididos com outro projeto.
- **Próximo passo**: `/to-tickets` sobre esta spec, etapa por etapa, começando pela etapa 1.
