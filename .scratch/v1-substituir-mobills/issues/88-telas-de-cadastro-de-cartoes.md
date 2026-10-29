# Telas de cadastro de cartões e das datas da fatura

Type: task
Status: ready-for-agent
Blocked by: 37
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design`
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #164
Origem: [ticket 37](37-cartoes-e-faturas.md): a API de cartões e faturas existe (`/api/cartoes`, `GET /api/cartoes/{id}/faturas`, `PATCH /api/cartoes/{id}/faturas/{mes}`), mas nenhuma tela cadastra cartão nem acerta as datas de uma fatura; nenhum outro ticket cobre essas telas (o [55](55-aba-cartoes.md) é a aba de consulta e o [42](42-jornada-completa-do-lancamento-rapido.md), a fileira do lançamento)

## O que construir

Na configuração, junto das contas (`#/contas-e-categorias`, ticket 74), o casal cadastra, edita e arquiva cartões e acerta o fechamento e o vencimento de uma fatura, só com internet ([ADR 0011](../../../docs/adr/0011-sem-internet-so-lancamentos-e-conflito-decidido-a-mao.md)).

## Checklist

- [ ] Cartão titular: nome, dia de fechamento e de vencimento padrão, limite opcional e "conta no mês anterior ao fechamento"; cartão adicional ligado a um titular (sem dias nem limite próprios); arquivar e desarquivar
- [ ] Mudar o dia padrão avisa que só as faturas abertas e futuras mudam e que as compras delas vão para a fatura certa
- [ ] Acertar o fechamento e o vencimento de uma fatura (a atual, a próxima ou outra pelo mês), com o aviso de que as compras se redistribuem
- [ ] Botões desativados com "precisa de internet" sem rede (história 53)
- [ ] Testes de navegador
- [ ] Verificações do projeto rodando e PR aberto para `main`
