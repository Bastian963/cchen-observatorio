#!/usr/bin/env python3
"""Generate comments and source briefs for implemented Fernanda/CCHEN sources."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import math
import re
import textwrap
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
GOV_DIR = ROOT / "Data" / "Gobernanza"
REPORTS_DIR = ROOT / "Docs" / "reports" / "fuentes_fernanda_implementadas"

DEFAULT_CATALOG = GOV_DIR / "catalogo_fuentes_pre_adjudicacion.csv"
DEFAULT_RUNTIME = GOV_DIR / "data_sources_runtime.csv"
DEFAULT_COMMENTS_CSV = GOV_DIR / "comentarios_excel_fernanda_recomendados.csv"
DEFAULT_OUTPUT_DIR = REPORTS_DIR

BRIEF_REQUIRED_SECTIONS = [
    "Ficha rapida para Fernanda",
    "Que datos ofrece la fuente",
    "Que extraemos para CCHEN",
    "Como se filtra CCHEN-only",
    "Potencial para el observatorio",
    "Debilidades y riesgos",
    "Frecuencia recomendada",
    "Estado operativo",
    "Evidencia disponible",
    "Decision",
]

DIRECT_API_KEYS = {
    "arxiv",
    "crossref",
    "datacite_outputs",
    "europmc_works",
    "inspire_works",
    "openaire_outputs",
    "orcid",
    "pubmed_works",
    "semantic_scholar",
    "unpaywall_oa",
    "zenodo_outputs",
    "openalex",
}

DERIVED_SEEDED_KEYS = {
    "radiofarmacia_cchen_seeded",
    "clinvar",
    "genbank",
    "gene_expression_omnibus_geo",
    "nih",
    "sequence_read_archive",
}

LOCAL_RUNTIME_KEYS = {
    "datos_gob_cl",
    "iaea_inis_monitor",
}

REVIEW_MATCH_KEYS = {
    "news_monitor",
}

PRIORITY_ORDER = {
    "1_primera_ola": 1,
    "2_segunda_ola": 2,
    "runtime_base": 3,
    "manual_no_api": 4,
}

UTILITY_BY_CATEGORY = {
    "bio/farma": "Vigilancia tecnica en radiofarmacia, moleculas, radionuclidos y literatura biomédica relacionada con lineas CCHEN.",
    "cientifica": "Consolidacion de produccion cientifica, metadatos, citas, acceso abierto, autores y outputs asociados a CCHEN.",
    "científica": "Consolidacion de produccion cientifica, metadatos, citas, acceso abierto, autores y outputs asociados a CCHEN.",
    "datos abiertos": "Contexto institucional y datos publicos reutilizables para indicadores comparables.",
    "datos internos": "Evidencia institucional propia para completar lo que las APIs externas no capturan.",
    "gobernanza": "Trazabilidad interna de entidades, relaciones, personas, proyectos y reglas operativas del observatorio.",
    "nuclear": "Vigilancia de informacion nuclear especializada y oportunidades tecnicas relacionadas con CCHEN.",
    "patentes": "Seguimiento de propiedad industrial, inventores, solicitantes y tecnologias relacionadas con CCHEN.",
    "runtime existente": "Fuente operacional ya integrada al observatorio; sirve como activo de continuidad y evidencia para automatizacion.",
    "vigilancia": "Seguimiento de oportunidades, noticias, alertas y matching institucional.",
}

SOURCE_USE_OVERRIDES = {
    "altmetric": "Medir atencion publica y menciones externas asociadas a DOI CCHEN.",
    "crossref": "Enriquecer DOI CCHEN con metadatos bibliograficos, referencias, abstracts y funding.",
    "datacite_outputs": "Identificar datasets y outputs con DOI vinculados a CCHEN, ORCID o ROR.",
    "europmc_works": "Complementar publicaciones biomédicas y de radiofarmacia con metadatos Europe PMC.",
    "inspire_works": "Cubrir fisica, plasma, altas energias y areas afines donde CCHEN tiene produccion.",
    "orcid": "Mantener perfiles de investigadores CCHEN, afiliaciones, identificadores y obras declaradas.",
    "openaire_outputs": "Consolidar outputs academicos europeos y repositorios vinculados a ORCID/DOI CCHEN.",
    "pubmed_works": "Capturar publicaciones biomédicas, medicina nuclear y radiofarmacia con señal CCHEN.",
    "semantic_scholar": "Complementar citas, autores y metadatos semanticos de publicaciones CCHEN.",
    "unpaywall_oa": "Determinar disponibilidad open access de DOI CCHEN.",
    "zenodo_outputs": "Inventariar metadatos de datasets, presentaciones y outputs CCHEN en Zenodo sin descargar archivos.",
    "arxiv": "Vigilar preprints y produccion temprana en física y areas afines CCHEN.",
    "patentsview_uspto": "Buscar patentes USPTO asociadas a aliases CCHEN; actualmente depende de API key.",
    "radiofarmacia_cchen_seeded": "Consolidar semillas de radiofarmacos, radionuclidos, PubChem y literatura abierta relevante.",
    "repositorios_cchen_outputs_master": "Unificar Zenodo, DOAJ, HAL y CORE en una tabla maestra auditable para tablero y consultora.",
    "fernanda_free_api_candidates": "Probar DOAJ, HAL, CORE y otras APIs gratuitas con filtros CCHEN-only.",
    "openalex": "Base principal de publicaciones, autores, conceptos y relaciones bibliométricas CCHEN.",
    "datos_gob_cl": "Datos publicos nacionales vinculados a convenios, acuerdos e informacion institucional CCHEN.",
    "iaea_inis_monitor": "Vigilancia especializada de INIS/IAEA para informacion nuclear relevante a CCHEN.",
    "news_monitor": "Monitoreo de prensa y noticias sobre CCHEN y energia nuclear; no debe confundirse con datos financieros de Google Finance.",
}

WEAKNESS_OVERRIDES = {
    "altmetric": "Puede entregar pocos registros si los DOI CCHEN no tienen atencion publica rastreada.",
    "patentsview_uspto": "Registrada, pero la corrida queda bloqueada hasta configurar PATENTSVIEW_API_KEY.",
    "fernanda_free_api_candidates": "Es una fuente de prueba/curaduria: sus resultados deben consumirse a traves de las tablas revisadas.",
    "repositorios_cchen_outputs_master": "No consulta APIs directamente; depende de que Zenodo, DOAJ, HAL y CORE se refresquen primero.",
    "radiofarmacia_cchen_seeded": "Usa semillas tematicas; ampliar semillas exige justificacion experta para evitar ruido.",
    "news_monitor": "La fila del Excel indica Google Finance, pero el runtime conectado corresponde a News monitor. Requiere confirmar si se mantiene como vigilancia de noticias o se excluye del bloque financiero.",
}

DATA_TYPOLOGY_OVERRIDES = {
    "arxiv": "Preprints, metadatos bibliograficos y vigilancia temprana",
    "crossref": "Metadatos DOI, referencias, abstracts y funding",
    "datacite_outputs": "Datasets, DOIs y outputs de investigacion",
    "europmc_works": "Publicaciones biomédicas y metadatos Europe PMC",
    "inspire_works": "Publicaciones/preprints de fisica e informacion académica especializada",
    "openaire_outputs": "Outputs académicos, repositorios y relaciones ORCID/DOI",
    "orcid": "Perfiles de investigadores, afiliaciones e identificadores",
    "pubmed_works": "Publicaciones biomédicas, medicina nuclear y radiofarmacia",
    "semantic_scholar": "Metadatos académicos, autores, citas y relaciones semanticas",
    "unpaywall_oa": "Estado de acceso abierto por DOI",
    "zenodo_outputs": "Metadatos de datasets, presentaciones y archivos asociados",
    "patentsview_uspto": "Patentes USPTO, solicitantes e inventores",
    "radiofarmacia_cchen_seeded": "Radiofarmacos, radionuclidos, compuestos PubChem y literatura técnica",
    "clinvar": "Variantes clínicas relacionadas por flujos biomédicos derivados",
    "openalex": "Publicaciones, autores, conceptos, afiliaciones y citas",
    "datos_gob_cl": "Convenios, acuerdos e informacion institucional publica",
    "genbank": "Secuencias genéticas relacionadas por flujos biomédicos derivados",
    "gene_expression_omnibus_geo": "Datos de expresion génica relacionados por flujos derivados",
    "nih": "Investigacion biomédica relacionada por flujos derivados",
    "sequence_read_archive": "Datos genómicos relacionados por flujos derivados",
    "iaea_inis_monitor": "Registros de informacion nuclear y vigilancia técnica",
    "news_monitor": "Noticias y monitoreo de prensa CCHEN/nuclear; match financiero en revision",
}

DOWNLOADED_DATA_OVERRIDES = {
    "arxiv": "CSV de vigilancia semanal y CSV de trabajos arXiv CCHEN cuando hay DOI/autor/alias asociado.",
    "crossref": "CSV enriquecido por DOI CCHEN con metadatos, referencias, abstracts y financiadores.",
    "datacite_outputs": "CSV de outputs/datasets con DOI vinculados a CCHEN, ORCID/ROR o metadatos institucionales.",
    "europmc_works": "CSV de publicaciones biomédicas filtradas por CCHEN, autores, afiliaciones o DOI conocidos.",
    "inspire_works": "CSV de trabajos académicos de fisica filtrados por señal CCHEN.",
    "openaire_outputs": "CSV de outputs académicos y repositorios asociados a identificadores CCHEN.",
    "orcid": "CSV de perfiles ORCID de investigadores CCHEN y metadatos asociados.",
    "pubmed_works": "CSV de publicaciones PubMed con señal CCHEN en DOI, autor, afiliacion o tema relevante.",
    "semantic_scholar": "CSV de metadatos/citas Semantic Scholar asociados a publicaciones CCHEN.",
    "unpaywall_oa": "CSV con estado open access por DOI CCHEN.",
    "zenodo_outputs": "CSV de metadatos Zenodo y CSV de inventario de archivos; no descarga archivos binarios.",
    "patentsview_uspto": "Salida prevista para patentes USPTO CCHEN; actualmente sin registros por falta de API key.",
    "radiofarmacia_cchen_seeded": "CSVs de semillas, compuestos/radionuclidos, literatura, curaduria y revision operativa.",
    "clinvar": "No hay extractor directo ClinVar; la evidencia viene de PubMed/radiofarmacia como aproximacion temática.",
    "openalex": "CSVs de works, authorships, conceptos, grants y tablas bibliométricas CCHEN.",
    "datos_gob_cl": "CSVs institucionales de convenios y acuerdos públicos asociados a CCHEN.",
    "genbank": "No hay extractor directo GenBank; la evidencia viene de PubMed/radiofarmacia como aproximacion temática.",
    "gene_expression_omnibus_geo": "No hay extractor directo GEO; la evidencia viene de PubMed/radiofarmacia como aproximacion temática.",
    "nih": "No hay extractor directo NIH; la evidencia viene de PubMed/radiofarmacia como aproximacion temática.",
    "sequence_read_archive": "No hay extractor directo SRA; la evidencia viene de PubMed/radiofarmacia como aproximacion temática.",
    "iaea_inis_monitor": "CSV de vigilancia INIS/IAEA con registros nucleares relevantes a CCHEN.",
    "news_monitor": "CSV de noticias CCHEN/nuclear; no corresponde a descarga financiera desde Google Finance.",
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
    slug = re.sub(r"[^a-z0-9]+", "_", _norm(value)).strip("_")
    return slug or "fuente"


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _write_csv(path: Path, rows: list[dict[str, str]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _json_list(value: str) -> list[str]:
    value = _text(value)
    if not value:
        return []
    output: list[str] = []
    parts = [value]
    if "];" in value:
        parts = [part.strip() for part in value.split(";") if part.strip()]
    for part in parts:
        try:
            parsed = json.loads(part)
            if isinstance(parsed, list):
                output.extend(_text(item) for item in parsed if _text(item))
        except json.JSONDecodeError:
            continue
    return output


def _parse_record_count(value: str) -> int:
    nums = [int(match) for match in re.findall(r"\d+", _text(value))]
    return sum(nums)


def _record_count_label(value: str) -> str:
    text = _text(value)
    if not text:
        return "0"
    if ";" in text:
        return f"outputs multiples: {text}"
    return text


def _primary_frequency(value: str) -> str:
    parts = [_text(part) for part in _text(value).split(";") if _text(part)]
    return parts[0] if parts else "sin frecuencia"


def _frequency_label(value: str) -> str:
    parts = [_text(part) for part in _text(value).split(";") if _text(part)]
    if len(parts) > 1:
        return f"{parts[0]} (otros outputs: {', '.join(parts[1:])})"
    return parts[0] if parts else "sin frecuencia"


def display_source_name(row: dict[str, str]) -> str:
    if row.get("source_key") == "news_monitor":
        return "Google Finance / News monitor (revisar match)"
    return row.get("source_name", "")


def implementation_tier(row: dict[str, str]) -> str:
    key = row.get("source_key", "")
    if key == "patentsview_uspto":
        return "bloqueada_por_token"
    if key in REVIEW_MATCH_KEYS:
        return "revisar_match_runtime"
    if key in DIRECT_API_KEYS:
        return "implementada_directa_api"
    if key in DERIVED_SEEDED_KEYS:
        return "implementada_derivada_semilla"
    if key in LOCAL_RUNTIME_KEYS:
        return "implementada_runtime_local"
    return "implementada_runtime_indirecta"


def implementation_tier_label(value: str) -> str:
    return {
        "implementada_directa_api": "Implementada directa/API",
        "implementada_derivada_semilla": "Implementada derivada/semilla",
        "implementada_runtime_local": "Implementada runtime/local",
        "implementada_runtime_indirecta": "Implementada indirecta/runtime",
        "bloqueada_por_token": "Bloqueada por token",
        "revisar_match_runtime": "Revisar match runtime",
    }.get(value, value)


def decision_code(row: dict[str, str]) -> str:
    key = row.get("source_key", "")
    if key == "patentsview_uspto":
        return "bloqueada_por_token"
    if key in REVIEW_MATCH_KEYS:
        return "revisar_match"
    if key in DERIVED_SEEDED_KEYS:
        return "mantener_con_observacion"
    return "mantener"


def data_typology(row: dict[str, str]) -> str:
    key = row.get("source_key", "")
    if key in DATA_TYPOLOGY_OVERRIDES:
        return DATA_TYPOLOGY_OVERRIDES[key]
    return row.get("especialidad") or row.get("categoria") or "Datos de apoyo al observatorio"


def downloaded_data_text(row: dict[str, str]) -> str:
    key = row.get("source_key", "")
    if key in DOWNLOADED_DATA_OVERRIDES:
        return DOWNLOADED_DATA_OVERRIDES[key]
    outputs = _json_list(row.get("output_targets", ""))
    if outputs:
        return f"Artefactos locales: {', '.join(outputs[:4])}."
    return "Sin detalle de artefactos en runtime; revisar outputs antes de publicar."


def observatory_use_text(row: dict[str, str]) -> str:
    key = row.get("source_key", "")
    if key in REVIEW_MATCH_KEYS:
        return "Solo serviria para vigilancia de noticias si se reclasifica; no usar como fuente financiera sin confirmacion."
    if key == "patentsview_uspto":
        return "Serviria para propiedad industrial internacional cuando exista API key; por ahora queda como brecha documentada."
    if key in DERIVED_SEEDED_KEYS:
        return "Sirve como evidencia temática o vigilancia exploratoria; no como indicador directo de la fuente original."
    return utility_text(row)


def operational_status_text(row: dict[str, str]) -> str:
    code = decision_code(row)
    if code == "mantener":
        return "Implementada y usable con control de calidad/frescura."
    if code == "mantener_con_observacion":
        return "Implementada como derivada/semilla; requiere nota metodologica al usarla."
    if code == "bloqueada_por_token":
        return "Registrada, pero bloqueada hasta configurar credencial/API key."
    if code == "revisar_match":
        return "Requiere confirmacion de correspondencia entre planilla y runtime."
    return "Implementada con observaciones."


def _latex_escape(value: object) -> str:
    text = _text(value)
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(char, char) for char in text)


def _wrap_md(text: str) -> str:
    text = _text(text)
    if not text:
        return "Sin informacion registrada."
    return text


def _merge_rows(rows: list[dict[str, str]]) -> dict[str, str]:
    base = dict(rows[0])
    if len(rows) == 1:
        return base
    names = []
    comments = []
    urls = []
    api_urls = []
    raw_counts = []
    for row in rows:
        for value, target in [
            (row.get("source_name", ""), names),
            (row.get("comentario_excel_fernanda", ""), comments),
            (row.get("site_url", ""), urls),
            (row.get("api_url", ""), api_urls),
            (row.get("record_count", ""), raw_counts),
        ]:
            text = _text(value)
            if text and text not in target:
                target.append(text)
    base["source_name"] = " / ".join(names) if names else base.get("source_name", "")
    base["comentario_excel_fernanda"] = " ".join(comments)
    base["site_url"] = "; ".join(urls)
    base["api_url"] = "; ".join(api_urls)
    base["record_count"] = "; ".join(raw_counts)
    base["rows_merged"] = str(len(rows))
    return base


def implemented_sources(catalog_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in catalog_rows:
        if (
            row.get("implementation_status") == "implementada_runtime"
            and row.get("origen") == "matriz_fernanda"
        ):
            grouped[row["source_key"]].append(row)
    sources = [_merge_rows(rows) for rows in grouped.values()]
    sources.sort(
        key=lambda row: (
            PRIORITY_ORDER.get(row.get("priority_wave", ""), 9),
            _norm(row.get("categoria", "")),
            _norm(row.get("source_name", "")),
        )
    )
    return sources


def clean_generated_outputs(output_dir: Path) -> None:
    """Remove stale files generated by previous runs of this package."""
    patterns = [
        "comentarios_excel_fernanda_recomendados.md",
        "indice_fuentes_priorizadas.md",
        "resumen_ejecutivo_fuentes_implementadas.md",
        "resumen_ejecutivo_fuentes_implementadas.tex",
        "resumen_ejecutivo_fuentes_implementadas.pdf",
        "resumen_ejecutivo_fuentes_implementadas.aux",
        "resumen_ejecutivo_fuentes_implementadas.log",
        "resumen_ejecutivo_fuentes_implementadas.out",
        "briefs/brief_*",
        "assets/*.png",
    ]
    for pattern in patterns:
        for path in output_dir.glob(pattern):
            if path.is_file():
                path.unlink()


def runtime_by_key(runtime_rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {row.get("source_key", ""): row for row in runtime_rows if row.get("source_key", "")}


def maturity(row: dict[str, str]) -> str:
    if row.get("source_key") in REVIEW_MATCH_KEYS:
        return "revisar_match_runtime"
    if row.get("requires_token") == "True" and row.get("last_run_status") != "success":
        return "bloqueada_token"
    if row.get("last_run_status") and _norm(row.get("last_run_status")) not in {"failed", "error"}:
        return "implementada_ok"
    if row.get("runner_command"):
        return "implementada_revisar"
    return "implementada_manual"


def maturity_label(value: str) -> str:
    return {
        "implementada_ok": "Implementada OK",
        "implementada_revisar": "Implementada, revisar ultima corrida",
        "implementada_manual": "Implementada/manual",
        "bloqueada_token": "Bloqueada por token",
        "revisar_match_runtime": "Revisar match runtime",
    }.get(value, value)


def utility_text(row: dict[str, str]) -> str:
    key = row.get("source_key", "")
    if key in SOURCE_USE_OVERRIDES:
        return SOURCE_USE_OVERRIDES[key]
    category = _norm(row.get("categoria", ""))
    if category in UTILITY_BY_CATEGORY:
        return UTILITY_BY_CATEGORY[category]
    speciality = _text(row.get("especialidad", ""))
    if speciality:
        return f"Aporta {speciality.lower()} para completar vistas del observatorio."
    return "Aporta evidencia complementaria al observatorio CCHEN."


def weakness_text(row: dict[str, str]) -> str:
    key = row.get("source_key", "")
    if key in WEAKNESS_OVERRIDES:
        return WEAKNESS_OVERRIDES[key]
    if row.get("requires_token") == "True":
        return f"Requiere credencial {row.get('token_source') or 'externa'}; sin ella no debe tratarse como fuente automatizada estable."
    if _parse_record_count(row.get("record_count", "")) == 0:
        return "Tiene conteo cero o sin evidencia reciente; requiere revision antes de usar en tablero."
    if row.get("priority_wave") == "manual_no_api":
        return "Aparece como implementada por runtime, pero su origen en la matriz no era API priorizada; mantener trazabilidad de metodo y outputs."
    return "Riesgo principal: falsos positivos si se relaja el filtro CCHEN-only o si se consume sin curaduria."


def decision_text(row: dict[str, str]) -> str:
    key = row.get("source_key", "")
    if key == "patentsview_uspto":
        return "Mantener registrada, pero no exigir corrida hasta configurar PATENTSVIEW_API_KEY; separar de INAPI local."
    if key in REVIEW_MATCH_KEYS:
        return "Revisar con Fernanda: la planilla apunta a Google Finance, pero el runtime implementado es News monitor para prensa CCHEN/nuclear. Mantener solo si se reclasifica como vigilancia de noticias."
    if key in DERIVED_SEEDED_KEYS:
        return "Mantener como fuente derivada/semilla; no presentarla como conexión directa a la fuente original hasta implementar extractor propio."
    if maturity(row) == "implementada_ok":
        return "Mantener como fuente implementada del observatorio y exigir evidencia de refresco segun frecuencia declarada."
    if _parse_record_count(row.get("record_count", "")) == 0:
        return "Mantener como implementada en revision; no promover a indicador hasta confirmar salida con registros."
    return "Mantener implementada y revisar en el proximo ciclo de calidad."


def comment_text(row: dict[str, str]) -> str:
    key = row.get("source_key", "")
    frequency = row.get("recommended_frequency") or row.get("update_frequency") or "segun SLA"
    frequency = _frequency_label(frequency)
    use = utility_text(row).rstrip(".; ")
    if key == "patentsview_uspto":
        return "Implementada/registrada para CCHEN-only, pero bloqueada hasta configurar PATENTSVIEW_API_KEY; no reemplaza INAPI local."
    if key in REVIEW_MATCH_KEYS:
        return "Revisar match: la planilla indica Google Finance, pero el runtime implementado es News monitor para prensa CCHEN/nuclear; no tratar como fuente financiera sin confirmacion."
    if key in DERIVED_SEEDED_KEYS:
        return f"Implementada como fuente derivada/semilla CCHEN-only; {use}; mantener como evidencia tecnica, no como conexion directa a la fuente original."
    if maturity(row) == "implementada_ok":
        return f"Implementada para extraccion CCHEN-only; {use}; mantener frecuencia {frequency}."
    if _parse_record_count(row.get("record_count", "")) == 0:
        return f"Implementada en runtime, pero sin registros utiles recientes; revisar salida antes de usar en tablero."
    return f"Implementada para extraccion CCHEN-only; {use}; mantener frecuencia {frequency} y revisar calidad."


def cchen_extraction_text(row: dict[str, str]) -> str:
    if row.get("source_key") in DERIVED_SEEDED_KEYS:
        return (
            "La evidencia actual proviene de flujos relacionados ya implementados "
            f"({row.get('runtime_source_names') or 'runtime CCHEN'}). No hay extractor directo propio para esta fuente."
        )
    if row.get("source_key") in REVIEW_MATCH_KEYS:
        return (
            "El artefacto existente es Data/Vigilancia/news_monitor.csv, asociado a monitoreo de prensa CCHEN/nuclear. "
            "No corresponde a una extracción financiera de Google Finance."
        )
    outputs = _json_list(row.get("output_targets", ""))
    if outputs:
        output_label = ", ".join(outputs[:3])
        if len(outputs) > 3:
            output_label += f" y {len(outputs) - 3} artefactos adicionales"
        return f"Se guardan artefactos locales trazables: {output_label}."
    return "Se conserva evidencia en el runtime/catalogo; si no hay output listado, debe verificarse el artefacto operativo antes de publicar."


def filter_text(row: dict[str, str]) -> str:
    if row.get("source_key") in REVIEW_MATCH_KEYS:
        return "Filtro del runtime: consulta/curaduria de noticias CCHEN y energia nuclear. El filtro financiero de Google Finance no esta implementado."
    strategy = row.get("cchen_filter_strategy", "")
    if strategy:
        return strategy
    return "Filtro CCHEN-only por aliases institucionales, DOI/ORCID/ROR conocidos o activos institucionales ya presentes."


def source_state(row: dict[str, str]) -> str:
    return (
        f"Estado catalogo: {row.get('implementation_status', '')}. "
        f"Ultima corrida: {row.get('last_run_status') or 'sin estado'}; "
        f"ultima actualizacion: {row.get('last_updated') or 'sin fecha'}."
    )


def evidence_text(row: dict[str, str]) -> str:
    outputs = _json_list(row.get("output_targets", ""))
    output_text = "; ".join(outputs) if outputs else "sin output_targets registrado"
    text = (
        f"Conteo registrado: {_record_count_label(row.get('record_count', ''))}. "
        f"Calidad: {row.get('quality_score') or 'sin score'}. "
        f"Outputs: {output_text}."
    )
    if ";" in _text(row.get("record_count", "")):
        text += " Los conteos corresponden a artefactos distintos; no deben sumarse como una sola tabla."
    return text


def brief_context(row: dict[str, str], assets_dir: Path) -> dict[str, str]:
    key = row["source_key"]
    return {
        "source_key": key,
        "source_name": display_source_name(row),
        "categoria": row.get("categoria", ""),
        "acceso": row.get("acceso", ""),
        "api_available": row.get("api_available", ""),
        "maturity": maturity(row),
        "maturity_label": maturity_label(maturity(row)),
        "implementation_tier": implementation_tier(row),
        "implementation_tier_label": implementation_tier_label(implementation_tier(row)),
        "decision_code": decision_code(row),
        "data_typology": data_typology(row),
        "downloaded_data": downloaded_data_text(row),
        "observatory_use": observatory_use_text(row),
        "operational_status": operational_status_text(row),
        "comment": comment_text(row),
        "data_offer": row.get("especialidad") or row.get("description") or utility_text(row),
        "cchen_extract": cchen_extraction_text(row),
        "filter": filter_text(row),
        "potential": utility_text(row),
        "weakness": weakness_text(row),
        "frequency": _frequency_label(row.get("recommended_frequency") or row.get("update_frequency") or "sin frecuencia"),
        "sla": row.get("freshness_sla_days") or "sin SLA",
        "state": source_state(row),
        "evidence": evidence_text(row),
        "decision": decision_text(row),
        "site_url": row.get("site_url", ""),
        "api_url": row.get("api_url", ""),
        "record_count_total": str(_parse_record_count(row.get("record_count", ""))),
        "record_count_label": _record_count_label(row.get("record_count", "")),
        "chart_path": f"../assets/{key}_resumen.png",
    }


def plot_source_card(row: dict[str, str], assets_dir: Path) -> Path:
    key = row["source_key"]
    path = assets_dir / f"{key}_resumen.png"
    assets_dir.mkdir(parents=True, exist_ok=True)
    count = _parse_record_count(row.get("record_count", ""))
    mat = maturity(row)
    color = {
        "implementada_ok": "#2E7D32",
        "implementada_revisar": "#F9A825",
        "implementada_manual": "#1565C0",
        "bloqueada_token": "#C62828",
    }.get(mat, "#6F6F6F")

    fig, ax = plt.subplots(figsize=(8.5, 2.5))
    ax.axis("off")
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.add_patch(plt.Rectangle((2, 64), 18, 18, color=color, alpha=0.9))
    ax.text(24, 73, maturity_label(mat), va="center", ha="left", fontsize=11, weight="bold", color="#333333")
    ax.text(2, 48, f"Fuente: {display_source_name(row)}", fontsize=11, weight="bold", color="#483888")
    ax.text(
        2,
        32,
        f"Tipo: {implementation_tier_label(implementation_tier(row))} | Frecuencia: {_frequency_label(row.get('recommended_frequency') or row.get('update_frequency') or 'sin frecuencia')}",
        fontsize=9,
        color="#333333",
    )

    bar_width = min(70, math.log10(count + 1) * 16) if count else 1
    ax.add_patch(plt.Rectangle((2, 12), 70, 10, color="#F3F3F5", ec="#D9D9DF"))
    ax.add_patch(plt.Rectangle((2, 12), bar_width, 10, color="#DDDC40"))
    ax.text(75, 17, f"Registros: {_record_count_label(row.get('record_count', ''))}", va="center", fontsize=9, color="#333333")

    fig.tight_layout(pad=0.6)
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def plot_overview(sources: list[dict[str, str]], assets_dir: Path) -> None:
    assets_dir.mkdir(parents=True, exist_ok=True)
    maturity_counts = Counter(maturity(row) for row in sources)
    labels = [maturity_label(key) for key in maturity_counts]
    values = [maturity_counts[key] for key in maturity_counts]
    colors = ["#2E7D32" if key == "implementada_ok" else "#C62828" if key == "bloqueada_token" else "#F9A825" for key in maturity_counts]

    fig, ax = plt.subplots(figsize=(7.5, 4))
    ax.barh(labels, values, color=colors)
    ax.set_xlabel("Fuentes")
    ax.set_title("Madurez de fuentes implementadas")
    for index, value in enumerate(values):
        ax.text(value + 0.1, index, str(value), va="center")
    fig.tight_layout()
    fig.savefig(assets_dir / "madurez_fuentes_implementadas.png", dpi=150)
    plt.close(fig)

    categories = Counter(row.get("categoria", "(vacio)") for row in sources)
    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    pairs = categories.most_common(12)
    ax.bar([p[0] for p in pairs], [p[1] for p in pairs], color="#483888")
    ax.set_ylabel("Fuentes")
    ax.set_title("Fuentes implementadas por categoria")
    ax.tick_params(axis="x", rotation=35, labelsize=8)
    fig.tight_layout()
    fig.savefig(assets_dir / "categorias_fuentes_implementadas.png", dpi=150)
    plt.close(fig)

    tier_counts = Counter(implementation_tier(row) for row in sources)
    fig, ax = plt.subplots(figsize=(8, 4.4))
    labels = [implementation_tier_label(key) for key, _ in tier_counts.most_common()]
    values = [value for _, value in tier_counts.most_common()]
    ax.barh(labels, values, color="#483888")
    ax.set_xlabel("Fuentes")
    ax.set_title("Tipo de implementación")
    for index, value in enumerate(values):
        ax.text(value + 0.1, index, str(value), va="center")
    fig.tight_layout()
    fig.savefig(assets_dir / "tipo_implementacion_fuentes.png", dpi=150)
    plt.close(fig)


def write_markdown_brief(path: Path, ctx: dict[str, str]) -> None:
    lines = [
        f"# Brief de fuente implementada: {ctx['source_name']}",
        "",
        f"**Source key:** `{ctx['source_key']}`  ",
        f"**Categoria:** {ctx['categoria']}  ",
        f"**Madurez:** {ctx['maturity_label']}  ",
        f"**Tipo:** {ctx['implementation_tier_label']}  ",
        f"**Decision operativa:** `{ctx['decision_code']}`",
        "",
        f"![Resumen de fuente]({ctx['chart_path']})",
        "",
        "## Ficha rapida para Fernanda",
        "",
        f"- **Tipo de datos descargados:** {ctx['downloaded_data']}",
        f"- **Tipologia de datos:** {ctx['data_typology']}",
        f"- **Uso posible en el observatorio:** {ctx['observatory_use']}",
        f"- **Frecuencia de descarga:** {ctx['frequency']}",
        f"- **Estado:** {ctx['operational_status']}",
        f"- **Decision operativa:** `{ctx['decision_code']}`",
        "",
        "## Comentario para Excel",
        "",
        ctx["comment"],
        "",
    ]
    for title, body_key in [
        ("Que datos ofrece la fuente", "data_offer"),
        ("Que extraemos para CCHEN", "cchen_extract"),
        ("Como se filtra CCHEN-only", "filter"),
        ("Potencial para el observatorio", "potential"),
        ("Debilidades y riesgos", "weakness"),
        ("Frecuencia recomendada", "frequency"),
        ("Estado operativo", "state"),
        ("Evidencia disponible", "evidence"),
        ("Decision", "decision"),
    ]:
        lines.extend([f"## {title}", "", _wrap_md(ctx[body_key]), ""])
    if ctx["site_url"] or ctx["api_url"]:
        lines.extend(["## URLs", ""])
        if ctx["site_url"]:
            lines.append(f"- Sitio: {ctx['site_url']}")
        if ctx["api_url"]:
            lines.append(f"- API: {ctx['api_url']}")
        lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def write_latex_brief(path: Path, ctx: dict[str, str]) -> None:
    chart = _latex_escape(ctx["chart_path"])

    def section(title: str, value: str) -> str:
        return f"\\section*{{{_latex_escape(title)}}}\n{_latex_escape(_wrap_md(value))}\n"

    body = "\n".join(
        [
            section(
                "Ficha rapida para Fernanda",
                (
                    f"Tipo de datos descargados: {ctx['downloaded_data']}. "
                    f"Tipologia de datos: {ctx['data_typology']}. "
                    f"Uso posible en el observatorio: {ctx['observatory_use']}. "
                    f"Frecuencia de descarga: {ctx['frequency']}. "
                    f"Estado: {ctx['operational_status']}. "
                    f"Decision operativa: {ctx['decision_code']}."
                ),
            ),
            section("Comentario para Excel", ctx["comment"]),
            section("Que datos ofrece la fuente", ctx["data_offer"]),
            section("Que extraemos para CCHEN", ctx["cchen_extract"]),
            section("Como se filtra CCHEN-only", ctx["filter"]),
            section("Potencial para el observatorio", ctx["potential"]),
            section("Debilidades y riesgos", ctx["weakness"]),
            section("Frecuencia recomendada", f"{ctx['frequency']} (SLA: {ctx['sla']} dias)."),
            section("Estado operativo", ctx["state"]),
            section("Evidencia disponible", ctx["evidence"]),
            section("Decision", ctx["decision"]),
        ]
    )
    text = rf"""% !TeX program = pdflatex
