#!/usr/bin/env python3
"""Build a master table for CCHEN outputs from repository-style sources.

Inputs are already extracted and curated. This script does not call external
APIs; it normalizes Zenodo plus DOAJ/HAL/CORE into one auditable table.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GOV_DIR = ROOT / "Data" / "Gobernanza"
RESEARCH_OUTPUTS_DIR = ROOT / "Data" / "ResearchOutputs"
REPORTS_DIR = ROOT / "Docs" / "reports"

DEFAULT_ZENODO_META = RESEARCH_OUTPUTS_DIR / "cchen_zenodo_metadata.csv"
DEFAULT_ZENODO_CURATED = GOV_DIR / "curaduria_zenodo_cchen.csv"
DEFAULT_REPOSITORY_REVIEW = GOV_DIR / "revision_fuentes_fernanda_api_cchen.csv"
DEFAULT_MASTER = GOV_DIR / "outputs_repositorios_cchen_master.csv"
DEFAULT_PUBLICABLE = GOV_DIR / "outputs_repositorios_cchen_publicables.csv"
DEFAULT_SUMMARY = GOV_DIR / "outputs_repositorios_cchen_summary.csv"
DEFAULT_REPORT = REPORTS_DIR / "metodologia_outputs_repositorios_cchen.md"

MASTER_COLUMNS = [
    "master_id",
    "canonical_key",
    "duplicate_count",
    "duplicate_rank",
    "preferred_record",
    "source_key",
    "source_name",
    "record_id",
    "doi",
    "title",
    "published",
    "year",
    "url",
    "resource_type",
    "output_kind",
    "creators",
    "affiliations",
    "relation_scope",
    "theme",
    "review_decision",
    "publish_scope",
    "observatory_use",
    "priority_rank",
    "is_tablero_principal",
    "is_vigilancia",
    "is_auditoria",
    "is_descartado",
    "file_count",
    "total_file_size_mb",
    "license",
    "access_right",
    "source_recommendation",
    "rationale",
    "evidence",
    "fetched_at",
    "curated_at",
    "reviewed_at",
    "built_at",
]

SUMMARY_COLUMNS = ["artifact", "group_field", "group_value", "records", "generated_at"]

SOURCE_PRIORITY = {
    "zenodo": 1,
    "doaj": 2,
    "core": 3,
    "hal": 4,
}

DECISION_PRIORITY = {
    "publicar_recurrente": 1,
    "mantener_recurrente": 1,
    "mantener_indirecto": 2,
    "mantener_baja_prioridad": 3,
    "descartar_ruido": 9,
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


def _slug(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "_", _norm(value)).strip("_")


def _year(value: object) -> str:
    match = re.search(r"(19|20)\d{2}", _text(value))
    return match.group(0) if match else ""


def _doi_key(doi: object) -> str:
    text = _norm(doi)
    text = text.replace("https://doi.org/", "").replace("http://doi.org/", "")
    text = text.replace("doi:", "").strip().strip("/")
    return text


def canonical_key(row: dict[str, str]) -> str:
    doi = _doi_key(row.get("doi", ""))
    if doi:
        return f"doi:{doi}"
    url = _norm(row.get("url", ""))
    if url:
        return f"url:{url}"
    return f"{row.get('source_key', '')}:{row.get('record_id', '')}"


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


def _zenodo_publish_scope(decision: str) -> tuple[str, str, str]:
    if decision == "mantener_recurrente":
        return "publicar_recurrente", "tablero_principal", "output_institucional_repositorio"
    if decision == "mantener_indirecto":
        return "mantener_indirecto", "auditoria_no_tablero_principal", "vinculo_contextual"
    return "descartar_ruido", "no_publicar", "excluir"


def _resource_kind(source_key: str, resource_type: str, title: str, url: str) -> str:
    resource = _norm(resource_type)
    text = _norm(f"{resource_type} {title} {url}")
    if "dataset" in resource:
        return "dataset"
    if "presentation" in resource or "presentacion" in resource:
        return "presentacion"
    if "thesis" in resource or "tesis" in text:
        return "tesis"
    if "taxonomic treatment" in text:
        return "tratamiento_taxonomico"
    if source_key == "core" and (url.endswith(".pdf") or "download" in url):
        return "publicacion_fulltext_pdf"
    if source_key in {"doaj", "hal", "core"}:
        return "publicacion_repositorio"
    return "output_repositorio"


def build_zenodo_rows(meta_rows: list[dict[str, str]], curated_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    meta_by_id = {row.get("record_id", ""): row for row in meta_rows}
    rows: list[dict[str, str]] = []
    built_at = dt.datetime.now().isoformat(timespec="seconds")
    for curated in curated_rows:
        record_id = curated.get("record_id", "")
        meta = meta_by_id.get(record_id, {})
        decision, publish_scope, observatory_use = _zenodo_publish_scope(curated.get("curation_decision", ""))
        resource_type = _text(curated.get("resource_type_title") or curated.get("resource_type_type"))
        source_key = "zenodo"
        url = curated.get("url", "")
        row = {
            "master_id": f"zenodo:{record_id}",
            "source_key": source_key,
            "source_name": "Zenodo",
            "record_id": record_id,
            "doi": curated.get("doi", ""),
            "title": curated.get("title", ""),
            "published": curated.get("publication_date", ""),
            "year": _year(curated.get("publication_date", "")),
            "url": url,
            "resource_type": resource_type,
            "output_kind": _resource_kind(source_key, resource_type, curated.get("title", ""), url),
            "creators": meta.get("creators", ""),
            "affiliations": meta.get("affiliations", ""),
            "relation_scope": curated.get("relation_scope", ""),
            "theme": curated.get("information_type", ""),
            "review_decision": decision,
            "publish_scope": publish_scope,
            "observatory_use": observatory_use,
            "file_count": curated.get("file_count", ""),
            "total_file_size_mb": curated.get("total_file_size_mb", ""),
            "license": meta.get("license", ""),
            "access_right": meta.get("access_right", ""),
            "source_recommendation": curated.get("recommended_action", ""),
            "rationale": curated.get("rationale", ""),
            "evidence": f"match_scope={curated.get('match_scope', '')}; aliases={curated.get('matched_aliases', '')}",
            "fetched_at": curated.get("fetched_at", "") or meta.get("fetched_at", ""),
            "curated_at": curated.get("curated_at", ""),
            "reviewed_at": curated.get("curated_at", ""),
            "built_at": built_at,
        }
        rows.append(row)
    return rows


def build_repository_rows(review_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    built_at = dt.datetime.now().isoformat(timespec="seconds")
    for source in review_rows:
        source_key = source.get("source_key", "")
        decision = source.get("review_decision", "")
        if decision == "mantener_recurrente":
            publish_scope = "tablero_principal"
            observatory_use = source.get("observatory_use", "") or "produccion_cientifica_cchen"
            normalized_decision = "publicar_recurrente"
        elif decision == "mantener_baja_prioridad":
            publish_scope = "auditoria_no_tablero_principal"
            observatory_use = source.get("observatory_use", "") or "auditoria_no_tablero_principal"
            normalized_decision = decision
        else:
            publish_scope = "no_publicar"
            observatory_use = source.get("observatory_use", "") or "excluir"
            normalized_decision = "descartar_ruido"

        url = source.get("url", "")
        resource_type = "Repository record"
        row = {
            "master_id": f"{source_key}:{source.get('record_id', '')}",
            "source_key": source_key,
            "source_name": source.get("source_name", ""),
            "record_id": source.get("record_id", ""),
            "doi": source.get("doi", ""),
            "title": source.get("title", ""),
            "published": source.get("published", ""),
            "year": _year(source.get("published", "")),
            "url": url,
            "resource_type": resource_type,
            "output_kind": _resource_kind(source_key, resource_type, source.get("title", ""), url),
            "creators": "",
            "affiliations": "",
            "relation_scope": source.get("initial_decision", ""),
            "theme": source.get("review_theme", ""),
            "review_decision": normalized_decision,
            "publish_scope": publish_scope,
            "observatory_use": observatory_use,
            "file_count": "",
            "total_file_size_mb": "",
            "license": "",
            "access_right": "",
            "source_recommendation": source.get("source_recommendation", ""),
            "rationale": source.get("rationale", ""),
            "evidence": f"initial_theme={source.get('initial_theme', '')}; initial_decision={source.get('initial_decision', '')}",
            "fetched_at": "",
            "curated_at": "",
            "reviewed_at": source.get("reviewed_at", ""),
            "built_at": built_at,
        }
        rows.append(row)
    return rows


def _priority_rank(row: dict[str, str]) -> int:
    decision_rank = DECISION_PRIORITY.get(row.get("review_decision", ""), 8)
    source_rank = SOURCE_PRIORITY.get(row.get("source_key", ""), 9)
    year = int(row["year"]) if row.get("year", "").isdigit() else 0
    return decision_rank * 100000 + source_rank * 1000 - year


def finalize_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    title_counter = Counter(_slug(row.get("title", "")) for row in rows if _slug(row.get("title", "")))
    for row in rows:
        row["canonical_key"] = canonical_key(row)
        title_key = _slug(row.get("title", ""))
        if title_key and title_counter[title_key] > 1:
            row["canonical_key"] = f"title:{title_key}"
        row["priority_rank"] = str(_priority_rank(row))
        row["is_tablero_principal"] = str(row.get("publish_scope") == "tablero_principal")
        row["is_vigilancia"] = str(row.get("publish_scope") == "vigilancia")
        row["is_auditoria"] = str(row.get("publish_scope") == "auditoria_no_tablero_principal")
        row["is_descartado"] = str(row.get("publish_scope") == "no_publicar")

    by_canonical: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_canonical[row["canonical_key"]].append(row)

    for group in by_canonical.values():
        group.sort(key=lambda row: (int(row["priority_rank"]), _slug(row.get("title", "")), row.get("master_id", "")))
        for idx, row in enumerate(group, 1):
            row["duplicate_count"] = str(len(group))
            row["duplicate_rank"] = str(idx)
            row["preferred_record"] = str(idx == 1)

    rows.sort(key=lambda row: (row["is_descartado"] == "True", int(row["priority_rank"]), row.get("title", "")))
    return rows


def summary_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    generated_at = dt.datetime.now().isoformat(timespec="seconds")
    output: list[dict[str, str]] = []
    for field in ["source_key", "review_decision", "publish_scope", "output_kind", "theme", "preferred_record"]:
        counter = Counter(row.get(field, "") for row in rows)
        for value, count in sorted(counter.items()):
            output.append(
                {
                    "artifact": "outputs_repositorios_cchen_master",
                    "group_field": field,
                    "group_value": value or "(vacio)",
                    "records": str(count),
                    "generated_at": generated_at,
                }
            )
    return output


def write_report(path: Path, master_rows: list[dict[str, str]], publicable_rows: list[dict[str, str]]) -> None:
    source_counter = Counter(row["source_key"] for row in master_rows)
    decision_counter = Counter(row["review_decision"] for row in master_rows)
    scope_counter = Counter(row["publish_scope"] for row in master_rows)
    preferred_counter = Counter(row["preferred_record"] for row in master_rows)

    def table(counter: Counter[str]) -> str:
        lines = ["| Grupo | Registros |", "| --- | ---: |"]
        for key, value in sorted(counter.items()):
            lines.append(f"| {key or '(vacio)'} | {value} |")
        return "\n".join(lines)

    lines = [
        "# Metodologia - Tabla maestra de outputs CCHEN en repositorios",
        "",
        f"Fecha: {dt.date.today().isoformat()}",
        "",
        "## Objetivo",
        "",
        "Unificar Zenodo, DOAJ, HAL y CORE en una tabla maestra auditable. La tabla conserva descartes y baja prioridad para trazabilidad, pero separa claramente que puede alimentar el tablero.",
        "",
        "## Insumos",
        "",
        "- `Data/ResearchOutputs/cchen_zenodo_metadata.csv`",
        "- `Data/Gobernanza/curaduria_zenodo_cchen.csv`",
        "- `Data/Gobernanza/revision_fuentes_fernanda_api_cchen.csv`",
        "",
        "## Salidas",
        "",
        "- `Data/Gobernanza/outputs_repositorios_cchen_master.csv`: tabla completa con auditoria.",
        "- `Data/Gobernanza/outputs_repositorios_cchen_publicables.csv`: registros para tablero o vigilancia.",
        "- `Data/Gobernanza/outputs_repositorios_cchen_summary.csv`: conteos de control.",
        "- `Docs/reports/metodologia_outputs_repositorios_cchen.md`: metodologia replicable.",
        "",
        "## Reglas de uso",
        "",
        "- `publish_scope=tablero_principal`: puede alimentar vistas principales del observatorio.",
        "- `publish_scope=vigilancia`: se conserva para seguimiento y benchmark.",
        "- `publish_scope=auditoria_no_tablero_principal`: no se publica sin validacion experta.",
        "- `publish_scope=no_publicar`: descarte trazable.",
        "- `preferred_record=True`: fila preferida cuando hay DOI/URL repetido entre repositorios.",
        "",
        "## Resultados",
        "",
        f"- Registros totales: {len(master_rows)}.",
        f"- Registros publicables/vigilancia: {len(publicable_rows)}.",
        "",
        "### Por fuente",
        "",
        table(source_counter),
        "",
        "### Por decision",
        "",
        table(decision_counter),
        "",
        "### Por alcance",
        "",
        table(scope_counter),
        "",
        "### Preferidos vs duplicados",
        "",
        table(preferred_counter),
        "",
        "## Procedimiento replicable",
        "",
        "1. Refrescar `zenodo_outputs` y `fernanda_free_api_candidates` con el runner canonico.",
        "2. Ejecutar `python Scripts/run_source_refresh.py --source-key repositorios_cchen_outputs_master --force`.",
        "3. Consumir `outputs_repositorios_cchen_publicables.csv` para tablero/vigilancia.",
        "4. Mantener `outputs_repositorios_cchen_master.csv` como evidencia completa para auditoria y consultora.",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Construye tabla maestra de outputs CCHEN en repositorios.")
    parser.add_argument("--zenodo-metadata", type=Path, default=DEFAULT_ZENODO_META)
    parser.add_argument("--zenodo-curated", type=Path, default=DEFAULT_ZENODO_CURATED)
    parser.add_argument("--repository-review", type=Path, default=DEFAULT_REPOSITORY_REVIEW)
    parser.add_argument("--master-output", type=Path, default=DEFAULT_MASTER)
    parser.add_argument("--publicable-output", type=Path, default=DEFAULT_PUBLICABLE)
    parser.add_argument("--summary-output", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--report-output", type=Path, default=DEFAULT_REPORT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rows = []
    rows.extend(build_zenodo_rows(read_csv(args.zenodo_metadata), read_csv(args.zenodo_curated)))
    rows.extend(build_repository_rows(read_csv(args.repository_review)))
    rows = finalize_rows(rows)
    publicable = [row for row in rows if row.get("publish_scope") in {"tablero_principal", "vigilancia"}]
    summaries = summary_rows(rows)

    write_csv(args.master_output, rows, MASTER_COLUMNS)
    write_csv(args.publicable_output, publicable, MASTER_COLUMNS)
    write_csv(args.summary_output, summaries, SUMMARY_COLUMNS)
    write_report(args.report_output, rows, publicable)

    print(f"[OK] tabla maestra repositorios -> {args.master_output.relative_to(ROOT)} ({len(rows)} filas)")
    print(f"[OK] tabla publicable/vigilancia -> {args.publicable_output.relative_to(ROOT)} ({len(publicable)} filas)")
    print(f"[OK] resumen -> {args.summary_output.relative_to(ROOT)} ({len(summaries)} filas)")
    print(f"[OK] metodologia -> {args.report_output.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
