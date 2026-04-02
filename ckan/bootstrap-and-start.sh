#!/bin/sh
# Bootstrap operativo de CKAN:
# 1. espera PostgreSQL y Solr
# 2. asegura secretos locales
# 3. inicializa/actualiza schema principal y datastore
# 4. crea sysadmin opcional
# 5. arranca uWSGI
set -eu

CKAN_INI="${CKAN_INI:-/srv/app/ckan.ini}"
CKAN_SQLALCHEMY_URL="${CKAN_SQLALCHEMY_URL:-}"
CKAN_DATASTORE_WRITE_URL="${CKAN_DATASTORE_WRITE_URL:-}"
CKAN_SOLR_URL="${CKAN_SOLR_URL:-http://ckan-solr:8983/solr/ckan}"
MAX_ATTEMPTS="${BOOTSTRAP_MAX_ATTEMPTS:-60}"
SLEEP_SECONDS="${BOOTSTRAP_SLEEP_SECONDS:-5}"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

ensure_config() {
  if [ ! -f "$CKAN_INI" ]; then
    log "Generating CKAN config at $CKAN_INI"
    ckan generate config "$CKAN_INI"
  fi
}

wait_for_postgres() {
  if [ -z "$CKAN_SQLALCHEMY_URL" ]; then
    log "CKAN_SQLALCHEMY_URL is not set"
    exit 1
  fi

  attempt=1
  until pg_isready -d "$CKAN_SQLALCHEMY_URL" >/dev/null 2>&1; do
    log "Waiting for PostgreSQL (attempt $attempt/$MAX_ATTEMPTS)..."
    if [ "$attempt" -ge "$MAX_ATTEMPTS" ]; then
      log "PostgreSQL did not become ready"
      exit 1
    fi
    attempt=$((attempt + 1))
    sleep "$SLEEP_SECONDS"
  done
}

wait_for_solr_schema() {
  attempt=1
  while true; do
    response="$(curl -fsS "$CKAN_SOLR_URL/schema/name?wt=json" 2>/dev/null || true)"
    if printf '%s' "$response" | grep -q 'ckan'; then
      return
    fi

    log "Waiting for CKAN Solr schema at $CKAN_SOLR_URL (attempt $attempt/$MAX_ATTEMPTS)..."
    if [ "$attempt" -ge "$MAX_ATTEMPTS" ]; then
      log "CKAN Solr schema not ready"
      exit 1
    fi
    attempt=$((attempt + 1))
    sleep "$SLEEP_SECONDS"
  done
}

init_db() {
  log "Initializing or upgrading CKAN database"
  gosu ckan ckan -c "$CKAN_INI" db init
}

init_datastore() {
  if [ -z "$CKAN_DATASTORE_WRITE_URL" ]; then
    log "CKAN_DATASTORE_WRITE_URL is not set; skipping datastore bootstrap"
    return
  fi

  log "Applying datastore permissions"
  gosu ckan ckan -c "$CKAN_INI" datastore set-permissions | psql "$CKAN_DATASTORE_WRITE_URL" >/dev/null
}

create_sysadmin() {
  if [ -z "${CKAN_SYSADMIN_NAME:-}" ] || [ -z "${CKAN_SYSADMIN_EMAIL:-}" ] || [ -z "${CKAN_SYSADMIN_PASSWORD:-}" ]; then
    log "CKAN sysadmin variables are incomplete; skipping sysadmin bootstrap"
    return
  fi

  user_output="$(gosu ckan ckan -c "$CKAN_INI" user show "$CKAN_SYSADMIN_NAME" 2>/dev/null || true)"
  if printf '%s' "$user_output" | grep -qv 'User: None'; then
    log "CKAN sysadmin '$CKAN_SYSADMIN_NAME' already exists"
    return
  fi

  log "Creating CKAN sysadmin '$CKAN_SYSADMIN_NAME'"
  gosu ckan ckan -c "$CKAN_INI" user add "$CKAN_SYSADMIN_NAME" \
    "email=$CKAN_SYSADMIN_EMAIL" \
    "password=$CKAN_SYSADMIN_PASSWORD"
  gosu ckan ckan -c "$CKAN_INI" sysadmin add "$CKAN_SYSADMIN_NAME"
}

ensure_config
chown -R ckan:ckan /var/lib/ckan

wait_for_postgres
wait_for_solr_schema
init_db
init_datastore
create_sysadmin

log "Starting CKAN application"
exec gosu ckan "$@"
