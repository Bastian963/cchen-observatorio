#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
CHECK_SCRIPT="${CHECK_SCRIPT:-$ROOT_DIR/Scripts/check_observatorio_public_portal.sh}"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/.env.public}"
BASE_COMPOSE_FILE="${BASE_COMPOSE_FILE:-$ROOT_DIR/docker-compose.observatorio.yml}"
PUBLIC_COMPOSE_FILE="${PUBLIC_COMPOSE_FILE:-$ROOT_DIR/docker-compose.observatorio.public.yml}"
TIMEOUT_SECONDS="${TIMEOUT_SECONDS:-900}"
INTERVAL_SECONDS="${INTERVAL_SECONDS:-10}"
SHOW_COMPOSE_PS="${SHOW_COMPOSE_PS:-true}"

if [[ ! -f "$CHECK_SCRIPT" ]]; then
  echo "[post-start-public-portal] ERROR: no existe el script de chequeo: $CHECK_SCRIPT"
  exit 1
fi

if ! [[ "$TIMEOUT_SECONDS" =~ ^[0-9]+$ ]] || ! [[ "$INTERVAL_SECONDS" =~ ^[0-9]+$ ]]; then
  echo "[post-start-public-portal] ERROR: TIMEOUT_SECONDS e INTERVAL_SECONDS deben ser enteros"
  exit 1
fi

deadline=$(( $(date +%s) + TIMEOUT_SECONDS ))
attempt=1

echo "[post-start-public-portal] esperando que el portal publico 3 en 1 quede operativo"
echo "[post-start-public-portal] timeout=${TIMEOUT_SECONDS}s interval=${INTERVAL_SECONDS}s"

while true; do
  if output="$(ENV_FILE="$ENV_FILE" bash "$CHECK_SCRIPT" 2>&1)"; then
    printf '%s\n' "$output"
    echo "[post-start-public-portal] validacion completada"
    exit 0
  fi

  now=$(date +%s)
  remaining=$(( deadline - now ))

  echo "[post-start-public-portal] intento $attempt aun no exitoso"
  printf '%s\n' "$output"

  if [[ "$SHOW_COMPOSE_PS" == "true" ]] && command -v docker >/dev/null 2>&1 \
    && [[ -f "$BASE_COMPOSE_FILE" ]] && [[ -f "$PUBLIC_COMPOSE_FILE" ]]; then
    docker compose \
      --env-file "$ENV_FILE" \
      -f "$BASE_COMPOSE_FILE" \
      -f "$PUBLIC_COMPOSE_FILE" \
      ps || true
  fi

  if (( remaining <= 0 )); then
    echo "[post-start-public-portal] ERROR: se agoto la espera sin validar las URLs publicadas"
    exit 1
  fi

  echo "[post-start-public-portal] reintentando en ${INTERVAL_SECONDS}s (${remaining}s restantes)"
  sleep "$INTERVAL_SECONDS"
  attempt=$((attempt + 1))
done
