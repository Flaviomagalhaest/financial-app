# Retomar as pesquisas com a rede liberada

Type: task
Status: resolved
Blocked by: —
Skills: `wayfinder` (passo 5 de "Chart the map") e `research` (um sub-agente por ticket de pesquisa); HITL só se a rede continuar bloqueada (o dono libera)
Modelo recomendado: Sonnet
Effort recomendado: medium
Origem: traçado do [mapa V1 que substitui o Mobills](../map.md); a sessão que traçou o mapa parou no passo 5 porque a rede dela recusava as fontes oficiais

## Question

As pesquisas do traçado só andam com acesso às fontes primárias. A sessão que traçou o mapa recebeu 403 do proxy em `docs.aws.amazon.com`, `aws.amazon.com`, `webkit.org`, `developer.mozilla.org`, `web.dev`, `docs.expo.dev`, `capacitorjs.com`, `www.mobills.com.br` e `ajuda.mobills.com.br`, mesmo depois de o dono liberar a rede no ambiente.

Esta tarefa confirma o acesso e dispara o passo 5 do wayfinder para [O que o Mobills exporta](01-o-que-o-mobills-exporta.md), [Limites do app web instalável no iPhone e no Android](02-limites-do-app-web-instalavel.md) e [Banco de dados na AWS para dois usuários e histórico longo](03-banco-de-dados-na-aws.md).

## Checklist

- [x] Testar os domínios acima (`curl -sS -o /dev/null -w "%{http_code}" https://<domínio>/` e `curl -sS "$HTTPS_PROXY/__agentproxy/status"`); se algum continuar bloqueado, parar e pedir ao dono que o libere em Network access do ambiente, sem substituir a fonte por resultado de busca ou inventado
- [x] Reservar este ticket e os três de pesquisa na `main` (`Status: claimed`), um commit por arquivo, e mover os cards para DOING
- [x] Disparar em paralelo um sub-agente por ticket de pesquisa, cada um em worktree próprio, chamando a skill `research`; cada um grava os achados num único Markdown numa branch `research/<nome>` (o nome está no checklist do ticket) e envia a branch, sem PR e sem tag
- [x] Ao voltar cada sub-agente: registrar em `## Answer` do ticket o resumo e o ponteiro para a branch, marcar `Status: resolved` e acrescentar a linha em Decisions so far do mapa
- [x] Atualizar os cards (descrição copiada de novo, FINISHED para os resolvidos) e mover para TODO os tickets que ficarem desbloqueados
- [x] Fechar esta tarefa com o que foi feito e os domínios que precisaram ser liberados

## Answer

Rede confirmada: os nove domínios responderam (200; 301 em `ajuda.mobills.com.br` e 302 em `developer.mozilla.org`, que são redirecionamentos), depois de o dono liberar a rede em Network access e abrir sessão nova. Os três sub-agentes rodaram em paralelo, cada um em worktree próprio, e as branches `research/mobills-exportacao`, `research/app-web-instalavel` e `research/banco-de-dados-aws` foram enviadas, sem PR e sem tag.

- [Limites do app web instalável](02-limites-do-app-web-instalavel.md) e [Banco de dados na AWS](03-banco-de-dados-na-aws.md): `resolved`. [Plataforma do cliente](08-plataforma-do-cliente.md) ficou desbloqueado.
- [O que o Mobills exporta](01-o-que-o-mobills-exporta.md): resposta parcial, porque a central de ajuda do Mobills (`mobills.zendesk.com`) continua atrás do desafio da Cloudflare. Virou `ready-for-human`, bloqueado por [Ler a central de ajuda do Mobills e fazer uma exportação de teste](14-ler-a-central-de-ajuda-e-exportar-de-teste.md).
- Lacunas das duas outras pesquisas: [Reconferir as lacunas das pesquisas de plataforma e de banco](15-reconferir-lacunas-das-pesquisas.md).

Domínios que precisaram ser liberados: os nove da lista acima, que passaram a responder. Os sub-agentes também alcançaram `developer.apple.com`, `developer.android.com`, `sqlite.org`, `unpkg.com` e `pricing.us-east-1.amazonaws.com`. Não passou: `mobills.zendesk.com` (destino do redirecionamento de `ajuda.mobills.com.br`), que devolve o desafio da Cloudflare ao `curl` e não resolve no WebFetch; é limite do site, não da rede do ambiente.
