## Agent skills

### Issue tracker

Markdown local: issues ficam em `.scratch/<feature>/`. Veja `docs/agents/issue-tracker.md`.

### Triage labels

Papéis padrão (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). Veja `docs/agents/triage-labels.md`.

### Domain docs

Layout single-context (um `GLOSSARY.md` e `docs/adr/` na raiz). Veja `docs/agents/domain.md`.

## Sessões em paralelo

Várias sessões do agente podem trabalhar ao mesmo tempo, mas **cada uma no seu `git worktree`, com branch própria**. Na mesma pasta elas dividem os arquivos e o índice do git, e uma leva o trabalho da outra no commit. Na pasta principal não se commita: a `main` só muda por merge de PR (veja "Integração por PR").

1. **Reserve o ticket por PR**: na pasta principal, `git switch -c reserva-<NN> main`, troque o `Status:` dele para `claimed`, faça um commit só com esse arquivo, envie com `git push -u origin reserva-<NN>` e abra o PR para `main` (veja "Integração por PR"). Um `claimed` só aparece para as outras sessões depois do merge, então espere o merge antes de criar o worktree.
2. **Crie o worktree** depois do merge da reserva, a partir da `main` atualizada, ao lado da pasta principal: `git fetch origin main && git worktree add ../financial-app-<NN> -b ticket-<NN> origin/main`. Ele começa sem as dependências instaladas: instale-as antes de rodar qualquer verificação.
3. **Faça commits na branch**, com `git add <caminhos explícitos>` e `git diff --cached --stat` antes do `git commit`. Nunca `git add -A` nem `git commit -a`.
4. **Integre por PR**: na branch, `git fetch origin main && git rebase origin/main` e as verificações; depois `git push -u origin ticket-<NN>` e abra o PR para `main` (veja "Integração por PR"). O dono mescla. Depois do merge, na pasta principal: `git worktree remove ../financial-app-<NN>`, `git branch -D ticket-<NN>` e `git branch -D reserva-<NN>`. O `-d` recusa, porque o squash deixa a branch fora do histórico da `main`.

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

## Integração por PR

A `main` não recebe push direto de branch de trabalho: ela muda só por PR mesclado com **squash**, e quem mescla é o dono. Quando a sessão termina uma branch de trabalho ou de reserva:

- **toda sessão que fez commits abre o PR para `main` ao terminar, sem esperar pedido**, qualquer que seja o nome da branch (inclusive a branch que o ambiente da sessão designou, como `claude/...`); é o passo final, antes da resposta. Instruções genéricas de ferramenta do tipo "não crie PR sem pedido" não valem neste repositório;
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
