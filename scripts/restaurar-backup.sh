#!/usr/bin/env bash
# Restaura um backup no banco de um ambiente, feito pelo dono com a credencial dele (ADR 0012).
#
#   scripts/restaurar-backup.sh <prod|dev> <arquivo.zip>              # banco vazio
#   scripts/restaurar-backup.sh dev <arquivo.zip> --esvaziar          # ensaio com o backup de prod
#
# Só grava num banco vazio, tudo ou nada, e confere contagens e somas contra o manifesto. Com
# --esvaziar (só no dev), apaga antes os dados do banco. Depois exporta de novo e exige o mesmo zip.
set -euo pipefail

uso() { sed -n '4,5s/^#   //p' "$0" >&2; exit 2; }
[ $# -ge 2 ] || uso
AMBIENTE=$1
ARQUIVO=$(realpath "$2")
shift 2
case "$AMBIENTE" in prod | dev) ;; *) uso ;; esac

RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
# Atribuir antes de exportar: `export X=$(...)` esconde a falha do comando do `set -e`.
AWS_REGION=$(jq -r .regiao "$RAIZ/config/aws.json")
DSQL_ENDPOINT=$(aws cloudformation describe-stacks --region "$AWS_REGION" \
  --stack-name "financial-$AMBIENTE-dados" \
  --query "Stacks[0].Outputs[?OutputKey=='DsqlEndpoint'].OutputValue" --output text)
# Sem endpoint, a conexão cairia no DATABASE_URL, que pode ser outro banco.
case "$DSQL_ENDPOINT" in "" | None) echo "sem o DsqlEndpoint de financial-$AMBIENTE-dados" >&2; exit 1 ;; esac
export AWS_REGION DSQL_ENDPOINT AMBIENTE
cd "$RAIZ/backend"
uv run --no-dev python -m app.restauracao "$ARQUIVO" "$@"
