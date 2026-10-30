# Aviso de planejamento ao lançar

Type: task
Status: resolved
Blocked by: 51, 42
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` se mexer na interface
Modelo recomendado: Opus
Effort recomendado: high
Issue: #106
Origem: [spec da v1](../spec.md), etapa 4; histórias de usuário 25, 26, 27, 28, 29

## O que construir

A cada toque na tela de lançar, o casal vê o efeito no planejamento ("Mercado: 82% → 105% do planejado de out/26"), inclusive sem internet.

## Checklist

- [x] Cálculo puro sobre os totais do mês e o lançamento em edição, compartilhado entre servidor e app e testado por tabela; sem internet roda sobre o cache e a fila
- [x] Mostra quanto ainda dá para gastar ou quanto passa; em compra no cartão, a fatura e o mês que conta; "conta só no total do mês" quando nenhuma categoria tem item
- [x] Com duas ou mais categorias com item, "Conta no planejamento em:" com a última escolha para aquele conjunto, trocável com um toque
- [x] Sem internet, os totais vêm de `web/src/dados/` (ticket 33): a resposta guardada com a fila por cima, como `useLancamentos` faz com a lista
- [x] Testes de tabela e de navegador
- [x] Sem internet, o aviso da compra no cartão precisa da fatura: a regra está só no servidor (`backend/app/faturas.py`, ticket 37). Decidir se o aparelho repete a regra com as faturas guardadas (`GET /api/cartoes/{id}/faturas`) ou mostra o mês só depois do envio (ADR 0011 rejeitou repetir as regras no aparelho)
- [x] Verificações do projeto rodando e PR aberto para `main`

## Notas

- Do [ticket 51](51-item-do-lancamento-e-a-escolher.md): a escolha vai em `item_categoria_id` (a categoria do item, uma das do lançamento) no `POST /api/lancamentos`, no `PATCH` e no lote; "a última escolha para aquele conjunto" sai dos lançamentos guardados, que trazem `item_categoria_id` quando o casal escolheu. A regra de onde o lançamento conta (escolha, item atual, uma categoria só com item) está em `backend/app/item_em_que_conta.py` (`onde_conta`), para o cálculo puro do aviso repetir.

## Notas da implementação

- **Cálculo puro**: `web/src/dados/aviso.ts`. `avisoDePlanejamento(planejamento, antes, depois)` dá, para o mês em que o lançamento conta, as categorias dele com item, se ele fica "a escolher" e o item em que conta, com a porcentagem e o "ainda dá para gastar" antes e depois. Na edição, `antes` é a versão que já conta. `comAFila` põe as mudanças não enviadas sobre o `GET /api/planejamento/{mes}` guardado, somando como o servidor: o estorno diminui, o item estourado não abate a sobra do mês e o ajuste de fatura abate.
- **Compartilhado com o servidor**: as regras que o app repete têm a mesma tabela de casos em `tabelas-de-teste/`. São elas onde o lançamento conta (`onde_conta`), em que fatura cai a compra (`escolher_fatura`, extraída de `mes_da_compra` em `backend/app/faturas.py`) e a porcentagem (`percentual`, extraída de `planejamento.py`, com o meio arredondado para o par como o `round` do Python). O pytest (`tests/test_tabelas_compartilhadas.py`) e o Playwright (`web/e2e/tabelas.spec.ts`, sem navegador) rodam as tabelas. O resto do cálculo tem tabela própria em `web/e2e/aviso.spec.ts`.
- **Sem internet**: `useAvisoDePlanejamento` (`web/src/dados/index.ts`) lê o planejamento do mês como as outras leituras (a resposta guardada) e põe a fila por cima a partir da lista guardada e da fila, como `useLancamentos`. Ao abrir, o app guarda o planejamento do mês anterior, deste e do próximo, além das faturas dos cartões.
- **Decisão da fatura sem internet** ([ADR 0018](../../../docs/adr/0018-aviso-de-planejamento-repete-regras-do-servidor-so-para-mostrar.md)): o aparelho repete a escolha da fatura só para mostrar o aviso. Usa o fechamento das faturas guardadas ou, sem ele, o dia padrão do titular; na parcela n, conta n − 1 faturas depois. Quem grava a fatura e o mês continua sendo o servidor (ADR 0011).
- **Tela**: o aviso fica entre as categorias e o teclado (`web/src/lancamentos/AvisoDePlanejamento.tsx`). Mostra "Mercado: 82% → 105% do planejado de out/26", uma barra do planejado com a parte do lançamento, quanto ainda dá para gastar ou quanto passa (na receita, quanto falta) e, no cartão, "Cai na fatura de 11/2026, que fecha em 25/11, e conta em nov/26". Quando nenhuma categoria tem item: "conta só no total do mês". Com duas ou mais categorias com item, "Conta no planejamento em:" marca a escolha que vale: a tocada, a que o lançamento já tem ou, no lançamento novo, a última escolha para o mesmo conjunto. Sem nenhuma delas, nada fica marcado e o lançamento fica "a escolher".
- **Pendências**: as regras provisórias da escolha ao lançar foram para o dono no [ticket 100](100-conferir-as-regras-do-item-do-lancamento.md). Os casos que o aparelho ainda não sabe (criar talvez já no servidor, cartão arquivado na fila, meses não guardados, textos da receita sem teste, aviso na transferência) ficaram no [ticket 109](109-aviso-de-planejamento-casos-que-o-aparelho-nao-sabe.md).
