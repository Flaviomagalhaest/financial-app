# Confirmar previsto sem internet pela fila

Type: task
Status: resolved
Blocked by: 43
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando
Modelo recomendado: Opus
Effort recomendado: high
Issue: #157
Origem: [ticket 33](33-lancamento-sem-internet-fila-e-envio.md) (a história 44 pede confirmar sem internet; a fila do 33 leva criar, editar e excluir, e a confirmação do [ticket 43](43-previsto-realizado-e-contas-da-semana.md), em `POST /api/lancamentos/{id}/confirmar`, e o bloco `ContasDaSemana` falam direto com a API)

## O que construir

Confirmar um previsto (com ou sem ajuste de valor, data e conta) entra na fila de `web/src/dados/` e sobe no lote, como as outras mudanças ([ADR 0011](../../../docs/adr/0011-sem-internet-so-lancamentos-e-conflito-decidido-a-mao.md)).

## Checklist

- [x] Ação `confirmar` em `POST /api/lancamentos/lote`, com as regras da rota de confirmar do ticket 43 (ajuste opcional; reenvio igual devolve o gravado; ajuste diferente sobre um já confirmado vira o resultado `conflito` do lote, como a edição do ticket 34). A ação leva a `versao` que o aparelho tinha e só os ajustes que a pessoa fez, como o `ContasDaSemana` já manda para `/confirmar`; o conflito usa a mesma tela de decisão (hoje a confirmação em conflito entra na fila por `guardarConflito`)
- [x] Na fila (no máximo uma mudança por lançamento): confirmar o que ainda não subiu muda o pedido que já está lá; o aparelho mostra o lançamento como realizado ⏳
- [x] `ContasDaSemana` lê e escreve pela camada de dados, com "atualizado às" sem internet
- [x] Teste de navegador: confirmar sem internet, ⏳, envio sem duplicar
- [x] Verificações do projeto rodando e PR aberto para `main`

## Notas

- API: `AcaoConfirmar` em `backend/app/lote.py` (`{"acao": "confirmar", "id", "confirmacao": {versao, valor_centavos?, data?, conta_id?, acao_em?}}`) chama `confirmar` de `backend/app/lancamentos.py`, a mesma função da rota (antes `_confirmar`). Por isso o reenvio igual devolve o gravado, o ajuste diferente sobre um já confirmado vira `conflito`, o ajuste num campo mudado depois da `versao` também, e o excluído vira `descartada`. Testes em `backend/tests/test_conflitos.py`.
- Fila (`web/src/dados/fila.ts`): o item `confirmar` guarda o previsto já realizado, com os ajustes, e a `base` que a tela mostrava; ele sobe só com os ajustes que diferem da base. Se já há uma mudança não enviada, `enfileirarConfirmar` muda o pedido que está lá: o criar sobe realizado, e a edição leva a situação. Editar depois, sem mudar a data, mantém a situação escolhida antes, à mão ou ao confirmar (`pedidoDeSalvar`). Isso também corrige a edição seguinte de um não enviado com a situação escolhida à mão. O conflito da confirmação cai em `decidirConflito`, como o da edição; o `guardarConflito` do ticket 43 saiu.
- Contas da semana: com o merge do [ticket 53](53-aba-hoje.md), o bloco recebe da `TelaHoje` a lista `contas_da_semana` da leitura guardada de `GET /api/hoje`, com a fila por cima (`useContasDaSemana`). A janela é a mesma do servidor (`naSemana`, `contasDaSemanaDias`): o previsto criado sem internet entra, o confirmado sai, o mudado de data entra ou sai. O conflito e a recusa de uma conta da semana ficam no bloco, com "Decidir" e o motivo. O resultado do envio acerta a `/api/hoje` guardada, inclusive pelo service worker, para o confirmado não voltar ao bloco antes de a Hoje ser lida de novo. A contagem de atrasados da Hoje usa a mesma lista. O "atualizado às" é o da Hoje (`atualizado-em`).
- Teste de navegador em `web/e2e/contas-da-semana.spec.ts`: confirmar sem internet em um toque, com ajuste e sobre um previsto lançado sem internet; ⏳ no Histórico; editar sem desfazer; resposta do lote perdida e reenvio sem duplicar; saldo certo. O de conflito (`conflito.spec.ts`, do 43) passa pela fila.
- Pendências gravadas: a rota `GET /api/contas-da-semana` ficou sem uso no app ([ticket 104](104-rota-das-contas-da-semana-sem-uso.md)). O saldo e o "ainda dá para gastar" com a confirmação não enviada ficam no [ticket 81](81-saldo-conta-os-nao-enviados.md).
