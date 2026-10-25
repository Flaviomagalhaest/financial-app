#!/usr/bin/env bash
# Renomeia "Platinum Master Card - Despesas fixas.xlsx" para YYYYMM.xls.
# Uso: scripts/renomear-fatura.sh [YYYYMM]
#   - Com YYYYMM: usa esse nome (ex.: 202002 -> 202002.xls).
#   - Sem argumento: no diretório atual, pega o maior YYYYMM já existente
#     (arquivos YYYYMM.xls ou YYYYMM.xlsx) e usa o mês seguinte.
#     Se não houver nenhum, usa o mês corrente.
set -euo pipefail

ORIGEM="Platinum Master Card - Despesas fixas.xlsx"
dir=$(pwd)

if [ ! -f "$dir/$ORIGEM" ]; then
  echo "Arquivo não encontrado em $dir: $ORIGEM" >&2
  exit 1
fi

if [ $# -ge 1 ]; then
  nome=$1
  [[ $nome =~ ^[0-9]{6}$ ]] || { echo "Nome inválido, use YYYYMM: $nome" >&2; exit 1; }
else
  ultimo=""
  for f in "$dir"/[0-9][0-9][0-9][0-9][0-9][0-9].xls "$dir"/[0-9][0-9][0-9][0-9][0-9][0-9].xlsx; do
    [ -e "$f" ] || continue
    base=$(basename "$f"); base=${base%%.*}
    m=$((10#${base:4:2}))
    (( m >= 1 && m <= 12 )) || continue
    if [[ -z $ultimo || $base > $ultimo ]]; then ultimo=$base; fi
  done

  if [ -z "$ultimo" ]; then
    nome=$(date +%Y%m)
  else
    ano=$((10#${ultimo:0:4})); mes=$((10#${ultimo:4:2}))
    mes=$((mes + 1))
    if (( mes > 12 )); then mes=1; ano=$((ano + 1)); fi
    nome=$(printf '%04d%02d' "$ano" "$mes")
  fi
fi

destino="$dir/$nome.xls"
if [ -e "$destino" ]; then
  echo "Já existe, nada foi feito: $nome.xls" >&2
  exit 1
fi

mv -- "$dir/$ORIGEM" "$destino"
echo "$ORIGEM -> $nome.xls"
