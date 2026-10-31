# Recorrência: reabrir o fim e reagendar sem buraco nem previstos além do horizonte

Type: task
Status: resolved
Blocked by: —
Skills: `implement`, `tdd`; apoio: `run`
Modelo recomendado: Sonnet
Effort recomendado: high
Issue: #179
Origem: [ticket 45](45-recorrencia-mudar.md): dois efeitos de `PATCH /api/recorrencias/{id}` que a API aceita e que ainda não têm tratamento

## O que construir

Mudar o fim ou o calendário de uma recorrência não deixa buraco nem previsto fora do horizonte.

## Checklist

- [x] Reabrir o fim: encerrar exclui os previstos depois do fim (`excluido_em`), mas `recorrencias.geradas` fica onde estava e o id de cada previsto é `uuid5(regra, número)` (`ON CONFLICT (id) DO NOTHING`). Tirar ou adiar o fim depois (`ate: null`, `vezes: null`, uma data mais tarde) gera só da ocorrência `geradas + 1` em diante e deixa as que saíram como buraco. Escolher: trazer de volta as excluídas pela regra (e não as que o casal pulou; hoje as duas têm a mesma marca) ou recusar reabrir
- [x] Reagendar para menos frequente (por exemplo de 1 para 3 meses) refaz as datas das ocorrências já geradas e algumas passam do horizonte (`horizonteDaRecorrenciaMeses`); decidir se saem e voltam quando o horizonte chegar a elas
- [x] Testes de API de cada caminho
- [ ] Verificações do projeto rodando e PR aberto para `main`

## Notas

- Escolha: **trazer de volta** o que o fim ou o horizonte tirou, sem coluna nova. Quando o fim (ou o reagendamento, para o que passa do horizonte) exclui um previsto, `recorrencias.geradas` recua até antes dele (`LEAST`, em `_reajustar_um_lote`). O excluído com número acima de `geradas` é, então, o que a regra tirou; o mês pulado tem número já gerado e nunca volta. O número do pedido (`a_partir_da_ocorrencia`) passa a valer até a maior ocorrência que existe, não só `geradas + 1`, porque o recuo deixa ocorrências acima de `geradas`.
- `_gerar_um_lote` revive o excluído (só `situacao = 'previsto'`: o realizado que uma pessoa excluiu fica de fora) com a regra de hoje, sobe a versão e refaz categorias e tags, no lugar do `ON CONFLICT DO NOTHING` que deixava o buraco. A tarefa diária faz o mesmo, por isso o previsto que saiu do horizonte volta quando ele chega. O previsto alterado à mão não sai pelo horizonte (continua valendo "fica como está por inteiro").
- Mesma ideia do parcelamento (`reviver` em `parcelamentos.py`). Glossário: **Ocorrência** e **Horizonte**.
- Pendências gravadas: o mês pulado dentro do trecho que o fim tirou reaparece ao reabrir, no [110](110-recorrencia-mes-pulado-reaparece-ao-reabrir-o-fim.md) (resolvido com a coluna `excluido_pela_regra`, que substitui o critério do número acima de `geradas`); o número 95 repetido, no [09 do processo](../../processo-do-repositorio/issues/09-numero-de-ticket-repetido.md). Recorrência de antes desta mudança, já encerrada, tem `geradas` sem recuo e segue com o buraco (o app ainda não tem dados reais).
