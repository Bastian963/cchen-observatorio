#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

if [[ -n "${OBSERVATORIO_ENV_FILE:-}" ]]; then
  if [[ "${OBSERVATORIO_ENV_FILE}" = /* ]]; then
    DEFAULT_ENV_FILE="${OBSERVATORIO_ENV_FILE}"
  else
    DEFAULT_ENV_FILE="$ROOT_DIR/${OBSERVATORIO_ENV_FILE}"
  fi
else
  DEFAULT_ENV_FILE="$ROOT_DIR/.env.prod"
fi

ENV_FILE="${ENV_FILE:-$DEFAULT_ENV_FILE}"

if [[ -z "${ENV_TEMPLATE:-}" ]]; then
  case "$(basename "$ENV_FILE")" in
    .env.public)
      ENV_TEMPLATE="$ROOT_DIR/.env.public.example"
      ;;
    .env.prod)
      ENV_TEMPLATE="$ROOT_DIR/.env.prod.example"
      ;;
    *)
      ENV_TEMPLATE="$ROOT_DIR/.env.prod.example"
      ;;
  esac
fi

OBSERVATORIO_ROOT="${OBSERVATORIO_ROOT:-/srv/observatorio}"
TLS_DIR="${OBSERVATORIO_TLS_DIR:-$OBSERVATORIO_ROOT/tls}"
NGINX_DIR="$(dirname "${OBSERVATORIO_BASIC_AUTH_FILE:-$OBSERVATORIO_ROOT/nginx/.htpasswd}")"
LOG_DIR="${OBSERVATORIO_NGINX_LOG_DIR:-$OBSERVATORIO_ROOT/logs/nginx}"
BACKUP_DIR="${OBSERVATORIO_BACKUP_DIR:-$OBSERVATORIO_ROOT/backups}"
HTPASSWD_FILE="${OBSERVATORIO_BASIC_AUTH_FILE:-$NGINX_DIR/.htpasswd}"
BASIC_AUTH_USER="${OBSERVATORIO_BASIC_AUTH_USER:-observatorio}"
BASIC_AUTH_PASSWORD="${OBSERVATORIO_BASIC_AUTH_PASSWORD:-}"
CREATE_HTPASSWD="${CREATE_HTPASSWD:-true}"
FORCE_HTPASSWD="${FORCE_HTPASSWD:-false}"

if [[ ! -f "$ENV_TEMPLATE" ]]; then
  echo "[bootstrap-vm] ERROR: no existe la plantilla $ENV_TEMPLATE"
  exit 1
fi

mkdir -p "$TLS_DIR" "$NGINX_DIR" "$LOG_DIR" "$BACKUP_DIR"

if [[ ! -f "$ENV_FILE" ]]; then
  cp "$ENV_TEMPLATE" "$ENV_FILE"
  echo "[bootstrap-vm] archivo de entorno creado desde la plantilla: $ENV_FILE"
else
  echo "[bootstrap-vm] reutilizando archivo de entorno existente: $ENV_FILE"
fi

if [[ "$CREATE_HTPASSWD" == "true" ]]; then
  if [[ -f "$HTPASSWD_FILE" && "$FORCE_HTPASSWD" != "true" ]]; then
    echo "[bootstrap-vm] reutilizando Basic Auth existente: $HTPASSWD_FILE"
  else
    if [[ -z "$BASIC_AUTH_PASSWORD" ]]; then
      echo "[bootstrap-vm] ERROR: define OBSERVATORIO_BASIC_AUTH_PASSWORD para crear $HTPASSWD_FILE"
      exit 1
    fi

    docker run --rm --entrypoint htpasswd httpd:2 -Bbn "$BASIC_AUTH_USER" "$BASIC_AUTH_PASSWORD" \
      > "$HTPASSWD_FILE"
    chmod 600 "$HTPASSWD_FILE"
    echo "[bootstrap-vm] Basic Auth creado en $HTPASSWD_FILE"
  fi
fi

echo "[bootstrap-vm] directorios preparados:"
echo "  - TLS: $TLS_DIR"
echo "  - Nginx auth: $NGINX_DIR"
echo "  - Logs: $LOG_DIR"
echo "  - Backups: $BACKUP_DIR"
echo "[bootstrap-vm] siguientes pasos:"
echo "  1. copiar certificados TLS a $TLS_DIR"
echo "  2. completar $ENV_FILE"
case "$(basename "$ENV_FILE")" in
  .env.public)
    echo "  3. crear Dashboard/.streamlit/secrets.public.toml en la VM"
    echo "  4. crear Dashboard/.streamlit/secrets.toml para obs-int"
    ;;
  *)
    echo "  3. crear Dashboard/.streamlit/secrets.toml en la VM"
    ;;
esac
