# Estorno, ajuste de fatura e compra cancelada

Type: task
Status: resolved
Blocked by: 37
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` se mexer na interface
Modelo recomendado: Sonnet
Effort recomendado: high
Issue: #93
Origem: [spec da v1](../spec.md), etapa 2; histórias de usuário 82, 83, 84, 85

## O que construir

O casal acerta uma fatura que não bate: cancela, estorna ou ajusta, sem inventar categoria ([ADR 0008](../../../docs/adr/0008-ajuste-de-fatura-fica-na-fatura.md)).

## Checklist

- [x] Compra cancelada antes do fechamento some de tudo
- [x] Estorno ligado ao lançamento original, com as mesmas categorias e tags, na fatura em que aparece, diminuindo o total da tag naquele mês
- [x] Ajuste de fatura conta no total da fatura, nas despesas do mês, no "ainda dá para gastar" e no fechamento do mês, mas não em categoria, tag nem item do planejamento
- [x] Testes de API com exemplos concretos
- [x] Verificações do projeto rodando e PR aberto para `main`

## Notas

- Modelo: [ADR 0016](../../../docs/adr/0016-estorno-e-lancamento-que-diminui-ligado-a-compra.md). O estorno é um lançamento `despesa` com `estorno_de` (migration `0036`) que diminui nas somas (`GASTO_NO_CARTAO` em `app/lancamentos.py`; o planejamento tem o seu `CASE`); o ajuste é `faturas.ajuste_centavos` (migration `0037`, ADR 0008). Backup na versão 13, com o conversor da 12.
- API: `estorno_de` em `POST /api/lancamentos` (e no lote); 422 para compra original inexistente ou excluída, de conta, de receita ou de outro estorno, destino que não é cartão, categorias ou tags diferentes das da compra e soma dos estornos acima do valor. Editar um estorno não troca tipo, categorias nem tags, e o valor e o cartão seguem as mesmas regras. `PATCH /api/cartoes/{id}/faturas/{mes}` aceita `ajuste_centavos` (só ele não mexe nas datas); a fatura devolve `compras_centavos`, `ajuste_centavos` e `total_centavos`. O cancelamento é a exclusão que já existia, agora com teste: a compra sai da fatura, do planejamento e da lista.
- Onde os números aparecem: não havia leitura de despesas do mês, de total por tag nem de fechamento do mês (tickets 53 e 54), então este ticket criou `GET /api/meses/{mes}/totais` (`app/meses.py`: despesas com os ajustes, por categoria e por tag, sem o ajuste) como a base que esses tickets leem, e o planejamento ganhou `ajustes_de_fatura_centavos` e desconta os ajustes de `ainda_da_para_gastar_centavos` (os itens não mudam). Os tickets [53](53-aba-hoje.md), [54](54-aba-mes.md) e [91](91-importador-do-mobills-gravar-e-refazer.md) usam isso.
- A planilha exporta o estorno com o sinal de crédito.
- Fora deste ticket, de propósito: as telas ([ticket 93](93-telas-de-estorno-ajuste-e-cancelamento.md)); a importação de `Reajuste de fatura` ([68](68-importador-do-mobills-parcelamentos-pendentes-e-ajustes.md), que agora grava em `faturas.ajuste_centavos`); o comprometido do cartão com estorno ([56](56-limite-comprometido-do-cartao.md)).
- Comportamentos provisórios para o dono conferir no [ticket 94](94-conferir-as-regras-de-estorno-e-ajuste.md).
- O ticket foi feito direto na branch designada da sessão (`ccr-d603ea8e-s13jym`), sem a branch de reserva: a reserva pedia um PR mesclado antes de começar.
