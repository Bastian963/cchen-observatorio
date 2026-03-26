#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN=".venv/bin/python"
INPUT="Docs/reports/assistant_eval_template.csv"
TOP_K="5"
RUN_LABEL="publication_rag_sanity_$(date +"%Y%m%d_%H%M%S")"
OUTPUT=""
COMPARE_WITH=""
COMPARE_OUTPUT=""
QUIET="0"
JSON_OUTPUT="0"

usage() {
  cat <<'EOF'
Uso:
  bash Scripts/run_publication_rag_sanity.sh [opciones]

Opciones:
  --input PATH            CSV de prompts (default: Docs/reports/assistant_eval_template.csv)
  --top-k N               Top-k retrieval (default: 5)
  --run-label TXT         Etiqueta de corrida (default: publication_rag_sanity_<timestamp>)
  --output PATH           CSV de salida de la corrida (default: auto en Docs/reports)
  --compare-with PATH     CSV previo para comparar
  --compare-output PATH   CSV de comparación (default: auto en Docs/reports)
  --quiet, -q             Salida mínima (útil para CI)
  --json                  Salida JSON estructurada (implica --quiet)
  --python-bin PATH       Binario python (default: .venv/bin/python)
  --help                  Mostrar ayuda

Notas:
  - Ejecuta assistant_eval_batch.py filtrando con --mode publication_rag.
  - No consume tokens Groq (evalúa retrieval RAG local).
EOF
}

log() {
  if [[ "$QUIET" != "1" ]]; then
    echo "$@"
  fi
}

emit_json() {
  local status="$1"
  local rows="$2"
  local retrieval_ms_mean="$3"
  local keyword_hits_total="$4"
  local output_path="$5"
  local compare_path="$6"
  local run_label="$7"
  "$PYTHON_BIN" - "$status" "$rows" "$retrieval_ms_mean" "$keyword_hits_total" "$output_path" "$compare_path" "$run_label" <<'PY'
import json
import sys

status, rows, retrieval_ms_mean, keyword_hits_total, output_path, compare_path, run_label = sys.argv[1:8]
payload = {
    "status": status,
    "run_label": run_label,
    "rows": int(rows) if rows.isdigit() else rows,
    "retrieval_ms_mean": None if retrieval_ms_mean in {"", "N/A"} else float(retrieval_ms_mean),
    "keyword_hits_total": None if keyword_hits_total in {"", "N/A"} else int(keyword_hits_total),
    "output": output_path,
    "compare": compare_path if compare_path else None,
}
print(json.dumps(payload, ensure_ascii=False))
PY
}

fail() {
  local message="$1"
  if [[ "$JSON_OUTPUT" == "1" ]]; then
    "$PYTHON_BIN" - "$message" "$RUN_LABEL" <<'PY'
import json
import sys

message, run_label = sys.argv[1:3]
print(json.dumps({"status": "error", "run_label": run_label, "message": message}, ensure_ascii=False))
PY
  else
    echo "[ERROR] $message" >&2
  fi
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --input) INPUT="$2"; shift 2 ;;
    --top-k) TOP_K="$2"; shift 2 ;;
    --run-label) RUN_LABEL="$2"; shift 2 ;;
    --output) OUTPUT="$2"; shift 2 ;;
    --compare-with) COMPARE_WITH="$2"; shift 2 ;;
    --compare-output) COMPARE_OUTPUT="$2"; shift 2 ;;
    --quiet|-q) QUIET="1"; shift 1 ;;
    --json) JSON_OUTPUT="1"; QUIET="1"; shift 1 ;;
    --python-bin) PYTHON_BIN="$2"; shift 2 ;;
    --help|-h) usage; exit 0 ;;
    *)
      echo "[ERROR] Opción desconocida: $1" >&2
      usage
      exit 1
      ;;
  esac
done

[[ -x "$PYTHON_BIN" ]] || fail "Python no ejecutable: $PYTHON_BIN"
[[ -f "$INPUT" ]] || fail "Input no encontrado: $INPUT"
if [[ -n "$COMPARE_WITH" && ! -f "$COMPARE_WITH" ]]; then
  fail "compare-with no encontrado: $COMPARE_WITH"
fi

if [[ -z "$OUTPUT" ]]; then
  OUTPUT="Docs/reports/assistant_eval_run_${RUN_LABEL}.csv"
