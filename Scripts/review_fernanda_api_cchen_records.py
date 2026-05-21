#!/usr/bin/env python3
"""Manual review layer for DOAJ/HAL/CORE CCHEN-only candidates.

The previous curation script is rule-based. This script adds a transparent
review layer for the small set of records that need business/observatory
judgement before promoting a source to recurrent extraction.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import re
import unicodedata
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "Data" / "Gobernanza" / "curaduria_fuentes_fernanda_api_cchen.csv"
DEFAULT_OUTPUT = ROOT / "Data" / "Gobernanza" / "revision_fuentes_fernanda_api_cchen.csv"

OUTPUT_COLUMNS = [
    "source_key",
    "source_name",
    "record_id",
    "title",
    "doi",
    "url",
    "published",
    "initial_decision",
    "initial_theme",
    "review_decision",
    "review_theme",
    "observatory_use",
    "source_recommendation",
    "rationale",
    "reviewed_at",
]

LOW_PRIORITY = {
    "281692138": "CCHEN aparece, pero el tema es ingenieria clinica general; conservar como evidencia de produccion, no como prioridad tematica.",
    "10.3390/agronomy15030691": "Tema agricola/boro sin senal nuclear visible en titulo; conservar solo como produccion CCHEN de baja prioridad.",
    "10.3390/molecules30193984": "Tema alimentos/botanica sin senal nuclear visible en titulo; conservar solo como produccion CCHEN de baja prioridad.",
    "10.3390/e20090696": "Metodologia probabilistica general; puede ser produccion CCHEN, pero no eje tematico del observatorio.",
    "1902552": "Biofeedback/locomocion sin senal nuclear visible; conservar solo si se confirma afiliacion CCHEN.",
    "1331032": "Comportamiento colectivo sin senal nuclear visible; conservar solo si se confirma afiliacion CCHEN.",
    "1254155": "Decision colectiva sin senal nuclear visible; conservar solo si se confirma afiliacion CCHEN.",
}

DISCARD = {
    "122481241": "Reviewer Acknowledgements no es output cientifico CCHEN reutilizable para indicadores.",
    "86874791": "Reviewer Acknowledgements no es output cientifico CCHEN reutilizable para indicadores.",
}


def _text(value: object) -> str:
    return " ".join(str(value or "").replace("\xa0", " ").split()).strip()


def _norm(value: object) -> str:
    text = _text(value)
    text = "".join(
        char
        for char in unicodedata.normalize("NFKD", text)
        if not unicodedata.combining(char)
    )
    return text.lower()


def _has_any(text: str, terms: list[str]) -> bool:
    normalized = _norm(text)
    return any(term in normalized for term in terms)


def _theme(title: str, initial_theme: str) -> str:
    normalized = _norm(title)
    if _has_any(normalized, ["fluor 18", "f-18", "fdg", "tomografia de emision de positrones", "pet", "ciclotron"]):
        return "radiofarmacia_medicina_nuclear"
    if _has_any(normalized, ["dosimetr", "dicentric chromosome", "biodosim", "radiation", "radiacion", "gamma"]):
        return "radioproteccion_dosimetria_radiacion"
    if _has_any(normalized, ["plasma focus", "pinch", "z-pinch", "openmc", "reactor", "neutron", "radioactive beams", "decay properties"]):
        return "nuclear_plasma_reactores"
    if _has_any(normalized, ["solar wind", "whistler", "proton", "electron", "kinetic simulation", "kappa"]):
        return "fisica_plasma_espacial"
    if _has_any(normalized, ["rare-earth", "rare earth", "lanthanide", "tierras raras", "cu-cr", "moo3", "sofc", "cathodes", "photovoltaic", "thiophosphate"]):
        return "materiales_energia_tierras_raras"
    if _has_any(normalized, ["revolucion atomica", "energia nuclear en chile"]):
        return "historia_institucional_nuclear"
    if initial_theme != "cchen_sin_tema_prioritario":
        return initial_theme
    return "produccion_cchen_baja_prioridad"


def _recommendation(source_key: str, decision: str) -> str:
    if decision == "descartar_ruido":
        return "No promover al observatorio; conservar solo como evidencia de descarte."
    if source_key == "core":
        return "Mantener CORE como fuente recurrente secundaria semestral, con deduplicacion contra OpenAlex/CrossRef."
    if source_key == "doaj":
        return "Mantener DOAJ como fuente recurrente secundaria semestral para cobertura open access y verificacion cruzada."
    if source_key == "hal":
        return "Mantener HAL como fuente suplementaria semestral; revisar baja prioridad antes de publicar."
    return "Mantener con revision semestral."


def _review(row: dict[str, str]) -> dict[str, str]:
    record_id = row.get("record_id", "")
    title = row.get("title", "")
    initial_theme = row.get("theme", "")
    if record_id in DISCARD:
        decision = "descartar_ruido"
        theme = "ruido_editorial"
        use = "excluir"
        rationale = DISCARD[record_id]
    elif record_id in LOW_PRIORITY:
        decision = "mantener_baja_prioridad"
        theme = "produccion_cchen_baja_prioridad"
        use = "auditoria_no_tablero_principal"
        rationale = LOW_PRIORITY[record_id]
    else:
        decision = "mantener_recurrente"
        theme = _theme(title, initial_theme)
        if theme == "radiofarmacia_medicina_nuclear":
            use = "modulo_radiofarmacia_y_observatorio_general"
        elif theme in {"nuclear_plasma_reactores", "radioproteccion_dosimetria_radiacion"}:
            use = "observatorio_nuclear_general"
        else:
            use = "produccion_cientifica_cchen"
        rationale = "Registro con alias CCHEN visible y tema util para produccion cientifica, capacidades o historia institucional."

    return {
        "source_key": row.get("source_key", ""),
        "source_name": row.get("source_name", ""),
        "record_id": record_id,
        "title": title,
        "doi": row.get("doi", ""),
        "url": row.get("url", ""),
        "published": row.get("published", ""),
        "initial_decision": row.get("curation_decision", ""),
        "initial_theme": initial_theme,
        "review_decision": decision,
        "review_theme": theme,
        "observatory_use": use,
        "source_recommendation": _recommendation(row.get("source_key", ""), decision),
        "rationale": rationale,
        "reviewed_at": dt.date.today().isoformat(),
    }


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Revision curatorial DOAJ/HAL/CORE.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rows = read_csv(args.input)
    reviewed = [_review(row) for row in rows]
    reviewed.sort(key=lambda row: (row["review_decision"], row["source_key"], row["review_theme"], row["title"]))
    write_csv(args.output, reviewed)

    decisions: dict[str, int] = {}
    by_source: dict[tuple[str, str], int] = {}
    for row in reviewed:
        decisions[row["review_decision"]] = decisions.get(row["review_decision"], 0) + 1
        key = (row["source_key"], row["review_decision"])
        by_source[key] = by_source.get(key, 0) + 1
    print(f"[OK] revision Fernanda API -> {args.output.relative_to(ROOT)} ({len(reviewed)} registros)")
    print("[OK] decisiones:", ", ".join(f"{k}={v}" for k, v in sorted(decisions.items())))
    print("[OK] fuente/decision:", ", ".join(f"{s}:{d}={v}" for (s, d), v in sorted(by_source.items())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
