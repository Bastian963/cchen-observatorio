#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/.env.prod.example}"
BASE_COMPOSE_FILE="${BASE_COMPOSE_FILE:-$ROOT_DIR/docker-compose.observatorio.yml}"
PROD_COMPOSE_FILE="${PROD_COMPOSE_FILE:-$ROOT_DIR/docker-compose.observatorio.prod.yml}"
TMP_CONFIG="$(mktemp)"
trap 'rm -f "$TMP_CONFIG"' EXIT

search_text() {
  if command -v rg >/dev/null 2>&1; then
    rg "$@"
    return
  fi

  case "${1:-}" in
    -Fq)
      shift
      grep -Fq -- "$1" "$2"
      ;;
    -q)
      shift
      grep -q -- "$1" "$2"
      ;;
    -n)
      shift
      grep -En -- "$1" "$2"
      ;;
    *)
      grep -E -- "$1" "$2"
      ;;
  esac
}

required_files=(
  "$ROOT_DIR/.env.prod.example"
  "$ROOT_DIR/docker-compose.observatorio.prod.yml"
  "$ROOT_DIR/deploy/nginx/Dockerfile"
  "$ROOT_DIR/deploy/nginx/templates/observatorio-public.conf.template"
  "$ROOT_DIR/Scripts/check_observatorio_public_url.sh"
  "$ROOT_DIR/Scripts/wait_and_check_observatorio_public_url.sh"
  "$ROOT_DIR/Scripts/backup_observatorio_prod.sh"
  "$ROOT_DIR/Scripts/prepare_local_public_demo.sh"
  "$ROOT_DIR/dspace-frontend/docker-entrypoint.py"
)

for path in "${required_files[@]}"; do
  [[ -f "$path" ]] || { echo "[prod-overlay] ERROR: falta $path"; exit 1; }
done

python3 -m py_compile "$ROOT_DIR/dspace-frontend/docker-entrypoint.py"
bash -n \
  "$ROOT_DIR/Scripts/check_observatorio_public_url.sh" \
  "$ROOT_DIR/Scripts/wait_and_check_observatorio_public_url.sh" \
  "$ROOT_DIR/Scripts/backup_observatorio_prod.sh" \
  "$ROOT_DIR/Scripts/prepare_local_public_demo.sh"

docker compose \
  --env-file "$ENV_FILE" \
  -f "$BASE_COMPOSE_FILE" \
  -f "$PROD_COMPOSE_FILE" \
  config > "$TMP_CONFIG"

published_ports="$(search_text 'published:' "$TMP_CONFIG" | awk '{print $2}' | tr -d '"' | sort -n -u | paste -sd' ' -)"
if [[ "$published_ports" != "80 443" ]]; then
  echo "[prod-overlay] ERROR: puertos publicados inesperados: '${published_ports}'"
  exit 1
fi

if search_text -n 'published: "(8501|8080|5001|8983|8984|5432|6379)"' "$TMP_CONFIG" >/dev/null; then
  echo "[prod-overlay] ERROR: hay puertos internos publicados en el overlay productivo"
  exit 1
fi

search_text -q '/etc/nginx/.htpasswd' "$TMP_CONFIG"
search_text -q 'OBSERVATORIO_DASHBOARD_URL: https://obs-int.cchen.cl' "$TMP_CONFIG"
search_text -q 'CKAN_SITE_URL: https://datos-int.cchen.cl' "$TMP_CONFIG"
search_text -q 'dspace__P__server__P__url: https://repo-int.cchen.cl/server' "$TMP_CONFIG"

echo "[prod-overlay] OK: compose productivo renderiza solo 80/443 y mantiene URLs canónicas"
