#!/usr/bin/env python3
"""Operational review layer for radio-pharmacy CCHEN literature.

`curate_radiofarmacia_cchen.py` separates obvious records from ambiguous
records. This script applies a second, explicit review layer so the consultant
can reproduce which records are published, retained for surveillance, kept as
low priority, or discarded.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import re
import unicodedata
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GOV_DIR = ROOT / "Data" / "Gobernanza"
REPORTS_DIR = ROOT / "Docs" / "reports"

DEFAULT_INPUT = GOV_DIR / "radiofarmacia_cchen_literature_curated.csv"
DEFAULT_OUTPUT = GOV_DIR / "radiofarmacia_cchen_literature_reviewed.csv"
DEFAULT_SUMMARY = GOV_DIR / "radiofarmacia_cchen_review_summary.csv"
DEFAULT_REPORT = REPORTS_DIR / "metodologia_revision_radiofarmacia_cchen.md"

OUTPUT_COLUMNS = [
    "seed_key",
    "seed_label",
    "source_system",
    "source_id",
    "doi",
    "pmid",
    "pmcid",
    "title",
    "journal",
    "year",
    "url",
    "curation_decision",
    "information_type",
    "relation_scope",
    "review_decision",
    "review_theme",
    "publish_scope",
    "recommended_action",
    "review_rationale",
    "matched_technical_terms",
    "matched_clinical_terms",
    "matched_geo",
    "query",
    "fetched_at",
    "curated_at",
    "reviewed_at",
]

SUMMARY_COLUMNS = ["artifact", "group_field", "group_value", "records", "generated_at"]

HIGH_VALUE_TERMS = [
    "radiopharmaceutical",
    "radiofarmaco",
    "cyclotron",
    "ciclotron",
    "radioisotope",
    "isotope production",
    "radiochemical",
    "auger-electron emitter",
    "cross sections",
    "production feasibility",
    "gamma camera",
    "internal contamination",
    "nuclear medicine",
    "pet/ct",
    "pet-mri",
    "spect",
    "mibi",
    "sestamibi",
    "scintigraphy",
    "fdg",
    "fluorodeoxyglucose",
    "fludeoxyglucose",
    "fluorine-18",
    "18f",
    "lu-dotate",
    "ludotate",
    "dotatate",
    "radioiodine",
    "iodine",
    "thyroid cancer",
    "radioprotectors",
]

LOW_PRIORITY_TERMS = [
    "regulatory",
    "gmp",
    "good manufacturing practice",
    "substandard",
    "falsified medicine",
    "marketing authorization",
    "cancer in chile",
    "latin america",
    "hypoparathyroidism",
    "neuroendocrine tumors",
    "cardiac imaging",
    "heart failure",
    "sarcoidosis",
    "calcific aortic valve",
    "pheochromocytoma",
    "paraganglioma",
]

NOISE_TERMS = [
    "abstracts",
    "poster abstracts",
    "poster presentations",
    "invited lectures",
    "annual meeting",
    "congress",
    "conference",
    "collisions",
    "rhic",
    "cosmological",
    "gravitational",
    "viral frontier",
    "acidic lake",
    "disulfiram",
    "bcg vaccine",
    "stem cell",
    "extracellular vesicles",
    "food biocontrol",
    "insect-based feed",
    "osteoarthritis",
    "beagle dogs",
    "multiple sclerosis",
    "cutaneous leishmaniasis",
    "arsenic exposure",
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


def _token_match(text: str, term: str) -> bool:
    if term in {"pet", "spect", "fdg"}:
        return re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", text) is not None
    return term in text


def _matches(value: object, terms: list[str]) -> list[str]:
    normalized = _norm(value)
    return sorted({term for term in terms if _token_match(normalized, term)})


def _row_text(row: dict[str, str]) -> str:
    return " ".join(
        [
            row.get("title", ""),
            row.get("journal", ""),
            row.get("matched_technical_terms", ""),
            row.get("matched_clinical_terms", ""),
            row.get("matched_geo", ""),
        ]
    )


def _has_high_value(row: dict[str, str]) -> list[str]:
    text = _row_text(row)
    matches = _matches(text, HIGH_VALUE_TERMS)
    journal = _norm(row.get("journal", ""))
    title = _norm(row.get("title", ""))
    if "applied radiation and isotopes" in journal and ("production" in title or "cross sections" in title):
        matches.append("applied radiation and isotopes:production")
    if row.get("seed_key") == "tc99m_sestamibi" and _matches(text, ["spect", "mibi", "sestamibi", "scintigraphy"]):
        matches.append("tc99m_sestamibi_seed_match")
    return sorted(set(matches))


def _manual_review(row: dict[str, str]) -> tuple[str, str, str, str, str]:
    title = _text(row.get("title", ""))
    text = _row_text(row)
    high = _has_high_value(row)
    low = _matches(text, LOW_PRIORITY_TERMS)
    noise = _matches(text, NOISE_TERMS)
    seed = row.get("seed_key", "")

    if not title:
        return (
            "descartar_ruido",
            "sin_titulo_o_metadata_insuficiente",
            "no_publicar",
            "Excluir del tablero; conservar solo auditoria.",
            "Registro sin titulo suficiente para validar utilidad.",
        )

    if high:
        return (
            "mantener_vigilancia",
            "radiofarmacia_clinica_o_tecnica",
            "vigilancia",
            "Mantener como vigilancia tematica; no contar como produccion CCHEN salvo afiliacion confirmada.",
            "Contiene senal tecnica/clinica de radiofarmacia o medicina nuclear: " + "; ".join(high[:5]),
        )

    if seed == "control_calidad_radiofarmacos" and low:
        return (
            "mantener_baja_prioridad",
            "regulatorio_calidad_no_radiofarmacia",
            "auditoria_no_tablero_principal",
            "Conservar como referencia secundaria; no publicar en tablero principal de radiofarmacia.",
            "Tema regulatorio/GMP/salud con contexto regional, pero sin senal especifica de radiofarmaco.",
        )

    if low and not noise:
        return (
            "mantener_baja_prioridad",
            "clinico_contextual_no_especifico",
            "auditoria_no_tablero_principal",
            "Conservar como contexto; promover solo si experto CCHEN confirma utilidad.",
            "Tiene contexto clinico o regional, pero no senal suficiente para vigilancia recurrente.",
        )

    if noise:
        return (
            "descartar_ruido",
            "ruido_biomedico_o_conferencia",
            "no_publicar",
            "Excluir del tablero; conservar evidencia de descarte.",
            "Registro generico, conferencia, biomedico no radiofarmaceutico o fisica no aplicable.",
        )

    return (
        "descartar_ruido",
        "sin_senal_radiofarmacia_cchen",
        "no_publicar",
        "Excluir del tablero; revisar semilla si aparecen muchos casos similares.",
        "No muestra senal CCHEN, Chile/LatAm aplicable ni tema tecnico de radiofarmacia.",
    )


def review_row(row: dict[str, str]) -> dict[str, str]:
    base_decision = row.get("curation_decision", "")
    if base_decision == "mantener_recurrente":
        review_decision = "publicar_recurrente"
        review_theme = row.get("information_type", "")
        publish_scope = "tablero_principal"
        action = "Publicar en flujo recurrente del observatorio."
        rationale = "Curaduria base detecto vinculo regional/CCHEN o tema prioritario suficiente."
    elif base_decision == "mantener_vigilancia":
        review_decision = "mantener_vigilancia"
        review_theme = row.get("information_type", "")
        publish_scope = "vigilancia"
        action = "Mantener para tendencias y benchmark; no contar como produccion CCHEN."
        rationale = "Tema global util para vigilancia, sin vinculo institucional directo."
    elif base_decision == "descartar_ruido":
        review_decision = "descartar_ruido"
        review_theme = "ruido_probable"
        publish_scope = "no_publicar"
        action = "Excluir del tablero principal."
        rationale = row.get("rationale", "Registro clasificado como ruido por curaduria base.")
    else:
        review_decision, review_theme, publish_scope, action, rationale = _manual_review(row)

    out = {column: row.get(column, "") for column in OUTPUT_COLUMNS}
    out.update(
        {
            "review_decision": review_decision,
            "review_theme": review_theme,
            "publish_scope": publish_scope,
            "recommended_action": action,
            "review_rationale": rationale,
            "reviewed_at": dt.date.today().isoformat(),
        }
    )
    return out


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def write_csv(path: Path, rows: list[dict[str, str]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def summary_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    generated_at = dt.datetime.now().isoformat(timespec="seconds")
    result: list[dict[str, str]] = []
    for field in ["review_decision", "review_theme", "publish_scope", "seed_key", "source_system"]:
        counter = Counter(row.get(field, "") for row in rows)
        for value, count in sorted(counter.items()):
            result.append(
                {
                    "artifact": "radiofarmacia_literature_reviewed",
                    "group_field": field,
                    "group_value": value or "(vacio)",
                    "records": str(count),
                    "generated_at": generated_at,
                }
            )
    return result


def write_report(path: Path, rows: list[dict[str, str]], summary_path: Path, reviewed_path: Path) -> None:
    decision_counter = Counter(row["review_decision"] for row in rows)
    scope_counter = Counter(row["publish_scope"] for row in rows)
    manual_counter = Counter(
        row["review_decision"] for row in rows if row.get("curation_decision") == "revisar_manual"
    )

    def table(counter: Counter[str]) -> str:
        lines = ["| Grupo | Registros |", "| --- | ---: |"]
        for key, value in sorted(counter.items()):
            lines.append(f"| {key or '(vacio)'} | {value} |")
        return "\n".join(lines)

    lines = [
        "# Metodologia de revision operativa - Radiofarmacia CCHEN",
        "",
        f"Fecha: {dt.date.today().isoformat()}",
        "",
        "## Objetivo",
        "",
        "Cerrar la capa `revisar_manual` de radiofarmacia con reglas replicables. Esta revision no reemplaza la validacion experta CCHEN, pero evita publicar ruido clinico, biomédico o de conferencias en el tablero principal.",
        "",
        "## Insumos y salidas",
        "",
        "- Insumo: `Data/Gobernanza/radiofarmacia_cchen_literature_curated.csv`.",
        f"- Salida revisada: `{reviewed_path.relative_to(ROOT)}`.",
        f"- Resumen: `{summary_path.relative_to(ROOT)}`.",
        "",
        "## Criterios",
        "",
        "- `publicar_recurrente`: sale de la curaduria base como CCHEN/Chile/LatAm util o tema prioritario.",
        "- `mantener_vigilancia`: registro global con senal tecnica o clinica de radiofarmacia/medicina nuclear.",
        "- `mantener_baja_prioridad`: contexto regulatorio, clinico o regional sin senal radiofarmaceutica suficiente.",
        "- `descartar_ruido`: conferencia generica, biomedicina no radiofarmaceutica, fisica no aplicable, registro sin titulo o metadata insuficiente.",
        "",
        "## Resultados",
        "",
        "### Por decision final",
        "",
        table(decision_counter),
        "",
        "### Por alcance de publicacion",
        "",
        table(scope_counter),
        "",
        "### Solo registros que venian como revisar_manual",
        "",
        table(manual_counter),
        "",
        "## Uso operativo",
        "",
        "Para tablero principal usar `publish_scope=tablero_principal`. Para vigilancia usar `publish_scope=vigilancia`. `auditoria_no_tablero_principal` y `no_publicar` no deben alimentar vistas públicas sin revisión experta.",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Revision operativa de literatura radiofarmacia CCHEN.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--summary-output", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--report-output", type=Path, default=DEFAULT_REPORT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rows = read_csv(args.input)
    reviewed = [review_row(row) for row in rows]
    reviewed.sort(key=lambda row: (row["publish_scope"], row["review_decision"], row["seed_key"], row["title"]))
    summaries = summary_rows(reviewed)
    write_csv(args.output, reviewed, OUTPUT_COLUMNS)
    write_csv(args.summary_output, summaries, SUMMARY_COLUMNS)
    write_report(args.report_output, reviewed, args.summary_output, args.output)

    decision_counter = Counter(row["review_decision"] for row in reviewed)
    manual_counter = Counter(row["review_decision"] for row in reviewed if row.get("curation_decision") == "revisar_manual")
    print(f"[OK] revision radiofarmacia -> {args.output.relative_to(ROOT)} ({len(reviewed)} registros)")
    print(f"[OK] resumen -> {args.summary_output.relative_to(ROOT)} ({len(summaries)} filas)")
    print(f"[OK] metodologia -> {args.report_output.relative_to(ROOT)}")
    print("[OK] decisiones finales:", ", ".join(f"{k}={v}" for k, v in sorted(decision_counter.items())))
    print("[OK] manuales revisados:", ", ".join(f"{k}={v}" for k, v in sorted(manual_counter.items())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
