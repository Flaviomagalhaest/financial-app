# Ciclo de vida do lançamento futuro

Type: grilling
Status: resolved
Blocked by: —
Skills: `grilling` e `domain-modeling` (HITL: precisa do dono)
Modelo recomendado: Opus
Effort recomendado: high
Trello: ari:cloud:trello::card/workspace/598b72bf7efc694a04666f1f/6add2e6eff572483fb077c99
Origem: traçado do [mapa V1 que substitui o Mobills](../map.md)

## Question

Como um compromisso futuro nasce, muda e vira realizado?

Cobrir:

- **Vocabulário:** custo, gasto ou despesa? Como se chama o que está "previsto" (compromisso com data e valor) e o que está "planejado" (teto do mês)? São dois conceitos que hoje se confundem.
- **Recorrência:** com ou sem fim; mudar o valor daqui para frente; mudar o valor só de um mês, sem mexer no passado nem no futuro; pular um mês; encerrar.
- **Parcelamento:** uma compra gera N parcelas nas faturas seguintes; antecipar parcelas; quitar o restante; editar ou excluir a compra original depois de parcelada.
- **Conferência:** quando o previsto vira realizado (sozinho na data ou confirmado por alguém); o que entra em "contas da semana"; o que acontece com o que venceu sem confirmação.
- **Receitas:** se salário e outras receitas seguem as mesmas regras.

## Checklist

- [x] Decisão registrada em `## Answer`
- [x] `GLOSSARY.md` atualizado com os termos resolvidos
- [x] ADR em `docs/adr/` se a decisão for difícil de reverter, surpreendente e fruto de um trade-off real

## Answer

Um compromisso futuro é um **lançamento previsto**, que vira **realizado** quando acontece. Não existe uma entidade "compromisso" à parte. **Recorrência** e **parcelamento** não são lançamentos: são regras que geram lançamentos. Registrado em [ADR 0004](../../../docs/adr/0004-previsto-e-situacao-do-lancamento.md); os termos estão no [GLOSSARY.md](../../../GLOSSARY.md).

- **Vocabulário**: **despesa** e **receita** são os dois lados do lançamento ("gasto" e "custo" ficam em _Avoid_). **Previsto** e **realizado** são situações do mesmo lançamento; só o realizado mexe no saldo da conta, e o previsto entra na projeção. O teto do mês é o **planejamento**, feito de **itens do planejamento**: não é lançamento e não mexe em saldo. O "quanto ainda posso gastar" de um item é planejado − realizado − previsto do mês. Sobre o que o item incide é assunto do [ticket 04](04-categoria-unica-ou-so-tags.md).
- **Previsto avulso**: é um lançamento único no futuro (o IPVA, a viagem). Ao lançar, a situação vem da data (futura → previsto; hoje ou passado → realizado) e pode ser trocada à mão. Um previsto com data passada é um "devo, mas ainda não paguei".
- **Recorrência**: gera um previsto a cada N semanas ou N meses (anual = 12 meses), sem fim, até uma data ou depois de N vezes. Dia 31 em mês curto cai no último dia do mês. O valor é **fixo** (o Spotify) ou **estimado** (o salário, a luz). Os previstos herdam valor, descrição, tags, tag de pessoa, conta ou cartão e dia.
  - **Daqui para frente**: muda a regra a partir de uma data e atualiza os previstos dali em diante, em qualquer campo.
  - **Só um mês**: edita aquele previsto, que fica marcado como alterado à mão; uma mudança posterior "daqui para frente" não o sobrescreve.
  - **Pular um mês**: exclui aquele previsto, e a recorrência não o gera de novo.
  - **Encerrar**: põe a data de fim; os previstos depois dela somem.
  - **Excluir a recorrência**: o mesmo que encerrar hoje.
  - **Realizados nunca mudam** por mudança na recorrência e continuam como lançamentos comuns.
  - **Dia fixo**: sem regra de dia útil nem calendário de feriados na v1; a data real se ajusta na confirmação.
  - **Estimativa fixa**: o próximo previsto usa o valor da regra, não o último confirmado.
- **Parcelamento**: uma compra ou dívida em N parcelas gera N lançamentos, as **parcelas** (1/10 ... 10/10). A compra em si não é lançamento, para não contar duas vezes. Informa-se o valor total ou o valor da parcela (compra com juros); os centavos que sobram vão na 1ª parcela. As parcelas herdam tags e tag de pessoa. Dívida em boleto usa o mesmo parcelamento, fora do cartão. Em que fatura e em que mês cada parcela conta é regra do [ticket 06](06-em-que-mes-conta-uma-compra-no-cartao.md).
  - **Antecipar**: escolhem-se K parcelas, tiradas do fim; elas ganham a data de hoje (ou a informada) e o valor pode ser editado para o desconto. Continuam parcelas do mesmo parcelamento e contam no mês da nova data (no cartão, na fatura em que foram pagas).
  - **Quitar o restante**: é antecipar todas as que faltam.
  - **Editar descrição, tags ou tag de pessoa**: vale para todas as parcelas, inclusive as realizadas.
  - **Editar valor, número de parcelas ou data**: as parcelas são geradas de novo, com aviso quando uma parcela realizada vai mudar. Isso vale também para parcela em fatura fechada: corrigir um erro de digitação não é reorganizar faturas, e a parcela corrigida fica na mesma fatura e no mesmo mês da fatura. O "fatura fechada nunca muda" do ticket 06 trata de datas e de redistribuição de compras, e continua valendo.
  - **Editar uma parcela só**: marca aquela como alterada à mão, como na recorrência.
  - **Excluir**: apaga o parcelamento e todas as parcelas ("foi engano"). Compra cancelada e estorno seguem o ticket 06.
- **Conferência**: por padrão, o previsto vira realizado por **confirmação** de alguém do casal, que pode ajustar valor, data e conta. Recorrência de valor fixo e parcelamento podem ser **automáticos**: o previsto vira realizado sozinho na data. O parcelamento no cartão já nasce automático. Recorrência de valor estimado sempre pede confirmação, para o saldo nunca mostrar uma estimativa como real.
  - **Atrasado**: previsto que pede confirmação e cuja data passou sem ela. Continua previsto e contando na projeção e no "quanto ainda posso gastar" até ser confirmado ou excluído; nunca se realiza nem some sozinho.
  - **Contas da semana**: lista os previstos que pedem confirmação, atrasados ou com data até 7 dias à frente, despesas e receitas, em ordem de data. Cada item se confirma em um toque, com valor e data preenchidos e editáveis; a jornada vai para o protótipo do [ticket 10](10-fluxo-de-lancamento-rapido.md).
- **Receitas**: seguem as mesmas regras das despesas. O salário é uma recorrência de receita com valor estimado e confirmação manual, porque o dia e o valor variam (feriado, horas extras).

Para a importação do Mobills (no "Not yet specified" do mapa): o "pendente/efetivado" de lá vira previsto/realizado, e as parcelas de lá precisam ser reagrupadas em parcelamentos.
