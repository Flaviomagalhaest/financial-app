#!/usr/bin/env bash
# Monta o pacote da Lambda da API (arm64, python3.14) sem Docker: dependências em wheels
# de aarch64, o código de backend/app, as migrations e config/valores-iniciais.json.
# Uso: scripts/empacotar-lambda.sh [destino]   (padrão: build/lambda, lido pelo CDK em infra/)
set -euo pipefail

RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
DESTINO="${1:-$RAIZ/build/lambda}"

rm -rf "$DESTINO"
mkdir -p "$DESTINO/config"
(cd "$RAIZ/backend" && uv export --frozen --no-dev --no-hashes --no-emit-project -q) > "$DESTINO/.requisitos.txt"
uv pip install -q --target "$DESTINO" -r "$DESTINO/.requisitos.txt" \
  --python-platform aarch64-manylinux_2_28 --python-version 3.14 --only-binary :all:
rm "$DESTINO/.requisitos.txt"
cp -r "$RAIZ/backend/app" "$RAIZ/backend/migrations" "$DESTINO/"
cp "$RAIZ/config/valores-iniciais.json" "$DESTINO/config/"
find "$DESTINO" -name __pycache__ -type d -prune -exec rm -rf {} +
echo "pacote da Lambda em $DESTINO ($(du -sh "$DESTINO" | cut -f1))"
