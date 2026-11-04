# Fatura paga no meio do refazer da correção do parcelamento

Type: task
Status: resolved
Blocked by: —
Skills: `implement`, `tdd`
Modelo recomendado: Opus
Effort recomendado: medium
Issue: #431
Origem: revisão do [ticket 171](171-correcao-do-parcelamento-nao-mexe-na-fatura-paga.md) (04/11)

## O que construir

A correção do parcelamento confere as faturas pagas lote a lote antes de gravar (`parcelamentos._conferir_os_lotes`, ticket 171), mas os lotes do refazer (`_reajustar_um_lote`) e a geração das parcelas que faltam (`_gerar_um_lote`) não passam por `cartoes.protegida`. Se uma fatura for paga entre a gravação da correção e um lote seguinte (o pedido caiu no meio e a tarefa diária termina depois), a parcela que a correção leva para dentro dela entra, e a fatura paga muda.

A parcela que já está numa fatura paga não é afetada: cada lote recalcula `parcelas_nas_faturas_pagas` e a deixa como está. Só o caso de **entrar** numa fatura paga no meio fica descoberto. A mudança com alcance já trata esse caso (`terminar_o_pendente` com `protegida` e `mudanca_recusada`, ticket 149).

A decidir na implementação: recusar o lote com `protegida` e gravar a recusa no parcelamento, como a mudança com alcance faz (`_desistir_do_conserto` já existe em `completar`), ou deixar a parcela como está.

## Checklist

- [x] Teste de API: a fatura paga entre o pedido que caiu e a tarefa diária não recebe a parcela que a correção levaria para ela
- [x] O casal vê, na tela do parcelamento, que a correção parou e por quê
- [x] Medir o custo de `protegida` por lote no parcelamento longo (tickets 127 e 130)

## Answer

Feito em 04/11, pela recusa (como a mudança com alcance).

- **Os lotes do refazer e a geração passam por `cartoes.protegida`.** `parcelamentos._refazer_protegido` roda cada lote do refazer e cada lote da geração das parcelas que faltam numa transação protegida, no pedido (`refazer_as_parcelas`) e na tarefa diária (`completar`). O lote que levaria uma parcela para dentro de uma fatura paga é recusado: as parcelas que faltavam ficam como estavam e `_desistir_do_conserto` grava em `mudanca_recusada` o motivo seguido de "A correção do parcelamento parou: as parcelas que faltavam corrigir ficaram como estavam".
- **No pedido**, a correção responde 422 com o motivo e "A correção foi gravada e as primeiras parcelas mudaram; as que faltavam ficaram como estavam". Na mudança com alcance que refaz a classificação (`mudar_parcela`), a recusa do refazer também vira 422 com o contexto. A recusa achada ao terminar a correção de outro pedido (`_terminar_o_que_outro_pedido_deixou`) não para a mudança nova.
- **A recusa sai** na próxima correção (`_gravar_e_tirar_a_recusa`) ou mudança com alcance, e quando o conserto da tarefa diária termina (a fatura deixou de estar paga). A correção recusada continua destoando do parcelamento: a tarefa diária tenta de novo a cada dia.
- **Tela.** O aviso da tela do parcelamento mostra o motivo e agora diz também para corrigir o parcelamento de novo quando a correção parou.
- **Custo.** `backend/medir_fatura_paga.py` mede também a correção do parcelamento mais longo (420 parcelas, 83 por lote, 6 lotes do refazer e um da geração), no Postgres 16 local com o volume do ticket 127. Mediana de 5 rodadas: 222 ms com a proteção, 159 ms sem (63 ms a mais no pedido inteiro, uns 9 ms por lote). Não pesa. A latência do DSQL segue no [ticket 130](130-medir-a-protecao-da-fatura-paga-no-dsql.md).
- **Testes.** Testes de API em `backend/tests/test_fatura_paga.py`: o pedido que caiu e a fatura paga antes da tarefa diária; a fatura paga depois da conferência no próprio pedido, com a recusa saindo quando a fatura deixa de estar paga. O `GLOSSARY.md` (**Correção do parcelamento**) e as ADRs [0021](../../../docs/adr/0021-o-pagamento-quita-a-fatura.md) e [0023](../../../docs/adr/0023-alcance-da-mudanca-na-parcela.md) ganharam a regra.

Pendência: [ticket 182](182-recusa-da-correcao-parada-no-meio.md). A recusa não diz em que parcela a correção parou, e a tentativa de cada dia regrava a recusa por cima da de uma mudança com alcance.
