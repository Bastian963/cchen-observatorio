#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-$ROOT_DIR/.venv/bin/python}"
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8501}"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "[ERROR] No se encontro Python ejecutable en: $PYTHON_BIN"
  echo "        Configura PYTHON_BIN o crea el entorno en .venv"
  exit 1
fi

export CCHEN_DATA_ROOT="${CCHEN_DATA_ROOT:-$ROOT_DIR/Data}"
export STREAMLIT_SERVER_HEADLESS=true
export STREAMLIT_SERVER_ADDRESS="$HOST"
export STREAMLIT_SERVER_PORT="$PORT"
export STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

echo "[INFO] Iniciando dashboard CCHEN en modo headless"
echo "[INFO] URL: http://$HOST:$PORT"
echo "[INFO] Data root: $CCHEN_DATA_ROOT"

cd "$ROOT_DIR/Dashboard"
exec "$PYTHON_BIN" -m streamlit run app.py \
  --server.address "$HOST" \
  --server.port "$PORT"
