#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

resolve_env_file() {
  local raw_path="$1"
  if [[ "$raw_path" = /* ]]; then
    printf '%s\n' "$raw_path"
  else
    printf '%s\n' "$ROOT_DIR/$raw_path"
  fi
}

RAW_ENV_FILE="${ENV_FILE:-${OBSERVATORIO_ENV_FILE:-.env.public}}"
ENV_FILE="$(resolve_env_file "$RAW_ENV_FILE")"
LETSENCRYPT_BASE_DIR="${LETSENCRYPT_BASE_DIR:-/etc/letsencrypt/live}"

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

TLS_DIR="${OBSERVATORIO_TLS_DIR:-/srv/observatorio/tls}"
mkdir -p "$TLS_DIR"

hosts=(
  "${OBSERVATORIO_PUBLIC_DASHBOARD_HOST:-observatorio.cchen.cl}"
  "${OBSERVATORIO_INTERNAL_DASHBOARD_HOST:-obs-int.cchen.cl}"
  "${OBSERVATORIO_DSPACE_HOST:-repo.cchen.cl}"
  "${OBSERVATORIO_CKAN_HOST:-datos.cchen.cl}"
)

printf '%s\n' "${hosts[@]}" | awk 'NF' | sort -u | while read -r host; do
  cert_dir="${LETSENCRYPT_BASE_DIR%/}/$host"
  fullchain_path="$cert_dir/fullchain.pem"
  privkey_path="$cert_dir/privkey.pem"

  if [[ ! -r "$fullchain_path" || ! -r "$privkey_path" ]]; then
    echo "[letsencrypt-sync] ERROR: faltan certificados para $host en $cert_dir"
    exit 1
  fi

  install -m 644 "$fullchain_path" "$TLS_DIR/$host.crt"
  install -m 600 "$privkey_path" "$TLS_DIR/$host.key"
  echo "[letsencrypt-sync] OK: $host"
done

echo "[letsencrypt-sync] certificados sincronizados en $TLS_DIR"
