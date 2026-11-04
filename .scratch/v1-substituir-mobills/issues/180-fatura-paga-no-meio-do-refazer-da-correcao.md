# Fatura paga no meio do refazer da correção do parcelamento

Type: task
Status: claimed
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

- [ ] Teste de API: a fatura paga entre o pedido que caiu e a tarefa diária não recebe a parcela que a correção levaria para ela
- [ ] O casal vê, na tela do parcelamento, que a correção parou e por quê
- [ ] Medir o custo de `protegida` por lote no parcelamento longo (tickets 127 e 130)
