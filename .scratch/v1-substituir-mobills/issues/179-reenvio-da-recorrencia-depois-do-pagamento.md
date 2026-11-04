# Reenvio da recorrência depois do pagamento entre os lotes da geração

Type: task
Status: claimed
Blocked by: —
Skills: `implement`, `tdd`
Modelo recomendado: Opus
Effort recomendado: medium
Issue: #429
Origem: revisão (Spec) do [ticket 172](172-recorrencia-no-cartao-respeita-a-fatura-paga.md)

## O problema

A criação da recorrência no cartão confere as faturas pagas antes de gravar a regra (`_conferir_as_faturas_do_passado` em `backend/app/recorrencias.py`), mas a geração roda depois, em outras transações. Se a geração para no meio, a fatura de uma ocorrência de antes de hoje é paga e a fila reenvia, `_gravar` devolve a regra gravada sem conferir e `gerar_ate_o_horizonte` continua com o "antes de hoje" do dia do lançamento (`dia_do_lancamento_vigente`): as ocorrências que faltavam nascem dentro da fatura paga. O mesmo vale para um pagamento que chega entre a conferência e o primeiro lote.

É raro (as ocorrências de antes de hoje estão no primeiro lote, e o pagamento teria de cair exatamente no meio), mas é um caminho que muda uma fatura paga sem a proteção da [ADR 0021](../../../docs/adr/0021-o-pagamento-quita-a-fatura.md).

## Checklist

- [ ] Decidir o conserto: a geração não cria ocorrência de antes de hoje em fatura paga (sai como pulada?), ou a conferência e as ocorrências de antes de hoje vão na mesma transação da regra
- [ ] Teste de API em `backend/tests/test_fatura_paga.py`
