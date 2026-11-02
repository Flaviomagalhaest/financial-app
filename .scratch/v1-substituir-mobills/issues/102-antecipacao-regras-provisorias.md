# Antecipação e quitação: regras provisórias para o dono conferir

Type: grilling
Status: resolved
Blocked by: —
Skills: `grilling` para o dono decidir; depois `implement`, `tdd` se a regra mudar; HITL (decisão de produto)
Modelo recomendado: Sonnet
Effort recomendado: low
Issue: #197
Origem: [ticket 48](48-antecipar-e-quitar.md) (revisão: a spec diz "data de hoje ou outra" e "valor editável", e o 48 fixou algumas regras sem decisão do dono)

## As perguntas

1. **Data da antecipação.** Hoje a data não pode ser futura (422), porque a parcela antecipada já nasce realizada. A história 99 diz "hoje ou outra". Aceitar data futura deixaria a parcela prevista, e a tarefa diária a realizaria na data.
2. **O valor editável é o total das K parcelas**, dividido por igual, com os centavos que sobram na primeira antecipada. A alternativa é um valor por parcela.
3. **A parcela antecipada muda de `data`** para o dia do pagamento e, no cartão, passa à fatura que fecha depois dele (troca à mão), em vez de guardar a data da compra do parcelamento. No boleto, o `mes` vira o do pagamento.
4. **Reenvio do pedido.** A rota não leva chave de idempotência: repetir uma antecipação depois de resposta perdida antecipa as K parcelas seguintes, e repetir uma quitação dá 422. A fila sem internet (como o `criar_parcelamento` do 46) pede uma chave, por exemplo o id da antecipação gerado no aparelho.
5. **Quitar sem nada a pagar** dá 422 ("não há tantas parcelas por pagar"); a alternativa é uma resposta vazia.

## Checklist

- [x] O dono responde cada pergunta e a resposta vai para `## Answer`
- [x] Nenhuma regra existente mudou; a nova (chave) está no ticket 154

## Answer

1. **Data**: mantida. Só hoje ou passada (422 para futura).
2. **Valor editável**: mantido como total das K parcelas, dividido por igual, centavos na primeira.
3. **Data/fatura da parcela antecipada**: mantido (dia do pagamento; no cartão, fatura que fecha depois; boleto, mês do pagamento).
4. **Reenvio**: o dono quer a chave de idempotência. Vira o [ticket 154](154-antecipacao-chave-de-idempotencia.md).
5. **Quitar sem nada a pagar**: não houve resposta explícita; fica o 422 (padrão recomendado). O dono pode reabrir.
