# Retomar as pesquisas com a rede liberada

Type: task
Status: claimed
Blocked by: —
Skills: `wayfinder` (passo 5 de "Chart the map") e `research` (um sub-agente por ticket de pesquisa); HITL só se a rede continuar bloqueada (o dono libera)
Modelo recomendado: Sonnet
Effort recomendado: medium
Origem: traçado do [mapa V1 que substitui o Mobills](../map.md); a sessão que traçou o mapa parou no passo 5 porque a rede dela recusava as fontes oficiais

## Question

As pesquisas do traçado só andam com acesso às fontes primárias. A sessão que traçou o mapa recebeu 403 do proxy em `docs.aws.amazon.com`, `aws.amazon.com`, `webkit.org`, `developer.mozilla.org`, `web.dev`, `docs.expo.dev`, `capacitorjs.com`, `www.mobills.com.br` e `ajuda.mobills.com.br`, mesmo depois de o dono liberar a rede no ambiente.

Esta tarefa confirma o acesso e dispara o passo 5 do wayfinder para [O que o Mobills exporta](01-o-que-o-mobills-exporta.md), [Limites do app web instalável no iPhone e no Android](02-limites-do-app-web-instalavel.md) e [Banco de dados na AWS para dois usuários e histórico longo](03-banco-de-dados-na-aws.md).

## Checklist

- [ ] Testar os domínios acima (`curl -sS -o /dev/null -w "%{http_code}" https://<domínio>/` e `curl -sS "$HTTPS_PROXY/__agentproxy/status"`); se algum continuar bloqueado, parar e pedir ao dono que o libere em Network access do ambiente, sem substituir a fonte por resultado de busca ou inventado
- [ ] Reservar este ticket e os três de pesquisa na `main` (`Status: claimed`), um commit por arquivo, e mover os cards para DOING
- [ ] Disparar em paralelo um sub-agente por ticket de pesquisa, cada um em worktree próprio, chamando a skill `research`; cada um grava os achados num único Markdown numa branch `research/<nome>` (o nome está no checklist do ticket) e envia a branch, sem PR e sem tag
- [ ] Ao voltar cada sub-agente: registrar em `## Answer` do ticket o resumo e o ponteiro para a branch, marcar `Status: resolved` e acrescentar a linha em Decisions so far do mapa
- [ ] Atualizar os cards (descrição copiada de novo, FINISHED para os resolvidos) e mover para TODO os tickets que ficarem desbloqueados
- [ ] Fechar esta tarefa com o que foi feito e os domínios que precisaram ser liberados
