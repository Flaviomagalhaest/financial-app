---
name: conflitos-de-pr
description: Consolida todos os PRs abertos para `main` numa única branch de integração, resolvendo os conflitos um PR por vez, com o CI verde a cada passo. Use quando houver vários PRs abertos conflitando entre si ou com a `main`, ou quando o dono pedir "resolver os conflitos dos PRs".
---

Vários tickets correm em paralelo, então vários PRs ficam abertos para `main`; quando o dono mescla um, os outros conflitam. Esta skill resolve isso **numa sessão só**: uma **branch de integração** absorve os PRs abertos do mais antigo para o mais novo, cada um já sem conflito e com o CI verde, e termina num único PR para `main`. Cada PR absorvido é fechado.

Valem as regras de "Integração por PR" e "Commits sem autoria de agente" do `AGENTS.md`: a branch já enviada nunca leva `rebase` nem `push --force`, a `main` só muda por PR mesclado com squash pelo dono, e commits e PRs não trazem trailer nem menção de IA.

## 1. Levantar a fila

Liste os PRs abertos com base `main` (ferramentas de PR do GitHub; `gh` se houver). Ordene por data de criação, **do mais antigo para o mais novo**: é a fila.

- Fora da fila, com um aviso na resposta: PRs em rascunho, PRs de fork e o PR da própria branch de integração.
- Fila vazia: diga isso e encerre.
- Anote por PR: número, título, branch (`head`) e tickets que ele toca (`.scratch/`).

Critério de pronto: fila escrita na conversa, com todos os PRs elegíveis.

## 2. Criar a branch de integração

Se o ambiente designou uma branch (como `claude/...`), ela é a branch de integração. Senão: `git fetch origin main && git switch -c integracao-<AAAA-MM-DD> origin/main`.

Envie com `git push -u origin <branch>` e abra o PR para `main` (rascunho não: o CI precisa rodar). Título `Integração: NN, NN, ...` com os tickets da fila (atualize a cada PR absorvido), corpo vazio. Inscreva-se nele com `subscribe_pr_activity`.

Critério de pronto: a branch existe no remoto e o PR de integração está aberto.

## 3. Absorver um PR por vez

Para o PR da vez, do mais antigo ao mais novo:

1. **Atualize**: `git fetch origin` e `git merge origin/main`. Merge, nunca rebase: a branch já está no remoto, e outras sessões podem ter mexido nela.
2. **Traga o PR**: `git merge --no-ff origin/<head do PR>`.
3. **Resolva os conflitos** (veja "Como resolver"), com `git add <caminhos explícitos>`. Nunca `git add -A` nem `git commit -a`.
4. **Verifique localmente** o que mudou, com os mesmos passos de `.github/workflows/ci.yml` (lint, testes, contrato OpenAPI, tipos, build). Se faltar dependência, instale antes. A fonte da verdade do que o CI roda é o arquivo, não esta skill.
5. **Commit** da mesclagem, mensagem `NN: integra <título do PR>` (sem trailers), e `git push`.
6. **Acompanhe o CI** do PR de integração até todos os checks do commit enviado estarem verdes. Check pendente: inscrito no PR, termine o turno e retome quando o evento chegar; não faça polling com `sleep`. Check vermelho: leia o log do job (`get_job_logs`), reproduza a falha localmente, corrija na própria branch, mostre o mesmo comando passando e `git push` comum. Teste nunca é pulado, desabilitado nem apagado para ficar verde; se a falha vem do PR original e não da mesclagem, diga isso.
7. **Feche o PR antigo** só com o CI verde no commit que o contém: comentário curto apontando o PR de integração e depois fechar (`state: closed`). Não apague a branch remota.
8. **Registre**: atualize o título do PR de integração e passe ao próximo.

Critério de pronto de cada volta: PR antigo fechado, branch de integração enviada e verde, sem marcador de conflito (`git grep -n '^<<<<<<<'` vazio).

Se `origin/main` andar durante a sessão (o dono mesclou algo), o merge do passo 1 da próxima volta traz a novidade; antes de encerrar, repita-o uma última vez.

## Como resolver

Mantenha **as duas intenções**: o que a `main` ganhou e o que o PR acrescenta. Escolher um lado só some com o trabalho do outro.

- **Arquivos gerados** (`openapi.json`, `web/src/api/schema.d.ts`, lockfiles): não resolva à mão. Fique com a versão da `main`, aplique o código dos dois lados e regenere (`backend/gerar_openapi.py`, `npm run gerar-tipos` na `web`, `uv lock` / `npm install`). O CI tem um passo que reprova arquivo desatualizado.
- **Migrações** em `backend/migrations/`: número repetido entre `main` e PR vira renumeração da que chega, mantendo a ordem de dependência; confira que nenhuma migração já aplicada na `main` muda de conteúdo.
- **Tickets** (`.scratch/`), **`GLOSSARY.md`** e **`docs/adr/`**: some os dois lados. ADR com o mesmo número: renumere o que chega e corrija as referências a ele. Ticket que o outro lado já passou para `resolved`/`done` não volta para `claimed`.
- **Código**: leia a intenção de cada lado (commits, ticket de origem) antes de decidir; conflito semântico sem marcador (função renomeada, contrato mudado) aparece nos testes e na tipagem, então rode-os mesmo quando o merge sair limpo.
- Dúvida real de produto, que o código não responde: pare, registre como ticket `ready-for-human` (veja "Pendências vão para o tracker" no `AGENTS.md`) e siga com os demais PRs da fila; o PR em dúvida fica aberto.

## 4. Fechar

Ao esvaziar a fila:

1. Confirme o estado do PR de integração: `mergeable` sem conflito com a `main` (consulte de novo se estiver sendo calculado; sem a ferramenta, `git fetch origin main && git merge-tree --write-tree origin/main HEAD`) e todos os checks verdes.
2. Responda com: PRs absorvidos e fechados, PRs que ficaram abertos e por quê, tickets novos criados, e o link do PR de integração pronto para o dono mesclar com squash.

Critério de pronto: todo PR elegível da fila está fechado ou explicado na resposta, e o PR de integração está pronto para merge ou com um bloqueio nomeado.
