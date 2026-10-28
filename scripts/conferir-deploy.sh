#!/usr/bin/env bash
# Teste de fumaça depois do deploy: o endereço serve a PWA e /api/saude responde pela Lambda
# e pelo banco com ao menos as migrations do repositório aplicadas (o dev é dividido pelas
# branches, então pode ter migrations de outra branch a mais).
# Uso: scripts/conferir-deploy.sh https://dxxxx.cloudfront.net
set -euo pipefail

ENDERECO="${1:?uso: $0 <endereço do app>}"
ENDERECO="${ENDERECO%/}"
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
ESPERADAS=$(find "$RAIZ/backend/migrations" -name '[0-9][0-9][0-9][0-9]_*.sql' | wc -l)
TENTATIVAS="${TENTATIVAS:-10}"

for i in $(seq "$TENTATIVAS"); do
  # A primeira chamada pode pegar a Lambda e o DSQL frios; tenta de novo antes de falhar.
  if SAUDE=$(curl -fsS --max-time 20 "$ENDERECO/api/saude") \
    && echo "$SAUDE" | python3 -c '
import json, sys
s = json.load(sys.stdin)
sys.exit(0 if s["status"] == "ok" and s["migrations"] >= int(sys.argv[1]) else 1)' "$ESPERADAS"; then
    break
  fi
  echo "tentativa $i: /api/saude ainda não respondeu ok com $ESPERADAS migrations (${SAUDE:-sem resposta})"
  if [ "$i" = "$TENTATIVAS" ]; then
    echo "::error::$ENDERECO/api/saude não respondeu ok com $ESPERADAS migrations"
    exit 1
  fi
  sleep 6
done
echo "API no ar: $SAUDE"

curl -fsS --max-time 20 "$ENDERECO/" | grep -q '<div id="root">' \
  || { echo "::error::$ENDERECO/ não serviu a PWA"; exit 1; }
echo "PWA no ar em $ENDERECO"
