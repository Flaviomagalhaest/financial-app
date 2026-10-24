## Agent skills

### Issue tracker

Markdown local: issues ficam em `.scratch/<feature>/`. Veja `docs/agents/issue-tracker.md`.

### Triage labels

Papéis padrão (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). Veja `docs/agents/triage-labels.md`.

### Domain docs

Layout single-context (um `GLOSSARY.md` e `docs/adr/` na raiz). Veja `docs/agents/domain.md`.

## Sessões em paralelo

Várias sessões do agente podem trabalhar ao mesmo tempo, mas **cada uma no seu `git worktree`, com branch própria**. Na mesma pasta elas dividem os arquivos e o índice do git, e uma leva o trabalho da outra no commit. Na pasta principal, só se faz o merge (passo 4).

1. **Reserve o ticket na `main`**: troque o `Status:` dele para `claimed` e faça um commit só com esse arquivo, antes de criar o worktree. Um `claimed` feito dentro da branch só aparece para as outras sessões depois do merge.
2. **Crie o worktree** ao lado da pasta principal: `git worktree add ../financial-app-<NN> -b ticket-<NN> main`. Ele começa sem as dependências instaladas: instale-as antes de rodar qualquer verificação.
3. **Faça commits na branch**, com `git add <caminhos explícitos>` e `git diff --cached --stat` antes do `git commit`. Nunca `git add -A` nem `git commit -a`.
4. **Integre ao terminar**: na branch, `git rebase main` e as verificações; na pasta principal, `git merge --ff-only ticket-<NN>`. Se a `main` andou, repita o `rebase` e as verificações. Se o merge recusar por mudanças não commitadas de outra sessão, espere ou avise essa sessão: não use `stash`, `checkout` nem `reset` nos arquivos dela. Depois, `git worktree remove ../financial-app-<NN>` e `git branch -d ticket-<NN>`.

Não reescreva o histórico da `main` (`rebase`, `reset`, `commit --amend` de commits já feitos): as outras sessões têm commits em cima dele.

## Pendências vão para o tracker

Toda pendência conhecida, débito técnico, decisão de produto em aberto, valor provisório ou coisa "só compilada, nunca verificada" vira ticket em `.scratch/<feature>/issues/NN-slug.md`, nunca só uma mensagem no chat. Cada ticket traz **Origem**, **Status**, **Blocked by** e checklist; o que depende de decisão do dono é `ready-for-human`. Decisões difíceis de reverter viram ADR em `docs/adr/`, e vocabulário novo vai para o `GLOSSARY.md`. Ao fechar um ticket, grave as pendências no tracker na mesma sessão e cite o número delas na resposta.

**Todo ticket aberto traz `Skills:`, `Modelo recomendado:` e `Effort recomendado:`** nas linhas do topo, para o dono saber o que usar antes de abrir uma sessão nele. `Skills:` lista pelo nome as skills a invocar (para o tipo do ticket no mapa, as que o `## Notes` do mapa manda: `prototype`, `grilling` e `domain-modeling`, `research`) e as de apoio (`run`, `artifact-design`, `implement`, `tdd`...), e diz quando o ticket é HITL (precisa do dono). Ao criar um ticket, ao mudar o escopo ou ao reabri-lo, preencha ou confira os três; um ticket sem eles não está pronto.

## Trello espelha o tracker

