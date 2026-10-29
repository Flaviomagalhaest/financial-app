# Parcelamento: regras provisórias para o dono conferir

Type: grilling
Status: ready-for-human
Blocked by: —
Skills: `grilling` para o dono decidir; depois `implement`, `tdd` se a regra mudar; HITL (decisão de produto)
Modelo recomendado: Sonnet
Effort recomendado: low
Issue: #186
Origem: [ticket 46](46-parcelamento-criar.md) (revisão: a spec não diz quando a parcela no cartão vira realizada, e o 46 fixou alguns valores sem decisão do dono)

## As perguntas

1. **Quando a parcela no cartão vira realizada.** Todas as parcelas têm a data da compra, então "realizada na data" faria as N nascerem realizadas. Hoje a 1ª vira realizada na data da compra e a parcela n > 1 quando a fatura de antes fecha, isto é, quando ela entra na fatura aberta (`realiza_em` em `backend/app/parcelamentos.py`, rodado pela tarefa diária). Assim a fatura aberta só tem realizados e as futuras só têm as parcelas previstas, que são as "parcelas futuras" do comprometido ([ticket 56](56-limite-comprometido-do-cartao.md)). Opções:
   - **Como está**: quando a fatura de antes fecha.
   - **Quando a fatura dela fecha**: a parcela da fatura aberta fica prevista até o fechamento.
   - **No primeiro dia do mês da fatura**.
2. **`automatico: false` no cartão é recusado (422)**, porque "o parcelamento no cartão já nasce automático". Alternativa: aceitar e ignorar.
3. **Limite de 420 parcelas** (35 anos, `maximoDeParcelas` em `config/valores-iniciais.json`): o valor só protege a geração de um número sem sentido.
4. **Só despesa**: a receita parcelada (vender algo em 10x) fica de fora; o modelo já tem `tipo`, sem coluna no banco.
5. **Boleto com data no passado**: as parcelas que já passaram nascem previstas e atrasadas (pedindo confirmação) ou, com `automatico`, realizadas. É a mesma pergunta da recorrência no [ticket 87](87-recorrencia-com-inicio-no-passado.md); a parcela passada do cartão nasce realizada quando a fatura de antes já fechou.

## Checklist

- [ ] O dono responde cada pergunta e a resposta vai para `## Answer`
- [ ] Se uma regra mudar: teste de API em `backend/tests/test_parcelamentos.py` e ajuste em `realiza_em`, em `gravar` ou na validação de `NovoParcelamento` (`backend/app/parcelamentos.py`), e no verbete "Automático" do `GLOSSARY.md`
