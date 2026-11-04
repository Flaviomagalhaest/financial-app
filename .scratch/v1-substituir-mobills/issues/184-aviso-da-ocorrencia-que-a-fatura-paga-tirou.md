# Aviso da ocorrência que a fatura paga tirou da geração da recorrência

Type: grilling
Status: ready-for-human
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

- [ ] Decidir com o dono: deixar calado (como hoje), avisar na regra (como o parcelamento mostra a recusa travada) ou gravar a ocorrência excluída para o casal ver
- [ ] Se mudar, implementar com teste em `backend/tests/test_fatura_paga.py` e atualizar a ADR 0021
