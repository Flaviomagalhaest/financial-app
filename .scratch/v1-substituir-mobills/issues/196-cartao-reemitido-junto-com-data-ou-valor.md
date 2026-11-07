# Cartão reemitido em "todas" junto com a data ou o valor, e a recusa no meio

Type: task
Status: ready-for-human
Blocked by: —
Skills: `grilling` (HITL: a Q1 é do dono); depois `implement`, `tdd`
Modelo recomendado: Opus
Effort recomendado: medium
Issue: #494
Origem: [ticket 187](187-conta-em-todas-vai-para-o-parcelamento.md): revisão de Spec da implementação (a conta em "todas" vai para o parcelamento)

## O problema

Com o ticket 187, a conta mudada em "todas" para outra do mesmo tipo vai para o parcelamento na transação do pedido, e as outras parcelas mudam de conta em lotes, sem a marca de "alterada à mão". Ficaram dois casos sem verificação:

1. **Conta junto com a data ou o valor no mesmo pedido.** A correção do parcelamento (`gravar_correcao`) roda antes de a conta mudar, e simula as regras da fatura paga (`_conferir_os_lotes`) com as parcelas no cartão antigo e a data nova. A conferência dos lotes da conta (`_conferir_antes_de_gravar`) simula o cartão novo com a data antiga. A combinação aplicada no fim (cartão novo e data nova) nunca é conferida antes de gravar. O pedido pode ser recusado por uma fatura paga do cartão antigo que não importa, ou passar e parar no meio do refazer, com a recusa do ticket 180.
2. **Lote seguinte recusado.** Se a fatura em que uma parcela entraria no cartão novo é paga entre um lote e outro, a mudança para (`mudanca_recusada`). O parcelamento já está no cartão novo, e as parcelas que faltavam ficam no antigo, sem marca: na tela, parecem seguir o parcelamento, mas estão noutro cartão. A fatura delas segue o cartão em que estão (o ticket 187 trocou `_correcoes` para calcular o mês pela conta da parcela), mas a próxima correção não as leva ao cartão novo.

## Perguntas ao dono

- **Q1**: no caso 2, as parcelas que ficaram no cartão antigo devem ganhar a marca de conta mudada à mão, ficar como estão (o casal vê a recusa e muda de novo com "todas"), ou o parcelamento deve voltar ao cartão antigo?

## Checklist

- [ ] Q1 decidida pelo dono
- [ ] Simular a combinação final (cartão novo com a data e o valor novos) antes de gravar, quando o pedido em "todas" muda a conta junto com a data ou o valor
- [ ] Teste: cartão reemitido e data nova em "todas", com uma fatura paga só no cartão novo; o pedido é recusado antes de gravar
- [ ] Teste do caso 2, conforme a Q1
- [ ] Verificações do projeto e PR para `main`
