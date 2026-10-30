# Aba Mês: fechamento, comparações e ranking

Type: task
Status: claimed
Blocked by: 51, 37
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` se mexer na interface
Modelo recomendado: Opus
Effort recomendado: high
Issue: #108
Origem: [spec da v1](../spec.md), etapa 5; histórias de usuário 122, 123, 124, 125, 126, 127, 128

## O que construir

O casal navega mês a mês, lê o fechamento do mês em texto corrido e compara com o mês anterior e com o mesmo mês do ano passado.

## Checklist

- [ ] Mês atual: barra de despesas contra o planejado (realizado, previsto, livre) e receitas recebidas e previstas; mês passado: fechamento em texto corrido
- [ ] Planejamento do mês: botões "Copiar do mês anterior" e "Aplicar modelo padrão" e a tela de configurações do modelo (API do [50](50-copiar-planejamento-e-modelo-padrao.md): `POST /api/planejamento/{mes}/copiar`, `GET`/`PUT /api/planejamento/modelo`, `POST /api/planejamento/{mes}/aplicar-modelo`)
- [ ] Lista "a escolher" junto dos itens do planejamento, com a escolha num toque (`a_escolher` de `GET /api/planejamento/{mes}` e `PATCH /api/lancamentos/{id}` com `item_categoria_id`, [ticket 51](51-item-do-lancamento-e-a-escolher.md))
- [ ] Comparação por categoria contra os dois períodos, com os valores antigos ao tocar na linha; total que conta cada lançamento uma vez
- [ ] Ranking por categoria, tag ou pessoa que abre os lançamentos numa folha; barras e listas, sem pizza
- [ ] Tudo pelo mês da fatura ([ADR 0003](../../../docs/adr/0003-compra-no-cartao-conta-no-mes-da-fatura.md)); testes de API
- [ ] Verificações do projeto rodando e PR aberto para `main`

## Notas

- Do [ticket 39](39-estorno-ajuste-de-fatura-e-cancelamento.md): As despesas do mês (compras menos estornos, mais os ajustes de fatura) e os totais por categoria e por tag (sem o ajuste) saem de `GET /api/meses/{mes}/totais` (`app/meses.py`); o fechamento do mês parte dali, e o ajuste de fatura entra nas despesas dele e não em categoria nem tag.
