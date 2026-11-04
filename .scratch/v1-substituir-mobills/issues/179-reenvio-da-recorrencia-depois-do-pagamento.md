# Reenvio da recorrência depois do pagamento entre os lotes da geração

Type: task
Status: resolved
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

- [x] Decidir o conserto: a geração não cria ocorrência de antes de hoje em fatura paga (sai como pulada?), ou a conferência e as ocorrências de antes de hoje vão na mesma transação da regra
- [x] Teste de API em `backend/tests/test_fatura_paga.py`

## Resolução

A geração (`_gerar_um_lote`) passa pela ocorrência de antes de hoje que cairia numa fatura paga, como passa pela de antes do lançamento (ticket 87): `geradas` anda, nenhum lançamento nasce e a ocorrência segue contando no calendário e nas `vezes`. A conferência na criação continua recusando a regra inteira quando a fatura já está paga; a geração cobre o pagamento que chega depois dela, entre a conferência e o primeiro lote ou entre os lotes, em qualquer lote. Pôr a conferência e as ocorrências de antes de hoje na mesma transação da regra foi descartado: o lote tem limite de linhas, e as de antes de hoje podem não caber nele.

Testes: `test_reenvio_depois_do_pagamento_nao_gera_o_passado_dentro_da_fatura_paga` (pago entre a conferência e o primeiro lote) e `test_pagamento_entre_os_lotes_nao_leva_o_resto_do_passado_para_a_fatura_paga`.

Pendência: a ocorrência passa sem aviso ao casal ([ticket 184](184-aviso-da-ocorrencia-que-a-fatura-paga-tirou.md)).