\documentclass[10pt,a4paper]{{article}}
\usepackage[spanish,es-nodecimaldot,es-noshorthands]{{babel}}
\usepackage[T1]{{fontenc}}
\usepackage[utf8]{{inputenc}}
\usepackage{{lmodern}}
\renewcommand{{\familydefault}}{{\sfdefault}}
\usepackage[a4paper,left=1.6cm,right=1.6cm,top=1.35cm,bottom=1.45cm]{{geometry}}
\usepackage{{graphicx}}
\usepackage{{xcolor}}
\usepackage{{hyperref}}
\usepackage{{microtype}}
\definecolor{{cchenpurple}}{{HTML}}{{483888}}
\definecolor{{cchenlime}}{{HTML}}{{DDDC40}}
\definecolor{{textgray}}{{HTML}}{{333333}}
\hypersetup{{colorlinks=true, linkcolor=cchenpurple, urlcolor=cchenpurple}}
\setlength{{\parindent}}{{0pt}}
\setlength{{\parskip}}{{4pt}}
\begin{{document}}
{{\Large\bfseries\color{{cchenpurple}} Brief de fuente implementada: {_latex_escape(ctx['source_name'])}}}

\vspace{{2mm}}
{{\bfseries Source key:}} \texttt{{{_latex_escape(ctx['source_key'])}}} \quad
{{\bfseries Categoria:}} {_latex_escape(ctx['categoria'])} \quad
{{\bfseries Madurez:}} {_latex_escape(ctx['maturity_label'])}

