#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
CHECK_SCRIPT="${CHECK_SCRIPT:-$ROOT_DIR/Scripts/check_observatorio_stack.sh}"
COMPOSE_FILE="${COMPOSE_FILE:-$ROOT_DIR/docker-compose.observatorio.yml}"
TIMEOUT_SECONDS="${TIMEOUT_SECONDS:-900}"
INTERVAL_SECONDS="${INTERVAL_SECONDS:-10}"
SHOW_COMPOSE_PS="${SHOW_COMPOSE_PS:-true}"

if [[ ! -f "$CHECK_SCRIPT" ]]; then
  echo "[post-start] ERROR: no existe el script de chequeo: $CHECK_SCRIPT"
  exit 1
fi

if ! [[ "$TIMEOUT_SECONDS" =~ ^[0-9]+$ ]] || ! [[ "$INTERVAL_SECONDS" =~ ^[0-9]+$ ]]; then
  echo "[post-start] ERROR: TIMEOUT_SECONDS e INTERVAL_SECONDS deben ser enteros"
  exit 1
fi

deadline=$(( $(date +%s) + TIMEOUT_SECONDS ))
attempt=1

echo "[post-start] esperando que el observatorio 3 en 1 quede operativo"
echo "[post-start] timeout=${TIMEOUT_SECONDS}s interval=${INTERVAL_SECONDS}s"

while true; do
  if output="$(bash "$CHECK_SCRIPT" 2>&1)"; then
    printf '%s\n' "$output"
    echo "[post-start] validacion completada"
    exit 0
  fi

  now=$(date +%s)
  remaining=$(( deadline - now ))

  echo "[post-start] intento $attempt aun no exitoso"
  printf '%s\n' "$output"

  if [[ "$SHOW_COMPOSE_PS" == "true" ]] && command -v docker >/dev/null 2>&1 && [[ -f "$COMPOSE_FILE" ]]; then
    docker compose -f "$COMPOSE_FILE" ps || true
  fi

  if (( remaining <= 0 )); then
    echo "[post-start] ERROR: se agoto la espera sin validar el stack"
    exit 1
  fi

  echo "[post-start] reintentando en ${INTERVAL_SECONDS}s (${remaining}s restantes)"
  sleep "$INTERVAL_SECONDS"
  attempt=$((attempt + 1))
done
