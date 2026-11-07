# Item e pessoa do estorno acompanham a compra

Type: task
Status: resolved
Blocked by: —
Skills: `implement`, `tdd`
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #475
Origem: [ticket 159](159-estorno-de-parte-e-de-parcelas-pendencias.md): decisão do dono sobre o item do planejamento do estorno de todas e a pessoa do estorno ([ADR 0016](../../../docs/adr/0016-estorno-e-lancamento-que-diminui-ligado-a-compra.md), adendo do ticket 159)

## O que construir

- **Item do estorno de todas sem parte**: hoje `acompanhar_estornos_do_parcelamento` (`backend/app/lancamentos.py`) não dá escolha de item ao estorno de todas de um parcelamento sem partes (conta como o crédito avulso). Ele passa a levar a escolha de item do parcelamento (`parcelamentos.item_categoria_id`) ao nascer e toda vez que ela muda, como o de uma parte já leva a da parte (ticket 160). Continua contando inteiro no mês da fatura em que aparece; se a categoria escolhida não tem item nesse mês, vale a regra de sempre.
- **Pessoa do estorno ligado**: o servidor copia a pessoa da compra, da parte, da parcela ou do parcelamento (ou da parte dele) para o estorno ao criá-lo e a acompanha quando ela muda, nos mesmos caminhos de `acompanhar_estornos` e `acompanhar_estornos_do_parcelamento`; ignora a pessoa que o cliente manda no estorno ligado. O estorno avulso guarda a pessoa que o casal deu. O estorno anterior à divisão da compra (ou do parcelamento) fica com a pessoa que tinha, como a classificação.
- **Dado antigo**: sem migração nem acerto na restauração; o estorno se acerta quando a compra mudar (como no adendo do 148).
- **App**: a tela de estorno deixa de oferecer a pessoa no estorno ligado (mostra a da compra ou da parte, sem edição), e a cópia local repete o que o servidor faz para o aparelho mostrar certo sem internet.

## Checklist

- [x] Teste de API: o estorno de todas de um parcelamento sem partes conta no item da escolha do parcelamento, e muda de item quando a escolha muda (correção e edição em lote)
- [x] Teste de API: o estorno de compra, de parte, de parcela e de todas nasce com a pessoa da compra/parte/parcelamento, ignora a do cliente e acompanha a mudança dela
- [x] Teste de API: o estorno avulso guarda a pessoa dada; o anterior à divisão fica com a que tinha
- [x] Implementar no servidor
- [x] App: pessoa só leitura no estorno ligado (a cópia local ficou para o [ticket 194](194-copia-local-da-pessoa-e-do-item-do-estorno-ligado.md))
