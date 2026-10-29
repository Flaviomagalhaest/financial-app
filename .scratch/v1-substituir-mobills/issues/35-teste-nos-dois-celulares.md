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
- [ ] No dev, criar uma recorrência e conferir no DSQL os previstos gerados em lotes (`INSERT ... ON CONFLICT (id) DO NOTHING`, ticket 44, só rodou no Postgres) e, no dia seguinte, os logs da Lambda `TarefaDiaria` (das 00:07) com o automático do dia realizado
- [ ] Deixar o iPhone alguns dias sem abrir e conferir que nada local se perdeu (senão, retomar o roteiro do ticket 17)
- [ ] Resultado e decisão sobre seguir ou acionar o plano B em `## Answer`
- [ ] Verificações do projeto rodando e PR aberto para `main`
