# Em que mês conta uma compra no cartão

Type: grilling
Status: resolved
Blocked by: —
Skills: `grilling` e `domain-modeling` (HITL: precisa do dono)
Modelo recomendado: Opus
Effort recomendado: high
Trello: ari:cloud:trello::card/workspace/598b72bf7efc694a04666f1f/6add2e6facbfc01458b62a85
Origem: traçado do [mapa V1 que substitui o Mobills](../map.md)

## Question

Num cartão que fecha no dia 25 e vence no dia 5, uma compra de supermercado feita em 28/03 cai na fatura que fecha em 25/04 e vence em 05/05. Em que mês ela conta:

- no resumo do mês, onde o cartão aparece como uma linha só (a fatura);
- no planejamento (é "alimentação" de março ou de maio?);
- nos dashboards por tag;
- na projeção de saldo.

Cobrir também: estorno e compra cancelada; parcela que cai numa fatura futura; pagamento parcial da fatura; fatura paga antes do vencimento; mudança do dia de fechamento do cartão.

## Checklist

- [x] Decisão registrada em `## Answer`
- [x] `GLOSSARY.md` atualizado com os termos resolvidos
- [x] ADR em `docs/adr/` se a decisão for difícil de reverter, surpreendente e fruto de um trade-off real

## Answer

Compra no cartão conta no **mês da fatura**, não na data da compra. Isso vale para o planejamento, os dashboards por tag, as comparações entre meses, o resumo do mês e a projeção mês a mês. Só o saldo da conta segue o dia em que o pagamento da fatura acontece de fato. Registrado em [ADR 0003](../../../docs/adr/0003-compra-no-cartao-conta-no-mes-da-fatura.md).

No exemplo da pergunta: o cartão fecha em 25/04 e vence em 05/05, então a compra de mercado de 28/03 é "alimentação de **abril**", no resumo, no planejamento, nas tags e na projeção, mesmo se a fatura for paga em 02/05.

- **Mês da fatura**: é o mês do fechamento. Cada cartão pode trocar para "mês anterior ao fechamento", para cartões que fecham nos primeiros dias do mês.
- **Uma fatura por mês por cartão**: o mês da fatura é definido quando ela nasce, pelo dia padrão e pela regra do cartão. Um fechamento que escorrega para o mês seguinte (feriado) ou a mudança do dia padrão não tira a fatura do mês dela. A fatura de transição pode ficar mais curta ou mais longa.
- **Em que fatura cai a compra**: o app escolhe pela data da compra e pelo fechamento. Compra feita no próprio dia do fechamento vai para a fatura seguinte. Quem lança pode trocar a fatura de uma compra, para o banco que lança com atraso.
- **Datas**: o cartão tem um dia de fechamento e um de vencimento padrão. Cada fatura tem datas próprias, que nascem do padrão e podem ser editadas. Mudar o padrão vale só para as faturas abertas e futuras, e redistribui as compras delas. Fatura fechada nunca muda.
- **Planejamento e aviso na hora de lançar**: a compra no cartão conta no planejamento do mês da fatura, e o aviso já mostra esse mês ("Alimentação de abril: 82%"). Débito, Pix e dinheiro contam na própria data. "Alimentação de abril" é o débito/Pix de 01/04 a 30/04 mais as compras no cartão de 26/03 a 25/04.
- **Saldo da conta x mês**: o saldo da conta cai no dia do pagamento real, para bater com o extrato. O resumo do mês e a projeção mês a mês descontam a fatura no mês dela: o saldo projetado do fim de abril já desconta a fatura de abril.
- **Parcelas**: cada parcela conta no mês da fatura em que cai, com as tags da compra. Uma parcela antecipada passa a contar na fatura em que foi paga. A mecânica da antecipação é do [ticket 05](05-ciclo-de-vida-do-lancamento-futuro.md).
- **Compra cancelada antes do fechamento**: some de tudo.
- **Estorno**: é um crédito na fatura em que aparece, ligado à compra original e com as mesmas tags. Diminui o total da tag nesse mês. A fatura da compra original não muda, então uma tag pode ficar negativa num mês com estorno grande.
- **Pagamento parcial**: o que não foi pago vai para a fatura seguinte como saldo anterior, que não conta de novo no planejamento nem nas tags. Juros, IOF e multa do rotativo são lançamentos novos nessa fatura e contam no mês dela.
- **Pagamento antes do vencimento ou adiantado com a fatura aberta**: mexe só no saldo da conta, nunca no mês da fatura. O pagamento adiantado diminui o que falta pagar no vencimento.

Para a importação do Mobills (no "Not yet specified" do mapa): cada compra antiga no cartão precisa cair numa fatura com mês da fatura, então a importação tem que trazer ou reconstruir a fatura de cada compra.
