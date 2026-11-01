# Edição em lote no meio de uma geração parada faz o parcelamento perder o dia do lançamento

Type: task
Status: claimed
Blocked by: —
Skills: `implement`, `tdd`; apoio: `codebase-design` (como marcar a mudança de calendário)
Modelo recomendado: Opus
Effort recomendado: low
Issue: #312
Origem: revisão (Spec) do [ticket 127](127-envio-no-dia-seguinte-perde-a-de-hoje.md)

## O problema

O ticket 127 conta o "antes de hoje" a partir do dia do lançamento só enquanto a regra é a que o casal lançou, e o teste disso é `alterado_em == criado_em` (`dia_do_lancamento_vigente` em `backend/app/recorrencias.py`). A edição em lote de categorias (`backend/app/edicao_em_lote.py`, `UPDATE parcelamentos SET item_categoria_id ..., alterado_em`) também muda `alterado_em`, sem mudar o calendário, e o desfazer não o volta. Se a geração de um boleto lançado ontem parou antes do primeiro lote e o casal edita em lote antes da tarefa diária, a parcela do dia do lançamento é pulada (conta em `parcelas_puladas`) em vez de nascer realizada. Caso raro: a geração parada quase nunca dura até uma edição em lote.

## Checklist

- [ ] "A regra é a que o casal lançou" passa a olhar só a mudança de calendário (recorrência: PATCH; parcelamento: correção de valor, parcelas ou data), não a de classificação
- [ ] Teste de API: boleto lançado ontem com a geração parada, edição em lote das categorias, tarefa diária: a parcela de ontem nasce realizada
