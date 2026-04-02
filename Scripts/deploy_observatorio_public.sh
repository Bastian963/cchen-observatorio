#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/.env.public}"
BASE_COMPOSE_FILE="${BASE_COMPOSE_FILE:-$ROOT_DIR/docker-compose.observatorio.yml}"
PUBLIC_COMPOSE_FILE="${PUBLIC_COMPOSE_FILE:-$ROOT_DIR/docker-compose.observatorio.public.yml}"
COMPOSE_ACTION="${COMPOSE_ACTION:-up}"
WAIT_FOR_PUBLIC="${WAIT_FOR_PUBLIC:-true}"
RUN_LOCAL_OVERLAY_CHECK="${RUN_LOCAL_OVERLAY_CHECK:-true}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "[deploy-public] ERROR: no existe el archivo de entorno $ENV_FILE"
  exit 1
fi

compose() {
  docker compose \
    --env-file "$ENV_FILE" \
    -f "$BASE_COMPOSE_FILE" \
    -f "$PUBLIC_COMPOSE_FILE" \
    "$@"
}

if [[ "$RUN_LOCAL_OVERLAY_CHECK" == "true" ]]; then
  ENV_FILE="$ENV_FILE" BASE_COMPOSE_FILE="$BASE_COMPOSE_FILE" PUBLIC_COMPOSE_FILE="$PUBLIC_COMPOSE_FILE" \
    bash "$ROOT_DIR/Scripts/check_observatorio_public_overlay.sh"
fi

case "$COMPOSE_ACTION" in
  up)
    compose up -d --build
    ;;
  restart)
    compose restart
    ;;
  pull-up)
    compose pull
    compose up -d --build
    ;;
  *)
    echo "[deploy-public] ERROR: COMPOSE_ACTION debe ser up, restart o pull-up"
    exit 1
    ;;
esac

compose ps

if [[ "$WAIT_FOR_PUBLIC" == "true" ]]; then
  ENV_FILE="$ENV_FILE" BASE_COMPOSE_FILE="$BASE_COMPOSE_FILE" PUBLIC_COMPOSE_FILE="$PUBLIC_COMPOSE_FILE" \
    bash "$ROOT_DIR/Scripts/wait_and_check_observatorio_public_portal.sh"
fi
