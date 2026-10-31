# Edição em lote e desfazer

Type: task
Status: resolved
Blocked by: 59, 51
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` se mexer na interface
Modelo recomendado: Opus
Effort recomendado: high
Issue: #115
Origem: [spec da v1](../spec.md), etapa 5; histórias de usuário 147, 148, 149, 150, 151

## O que construir

O casal acerta o histórico importado trocando categorias e tags de muitos lançamentos de uma vez.

## Checklist

- [x] Marcar lançamentos ou todos do resultado; acrescentar, remover, trocar ou substituir categorias e tags; selecionar parcelada seleciona o parcelamento todo, com a contagem
- [x] Prévia (quantos mudam, os 5 primeiros antes e depois, quantos já estão como pedido, quantos trocam de item do planejamento); tudo ou nada; recusa lote que deixaria despesa ou receita sem categoria
- [x] Desfazer por 30 dias, pulando e avisando o que outra pessoa mudou depois; só com internet
- [x] Testes de API
- [x] Verificações do projeto rodando e PR aberto para `main`

## Notas da implementação

- **API** (`backend/app/edicao_em_lote.py`, testes em `backend/tests/test_edicao_em_lote.py`): `POST /api/edicoes-em-lote/previa`, `POST /api/edicoes-em-lote` (com o `id` do aparelho), `GET /api/edicoes-em-lote` e `POST /api/edicoes-em-lote/{id}/desfazer`. A seleção são os marcados (`lancamento_ids`, `parcelamento_ids`) ou todos do resultado (`busca`, que usa `lancamentos_do_resultado` de `app/busca.py`, sem as transferências); a parcela leva o parcelamento todo e a compra leva os estornos dela. A mudança é de categorias ou de tags (ou das duas), com acrescentar, remover, trocar (`por`) ou substituir. A prévia traz compras, lançamentos, quantos mudam, quantos já estão como pedido, de outro tipo, quantos trocam de item do planejamento (`onde_conta`, ADR 0006), estornos de fora, a amostra (`amostraDaEdicaoEmLote`) e a `recusa` do lote que deixaria lançamento sem categoria.
- **Tudo ou nada no DSQL** (ADR 0009, ADR 0012): o lote grava em partes de `POR_TRANSACAO` lançamentos, uma transação cada, sobre o que cada lançamento tem na hora; uma parte recusada desfaz as anteriores com o mesmo código do desfazer, e o lote fica `cancelada` com o motivo (o reenvio do mesmo id devolve a recusa). Cada lançamento sobe a versão e registra em `lancamento_campos` os campos mudados, então a fila de outro aparelho vê a mudança como do outro lado (ADR 0011).
- **Desfazer** por `desfazerEdicaoEmLoteDias`: volta categorias, tags, a escolha do item e o item atual guardados em `edicao_em_lote_lancamentos`; pula, dizendo quem e quando, o lançamento excluído, o que teve categorias, tags ou item mudados depois e o que tinha uma categoria ou tag juntada ou excluída. O parcelamento muda junto a classificação que guarda (`edicao_em_lote_parcelamentos`), que a correção do parcelamento usa nas parcelas que voltam (revisão do ticket), e volta se ninguém a mudou depois.
- **Backup v20** com as três tabelas (migrations `0051` a `0053`), conversor da v19 e teste de restauração.
- **Tela** (`web/src/busca/`): "Selecionar para editar em lote" na busca, com a caixa em cada linha, "Todos do resultado", "Limpar seleção" e "Editar em lote"; a folha (`FolhaDaEdicaoEmLote`) escolhe categorias ou tags e a ação, mostra a prévia e aplica; `#/edicoes-em-lote` (`TelaDasEdicoesEmLote`) lista as que ainda se desfazem, com "Desfazer" e os pulados. Tudo só com internet, pela camada de dados (`verPreviaDoLote`, `aplicarLote`, `useEdicoesEmLote`, `desfazerLote`), que depois lê de novo a lista, as tags e o índice de sugestão. Teste de navegador em `web/e2e/edicao-em-lote.spec.ts`.
- **Revisão** (Standards e Spec em sub-agentes): amostra para a configuração, gravação comum ao aplicar e ao desfazer, a regra do parcelamento acompanhando o lote, e os achados de duplicação e nomes na tela.
- **Pendências**: as regras provisórias vão para o dono no [ticket 116](116-edicao-em-lote-regras-provisorias.md) (inclusive o desfazer pular o que a própria pessoa mudou, contra o "outra pessoa" da história 151); o lote que para no meio e a compensação com mudança concorrente ficam no [ticket 117](117-edicao-em-lote-interrompida.md); medir no DSQL um lote grande entrou no [ticket 35](35-teste-nos-dois-celulares.md). A reserva foi feita na própria branch que o ambiente designou, como nas sessões anteriores na nuvem.
