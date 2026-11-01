# O estorno acompanha a compra e trava a exclusão

Type: task
Status: resolved
Blocked by: —
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando, `artifact-design` nas telas
Modelo recomendado: Sonnet
Effort recomendado: high
Issue: #321
Origem: [ticket 94](94-conferir-as-regras-de-estorno-e-ajuste.md): decisões do dono sobre estorno, ajuste de fatura e partes da compra

## O que construir

O estorno passa a seguir as categorias e tags da compra (também as arquivadas), e a compra com estorno não pode mais ser excluída. Hoje o estorno guarda uma cópia que não muda, recusa a tag arquivada e fica solto quando a compra sai.

## Checklist

- [x] Estorno sem categorias e tags próprias: vale o que a compra tem agora; mudar a compra muda o que o estorno desconta (categoria, tag, item do planejamento)
- [x] Estorno de compra com tag ou categoria arquivada é aceito
- [x] Excluir compra com estorno: 422 "a compra tem estorno; exclua o estorno antes"
- [x] Tela: "Excluir" segue ativo na compra com estorno; ao tocar, mostra a mensagem com link para o estorno
- [x] "Estornar" aparece também na compra de cartão arquivado (cartão reemitido); a escolha do cartão segue só com os ativos
- [x] Fila sem internet: a exclusão recusada aparece como recusada, com o motivo
- [x] Testes de API e de navegador; verificações do projeto e PR para `main`

## Notas

- Decisões Q2, Q4, Q7, Q22 e Q24 do ticket 94; adendo da [ADR 0016](../../../docs/adr/0016-estorno-e-lancamento-que-diminui-ligado-a-compra.md).
- Ponto de partida: `_conferir_estorno` em `backend/app/lancamentos.py`.

## Entregue

- `acompanhar_estornos` (`backend/app/lancamentos.py`) copia da compra para os estornos as categorias, as tags (arquivadas inclusive) e o item do planejamento; roda na criação do estorno e onde a compra muda (edição, correção de parcelamento, reajuste de recorrência). A edição em lote já levava o estorno junto.
- O estorno novo ignora categorias e tags enviadas e leva as da compra; o estorno não muda de categoria, tag nem item por conta própria (422).
- Excluir compra com estorno: 422, também pela fila (volta recusada com o motivo) e em `DELETE /api/parcelamentos/{id}`, que recusa antes de fechar o parcelamento.
- Telas: "Excluir" mostra a mensagem com o link para o estorno; "Estornar" aparece no cartão arquivado, e o cartão do estorno é escolhido entre os ativos.
- Pendência: [ticket 148](148-parcela-com-estorno-quando-a-regra-a-tira.md) (regras que tiram parcela ou ocorrência com estorno).
