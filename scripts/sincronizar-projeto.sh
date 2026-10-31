#!/usr/bin/env bash
# Espelha os tickets de .scratch/ no projeto "Financial App" do GitHub:
# adiciona a issue ao projeto, põe a coluna certa em "Status" e abre/fecha a issue.
# Lê o projeto inteiro de uma vez e só muda o que difere: a cota GraphQL é do usuário dono do
# token e acabava com a sincronização completa da main (ticket 11). Abrir, fechar e o rótulo
# vão pela API REST, que tem cota à parte.
# Só a main põe issue no projeto (ticket 12): o ticket de uma branch ainda não mesclada fica de fora.
#   --so-no-projeto      (branches) só mexe nos tickets cuja issue já está no projeto
#   --tirar-sem-ticket   (main, sem lista de tickets) tira do projeto as issues deste repositório
#                        que não são de nenhum ticket daqui, as que entraram por uma branch
# Precisa do gh autenticado com o escopo `project` (gh auth refresh -s project).
# Uso: scripts/sincronizar-projeto.sh [--dry-run] [--so-no-projeto] [--tirar-sem-ticket] [caminho-do-ticket ...]
set -euo pipefail

OWNER=Flaviomagalhaest
REPO=financial-app
PROJECT=3

dry=0 so_no_projeto=0 tirar=0
while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) dry=1 ;;
    --so-no-projeto) so_no_projeto=1 ;;
    --tirar-sem-ticket) tirar=1 ;;
    *) break ;;
  esac
  shift
done
cd "$(git rev-parse --show-toplevel)"
files=("$@")
if [ ${#files[@]} -eq 0 ]; then
  files=(.scratch/*/issues/*.md)
elif [ $tirar -eq 1 ]; then
  # Com uma lista, os tickets de fora dela não estão aqui, e as issues deles sairiam do projeto.
  echo "--tirar-sem-ticket só vale sem lista de tickets" >&2; exit 1
fi

campo() { sed -n "s/^$2: *//p" "$1" | head -1; }

# aberto = Status que ainda não fechou o ticket
fechado() { case "$(campo "$1" Status)" in resolved|done|wontfix*) return 0 ;; *) return 1 ;; esac; }

bloqueado() {
  local f=$1 dir n b
  dir=$(dirname "$f")
  for n in $(campo "$f" 'Blocked by' | grep -oE '[0-9]+' || true); do
    b=$(ls "$dir"/"$n"-*.md 2>/dev/null | head -1) || true
    [ -n "$b" ] && ! fechado "$b" && return 0
  done
  return 1
}

coluna() {
  local f=$1 s
  s=$(campo "$f" Status)
  if fechado "$f"; then echo FINISHED; return; fi
  if bloqueado "$f"; then echo BLOCKED; return; fi
  case "$s" in
    claimed) echo DOING ;;
    needs-triage|needs-info|ready-for-human) echo WAITING ;;
    *) echo TODO ;;  # ready-for-agent e open
  esac
}

# O projeto, o campo Status e cada item com a issue, a coluna, o estado e os rótulos, 100 por página.
CONSULTA='query($owner: String!, $numero: Int!, $endCursor: String) {
  user(login: $owner) {
    projectV2(number: $numero) {
      id
      field(name: "Status") { ... on ProjectV2SingleSelectField { id options { id name } } }
      items(first: 100, after: $endCursor) {
        pageInfo { hasNextPage endCursor }
        nodes {
          id
          status: fieldValueByName(name: "Status") { ... on ProjectV2ItemFieldSingleSelectValue { name } }
          content { ... on Issue { number state repository { nameWithOwner } labels(first: 20) { nodes { name } } } }
        }
      }
    }
  }
}'
ADICIONAR='mutation($projeto: ID!, $issue: ID!) {
  addProjectV2ItemById(input: { projectId: $projeto, contentId: $issue }) { item { id } }
}'
MOVER='mutation($projeto: ID!, $item: ID!, $campo: ID!, $opcao: String!) {
  updateProjectV2ItemFieldValue(input: {
    projectId: $projeto, itemId: $item, fieldId: $campo, value: { singleSelectOptionId: $opcao }
  }) { projectV2Item { id } }
}'
TIRAR='mutation($projeto: ID!, $item: ID!) {
  deleteProjectV2Item(input: { projectId: $projeto, itemId: $item }) { deletedItemId }
}'