O quadro **Financial App** (https://trello.com/b/SNRQ3kKH/financial-app) mostra os tickets de `.scratch/` para acompanhamento. O repo continua sendo a fonte de verdade: o que vale é o arquivo do ticket. Sempre que uma sessão criar, alterar, reabrir ou fechar um ticket, ela atualiza o card correspondente no Trello **na mesma sessão**, antes de responder.

- **Localizar o card**: pela linha `Trello:` do ticket, que guarda o ARI do card (`ari:cloud:trello::card/...`). Não é preciso listar o quadro para achar o card. Se um ticket não tiver a linha, busque o card com `trelloSearch` (`search_cards`, com `boardIds` do quadro) pelo caminho do ticket, e grave o ARI no ticket antes de qualquer outra mudança.
- **Descrição**: cabeçalho com `Feature`, `Skills`, `Modelo recomendado` e `Effort recomendado`, `Status`, `Blocked by` e `Arquivo`; depois uma linha `---` e a **cópia exata** do arquivo do ticket, incluindo `## Comments`, **sem** a linha `Trello:` (o id só existe depois que o card é criado). Se passar de 16.384 caracteres, o restante vai em comentários, em partes, e a descrição diz isso. Ao mudar o ticket, copie o arquivo de novo.
- **Título**: `NN: título do ticket`, sem prefixo de feature.
- **Etiqueta**: uma etiqueta por feature de `.scratch/`, com o nome legível da feature. Quando um ticket inicia uma feature nova e a etiqueta dela ainda não existe no quadro, a sessão cria a etiqueta antes de criar o card. Nenhum outro ticket recebe etiqueta.
- **Lista**, pelo `Status:`:
  - `ready-for-agent` → TODO;
  - `needs-triage`, `needs-info`, `ready-for-human` → WAITING;
  - `claimed` → DOING;
  - `resolved`, `done`, `wontfix` → FINISHED.
  - Ticket com `Blocked by` apontando para ticket ainda aberto vai para BLOCKED, mesmo que o status o mandasse para TODO ou WAITING. Quando o bloqueio acaba, volta para a lista do status.
- **Ticket novo, nesta ordem**:
  1. crie o card com `trelloWriteCard` (`create`) na lista certa, com a etiqueta da feature (criada antes, se ainda não existir: veja Etiqueta acima);
  2. pegue o id do card (o ARI) da resposta da criação;
  3. grave a linha `Trello: <ARI>` no cabeçalho do ticket, logo abaixo de `Effort recomendado:`;
  4. só então faça o commit do ticket.

  Se o card não puder ser criado (sem conector Trello na sessão), o ticket não é commitado: diga na resposta que falta o card e qual ticket está pendente.
- **Ticket fechado sem card**: não crie; se o card existir, mova para FINISHED.
- **Não criar** listas, etiquetas, quadros nem cards além do descrito aqui sem pedido do dono.
- **Sem conector Trello na sessão**: não marque como feito. Diga na resposta que o Trello ficou para trás e qual ticket precisa de sincronização.

## Branches mescladas recebem tag

Quando uma branch é mesclada na `main`, a sessão que fez o merge cria a tag `merged/<branch>` apontando para o último commit dela (sem o prefixo `origin/`) e envia a tag: `git tag merged/<branch> <commit>` e `git push origin merged/<branch>`. Assim o dono acha as branches que pode apagar listando as tags `merged/*`. A sessão **não apaga** a branch remota: quem apaga é o dono.

Branches que não entram na `main` de propósito (`prototipo/*`, `research/*`, `rascunho/*` e as de tickets ainda não mesclados) não recebem tag.

## Commits sem autoria de agente

Commits e PRs deste repositório não levam trailers nem menções de autoria de IA: nada de `Co-Authored-By` apontando para agente, `Claude-Session`, `Generated with ...` ou linha equivalente. A mensagem descreve só a mudança. Isso vale mesmo quando a ferramenta de commit ou o contexto da sessão pedir esses trailers.

## Revisão com sub-agentes

As skills `code-review` e `implement` devem rodar a revisão com os sub-agentes em paralelo (Standards e Spec), como descrito na skill: o dono autoriza o uso da ferramenta de sub-agentes para isso. Não substitua a revisão por uma leitura própria. Cada sub-agente começa sem o contexto da conversa, então o prompt precisa trazer o diff, as fontes de padrões e o ticket de origem.

## Sessões na nuvem (Claude Code web/celular)

Tudo de que o fluxo precisa está neste repositório: o mapa e os tickets (`.scratch/`), as decisões (`docs/adr/`, `GLOSSARY.md`) e as skills (`.claude/skills/`: `wayfinder`, `implement`, `triage`, `tdd`, `research` etc.). Uma sessão na nuvem trabalha num clone só dela, então não precisa de `git worktree`; o resto do processo vale:

1. **Reserve o ticket**: troque o `Status:` para `claimed`, faça um commit só com esse arquivo e envie para a `main` (`git push origin main`) antes de trabalhar, para as outras sessões verem.
2. **Trabalhe numa branch `ticket-<NN>`**, com `git add <caminhos explícitos>` (nunca `git add -A`).
3. **Integre ao terminar**: `git rebase main`, as verificações do projeto, `git merge --ff-only` na `main` e `git push origin main`. Se a sessão não puder enviar para a `main`, envie a branch `ticket-<NN>` e diga na resposta que falta o merge.
4. As skills de `.claude/skills/` são a cópia do projeto: se uma mudar, mude aqui e não numa cópia local.
