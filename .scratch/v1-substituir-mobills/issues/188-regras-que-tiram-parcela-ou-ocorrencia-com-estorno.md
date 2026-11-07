# Regras que tiram parcela ou ocorrência com estorno

Type: task
Status: resolved
Blocked by: —
Skills: `implement`, `tdd`
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #470
Origem: [ticket 148](148-parcela-com-estorno-quando-a-regra-a-tira.md): decisão do dono sobre a regra que tiraria um lançamento com estorno ([ADR 0016](../../../docs/adr/0016-estorno-e-lancamento-que-diminui-ligado-a-compra.md), adendo do ticket 148); o [ticket 159](159-estorno-de-parte-e-de-parcelas-pendencias.md) juntou o limite do estorno de todas (adendo do ticket 159)

## O que construir

Hoje `lancamentos.excluir` recusa (422) a compra com estorno por qualquer caminho, e as regras que tiram lançamentos quebram no meio. Cada caminho passa a seguir o que o dono decidiu:

- **Correção de parcelamento** (`PATCH /api/parcelamentos/{id}`: menos parcelas, ou a parcela que vira `excluir`/`pular` em `app/parcelamentos.py`): se uma parcela que sairia tem estorno, recusa o pedido (422, dizendo a parcela) **antes de gravar** a correção, como a recusa da fatura paga. Usar o `conferir_sem_estorno` que a exclusão do parcelamento já usa sobre o que sairia. Se o estorno nascer entre a gravação e o refazer, a recusa segue o caminho que já existe para a fatura paga no meio do refazer (tickets 180 e 182).
- **Limite do estorno de todas** (ticket 159): no parcelamento com estorno de todas, a correção (`PATCH /api/parcelamentos/{id}`: total menor, menos parcelas) e a exclusão de uma parcela são recusadas (422, dizendo o já estornado) **antes de gravar** quando a soma das parcelas que ficam (na parte, a soma da parte nelas) ficaria abaixo do já estornado (de todas e de cada parcela). A que não fura o limite passa. É a mesma conta do limite de `_conferir_estorno_de_todas`.
- **Reajuste de recorrência** (`recorrencias._reajustar_um_lote`): o previsto com estorno fica como está por inteiro, como o mexido à mão: não sai nem é refeito, e o lote segue com os outros. A tarefa diária nunca para nele.
- **Exclusão da regra de recorrência** (`excluir_regra`): o previsto com estorno fica, como o realizado e o atrasado; a exclusão da regra nunca é recusada por ele.
- **Correção de fatura** (`compras_excluidas` em `app/correcao_de_fatura.py`): o servidor exclui primeiro os estornos da lista e depois as compras, então a ordem do cliente não importa. A compra cujo estorno não está na lista segue recusada (422), tudo ou nada.
- **Dado antigo**: nada a fazer (sem migração nem acerto na restauração).

## Checklist

- [x] Teste de API: corrigir o parcelamento para menos parcelas com estorno na que sairia volta 422 e não grava nada (parcelamento e parcelas como antes)
- [x] Teste de API: com estorno de todas, corrigir o parcelamento para um total abaixo do estornado, ou excluir a parcela que o deixaria abaixo, volta 422 e não grava nada; a correção e a exclusão que ficam no limite passam
- [x] Teste de API: reajuste e exclusão da regra de recorrência deixam o previsto com estorno e tiram os outros
- [x] Teste de API: correção de fatura com o estorno depois da compra em `compras_excluidas` exclui os dois
- [x] Implementar os cinco caminhos
- [x] Conferir se o app (correção do parcelamento sem internet) precisa mostrar a recusa nova; se precisar, ticket próprio

## Resolução

- Correção do parcelamento: `gravar_correcao` confere, antes de gravar e antes do aviso de realizadas, `conferir_sem_estorno` nas parcelas que saem (`excluir`/`pular`) e `conferir_o_que_fica_do_estorno_de_todas` (soma das parcelas que ficam, e da parte, não abaixo do já estornado). A exclusão de uma parcela pela rota e pelo lote da fila (`da_pessoa=True`) usa a mesma conta.
- Reajuste da recorrência: o previsto com estorno sai do trabalho do lote. Exclusão da regra: a consulta pula o previsto com estorno.
- Correção de fatura: os estornos de `compras_excluidas` saem antes das compras.
- App: a recusa 422 da correção já aparece pelo `erro` da `TelaDoParcelamento` (a correção exige internet); sem ticket novo.
