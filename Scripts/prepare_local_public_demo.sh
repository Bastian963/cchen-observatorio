#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
RUNTIME_DIR="${RUNTIME_DIR:-$ROOT_DIR/deploy/local-prod-demo/runtime}"
TLS_DIR="${TLS_DIR:-$RUNTIME_DIR/tls}"
NGINX_DIR="${NGINX_DIR:-$RUNTIME_DIR/nginx}"
LOG_DIR="${LOG_DIR:-$RUNTIME_DIR/logs/nginx}"
BACKUP_DIR="${BACKUP_DIR:-$RUNTIME_DIR/backups}"
ENV_FILE="${ENV_FILE:-$RUNTIME_DIR/.env.prod.localhost}"

DASHBOARD_HOST="${DASHBOARD_HOST:-obs-int.localhost}"
DSPACE_HOST="${DSPACE_HOST:-repo-int.localhost}"
CKAN_HOST="${CKAN_HOST:-datos-int.localhost}"
HTTP_PORT="${HTTP_PORT:-8081}"
HTTPS_PORT="${HTTPS_PORT:-8443}"
BASIC_AUTH_USER="${BASIC_AUTH_USER:-observatorio}"
BASIC_AUTH_PASSWORD="${BASIC_AUTH_PASSWORD:-observatorio-demo}"

mkdir -p "$TLS_DIR" "$NGINX_DIR" "$LOG_DIR" "$BACKUP_DIR"

generate_cert() {
  local host="$1"
  local crt="$TLS_DIR/${host}.crt"
  local key="$TLS_DIR/${host}.key"

  if [[ -f "$crt" && -f "$key" ]]; then
    return
  fi

  openssl req \
    -x509 \
    -nodes \
    -newkey rsa:2048 \
    -days 30 \
    -subj "/CN=${host}" \
    -addext "subjectAltName=DNS:${host}" \
    -keyout "$key" \
    -out "$crt" >/dev/null 2>&1
}

generate_cert "$DASHBOARD_HOST"
generate_cert "$DSPACE_HOST"
generate_cert "$CKAN_HOST"

printf '%s:%s\n' "$BASIC_AUTH_USER" "$(openssl passwd -apr1 "$BASIC_AUTH_PASSWORD")" > "$NGINX_DIR/.htpasswd"
chmod 600 "$NGINX_DIR/.htpasswd"

cat > "$ENV_FILE" <<EOF
OBSERVATORIO_DASHBOARD_HOST=$DASHBOARD_HOST
OBSERVATORIO_DSPACE_HOST=$DSPACE_HOST
OBSERVATORIO_CKAN_HOST=$CKAN_HOST

OBSERVATORIO_DASHBOARD_URL=https://$DASHBOARD_HOST:$HTTPS_PORT
OBSERVATORIO_DSPACE_UI_URL=https://$DSPACE_HOST:$HTTPS_PORT
OBSERVATORIO_DSPACE_SERVER_URL=https://$DSPACE_HOST:$HTTPS_PORT/server
OBSERVATORIO_DSPACE_API_URL=https://$DSPACE_HOST:$HTTPS_PORT/server/api
OBSERVATORIO_CKAN_URL=https://$CKAN_HOST:$HTTPS_PORT
OBSERVATORIO_CKAN_API_URL=https://$CKAN_HOST:$HTTPS_PORT/api/3/action/status_show

OBSERVATORIO_HTTP_PORT=$HTTP_PORT
OBSERVATORIO_HTTPS_PORT=$HTTPS_PORT
OBSERVATORIO_BASIC_AUTH_REALM=Observatorio CCHEN Demo Local
OBSERVATORIO_TLS_DIR=$TLS_DIR
OBSERVATORIO_BASIC_AUTH_FILE=$NGINX_DIR/.htpasswd
OBSERVATORIO_NGINX_LOG_DIR=$LOG_DIR
OBSERVATORIO_BACKUP_DIR=$BACKUP_DIR
OBSERVATORIO_ENV_FILE=$ENV_FILE
OBSERVATORIO_BASIC_AUTH_CREDENTIALS=$BASIC_AUTH_USER:$BASIC_AUTH_PASSWORD
OBSERVATORIO_TLS_INSECURE=true

DSPACE_FRONTEND_REST_SSL=true
DSPACE_FRONTEND_REST_PORT=$HTTPS_PORT
DSPACE_FRONTEND_REST_NAMESPACE=/server
DSPACE_FRONTEND_UI_SSL=true
DSPACE_FRONTEND_UI_PORT=$HTTPS_PORT
DSPACE_FRONTEND_UI_NAMESPACE=/
EOF

echo "[local-prod-demo] entorno listo en $RUNTIME_DIR"
echo "[local-prod-demo] env file: $ENV_FILE"
echo "[local-prod-demo] credenciales proxy: $BASIC_AUTH_USER / $BASIC_AUTH_PASSWORD"
echo "[local-prod-demo] hosts:"
echo "  - https://$DASHBOARD_HOST:$HTTPS_PORT"
echo "  - https://$DSPACE_HOST:$HTTPS_PORT"
echo "  - https://$CKAN_HOST:$HTTPS_PORT"
