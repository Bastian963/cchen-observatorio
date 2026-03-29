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

OBSERVATORIO_DASHBOARD_URL="${OBSERVATORIO_DASHBOARD_URL:-https://obs-int.cchen.cl}"
OBSERVATORIO_DSPACE_UI_URL="${OBSERVATORIO_DSPACE_UI_URL:-https://repo-int.cchen.cl}"
OBSERVATORIO_DSPACE_API_URL="${OBSERVATORIO_DSPACE_API_URL:-https://repo-int.cchen.cl/server/api}"
OBSERVATORIO_CKAN_URL="${OBSERVATORIO_CKAN_URL:-https://datos-int.cchen.cl}"
OBSERVATORIO_CKAN_API_URL="${OBSERVATORIO_CKAN_API_URL:-https://datos-int.cchen.cl/api/3/action/status_show}"
OBSERVATORIO_BASIC_AUTH_CREDENTIALS="${OBSERVATORIO_BASIC_AUTH_CREDENTIALS:-}"
OBSERVATORIO_TLS_INSECURE="${OBSERVATORIO_TLS_INSECURE:-false}"

curl_args=( -fsS --max-time 12 )
if [[ -n "${OBSERVATORIO_BASIC_AUTH_CREDENTIALS}" ]]; then
  curl_args+=( -u "${OBSERVATORIO_BASIC_AUTH_CREDENTIALS}" )
fi
if [[ "${OBSERVATORIO_TLS_INSECURE}" == "true" ]]; then
  curl_args+=( -k )
fi

check_url() {
  local label="$1"
  local url="$2"
  local needle="${3:-}"

  echo "[public] ${label}: ${url}"
  if ! body="$(curl "${curl_args[@]}" "${url}")"; then
    echo "[public] ERROR: ${label} sin respuesta"
    return 1
  fi

  if [[ -n "${needle}" ]] && ! grep -Eqi "${needle}" <<<"${body}"; then
    echo "[public] ERROR: ${label} respondió, pero no contiene '${needle}'"
    return 1
  fi

  echo "[public] OK: ${label}"
}

check_url "Dashboard" "${OBSERVATORIO_DASHBOARD_URL%/}/_stcore/health" "ok"
check_url "DSpace UI" "${OBSERVATORIO_DSPACE_UI_URL}"
check_url "DSpace REST" "${OBSERVATORIO_DSPACE_API_URL}" "_links"
check_url "CKAN UI" "${OBSERVATORIO_CKAN_URL}"
check_url "CKAN Action API" "${OBSERVATORIO_CKAN_API_URL}" "success"

echo "[public] observatorio 3 en 1 publicado y accesible por URL"
