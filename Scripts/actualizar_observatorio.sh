#!/usr/bin/env bash
# =============================================================
#  actualizar_observatorio.sh
#  Orquestador Paso 1: genera stats + compila PDF del observatorio.
#
#  Uso rápido (solo stats + PDF, sin fetch de APIs):
#      bash Scripts/actualizar_observatorio.sh
#
#  Uso completo (fetch + stats + PDF):
#      bash Scripts/actualizar_observatorio.sh --full
# =============================================================

set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON="${REPO}/.venv/bin/python"
TEX_DIR="${REPO}/Docs/reports"
TEX_FILE="${TEX_DIR}/observatorio_cchen_documentacion.tex"
PDF_FILE="${TEX_DIR}/observatorio_cchen_documentacion.pdf"
LOG="${TEX_DIR}/lualatex.log"
FULL_MODE=false

# ---- Colores de terminal ------------------------------------
GREEN="\033[0;32m"; YELLOW="\033[1;33m"; RED="\033[0;31m"; NC="\033[0m"
ok()   { echo -e "${GREEN}✓${NC} $*"; }
info() { echo -e "${YELLOW}→${NC} $*"; }
fail() { echo -e "${RED}✗${NC} $*" >&2; exit 1; }

# ---- Argumentos ---------------------------------------------
for arg in "$@"; do
  [[ "$arg" == "--full" ]] && FULL_MODE=true
done

echo "=============================================="
echo "  Observatorio CCHEN 360° — Actualización"
echo "  $(date '+%Y-%m-%d %H:%M')"
echo "=============================================="
cd "$REPO"

# ---- 1. Fetch de fuentes externas (solo --full) -------------
if $FULL_MODE; then
  info "Fetch Semantic Scholar..."
  "$PYTHON" Scripts/fetch_semantic_scholar.py && ok "Semantic Scholar" || echo "  [WARN] fetch_semantic_scholar falló, continuando"

  info "Fetch EuropePMC..."
  "$PYTHON" Scripts/fetch_europmc.py && ok "EuropePMC" || echo "  [WARN] fetch_europmc falló, continuando"

  info "Fetch OpenAIRE..."
  "$PYTHON" Scripts/fetch_openaire_outputs.py && ok "OpenAIRE" || echo "  [WARN] fetch_openaire falló, continuando"

  info "Rebuild embeddings..."
  "$PYTHON" Scripts/build_embeddings.py && ok "Embeddings" || echo "  [WARN] build_embeddings falló, continuando"
else
  info "Modo rápido (sin fetch). Usa --full para actualizar fuentes externas."
fi

# ---- 2. Generar auto_stats.tex ------------------------------
info "Generando auto_stats.tex desde CSVs locales..."
"$PYTHON" Scripts/generar_stats_latex.py || fail "generar_stats_latex.py falló"
ok "auto_stats.tex generado en Docs/reports/"

# ---- 3. Compilar PDF con LuaLaTeX --------------------------
info "Compilando PDF (LuaLaTeX, 2 pasadas)..."
cd "$TEX_DIR"

lualatex -interaction=nonstopmode -halt-on-error \
  "$(basename "$TEX_FILE")" > "$LOG" 2>&1 || {
  echo ""
  echo "  Últimas líneas del log:"
  tail -20 "$LOG"
  fail "LuaLaTeX falló en la primera pasada. Ver: $LOG"
}

# Segunda pasada para referencias/TOC
lualatex -interaction=nonstopmode -halt-on-error \
  "$(basename "$TEX_FILE")" >> "$LOG" 2>&1 || {
  fail "LuaLaTeX falló en la segunda pasada. Ver: $LOG"
}

cd "$REPO"

# ---- 4. Resultado -------------------------------------------
if [[ -f "$PDF_FILE" ]]; then
  SIZE=$(du -sh "$PDF_FILE" | cut -f1)
  ok "PDF generado: ${PDF_FILE/$REPO\//} ($SIZE)"
else
  fail "PDF no encontrado después de la compilación."
fi

echo ""
echo "=============================================="
echo "  Listo. $(date '+%Y-%m-%d %H:%M')"
echo "=============================================="
