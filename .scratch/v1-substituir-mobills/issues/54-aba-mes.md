# Aba Mês: fechamento, comparações e ranking

Type: task
Status: ready-for-agent
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
- [ ] Comparação por categoria contra os dois períodos, com os valores antigos ao tocar na linha; total que conta cada lançamento uma vez
- [ ] Ranking por categoria, tag ou pessoa que abre os lançamentos numa folha; barras e listas, sem pizza
- [ ] Tudo pelo mês da fatura ([ADR 0003](../../../docs/adr/0003-compra-no-cartao-conta-no-mes-da-fatura.md)); testes de API
- [ ] Verificações do projeto rodando e PR aberto para `main`
