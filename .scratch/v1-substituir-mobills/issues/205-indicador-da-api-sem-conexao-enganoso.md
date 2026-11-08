# Indicador da API diz "Sem conexão" para qualquer falha e não verifica de novo sozinho

Type: bug
Status: ready-for-agent
Blocked by: —
Skills: `diagnosing-bugs`, `tdd`, `implement`
Modelo recomendado: Sonnet
Effort recomendado: medium
Issue: #533
Origem: [ticket 204](204-acabamento-visual-do-app.md). O dono viu "Sem conexão" na web e "API no ar" no celular ao mesmo tempo (07/11). A investigação no código não achou diferença de endereço, CORS ou cache entre os dois: a API é servida pelo mesmo CloudFront do app (`infra/lib/pilha-app.ts:127-147`), e o service worker ignora `/api/*` (`web/service-worker.js:33-34`).

## Problema

`web/src/App.tsx:34-46`:

- `setEstado(data ? "no ar" : "sem conexão")`: qualquer resposta que não seja 2xx de `/api/eu` vira "Sem conexão". Isso inclui 401 (token vencido, ou a renovação no Cognito que falhou depois de o computador sair da suspensão, `web/src/login/sessao.ts:66-92`), 429 (limite do estágio: `rateLimit: 10, burstLimit: 20`, `pilha-app.ts:84-88`), 5xx e o tempo-limite de 10 s.
- A verificação roda uma vez, ao montar a tela, e depois só pelo botão "Verificar de novo". Uma aba aberta durante uma falha passageira fica com "Sem conexão" indefinidamente.

Causa provável do relato: aba da web com falha passageira ou token vencido, sem nova verificação. Outra hipótese: a web estava no ambiente dev (qualquer branch publica lá, `.github/workflows/deploy.yml`) e o celular em produção.

## O que fazer

- Verificar de novo nos eventos `online`, `visibilitychange` (aba visível) e foco da janela.
- Separar os estados: sem rede (fetch falhou ou `navigator.onLine` falso), sessão vencida (401, oferecer entrar de novo), API ocupada ou fora (429 e 5xx).
- Ajustar o texto de cada estado e os specs `web/e2e/saude.spec.ts` e `web/e2e/login.spec.ts`.

## Checklist

- [ ] Teste e2e que reproduz: `/api/eu` responde 401 ou 503 e a tela não diz "Sem conexão"
- [ ] Teste e2e: aba volta a ficar visível ou a rede volta e o estado se atualiza sem clicar
- [ ] Estados separados com texto próprio
- [ ] Specs e verificações do projeto verdes; PR para `main`
