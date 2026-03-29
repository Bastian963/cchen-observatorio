#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/.env.prod}"
BASE_COMPOSE_FILE="${BASE_COMPOSE_FILE:-$ROOT_DIR/docker-compose.observatorio.yml}"
PROD_COMPOSE_FILE="${PROD_COMPOSE_FILE:-$ROOT_DIR/docker-compose.observatorio.prod.yml}"

reverse_proxy_name="${REVERSE_PROXY_NAME:-observatorio-reverse-proxy}"
forbidden_ports_regex=':(8501|8080|5001|8983|8984|5432|6379)->'

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

HTTP_PORT="${OBSERVATORIO_HTTP_PORT:-80}"
HTTPS_PORT="${OBSERVATORIO_HTTPS_PORT:-443}"

compose() {
  docker compose \
    --env-file "$ENV_FILE" \
    -f "$BASE_COMPOSE_FILE" \
    -f "$PROD_COMPOSE_FILE" \
    "$@"
}

if ! compose ps >/dev/null 2>&1; then
  echo "[published-ports] ERROR: no fue posible consultar el stack productivo"
  exit 1
fi

ps_output="$(docker ps --format '{{.Names}}\t{{.Ports}}')"

reverse_proxy_ports="$(grep -E "^${reverse_proxy_name}[[:space:]]" <<<"$ps_output" || true)"
if [[ -z "$reverse_proxy_ports" ]]; then
  echo "[published-ports] ERROR: no se encontro el contenedor ${reverse_proxy_name}"
  exit 1
fi

if ! grep -Eq ":${HTTP_PORT}->" <<<"$reverse_proxy_ports" || ! grep -Eq ":${HTTPS_PORT}->" <<<"$reverse_proxy_ports"; then
  echo "[published-ports] ERROR: el reverse proxy no expone ${HTTP_PORT}/${HTTPS_PORT} como se esperaba"
  exit 1
fi

if grep -Ev "^${reverse_proxy_name}[[:space:]]" <<<"$ps_output" | grep -Eq "$forbidden_ports_regex"; then
  echo "[published-ports] ERROR: hay puertos internos publicados fuera del reverse proxy"
  grep -Ev "^${reverse_proxy_name}[[:space:]]" <<<"$ps_output" | grep -E "$forbidden_ports_regex" || true
  exit 1
fi

echo "[published-ports] OK: solo el reverse proxy publica ${HTTP_PORT}/${HTTPS_PORT}"
