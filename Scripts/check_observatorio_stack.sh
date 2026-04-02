#!/usr/bin/env bash
set -euo pipefail

DASHBOARD_HEALTH_URL="${DASHBOARD_HEALTH_URL:-http://localhost:8501/_stcore/health}"
DSPACE_UI_URL="${DSPACE_UI_URL:-http://localhost:4000}"
DSPACE_API_URL="${DSPACE_API_URL:-http://localhost:8080/server/api}"
CKAN_UI_URL="${CKAN_UI_URL:-http://localhost:5001}"
CKAN_API_URL="${CKAN_API_URL:-http://localhost:5001/api/3/action/status_show}"
DSPACE_SOLR_URL="${DSPACE_SOLR_URL:-http://localhost:8983/solr/search/admin/ping?wt=json}"
CKAN_SOLR_URL="${CKAN_SOLR_URL:-http://localhost:8984/solr/ckan/admin/ping?wt=json}"

check_url() {
  local label="$1"
  local url="$2"
  local needle="${3:-}"

  echo "[stack] ${label}: ${url}"
  if ! body="$(curl -fsS --max-time 8 "${url}")"; then
    echo "[stack] ERROR: ${label} sin respuesta"
    return 1
  fi

  if [[ -n "${needle}" ]] && ! grep -Eqi "${needle}" <<<"${body}"; then
    echo "[stack] ERROR: ${label} respondió, pero no contiene '${needle}'"
    return 1
  fi

  echo "[stack] OK: ${label}"
}

check_url "Dashboard" "${DASHBOARD_HEALTH_URL}" "ok"
check_url "DSpace UI" "${DSPACE_UI_URL}"
check_url "DSpace REST" "${DSPACE_API_URL}" "_links"
check_url "CKAN UI" "${CKAN_UI_URL}"
check_url "CKAN Action API" "${CKAN_API_URL}" "success"
check_url "Solr DSpace" "${DSPACE_SOLR_URL}" "\"status\"[[:space:]]*:[[:space:]]*\"OK\""
check_url "Solr CKAN" "${CKAN_SOLR_URL}" "\"status\"[[:space:]]*:[[:space:]]*\"OK\""

echo "[stack] observatorio 3 en 1 operativo"
