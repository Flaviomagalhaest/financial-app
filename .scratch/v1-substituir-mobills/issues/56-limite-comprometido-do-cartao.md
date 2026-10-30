# Limite comprometido e disponível do cartão

Type: task
Status: resolved
Blocked by: 55, 46
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` se mexer na interface
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #110
Origem: [spec da v1](../spec.md), etapa 5; histórias de usuário 131, 132, 133

## O que construir

O casal vê quanto do limite já está ocupado, só na aba Cartões, como decidido no ticket 23.

## Checklist

- [x] Comprometido = fatura aberta + fechadas não pagas + parcelas futuras; disponível = limite menos ele; recorrência não conta; cartão adicional divide o limite do titular
- [x] Barra na linha do cartão (só com limite informado) e, no detalhe, as três partes, os parcelamentos em andamento e a lista dos próximos 12 meses
- [x] Testes de API com exemplos concretos
- [x] Verificações do projeto rodando e PR aberto para `main`

## Notas

- Do [ticket 39](39-estorno-ajuste-de-fatura-e-cancelamento.md): O estorno (`estorno_de`, ADR 0016) é um lançamento de despesa que diminui: a soma do comprometido usa `VALOR_COM_SINAL` (`app/lancamentos.py`) e o ajuste da fatura (`faturas.ajuste_centavos`) entra no total da fatura fechada.
- Do [ticket 46](46-parcelamento-criar.md): as parcelas futuras do cartão são os lançamentos previstos com `parcelamento_id` num cartão; a parcela vira realizada quando entra na fatura aberta (regra provisória, [ticket 99](99-parcelamento-regras-provisorias.md)).

## Resolução

- API: `GET /api/cartoes/{id}/limite` (`backend/app/limite.py`, testes em `backend/tests/test_limite_do_cartao.py`). O adicional devolve o limite e o comprometido do titular.
- Fatura aberta = compras **realizadas** das faturas ainda não fechadas, com o ajuste; faturas fechadas = o `a_pagar` da última fechada (já carrega o saldo anterior das anteriores); parcelas futuras = lançamentos previstos com `parcelamento_id` nas faturas não fechadas. Previsto sem parcelamento (recorrência) não conta; a recorrência realizada já está na fatura e conta.
- Provisório: a lista dos próximos 12 meses põe cada parte no mês do **vencimento** da fatura em que ela está (o vencimento que já passou cai no mês de hoje; fatura sem vencimento, no mês dela). O ticket 23 diz "a fatura que vence e as parcelas que terminam"; "parcelas que terminam" foi lido como as parcelas futuras das faturas que vencem no mês. O dono confirma se prefere outra leitura.
- Parcela prevista dentro de fatura já fechada (só a importada sem datas) conta na fatura fechada, não em parcelas futuras, para não contar duas vezes.
- Tela: `<details>` na linha do cartão titular com limite informado (barra `progress`, três partes, parcelamentos em andamento e 12 meses). Teste e2e em `web/e2e/cartoes.spec.ts`.
