# Conferir as regras de fatura escolhidas no ticket 37

Type: grilling
Status: ready-for-human
Blocked by: 37
Skills: `grilling`, `domain-modeling` (HITL: decisões do dono)
Modelo recomendado: Opus
Effort recomendado: medium
Issue: #165
Origem: [ticket 37](37-cartoes-e-faturas.md) (e o [77](77-ligar-o-csv-de-planilha-ao-esquema-real.md), feito com ele): a spec e a [ADR 0003](../../../docs/adr/0003-compra-no-cartao-conta-no-mes-da-fatura.md) não dizem o que fazer nestes casos, e o ticket 37 escolheu um comportamento provisório para cada um (já em `backend/app/cartoes.py` e `backend/app/faturas.py`, com teste)

## O que decidir

Para cada regra abaixo, o dono confirma o comportamento provisório ou pede outro. Mudança vira ticket de implementação; o que ficar vai para o glossário ou para a ADR 0003.

## Checklist

- [ ] **Mudar o dia padrão sobrescreve as datas acertadas à mão** nas faturas abertas e futuras (a fatura do feriado volta para o novo padrão). Alternativa: manter as datas editadas à mão
- [ ] **Fatura fechada recebe compra lançada depois**: a compra esquecida, lançada com a data antiga, cai na fatura fechada daquela data, porque o banco já a cobrou ali. "Fatura fechada nunca muda" vale só para a mudança do dia padrão
- [ ] **Acertar as datas de uma fatura fechada** (o feriado só foi notado depois do fechamento) traz para ela as compras das abertas que agora cabem nela; as compras dela que ficariam de fora não saem
- [ ] **Mudar o dia padrão para antes de hoje fecha a fatura atual na hora**: fecha em 25, hoje é 20/04 e o novo dia é 15 → a fatura de abril passa a fechar em 15/04 (já fechada), e as compras de 15/04 a 20/04 vão para maio. Alternativa: o novo dia vale a partir da fatura seguinte
- [ ] **Trocar a regra "mês anterior ao fechamento"** recalcula as datas das faturas abertas pelo novo mês do fechamento, sem mudar o mês delas
- [ ] **Vencimento padrão** cai no mês do fechamento se o dia vier depois do fechamento, senão no mês seguinte (fecha 25, vence 5 → 05 do mês seguinte; fecha 3, vence 10 → dia 10 do mesmo mês)
- [ ] **Troca de fatura sem volta**: não há "voltar para a fatura que o app escolheria"; trocar para a fatura certa continua marcado como à mão (só trocar de cartão desfaz a marca)
- [ ] **Trocar para a fatura que o app já escolheu não marca a troca**: o pedido não muda nada, então a próxima mudança de data escolhe a fatura de novo. Alternativa: marcar como à mão mesmo assim
- [ ] **Cartão sem dia de fechamento** (os inativos do histórico) recusa a compra sem a fatura escolhida
- [ ] **CSV de planilha** ([ticket 77](77-ligar-o-csv-de-planilha-ao-esquema-real.md), feito com o 37): a transferência sai numa linha só ("Corrente → Poupança", valor sem sinal), os nomes das colunas ficam sem acento (`descricao`, `situacao`) e a coluna `fonte` (importado do Mobills ou app) fica de fora. Alternativas: duas linhas por transferência (saída e entrada), cabeçalho com acento, coluna `fonte`
- [ ] **Fatura fechada no próprio dia do fechamento** (`situacao: fechada` a partir dele), como a compra desse dia, que já vai para a seguinte
