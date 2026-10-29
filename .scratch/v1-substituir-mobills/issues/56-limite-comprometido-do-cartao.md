# Limite comprometido e disponível do cartão

Type: task
Status: ready-for-agent
Blocked by: 55, 46
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` se mexer na interface
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #110
Origem: [spec da v1](../spec.md), etapa 5; histórias de usuário 131, 132, 133

## O que construir

O casal vê quanto do limite já está ocupado, só na aba Cartões, como decidido no ticket 23.

## Checklist

- [ ] Comprometido = fatura aberta + fechadas não pagas + parcelas futuras; disponível = limite menos ele; recorrência não conta; cartão adicional divide o limite do titular
- [ ] Barra na linha do cartão (só com limite informado) e, no detalhe, as três partes, os parcelamentos em andamento e a lista dos próximos 12 meses
- [ ] Testes de API com exemplos concretos
- [ ] Verificações do projeto rodando e PR aberto para `main`

## Notas

- Do [ticket 39](39-estorno-ajuste-de-fatura-e-cancelamento.md): O estorno (`estorno_de`, ADR 0016) é um lançamento de despesa que diminui: a soma do comprometido usa `VALOR_COM_SINAL` (`app/lancamentos.py`) e o ajuste da fatura (`faturas.ajuste_centavos`) entra no total da fatura fechada.
- Do [ticket 46](46-parcelamento-criar.md): as parcelas futuras do cartão são os lançamentos previstos com `parcelamento_id` num cartão; a parcela vira realizada quando entra na fatura aberta (regra provisória, [ticket 99](99-parcelamento-regras-provisorias.md)).
