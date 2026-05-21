#!/usr/bin/env python3
"""Curate CCHEN-only records found in Fernanda's free API candidates.

This creates a first-pass, reproducible triage table. It does not replace
expert review; it separates records that are clearly useful from records that
need manual review before promoting a source to recurrent extraction.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import re
import unicodedata
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "Data" / "Gobernanza" / "fuentes_fernanda_api_cchen_records.csv"
DEFAULT_OUTPUT = ROOT / "Data" / "Gobernanza" / "curaduria_fuentes_fernanda_api_cchen.csv"

CCHEN_PATTERNS = [
    "comision chilena de energia nuclear",
    "chilean nuclear energy commission",
    "cchen",
]

RADIOPHARMACY_TERMS = {
    "radiofarmacia": [
        "radiofarmaco",
        "radiofarmacos",
        "radiopharmaceutical",
        "radiopharmaceuticals",
        "radiotracer",
        "radiotracers",
    ],
    "medicina_nuclear": [
        "nuclear medicine",
        "medicina nuclear",
        "pet",
        "spect",
        "tomografia de emision de positrones",
        "positron emission tomography",
    ],
    "isotopos_radiofarmacos": [
        "f-18",
        "fluor 18",
        "fluorine-18",
        "18f",
        "fdg",
        "fluorodeoxyglucose",
        "fludeoxyglucose",
        "ga-68",
        "gallium-68",
        "lu-177",
        "lutetium-177",
        "tc-99m",
        "technetium",
        "tecnecio",
        "i-131",
        "iodine-131",
    ],
    "produccion_control": [
        "cyclotron",
        "ciclotron",
        "isotope production",
        "produccion de isotopos",
        "quality control",
        "control de calidad",
        "dosimetry",
        "dosimetria",
    ],
}

NUCLEAR_TECH_TERMS = [
    "neutron",
    "neutronica",
    "reactor",
    "plasma focus",
    "radiation",
    "radiacion",
    "gamma",
    "x-ray",
    "rayos x",
    "activation analysis",
    "analisis por activacion",
    "radioactive waste",
    "residuos radiactivos",
    "nuclear safety",
    "seguridad nuclear",
    "radioprotection",
    "proteccion radiologica",
]

OUTPUT_COLUMNS = [
    "source_key",
    "source_name",
    "record_id",
    "title",
    "doi",
    "url",
    "published",
    "curation_decision",
    "theme",
    "relevance_score",
    "matched_cchen",
    "matched_terms",
    "recommended_action",
    "rationale",
    "query",
    "fetched_at",
    "curated_at",
]


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


def _contains_cchen(text: str) -> tuple[bool, list[str]]:
    found: list[str] = []
    normalized = _norm(text)
    for pattern in CCHEN_PATTERNS:
        if pattern == "cchen":
            if re.search(r"(?<![a-z0-9])cchen(?![a-z0-9])", normalized):
                found.append(pattern)
        elif pattern in normalized:
            found.append(pattern)
    return bool(found), found


def _matched_terms(text: str) -> tuple[list[str], list[str]]:
    normalized = _norm(text)
    radio_matches: list[str] = []
    nuclear_matches: list[str] = []
    for group, terms in RADIOPHARMACY_TERMS.items():
        for term in terms:
            if term in {"pet", "spect"}:
                matched = re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", normalized) is not None
            else:
                matched = term in normalized
            if matched:
                radio_matches.append(f"{group}:{term}")
    for term in NUCLEAR_TECH_TERMS:
        if term in normalized:
            nuclear_matches.append(term)
    return radio_matches, nuclear_matches


def _curate(row: dict[str, str]) -> dict[str, str]:
    searchable = " ".join(
        [
            row.get("title", ""),
            row.get("snippet", ""),
            row.get("query", ""),
            row.get("doi", ""),
        ]
    )
    has_cchen, cchen_matches = _contains_cchen(searchable)
    radio_matches, nuclear_matches = _matched_terms(searchable)

    score = 0
    if has_cchen:
        score += 3
    if radio_matches:
        score += 4
    if nuclear_matches:
        score += 2
    if row.get("doi"):
        score += 1

    if has_cchen and radio_matches:
        decision = "mantener"
        theme = "radiofarmacia_medicina_nuclear"
        action = "Promover como evidencia util; usar para definir extractor recurrente por fuente."
        rationale = "Tiene alias CCHEN visible y términos de radiofarmacia/medicina nuclear."
    elif has_cchen and nuclear_matches:
        decision = "mantener"
        theme = "nuclear_cchen_no_radiofarmacia"
        action = "Mantener para observatorio nuclear general; no mezclar con módulo radiofarmacia salvo tema específico."
        rationale = "Tiene alias CCHEN visible y términos nucleares relevantes."
    elif has_cchen:
        decision = "revisar"
        theme = "cchen_sin_tema_prioritario"
        action = "Revisión manual antes de activar como extracción recurrente."
        rationale = "Tiene alias CCHEN, pero no muestra términos prioritarios en la muestra."
    else:
        decision = "descartar"
        theme = "sin_vinculo_cchen_visible"
        action = "No promover; ajustar filtro o descartar el resultado."
        rationale = "No se detectó alias CCHEN visible en los campos recuperados."

    return {
        "source_key": row.get("source_key", ""),
        "source_name": row.get("source_name", ""),
        "record_id": row.get("record_id", ""),
        "title": row.get("title", ""),
        "doi": row.get("doi", ""),
        "url": row.get("url", ""),
        "published": row.get("published", ""),
        "curation_decision": decision,
        "theme": theme,
        "relevance_score": str(score),
        "matched_cchen": "; ".join(cchen_matches),
        "matched_terms": "; ".join(radio_matches + nuclear_matches),
        "recommended_action": action,
        "rationale": rationale,
        "query": row.get("query", ""),
        "fetched_at": row.get("fetched_at", ""),
        "curated_at": dt.date.today().isoformat(),
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
    parser = argparse.ArgumentParser(description="Curaduría inicial de fuentes Fernanda CCHEN-only.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rows = read_csv(args.input)
    curated = [_curate(row) for row in rows if row.get("source_key") in {"doaj", "hal", "core"}]
    curated.sort(key=lambda row: (row["curation_decision"], row["source_key"], row["title"]))
    write_csv(args.output, curated)

    counts: dict[str, int] = {}
    themes: dict[str, int] = {}
    for row in curated:
        counts[row["curation_decision"]] = counts.get(row["curation_decision"], 0) + 1
        themes[row["theme"]] = themes.get(row["theme"], 0) + 1
    print(f"[OK] curaduría -> {args.output.relative_to(ROOT)} ({len(curated)} registros)")
    print("[OK] decisiones:", ", ".join(f"{key}={value}" for key, value in sorted(counts.items())))
    print("[OK] temas:", ", ".join(f"{key}={value}" for key, value in sorted(themes.items())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
