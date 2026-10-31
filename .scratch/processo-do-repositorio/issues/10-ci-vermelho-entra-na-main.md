# CI vermelho entra na main e falha sem material para diagnóstico

Type: task
Status: ready-for-human
Blocked by: —
Skills: `writing-for-agents` (AGENTS.md); HITL: o dono muda as configurações do repositório
Modelo recomendado: Sonnet
Effort recomendado: low
Issue: #237
Origem: revisão do CI pedida pelo dono (30/10), depois de sessões dizerem que a quebra do CI nos PRs era intermitente e não vinha delas.

## O que a revisão achou

O `ci.yml` cobre o que o repositório tem (lint e testes do backend com Postgres, contrato OpenAPI, build da PWA, synth da infra, testes de navegador), e o job roda no commit de merge do PR com a `main`. Por isso um defeito da `main` aparece em todo PR. Nas últimas 40 rodadas, toda falha foi nos testes de navegador, e as falhas são as mesmas nos PRs e na própria `main` (runs 133, 137 e 153). As duas mais comuns têm causa achada e não vêm dos PRs: tickets [113 da V1](../../v1-substituir-mobills/issues/113-editar-enquanto-a-criacao-sobe-vira-conflito.md) (bug do app) e [114 da V1](../../v1-substituir-mobills/issues/114-confirmar-com-ajuste-nao-espera-a-outra-pessoa.md) (corrida no teste). O que deixa isso acontecer e se repetir:

- **O check não é obrigatório.** O PR #218 foi mesclado com o run 154 vermelho nas duas tentativas (`mergeable_state: unstable`). Outros entraram depois de rodar o job de novo até passar. A `main` fica vermelha, e o PR seguinte herda a falha.
- **Os merges não são squash.** Os commits da `main` são "Merge pull request #N", e o AGENTS.md pede squash.
- **A falha não deixa material.** O Playwright grava `error-context.md` e o estado da página em `web/test-results/`, mas o job não sobe nada. A sessão só tem o log e conclui "intermitente".
- **Menores**: as actions (`checkout@v4`, `setup-node@v4`, `setup-uv@v5`) rodam forçadas em Node 24, com aviso de depreciação; push novo no PR não cancela a rodada anterior (sem `concurrency`); o Chromium é baixado a cada rodada.

## Checklist

- [ ] (dono) Proteção da `main`: exigir o check `verificar` para mesclar
- [ ] (dono) Configurações do repositório: permitir só "Squash merging"
- [ ] `ci.yml`: com o job falho, subir `web/test-results` como artifact (`actions/upload-artifact`, `if: failure()`); no `playwright.config.ts`, `trace: "retain-on-failure"` quando `CI`
- [ ] `ci.yml`: `concurrency` por PR com `cancel-in-progress: true`; actions em versões que rodam em Node 24; cache de `~/.cache/ms-playwright`
- [ ] AGENTS.md: antes de chamar uma falha de intermitente, conferir se o mesmo teste falha na `main` ou em outros PRs (runs do `ci.yml`) e, se falha, registrar no ticket do teste em vez de só rodar o job de novo
- [ ] Sem `retries` no Playwright enquanto os tickets 113 e 114 da V1 estiverem abertos: a repetição esconderia os dois defeitos

## Notas

- Os números de ticket repetidos (73, 95, 100, 102, 103, 104 e 109 na V1, com um terceiro 109 no PR do 57) são o assunto do ticket 09, aberto no PR do 95.
