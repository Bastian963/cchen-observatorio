#!/usr/bin/env python3
"""Build the pre-award source catalog package for the consultant handoff.

The script reads Fernanda's workbook, reconciles it with the existing runtime
source registry, and writes CSV + Markdown artifacts under Data/Gobernanza and
Docs/reports. It intentionally does not mutate the operational source runtime.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import importlib.util
import json
import os
import re
import subprocess
import sys
import unicodedata
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse
from xml.etree import ElementTree as ET
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
GOV_DIR = ROOT / "Data" / "Gobernanza"
REPORTS_DIR = ROOT / "Docs" / "reports"
RUNTIME_PATH = GOV_DIR / "data_sources_runtime.csv"
DEFAULT_MATRIX_PATH = Path(
    os.environ.get(
        "FUENTES_INFORMACION_XLSX",
        "/media/bastin/Nuevo vol/Mumito/Descarga/Fuentes de informacion.xlsx",
    )
)
ALT_MATRIX_PATH = Path("/media/bastin/Nuevo vol/Mumito/Descarga/Fuentes de información.xlsx")

XLSX_NS = {
    "a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}
REL_NS = {"rel": "http://schemas.openxmlformats.org/package/2006/relationships"}

RAW_COLUMNS = [
    "matrix_row",
    "categoria",
    "subcategoria",
    "source_name",
    "especialidad",
    "acceso",
    "site_url",
    "api_available",
    "api_url",
    "estado_planilla",
    "comentarios_fena",
    "comentarios_bastian",
]

CATALOG_COLUMNS = [
    "source_key",
    "source_name",
    "origen",
    "categoria",
    "subcategoria",
    "especialidad",
    "acceso",
    "site_url",
    "api_available",
    "api_url",
    "cchen_only_scope",
    "cchen_filter_strategy",
    "runtime_source_keys",
    "runtime_source_names",
    "implementation_status",
    "priority_wave",
    "recommended_frequency",
    "freshness_sla_days",
    "requires_token",
    "token_source",
    "runner_command",
    "output_targets",
    "owner",
    "visibility",
    "blocking",
    "last_updated",
    "next_update_due",
    "record_count",
    "quality_score",
    "last_run_status",
    "estado_planilla",
    "comentarios_fena",
    "comentarios_bastian",
    "comentario_excel_fernanda",
    "rows_merged",
    "match_notes",
    "gap_summary",
]

API_PRIORITY_COLUMNS = [
    "source_key",
    "source_name",
    "categoria",
    "subcategoria",
    "acceso",
    "api_url",
    "cchen_filter_strategy",
    "comentario_excel_fernanda",
    "implementation_status",
    "priority_wave",
    "recommended_frequency",
    "freshness_sla_days",
    "runtime_source_keys",
    "requires_token",
    "runner_command",
    "gap_summary",
]

GAP_COLUMNS = [
    "gap_id",
    "source_key",
    "source_name",
    "gap_type",
    "severity",
    "description",
    "recommended_action",
    "owner",
    "blocks_adjudication",
]

FIRST_WAVE_NAMES = {
    "crossref",
    "orcid",
    "pubmed",
    "europe pmc",
    "inspire",
    "semantic scholar",
    "arxiv",
    "datacite",
    "openaire",
    "patentsview",
    "uspto",
    "altmetric",
    "unpaywall",
    "zenodo",
}

SECOND_WAVE_NAMES = {
    "base",
    "doaj",
    "core",
    "biorxiv",
    "medrxiv",
    "figshare",
    "hal",
    "pubchem",
    "uniprot",
    "string db",
    "wipo patentscope",
    "epo ops",
    "espacenet",
}

COMMERCIAL_OR_ACCESS_REVIEW = {
    "scopus",
    "web of science",
    "ieee xplore",
    "dimensions",
    "jstor",
    "ahrefs",
    "semrush",
    "google patents",
    "g2",
    "the lens",
    "drugbank",
    "openweathermap",
    "iqair airvisual",
    "product hunt",
}

RUNTIME_ALIAS_BY_MATRIX_NAME = {
    "crossref": ["crossref"],
    "orcid": ["orcid"],
    "pubmed": ["pubmed_works"],
    "europe pmc": ["europmc_works"],
    "inspire": ["inspire_works"],
    "semantic scholar": ["semantic_scholar"],
    "arxiv": ["arxiv_monitor", "arxiv_works"],
    "datacite": ["datacite_outputs"],
    "zenodo": ["zenodo_outputs"],
    "patentsview": ["patentsview_uspto"],
    "uspto": ["patentsview_uspto"],
    "unpaywall": ["unpaywall_oa"],
}

RUNTIME_ONLY_CATEGORY = {
    "openalex_publicaciones": "Cientifica",
    "openalex_conceptos": "Cientifica",
    "openaire_outputs": "Cientifica",
    "altmetric": "Cientifica",
    "unpaywall_oa": "Cientifica",
    "citation_graph": "Cientifica",
    "openalex_citations": "Cientifica",
    "datos_gob_convenios": "Datos institucionales",
    "datos_gob_acuerdos": "Datos institucionales",
    "convocatorias_curadas": "Vigilancia",
    "matching_institucional": "Vigilancia",
    "iaea_inis_monitor": "Vigilancia",
    "news_monitor": "Vigilancia",
    "capital_humano": "Datos internos",
    "dian_publications": "Datos internos",
    "entity_registry_personas": "Gobernanza",
    "entity_registry_proyectos": "Gobernanza",
    "entity_registry_convocatorias": "Gobernanza",
    "entity_links": "Gobernanza",
    "fernanda_free_api_candidates": "Gobernanza",
    "radiofarmacia_cchen_seeded": "Bio/Farma",
    "zenodo_outputs": "Cientifica",
}

SUGGESTED_MATRIX_RUNNERS = {
    "unpaywall": {
        "runner_command": "python Scripts/enrich_unpaywall.py --email $CCHEN_CONTACT_EMAIL",
        "output_targets": '["Data/Publications/cchen_unpaywall_oa.csv"]',
        "gap_summary": "Script existente; falta registrar runtime y migracion si se publica en BBDD.",
    }
}

FREQUENCY_DAYS = {
    "diaria": 1,
    "semanal": 7,
    "quincenal": 14,
    "mensual": 30,
    "trimestral": 90,
    "semestral": 180,
    "anual": 365,
}


def _text(value: object) -> str:
    if value is None:
        return ""
    return " ".join(str(value).replace("\xa0", " ").split()).strip()


def _strip_accents(value: str) -> str:
    return "".join(
        char
        for char in unicodedata.normalize("NFKD", value)
        if not unicodedata.combining(char)
    )


def _norm(value: object) -> str:
    text = _strip_accents(_text(value)).lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _slug(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "_", _norm(value)).strip("_") or "source"


def _yes(value: object) -> bool:
    return _norm(value) in {"si", "yes", "true", "1"}


def _bool(value: object) -> bool:
    return _norm(value) in {"si", "yes", "true", "1"}


def _unique_join(values: list[object], sep: str = "; ") -> str:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        text = _text(value)
        if not text:
            continue
        for chunk in str(text).split(";"):
            clean = _text(chunk)
            key = _norm(clean)
            if clean and key not in seen:
                out.append(clean)
                seen.add(key)
    return sep.join(out)


def _domain(value: object) -> str:
    text = _text(value)
    if not text:
        return ""
    parsed = urlparse(text if "://" in text else f"https://{text}")
    return parsed.netloc.replace("www.", "").lower()


def _resolve_matrix_path(path: Path) -> Path:
    if path.exists():
        return path
    if path == DEFAULT_MATRIX_PATH and ALT_MATRIX_PATH.exists():
        return ALT_MATRIX_PATH
    raise FileNotFoundError(f"No se encontro la matriz: {path}")


def _xlsx_target(target: str) -> str:
    target = target.lstrip("/")
    return target if target.startswith("xl/") else f"xl/{target}"


def _col_number(cell_ref: str) -> int:
    letters = "".join(char for char in cell_ref if char.isalpha())
    number = 0
    for char in letters:
        number = number * 26 + ord(char.upper()) - 64
    return number


def _read_shared_strings(zf: ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in zf.namelist():
        return []
    root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
    shared: list[str] = []
    for item in root.findall("a:si", XLSX_NS):
        shared.append("".join(node.text or "" for node in item.findall(".//a:t", XLSX_NS)))
    return shared


def _cell_value(cell: ET.Element, shared: list[str]) -> str:
    cell_type = cell.attrib.get("t")
    if cell_type == "inlineStr":
        return "".join(node.text or "" for node in cell.findall(".//a:t", XLSX_NS))
    value = cell.find("a:v", XLSX_NS)
    if value is None:
        return ""
    raw = value.text or ""
    if cell_type == "s":
        try:
            return shared[int(raw)]
        except Exception:
            return raw
    return raw


def read_xlsx_sheet(path: Path, sheet_name: str) -> list[list[str]]:
    with ZipFile(path) as zf:
        shared = _read_shared_strings(zf)
        workbook = ET.fromstring(zf.read("xl/workbook.xml"))
        rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
        relmap = {rel.attrib["Id"]: rel.attrib["Target"] for rel in rels.findall("rel:Relationship", REL_NS)}
        for sheet in workbook.find("a:sheets", XLSX_NS).findall("a:sheet", XLSX_NS):
            if sheet.attrib["name"] != sheet_name:
                continue
            rel_id = sheet.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]
            root = ET.fromstring(zf.read(_xlsx_target(relmap[rel_id])))
            rows: list[list[str]] = []
            for row in root.findall(".//a:sheetData/a:row", XLSX_NS):
                values: list[str] = []
                current = 1
                for cell in row.findall("a:c", XLSX_NS):
                    number = _col_number(cell.attrib.get("r", "A1"))
                    while current < number:
                        values.append("")
                        current += 1
                    values.append(_text(_cell_value(cell, shared)))
                    current = number + 1
                rows.append(values)
            return rows
    raise ValueError(f"No se encontro la hoja {sheet_name!r} en {path}")


def load_matrix(path: Path) -> list[dict[str, str]]:
    rows = read_xlsx_sheet(path, "Fuentes de Datos")
    if not rows:
        return []
    header = [_norm(value) for value in rows[0]]
    header_map = {
        "categoria": "categoria",
        "subcategoria": "subcategoria",
        "fuente base de datos": "source_name",
        "especialidad": "especialidad",
        "acceso": "acceso",
        "sitio web": "site_url",
        "api disponible": "api_available",
        "url api": "api_url",
        "estado de implementacion": "estado_planilla",
        "comentarios fena": "comentarios_fena",
        "comentarios bastian": "comentarios_bastian",
    }
    records: list[dict[str, str]] = []
    for index, values in enumerate(rows[1:], start=2):
        if not any(values):
            continue
        record = {column: "" for column in RAW_COLUMNS}
        record["matrix_row"] = str(index)
        for position, raw_header in enumerate(header):
            target = header_map.get(raw_header)
            if not target:
                continue
            record[target] = _text(values[position] if position < len(values) else "")
        if record["source_name"]:
            records.append(record)
    return records


def load_runtime(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _runtime_lookup(runtime_rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {row["source_key"]: row for row in runtime_rows if row.get("source_key")}


def _match_runtime(record: dict[str, str], runtime_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    source_norm = _norm(record.get("source_name"))
    aliases = RUNTIME_ALIAS_BY_MATRIX_NAME.get(source_norm, [])
    by_key = _runtime_lookup(runtime_rows)
    matches = [by_key[key] for key in aliases if key in by_key]
    if matches:
        return matches

    source_tokens = set(source_norm.split())
    api_domain = _domain(record.get("api_url"))
    site_domain = _domain(record.get("site_url"))
    for row in runtime_rows:
        if row.get("source_key") == "fernanda_free_api_candidates":
            continue
        runtime_name = _norm(row.get("source_name"))
        runtime_key = _norm(row.get("source_key"))
        runtime_url = _domain(row.get("url"))
        if source_norm and source_norm in {runtime_name, runtime_key}:
            matches.append(row)
        elif source_norm and runtime_name and (source_norm in runtime_name or runtime_name in source_norm):
            if len(source_norm) > 4 and len(runtime_name) > 4:
                matches.append(row)
        elif api_domain and runtime_url and (api_domain == runtime_url or api_domain.endswith(runtime_url) or runtime_url.endswith(api_domain)):
            matches.append(row)
        elif site_domain and runtime_url and (site_domain == runtime_url or site_domain.endswith(runtime_url) or runtime_url.endswith(site_domain)):
            matches.append(row)
        elif len(source_tokens) == 1 and next(iter(source_tokens), "") in runtime_name.split():
            matches.append(row)
    unique: dict[str, dict[str, str]] = {}
    for match in matches:
        unique[match["source_key"]] = match
    return list(unique.values())


def _matrix_groups(records: list[dict[str, str]]) -> list[dict[str, str]]:
    groups: dict[str, list[dict[str, str]]] = {}
    for record in records:
        groups.setdefault(_slug(record["source_name"]), []).append(record)

    collapsed: list[dict[str, str]] = []
    for key, rows in groups.items():
        base = rows[0].copy()
        base["source_key"] = key
        base["categoria"] = _unique_join([row["categoria"] for row in rows])
        base["subcategoria"] = _unique_join([row["subcategoria"] for row in rows])
        base["especialidad"] = _unique_join([row["especialidad"] for row in rows])
        base["acceso"] = _unique_join([row["acceso"] for row in rows])
        base["site_url"] = _unique_join([row["site_url"] for row in rows])
        base["api_available"] = "Si" if any(_yes(row["api_available"]) for row in rows) else "No"
        base["api_url"] = _unique_join([row["api_url"] for row in rows])
        base["estado_planilla"] = _unique_join([row["estado_planilla"] for row in rows])
        base["comentarios_fena"] = _unique_join([row["comentarios_fena"] for row in rows])
        base["comentarios_bastian"] = _unique_join([row["comentarios_bastian"] for row in rows])
        base["rows_merged"] = "; ".join(row["matrix_row"] for row in rows)
        collapsed.append(base)
    return sorted(collapsed, key=lambda row: (_norm(row["categoria"]), _norm(row["source_name"])))


def _runtime_join(matches: list[dict[str, str]], field: str) -> str:
    return _unique_join([row.get(field, "") for row in matches])


def _default_frequency(record: dict[str, str], status: str) -> tuple[str, str]:
    source_norm = _norm(record.get("source_name"))
    category_norm = _norm(record.get("categoria"))
    sub_norm = _norm(record.get("subcategoria"))

    if status.startswith("diferida"):
        return "por definir", ""
    if not _yes(record.get("api_available")):
        return "manual/anual", "365"
    if source_norm in FIRST_WAVE_NAMES:
        if source_norm in {"pubmed", "europe pmc", "inspire", "datacite", "openaire", "unpaywall"}:
            return "semestral", "180"
        if source_norm in {"patentsview", "uspto"}:
            return "semestral", "180"
        return "trimestral", "90"
    if source_norm in SECOND_WAVE_NAMES:
        return "semestral", "180"
    if "patente" in category_norm:
        return "semestral", "180"
    if "cientifica" in category_norm or "repositorios" in sub_norm:
        return "trimestral", "90"
    return "semestral", "180"


def _visibility(record: dict[str, str], matches: list[dict[str, str]]) -> str:
    runtime_visibility = _runtime_join(matches, "visibility")
    if runtime_visibility:
        return runtime_visibility
    access_norm = _norm(record.get("acceso"))
    if any(term in access_norm for term in ["pago", "freemium", "restringido"]):
        return "operador"
    return "publico"


def _requires_token(record: dict[str, str], matches: list[dict[str, str]]) -> tuple[bool, str]:
    token_sources = [row.get("token_source", "") for row in matches if _bool(row.get("requires_token"))]
    source_norm = _norm(record.get("source_name"))
    access_norm = _norm(record.get("acceso"))
    if token_sources:
        return True, _unique_join(token_sources)
    if source_norm in COMMERCIAL_OR_ACCESS_REVIEW:
        return True, "credencial/subscripcion por validar"
    if any(term in access_norm for term in ["pago", "freemium", "restringido"]):
        return True, "credencial/subscripcion por validar"
    return False, ""


def _implementation_status(record: dict[str, str], matches: list[dict[str, str]]) -> str:
    source_norm = _norm(record.get("source_name"))
    access_norm = _norm(record.get("acceso"))
    if matches:
        enabled = any(_bool(row.get("enabled")) for row in matches)
        command = any(_text(row.get("runner_command")) for row in matches)
        if enabled and command:
            return "implementada_runtime"
        if enabled:
            return "registrada_sin_runner"
        return "registrada_diferida"
    if source_norm in SUGGESTED_MATRIX_RUNNERS and not matches:
        return "casi_lista_sin_runtime"
    if source_norm in COMMERCIAL_OR_ACCESS_REVIEW or any(term in access_norm for term in ["pago", "freemium", "restringido"]):
        return "diferida_acceso_pago_token"
    if source_norm in FIRST_WAVE_NAMES:
        return "primera_ola_pendiente"
    if source_norm in SECOND_WAVE_NAMES:
        return "segunda_ola_candidata"
    if _yes(record.get("api_available")):
        return "api_revisar_relevancia"
    return "manual_sin_api"


def _priority_wave(record: dict[str, str], status: str) -> str:
    source_norm = _norm(record.get("source_name"))
    if status in {"implementada_runtime", "casi_lista_sin_runtime", "primera_ola_pendiente"} and (
        source_norm in FIRST_WAVE_NAMES or source_norm in SUGGESTED_MATRIX_RUNNERS
    ):
        return "1_primera_ola"
    if status == "registrada_diferida":
        return "diferida"
    if status == "segunda_ola_candidata" or source_norm in SECOND_WAVE_NAMES:
        return "2_segunda_ola"
    if status == "api_revisar_relevancia":
        return "3_revision"
    if status.startswith("diferida"):
        return "diferida"
    return "manual_no_api"


def _gap_summary(record: dict[str, str], matches: list[dict[str, str]], status: str) -> str:
    source_norm = _norm(record.get("source_name"))
    if source_norm in SUGGESTED_MATRIX_RUNNERS and not matches:
        return SUGGESTED_MATRIX_RUNNERS[source_norm]["gap_summary"]
    if status == "implementada_runtime":
        if any(_text(row.get("last_run_status")) == "failed" for row in matches):
            token_sources = [_text(row.get("token_source")) for row in matches if _bool(row.get("requires_token")) and _text(row.get("token_source"))]
            if token_sources:
                return f"Registrada con runner, pero ultima corrida fallo; validar credencial {', '.join(sorted(set(token_sources)))}."
            return "Registrada con runner, pero ultima corrida fallo; revisar error y reintentar refresh."
        if any(_text(row.get("last_run_status")) == "not_run" for row in matches):
            return "Registrada con runner, pero sin corrida exitosa registrada."
        return "Sin brecha critica de implementacion; validar frescura y calidad."
    if status == "registrada_diferida":
        return "Registrada en runtime pero deshabilitada; requiere decision de activacion."
    if status == "primera_ola_pendiente":
        return "Fuente prioritaria sin runtime; falta extractor, outputs y migracion si aplica."
    if status == "segunda_ola_candidata":
        return "Candidata de segunda ola; requiere validacion de relevancia CCHEN y diseno de extractor."
    if status.startswith("diferida"):
        return "Diferida por costo, token comercial, freemium o acceso restringido."
    if status == "api_revisar_relevancia":
        return "API disponible, pero no priorizada; requiere evaluacion tematica."
    return "Sin API documentada; documentar como fuente manual o de vigilancia editorial."


def _source_comment(record: dict[str, str], status: str) -> str:
    source_norm = _norm(record.get("source_name"))
    name = source_norm
    if "crossref" in name:
        return "Implementada. Util para enriquecer DOI CCHEN con metadatos, referencias y funding; mantener frecuencia trimestral."
    if "orcid" in name:
        return "Implementada. Util para perfiles de investigadores CCHEN; mantener frecuencia semestral."
    if "pubmed" in name or "europe pmc" in name:
        return "Implementada. Mantener solo resultados asociados a autores, afiliaciones o DOI CCHEN; frecuencia semestral."
    if "inspire" in name or "arxiv" in name or "semantic scholar" in name:
        return "Implementada. Util para fisica, preprints y metadatos academicos; revisar relevancia CCHEN y falsos positivos."
    if "datacite" in name or "openaire" in name:
        return "Implementada o preservada en runtime. Util para outputs, datasets y produccion asociada a ORCID/ROR CCHEN."
    if "zenodo" in name:
        return "Implementada metadata-only. Util para datasets y outputs CCHEN en Zenodo; no descarga archivos, solo inventario y curaduria."
    if "unpaywall" in name:
        return "Implementada en runtime. Prioridad alta por ser gratuita y enriquecer acceso abierto desde DOI CCHEN."
    if "patentsview" in name or "uspto" in name:
        return "Registrada, pero requiere PATENTSVIEW_API_KEY para corrida exitosa; separar de INAPI local."
    if source_norm in {"base", "doaj", "core", "figshare", "hal", "biorxiv", "medrxiv"}:
        return "API gratuita candidata. Implementar solo si el filtro CCHEN entrega resultados relevantes; revisar estado del probe CCHEN-only."
    if source_norm in {"pubchem", "uniprot", "string", "string db"}:
        return "API gratuita candidata Bio/Farma. Requiere validacion tematica: activar si hay relacion con radiofarmacos, moleculas, proteinas o lineas CCHEN."
    if source_norm in {"epo ops", "espacenet", "wipo patentscope"}:
        return "API gratuita/candidata para patentes. Priorizar despues de resolver PatentsView e INAPI."
    if any(term in name for term in ["scopus", "web of science", "ieee", "jstor", "nature", "dimensions"]):
        return "Fuente valiosa pero de pago o con acceso institucional. Documentar, no bloquear implementacion."
    if "google patents" in name:
        return "No tratar como gratuito institucional si depende de SerpAPI u otro servicio externo/pago. Diferida."
    if any(term in name for term in ["ahrefs", "semrush", "g2", "product hunt"]):
        return "No prioritaria para CCHEN I+D en esta fase; freemium/pago y baja relevancia directa."
    if status.startswith("diferida"):
        return "Documentar como diferida por pago, token comercial, freemium o acceso restringido; no bloquea adjudicacion."
    if status == "segunda_ola_candidata":
        return "Candidata gratuita con API; probar filtro CCHEN antes de cualquier extraccion recurrente."
    if _yes(record.get("api_available")):
        return "API disponible, pero debe validarse capacidad de filtrar por CCHEN, afiliacion, autor, DOI, ORCID, ROR o aliases."
    return "Fuente manual o sin API documentada; mantener como referencia, no como prioridad tecnica pre-adjudicacion."


def _cchen_filter_strategy(record: dict[str, str], matches: list[dict[str, str]], status: str) -> str:
    source_norm = _norm(record.get("source_name"))
    runtime_keys = {row.get("source_key", "") for row in matches}
    if source_norm in {"crossref", "altmetric", "unpaywall"} or runtime_keys & {"crossref", "altmetric", "unpaywall_oa"}:
        return "DOI CCHEN conocido; no se consulta universo completo."
    if source_norm == "orcid" or "orcid" in runtime_keys:
        return "Afiliacion/nombre investigador CCHEN y ORCID conocido."
    if source_norm in {"pubmed", "europe pmc", "inspire", "arxiv", "semantic scholar"} or runtime_keys & {"pubmed_works", "europmc_works", "inspire_works", "arxiv_works", "semantic_scholar"}:
        return "Aliases CCHEN, autores/afiliaciones o DOI ya conocidos; revisar falsos positivos."
    if source_norm in {"datacite", "openaire"} or runtime_keys & {"datacite_outputs", "openaire_outputs"}:
        return "ORCID/ROR/DOI CCHEN y metadatos de outputs institucionales."
    if source_norm == "zenodo" or "zenodo_outputs" in runtime_keys:
        return "Aliases institucionales CCHEN visibles en afiliacion o metadatos; metadata-only, sin descarga de archivos."
    if source_norm in {"patentsview", "uspto"} or "patentsview_uspto" in runtime_keys:
        return "Aliases de solicitante/inventor CCHEN; requiere PATENTSVIEW_API_KEY."
    if source_norm in SECOND_WAVE_NAMES:
        return "Probe CCHEN-only por alias institucional; activar solo con resultados relevantes."
    if status.startswith("diferida"):
        return "No se extrae en esta fase; documentada por pago/acceso/token."
    if _yes(record.get("api_available")):
        return "Filtro CCHEN por validar antes de implementar."
    return "Sin API; eventual carga manual/curada."


def build_catalog(matrix_records: list[dict[str, str]], runtime_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    catalog: list[dict[str, str]] = []
    matched_runtime_keys: set[str] = set()

    for record in _matrix_groups(matrix_records):
        matches = _match_runtime(record, runtime_rows)
        matched_runtime_keys.update(row["source_key"] for row in matches)
        status = _implementation_status(record, matches)
        priority = _priority_wave(record, status)
        if matches:
            frequency = _runtime_join(matches, "update_frequency")
            sla = _runtime_join(matches, "freshness_sla_days")
        else:
            frequency, sla = _default_frequency(record, status)
        requires_token, token_source = _requires_token(record, matches)
        suggested = SUGGESTED_MATRIX_RUNNERS.get(_norm(record["source_name"]), {})
        source_key = record["source_key"]
        runtime_keys = _runtime_join(matches, "source_key")
        if len(matches) == 1:
            source_key = matches[0]["source_key"]
        filter_strategy = _cchen_filter_strategy(record, matches, status)
        catalog.append({
            "source_key": source_key,
            "source_name": record["source_name"],
            "origen": "matriz_fernanda",
            "categoria": record["categoria"],
            "subcategoria": record["subcategoria"],
            "especialidad": record["especialidad"],
            "acceso": record["acceso"],
            "site_url": record["site_url"],
            "api_available": "True" if _yes(record["api_available"]) else "False",
            "api_url": record["api_url"],
            "cchen_only_scope": "True",
            "cchen_filter_strategy": filter_strategy,
            "runtime_source_keys": runtime_keys,
            "runtime_source_names": _runtime_join(matches, "source_name"),
            "implementation_status": status,
            "priority_wave": priority,
            "recommended_frequency": frequency,
            "freshness_sla_days": sla,
            "requires_token": "True" if requires_token else "False",
            "token_source": token_source,
            "runner_command": _runtime_join(matches, "runner_command") or suggested.get("runner_command", ""),
            "output_targets": _runtime_join(matches, "output_targets") or suggested.get("output_targets", ""),
            "owner": _runtime_join(matches, "owner") or "observatorio-cchen",
            "visibility": _visibility(record, matches),
            "blocking": _runtime_join(matches, "blocking") or "False",
            "last_updated": _runtime_join(matches, "last_updated"),
            "next_update_due": _runtime_join(matches, "next_update_due"),
            "record_count": _runtime_join(matches, "record_count"),
            "quality_score": _runtime_join(matches, "quality_score"),
            "last_run_status": _runtime_join(matches, "last_run_status"),
            "estado_planilla": record["estado_planilla"],
            "comentarios_fena": record["comentarios_fena"],
            "comentarios_bastian": record["comentarios_bastian"],
            "comentario_excel_fernanda": _source_comment(record, status),
            "rows_merged": record.get("rows_merged", record.get("matrix_row", "")),
            "match_notes": f"runtime_match={runtime_keys or 'no'}",
            "gap_summary": _gap_summary(record, matches, status),
        })

    for row in runtime_rows:
        if row["source_key"] in matched_runtime_keys:
            continue
        enabled = _bool(row.get("enabled"))
        command = bool(_text(row.get("runner_command")))
        if enabled and command:
            status = "implementada_runtime"
        elif enabled:
            status = "registrada_sin_runner"
        else:
            status = "registrada_diferida"
        catalog.append({
            "source_key": row["source_key"],
            "source_name": row.get("source_name", row["source_key"]),
            "origen": "runtime_existente",
            "categoria": RUNTIME_ONLY_CATEGORY.get(row["source_key"], "Runtime existente"),
            "subcategoria": "",
            "especialidad": row.get("description", ""),
            "acceso": "Abierto" if not _bool(row.get("requires_token")) else "Restringido",
            "site_url": row.get("url", ""),
            "api_available": "True" if row.get("url") else "False",
            "api_url": row.get("url", ""),
            "cchen_only_scope": "True",
            "cchen_filter_strategy": "Runtime existente preservado; se asume filtro CCHEN propio de la fuente.",
            "runtime_source_keys": row["source_key"],
            "runtime_source_names": row.get("source_name", ""),
            "implementation_status": status,
            "priority_wave": "1_primera_ola" if row["source_key"] in {"openaire_outputs", "altmetric", "openalex_publicaciones"} else "runtime_base",
            "recommended_frequency": row.get("update_frequency", ""),
            "freshness_sla_days": row.get("freshness_sla_days", ""),
            "requires_token": "True" if _bool(row.get("requires_token")) else "False",
            "token_source": row.get("token_source", ""),
            "runner_command": row.get("runner_command", ""),
            "output_targets": row.get("output_targets", ""),
            "owner": row.get("owner", "observatorio-cchen"),
            "visibility": row.get("visibility", "publico"),
            "blocking": row.get("blocking", "False"),
            "last_updated": row.get("last_updated", ""),
            "next_update_due": row.get("next_update_due", ""),
            "record_count": row.get("record_count", ""),
            "quality_score": row.get("quality_score", ""),
            "last_run_status": row.get("last_run_status", ""),
            "estado_planilla": "",
            "comentarios_fena": "",
            "comentarios_bastian": "",
            "comentario_excel_fernanda": "Fuente runtime preservada para no perder cobertura operativa CCHEN.",
            "rows_merged": "",
            "match_notes": "runtime_only_preserved",
            "gap_summary": "Fuente existente en runtime no listada en la matriz; se preserva para no perder cobertura operativa.",
        })
    return sorted(catalog, key=lambda row: (row["priority_wave"], row["categoria"], row["source_name"]))


def parse_date(value: object) -> dt.date | None:
    text = _text(value)
    if not text:
        return None
    try:
        return dt.date.fromisoformat(text[:10])
    except ValueError:
        return None


def is_due(row: dict[str, str], today: dt.date) -> tuple[bool, str]:
    if not _bool(row.get("enabled")):
        return False, ""
    next_due = parse_date(row.get("next_update_due"))
    if next_due is None:
        last_updated = parse_date(row.get("last_updated"))
        if last_updated is not None:
            days = FREQUENCY_DAYS.get(_norm(row.get("update_frequency")), 0)
            if not days:
                try:
                    days = int(row.get("freshness_sla_days") or 0)
                except ValueError:
                    days = 0
            if days:
                next_due = last_updated + dt.timedelta(days=days)
    if next_due is None:
        return True, "sin fecha"
    if next_due <= today:
        return True, str((today - next_due).days)
    return False, ""


def _quality_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def build_gaps(
    catalog: list[dict[str, str]],
    runtime_rows: list[dict[str, str]],
    quality_rows: list[dict[str, str]],
    today: dt.date,
    preflight: dict[str, object],
) -> list[dict[str, str]]:
    gaps: list[dict[str, str]] = []

    def add(source_key: str, source_name: str, gap_type: str, severity: str, description: str, action: str, *, block: bool = False) -> None:
        gaps.append({
            "gap_id": f"gap_{len(gaps) + 1:03d}",
            "source_key": source_key,
            "source_name": source_name,
            "gap_type": gap_type,
            "severity": severity,
            "description": description,
            "recommended_action": action,
            "owner": "observatorio-cchen",
            "blocks_adjudication": "True" if block else "False",
        })

    for package_name, ok in preflight.get("imports", {}).items():
        if not ok:
            add(
                "entorno_local",
                package_name,
                "preflight_entorno",
                "alta",
                f"Dependencia Python no disponible: {package_name}.",
                "Instalar dependencias declaradas antes de ejecutar runners o migraciones.",
                block=True,
            )
    if preflight.get("dry_run_returncode") not in {0, None}:
        add(
            "run_source_refresh",
            "Runner canonico",
            "preflight_runner",
            "alta",
            "El dry-run del runner canonico fallo.",
            "Revisar dependencias y ejecutar `python Scripts/run_source_refresh.py --all-due --dry-run` hasta estado OK.",
            block=True,
        )

    for row in runtime_rows:
        due, days_late = is_due(row, today)
        if due:
            severity = "alta" if _bool(row.get("blocking")) else "media"
            add(
                row["source_key"],
                row.get("source_name", row["source_key"]),
                "frescura_vencida",
                severity,
                f"Fuente vencida al {today.isoformat()} ({days_late} dias de atraso).",
                "Ejecutar refresh focalizado, validar outputs y actualizar runtime.",
                block=_bool(row.get("blocking")),
            )
        if row["source_key"] == "patentsview_uspto" and _text(row.get("last_run_status")) == "not_run":
            add(
                row["source_key"],
                row.get("source_name", row["source_key"]),
                "sin_corrida",
                "media",
                "PatentsView/USPTO esta registrado, pero sin corrida registrada.",
                "Confirmar PATENTSVIEW_API_KEY y ejecutar extractor; mantener INAPI como fuente local separada.",
            )
        if row["source_key"] == "dian_publications" and _text(row.get("record_count")) in {"", "0"}:
            add(
                row["source_key"],
                row.get("source_name", row["source_key"]),
                "conteo_runtime",
                "alta",
                "Publicaciones DIAN tiene Excel disponible, pero record_count runtime aparece en 0.",
                "Verificar migracion DIAN, conteo de registros y salida de la tabla destino.",
            )

    for row in catalog:
        if row["implementation_status"] in {"primera_ola_pendiente", "casi_lista_sin_runtime"}:
            add(
                row["source_key"],
                row["source_name"],
                "primera_ola_sin_runtime",
                "media",
                row["gap_summary"],
                "Crear entrada runtime, extractor/output y migracion si la fuente pasa validacion final.",
            )
        elif row["implementation_status"] == "segunda_ola_candidata":
            add(
                row["source_key"],
                row["source_name"],
                "segunda_ola_por_validar",
                "baja",
                row["gap_summary"],
                "Evaluar relevancia CCHEN y estimar costo de implementacion antes de activar.",
            )

    for row in quality_rows:
        if _text(row.get("estado")) == "ADVERTENCIA":
            add(
                row.get("archivo", "calidad_datos"),
                row.get("fuente", "Calidad de datos"),
                "calidad_advertencia",
                "media",
                _text(row.get("alertas")) or "Advertencia de calidad sin detalle.",
                "Documentar causa, aceptar explicitamente o corregir antes del traspaso.",
            )
        elif _text(row.get("estado")) == "CRITICO":
            add(
                row.get("archivo", "calidad_datos"),
                row.get("fuente", "Calidad de datos"),
                "calidad_critica",
                "critica",
                _text(row.get("alertas")) or "Critico de calidad sin detalle.",
                "Corregir antes de entregar paquete a consultora.",
                block=True,
            )
    return gaps


def write_csv(path: Path, rows: list[dict[str, str]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def run_preflight(run_date: dt.date, run_dry_run: bool) -> dict[str, object]:
    imports = {
        "dotenv": importlib.util.find_spec("dotenv") is not None,
        "openpyxl": importlib.util.find_spec("openpyxl") is not None,
        "pandas": importlib.util.find_spec("pandas") is not None,
        "supabase": importlib.util.find_spec("supabase") is not None,
    }
    result: dict[str, object] = {"imports": imports, "dry_run_returncode": None, "dry_run_stdout": "", "dry_run_stderr": ""}
    if not run_dry_run:
        return result
    command = [sys.executable, "Scripts/run_source_refresh.py", "--all-due", "--dry-run"]
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    result["dry_run_returncode"] = completed.returncode
    result["dry_run_stdout"] = completed.stdout
    result["dry_run_stderr"] = completed.stderr
    dry_run_log = REPORTS_DIR / f"preflight_source_refresh_dry_run_{run_date.isoformat()}.txt"
    dry_run_log.write_text(completed.stdout + ("\nSTDERR:\n" + completed.stderr if completed.stderr else ""), encoding="utf-8")
    result["dry_run_log"] = str(dry_run_log.relative_to(ROOT))
    return result


def run_quality(run_date: dt.date, enabled: bool) -> tuple[Path | None, list[dict[str, str]]]:
    if not enabled:
        return None, []
    output = REPORTS_DIR / f"calidad_pre_adjudicacion_fuentes_{run_date.isoformat()}.csv"
    subprocess.run([sys.executable, "Database/data_quality.py", "--output", str(output)], cwd=ROOT, check=False)
    return output, _quality_rows(output)


def _md_table(rows: list[list[str]], headers: list[str], *, limit: int = 20) -> str:
    if not rows:
        return "_Sin registros._"
    selected = rows[:limit]
    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in selected:
        out.append("| " + " | ".join(_text(cell).replace("|", "/") for cell in row) + " |")
    if len(rows) > limit:
        out.append(f"\n_Se muestran {limit} de {len(rows)} registros._")
    return "\n".join(out)


def write_report(
    path: Path,
    matrix_path: Path,
    raw_records: list[dict[str, str]],
    catalog: list[dict[str, str]],
    api_priority: list[dict[str, str]],
    gaps: list[dict[str, str]],
    runtime_rows: list[dict[str, str]],
    quality_path: Path | None,
    quality_rows: list[dict[str, str]],
    preflight: dict[str, object],
    run_date: dt.date,
) -> None:
    access_counts = Counter(row["acceso"] for row in raw_records)
    api_rows = [row for row in raw_records if _yes(row["api_available"])]
    status_counts = Counter(row["implementation_status"] for row in catalog)
    wave_counts = Counter(row["priority_wave"] for row in catalog)
    gap_counts = Counter(row["severity"] for row in gaps)
    quality_counts = Counter(row.get("estado", "") for row in quality_rows)
    due_runtime = []
    for row in runtime_rows:
        due, days = is_due(row, run_date)
        if due:
            due_runtime.append([row["source_key"], row.get("source_name", ""), row.get("last_updated", ""), row.get("next_update_due", ""), days, row.get("blocking", "")])

    first_wave_rows = [
        [
            row["source_name"],
            row["implementation_status"],
            row["runtime_source_keys"] or "-",
            row["recommended_frequency"],
            row.get("cchen_filter_strategy", ""),
            row["gap_summary"],
        ]
        for row in catalog
        if row["priority_wave"] == "1_primera_ola"
    ]
    second_wave_rows = [
        [row["source_name"], row["categoria"], row["api_url"], row["gap_summary"]]
        for row in api_priority
        if row["priority_wave"] == "2_segunda_ola"
    ]
    top_gaps = [
        [row["severity"], row["source_key"], row["gap_type"], row["description"], row["recommended_action"]]
        for row in gaps
        if row["severity"] in {"critica", "alta", "media"}
    ]
    top_gaps.sort(key=lambda row: {"critica": 0, "alta": 1, "media": 2}.get(row[0], 3))

    import_rows = [[name, "OK" if ok else "FALTA"] for name, ok in preflight.get("imports", {}).items()]
    dry_run_status = "no ejecutado"
    if preflight.get("dry_run_returncode") is not None:
        dry_run_status = "OK" if preflight.get("dry_run_returncode") == 0 else f"FALLO {preflight.get('dry_run_returncode')}"

    lines = [
        "# Paquete pre-adjudicacion - Extraccion y catalogo de fuentes",
        "",
        f"Fecha de generacion: {run_date.isoformat()}",
        f"Matriz origen: `{matrix_path}`",
        "",
        "## Artefactos generados",
        "",
        "- `Data/Gobernanza/fuentes_informacion_fernanda_raw.csv`",
        "- `Data/Gobernanza/catalogo_fuentes_pre_adjudicacion.csv`",
        "- `Data/Gobernanza/priorizacion_fuentes_api_pre_adjudicacion.csv`",
        "- `Data/Gobernanza/brechas_fuentes_pre_adjudicacion.csv`",
        f"- `Docs/reports/comentarios_excel_fernanda_fuentes_{run_date.isoformat()}.md`",
        f"- `{quality_path.relative_to(ROOT)}`" if quality_path else "- Calidad de datos: no ejecutada en esta corrida",
        f"- `{preflight.get('dry_run_log')}`" if preflight.get("dry_run_log") else "- Dry-run del runner: no ejecutado en esta corrida",
        "",
        "## Resumen ejecutivo",
        "",
        "- Regla de extraccion: CCHEN-only. Se priorizan filtros por afiliacion, alias institucional, DOI, ORCID, ROR, autores conocidos o activos institucionales.",
        f"- Matriz cruda: {len(raw_records)} fuentes.",
        f"- Acceso: {access_counts.get('Abierto', 0)} abiertas, {access_counts.get('Freemium', 0)} freemium, {access_counts.get('Pago', 0)} de pago, {access_counts.get('Restringido', 0)} restringidas.",
        f"- API marcada en planilla: {len(api_rows)} filas; catalogo API deduplicado: {len(api_priority)} fuentes.",
        f"- Runtime existente preservado: {len(runtime_rows)} fuentes registradas.",
        f"- Catalogo reconciliado final: {len(catalog)} fuentes normalizadas.",
        f"- Brechas registradas: {len(gaps)} ({', '.join(f'{key}: {value}' for key, value in sorted(gap_counts.items())) or 'sin brechas'}).",
        "",
        "## Preflight",
        "",
        _md_table(import_rows, ["Dependencia", "Estado"], limit=10),
        "",
        f"- Dry-run `run_source_refresh.py --all-due --dry-run`: {dry_run_status}.",
        f"- Calidad de datos: {', '.join(f'{key}: {value}' for key, value in sorted(quality_counts.items())) or 'no ejecutada'}.",
        "",
        "## Estado de implementacion",
        "",
        "- Por estado: " + (", ".join(f"{key}: {value}" for key, value in sorted(status_counts.items())) or "sin registros") + ".",
        "- Por prioridad: " + (", ".join(f"{key}: {value}" for key, value in sorted(wave_counts.items())) or "sin registros") + ".",
        "",
        "## Primera ola API",
        "",
        _md_table(first_wave_rows, ["Fuente", "Estado", "Runtime", "Frecuencia", "Filtro CCHEN", "Brecha/accion"], limit=30),
        "",
        "## Segunda ola API",
        "",
        _md_table(second_wave_rows, ["Fuente", "Categoria", "API", "Accion"], limit=30),
        "",
        "## Fuentes runtime vencidas",
        "",
        _md_table(due_runtime, ["source_key", "Fuente", "last_updated", "next_due", "dias_atraso", "blocking"], limit=30),
        "",
        "## Brechas priorizadas",
        "",
        _md_table(top_gaps, ["Severidad", "source_key", "Tipo", "Descripcion", "Accion"], limit=40),
        "",
        "## Criterio de traspaso a consultora",
        "",
        "- El equipo interno mantiene la extraccion, limpieza cientifica y validacion experta.",
        "- La consultora debe integrar, desplegar, automatizar, asegurar y monitorear los pipelines priorizados.",
        "- Las fuentes de pago, restringidas o con token comercial quedan documentadas y no bloquean la adjudicacion.",
        "- Ninguna fuente nueva debe activarse si no puede limitarse a CCHEN o a semillas institucionales verificadas.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_comments_file(path: Path, catalog: list[dict[str, str]], run_date: dt.date) -> None:
    rows = [
        [
            row["source_name"],
            row["implementation_status"],
            row["priority_wave"],
            row.get("cchen_filter_strategy", ""),
            row.get("comentario_excel_fernanda", ""),
        ]
        for row in catalog
        if row.get("origen") == "matriz_fernanda"
    ]
    lines = [
        "# Comentarios para planilla Fernanda",
        "",
        f"Fecha: {run_date.isoformat()}",
        "",
        "No se modifico el Excel original. Estos comentarios estan listos para revisar/copiar si se decide anotar la planilla.",
        "",
        "## Comentario general",
        "",
        "Se priorizaran fuentes con API gratuita y capacidad de filtrar por CCHEN, afiliacion, autor, DOI, ORCID, ROR o aliases institucionales. Fuentes sin filtro claro quedan en revision para evitar ruido.",
        "",
        "## Comentarios por fuente",
        "",
        _md_table(rows, ["Fuente", "Estado", "Prioridad", "Filtro CCHEN", "Comentario"], limit=300),
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Genera paquete pre-adjudicacion de fuentes.")
    parser.add_argument("--input", type=Path, default=DEFAULT_MATRIX_PATH, help="Ruta al Excel Fuentes de informacion.xlsx")
    parser.add_argument("--date", default=dt.date.today().isoformat(), help="Fecha de corte YYYY-MM-DD")
    parser.add_argument("--run-preflight", action="store_true", help="Ejecuta dry-run no mutante del runner canonico")
    parser.add_argument("--run-quality", action="store_true", help="Ejecuta Database/data_quality.py y guarda evidencia CSV")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_date = dt.date.fromisoformat(args.date)
    matrix_path = _resolve_matrix_path(args.input)

    raw_records = load_matrix(matrix_path)
    runtime_rows = load_runtime(RUNTIME_PATH)
    catalog = build_catalog(raw_records, runtime_rows)
    api_priority = [
        {column: row.get(column, "") for column in API_PRIORITY_COLUMNS}
        for row in catalog
        if row["origen"] == "matriz_fernanda" and row["api_available"] == "True"
    ]

    preflight = run_preflight(run_date, args.run_preflight)
    quality_path, quality_rows = run_quality(run_date, args.run_quality)
    gaps = build_gaps(catalog, runtime_rows, quality_rows, run_date, preflight)

    raw_path = GOV_DIR / "fuentes_informacion_fernanda_raw.csv"
    catalog_path = GOV_DIR / "catalogo_fuentes_pre_adjudicacion.csv"
    api_path = GOV_DIR / "priorizacion_fuentes_api_pre_adjudicacion.csv"
    gaps_path = GOV_DIR / "brechas_fuentes_pre_adjudicacion.csv"
    report_path = REPORTS_DIR / f"paquete_pre_adjudicacion_fuentes_{run_date.isoformat()}.md"
    comments_path = REPORTS_DIR / f"comentarios_excel_fernanda_fuentes_{run_date.isoformat()}.md"

    write_csv(raw_path, raw_records, RAW_COLUMNS)
    write_csv(catalog_path, catalog, CATALOG_COLUMNS)
    write_csv(api_path, api_priority, API_PRIORITY_COLUMNS)
    write_csv(gaps_path, gaps, GAP_COLUMNS)
    write_comments_file(comments_path, catalog, run_date)
    write_report(
        report_path,
        matrix_path,
        raw_records,
        catalog,
        api_priority,
        gaps,
        runtime_rows,
        quality_path,
        quality_rows,
        preflight,
        run_date,
    )

    print(f"[OK] matriz cruda -> {raw_path.relative_to(ROOT)} ({len(raw_records)} filas)")
    print(f"[OK] catalogo -> {catalog_path.relative_to(ROOT)} ({len(catalog)} fuentes)")
    print(f"[OK] priorizacion API -> {api_path.relative_to(ROOT)} ({len(api_priority)} fuentes)")
    print(f"[OK] brechas -> {gaps_path.relative_to(ROOT)} ({len(gaps)} brechas)")
    print(f"[OK] comentarios Fernanda -> {comments_path.relative_to(ROOT)}")
    print(f"[OK] reporte -> {report_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
