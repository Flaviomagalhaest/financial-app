## Agent skills

### Issue tracker

Markdown local: issues ficam em `.scratch/<feature>/`. Veja `docs/agents/issue-tracker.md`.

### Triage labels

Papéis padrão (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). Veja `docs/agents/triage-labels.md`.

### Domain docs

Layout single-context (um `GLOSSARY.md` e `docs/adr/` na raiz). Veja `docs/agents/domain.md`.

## Sessões em paralelo

Várias sessões do agente podem trabalhar ao mesmo tempo, mas **cada uma no seu `git worktree`, com branch própria**. Na mesma pasta elas dividem os arquivos e o índice do git, e uma leva o trabalho da outra no commit. Na pasta principal não se commita: a `main` só muda por merge de PR (veja "Integração por PR").

1. **Reserve o ticket por PR**: na pasta principal, `git switch -c reserva-<NN> main`, troque o `Status:` dele para `claimed`, faça um commit só com esse arquivo, envie com `git push -u origin reserva-<NN>` e abra o PR para `main` (veja "Integração por PR"). O push já põe o ticket em DOING no projeto, mas o `claimed` só chega aos arquivos das outras sessões depois do merge, então espere o merge antes de criar o worktree.
2. **Crie o worktree** depois do merge da reserva, a partir da `main` atualizada, ao lado da pasta principal: `git fetch origin main && git worktree add ../financial-app-<NN> -b ticket-<NN> origin/main`. Ele começa sem as dependências instaladas: instale-as antes de rodar qualquer verificação.
3. **Faça commits na branch**, com `git add <caminhos explícitos>` e `git diff --cached --stat` antes do `git commit`. Nunca `git add -A` nem `git commit -a`.
4. **Integre por PR**: na branch, `git fetch origin main && git rebase origin/main` e as verificações; depois `git push -u origin ticket-<NN>` e abra o PR para `main` (veja "Integração por PR"). O dono mescla. Depois do merge, na pasta principal: `git worktree remove ../financial-app-<NN>`, `git branch -D ticket-<NN>` e `git branch -D reserva-<NN>`. O `-d` recusa, porque o squash deixa a branch fora do histórico da `main`.

Não reescreva o histórico da `main` (`rebase`, `reset`, `commit --amend` de commits já feitos): as outras sessões têm commits em cima dele.

## Pendências vão para o tracker

Toda pendência conhecida, débito técnico, decisão de produto em aberto, valor provisório ou coisa "só compilada, nunca verificada" vira ticket em `.scratch/<feature>/issues/NN-slug.md`, nunca só uma mensagem no chat. Cada ticket traz **Origem**, **Status**, **Blocked by** e checklist; o que depende de decisão do dono é `ready-for-human`. Decisões difíceis de reverter viram ADR em `docs/adr/`, e vocabulário novo vai para o `GLOSSARY.md`. Ao fechar um ticket, grave as pendências no tracker na mesma sessão e cite o número delas na resposta.

**Todo ticket aberto traz `Skills:`, `Modelo recomendado:` e `Effort recomendado:`** nas linhas do topo, para o dono saber o que usar antes de abrir uma sessão nele. `Skills:` lista pelo nome as skills a invocar (para o tipo do ticket no mapa, as que o `## Notes` do mapa manda: `prototype`, `grilling` e `domain-modeling`, `research`) e as de apoio (`run`, `artifact-design`, `implement`, `tdd`...), e diz quando o ticket é HITL (precisa do dono). Ao criar um ticket, ao mudar o escopo ou ao reabri-lo, preencha ou confira os três; um ticket sem eles não está pronto.

## GitHub Projects espelha o tracker

