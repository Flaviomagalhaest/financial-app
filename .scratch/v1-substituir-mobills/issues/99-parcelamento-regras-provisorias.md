# Parcelamento: regras provisórias para o dono conferir

Type: grilling
Status: ready-for-human
Blocked by: —
Skills: `grilling` para o dono decidir; depois `implement`, `tdd` se a regra mudar; HITL (decisão de produto)
Modelo recomendado: Sonnet
Effort recomendado: low
Issue: #186
Origem: [ticket 46](46-parcelamento-criar.md) (revisão: a spec não diz quando a parcela no cartão vira realizada, e o 46 fixou alguns valores sem decisão do dono) e [ticket 47](47-parcelamento-editar-regerar-excluir.md) (perguntas 6 a 12)

## As perguntas

1. **Quando a parcela no cartão vira realizada.** Todas as parcelas têm a data da compra, então "realizada na data" faria as N nascerem realizadas. Hoje a 1ª vira realizada na data da compra e a parcela n > 1 quando a fatura de antes fecha, isto é, quando ela entra na fatura aberta (`realiza_em` em `backend/app/parcelamentos.py`, rodado pela tarefa diária). Assim a fatura aberta só tem realizados e as futuras só têm as parcelas previstas, que são as "parcelas futuras" do comprometido ([ticket 56](56-limite-comprometido-do-cartao.md)). Opções:
   - **Como está**: quando a fatura de antes fecha.
   - **Quando a fatura dela fecha**: a parcela da fatura aberta fica prevista até o fechamento.
   - **No primeiro dia do mês da fatura**.
2. **`automatico: false` no cartão é recusado (422)**, porque "o parcelamento no cartão já nasce automático". Alternativa: aceitar e ignorar.
3. **Limite de 420 parcelas** (35 anos, `maximoDeParcelas` em `config/valores-iniciais.json`): o valor só protege a geração de um número sem sentido.
4. **Só despesa**: a receita parcelada (vender algo em 10x) fica de fora; o modelo já tem `tipo`, sem coluna no banco.
5. **Boleto com data no passado**: as parcelas que já passaram nascem previstas e atrasadas (pedindo confirmação) ou, com `automatico`, realizadas. É a mesma pergunta da recorrência no [ticket 87](87-recorrencia-com-inicio-no-passado.md); a parcela passada do cartão nasce realizada quando a fatura de antes já fechou.
6. **Só o número de parcelas mudou: o total fica** (`PATCH /api/parcelamentos/{id}` com `parcelas` e sem valor), e as parcelas se dividem de novo. Alternativa: manter o valor da parcela e o total mudar (comum na compra com juros). Quem quiser o outro manda o valor junto.
7. **A classificação sobrescreve a parcela editada à mão.** Descrição, categorias, tags, pessoa e item valem para todas, como a história 101 pede; só valor, data, conta e fatura ficam como a pessoa pôs. Alternativa: a parcela editada à mão não recebe nada.
8. **Excluir o parcelamento exclui também as realizadas e as editadas à mão, sem aviso do servidor** (a despesa sai do saldo; `DELETE /api/parcelamentos/{id}`). A história 104 fala em desfazer um lançamento feito por engano. Alternativas: pedir `confirmar_realizadas` como na correção, ou preservar as realizadas como a recorrência faz.
9. **Encolher o parcelamento além de uma parcela editada à mão é recusado (422)**, em vez de tirar a parcela com aviso.
10. **A realizada cuja data vai para o futuro segue realizada** (o aviso mostra a data nova). Alternativa: voltar a prevista.
11. **A correção não troca cartão ou conta, nem `automatico`.** O casal exclui e lança de novo. Alternativa: aceitar `conta_id` (refaz a fatura de todas) e `automatico`.
12. **A parcela excluída uma a uma não volta numa correção** (é uma parcela pulada, como o previsto da recorrência); a que sai porque o parcelamento encolheu volta se ele crescer, e a exclusão de uma parcela depois do novo fim, seguida de encolher e crescer, a traz de volta.

## Checklist

- [ ] O dono responde cada pergunta e a resposta vai para `## Answer`
- [ ] Se uma regra mudar: teste de API em `backend/tests/test_parcelamentos.py` e ajuste em `realiza_em`, em `gravar` ou na validação de `NovoParcelamento` (`backend/app/parcelamentos.py`; as 6 a 12 estão em `_mudar`, `_trabalho` e `excluir_parcelamento`), e nos verbetes "Parcela alterada à mão" e "Correção do parcelamento" e no "Automático" do `GLOSSARY.md`
