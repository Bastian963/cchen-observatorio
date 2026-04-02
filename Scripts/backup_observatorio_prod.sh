#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BASE_COMPOSE_FILE="${BASE_COMPOSE_FILE:-$ROOT_DIR/docker-compose.observatorio.yml}"

resolve_env_file() {
  local raw_path="$1"
  if [[ "$raw_path" = /* ]]; then
    printf '%s\n' "$raw_path"
  else
    printf '%s\n' "$ROOT_DIR/$raw_path"
  fi
}

RAW_ENV_FILE="${ENV_FILE:-${OBSERVATORIO_ENV_FILE:-.env.prod}}"
ENV_FILE="$(resolve_env_file "$RAW_ENV_FILE")"

case "$(basename "$ENV_FILE")" in
  .env.public)
    OVERLAY_COMPOSE_FILE="${PUBLIC_COMPOSE_FILE:-$ROOT_DIR/docker-compose.observatorio.public.yml}"
    ;;
  *)
    OVERLAY_COMPOSE_FILE="${PROD_COMPOSE_FILE:-$ROOT_DIR/docker-compose.observatorio.prod.yml}"
    ;;
esac

if [[ ! -f "$ENV_FILE" ]]; then
  echo "[backup] ERROR: no existe el archivo de entorno $ENV_FILE"
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

BACKUP_DIR="${OBSERVATORIO_BACKUP_DIR:-/srv/observatorio/backups}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
TARGET_DIR="${BACKUP_DIR%/}/${TIMESTAMP}"

compose() {
  docker compose \
    --env-file "$ENV_FILE" \
    -f "$BASE_COMPOSE_FILE" \
    -f "$OVERLAY_COMPOSE_FILE" \
    "$@"
}

mkdir -p "$TARGET_DIR"

echo "[backup] destino: $TARGET_DIR"
echo "[backup] exportando base DSpace"
compose exec -T dspace-db pg_dump -U dspace -d dspace > "${TARGET_DIR}/dspace.sql"

echo "[backup] exportando base CKAN"
compose exec -T ckan-db pg_dump -U ckan -d ckan > "${TARGET_DIR}/ckan.sql"

echo "[backup] exportando datastore CKAN"
compose exec -T ckan-db pg_dump -U ckan -d datastore > "${TARGET_DIR}/ckan_datastore.sql"

echo "[backup] archivando assetstore DSpace"
compose exec -T dspace-backend tar -C /dspace -czf - assetstore > "${TARGET_DIR}/dspace_assetstore.tgz"

echo "[backup] archivando storage CKAN"
compose exec -T ckan tar -C /var/lib -czf - ckan > "${TARGET_DIR}/ckan_storage.tgz"

echo "[backup] respaldo completado en $TARGET_DIR"