{{\bfseries Tipo:}} {_latex_escape(ctx['implementation_tier_label'])} \quad
{{\bfseries Decision operativa:}} \texttt{{{_latex_escape(ctx['decision_code'])}}}

\vspace{{2mm}}
\includegraphics[width=\textwidth]{{{chart}}}

{body}

\section*{{URLs}}
Sitio: {_latex_escape(ctx['site_url'] or 'sin URL registrada')}\\
API: {_latex_escape(ctx['api_url'] or 'sin API registrada')}
\end{{document}}
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_comments_markdown(path: Path, rows: list[dict[str, str]]) -> None:
    lines = [
        "# Comentarios recomendados para Excel de Fernanda - fuentes implementadas",
        "",
        f"Fecha: {dt.date.today().isoformat()}",
        "",
        "No se modifica el Excel original. Estos comentarios estan listos para copiar en la columna de comentarios.",
        "",
        "| Fuente | Source key | Tipologia | Uso observatorio | Frecuencia | Estado | Decision | Comentario recomendado |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['source_name']} | `{row['source_key']}` | {row['tipologia_datos']} | "
            f"{row['uso_observatorio']} | {row['frecuencia_descarga']} | {row['estado_fuente']} | "
            f"`{row['decision_operativa']}` | {row['comentario_excel_recomendado']} |"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_index(path: Path, sources: list[dict[str, str]], contexts: list[dict[str, str]]) -> None:
    ctx_by_key = {ctx["source_key"]: ctx for ctx in contexts}
    maturity_counts = Counter(ctx["maturity_label"] for ctx in contexts)
    category_counts = Counter(row.get("categoria", "(vacio)") for row in sources)
    tier_counts = Counter(ctx["implementation_tier_label"] for ctx in contexts)
    decision_counts = Counter(ctx["decision_code"] for ctx in contexts)
    lines = [
        "# Indice de fuentes implementadas Fernanda/CCHEN",
        "",
        f"Fecha: {dt.date.today().isoformat()}",
        "",
        f"Total fuentes implementadas documentadas: {len(contexts)}.",
        "",
        "## Resumen",
        "",
        "| Grupo | Fuentes |",
        "| --- | ---: |",
    ]
    for key, value in sorted(maturity_counts.items()):
        lines.append(f"| {key} | {value} |")
    lines.extend(["", "## Tipo de implementacion", "", "| Tipo | Fuentes |", "| --- | ---: |"])
    for key, value in tier_counts.most_common():
        lines.append(f"| {key} | {value} |")
    lines.extend(["", "## Decision operativa", "", "| Decision | Fuentes |", "| --- | ---: |"])
    for key, value in decision_counts.most_common():
        lines.append(f"| `{key}` | {value} |")
    lines.extend(["", "## Categorias", "", "| Categoria | Fuentes |", "| --- | ---: |"])
    for key, value in category_counts.most_common():
        lines.append(f"| {key or '(vacio)'} | {value} |")
    lines.extend(
        [
            "",
            "## Fuentes",
            "",
            "| Fuente | Tipologia de datos | Uso observatorio | Tipo | Decision | Frecuencia | Estado | Brief |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in sources:
        ctx = ctx_by_key[row["source_key"]]
        brief = f"briefs/brief_{row['source_key']}.md"
        lines.append(
            f"| {ctx['source_name']} | {ctx['data_typology']} | {ctx['observatory_use']} | "
            f"{ctx['implementation_tier_label']} | `{ctx['decision_code']}` | {ctx['frequency']} | "
            f"{ctx['operational_status']} | [{brief}]({brief}) |"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_executive_summary(output_dir: Path, contexts: list[dict[str, str]]) -> None:
    maturity_counts = Counter(ctx["maturity_label"] for ctx in contexts)
    tier_counts = Counter(ctx["implementation_tier_label"] for ctx in contexts)
    decision_counts = Counter(ctx["decision_code"] for ctx in contexts)
    direct = [ctx for ctx in contexts if ctx["implementation_tier"] == "implementada_directa_api"]
    derived = [ctx for ctx in contexts if ctx["implementation_tier"] == "implementada_derivada_semilla"]
    review = [ctx for ctx in contexts if ctx["decision_code"] == "revisar_match"]
    blocked = [ctx for ctx in contexts if ctx["decision_code"] == "bloqueada_por_token"]

    lines = [
        "# Resumen ejecutivo - Fuentes implementadas desde matriz Fernanda",
        "",
        f"Fecha: {dt.date.today().isoformat()}",
        "",
        f"Se documentaron {len(contexts)} fuentes implementadas provenientes de la matriz de Fernanda. El paquete separa conexiones directas/API, fuentes derivadas por semillas, runtime local y casos que requieren revision antes de presentarse como fuente estable.",
        "",
        "## Lectura ejecutiva",
        "",
        f"- Fuentes directas/API listas: {len(direct)}.",
        f"- Fuentes derivadas o por semillas: {len(derived)}.",
        f"- Fuentes bloqueadas por token: {len(blocked)}.",
        f"- Matches a revisar: {len(review)}.",
        "- Regla metodologica: no se descarga universo completo; toda fuente debe operar CCHEN-only o por semillas justificadas.",
        "",
        "![Tipo de implementacion](assets/tipo_implementacion_fuentes.png)",
        "",
        "![Madurez](assets/madurez_fuentes_implementadas.png)",
        "",
        "## Decisiones operativas",
        "",
        "| Decision | Fuentes |",
        "| --- | ---: |",
    ]
    for key, value in decision_counts.most_common():
        lines.append(f"| `{key}` | {value} |")
    lines.extend(["", "## Tipo de implementacion", "", "| Tipo | Fuentes |", "| --- | ---: |"])
    for key, value in tier_counts.most_common():
        lines.append(f"| {key} | {value} |")
    lines.extend(["", "## Madurez", "", "| Madurez | Fuentes |", "| --- | ---: |"])
    for key, value in maturity_counts.most_common():
        lines.append(f"| {key} | {value} |")
    lines.extend(
        [
            "",
            "## Alertas para consultora",
            "",
            "- `PatentsView / USPTO` esta registrado, pero requiere `PATENTSVIEW_API_KEY`; no debe reemplazar INAPI local.",
            "- `Google Finance / News monitor` debe revisarse: el runtime existente monitorea noticias CCHEN/nuclear, no datos financieros de Google Finance.",
            "- `ClinVar`, `GenBank`, `GEO`, `NIH` y `SRA` aparecen como implementadas por flujos relacionados; presentarlas como derivadas/semilla hasta tener extractores directos.",
            "- Los conteos con multiples valores representan artefactos distintos; no deben sumarse como una unica tabla.",
            "",
            "## Fuentes directas/API recomendadas para mostrar primero",
            "",
            ", ".join(ctx["source_name"] for ctx in direct) + ".",
            "",
            "## Archivos de apoyo",
            "",
            "- `comentarios_excel_fernanda_recomendados.md`: comentarios listos para revisar/copiar.",
            "- `indice_fuentes_priorizadas.md`: indice navegable a cada brief.",
            "- `briefs/`: briefs Markdown, LaTeX y PDF por fuente.",
            "- `assets/`: graficos de madurez, tipo de implementacion y tarjetas por fuente.",
        ]
    )
    md_path = output_dir / "resumen_ejecutivo_fuentes_implementadas.md"
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    latex_rows = "\n".join(
        f"{_latex_escape(key)} & {value} \\\\"
        for key, value in decision_counts.most_common()
    )
    alerts = (
        "\\item PatentsView / USPTO requiere \\texttt{PATENTSVIEW\\_API\\_KEY}; no reemplaza INAPI local.\n"
        "\\item Google Finance / News monitor requiere revision: el runtime monitorea noticias CCHEN/nuclear, no datos financieros.\n"
        "\\item Las fuentes Life Sciences derivadas deben presentarse como evidencia por semillas hasta implementar extractores directos.\n"
        "\\item Los conteos multiples son artefactos distintos y no se suman como tabla unica."
    )
    tex = rf"""% !TeX program = pdflatex
\documentclass[10pt,a4paper]{{article}}
\usepackage[spanish,es-nodecimaldot,es-noshorthands]{{babel}}
\usepackage[T1]{{fontenc}}
\usepackage[utf8]{{inputenc}}
\usepackage{{lmodern}}
\renewcommand{{\familydefault}}{{\sfdefault}}
\usepackage[a4paper,left=1.55cm,right=1.55cm,top=1.3cm,bottom=1.45cm]{{geometry}}
\usepackage{{graphicx}}
\usepackage{{xcolor}}
\usepackage{{booktabs}}
\usepackage{{hyperref}}
\definecolor{{cchenpurple}}{{HTML}}{{483888}}
\setlength{{\parindent}}{{0pt}}
\setlength{{\parskip}}{{4pt}}
\begin{{document}}
{{\Large\bfseries\color{{cchenpurple}} Resumen ejecutivo: fuentes implementadas desde matriz Fernanda}}

Fecha: {dt.date.today().isoformat()}

Se documentaron {len(contexts)} fuentes implementadas provenientes de la matriz de Fernanda. El paquete separa conexiones directas/API, fuentes derivadas por semillas, runtime local y casos que requieren revision antes de presentarse como fuente estable.

\section*{{Lectura ejecutiva}}
\begin{{itemize}}
\item Fuentes directas/API listas: {len(direct)}.
\item Fuentes derivadas o por semillas: {len(derived)}.
\item Fuentes bloqueadas por token: {len(blocked)}.
\item Matches a revisar: {len(review)}.
\item Regla metodologica: no se descarga universo completo; toda fuente debe operar CCHEN-only o por semillas justificadas.
\end{{itemize}}

\includegraphics[width=\textwidth]{{assets/tipo_implementacion_fuentes.png}}

\includegraphics[width=\textwidth]{{assets/madurez_fuentes_implementadas.png}}

\section*{{Decisiones operativas}}
\begin{{tabular}}{{lr}}
\toprule
Decision & Fuentes \\
\midrule
{latex_rows}
\bottomrule
\end{{tabular}}

\section*{{Alertas para consultora}}
\begin{{itemize}}
{alerts}
\end{{itemize}}
\end{{document}}
"""
    (output_dir / "resumen_ejecutivo_fuentes_implementadas.tex").write_text(tex, encoding="utf-8")


def enrich_with_runtime(catalog_sources: list[dict[str, str]], runtime: dict[str, dict[str, str]]) -> list[dict[str, str]]:
    enriched = []
    for source in catalog_sources:
        row = dict(source)
        runtime_row = runtime.get(row["source_key"], {})
        for field in [
            "runner_command",
            "output_targets",
            "last_updated",
            "next_update_due",
            "record_count",
            "quality_score",
            "last_run_status",
            "updated_at",
            "update_frequency",
            "freshness_sla_days",
        ]:
            if runtime_row.get(field):
                row[field] = runtime_row[field]
        if not row.get("recommended_frequency"):
            row["recommended_frequency"] = row.get("update_frequency", "")
        enriched.append(row)
    return enriched


def validate_outputs(comments: list[dict[str, str]], contexts: list[dict[str, str]], briefs_dir: Path) -> list[str]:
    errors = []
    for row in comments:
        if not row.get("comentario_excel_recomendado"):
            errors.append(f"Comentario vacio: {row.get('source_key')}")
    for ctx in contexts:
        md = briefs_dir / f"brief_{ctx['source_key']}.md"
        if not md.exists():
            errors.append(f"Brief Markdown faltante: {ctx['source_key']}")
            continue
        text = md.read_text(encoding="utf-8")
        for section in BRIEF_REQUIRED_SECTIONS:
            if f"## {section}" not in text:
                errors.append(f"Seccion faltante {section}: {ctx['source_key']}")
        if "universo completo" in _norm(text) and "no se consulta universo completo" not in _norm(text):
            errors.append(f"Posible descarga de universo completo: {ctx['source_key']}")
    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Genera comentarios y briefs para fuentes implementadas.")
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--runtime", type=Path, default=DEFAULT_RUNTIME)
    parser.add_argument("--comments-csv", type=Path, default=DEFAULT_COMMENTS_CSV)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    catalog_rows = _read_csv(args.catalog)
    runtime_rows = _read_csv(args.runtime)
    sources = enrich_with_runtime(implemented_sources(catalog_rows), runtime_by_key(runtime_rows))

    output_dir = args.output_dir
    clean_generated_outputs(output_dir)
    briefs_dir = output_dir / "briefs"
    assets_dir = output_dir / "assets"
    plot_overview(sources, assets_dir)

    contexts = []
    comment_rows = []
    for row in sources:
        plot_source_card(row, assets_dir)
        ctx = brief_context(row, assets_dir)
        contexts.append(ctx)
        comment_rows.append(
            {
                "source_key": row["source_key"],
                "source_name": ctx["source_name"],
                "categoria": row.get("categoria", ""),
                "implementation_status": row.get("implementation_status", ""),
                "tipo_implementacion": ctx["implementation_tier_label"],
                "decision_operativa": ctx["decision_code"],
                "tipo_datos_descargados": ctx["downloaded_data"],
                "tipologia_datos": ctx["data_typology"],
                "uso_observatorio": ctx["observatory_use"],
                "frecuencia_descarga": ctx["frequency"],
                "estado_fuente": ctx["operational_status"],
                "priority_wave": row.get("priority_wave", ""),
                "recommended_frequency": ctx["frequency"],
                "last_run_status": row.get("last_run_status", ""),
                "record_count": row.get("record_count", ""),
                "comentario_excel_recomendado": ctx["comment"],
                "brief_markdown": f"Docs/reports/fuentes_fernanda_implementadas/briefs/brief_{row['source_key']}.md",
                "brief_latex": f"Docs/reports/fuentes_fernanda_implementadas/briefs/brief_{row['source_key']}.tex",
            }
        )
        write_markdown_brief(briefs_dir / f"brief_{row['source_key']}.md", ctx)
        write_latex_brief(briefs_dir / f"brief_{row['source_key']}.tex", ctx)

    _write_csv(
        args.comments_csv,
        comment_rows,
        [
            "source_key",
            "source_name",
            "categoria",
            "implementation_status",
            "tipo_implementacion",
            "decision_operativa",
            "tipo_datos_descargados",
            "tipologia_datos",
            "uso_observatorio",
            "frecuencia_descarga",
            "estado_fuente",
            "priority_wave",
            "recommended_frequency",
            "last_run_status",
            "record_count",
            "comentario_excel_recomendado",
            "brief_markdown",
            "brief_latex",
        ],
    )
    write_comments_markdown(output_dir / "comentarios_excel_fernanda_recomendados.md", comment_rows)
    write_index(output_dir / "indice_fuentes_priorizadas.md", sources, contexts)
    write_executive_summary(output_dir, contexts)

    errors = validate_outputs(comment_rows, contexts, briefs_dir)
    if errors:
        for error in errors:
            print(f"[ERROR] {error}")
        return 1

    print(f"[OK] fuentes implementadas documentadas: {len(sources)}")
    print(f"[OK] comentarios CSV -> {args.comments_csv.relative_to(ROOT)}")
    print(f"[OK] comentarios MD -> {(output_dir / 'comentarios_excel_fernanda_recomendados.md').relative_to(ROOT)}")
    print(f"[OK] indice -> {(output_dir / 'indice_fuentes_priorizadas.md').relative_to(ROOT)}")
    print(f"[OK] briefs -> {briefs_dir.relative_to(ROOT)}")
    print(f"[OK] assets -> {assets_dir.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
