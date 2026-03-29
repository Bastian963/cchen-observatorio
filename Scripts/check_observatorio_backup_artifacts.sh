#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/.env.prod}"

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

BACKUP_DIR="${OBSERVATORIO_BACKUP_DIR:-/srv/observatorio/backups}"
TARGET_DIR="${TARGET_DIR:-}"

if [[ -z "$TARGET_DIR" ]]; then
  TARGET_DIR="$(find "$BACKUP_DIR" -mindepth 1 -maxdepth 1 -type d | sort | tail -n 1)"
fi

if [[ -z "$TARGET_DIR" || ! -d "$TARGET_DIR" ]]; then
  echo "[backup-check] ERROR: no se encontro un directorio de respaldo valido"
  exit 1
fi

required_files=(
  "dspace.sql"
  "ckan.sql"
  "ckan_datastore.sql"
  "dspace_assetstore.tgz"
  "ckan_storage.tgz"
)

for name in "${required_files[@]}"; do
  path="$TARGET_DIR/$name"
  [[ -s "$path" ]] || { echo "[backup-check] ERROR: falta o esta vacio $path"; exit 1; }
done

tar -tzf "$TARGET_DIR/dspace_assetstore.tgz" >/dev/null
tar -tzf "$TARGET_DIR/ckan_storage.tgz" >/dev/null

echo "[backup-check] OK: respaldo valido en $TARGET_DIR"
