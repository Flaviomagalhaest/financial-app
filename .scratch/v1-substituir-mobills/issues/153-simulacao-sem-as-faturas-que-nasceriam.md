# Simulação da fatura paga sem as faturas que a mudança faria nascer

Type: task
Status: claimed
Blocked by: —
Skills: `implement`, `tdd`
Modelo recomendado: Opus
Effort recomendado: low
Issue: #359
Origem: [ticket 149](149-recusa-da-mudanca-parcela-a-parcela-nao-prevista.md): achado da revisão

## O que construir

A mudança com alcance simula cada lote das outras parcelas antes de gravar (`cartoes.conferir_sem_gravar`). A simulação soma as compras a mais nas faturas que já existem. Duas coisas que a gravação faz ficam fora dela:

- a compra que cai num mês ainda sem fatura: gravada, ela cria a fatura, e essa fatura recebe o saldo anterior que a paga de antes passa adiante;
- o `_garantir_a_seguinte` de `cartoes.protegida`.

Nesses casos, a regra "o pagamento passa do valor da fatura" de uma fatura seguinte pode dar uma resposta na simulação e outra ao gravar. Quando divergem, o pedido volta ao que fazia antes do ticket 149: a recusa vem no lote seguinte (422 na rota) e fica gravada no parcelamento (`mudanca_recusada`). Nenhum dado fica errado.

## Checklist

- [ ] Simular a fatura que nasceria (datas padrão, saldo anterior da paga de antes) e o `_garantir_a_seguinte`
- [ ] Teste de API com a parcela que cai num mês sem fatura, depois de uma paga que passa saldo adiante

## Notas

- Raro: precisa de um parcelamento com mais de um lote, de uma parcela que vai para um mês sem fatura e de um pagamento nas faturas seguintes.
