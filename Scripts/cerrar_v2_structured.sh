#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

HEAD_SOURCE="Docs/reports/assistant_eval_structured_responses_v2.csv"
HEAD_FILE="Docs/reports/assistant_eval_structured_responses_v2_q01_q02.csv"
PENDING_INPUT="Docs/reports/assistant_eval_template_pending_q03_q10.csv"
PENDING_OUTPUT="Docs/reports/assistant_eval_structured_responses_v2_pending.csv"
FINAL_OUTPUT="Docs/reports/assistant_eval_structured_responses_v2_final.csv"
COMPARE_OUTPUT="Docs/reports/assistant_eval_compare_structured_v2_final_vs_v1.csv"
RESUMEN_TEMPLATE="Docs/reports/resumen_cierre_v2_template.md"
RESUMEN_OUTPUT="Docs/reports/resumen_cierre_v2.md"
RESUMEN_RESPONSABLE="Bastián Ayala"
V1_BASELINE="Docs/reports/assistant_eval_structured_responses_v1.csv"
RUN_LABEL_PENDING="structured_responses_v2_pending"
RUN_LABEL_FINAL="structured_responses_v2_final"
GROQ_MODEL="llama-3.3-70b-versatile"
MAX_TOKENS="2048"
PYTHON_BIN=".venv/bin/python"

usage() {
  cat <<'EOF'
Uso:
  GROQ_API_KEY="gsk_..." Scripts/cerrar_v2_structured.sh [opciones]

Opciones:
  --head-source PATH        CSV base para extraer Q01-Q02 (default: assistant_eval_structured_responses_v2.csv)
  --head-file PATH          CSV de salida con Q01-Q02 (default: assistant_eval_structured_responses_v2_q01_q02.csv)
  --pending-input PATH      Input de queries pendientes (default: assistant_eval_template_pending_q03_q10.csv)
  --pending-output PATH     Salida del rerun pendiente (default: assistant_eval_structured_responses_v2_pending.csv)
  --final-output PATH       Salida del merge final (default: assistant_eval_structured_responses_v2_final.csv)
  --compare-output PATH     Salida comparación v1 vs v2 final (default: assistant_eval_compare_structured_v2_final_vs_v1.csv)
  --resumen-template PATH   Plantilla de resumen ejecutivo (default: resumen_cierre_v2_template.md)
  --resumen-output PATH     Salida resumen ejecutivo generado (default: resumen_cierre_v2.md)
  --resumen-responsable TXT Responsable del resumen ejecutivo (default: Bastián Ayala)
  --v1-baseline PATH        CSV baseline v1 structured (default: assistant_eval_structured_responses_v1.csv)
  --run-label-pending TXT   run_label del rerun pendiente (default: structured_responses_v2_pending)
  --run-label-final TXT     run_label del merge final (default: structured_responses_v2_final)
  --groq-model TXT          modelo Groq (default: llama-3.3-70b-versatile)
  --max-tokens N            max_tokens por respuesta (default: 2048)
  --python-bin PATH         binario python (default: .venv/bin/python)
  --help                    mostrar ayuda

Flujo que ejecuta:
  1) Genera head Q01-Q02 desde --head-source
  2) Ejecuta structured_responses para Q03-Q10
  3) Hace merge final con strict-complete
  4) Compara v1 vs v2 final
  5) Genera resumen ejecutivo automático
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --head-source) HEAD_SOURCE="$2"; shift 2 ;;
    --head-file) HEAD_FILE="$2"; shift 2 ;;
    --pending-input) PENDING_INPUT="$2"; shift 2 ;;
    --pending-output) PENDING_OUTPUT="$2"; shift 2 ;;
    --final-output) FINAL_OUTPUT="$2"; shift 2 ;;
    --compare-output) COMPARE_OUTPUT="$2"; shift 2 ;;
    --resumen-template) RESUMEN_TEMPLATE="$2"; shift 2 ;;
    --resumen-output) RESUMEN_OUTPUT="$2"; shift 2 ;;
    --resumen-responsable) RESUMEN_RESPONSABLE="$2"; shift 2 ;;
    --v1-baseline) V1_BASELINE="$2"; shift 2 ;;
    --run-label-pending) RUN_LABEL_PENDING="$2"; shift 2 ;;
    --run-label-final) RUN_LABEL_FINAL="$2"; shift 2 ;;
    --groq-model) GROQ_MODEL="$2"; shift 2 ;;
    --max-tokens) MAX_TOKENS="$2"; shift 2 ;;
    --python-bin) PYTHON_BIN="$2"; shift 2 ;;
    --help|-h) usage; exit 0 ;;
    *)
      echo "[ERROR] Opción desconocida: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ -z "${GROQ_API_KEY:-}" ]]; then
  echo "[ERROR] Debes exportar GROQ_API_KEY antes de ejecutar este script." >&2
  exit 1
fi

for path in "$HEAD_SOURCE" "$PENDING_INPUT" "$V1_BASELINE" "$RESUMEN_TEMPLATE"; do
  if [[ ! -f "$path" ]]; then
    echo "[ERROR] Archivo no encontrado: $path" >&2
    exit 1
  fi
done

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "[ERROR] Python no ejecutable: $PYTHON_BIN" >&2
  exit 1
fi

echo "[1/5] Generando head Q01-Q02 desde $HEAD_SOURCE"
awk -F, 'NR==1 || $1=="Q01" || $1=="Q02"' "$HEAD_SOURCE" > "$HEAD_FILE"

echo "[2/5] Ejecutando rerun pendiente (Q03-Q10)"
"$PYTHON_BIN" Scripts/assistant_eval_structured_responses.py \
  --input "$PENDING_INPUT" \
  --run-label "$RUN_LABEL_PENDING" \
  --output "$PENDING_OUTPUT" \
  --groq-model "$GROQ_MODEL" \
  --max-tokens "$MAX_TOKENS"

echo "[3/5] Consolidando merge final"
"$PYTHON_BIN" Scripts/merge_structured_eval_runs.py \
  --head "$HEAD_FILE" \
  --tail "$PENDING_OUTPUT" \
  --template "$V1_BASELINE" \
  --run-label "$RUN_LABEL_FINAL" \
  --output "$FINAL_OUTPUT" \
  --strict-complete

echo "[4/5] Comparando v1 vs v2 final"
"$PYTHON_BIN" Scripts/compare_eval_runs.py \
  --v1 "$V1_BASELINE" \
  --v2 "$FINAL_OUTPUT" \
  --output "$COMPARE_OUTPUT"

echo "[5/5] Generando resumen ejecutivo"
"$PYTHON_BIN" Scripts/generar_resumen_cierre_v2.py \
  --compare "$COMPARE_OUTPUT" \
  --template "$RESUMEN_TEMPLATE" \
  --output "$RESUMEN_OUTPUT" \
  --responsable "$RESUMEN_RESPONSABLE"

echo
echo "[OK] Cierre v2 completado"
echo "  final:   $FINAL_OUTPUT"
echo "  compare: $COMPARE_OUTPUT"
echo "  resumen: $RESUMEN_OUTPUT"
