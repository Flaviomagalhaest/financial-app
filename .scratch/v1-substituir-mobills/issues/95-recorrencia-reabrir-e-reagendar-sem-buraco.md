# Recorrência: reabrir o fim e reagendar sem buraco nem previstos além do horizonte

Type: task
Status: ready-for-agent
Blocked by: —
Skills: `implement`, `tdd`; apoio: `run`
Modelo recomendado: Sonnet
Effort recomendado: high
Issue: #179
Origem: [ticket 45](45-recorrencia-mudar.md): dois efeitos de `PATCH /api/recorrencias/{id}` que a API aceita e que ainda não têm tratamento

## O que construir

Mudar o fim ou o calendário de uma recorrência não deixa buraco nem previsto fora do horizonte.

## Checklist

- [ ] Reabrir o fim: encerrar exclui os previstos depois do fim (`excluido_em`), mas `recorrencias.geradas` fica onde estava e o id de cada previsto é `uuid5(regra, número)` (`ON CONFLICT (id) DO NOTHING`). Tirar ou adiar o fim depois (`ate: null`, `vezes: null`, uma data mais tarde) gera só da ocorrência `geradas + 1` em diante e deixa as que saíram como buraco. Escolher: trazer de volta as excluídas pela regra (e não as que o casal pulou; hoje as duas têm a mesma marca) ou recusar reabrir
- [ ] Reagendar para menos frequente (por exemplo de 1 para 3 meses) refaz as datas das ocorrências já geradas e algumas passam do horizonte (`horizonteDaRecorrenciaMeses`); decidir se saem e voltam quando o horizonte chegar a elas
- [ ] Testes de API de cada caminho
- [ ] Verificações do projeto rodando e PR aberto para `main`
