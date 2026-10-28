# Data da confirmação de um previsto futuro

Type: grilling
Status: ready-for-human
Blocked by: —
Skills: `grilling` para o dono decidir; depois `implement`, `tdd` se a regra mudar; HITL (decisão de produto)
Modelo recomendado: Sonnet
Effort recomendado: low
Issue: #152
Origem: [ticket 43](43-previsto-realizado-e-contas-da-semana.md) (revisão: a confirmação aceita qualquer data, e o "Confirmar" em um toque mantém a data do previsto)

## A pergunta

As contas da semana mostram previstos dos próximos 7 dias. Quem paga hoje a conta que vence daqui a 3 dias e toca "Confirmar" deixa um **realizado com data futura**: a data do previsto fica, e o valor já entra no saldo da conta. O "Ajustar" também aceita uma data futura.

Hoje a API (`POST /api/lancamentos/{id}/confirmar`) aceita isso, e o lançamento manual também (história 19: "podendo trocar à mão").

## Opções

- **Deixar como está**: a confirmação mantém a data do previsto; quem pagou antes ajusta a data.
- **Confirmar em um toque usa hoje quando o previsto é futuro**: a data vira a de hoje, e o "Ajustar" continua livre.
- **Recusar realizado com data futura na confirmação** (422), deixando o lançamento manual como está.

## Checklist

- [ ] O dono escolhe a regra e ela vai para `## Answer`
- [ ] Se a regra mudar: teste de API em `backend/tests/test_previstos.py`, ajuste em `confirmar_lancamento` (`backend/app/lancamentos.py`) e, se precisar, no bloco `ContasDaSemana` do app