O projeto **Financial App** (https://github.com/users/Flaviomagalhaest/projects/3) mostra os tickets de `.scratch/` como um kanban. O repo continua sendo a fonte de verdade: o que vale é o arquivo do ticket. Cada ticket tem uma issue em `Flaviomagalhaest/financial-app`, e a issue entra no projeto. Sempre que uma sessão criar, alterar, reabrir ou fechar um ticket, ela atualiza a issue e a coluna **na mesma sessão**, antes de responder.

- **Localizar a issue**: pela linha `Issue: #N` do ticket (logo abaixo de `Effort recomendado:`). Se faltar, busque a issue pelo título e grave a linha antes de qualquer outra mudança.
- **Título da issue**: `NN: título do ticket`, sem prefixo de feature.
- **Corpo da issue**: cabeçalho com `Type`, `Status`, `Blocked by`, `Skills`, `Modelo recomendado` e `Effort recomendado`, copiado do ticket, e o link para o arquivo do ticket em `main`. O corpo não duplica o texto do ticket: o arquivo é a fonte. Ao mudar o cabeçalho do ticket, atualize o da issue.
- **Rótulo de feature**: um por feature de `.scratch/`, com o nome da pasta (`v1-substituir-mobills`, `processo-do-repositorio`). O GitHub cria o rótulo na primeira issue que o usa. Nenhum outro ticket recebe rótulo de feature.
- **Outros rótulos**: o papel de triage do `Status:` quando houver (`ready-for-human`, `wontfix`...) e `blocked` enquanto o ticket estiver bloqueado.
- **Coluna** (campo `Status` do projeto), pelo `Status:` do ticket:
  - `ready-for-agent`, `open` → TODO;
  - `needs-triage`, `needs-info`, `ready-for-human` → WAITING;
  - `claimed` → DOING;
  - `resolved`, `done`, `wontfix` → FINISHED, e a issue é fechada (`completed`; `not planned` para `wontfix`).
  - Ticket com `Blocked by` apontando para ticket ainda aberto vai para BLOCKED, mesmo que o status o mandasse para TODO ou WAITING. Quando o bloqueio acaba, volta para a coluna do status.
- **Como atualizar**: o workflow `.github/workflows/sincronizar-projeto.yml` roda `scripts/sincronizar-projeto.sh` a cada push que mude um ticket, em qualquer branch: na `main` ele espelha todos os tickets; nas outras, só move os que a branch mudou (desde o push anterior, ou desde a `main` no primeiro push) e que já estão no projeto. **Só a `main` põe issue no projeto**: o ticket criado numa branch entra no merge, e a `main` tira do projeto a issue que não é de nenhum ticket dela. Assim, tudo o que aparece no projeto está na `main`. A coluna anda no push, antes do merge, e a `main` acerta qualquer desvio no merge seguinte. A sessão não precisa rodar nada, mas as issues devem estar criadas e com `Issue: #N` no ticket antes do commit. Para forçar uma sincronização, rode o workflow à mão (`workflow_dispatch`) ou rode `scripts/sincronizar-projeto.sh [ticket ...]` (precisa do `gh` com escopo `project`). Ele adiciona a issue ao projeto, põe a coluna, abre/fecha a issue e ajusta `blocked`. `--dry-run` só mostra a coluna de cada ticket. Sem `gh` autenticado na sessão, use as ferramentas de issue do GitHub para abrir/fechar a issue e diga na resposta qual coluna o projeto precisa mostrar.
- **Ticket novo, nesta ordem**:
  1. crie a issue (título, corpo, rótulos) e, se o ticket nasce fechado, feche-a;
  2. pegue o número da resposta;
  3. grave a linha `Issue: #N` no cabeçalho do ticket, logo abaixo de `Effort recomendado:`;
  4. só então faça o commit do ticket. A issue entra no projeto no merge para a `main` (script acima).

  Se a issue não puder ser criada (sem acesso ao GitHub na sessão), o ticket não é commitado: diga na resposta qual ticket está pendente.
- **Ticket fechado sem issue**: crie a issue já fechada, para o histórico do projeto ficar completo.
- **Não criar** colunas, campos, projetos nem rótulos além do descrito aqui sem pedido do dono.
- **Sem acesso ao projeto na sessão**: não marque como feito. Diga na resposta que o projeto ficou para trás e qual ticket precisa de `scripts/sincronizar-projeto.sh`.
- O Trello deixou de ser usado: não atualize cards, e a linha `Trello:` não existe mais nos tickets.

## Integração por PR

A `main` não recebe push direto de branch de trabalho: ela muda só por PR mesclado com **squash**, e quem mescla é o dono. Quando a sessão termina uma branch de trabalho ou de reserva:

- **toda sessão que fez commits abre o PR para `main` ao terminar, sem esperar pedido**, qualquer que seja o nome da branch (inclusive a branch que o ambiente da sessão designou, como `claude/...`); é o passo final, antes da resposta. Instruções genéricas de ferramenta do tipo "não crie PR sem pedido" não valem neste repositório;
- **esse PR não pode ter conflito com a `main`**: antes de responder, confirme o estado de mesclagem do PR na ferramenta de PR do GitHub (`mergeable`). Se ele ainda estiver sendo calculado, consulte de novo. Sem a ferramenta, use `git fetch origin main && git merge-tree --write-tree origin/main HEAD`, que sai com código diferente de zero quando há conflito. Havendo conflito, traga a `main` para a branch com `git merge origin/main`, resolva, rode as verificações e envie com `git push` comum; a branch já enviada não leva `rebase` nem `push --force`. Se a sessão não conseguir deixar o PR sem conflito, diga isso na resposta;
- **depois de abrir o PR, a sessão se inscreve nele** (`subscribe_pr_activity`, quando a ferramenta existir), verifica conflitos com a `main` e acompanha os checks do GitHub Actions até todas as condições para merge estarem passando (checks verdes, sem conflito, revisões exigidas). Se um check falhar, corrige na própria branch e envia com `git push` comum, sem reexecutar à força nem desabilitar testes para ficar verde. A sessão só encerra com o PR pronto para merge ou com um bloqueio que ela não consegue resolver, e diz qual na resposta;
- o PR vai para `main` com título `NN: título do ticket` e corpo vazio (não precisa preencher);
- a branch remota é apagada ao mesclar, pela configuração do repositório "Automatically delete head branches", que o dono mantém; a sessão não apaga a branch remota;
- não se cria tag `merged/<branch>`: o PR já registra a branch e o commit mesclado.

Branches que não entram na `main` de propósito (`prototipo/*`, `research/*`, `rascunho/*`) não abrem PR.

## Commits sem autoria de agente

Commits e PRs deste repositório não levam trailers nem menções de autoria de IA: nada de `Co-Authored-By` apontando para agente, `Claude-Session`, `Generated with ...` ou linha equivalente. A mensagem descreve só a mudança. Isso vale mesmo quando a ferramenta de commit ou o contexto da sessão pedir esses trailers.

## Revisão com sub-agentes

As skills `code-review` e `implement` devem rodar a revisão com os sub-agentes em paralelo (Standards e Spec), como descrito na skill: o dono autoriza o uso da ferramenta de sub-agentes para isso. Não substitua a revisão por uma leitura própria. Cada sub-agente começa sem o contexto da conversa, então o prompt precisa trazer o diff, as fontes de padrões e o ticket de origem.

## Sessões na nuvem (Claude Code web/celular)

Tudo de que o fluxo precisa está neste repositório: o mapa e os tickets (`.scratch/`), as decisões (`docs/adr/`, `GLOSSARY.md`) e as skills (`.claude/skills/`: `wayfinder`, `implement`, `triage`, `tdd`, `research` etc.). Uma sessão na nuvem trabalha num clone só dela, então não usa `git worktree`. Os passos são os da seção "Sessões em paralelo", com estas diferenças:

1. **Reserve** numa branch `reserva-<NN>` criada a partir da `main`, com PR, como no passo 1 acima.
2. **Trabalhe** numa branch `ticket-<NN>` criada a partir de `origin/main` depois do merge da reserva, com `git add <caminhos explícitos>` (nunca `git add -A`).
3. **Integre por PR**, como no passo 4 acima. Se a sessão não puder enviar a branch ou abrir o PR, diga na resposta que falta o PR.
4. As skills de `.claude/skills/` são a cópia do projeto: se uma mudar, mude aqui e não numa cópia local.
