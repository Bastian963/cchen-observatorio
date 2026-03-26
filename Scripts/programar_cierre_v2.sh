#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

RUN_ID="${1:-$(date +"%Y-%m-%d_%H%M%S")}" 
LOG_DIR="Docs/reports"
OUT_LOG="$LOG_DIR/cierre_v2_scheduler_${RUN_ID}.out"
PID_FILE="$LOG_DIR/cierre_v2_scheduler_${RUN_ID}.pid"

mkdir -p "$LOG_DIR"

if [[ -z "${GROQ_API_KEY:-}" ]]; then
  echo "[ERROR] Debes exportar GROQ_API_KEY antes de programar la corrida." >&2
  exit 1
fi

nohup .venv/bin/python Scripts/ejecutar_cierre_v2_job.py --run-id "$RUN_ID" --log-dir "$LOG_DIR" > "$OUT_LOG" 2>&1 &
PID=$!

echo "$PID" > "$PID_FILE"

echo "[OK] Corrida programada"
echo "  run_id:   $RUN_ID"
echo "  pid:      $PID"
echo "  pid_file: $PID_FILE"
echo "  out_log:  $OUT_LOG"
