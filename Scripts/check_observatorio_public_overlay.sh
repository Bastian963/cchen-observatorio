#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/.env.public.example}"
BASE_COMPOSE_FILE="${BASE_COMPOSE_FILE:-$ROOT_DIR/docker-compose.observatorio.yml}"
PUBLIC_COMPOSE_FILE="${PUBLIC_COMPOSE_FILE:-$ROOT_DIR/docker-compose.observatorio.public.yml}"
TMP_CONFIG="$(mktemp)"
trap 'rm -f "$TMP_CONFIG"' EXIT

required_files=(
  "$ROOT_DIR/.env.public.example"
  "$ROOT_DIR/docker-compose.observatorio.public.yml"
  "$ROOT_DIR/deploy/nginx/Dockerfile"
  "$ROOT_DIR/deploy/nginx/templates/observatorio-public-portal.conf.template"
  "$ROOT_DIR/Dashboard/.streamlit/secrets.public.toml.example"
  "$ROOT_DIR/Scripts/check_observatorio_public_portal.sh"
  "$ROOT_DIR/Scripts/wait_and_check_observatorio_public_portal.sh"
  "$ROOT_DIR/Scripts/deploy_observatorio_public.sh"
  "$ROOT_DIR/Scripts/check_public_beta_readiness.py"
)

for path in "${required_files[@]}"; do
  [[ -f "$path" ]] || { echo "[public-overlay] ERROR: falta $path"; exit 1; }
done

python3 -m py_compile \
  "$ROOT_DIR/Dashboard/app.py" \
  "$ROOT_DIR/Dashboard/sections/asistente_id.py" \
  "$ROOT_DIR/Dashboard/sections/plataforma_institucional.py" \
  "$ROOT_DIR/Dashboard/sections/shared.py" \
  "$ROOT_DIR/dspace-frontend/docker-entrypoint.py"

bash -n \
  "$ROOT_DIR/Scripts/check_observatorio_public_portal.sh" \
  "$ROOT_DIR/Scripts/wait_and_check_observatorio_public_portal.sh" \
  "$ROOT_DIR/Scripts/deploy_observatorio_public.sh"

python3 "$ROOT_DIR/Scripts/validate_asset_catalog.py"
python3 "$ROOT_DIR/Scripts/check_assistant_asset_links.py"
python3 "$ROOT_DIR/Scripts/check_public_beta_readiness.py"

docker compose \
  --env-file "$ENV_FILE" \
  -f "$BASE_COMPOSE_FILE" \
  -f "$PUBLIC_COMPOSE_FILE" \
  config > "$TMP_CONFIG"

published_ports="$(rg 'published:' "$TMP_CONFIG" | awk '{print $2}' | tr -d '"' | sort -n -u | paste -sd' ' -)"
if [[ "$published_ports" != "80 443" ]]; then
  echo "[public-overlay] ERROR: puertos publicados inesperados: '${published_ports}'"
  exit 1
fi

if rg -n 'published: "(8501|8080|5001|8983|8984|5432|6379)"' "$TMP_CONFIG" >/dev/null; then
  echo "[public-overlay] ERROR: hay puertos internos publicados en el overlay publico"
  exit 1
fi

rg -q 'OBSERVATORIO_APP_MODE: public' "$TMP_CONFIG"
rg -q 'OBSERVATORIO_APP_MODE: internal' "$TMP_CONFIG"
rg -Fq 'OBSERVATORIO_PUBLIC_SECRETS_FILE' "$ROOT_DIR/.env.public.example"
rg -Fq 'secrets.public.toml' "$TMP_CONFIG"
rg -Fq 'server_name ${OBSERVATORIO_PUBLIC_DASHBOARD_HOST};' "$ROOT_DIR/deploy/nginx/templates/observatorio-public-portal.conf.template"

echo "[public-overlay] OK: overlay publico renderiza solo 80/443 y separa dashboard publico e interno"
