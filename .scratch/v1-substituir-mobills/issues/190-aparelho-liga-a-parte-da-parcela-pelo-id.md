# Aparelho liga a parte da parcela à do parcelamento pelo id, como o servidor

Type: task
Status: ready-for-agent
Blocked by: —
Skills: `implement`, `tdd`; apoio: `run` para ver funcionando
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #477
Origem: decisão do dono no [ticket 161](161-limite-do-estorno-de-parte-do-parcelamento.md), item "Ligação no aparelho pela posição" ([ADR 0016](../../../docs/adr/0016-estorno-e-lancamento-que-diminui-ligado-a-compra.md), adendo do ticket 161)

## O que construir

O servidor liga a parte de uma parcela à parte do parcelamento pelo id: o id da parte na parcela é `id_na_parcela(parcela_id, parte_id)` = `uuid5(parcela_id, str(parte_id))` (`backend/app/partes.py`). O aparelho liga pela posição (`parteDoParcelamento` e `parteDaParcela` em `web/src/lancamentos/apresentacao.tsx`). Por isso, uma parcela com partes próprias (mudou "só nesta") e com o mesmo número de partes do parcelamento é ligada pelo aparelho e não pelo servidor. O "restante" que o aparelho mostra (`restanteDaParteDoParcelamento`) passa do que o servidor aceita, e um estorno criado sem internet é recusado na sincronização.

O dono decidiu: o aparelho faz a mesma conta do servidor.

- O app ganha um `uuid5(namespace, nome)` próprio (RFC 9562: SHA-1 do namespace em bytes mais o nome em UTF-8, versão 5 e variante nos bits certos). Ele é **síncrono**, porque `parteDoParcelamento` é chamada nas somas da tela, então não dá para usar `crypto.subtle`. Pode ser uma função SHA-1 pequena, sem dependência nova.
- `parteDoParcelamento(parcela, parteId, regra)` devolve a parte do parcelamento `r` cujo `uuid5(parcela.id, r.id)` é `parteId`, ou nada. `parteDaParcela` faz o caminho inverso pela mesma conta. Somem a comparação pela posição e a exigência do mesmo número de partes.
- A tabela `tabelas-de-teste/ids-das-partes-nas-parcelas.json` prende as duas contas (ADR 0018): pares `(parcela_id, parte_id)` e o id esperado, lidos pelo `backend/tests/test_tabelas_compartilhadas.py` e pelo teste do app.

## Checklist

- [ ] `uuid5` no app, com a tabela compartilhada passando no servidor e no app
- [ ] `parteDoParcelamento` e `parteDaParcela` pelo id; atualizar o comentário que fala da posição
- [ ] Teste: parcela com partes próprias com o mesmo número de partes não conta no restante da parte do parcelamento, igual ao servidor
- [ ] ADR 0016: o adendo do 160 deixa de dizer "pela posição"
- [ ] Verificações do projeto e PR para `main`
