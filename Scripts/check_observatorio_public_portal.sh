#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/.env.public}"
if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

OBSERVATORIO_DASHBOARD_URL="${OBSERVATORIO_DASHBOARD_URL:-https://observatorio.cchen.cl}"
OBSERVATORIO_INTERNAL_DASHBOARD_URL="${OBSERVATORIO_INTERNAL_DASHBOARD_URL:-https://obs-int.cchen.cl}"
OBSERVATORIO_DSPACE_UI_URL="${OBSERVATORIO_DSPACE_UI_URL:-https://repo.cchen.cl}"
OBSERVATORIO_DSPACE_API_URL="${OBSERVATORIO_DSPACE_API_URL:-https://repo.cchen.cl/server/api}"
OBSERVATORIO_CKAN_URL="${OBSERVATORIO_CKAN_URL:-https://datos.cchen.cl}"
OBSERVATORIO_CKAN_API_URL="${OBSERVATORIO_CKAN_API_URL:-https://datos.cchen.cl/api/3/action/status_show}"
OBSERVATORIO_INTERNAL_BASIC_AUTH_CREDENTIALS="${OBSERVATORIO_INTERNAL_BASIC_AUTH_CREDENTIALS:-${OBSERVATORIO_BASIC_AUTH_CREDENTIALS:-}}"
OBSERVATORIO_TLS_INSECURE="${OBSERVATORIO_TLS_INSECURE:-false}"

curl_args=( -fsS --max-time 12 )
if [[ "${OBSERVATORIO_TLS_INSECURE}" == "true" ]]; then
  curl_args+=( -k )
fi

check_url() {
  local label="$1"
  local url="$2"
  local needle="${3:-}"
  shift 3 || true
  local extra_args=( "$@" )

  echo "[public-portal] ${label}: ${url}"
  if ! body="$(curl "${curl_args[@]}" "${extra_args[@]}" "${url}")"; then
    echo "[public-portal] ERROR: ${label} sin respuesta"
    return 1
  fi

  if [[ -n "${needle}" ]] && ! grep -Eqi "${needle}" <<<"${body}"; then
    echo "[public-portal] ERROR: ${label} respondió, pero no contiene '${needle}'"
    return 1
  fi

  echo "[public-portal] OK: ${label}"
}

check_url "Dashboard publico" "${OBSERVATORIO_DASHBOARD_URL%/}/_stcore/health" "ok"
check_url "DSpace UI" "${OBSERVATORIO_DSPACE_UI_URL}"
check_url "DSpace REST" "${OBSERVATORIO_DSPACE_API_URL}" "_links"
check_url "CKAN UI" "${OBSERVATORIO_CKAN_URL}"
check_url "CKAN Action API" "${OBSERVATORIO_CKAN_API_URL}" "success"

if [[ -n "${OBSERVATORIO_INTERNAL_BASIC_AUTH_CREDENTIALS}" ]]; then
  check_url \
    "Dashboard interno" \
    "${OBSERVATORIO_INTERNAL_DASHBOARD_URL%/}/_stcore/health" \
    "ok" \
    -u "${OBSERVATORIO_INTERNAL_BASIC_AUTH_CREDENTIALS}"
else
  echo "[public-portal] SKIP: dashboard interno sin credenciales Basic Auth configuradas"
fi

echo "[public-portal] observatorio 3 en 1 publico y accesible por URL"
