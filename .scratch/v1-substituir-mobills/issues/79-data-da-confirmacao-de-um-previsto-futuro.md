# Data da confirmação de um previsto futuro

Type: grilling
Status: resolved
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

- [x] O dono escolhe a regra e ela vai para `## Answer`
- [x] Se a regra mudar (não mudou: o comportamento atual já é a regra, sem código novo): teste de API em `backend/tests/test_previstos.py`, ajuste em `confirmar_lancamento` (`backend/app/lancamentos.py`) e, se precisar, no bloco `ContasDaSemana` do app

## Answer

Decisão do dono: a confirmação traz a **data do previsto como padrão**, com a opção de trocar por **qualquer data**, inclusive a da efetivação (hoje). Não há recusa nem troca automática por hoje. O "Ajustar" segue livre e o lançamento manual não muda.

É exatamente o comportamento atual: o "Confirmar" em um toque mantém a data do previsto, e o "Ajustar" (`ContasDaSemana`) tem o campo Data aceito pela API (`POST /api/lancamentos/{id}/confirmar`, coberto por `test_confirmar_ajusta_valor_data_e_conta`). Nenhuma mudança de código.
