# Telas de estorno, ajuste de fatura e compra cancelada

Type: task
Status: resolved
Blocked by: 55, 88
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design`
Modelo recomendado: Sonnet
Effort recomendado: high
Issue: #181
Origem: [ticket 39](39-estorno-ajuste-de-fatura-e-cancelamento.md): a API de estorno, ajuste de fatura e cancelamento existe (`estorno_de` no lançamento, `ajuste_centavos` na fatura, `GET /api/meses/{mes}/totais`), mas nenhuma tela a usa; nenhum outro ticket cobre essas telas

## O que construir

O casal acerta uma fatura que não bate pelo app: cancela uma compra, registra um estorno ligado a ela e lança o ajuste da fatura, com as regras do [ticket 39](39-estorno-ajuste-de-fatura-e-cancelamento.md) e da [ADR 0016](../../../docs/adr/0016-estorno-e-lancamento-que-diminui-ligado-a-compra.md).

## Checklist

- [x] Na compra no cartão, "Estornar": abre o lançamento já com as categorias, as tags e o valor da compra (o valor pode ser menor), a data de hoje e o cartão dela; mostra a fatura em que o estorno vai cair
- [x] O estorno aparece ligado à compra original nas duas pontas ("estornada em ...", "estorno de ...") e a lista o mostra como crédito
- [x] Na fatura (aba Cartões, ticket 55): "Ajustar fatura" com o valor real da fatura ou a diferença, positivo ou negativo, e o total da fatura mostrando compras, estornos e ajuste
- [x] Cancelar uma compra de fatura aberta é a exclusão que já existe; depois do fechamento, a tela sugere o estorno
- [x] Sem internet, o estorno entra na fila como qualquer lançamento; o ajuste exige internet (como as datas da fatura, ticket 88)
- [x] Testes de navegador
- [x] Verificações do projeto rodando e PR aberto para `main`

## Notas

- Tela do estorno: `#/estornar/<id>` reaproveita `TelaDeLancamento` (`estornoDe`); categorias e tags travadas (a API as exige iguais), valor no máximo o que ainda resta da compra, "Entra na fatura de ..." pela data (ou pela fatura escolhida na folha). Editar o estorno (`#/novo/<id>`) mantém tudo travado. `estorno_de` vai no pedido de criar da fila; a edição não o manda (a API não o troca).
- Ligação nas duas pontas e sinal de crédito: `ligacaoDoEstorno`, `restanteDaCompra` e `ValorComSinal` em `web/src/lancamentos/apresentacao.tsx`, usados no Histórico e no detalhe da fatura (a aba Mês e as contas da semana também mostram o `+` do estorno).
- Ajuste: `FormularioDeAjuste` em `web/src/cartoes/TelaDaFatura.tsx`; sem internet o botão fica desligado, com o aviso.
- Cancelar: em fatura aberta, a exclusão de sempre; depois do fechamento, o Histórico sugere o estorno (`situacaoDaFatura`, lida do servidor ou da última resposta guardada) e a fatura fechada traz o aviso.
- Comportamentos provisórios para o dono conferir no [ticket 94](94-conferir-as-regras-de-estorno-e-ajuste.md) (itens novos no fim da lista).
- Testes: `web/e2e/estorno.spec.ts` (5 testes de navegador, incluindo sem internet).
- O ticket foi feito direto na branch designada da sessão (`claude/vibrant-faraday-f04lni`), sem a branch de reserva: a reserva pedia um PR mesclado antes de começar.
