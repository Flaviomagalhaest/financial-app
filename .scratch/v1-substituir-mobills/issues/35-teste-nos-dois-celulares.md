# Teste manual nos dois celulares

Type: task
Status: ready-for-human
Blocked by: 34
Skills: `run` (HITL: o dono faz no aparelho/na AWS e registra o resultado); apoio: `wizard`
Modelo recomendado: Sonnet
Effort recomendado: low
Issue: #89
Origem: [spec da v1](../spec.md), etapa 1; histórias de usuário 1, 2, 6, 49, 55

## O que construir

Fecha a etapa 1 com o teste de verdade nos aparelhos do casal (HITL, do dono). Se a PWA decepcionar, o plano B (Capacitor) é discutido antes de seguir ([ADR 0005](../../../docs/adr/0005-app-web-instalavel-em-vez-de-app-nativo.md)).

## Checklist

- [ ] Instalar o app pelo Compartilhar no iPhone e pelo Chrome no Android
- [ ] Lançar sem internet nos dois, enviar a fila e conferir que nada duplicou; no iPhone, ver a fila subir ao abrir o app
- [ ] No Android, fechar o app com lançamentos não enviados, ligar a rede e conferir que eles sobem sozinhos (o `sync` do service worker, ticket 33; o teste automático só o dispara pelo CDP do Chromium)
- [ ] Provocar um conflito de verdade entre os dois aparelhos e decidi-lo
- [ ] No DSQL (dev ou prod), conferir que editar o mesmo lançamento nos dois grava a versão de cada campo (o `INSERT ... ON CONFLICT DO UPDATE` em `lancamento_campos`, ticket 34, só rodou no Postgres) e que a disputa entre duas edições ao mesmo tempo termina em conflito, não em erro
- [ ] No dev, criar uma recorrência e conferir no DSQL os previstos gerados em lotes (`INSERT ... ON CONFLICT (id) DO NOTHING`, ticket 44, só rodou no Postgres) e, no dia seguinte, os logs da Lambda `TarefaDiaria` (das 00:07) com o automático do dia realizado; o mesmo com um parcelamento no cartão (ticket 46: parcelas geradas em lotes e a parcela realizada quando a fatura de antes fecha)
- [ ] Deixar o iPhone alguns dias sem abrir e conferir que nada local se perdeu (senão, retomar o roteiro do ticket 17)
- [ ] Lançar pela jornada do [ticket 42](42-jornada-completa-do-lancamento-rapido.md) nos dois celulares (atalho do ícone no Android, botão na Hoje no iPhone, folha de detalhes, "Repetir último", transferência) e confirmar as escolhas sem protótipo: "Transferência" no seletor de tipo, "Repetir último" só com os lançamentos de quem está no aparelho e a data do resumo em `dd/mm/aaaa`
- [ ] Sugestão pelo histórico ([ticket 63](63-sugestao-pelo-historico.md)) nos dois celulares, sem internet: digitar a descrição na folha de detalhes, escolher e corrigir. No DSQL (dev ou prod, com o histórico importado), conferir o tempo e o tamanho de `GET /api/sugestoes` (só rodou no Postgres, com `GREATEST` e subconsultas por lançamento)
- [ ] Resultado e decisão sobre seguir ou acionar o plano B em `## Answer`
- [ ] Conferir no DSQL se `itens_do_planejamento` aceita um índice único em (`mes`, `categoria_id`) (ticket 49: hoje a unicidade é só da rota)
- [ ] Verificações do projeto rodando e PR aberto para `main`
