#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN=".venv/bin/python"
HEAD_SOURCE="Docs/reports/assistant_eval_structured_responses_v2.csv"
PENDING_INPUT="Docs/reports/assistant_eval_template_pending_q03_q10.csv"
V1_BASELINE="Docs/reports/assistant_eval_structured_responses_v1.csv"
RESUMEN_TEMPLATE="Docs/reports/resumen_cierre_v2_template.md"
RUNBOOK="Docs/reports/runbook_cierre_v2_2026-03-24.md"

STATUS_DIR="Docs/reports"
RUN_ID="$(date +"%Y-%m-%d_%H%M%S")"
STATUS_FILE="$STATUS_DIR/preflight_cierre_v2_${RUN_ID}.json"

usage() {
  cat <<'EOF'
Uso:
  bash Scripts/preflight_cierre_v2.sh [opciones]

Opciones:
  --python-bin PATH         Binario python a usar (default: .venv/bin/python)
  --head-source PATH        CSV base de head Q01-Q02
  --pending-input PATH      Input de pendientes Q03-Q10
  --v1-baseline PATH        Baseline v1 structured
  --resumen-template PATH   Plantilla resumen ejecutivo
  --runbook PATH            Runbook operativo
  --help                    Mostrar ayuda

Qué valida (sin gastar tokens Groq):
  1) Existencia de scripts y archivos de entrada.
  2) Que python esté disponible y ejecute.
  3) Sintaxis de scripts Python y shell.
  4) Ayuda de scripts clave para detectar argumentos rotos.
  5) Que el template pendiente contenga Q03..Q10.
  6) Escribe un JSON de estado en Docs/reports/preflight_cierre_v2_<timestamp>.json
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --python-bin) PYTHON_BIN="$2"; shift 2 ;;
    --head-source) HEAD_SOURCE="$2"; shift 2 ;;
    --pending-input) PENDING_INPUT="$2"; shift 2 ;;
    --v1-baseline) V1_BASELINE="$2"; shift 2 ;;
    --resumen-template) RESUMEN_TEMPLATE="$2"; shift 2 ;;
    --runbook) RUNBOOK="$2"; shift 2 ;;
    --help|-h) usage; exit 0 ;;
    *)
      echo "[ERROR] Opción desconocida: $1" >&2
      usage
      exit 1
      ;;
  esac
done

mkdir -p "$STATUS_DIR"

fail() {
  local msg="$1"
  echo "[FAIL] $msg" >&2
  cat > "$STATUS_FILE" <<JSON
{
  "status": "fail",
  "error": $(printf '%s' "$msg" | $PYTHON_BIN -c 'import json,sys; print(json.dumps(sys.stdin.read()))' 2>/dev/null || printf '"%s"' "$msg"),
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
}
JSON
  echo "[saved] $STATUS_FILE"
  exit 1
}

ok_check() {
  echo "[OK] $1"
}

# 1) Archivos y scripts requeridos
required_files=(
  "$HEAD_SOURCE"
  "$PENDING_INPUT"
  "$V1_BASELINE"
  "$RESUMEN_TEMPLATE"
  "$RUNBOOK"
  "Scripts/cerrar_v2_structured.sh"
  "Scripts/merge_structured_eval_runs.py"
  "Scripts/compare_eval_runs.py"
  "Scripts/generar_resumen_cierre_v2.py"
  "Scripts/assistant_eval_structured_responses.py"
)

for f in "${required_files[@]}"; do
  [[ -f "$f" ]] || fail "No existe requerido: $f"
done
ok_check "Archivos requeridos presentes"

# 2) Python disponible
[[ -x "$PYTHON_BIN" ]] || fail "Python no ejecutable: $PYTHON_BIN"
"$PYTHON_BIN" -V >/dev/null 2>&1 || fail "Python no responde: $PYTHON_BIN"
ok_check "Python disponible ($PYTHON_BIN)"

# 3) Sintaxis scripts
"$PYTHON_BIN" -m py_compile \
  Scripts/assistant_eval_structured_responses.py \
  Scripts/merge_structured_eval_runs.py \
  Scripts/compare_eval_runs.py \
  Scripts/generar_resumen_cierre_v2.py \
  Scripts/ejecutar_cierre_v2_job.py >/dev/null 2>&1 || fail "py_compile falló en scripts Python"

bash -n Scripts/cerrar_v2_structured.sh || fail "bash -n falló en cerrar_v2_structured.sh"
bash -n Scripts/programar_cierre_v2.sh || fail "bash -n falló en programar_cierre_v2.sh"
ok_check "Sintaxis de scripts validada"

# 4) Ayuda scripts clave
"$PYTHON_BIN" Scripts/merge_structured_eval_runs.py --help >/dev/null 2>&1 || fail "--help falló en merge_structured_eval_runs.py"
"$PYTHON_BIN" Scripts/compare_eval_runs.py --help >/dev/null 2>&1 || fail "--help falló en compare_eval_runs.py"
"$PYTHON_BIN" Scripts/generar_resumen_cierre_v2.py --help >/dev/null 2>&1 || fail "--help falló en generar_resumen_cierre_v2.py"
"$PYTHON_BIN" Scripts/assistant_eval_structured_responses.py --help >/dev/null 2>&1 || fail "--help falló en assistant_eval_structured_responses.py"
bash Scripts/cerrar_v2_structured.sh --help >/dev/null 2>&1 || fail "--help falló en cerrar_v2_structured.sh"
ok_check "Ayuda de scripts clave validada"

# 5) Validar template pendiente contiene Q03..Q10
_qid_tmp="$(mktemp)"
awk -F, 'NR>1{print $1}' "$PENDING_INPUT" | tr -d '\r' | sort -u > "$_qid_tmp"
missing_qids="$($PYTHON_BIN - "$_qid_tmp" <<'PY'
import pathlib
import sys

expected = {"Q03", "Q04", "Q05", "Q06", "Q07", "Q08", "Q09", "Q10"}
qid_path = pathlib.Path(sys.argv[1])
found = {line.strip() for line in qid_path.read_text(encoding="utf-8", errors="replace").splitlines() if line.strip()}
missing = sorted(expected - found)
print(",".join(missing))
PY
)"
rm -f "$_qid_tmp"

if [[ -n "$missing_qids" ]]; then
  fail "El input pendiente no contiene todas las queries esperadas: $missing_qids"
fi
ok_check "Template pendiente contiene Q03..Q10"

# 6) JSON de estado
cat > "$STATUS_FILE" <<JSON
{
  "status": "ok",
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "python_bin": "$PYTHON_BIN",
  "head_source": "$HEAD_SOURCE",
  "pending_input": "$PENDING_INPUT",
  "v1_baseline": "$V1_BASELINE",
  "resumen_template": "$RESUMEN_TEMPLATE",
  "runbook": "$RUNBOOK",
  "checks": [
    "required_files",
    "python_available",
    "script_syntax",
    "script_help",
    "pending_queries_q03_q10"
  ]
}
JSON

ok_check "Preflight completado"
echo "[saved] $STATUS_FILE"
