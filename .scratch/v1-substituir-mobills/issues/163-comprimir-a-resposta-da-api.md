# Comprimir a resposta da API

Type: task
Status: resolved
Blocked by: —
Skills: `implement`, `tdd`; apoio: `run`; HITL só na conferência com `curl` no `dev`
Modelo recomendado: Sonnet
Effort recomendado: low
Issue: #400
Origem: [ticket 124](124-historico-sem-a-lista-inteira.md) e [ADR 0025](../../../docs/adr/0025-sem-internet-so-a-janela-do-aparelho.md) (decisão Q8). Números na [pesquisa dos limites de resposta](../research/limites-de-resposta-da-lambda.md).

## O que construir

A API responde sem compressão, e a lista de 11 mil lançamentos passa do limite de 6 MiB da Lambda (o teto sem compressão fica perto de 7.900). Ligar o `GZipMiddleware` na FastAPI: com ele o Mangum devolve o corpo em base64 com `content-encoding: gzip`, e a lista de 11 mil cai para 1,1 a 1,7 MB de envelope (medido na pesquisa, seção 4). O CloudFront não ajuda (`/api/*` usa `CachingDisabled`), então a compressão tem de ser da API.

## Checklist

- [x] Teste do backend: resposta grande com `Accept-Encoding: gzip` sai comprimida e em base64 pelo Mangum; sem o cabeçalho, sai como hoje
- [x] `GZipMiddleware` na `create_app`, com `minimum_size` que não comprima respostas pequenas
- [x] Teste de navegador segue verde (o navegador descomprime antes do `response.json()`)
- [x] HITL: no `dev`, rodar o `curl` da seção "O que falta conferir" da pesquisa e conferir que o `Accept-Encoding` chega à Lambda e o `content-encoding: gzip` volta ao navegador
