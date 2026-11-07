# Aviso da ocorrência que a fatura paga tirou da geração da recorrência

Type: grilling
Status: resolved
Blocked by: —
Skills: `grilling` e `domain-modeling` (HITL: o dono decide se o casal é avisado e como); apoio: `implement`, `tdd`
Modelo recomendado: Opus
Effort recomendado: low
Issue: #443
Origem: revisão (Spec) do [ticket 179](179-reenvio-da-recorrencia-depois-do-pagamento.md)

## A pergunta

O 179 fez a geração passar, sem virar lançamento, pela ocorrência de antes de hoje que cairia numa fatura paga depois da criação da regra (o pagamento chegou entre a conferência e o primeiro lote, ou entre os lotes; `_gerar_um_lote` em `backend/app/recorrencias.py`). O casal não fica sabendo: o reenvio da fila sai como os outros, enquanto a mesma regra lançada depois do pagamento seria recusada com o aviso da fatura paga. E, passada a ocorrência (`geradas` andou), desfazer o pagamento não a traz de volta.

É raro (pede um pagamento exatamente no meio da geração), mas a ocorrência do dia do lançamento, que nasceria realizada, some calada.

## Checklist

- [x] Decidir com o dono: deixar calado (como hoje), avisar na regra (como o parcelamento mostra a recusa travada) ou gravar a ocorrência excluída para o casal ver
- [x] Implementação nos tickets 192 (servidor) e 193 (tela)

## Answer

Decidido com o dono (grilling): avisar na regra.

1. A ocorrência pulada pela fatura paga deixa um aviso de texto na recorrência, no padrão de `mudanca_recusada` do parcelamento.
2. O aviso só informa (data, titular e mês da fatura, "lance à mão se precisar"); não refaz a ocorrência nem volta `geradas`.
3. Fica até o casal dispensar; outra ocorrência pulada antes disso junta a data no mesmo aviso.
4. Só na tela da regra, fora da aba inicial.
5. Termo novo no glossário: "ocorrência pulada pela fatura paga", com a ADR 0021 atualizada.

Implementação: [192](192-recorrencia-grava-o-aviso-da-ocorrencia-pulada.md) (servidor, ADR, glossário) e [193](193-tela-da-regra-mostra-o-aviso-da-ocorrencia-pulada.md) (tela).
