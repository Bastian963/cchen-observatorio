#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

run_python311_script() {
  local script_path="$1"
  shift || true

  if command -v uv >/dev/null 2>&1; then
    uv run --python 3.11 --with-requirements "$ROOT_DIR/requirements.txt" python "$script_path" "$@"
    return
  fi

  local py_major py_minor
  py_major="$(python3 -c 'import sys; print(sys.version_info.major)')"
  py_minor="$(python3 -c 'import sys; print(sys.version_info.minor)')"
  if [[ "$py_major" -gt 3 || ( "$py_major" -eq 3 && "$py_minor" -ge 11 ) ]]; then
    python3 "$script_path" "$@"
    return
  fi

  echo "[public-beta-release] ERROR: se requiere Python 3.11+ o uv para ejecutar $script_path"
  exit 1
}

echo "[public-beta-release] validando smoke local del dashboard..."
OBSERVATORIO_DATA_SOURCE=local python3 "$ROOT_DIR/Scripts/check_dashboard_smoke.py"

echo "[public-beta-release] validando overlay publico..."
bash "$ROOT_DIR/Scripts/check_observatorio_public_overlay.sh"

echo "[public-beta-release] validando modo publico del dashboard..."
run_python311_script "$ROOT_DIR/Scripts/check_dashboard_public_mode.py"

echo "[public-beta-release] OK: gate de beta publica del portal 3 en 1 en verde"