fi
if [[ -n "$COMPARE_WITH" && -z "$COMPARE_OUTPUT" ]]; then
  COMPARE_OUTPUT="Docs/reports/assistant_eval_compare_${RUN_LABEL}.csv"
fi

# Keep CLI output clean from known third-party warning noise.
export PYTHONWARNINGS="${PYTHONWARNINGS:-ignore:urllib3 v2 only supports OpenSSL 1.1.1+:Warning,ignore:Python versions below 3.10 are deprecated:DeprecationWarning,ignore:The 'timeout' parameter is deprecated:DeprecationWarning,ignore:The 'verify' parameter is deprecated:DeprecationWarning}"

cmd=("$PYTHON_BIN" Scripts/assistant_eval_batch.py --input "$INPUT" --mode publication_rag --top-k "$TOP_K" --run-label "$RUN_LABEL" --output "$OUTPUT")
if [[ -n "$COMPARE_WITH" ]]; then
  cmd+=(--compare-with "$COMPARE_WITH")
fi
if [[ -n "$COMPARE_OUTPUT" ]]; then
  cmd+=(--compare-output "$COMPARE_OUTPUT")
fi

log "[run] ${cmd[*]}"
if [[ "$QUIET" == "1" ]]; then
  _tmp_log="$(mktemp)"
  if ! "${cmd[@]}" >"$_tmp_log" 2>&1; then
    cat "$_tmp_log" >&2
    rm -f "$_tmp_log"
    fail "assistant_eval_batch execution failed"
  fi
  rm -f "$_tmp_log"
else
  "${cmd[@]}" || fail "assistant_eval_batch execution failed"
fi

if [[ "$QUIET" == "1" ]]; then
summary_output="$($PYTHON_BIN - "$OUTPUT" <<'PY'
import pandas as pd
import sys

path = sys.argv[1]
df = pd.read_csv(path).fillna("")
rows = len(df)
ms = pd.to_numeric(df.get("retrieval_ms"), errors="coerce")
hits = pd.to_numeric(df.get("keyword_hits"), errors="coerce")
ms_value = f"{ms.mean():.2f}" if ms.notna().any() else "N/A"
hits_value = str(int(hits.sum())) if hits.notna().any() else "N/A"
print(f"rows={rows} retrieval_ms_mean={ms_value} keyword_hits_total={hits_value}")
PY
)"
  rows_value="$(echo "$summary_output" | awk '{for(i=1;i<=NF;i++){if($i ~ /^rows=/){sub(/^rows=/,"",$i); print $i; break}}}')"
  ms_value="$(echo "$summary_output" | awk '{for(i=1;i<=NF;i++){if($i ~ /^retrieval_ms_mean=/){sub(/^retrieval_ms_mean=/,"",$i); print $i; break}}}')"
  hits_value="$(echo "$summary_output" | awk '{for(i=1;i<=NF;i++){if($i ~ /^keyword_hits_total=/){sub(/^keyword_hits_total=/,"",$i); print $i; break}}}')"
  if [[ "$JSON_OUTPUT" == "1" ]]; then
    emit_json "ok" "$rows_value" "$ms_value" "$hits_value" "$OUTPUT" "$COMPARE_OUTPUT" "$RUN_LABEL"
  else
    echo "[OK] $summary_output output=$OUTPUT${COMPARE_OUTPUT:+ compare=$COMPARE_OUTPUT}"
  fi
else
summary_output="$($PYTHON_BIN - "$OUTPUT" <<'PY'
import pandas as pd
import sys

path = sys.argv[1]
df = pd.read_csv(path).fillna("")
rows = len(df)
ms = pd.to_numeric(df.get("retrieval_ms"), errors="coerce")
hits = pd.to_numeric(df.get("keyword_hits"), errors="coerce")
print(f"rows: {rows}")
print(f"retrieval_ms_mean: {ms.mean():.2f}" if ms.notna().any() else "retrieval_ms_mean: N/A")
print(f"keyword_hits_total: {int(hits.sum())}" if hits.notna().any() else "keyword_hits_total: N/A")
PY
)"
  echo "[summary] $OUTPUT"
  while IFS= read -r line; do
    echo "  $line"
  done <<< "$summary_output"
fi

if [[ -n "$COMPARE_OUTPUT" ]]; then
  log "[summary] compare: $COMPARE_OUTPUT"
fi

log "[OK] publication_rag sanity finalizado"
