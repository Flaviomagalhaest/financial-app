# Cartão reemitido em "todas" junto com a data ou o valor, e a recusa no meio

Type: task
Status: resolved
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
  - **Decidido (2026-11-07)**: ficam como estão, sem marca, e o casal repete "todas". Para a repetição sair limpa, em "todas" a conta pedida que já é a do parcelamento leva as parcelas que estão noutra conta do mesmo tipo a seguir o parcelamento sem a marca de "alterada à mão" (como no ticket 187). O texto da recusa diz que as parcelas que faltavam ficaram no cartão antigo. Voltar o parcelamento ao cartão antigo foi descartado: a volta pode ser recusada por uma fatura paga do cartão antigo.

## Checklist

- [x] Q1 decidida pelo dono
- [x] Simular a combinação final (cartão novo com a data e o valor novos) antes de gravar, quando o pedido em "todas" muda a conta junto com a data ou o valor
- [x] Teste: cartão reemitido e data nova em "todas", com uma fatura paga só no cartão novo; o pedido é recusado antes de gravar
- [x] Teste do caso 2, conforme a Q1
- [ ] Verificações do projeto e PR para `main`

## Resolução

- `_mudar_a_parcela` (`backend/app/mudanca_na_parcela.py`): quando a conta do mesmo tipo em "todas" vem com a data ou o valor, a correção é conferida num savepoint com o parcelamento e as parcelas que faltam já na conta nova (`_por_no_cartao_novo`), e a correção de verdade grava sem conferir de novo os lotes (`gravar_correcao(conferir_os_lotes=False)`). A troca de conta continua conferida com a data de antes (`_conferir_antes_de_gravar`).
- Caso 2 (Q1, opção B): a conta pedida em "todas" que já é a do parcelamento leva as parcelas que ficaram na antiga sem a marca. Isso também vale com a data ou o valor, com a mesma simulação. A recusa gravada no parcelamento e a resposta do pedido dizem que as que faltavam ficaram no cartão antigo (ou na conta antiga) e como levá-las.
- Testes em `backend/tests/test_alcance_da_mudanca_na_parcela.py`: a fatura paga só no cartão novo recusa antes de gravar; a paga só no antigo não recusa; a recusa no meio (na tarefa diária e no próprio pedido) deixa as que faltavam no antigo sem marca; e o "todas" de novo as leva, inclusive com a data nova.
- ADR 0023: consequência nova.
