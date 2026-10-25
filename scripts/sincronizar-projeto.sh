#!/usr/bin/env bash
# Espelha os tickets de .scratch/ no projeto "Financial App" do GitHub:
# adiciona a issue ao projeto, põe a coluna certa em "Status" e abre/fecha a issue.
# Precisa do gh autenticado com o escopo `project` (gh auth refresh -s project).
# Uso: scripts/sincronizar-projeto.sh [--dry-run] [caminho-do-ticket ...]
set -euo pipefail

OWNER=Flaviomagalhaest
REPO=financial-app
PROJECT=3

dry=0
[ "${1:-}" = "--dry-run" ] && { dry=1; shift; }
cd "$(git rev-parse --show-toplevel)"
files=("$@")
[ ${#files[@]} -eq 0 ] && files=(.scratch/*/issues/*.md)

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

if [ $dry -eq 0 ]; then
  proj_id=$(gh project view $PROJECT --owner $OWNER --format json --jq .id)
  field=$(gh project field-list $PROJECT --owner $OWNER --format json \
    --jq '.fields[] | select(.name=="Status")')
  field_id=$(jq -r .id <<<"$field")
fi

for f in "${files[@]}"; do
  num=$(campo "$f" Issue | tr -dc 0-9)
  [ -z "$num" ] && { echo "sem linha Issue: $f" >&2; continue; }
  col=$(coluna "$f")
  echo "#$num -> $col  ($f)"
  [ $dry -eq 1 ] && continue

  url=https://github.com/$OWNER/$REPO/issues/$num
  item=$(gh project item-add $PROJECT --owner $OWNER --url "$url" --format json --jq .id)
  opt=$(jq -r --arg c "$col" '.options[] | select(.name==$c) | .id' <<<"$field")
  [ -z "$opt" ] && { echo "coluna $col não existe no projeto" >&2; exit 1; }
  gh project item-edit --id "$item" --project-id "$proj_id" --field-id "$field_id" \
    --single-select-option-id "$opt" >/dev/null

  if fechado "$f"; then
    reason=completed; case "$(campo "$f" Status)" in wontfix*) reason="not planned" ;; esac
    gh issue close "$num" --repo $OWNER/$REPO --reason "$reason" >/dev/null 2>&1 || true
  else
    gh issue reopen "$num" --repo $OWNER/$REPO >/dev/null 2>&1 || true
  fi
  if [ "$col" = BLOCKED ]; then
    gh issue edit "$num" --repo $OWNER/$REPO --add-label blocked >/dev/null
  else
    gh issue edit "$num" --repo $OWNER/$REPO --remove-label blocked >/dev/null 2>&1 || true
  fi
done
