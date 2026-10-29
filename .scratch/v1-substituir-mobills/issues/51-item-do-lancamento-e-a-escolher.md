# Item em que o lançamento conta e lista "a escolher"

Type: task
Status: resolved
Blocked by: 49
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` se mexer na interface
Modelo recomendado: Opus
Effort recomendado: high
Issue: #105
Origem: [spec da v1](../spec.md), etapa 4; histórias de usuário 114, 115, 116, 111

## O que construir

Cada lançamento conta em no máximo um item do planejamento, sem contar o mesmo dinheiro duas vezes ([ADR 0006](../../../docs/adr/0006-varias-categorias-e-um-item-do-planejamento.md)).

## Checklist

- [x] Conta automaticamente quando só uma das categorias tem item; escolha explícita nunca muda sozinha
- [x] Ambiguidade que surge depois (item criado no meio do mês, planejamento copiado, categorias editadas) mantém o item atual e entra na lista "a escolher"
- [x] Recorrência e parcelamento guardam a escolha e os previstos já nascem com ela
  - A recorrência guarda a escolha na coluna `item_id` do [ticket 45](45-recorrencia-mudar.md): `_gerar_um_lote` a copia para o previsto novo e `_reajustar_um_lote` a refaz quando a regra muda (veja as notas)
- [x] Testes de API para cada caminho
- [x] Juntar categorias (`POST /api/categorias/{id}/juntar`) também move as escolhas de item, e a leitura do planejamento (`GET /api/planejamento/{mes}`, ticket 49) passa a contar o lançamento com mais de uma categoria com item no item escolhido; hoje ele não conta em nenhum
- [x] Verificações do projeto rodando e PR aberto para `main`

## Notas da implementação

- **Onde fica a escolha**: pela categoria, não pelo id do item, para valer em qualquer mês, na cópia do planejamento e na recorrência. O lançamento guarda `item_categoria_id` (a escolha do casal; migration 0046) e `item_atual_categoria_id` (o item em que ele contava sozinho quando a ambiguidade surgiu, que só o servidor grava; migration 0047). A regra está em `backend/app/item_em_que_conta.py`: a escolha vale quando a categoria dela tem item no mês; senão, o item atual, se ainda tem item; senão, conta sozinho quando só uma categoria tem item; com duas ou mais, está "a escolher".
- **Ficar onde estava**: `guardar_item_atual` grava o item atual antes do que cria ambiguidade: criar item no mês (`criar_item`), editar o lançamento (categorias, data, conta, fatura), confirmar com troca de mês, a fatura escolhida de novo pelas datas do cartão (`mudar_fatura`) e juntar categorias. Copiar o planejamento e aplicar o modelo só gravam em mês vazio, onde ninguém contava em item. Esse registro não sobe a versão do lançamento: não é mudança de ninguém.
- **API**: `item_categoria_id` em `POST /api/lancamentos`, no `PATCH` e no lote (uma das categorias do lançamento, senão 422 "o item escolhido não é de uma categoria do lançamento"); é campo versionado do conflito (ADR 0011), com rótulo "Item do planejamento" na tela de conflito e em `CAMPOS` da fila (`web/src/dados/fila.ts`, que não manda a escolha vazia). A escolha sai quando a categoria dela sai do lançamento. `GET /api/planejamento/{mes}` traz `a_escolher`: `lancamento_id`, `item_categoria_id` (o item em que ele conta enquanto ninguém escolhe, ou null) e `categorias_com_item`.
- **Recorrência**: `item_categoria_id` na regra, guardado na coluna `item_id` que o [ticket 45](45-recorrencia-mudar.md) criou (migration 0039; o campo da API mudou de nome e passou a ser conferido). Os previstos nascem com a escolha, e mudar "daqui para frente" a leva aos previstos que ninguém alterou à mão. **Parcelamento**: `item_categoria_id` (migration 0048), com que as parcelas nascem.
- **Estorno**: nasce com a escolha da compra ou, sem ela, com o item em que a compra conta sozinha, para diminuir o mesmo item (ADR 0016).
- **Juntar categorias** move as escolhas e os itens atuais dos lançamentos e as escolhas das recorrências e dos parcelamentos, e passou a mover também as categorias das recorrências e dos parcelamentos (antes ficavam com a categoria apagada).
- Backup na versão 17, com o conversor da 16.
- **Pendências**: as regras provisórias acima vão para o dono no [ticket 100](100-conferir-as-regras-do-item-do-lancamento.md); a escolha nas telas fica nos tickets [52](52-aviso-de-planejamento-ao-lancar.md) (ao lançar), [53](53-aba-hoje.md) e [54](54-aba-mes.md) (lista "a escolher"), com notas novas da API; o limite de linhas por transação do DSQL ao criar item ou juntar categoria com muito histórico, linha nova no [35](35-teste-nos-dois-celulares.md).
