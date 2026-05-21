#!/usr/bin/env python3
"""First-pass curation for Zenodo CCHEN metadata records."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import re
import unicodedata
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "Data" / "ResearchOutputs" / "cchen_zenodo_metadata.csv"
DEFAULT_OUTPUT = ROOT / "Data" / "Gobernanza" / "curaduria_zenodo_cchen.csv"

CCHEN_PATTERNS = [
    "comision chilena de energia nuclear",
    "chilean nuclear energy commission",
    "cchen",
]

REVIEW_OVERRIDES = {
    "17700048": {
        "curation_decision": "mantener_indirecto",
        "relation_scope": "dataset_de_publicacion_cchen_relacionada",
        "information_type": "dataset_repositorio",
        "recommended_action": "Mantener como vinculo indirecto; no contarlo como output institucional Zenodo hasta confirmar afiliacion.",
        "rationale": "Dataset asociado a paper con senal CCHEN, pero el registro Zenodo declara creador/afiliacion externa.",
    },
    "13951500": {
        "curation_decision": "descartar_ruido",
        "relation_scope": "sin_relacion_cchen_curada",
        "information_type": "publicacion_output",
        "recommended_action": "Excluir del observatorio; conservar solo como evidencia de descarte.",
        "rationale": "El alias CCHEN aparece solo en metadata cruda y el registro no muestra afiliacion ni tema CCHEN.",
    },
}

RADIOPHARMACY_TERMS = [
    "radiofarmaco",
    "radiopharmaceutical",
    "radiotracer",
    "nuclear medicine",
    "medicina nuclear",
    "f-18",
    "18f",
    "fdg",
    "ga-68",
    "lu-177",
    "tc-99m",
    "i-131",
    "cyclotron",
    "ciclotron",
    "dosimetry",
    "dosimetria",
]

NUCLEAR_TERMS = [
    "nuclear",
    "reactor",
    "neutron",
    "radiation",
    "radiacion",
    "gamma",
    "radioactive",
    "radiactivo",
    "activation analysis",
    "plasma focus",
    "radiological",
    "radiologico",
]

OUTPUT_COLUMNS = [
    "record_id",
    "doi",
    "title",
    "publication_date",
    "resource_type_type",
    "resource_type_title",
    "url",
    "curation_decision",
    "relation_scope",
    "information_type",
    "matched_terms",
    "recommended_action",
    "rationale",
    "match_scope",
    "matched_aliases",
    "file_count",
    "total_file_size_mb",
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


def _contains_cchen(value: object) -> bool:
    normalized = _norm(value)
    return any(pattern in normalized for pattern in CCHEN_PATTERNS if pattern != "cchen") or bool(
        re.search(r"(?<![a-z0-9])cchen(?![a-z0-9])", normalized)
    )


def _matches(value: object, terms: list[str]) -> list[str]:
    normalized = _norm(value)
    return sorted({term for term in terms if term in normalized})


def _information_type(row: dict[str, str], searchable: str) -> tuple[str, list[str]]:
    radio_matches = _matches(searchable, RADIOPHARMACY_TERMS)
    nuclear_matches = _matches(searchable, NUCLEAR_TERMS)
    resource_type = _norm(f"{row.get('resource_type_type', '')} {row.get('resource_type_title', '')}")

    if radio_matches:
        return "radiofarmacia_medicina_nuclear", radio_matches
    if nuclear_matches:
        return "nuclear_general_cchen", nuclear_matches
    if "dataset" in resource_type or "data" in resource_type:
        return "dataset_repositorio", []
    if "software" in resource_type:
        return "software_repositorio", []
    if "poster" in resource_type or "presentation" in resource_type:
        return "presentacion_material", []
    if "publication" in resource_type or row.get("doi"):
        return "publicacion_output", []
    return "otro_output", []


def _is_email_acronym_false_positive(row: dict[str, str]) -> bool:
    aliases = _text(row.get("matched_aliases", ""))
    affiliations = _norm(row.get("affiliations", ""))
    if aliases != "CCHEN":
        return False
    return re.search(r"(?<![a-z0-9])cchen\s*@", affiliations) is not None


def _curate(row: dict[str, str]) -> dict[str, str]:
    searchable = " ".join(
        [
            row.get("title", ""),
            row.get("description_snippet", ""),
            row.get("keywords", ""),
            row.get("communities", ""),
            row.get("creators", ""),
            row.get("affiliations", ""),
        ]
    )
    has_cchen = _contains_cchen(searchable) or bool(_text(row.get("matched_aliases", "")))
    information_type, matched_terms = _information_type(row, searchable)
    match_scope = row.get("match_scope", "")

    override = REVIEW_OVERRIDES.get(row.get("record_id", ""))
    if override:
        decision = override["curation_decision"]
        relation_scope = override["relation_scope"]
        information_type = override["information_type"]
        action = override["recommended_action"]
        rationale = override["rationale"]
        matched_terms = []
    elif _is_email_acronym_false_positive(row):
        decision = "descartar_ruido"
        relation_scope = "alias_cchen_en_email_no_institucional"
        information_type = "falso_positivo_alias"
        action = "Excluir del observatorio; conservar solo como evidencia de filtro."
        rationale = "El token CCHEN aparece como parte de un correo o identificador externo, no como afiliacion institucional CCHEN."
        matched_terms = []
    elif match_scope == "creator_affiliation":
        decision = "mantener_recurrente"
        relation_scope = "cchen_affiliation"
        action = "Incorporar como output institucional Zenodo; refresco semestral."
        rationale = "El alias CCHEN aparece en afiliacion de creador."
    elif match_scope == "metadata_text" and not _contains_cchen(searchable):
        decision = "revisar_manual"
        relation_scope = "cchen_raw_metadata_only"
        action = "Revisar en Zenodo antes de publicar como dato institucional."
        rationale = "El alias CCHEN aparece solo en metadata cruda no expuesta en campos curados."
    elif has_cchen and information_type in {"radiofarmacia_medicina_nuclear", "nuclear_general_cchen"}:
        decision = "mantener_recurrente"
        relation_scope = "cchen_metadata_tema_prioritario"
        action = "Mantener; validar afiliacion si se usara en indicadores institucionales."
        rationale = "El alias CCHEN aparece en metadatos y el tema es prioritario para el observatorio."
    elif has_cchen:
        decision = "revisar_manual"
        relation_scope = "cchen_metadata_no_afiliacion"
        action = "Revisar antes de publicar como dato institucional."
        rationale = "El alias CCHEN aparece, pero no necesariamente como afiliacion institucional."
    else:
        decision = "descartar_ruido"
        relation_scope = "sin_cchen_visible"
        action = "No promover; ajustar filtro."
        rationale = "No se detecto alias CCHEN visible en campos curados."

    return {
        "record_id": row.get("record_id", ""),
        "doi": row.get("doi", ""),
        "title": row.get("title", ""),
        "publication_date": row.get("publication_date", ""),
        "resource_type_type": row.get("resource_type_type", ""),
        "resource_type_title": row.get("resource_type_title", ""),
        "url": row.get("url", ""),
        "curation_decision": decision,
        "relation_scope": relation_scope,
        "information_type": information_type,
        "matched_terms": "; ".join(matched_terms),
        "recommended_action": action,
        "rationale": rationale,
        "match_scope": match_scope,
        "matched_aliases": row.get("matched_aliases", ""),
        "file_count": row.get("file_count", ""),
        "total_file_size_mb": row.get("total_file_size_mb", ""),
        "fetched_at": row.get("fetched_at", ""),
        "curated_at": dt.date.today().isoformat(),
    }


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Curaduria inicial de metadatos Zenodo CCHEN.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rows = read_csv(args.input)
    curated = [_curate(row) for row in rows]
    curated.sort(key=lambda row: (row["curation_decision"], row["publication_date"], row["title"]), reverse=True)
    write_csv(args.output, curated)

    counts: dict[str, int] = {}
    relation: dict[str, int] = {}
    for row in curated:
        counts[row["curation_decision"]] = counts.get(row["curation_decision"], 0) + 1
        relation[row["relation_scope"]] = relation.get(row["relation_scope"], 0) + 1
    print(f"[OK] curaduria Zenodo -> {args.output.relative_to(ROOT)} ({len(curated)} registros)")
    print("[OK] decisiones:", ", ".join(f"{key}={value}" for key, value in sorted(counts.items())) or "sin registros")
    print("[OK] relacion:", ", ".join(f"{key}={value}" for key, value in sorted(relation.items())) or "sin registros")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
