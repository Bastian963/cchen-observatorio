#!/usr/bin/env python3
"""Curate seeded radio-pharmacy extraction for CCHEN.

The rules are deliberately transparent so the consultant can reproduce the
same decisions after each refresh and then add expert overrides where needed.
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

DEFAULT_LITERATURE = GOV_DIR / "radiofarmacia_cchen_literature.csv"
DEFAULT_COMPOUNDS = GOV_DIR / "radiofarmacia_cchen_pubchem_compounds.csv"
DEFAULT_LITERATURE_OUT = GOV_DIR / "radiofarmacia_cchen_literature_curated.csv"
DEFAULT_COMPOUNDS_OUT = GOV_DIR / "radiofarmacia_cchen_compounds_curated.csv"
DEFAULT_SUMMARY_OUT = GOV_DIR / "radiofarmacia_cchen_curation_summary.csv"
DEFAULT_REPORT_OUT = REPORTS_DIR / "metodologia_curaduria_radiofarmacia_cchen.md"

CCHEN_ALIASES = [
    "cchen",
    "comision chilena de energia nuclear",
    "chilean nuclear energy commission",
]

CHILE_LATAM_TERMS = [
    "chile",
    "chilean",
    "latin america",
    "latin american",
    "latam",
    "america latina",
    "latinoamerica",
    "brazil",
    "brasil",
    "argentina",
    "mexico",
    "colombia",
    "peru",
    "uruguay",
]

PRODUCTION_TERMS = [
    "cyclotron",
    "ciclotron",
    "isotope production",
    "radioisotope production",
    "radiopharmaceutical production",
    "fdg production",
    "18f-fdg production",
    "synthesis module",
    "radiosynthesis",
    "radiochemical yield",
    "automated synthesizer",
    "targetry",
    "bombardment",
    "radiopharmaceutical quality control",
    "quality control of radiopharmaceutical",
    "control de calidad de radiofarmacos",
    "control de calidad",
    "radiochemical purity",
    "final purification",
]

DOSIMETRY_SAFETY_TERMS = [
    "dosimetry",
    "dosimetria",
    "internal dosimetry",
    "radiation protection",
    "radioprotection",
    "proteccion radiologica",
    "occupational exposure",
    "dose assessment",
    "absorbed dose",
    "biodistribution",
]

THERANOSTIC_TERMS = [
    "theranostic",
    "theranostics",
    "dotatate",
    "psma",
    "lutetium",
    "lu-177",
    "177lu",
    "gallium",
    "ga-68",
    "68ga",
    "radioiodine",
    "iodine-131",
    "i-131",
    "sestamibi",
    "tc-99m",
    "99mtc",
    "radiopharmaceutical",
    "radiofarmaco",
    "radiofarmacos",
    "radiotracer",
]

CLINICAL_GENERIC_TERMS = [
    "pet/ct",
    "pet",
    "spect",
    "fdg",
    "fludeoxyglucose",
    "fluorodeoxyglucose",
    "imaging",
    "diagnostic",
    "staging",
    "metastasis",
]

LOW_SIGNAL_TERMS = [
    "case report",
    "meta-analysis",
    "umbrella review",
    "breast cancer",
    "gastric cancer",
    "melanoma",
    "lung cancer",
    "lymphoma",
]

LITERATURE_COLUMNS = [
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
    "relation_scope",
    "information_type",
    "curation_decision",
    "priority_score",
    "matched_cchen",
    "matched_geo",
    "matched_technical_terms",
    "matched_clinical_terms",
    "rationale",
    "recommended_consultant_action",
    "query",
    "fetched_at",
    "curated_at",
]

COMPOUND_COLUMNS = [
    "seed_key",
    "seed_label",
    "compound_query",
    "cid",
    "title",
    "molecular_formula",
    "molecular_weight",
    "inchi_key",
    "pubchem_url",
    "relation_scope",
    "information_type",
    "curation_decision",
    "priority_score",
    "rationale",
    "recommended_consultant_action",
    "fetched_at",
    "curated_at",
]

SUMMARY_COLUMNS = [
    "artifact",
    "group_field",
    "group_value",
    "records",
    "generated_at",
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


def _has_token(text: str, term: str) -> bool:
    if term == "cchen":
        return re.search(r"(?<![a-z0-9])cchen(?![a-z0-9])", text) is not None
    if term in {"pet", "spect", "fdg"}:
        return re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", text) is not None
    return term in text


def _matches(text: str, terms: list[str]) -> list[str]:
    return [term for term in terms if _has_token(text, term)]


def _classify_information_type(
    production: list[str],
    dosimetry: list[str],
    theranostic: list[str],
    clinical: list[str],
) -> str:
    if production:
        return "produccion_ciclotron_control_calidad"
    if dosimetry:
        return "dosimetria_seguridad_radiologica"
    if theranostic:
        return "radiofarmaco_teranostico_compuesto"
    if clinical:
        return "paper_clinico_pet_spect"
    return "otro_revisar"


def _classify_relation_scope(
    cchen: list[str],
    geo: list[str],
    information_type: str,
    low_signal: list[str],
) -> str:
    if cchen:
        return "cchen_directo"
    if geo and information_type != "otro_revisar":
        return "chile_latam_util"
    if information_type in {
        "produccion_ciclotron_control_calidad",
        "dosimetria_seguridad_radiologica",
        "radiofarmaco_teranostico_compuesto",
    }:
        return "vigilancia_global_util"
    if low_signal:
        return "ruido_probable"
    return "revisar_manual"


def _decision(relation_scope: str, information_type: str) -> tuple[str, str, str]:
    if relation_scope == "cchen_directo":
        return (
            "mantener_recurrente",
            "Vinculo CCHEN visible en el registro.",
            "Mantener en extracción recurrente y priorizar para revisión experta.",
        )
    if relation_scope == "chile_latam_util":
        return (
            "mantener_recurrente",
            "Registro útil por contexto Chile/LatAm en tema radiofarmacia o medicina nuclear.",
            "Mantener como vigilancia regional; etiquetar para validación temática.",
        )
    if relation_scope == "vigilancia_global_util":
        return (
            "mantener_vigilancia",
            "No es CCHEN directo, pero cubre capacidad, compuesto, dosimetría o control relevante.",
            "Mantener con cupo limitado por semilla; usar para tendencias y benchmark.",
        )
    if relation_scope == "ruido_probable":
        return (
            "descartar_ruido",
            "Registro clínico genérico sin vínculo CCHEN/Chile/LatAm ni señal técnica prioritaria.",
            "Excluir de tablero principal; conservar solo en auditoría si se requiere trazabilidad.",
        )
    return (
        "revisar_manual",
        f"Señal insuficiente o ambigua para {information_type}.",
        "Revisión manual antes de promover o descartar.",
    )


def _score(cchen: list[str], geo: list[str], production: list[str], dosimetry: list[str], theranostic: list[str], clinical: list[str]) -> int:
    score = 0
    if cchen:
        score += 6
    if geo:
        score += 3
    if production:
        score += 4
    if dosimetry:
        score += 3
    if theranostic:
        score += 3
    if clinical:
        score += 1
    return score


def curate_literature(row: dict[str, str]) -> dict[str, str]:
    content = " ".join(
        [
            row.get("title", ""),
            row.get("abstract", ""),
            row.get("authors", ""),
            row.get("journal", ""),
        ]
    )
    normalized = _norm(content)
    cchen = _matches(normalized, CCHEN_ALIASES)
    geo = _matches(normalized, CHILE_LATAM_TERMS)
    production = _matches(normalized, PRODUCTION_TERMS)
    dosimetry = _matches(normalized, DOSIMETRY_SAFETY_TERMS)
    theranostic = _matches(normalized, THERANOSTIC_TERMS)
    clinical = _matches(normalized, CLINICAL_GENERIC_TERMS)
    low_signal = _matches(normalized, LOW_SIGNAL_TERMS)
    information_type = _classify_information_type(production, dosimetry, theranostic, clinical)
    relation_scope = _classify_relation_scope(cchen, geo, information_type, low_signal)
    decision, rationale, action = _decision(relation_scope, information_type)

    return {
        "seed_key": row.get("seed_key", ""),
        "seed_label": row.get("seed_label", ""),
        "source_system": row.get("source_system", ""),
        "source_id": row.get("source_id", ""),
        "doi": row.get("doi", ""),
        "pmid": row.get("pmid", ""),
        "pmcid": row.get("pmcid", ""),
        "title": row.get("title", ""),
        "journal": row.get("journal", ""),
        "year": row.get("year", ""),
        "url": row.get("url", ""),
        "relation_scope": relation_scope,
        "information_type": information_type,
        "curation_decision": decision,
        "priority_score": str(_score(cchen, geo, production, dosimetry, theranostic, clinical)),
        "matched_cchen": "; ".join(cchen),
        "matched_geo": "; ".join(geo),
        "matched_technical_terms": "; ".join(production + dosimetry + theranostic),
        "matched_clinical_terms": "; ".join(clinical),
        "rationale": rationale,
        "recommended_consultant_action": action,
        "query": row.get("query", ""),
        "fetched_at": row.get("fetched_at", ""),
        "curated_at": dt.date.today().isoformat(),
    }


def curate_compound(row: dict[str, str]) -> dict[str, str]:
    return {
        "seed_key": row.get("seed_key", ""),
        "seed_label": row.get("seed_label", ""),
        "compound_query": row.get("compound_query", ""),
        "cid": row.get("cid", ""),
        "title": row.get("title", ""),
        "molecular_formula": row.get("molecular_formula", ""),
        "molecular_weight": row.get("molecular_weight", ""),
        "inchi_key": row.get("inchi_key", ""),
        "pubchem_url": row.get("pubchem_url", ""),
        "relation_scope": "semilla_cchen",
        "information_type": "ficha_compuesto_radionuclido",
        "curation_decision": "mantener_recurrente",
        "priority_score": "10",
        "rationale": "Compuesto/radionúclido incluido explícitamente en la lista semilla CCHEN.",
        "recommended_consultant_action": "Mantener y enriquecer con sinónimos, proveedores, uso clínico y enlaces regulatorios si se incorporan nuevas APIs.",
        "fetched_at": row.get("fetched_at", ""),
        "curated_at": dt.date.today().isoformat(),
    }


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def write_csv(path: Path, rows: list[dict[str, str]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _summary_rows(artifact: str, rows: list[dict[str, str]], fields: list[str]) -> list[dict[str, str]]:
    generated_at = dt.datetime.now().isoformat(timespec="seconds")
    out: list[dict[str, str]] = []
    for field in fields:
        counter = Counter(row.get(field, "") for row in rows)
        for value, count in sorted(counter.items()):
            out.append(
                {
                    "artifact": artifact,
                    "group_field": field,
                    "group_value": value or "(vacio)",
                    "records": str(count),
                    "generated_at": generated_at,
                }
            )
    return out


def write_methodology_report(
    path: Path,
    literature_rows: list[dict[str, str]],
    compound_rows: list[dict[str, str]],
    literature_out: Path,
    compound_out: Path,
    summary_out: Path,
) -> None:
    def table(counter: Counter[str]) -> str:
        if not counter:
            return "_Sin registros._"
        lines = ["| Grupo | Registros |", "| --- | ---: |"]
        for key, value in sorted(counter.items()):
            lines.append(f"| {key or '(vacio)'} | {value} |")
        return "\n".join(lines)

    relation_counter = Counter(row["relation_scope"] for row in literature_rows)
    decision_counter = Counter(row["curation_decision"] for row in literature_rows)
    type_counter = Counter(row["information_type"] for row in literature_rows)
    seed_counter = Counter(row["seed_key"] for row in literature_rows)

    lines = [
        "# Metodologia replicable - Curaduria Radiofarmacia CCHEN",
        "",
        f"Fecha: {dt.date.today().isoformat()}",
        "",
        "## Objetivo",
        "",
        "Separar datos utiles de ruido en la extraccion semilla de radiofarmacia CCHEN. La metodologia evita descargar Bio/Farma completo y usa semillas controladas mas reglas trazables de curaduria.",
        "",
        "## Insumos",
        "",
        "- `Data/Gobernanza/radiofarmacia_cchen_seeds.csv`: lista de semillas aprobadas.",
        "- `Data/Gobernanza/radiofarmacia_cchen_pubchem_compounds.csv`: fichas PubChem por compuesto/radionuclido semilla.",
        "- `Data/Gobernanza/radiofarmacia_cchen_literature.csv`: literatura desde Europe PMC y PubMed.",
        "",
        "## Salidas",
        "",
        f"- `{literature_out.relative_to(ROOT)}`",
        f"- `{compound_out.relative_to(ROOT)}`",
        f"- `{summary_out.relative_to(ROOT)}`",
        "",
        "## Reglas de clasificacion",
        "",
        "1. `cchen_directo`: el registro menciona CCHEN, Comision Chilena de Energia Nuclear o Chilean Nuclear Energy Commission.",
        "2. `chile_latam_util`: no menciona CCHEN, pero contiene Chile/Chilean/Latin America u otro termino regional latinoamericano.",
        "3. `vigilancia_global_util`: no tiene foco geografico, pero trata produccion/ciclotron/control de calidad/dosimetria/radiofarmacos/teranosticos priorizados.",
        "4. `ruido_probable`: paper clinico generico sin vinculo CCHEN/Chile/LatAm ni senal tecnica prioritaria.",
        "5. `revisar_manual`: registro ambiguo que no debe promoverse automaticamente.",
        "",
        "## Tipos de informacion",
        "",
        "- `ficha_compuesto_radionuclido`: PubChem para compuestos definidos por semilla.",
        "- `produccion_ciclotron_control_calidad`: produccion, sintesis, GMP, rendimiento radioquimico, control de calidad.",
        "- `dosimetria_seguridad_radiologica`: dosimetria, biodistribucion, proteccion radiologica, exposicion ocupacional.",
        "- `radiofarmaco_teranostico_compuesto`: DOTATATE, Lu-177, Ga-68, Tc-99m, I-131, radiotracers, theranostics.",
        "- `paper_clinico_pet_spect`: uso clinico PET/SPECT/FDG sin otra senal tecnica.",
        "",
        "## Decisiones",
        "",
        "- `mantener_recurrente`: ingresa al flujo regular del observatorio.",
        "- `mantener_vigilancia`: se conserva con cupo limitado para tendencias o benchmark.",
        "- `revisar_manual`: requiere validacion experta antes de publicarse.",
        "- `descartar_ruido`: excluir del tablero principal; conservar solo como auditoria.",
        "",
        "## Resultados literatura",
        "",
        "### Por relacion CCHEN",
        "",
        table(relation_counter),
        "",
        "### Por decision",
        "",
        table(decision_counter),
        "",
        "### Por tipo de informacion",
        "",
        table(type_counter),
        "",
        "### Por semilla",
        "",
        table(seed_counter),
        "",
        "## Resultados compuestos",
        "",
        f"- Compuestos/radionuclidos curados: {len(compound_rows)}.",
        "- Todos se clasifican como `mantener_recurrente` porque nacen de la lista semilla aprobada.",
        "",
        "## Procedimiento operativo para la consultora",
        "",
        "1. Ejecutar `python Scripts/fetch_radiofarmacia_cchen_seeded.py --max-literature-per-seed 20`.",
        "2. Ejecutar `python Scripts/curate_radiofarmacia_cchen.py`.",
        "3. Ejecutar `python Scripts/review_radiofarmacia_cchen.py` para cerrar la capa operativa de revision.",
        "4. Publicar solo `publish_scope=tablero_principal`; usar `publish_scope=vigilancia` para tendencias y benchmark.",
        "5. No ampliar semillas ni fuentes sin registrar justificacion, filtro, fecha, conteo y evidencia de ruido.",
        "6. Si una semilla produce demasiado `descartar_ruido`, ajustar `scope_terms` en `radiofarmacia_cchen_seeds.csv` antes de la siguiente corrida.",
        "",
        "## Control de cambios",
        "",
        "Toda modificacion de reglas o semillas debe quedar versionada y documentada en este archivo o en el runbook operativo.",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Curaduria replicable de radiofarmacia CCHEN.")
    parser.add_argument("--literature", type=Path, default=DEFAULT_LITERATURE)
    parser.add_argument("--compounds", type=Path, default=DEFAULT_COMPOUNDS)
    parser.add_argument("--literature-output", type=Path, default=DEFAULT_LITERATURE_OUT)
    parser.add_argument("--compounds-output", type=Path, default=DEFAULT_COMPOUNDS_OUT)
    parser.add_argument("--summary-output", type=Path, default=DEFAULT_SUMMARY_OUT)
    parser.add_argument("--report-output", type=Path, default=DEFAULT_REPORT_OUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    literature_raw = read_csv(args.literature)
    compounds_raw = read_csv(args.compounds)
    literature_rows = [curate_literature(row) for row in literature_raw]
    compounds_rows = [curate_compound(row) for row in compounds_raw]

    literature_rows.sort(
        key=lambda row: (
            {"mantener_recurrente": 0, "mantener_vigilancia": 1, "revisar_manual": 2, "descartar_ruido": 3}.get(row["curation_decision"], 4),
            -int(row["priority_score"] or 0),
            row["seed_key"],
            row["title"],
        )
    )
    compounds_rows.sort(key=lambda row: (row["seed_key"], row["title"], row["cid"]))

    summary_rows = []
    summary_rows.extend(_summary_rows("literature", literature_rows, ["relation_scope", "information_type", "curation_decision", "seed_key", "source_system"]))
    summary_rows.extend(_summary_rows("compounds", compounds_rows, ["relation_scope", "information_type", "curation_decision", "seed_key"]))

    write_csv(args.literature_output, literature_rows, LITERATURE_COLUMNS)
    write_csv(args.compounds_output, compounds_rows, COMPOUND_COLUMNS)
    write_csv(args.summary_output, summary_rows, SUMMARY_COLUMNS)
    write_methodology_report(
        args.report_output,
        literature_rows,
        compounds_rows,
        args.literature_output,
        args.compounds_output,
        args.summary_output,
    )

    decisions = Counter(row["curation_decision"] for row in literature_rows)
    scopes = Counter(row["relation_scope"] for row in literature_rows)
    print(f"[OK] literatura curada -> {args.literature_output.relative_to(ROOT)} ({len(literature_rows)} filas)")
    print(f"[OK] compuestos curados -> {args.compounds_output.relative_to(ROOT)} ({len(compounds_rows)} filas)")
    print(f"[OK] resumen -> {args.summary_output.relative_to(ROOT)} ({len(summary_rows)} filas)")
    print(f"[OK] metodologia -> {args.report_output.relative_to(ROOT)}")
    print("[OK] decisiones literatura:", ", ".join(f"{key}={value}" for key, value in sorted(decisions.items())))
    print("[OK] relacion literatura:", ", ".join(f"{key}={value}" for key, value in sorted(scopes.items())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
