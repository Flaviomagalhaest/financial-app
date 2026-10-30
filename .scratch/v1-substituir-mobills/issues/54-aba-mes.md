# Aba Mês: fechamento, comparações e ranking

Type: task
Status: resolved
Blocked by: 51, 37
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` se mexer na interface
Modelo recomendado: Opus
Effort recomendado: high
Issue: #108
Origem: [spec da v1](../spec.md), etapa 5; histórias de usuário 122, 123, 124, 125, 126, 127, 128

## O que construir

O casal navega mês a mês, lê o fechamento do mês em texto corrido e compara com o mês anterior e com o mesmo mês do ano passado.

## Checklist

- [x] Mês atual: barra de despesas contra o planejado (realizado, previsto, livre) e receitas recebidas e previstas; mês passado: fechamento em texto corrido
- [x] Planejamento do mês: botões "Copiar do mês anterior" e "Aplicar modelo padrão" e a tela de configurações do modelo (API do [50](50-copiar-planejamento-e-modelo-padrao.md): `POST /api/planejamento/{mes}/copiar`, `GET`/`PUT /api/planejamento/modelo`, `POST /api/planejamento/{mes}/aplicar-modelo`)
- [x] Lista "a escolher" junto dos itens do planejamento, com a escolha num toque (`a_escolher` de `GET /api/planejamento/{mes}` e `PATCH /api/lancamentos/{id}` com `item_categoria_id`, [ticket 51](51-item-do-lancamento-e-a-escolher.md))
- [x] Comparação por categoria contra os dois períodos, com os valores antigos ao tocar na linha; total que conta cada lançamento uma vez
- [x] Ranking por categoria, tag ou pessoa que abre os lançamentos numa folha; barras e listas, sem pizza
- [x] Tudo pelo mês da fatura ([ADR 0003](../../../docs/adr/0003-compra-no-cartao-conta-no-mes-da-fatura.md)); testes de API
- [x] Verificações do projeto rodando e PR aberto para `main`

## Notas

- Do [ticket 39](39-estorno-ajuste-de-fatura-e-cancelamento.md): As despesas do mês (compras menos estornos, mais os ajustes de fatura) e os totais por categoria e por tag (sem o ajuste) saem de `GET /api/meses/{mes}/totais` (`app/meses.py`); o fechamento do mês parte dali, e o ajuste de fatura entra nas despesas dele e não em categoria nem tag.

## Notas da implementação

- **Uma leitura por tela**: `GET /api/meses/{mes}` (`backend/app/meses.py`, testes em `backend/tests/test_aba_mes.py`) devolve o mês já somado pelo mês em que cada lançamento conta (ADR 0003): `situacao` (`passado`, `atual` ou `futuro`, pelo dia de São Paulo), despesas (realizado com os ajustes de fatura, previsto, o planejado dos itens de despesa e o `livre`) e receitas por situação, o planejamento do mês (o mesmo de `GET /api/planejamento/{mes}`, agora `planejamento_do_mes` em `app/planejamento.py`), a comparação por categoria com o mês anterior e o mesmo mês do ano passado (o total conta cada lançamento uma vez, com os ajustes; as linhas não levam o ajuste, ADR 0008), o ranking das despesas por categoria, tag e pessoa com os `lancamento_ids` de cada linha, e o `fechamento` só no mês passado. O app guarda a resposta como as outras leituras e a mostra sem internet com "atualizado às".
- **Fechamento**: conta só o realizado, como o protótipo (o previsto sem confirmar fica de fora e o texto diz quantos são): receitas, despesas, sobra e a porcentagem dela, o guardado (transferências realizadas com categoria), os itens de despesa que passaram do planejado e a variação das despesas. O texto corrido é montado no app (`web/src/mes/apresentacao.ts`).
- **Tela** (`web/src/mes/TelaDoMes.tsx`, rota `#/mes` e `#/mes/<AAAA-MM>`): setas para o mês anterior e o seguinte; no mês passado, o fechamento; no atual e no futuro, a barra das despesas contra o planejado (realizado, previsto riscado e livre, com a marca do planejado) e as receitas recebidas e previstas; a lista "a escolher" com um botão por item (a escolha vai pela fila e já some da lista sem internet); a tabela dos itens com "Ainda dá para gastar" e, no mês sem itens, "Copiar do mês anterior" e "Aplicar modelo padrão" (só com internet); a comparação, que mostra os valores antigos ao tocar no nome da linha; e o ranking em barras (sem pizza), que abre os lançamentos da linha numa folha. O modelo padrão se edita em `#/modelo-do-planejamento` (`TelaDoModelo.tsx`), com o atalho em Configurações.
- **Folha do ranking e "a escolher"** montam os lançamentos a partir de `useLancamentos` (a lista inteira que o aparelho já guarda, com a fila por cima), como o detalhe da fatura do [ticket 55](55-aba-cartoes.md); a leitura do mês traz só os ids.
- **Testes de navegador** em `web/e2e/mes.spec.ts`, num ano antigo conferido como vazio pela API (`anoVazio`), porque os testes dividem o banco; o token da página e o POST de preparo ficaram em `web/e2e/api.ts`, também usado por `cartoes.spec.ts`.
- **Pendências**: as regras provisórias (o que é "guardado", o fechamento só com o realizado, a variação só das despesas, "livre" contra "ainda dá para gastar", os meses futuros e os avisos fora do protótipo) vão para o dono no [ticket 105](105-regras-provisorias-da-aba-mes.md); criar, mudar e excluir um item avulso do mês pela tela fica no [ticket 104](104-itens-do-planejamento-pela-tela.md).
