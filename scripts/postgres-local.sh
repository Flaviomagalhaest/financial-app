#!/usr/bin/env bash
# Sobe um Postgres descartável sem Docker e imprime a DATABASE_URL.
# Uso: eval "$(scripts/postgres-local.sh)"   (o CI usa um service container, não este script)
# Como root (sessões na nuvem), o servidor roda como o usuário `postgres` do sistema.
set -euo pipefail

BIN="$(ls -d /usr/lib/postgresql/*/bin | sort -V | tail -1)"
PORT="${PGLOCAL_PORT:-54329}"
if [ "$(id -u)" = 0 ]; then
  DIR="${PGLOCAL_DIR:-/tmp/financial-app-pg}"
  AS=(runuser -u postgres --)
  mkdir -p "$DIR" && chown postgres "$DIR"
else
  DIR="${PGLOCAL_DIR:-$HOME/.cache/financial-app-pg}"
  AS=()
  mkdir -p "$DIR"
fi

if [ ! -d "$DIR/data" ]; then
  "${AS[@]}" "$BIN/initdb" -D "$DIR/data" -U postgres --auth=trust -E UTF8 --locale=C.UTF-8 >/dev/null
fi
if ! "${AS[@]}" "$BIN/pg_ctl" -D "$DIR/data" status >/dev/null 2>&1; then
  "${AS[@]}" "$BIN/pg_ctl" -D "$DIR/data" -o "-p $PORT -k $DIR" -l "$DIR/log" -w start >/dev/null
fi
"$BIN/psql" -h localhost -p "$PORT" -U postgres -tAc \
  "SELECT 1 FROM pg_database WHERE datname='financial_app'" | grep -q 1 \
  || "$BIN/createdb" -h localhost -p "$PORT" -U postgres financial_app

echo "export DATABASE_URL=postgresql://postgres@localhost:$PORT/financial_app"
