# Recusa da mudança parcela a parcela que a conferência antes de gravar não prevê

Type: task
Status: claimed
Blocked by: —
Skills: `implement`, `tdd`
Modelo recomendado: Opus
Effort recomendado: medium
Issue: #348
Origem: [ticket 145](145-retomar-a-mudanca-parcela-a-parcela.md): achados da revisão

## O que construir

A mudança com alcance confere, antes de gravar, se alguma das outras parcelas sai de uma fatura paga ou entra numa (`_conferir_faturas_pagas` em `backend/app/mudanca_na_parcela.py`). Ela não confere as outras regras de `cartoes.protegida`, como o pagamento que passaria do valor da fatura quando o valor de uma parcela de fatura fechada e já paga em parte diminui. Também não confere uma fatura que foi paga entre um lote e outro. Quando um lote seguinte é recusado, a rota responde 422 e diz que parte já mudou. Já a tarefa diária tira o pendente e deixa as parcelas que faltam como estavam, sem aviso para o casal.

## Checklist

- [ ] Conferir antes de gravar também o pagamento que passaria do valor da fatura, ou simular cada lote antes do primeiro
- [ ] A recusa na tarefa diária fica visível para o casal (aviso, registro) em vez de sumir
- [ ] `lancamentos.fatura_em_que_ficaria` repete a escolha de `_fatura_depois` sem criar a fatura: juntar as duas num caminho só
- [ ] Teste de API para cada recusa coberta

## Notas

- Raro: só acontece num parcelamento com mais de um lote (perto de 80 parcelas) ou num pedido que cai no meio, e com uma fatura paga no caminho.
