# Limite comprometido do cartão

Type: grilling
Status: resolved
Blocked by: —
Skills: `grilling` e `domain-modeling` (HITL: precisa do dono)
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #66
Origem: fog "Limite comprometido do cartão" do [mapa V1 que substitui o Mobills](../map.md), graduado agora que o mês da fatura ([ticket 06](06-em-que-mes-conta-uma-compra-no-cartao.md)), o parcelamento ([ticket 05](05-ciclo-de-vida-do-lancamento-futuro.md)) e as abas ([ticket 11](11-dashboards-e-fechamento-do-mes.md)) estão decididos

## Question

Como mostrar quanto do limite do cartão as parcelas futuras ocupam?

## Checklist

- [x] Decisão registrada em `## Answer`
- [x] Vocabulário novo no `GLOSSARY.md` e ADR para o que for difícil de reverter

## Answer

Decidido com o dono em 2026-10-27. O limite é uma informação de pouca importância (hoje são 2 cartões com limites dificilmente atingíveis), então a v1 o mostra de forma discreta e sem aviso.

- **O que é o comprometido**: a soma de três partes: as compras da fatura aberta; as faturas fechadas e ainda não pagas, com o saldo anterior; e as parcelas futuras dos parcelamentos. O **disponível** é o limite menos o comprometido. Pagar a fatura, estorno, parcela paga e antecipar ou quitar parcelas liberam limite.
- **Fora da conta**: recorrências no cartão não contam, porque o banco só ocupa o limite quando a cobrança acontece.
- **Valor do limite**: o Mobills não o exporta. O casal o informa ao cadastrar o cartão, junto do fechamento e do vencimento padrão, e o edita quando o banco mudar. É opcional, por cartão: sem limite informado, não aparece nada. No cartão adicional há um só limite, o do titular, e o comprometido soma as compras dos dois.
- **Onde aparece**: só na aba **Cartões** ([ticket 11](11-dashboards-e-fechamento-do-mes.md)). A linha do cartão ganha uma barra com o comprometido e o disponível; ao tocar, o detalhe mostra as três partes, os parcelamentos em andamento com o que falta de cada um e o fim previsto, e uma lista curta dos próximos 12 meses com quanto do comprometido se libera em cada um (a fatura que vence e as parcelas que terminam), sem gráfico novo. Nas abas Hoje e Mês não entra limite.
- **Sem aviso ao lançar**: o dono descartou o aviso de disponível antes e depois da compra, no lançamento. Não há bloqueio nem aviso de limite.
- **Importação e virada** ([ticket 18](18-importacao-do-mobills-cartao-e-datas.md)): as parcelas futuras que a importação gera como previstas já alimentam o comprometido. Na virada, toda fatura importada é tratada como **paga**, menos a aberta e as fechadas ainda dentro do vencimento, que o dono confirma na hora de informar o saldo de abertura; o limite de cada cartão é informado nessa mesma hora.

Termos novos no [glossário](../../../GLOSSARY.md): **Limite**, **Comprometido** e **Disponível**. Sem ADR, porque a decisão é fácil de reverter.
