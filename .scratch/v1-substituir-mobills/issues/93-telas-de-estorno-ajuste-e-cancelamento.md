# Telas de estorno, ajuste de fatura e compra cancelada

Type: task
Status: claimed
Blocked by: 55, 88
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design`
Modelo recomendado: Sonnet
Effort recomendado: high
Issue: #181
Origem: [ticket 39](39-estorno-ajuste-de-fatura-e-cancelamento.md): a API de estorno, ajuste de fatura e cancelamento existe (`estorno_de` no lançamento, `ajuste_centavos` na fatura, `GET /api/meses/{mes}/totais`), mas nenhuma tela a usa; nenhum outro ticket cobre essas telas

## O que construir

O casal acerta uma fatura que não bate pelo app: cancela uma compra, registra um estorno ligado a ela e lança o ajuste da fatura, com as regras do [ticket 39](39-estorno-ajuste-de-fatura-e-cancelamento.md) e da [ADR 0016](../../../docs/adr/0016-estorno-e-lancamento-que-diminui-ligado-a-compra.md).

## Checklist

- [ ] Na compra no cartão, "Estornar": abre o lançamento já com as categorias, as tags e o valor da compra (o valor pode ser menor), a data de hoje e o cartão dela; mostra a fatura em que o estorno vai cair
- [ ] O estorno aparece ligado à compra original nas duas pontas ("estornada em ...", "estorno de ...") e a lista o mostra como crédito
- [ ] Na fatura (aba Cartões, ticket 55): "Ajustar fatura" com o valor real da fatura ou a diferença, positivo ou negativo, e o total da fatura mostrando compras, estornos e ajuste
- [ ] Cancelar uma compra de fatura aberta é a exclusão que já existe; depois do fechamento, a tela sugere o estorno
- [ ] Sem internet, o estorno entra na fila como qualquer lançamento; o ajuste exige internet (como as datas da fatura, ticket 88)
- [ ] Testes de navegador
- [ ] Verificações do projeto rodando e PR aberto para `main`
