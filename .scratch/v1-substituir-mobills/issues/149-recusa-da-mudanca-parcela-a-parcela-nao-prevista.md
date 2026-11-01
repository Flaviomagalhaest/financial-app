# Recusa da mudança parcela a parcela que a conferência antes de gravar não prevê

Type: task
Status: resolved
Blocked by: —
Skills: `implement`, `tdd`
Modelo recomendado: Opus
Effort recomendado: medium
Issue: #348
Origem: [ticket 145](145-retomar-a-mudanca-parcela-a-parcela.md): achados da revisão

## O que construir

A mudança com alcance confere, antes de gravar, se alguma das outras parcelas sai de uma fatura paga ou entra numa (`_conferir_faturas_pagas` em `backend/app/mudanca_na_parcela.py`). Ela não confere as outras regras de `cartoes.protegida`, como o pagamento que passaria do valor da fatura quando o valor de uma parcela de fatura fechada e já paga em parte diminui. Também não confere uma fatura que foi paga entre um lote e outro. Quando um lote seguinte é recusado, a rota responde 422 e diz que parte já mudou. Já a tarefa diária tira o pendente e deixa as parcelas que faltam como estavam, sem aviso para o casal.

## Checklist

- [x] Conferir antes de gravar também o pagamento que passaria do valor da fatura, ou simular cada lote antes do primeiro
- [x] A recusa na tarefa diária fica visível para o casal (aviso, registro) em vez de sumir
- [x] `lancamentos.fatura_em_que_ficaria` repete a escolha de `_fatura_depois` sem criar a fatura: juntar as duas num caminho só
- [x] Teste de API para cada recusa coberta

## Notas

- Raro: só acontece num parcelamento com mais de um lote (perto de 80 parcelas) ou num pedido que cai no meio, e com uma fatura paga no caminho.

## Answer

Feito ([ADR 0023](../../../docs/adr/0023-alcance-da-mudanca-na-parcela.md), consequências):

- **Simulação de cada lote antes do primeiro**: `_conferir_antes_de_gravar` monta, lote a lote, as compras que cada parcela tira da fatura em que está e põe na nova (com o sinal de `VALOR_COM_SINAL`), e `cartoes.conferir_sem_gravar` aplica a elas as mesmas regras de `cartoes.protegida` (`_conferir_o_que_mudou`, agora dividida entre as duas), sobre `faturas_do_titular` com `compras_a_mais`. A parcela que sai de uma fatura paga ou entra numa e o pagamento que passaria do valor da fatura recusam o pedido inteiro (422, nada gravado).
- **Recusa visível**: a recusa de um lote seguinte, na rota, na tarefa diária ou ao terminar o pedido anterior, fica gravada no parcelamento (`mudanca_recusada`, migration 0067, formato do backup 29) com a parcela em que a mudança parou. A tela do parcelamento mostra o aviso até a próxima mudança com alcance; a recusa que o próprio pedido acha ao terminar o anterior fica.
- **Escolha da fatura num caminho só**: `fatura_em_que_ficaria` saiu; `onde_ficaria` usa `_fatura_depois` com `criar=False`, que só deixa de criar a fatura.
- **Testes**: de API para o pagamento que passaria do valor num lote seguinte, para a recusa da tarefa diária (gravada e tirada pela mudança seguinte) e para a recusa achada ao terminar o pedido anterior; de restauração do backup do formato 28; e2e do aviso na tela do parcelamento.
- **Pendência**: [153](153-simulacao-sem-as-faturas-que-nasceriam.md) (a simulação não cria as faturas que a mudança faria nascer, nem roda o `_garantir_a_seguinte`).
