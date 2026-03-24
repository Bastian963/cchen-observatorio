#!/usr/bin/env python3
"""
Copia los boletines generados a docs/boletines/ y actualiza docs/index.html.

Uso (desde la raíz del repositorio):
    python3 Scripts/build_boletines_index.py
"""
from __future__ import annotations
import json
import re
import shutil
from pathlib import Path

ROOT        = Path(__file__).resolve().parents[1]
SRC_DIR     = ROOT / "Data" / "Boletines"
DOCS_DIR    = ROOT / "Docs" / "boletines"
INDEX_TMPL  = ROOT / "Docs" / "index.html"

DOCS_DIR.mkdir(parents=True, exist_ok=True)


def _semana_label(stem: str) -> str:
    """'boletin_2026-S13' → 'Semana 13 · 2026'"""
    m = re.search(r"(\d{4})-S(\d+)", stem)
    if m:
        return f"Semana {int(m.group(2))} · {m.group(1)}"
    return stem


def main() -> None:
    # 1. Copiar boletines al directorio docs/boletines/
    html_files = sorted(SRC_DIR.glob("boletin_*.html"), reverse=True)
    if not html_files:
        print("No hay boletines en Data/Boletines/ — nada que publicar.")
        return

    copied = []
    for src in html_files:
        dst = DOCS_DIR / src.name
        shutil.copy2(src, dst)
        copied.append(dst)
        print(f"  Copiado: {src.name} → docs/boletines/")

    # 2. Construir lista JSON para el index.html
    entries = []
    for f in sorted(copied, reverse=True):
        entries.append({
            "url":    f"boletines/{f.name}",
            "label":  _semana_label(f.stem),
            "semana": _semana_label(f.stem),
        })

    # 3. Actualizar docs/index.html reemplazando el placeholder
    if INDEX_TMPL.exists():
        html = INDEX_TMPL.read_text(encoding="utf-8")
        html = re.sub(
            r"const boletines = BOLETINES_JSON_PLACEHOLDER;",
            f"const boletines = {json.dumps(entries, ensure_ascii=False)};",
            html,
        )
        # Si ya fue reemplazado antes, actualizar el array
        html = re.sub(
            r"const boletines = \[.*?\];",
            f"const boletines = {json.dumps(entries, ensure_ascii=False)};",
            html,
            flags=re.DOTALL,
        )
        INDEX_TMPL.write_text(html, encoding="utf-8")
        print(f"  Índice actualizado: {len(entries)} boletín(es) listado(s).")
    else:
        print("  AVISO: docs/index.html no encontrado, omitiendo actualización del índice.")


if __name__ == "__main__":
    main()