if [ $dry -eq 0 ]; then
  paginas=$(gh api graphql --paginate -F owner=$OWNER -F numero=$PROJECT -f query="$CONSULTA")
  proj_id=$(jq -rs '.[0].data.user.projectV2.id' <<<"$paginas")
  field_id=$(jq -rs '.[0].data.user.projectV2.field.id' <<<"$paginas")
  opcoes=$(jq -cs '.[0].data.user.projectV2.field.options' <<<"$paginas")
  # Uma linha por issue deste repositório no projeto: número, item, coluna, estado, se tem `blocked`.
  itens=$(jq -rs --arg repo "$OWNER/$REPO" '
    [.[].data.user.projectV2.items.nodes[]] | .[]
    | select(.content.repository.nameWithOwner? == $repo)
    | [.content.number, .id, (.status.name // "-"), .content.state,
       (if any(.content.labels.nodes[]; .name == "blocked") then "sim" else "nao" end)]
    | @tsv' <<<"$paginas")
fi

mudancas=0
dos_tickets=" "
for f in "${files[@]}"; do
  num=$(campo "$f" Issue | tr -dc 0-9)
  [ -z "$num" ] && { echo "sem linha Issue: $f" >&2; continue; }
  dos_tickets+="$num "
  col=$(coluna "$f")
  echo "#$num -> $col  ($f)"
  [ $dry -eq 1 ] && continue

  linha=$(awk -F'\t' -v n="$num" '$1 == n { print; exit }' <<<"$itens")
  if [ -n "$linha" ]; then
    IFS=$'\t' read -r _ item atual estado rotulo <<<"$linha"
  elif [ $so_no_projeto -eq 1 ]; then
    echo "  fora do projeto: entra no merge para a main"
    continue
  else
    # Fora do projeto: o estado vem da issue, e ela entra no projeto.
    IFS=$'\t' read -r no estado rotulo < <(gh api "repos/$OWNER/$REPO/issues/$num" \
      --jq '[.node_id, (.state | ascii_upcase), (if any(.labels[]; .name == "blocked") then "sim" else "nao" end)] | @tsv')
    item=$(gh api graphql -f query="$ADICIONAR" -f projeto="$proj_id" -f issue="$no" \
      --jq .data.addProjectV2ItemById.item.id)
    atual=-
    echo "  entrou no projeto"; mudancas=$((mudancas + 1))
  fi

  if [ "$atual" != "$col" ]; then
    opt=$(jq -r --arg c "$col" '.[] | select(.name == $c) | .id' <<<"$opcoes")
    [ -z "$opt" ] && { echo "coluna $col não existe no projeto" >&2; exit 1; }
    gh api graphql -f query="$MOVER" -f projeto="$proj_id" -f item="$item" -f campo="$field_id" \
      -f opcao="$opt" >/dev/null
    echo "  coluna: $atual -> $col"; mudancas=$((mudancas + 1))
  fi

  if fechado "$f" && [ "$estado" != CLOSED ]; then
    reason=completed; case "$(campo "$f" Status)" in wontfix*) reason=not_planned ;; esac
    gh api -X PATCH "repos/$OWNER/$REPO/issues/$num" -f state=closed -f state_reason=$reason >/dev/null
    echo "  issue fechada ($reason)"; mudancas=$((mudancas + 1))
  elif ! fechado "$f" && [ "$estado" != OPEN ]; then
    gh api -X PATCH "repos/$OWNER/$REPO/issues/$num" -f state=open >/dev/null
    echo "  issue reaberta"; mudancas=$((mudancas + 1))
  fi

  if [ "$col" = BLOCKED ] && [ "$rotulo" = nao ]; then
    gh api -X POST "repos/$OWNER/$REPO/issues/$num/labels" -f 'labels[]=blocked' >/dev/null
    echo "  + blocked"; mudancas=$((mudancas + 1))
  elif [ "$col" != BLOCKED ] && [ "$rotulo" = sim ]; then
    gh api -X DELETE "repos/$OWNER/$REPO/issues/$num/labels/blocked" >/dev/null
    echo "  - blocked"; mudancas=$((mudancas + 1))
  fi
done

if [ $tirar -eq 1 ] && [ $dry -eq 0 ]; then
  while IFS=$'\t' read -r num item _; do
    [ -z "$num" ] || [[ "$dos_tickets" == *" $num "* ]] && continue
    gh api graphql -f query="$TIRAR" -f projeto="$proj_id" -f item="$item" >/dev/null
    echo "#$num saiu do projeto: não é de nenhum ticket daqui"; mudancas=$((mudancas + 1))
  done <<<"$itens"
fi
[ $dry -eq 0 ] && echo "$mudancas mudança(s)"
exit 0
