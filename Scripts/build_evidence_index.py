#!/usr/bin/env python3
"""
Build a unified evidence index for CCHEN research and innovation management.

Outputs:
  Data/Semantic/evidence_index.csv
  Data/Semantic/evidence_embeddings.npy
  Data/Semantic/evidence_embeddings_meta.csv
  Data/Semantic/evidence_embedding_pipeline.joblib  (TF-IDF fallback)
  Data/Semantic/evidence_index_summary.csv
  Data/Semantic/evidence_index_state.json

The index is intentionally CCHEN-only: it normalizes records already extracted
or curated for CCHEN instead of downloading full external universes.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html
import json
import re
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "Data"
OUT_DIR = DATA / "Semantic"
GOVERNANCE_DIR = DATA / "Gobernanza"

INDEX_PATH = OUT_DIR / "evidence_index.csv"
EMB_PATH = OUT_DIR / "evidence_embeddings.npy"
META_PATH = OUT_DIR / "evidence_embeddings_meta.csv"
PIPELINE_PATH = OUT_DIR / "evidence_embedding_pipeline.joblib"
STATE_PATH = OUT_DIR / "evidence_index_state.json"
SUMMARY_PATH = OUT_DIR / "evidence_index_summary.csv"
PUBLICABLE_INDEX_PATH = GOVERNANCE_DIR / "evidence_index_publicable.csv"
PUBLICABLE_SUMMARY_PATH = GOVERNANCE_DIR / "evidence_index_publicable_summary.csv"

INDEX_COLUMNS = [
    "id",
    "titulo",
    "resumen",
    "tipo_evidencia",
    "fuente",
    "source_key",
    "url",
    "fecha",
    "autores",
    "relacion_cchen",
    "tema",
    "uso_observatorio",
    "brecha",
    "nivel_confianza",
    "identificador",
    "source_path",
    "texto_embedding",
    "fetched_at",
]

PUBLICABLE_COLUMNS = [
    "id",
    "titulo",
    "resumen",
    "tipo_evidencia",
    "fuente",
    "source_key",
    "url",
    "fecha",
    "autores",
    "relacion_cchen",
    "tema",
    "uso_observatorio",
    "brecha",
    "nivel_confianza",
    "identificador",
    "source_path",
    "fetched_at",
]

THEME_RULES = [
    (
        "radiofarmacia",
        [
            "radiofarm", "radiopharmaceutical", "fdg", "f-18", "fluorine-18",
            "ga-68", "gallium-68", "lu-177", "lutetium-177", "tc-99m",
            "technetium", "i-131", "iodine-131", "ciclotron", "cyclotron",
        ],
    ),
    (
        "medicina nuclear",
        [
            "medicina nuclear", "nuclear medicine", "pet", "spect", "dosimetr",
            "radiotherapy", "radioterapia", "imaging", "imagenologia",
        ],
    ),
    (
        "materiales",
        [
            "material", "nanoparticle", "nanoparticula", "composite",
            "polymer", "corrosion", "irradiation", "irradiacion", "lithium",
        ],
    ),
    (
        "seguridad radiologica",
        [
            "seguridad radiologica", "radiological protection", "radioproteccion",
            "radiacion", "radiation", "dosimetry", "dosimetria",
        ],
    ),
    (
        "patentes y transferencia",
        [
            "patent", "patente", "transferencia", "licenciamiento", "propiedad intelectual",
            "pi", "inapi", "uspto", "wipo", "epo",
        ],
    ),
    (
        "datos y repositorios",
        [
            "dataset", "data", "zenodo", "datacite", "openaire", "repositorio",
            "software", "doi", "output",
        ],
    ),
    (
        "financiamiento y oportunidades",
        [
            "anid", "convocatoria", "fondo", "financiamiento", "proyecto",
            "matching", "corfo", "iaea", "horizon",
        ],
    ),
    (
        "colaboracion institucional",
        [
            "convenio", "acuerdo", "colaboracion", "cooperacion", "universidad",
            "organismo internacional",
        ],
    ),
]

USE_BY_TYPE = {
    "publicacion": "Mapear capacidad cientifica, autores, temas y evidencia tecnica acumulada.",
    "dataset/output": "Identificar resultados reutilizables, trazables y publicables.",
    "compuesto": "Apoyar vigilancia tematica y conversaciones tecnicas en radiofarmacia.",
    "patente": "Levantar antecedentes de propiedad intelectual y brechas de proteccion.",
    "proyecto": "Conectar financiamiento, capacidades y resultados asociados a CCHEN.",
    "oportunidad": "Priorizar postulaciones y rutas de maduracion institucional.",
    "convenio": "Identificar redes, contrapartes y posibles rutas de colaboracion.",
    "registro interno": "Cruzar evidencia interna con fuentes abiertas y procesos de gestion.",
    "senal tematica": "Explorar una linea aplicada antes de validarla con responsables tecnicos.",
    "acceso abierto": "Evaluar disponibilidad publica de publicaciones CCHEN.",
}

BRECHA_BY_TYPE = {
    "publicacion": "Validar si la evidencia cientifica se vincula a un activo, capacidad o linea institucional.",
    "dataset/output": "Clasificar utilidad para gestion interna, publicacion o transferencia.",
    "compuesto": "No asumir capacidad CCHEN directa sin validacion tecnica.",
    "patente": "Revisar vigencia, titulares, estado legal y relacion con activos actuales.",
    "proyecto": "Vincular con resultados, responsables y productos derivados.",
    "oportunidad": "Confirmar elegibilidad, plazo y responsables antes de actuar.",
    "convenio": "Verificar vigencia, alcance operativo y unidad responsable.",
    "registro interno": "Normalizar campos y resolver duplicados antes de usar como indicador.",
    "senal tematica": "Distinguir evidencia directa CCHEN de vigilancia exploratoria.",
    "acceso abierto": "Confirmar enlace abierto y version disponible antes de difundir.",
}


def read_csv(relative_path: str) -> pd.DataFrame:
    path = DATA / relative_path
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path, low_memory=False, encoding="utf-8-sig").fillna("")
    except UnicodeDecodeError:
        return pd.read_csv(path, low_memory=False, encoding="latin-1").fillna("")


def clean_text(value: object, *, max_len: int | None = None) -> str:
    text = html.unescape(str(value or ""))
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if max_len and len(text) > max_len:
        return text[: max_len - 1].rstrip() + "..."
    return text


def row_value(row: pd.Series, candidates: Iterable[str], default: str = "") -> str:
    for col in candidates:
        if col in row.index:
            value = clean_text(row.get(col, ""))
            if value:
                return value
    return default


def doi_url(doi: str) -> str:
    doi = clean_text(doi)
    if not doi:
        return ""
    if doi.lower().startswith("http"):
        return doi
    return f"https://doi.org/{doi}"


def stable_id(source_key: str, *parts: object) -> str:
    raw = "||".join(clean_text(part) for part in parts if clean_text(part))
    if not raw:
        raw = source_key
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:14]
    return f"{source_key}:{digest}"


def infer_theme(*values: object) -> str:
    text = " ".join(clean_text(v).lower() for v in values)
    themes = []
    for theme, keywords in THEME_RULES:
        if any(keyword in text for keyword in keywords):
            themes.append(theme)
    return "; ".join(themes[:3]) if themes else "general CCHEN"


def canonical_evidence_type(value: object) -> str:
    text = clean_text(value).strip().lower()
    replacements = {
        "publicación": "publicacion",
        "publicaciones": "publicacion",
        "publication": "publicacion",
        "paper": "publicacion",
        "papers": "publicacion",
        "señal temática": "senal tematica",
        "señal tematica": "senal tematica",
        "senal temática": "senal tematica",
        "señal": "senal tematica",
        "dataset": "dataset/output",
        "output": "dataset/output",
        "outputs": "dataset/output",
        "patentes": "patente",
        "proyectos": "proyecto",
        "convocatoria": "oportunidad",
        "convocatorias": "oportunidad",
        "convenios": "convenio",
    }
    return replacements.get(text, text or "registro")


def add_record(
    records: list[dict],
    *,
    source_key: str,
    fuente: str,
    tipo_evidencia: str,
    titulo: object,
    resumen: object = "",
    identificador: object = "",
    url: object = "",
    fecha: object = "",
    autores: object = "",
    relacion_cchen: object = "",
    tema: object = "",
    uso_observatorio: object = "",
    brecha: object = "",
    nivel_confianza: str = "medio",
    source_path: str = "",
    fetched_at: object = "",
) -> None:
    title = clean_text(titulo, max_len=500)
    summary = clean_text(resumen, max_len=1200)
    if not title and not summary:
        return
    if not title:
        title = clean_text(summary, max_len=140)

    identifier = clean_text(identificador)
    link = clean_text(url)
    evidence_type = canonical_evidence_type(tipo_evidencia)
    theme = clean_text(tema) or infer_theme(title, summary, identifier)
    use = clean_text(uso_observatorio) or USE_BY_TYPE.get(evidence_type, "Organizar evidencia para gestion interna y revision experta.")
    gap = clean_text(brecha) or BRECHA_BY_TYPE.get(evidence_type, "Validar pertinencia y calidad antes de usar como evidencia principal.")
    relation = clean_text(relacion_cchen) or "Registro recuperado desde fuente filtrada o curada para CCHEN."

    embedding_text = " | ".join(
        part for part in [title, summary, evidence_type, fuente, relation, theme, use, gap] if part
    )
    records.append(
        {
            "id": stable_id(source_key, identifier, title, link),
            "titulo": title,
            "resumen": summary,
            "tipo_evidencia": evidence_type,
            "fuente": clean_text(fuente),
            "source_key": clean_text(source_key),
            "url": link,
            "fecha": clean_text(fecha),
            "autores": clean_text(autores, max_len=700),
            "relacion_cchen": relation,
            "tema": theme,
            "uso_observatorio": use,
            "brecha": gap,
            "nivel_confianza": clean_text(nivel_confianza) or "medio",
            "identificador": identifier,
            "source_path": source_path,
            "texto_embedding": embedding_text,
            "fetched_at": clean_text(fetched_at),
        }
    )


def build_publication_lookup() -> pd.DataFrame:
    works = read_csv("Publications/cchen_openalex_works.csv")
    abstracts = read_csv("Publications/cchen_abstracts_merged.csv")
    if abstracts.empty and works.empty:
        return pd.DataFrame()
    if abstracts.empty:
        abstracts = works.copy()
        abstracts["abstract_best"] = ""
    if not works.empty and "openalex_id" in abstracts.columns and "openalex_id" in works.columns:
        keep = [c for c in ["openalex_id", "source", "type", "is_oa", "oa_status", "oa_url", "pmid", "pmcid"] if c in works.columns]
        abstracts = abstracts.merge(
            works[keep].drop_duplicates("openalex_id"),
            on="openalex_id",
            how="left",
            suffixes=("", "_works"),
        )
    return abstracts.fillna("")


def add_openalex_publications(records: list[dict]) -> None:
    df = build_publication_lookup()
    if df.empty:
        return
    for _, row in df.iterrows():
        doi = row_value(row, ["doi"])
        add_record(
            records,
            source_key="openalex_publicaciones",
            fuente="OpenAlex publicaciones",
            tipo_evidencia="publicacion",
            titulo=row_value(row, ["title", "display_name"]),
            resumen=row_value(row, ["abstract_best", "abstract", "tldr"]),
            identificador=doi or row_value(row, ["openalex_id"]),
            url=doi_url(doi) or row_value(row, ["openalex_id", "oa_url"]),
            fecha=row_value(row, ["year"]),
            relacion_cchen="Publicacion del corpus institucional CCHEN recuperada por afiliacion, DOI o identificador conocido.",
            tema=row_value(row, ["fields_of_study", "source"], default=""),
            nivel_confianza="alto",
            source_path="Data/Publications/cchen_abstracts_merged.csv",
        )


def add_publication_source(
    records: list[dict],
    relative_path: str,
    source_key: str,
    fuente: str,
    id_cols: list[str],
    url_cols: list[str],
    relation: str,
) -> None:
    df = read_csv(relative_path)
    if df.empty:
        return
    for _, row in df.iterrows():
        doi = row_value(row, ["doi"])
        identifier = doi or row_value(row, id_cols)
        add_record(
            records,
            source_key=source_key,
            fuente=fuente,
            tipo_evidencia="publicacion",
            titulo=row_value(row, ["title", "main_title"]),
            resumen=row_value(row, ["abstract", "tldr", "keywords", "inspire_categories"]),
            identificador=identifier,
            url=doi_url(doi) or row_value(row, url_cols),
            fecha=row_value(row, ["year", "pub_date", "publication_date"]),
            autores=row_value(row, ["authors", "creators"]),
            relacion_cchen=relation,
            nivel_confianza="alto",
            source_path=f"Data/{relative_path}",
            fetched_at=row_value(row, ["fetched_at"]),
        )


def add_crossref_unpaywall(records: list[dict]) -> None:
    lookup = build_publication_lookup()
    title_by_doi = {}
    if not lookup.empty and "doi" in lookup.columns:
        for _, row in lookup.iterrows():
            doi = clean_text(row.get("doi"))
            title = row_value(row, ["title"])
            if doi and title and doi not in title_by_doi:
                title_by_doi[doi] = title

    crossref = read_csv("Publications/cchen_crossref_enriched.csv")
    for _, row in crossref.iterrows():
        doi = row_value(row, ["doi"])
        title = title_by_doi.get(doi, doi)
        summary_parts = [
            f"Publisher: {row_value(row, ['publisher'])}" if row_value(row, ["publisher"]) else "",
            f"Funders: {row_value(row, ['crossref_funders'])}" if row_value(row, ["crossref_funders"]) else "",
            f"References: {row_value(row, ['references_count'])}" if row_value(row, ["references_count"]) else "",
            row_value(row, ["abstract"]),
        ]
        add_record(
            records,
            source_key="crossref",
            fuente="CrossRef",
            tipo_evidencia="publicacion",
            titulo=title,
            resumen="; ".join(part for part in summary_parts if part),
            identificador=doi,
            url=doi_url(doi),
            relacion_cchen="Enriquecimiento por DOI de publicaciones CCHEN ya conocidas.",
            tema=row_value(row, ["subject"]),
            uso_observatorio="Enriquecer DOI CCHEN con editorial, referencias, funding y metadatos.",
            brecha="CrossRef no prueba por si solo pertinencia tecnologica; debe cruzarse con autores, temas y activos.",
            nivel_confianza="alto",
            source_path="Data/Publications/cchen_crossref_enriched.csv",
        )

    unpaywall = read_csv("Publications/cchen_unpaywall_oa.csv")
    for _, row in unpaywall.iterrows():
        doi = row_value(row, ["doi"])
        title = title_by_doi.get(doi, doi)
        summary = (
            f"Estado de acceso abierto: {row_value(row, ['oa_status'])}; "
            f"revista: {row_value(row, ['journal_name'])}; publisher: {row_value(row, ['publisher'])}."
        )
        add_record(
            records,
            source_key="unpaywall_oa",
            fuente="Unpaywall",
            tipo_evidencia="acceso abierto",
            titulo=title,
            resumen=summary,
            identificador=doi,
            url=row_value(row, ["oa_url", "oa_pdf_url"]) or doi_url(doi),
            fecha=row_value(row, ["published_date", "updated"]),
            relacion_cchen="Enriquecimiento por DOI de publicaciones CCHEN ya conocidas.",
            tema="datos y repositorios",
            nivel_confianza="alto",
            source_path="Data/Publications/cchen_unpaywall_oa.csv",
            fetched_at=row_value(row, ["fetched_at"]),
        )


def add_outputs(records: list[dict]) -> None:
    datacite = read_csv("ResearchOutputs/cchen_datacite_outputs.csv")
    for _, row in datacite.iterrows():
        add_record(
            records,
            source_key="datacite_outputs",
            fuente="DataCite",
            tipo_evidencia="dataset/output",
            titulo=row_value(row, ["title"]),
            resumen=row_value(row, ["description", "subjects", "resource_type"]),
            identificador=row_value(row, ["doi"]),
            url=row_value(row, ["url"]) or doi_url(row_value(row, ["doi"])),
            fecha=row_value(row, ["publication_year", "created", "updated"]),
            autores=row_value(row, ["creators"]),
            relacion_cchen="Output asociado al ROR o afiliacion CCHEN en DataCite.",
            tema=row_value(row, ["resource_type_general", "subjects"]),
            nivel_confianza="alto",
            source_path="Data/ResearchOutputs/cchen_datacite_outputs.csv",
        )

    openaire = read_csv("ResearchOutputs/cchen_openaire_outputs.csv")
    for _, row in openaire.iterrows():
        relation = row_value(row, ["match_scope"], default="ORCID o institucion asociada a CCHEN")
        add_record(
            records,
            source_key="openaire_outputs",
            fuente="OpenAIRE",
            tipo_evidencia="dataset/output",
            titulo=row_value(row, ["main_title"]),
            resumen="; ".join(
                part for part in [
                    row_value(row, ["type"]),
                    row_value(row, ["publisher"]),
                    row_value(row, ["best_access_right_label"]),
                    row_value(row, ["sources"]),
                    row_value(row, ["project_codes"]),
                ] if part
            ),
            identificador=row_value(row, ["openaire_id", "pids"]),
            url=row_value(row, ["instance_urls"]),
            fecha=row_value(row, ["publication_date"]),
            autores=row_value(row, ["authors", "matched_researchers"]),
            relacion_cchen=f"Vinculo OpenAIRE: {relation}.",
            tema=row_value(row, ["type", "project_funders"]),
            brecha="Distinguir vinculos institucionales directos de vinculos solo por autor/ORCID.",
            nivel_confianza="medio",
            source_path="Data/ResearchOutputs/cchen_openaire_outputs.csv",
        )

    zenodo = read_csv("ResearchOutputs/cchen_zenodo_metadata.csv")
    for _, row in zenodo.iterrows():
        add_record(
            records,
            source_key="zenodo_outputs",
            fuente="Zenodo",
            tipo_evidencia="dataset/output",
            titulo=row_value(row, ["title"]),
            resumen=row_value(row, ["description_snippet", "keywords", "resource_type_title"]),
            identificador=row_value(row, ["doi", "record_id"]),
            url=row_value(row, ["url", "api_url"]) or doi_url(row_value(row, ["doi"])),
            fecha=row_value(row, ["publication_date"]),
            autores=row_value(row, ["creators"]),
            relacion_cchen=f"Busqueda por aliases CCHEN; alcance: {row_value(row, ['match_scope'])}.",
            tema=row_value(row, ["resource_type_title", "keywords"]),
            nivel_confianza="medio",
            source_path="Data/ResearchOutputs/cchen_zenodo_metadata.csv",
            fetched_at=row_value(row, ["fetched_at"]),
        )

    master = read_csv("Gobernanza/outputs_repositorios_cchen_master.csv")
    for _, row in master.iterrows():
        if str(row.get("is_descartado", "")).lower() == "true":
            continue
        add_record(
            records,
            source_key="repositorios_cchen_outputs_master",
            fuente=row_value(row, ["source_name"], default="Repositorio abierto"),
            tipo_evidencia="dataset/output",
            titulo=row_value(row, ["title"]),
            resumen="; ".join(
                part for part in [
                    row_value(row, ["observatory_use"]),
                    row_value(row, ["review_decision"]),
                    row_value(row, ["resource_type"]),
                ] if part
            ),
            identificador=row_value(row, ["doi", "master_id", "record_id"]),
            url=row_value(row, ["url"]) or doi_url(row_value(row, ["doi"])),
            fecha=row_value(row, ["published", "year"]),
            autores=row_value(row, ["creators"]),
            relacion_cchen=f"Tabla maestra curada; alcance: {row_value(row, ['relation_scope'])}.",
            tema=row_value(row, ["theme", "output_kind", "publish_scope"]),
            brecha=row_value(row, ["quality_notes"]) or "Revisar decision de curaduria antes de usar como evidencia principal.",
            nivel_confianza="medio",
            source_path="Data/Gobernanza/outputs_repositorios_cchen_master.csv",
        )


def add_radiofarmacia(records: list[dict]) -> None:
    literature = read_csv("Gobernanza/radiofarmacia_cchen_literature_reviewed.csv")
    for _, row in literature.iterrows():
        publish_scope = row_value(row, ["publish_scope"]).lower()
        review_decision = row_value(row, ["review_decision", "curation_decision"]).lower()
        if publish_scope in {"no_publicar", "auditoria_no_tablero_principal"} or "descartar" in review_decision:
            continue
        add_record(
            records,
            source_key="radiofarmacia_literature",
            fuente=row_value(row, ["source_system"], default="Radiofarmacia curada"),
            tipo_evidencia="senal tematica",
            titulo=row_value(row, ["title"]),
            resumen="; ".join(
                part for part in [
                    row_value(row, ["seed_label"]),
                    row_value(row, ["information_type"]),
                    row_value(row, ["review_theme"]),
                    row_value(row, ["review_rationale"]),
                ] if part
            ),
            identificador=row_value(row, ["doi", "pmid", "source_id"]),
            url=row_value(row, ["url"]) or doi_url(row_value(row, ["doi"])),
            fecha=row_value(row, ["year"]),
            relacion_cchen=f"Semilla tematica para CCHEN; alcance: {row_value(row, ['relation_scope'])}.",
            tema="radiofarmacia; medicina nuclear",
            uso_observatorio="Explorar evidencia tecnica y clinica relacionada con radiofarmacia para priorizar revision experta.",
            brecha=row_value(row, ["recommended_action", "review_rationale"]) or BRECHA_BY_TYPE["senal tematica"],
            nivel_confianza="medio",
            source_path="Data/Gobernanza/radiofarmacia_cchen_literature_reviewed.csv",
            fetched_at=row_value(row, ["fetched_at", "reviewed_at"]),
        )

    compounds = read_csv("Gobernanza/radiofarmacia_cchen_compounds_curated.csv")
    for _, row in compounds.iterrows():
        add_record(
            records,
            source_key="radiofarmacia_compounds",
            fuente="PubChem / radiofarmacia curada",
            tipo_evidencia="compuesto",
            titulo=row_value(row, ["title", "compound_query"]),
            resumen="; ".join(
                part for part in [
                    f"Formula: {row_value(row, ['molecular_formula'])}" if row_value(row, ["molecular_formula"]) else "",
                    f"Peso molecular: {row_value(row, ['molecular_weight'])}" if row_value(row, ["molecular_weight"]) else "",
                    row_value(row, ["rationale"]),
                ] if part
            ),
            identificador=row_value(row, ["cid", "inchi_key"]),
            url=row_value(row, ["pubchem_url"]),
            fecha=row_value(row, ["fetched_at"]),
            relacion_cchen=f"Compuesto semilla para linea radiofarmacia; alcance: {row_value(row, ['relation_scope'])}.",
            tema="radiofarmacia; medicina nuclear",
            brecha=row_value(row, ["recommended_consultant_action"]) or BRECHA_BY_TYPE["compuesto"],
            nivel_confianza="medio",
            source_path="Data/Gobernanza/radiofarmacia_cchen_compounds_curated.csv",
            fetched_at=row_value(row, ["fetched_at"]),
        )


def add_projects_opportunities(records: list[dict]) -> None:
    anid = read_csv("ANID/RepositorioAnid_con_monto.csv")
    for _, row in anid.iterrows():
        add_record(
            records,
            source_key="anid_repositorio",
            fuente="ANID Repositorio",
            tipo_evidencia="proyecto",
            titulo=row_value(row, ["titulo", "proyecto"]),
            resumen=row_value(row, ["resumen", "instrumento_full", "concurso_full", "programa_full"]),
            identificador=row_value(row, ["proyecto", "folio_full"]),
            url=row_value(row, ["full_url", "link"]),
            fecha=row_value(row, ["anio_concurso", "anio"]),
            autores=row_value(row, ["autor", "dc.contributor.author"]),
            relacion_cchen=row_value(row, ["institucion", "institucion_full"], default="Proyecto adjudicado o asociado a CCHEN."),
            tema=row_value(row, ["programa", "instrumento", "tipo"]),
            nivel_confianza="alto",
            source_path="Data/ANID/RepositorioAnid_con_monto.csv",
        )

    convocatorias = read_csv("Vigilancia/convocatorias_curadas.csv")
    for _, row in convocatorias.iterrows():
        add_record(
            records,
            source_key="convocatorias_curadas",
            fuente=row_value(row, ["organismo"], default="Convocatorias curadas"),
            tipo_evidencia="oportunidad",
            titulo=row_value(row, ["titulo"]),
            resumen="; ".join(
                part for part in [
                    row_value(row, ["categoria"]),
                    row_value(row, ["perfil_objetivo"]),
                    row_value(row, ["relevancia_cchen"]),
                    row_value(row, ["notas"]),
                ] if part
            ),
            identificador=row_value(row, ["conv_id"]),
            url=row_value(row, ["url"]),
            fecha=row_value(row, ["cierre_iso", "apertura_iso", "cierre_texto"]),
            relacion_cchen="Convocatoria curada por relevancia institucional CCHEN.",
            tema=row_value(row, ["categoria", "perfil_objetivo"]),
            nivel_confianza="alto",
            source_path="Data/Vigilancia/convocatorias_curadas.csv",
        )

    matching = read_csv("Vigilancia/convocatorias_matching_institucional.csv")
    for _, row in matching.iterrows():
        add_record(
            records,
            source_key="matching_institucional",
            fuente="Matching institucional",
            tipo_evidencia="oportunidad",
            titulo=row_value(row, ["convocatoria_titulo"]),
            resumen="; ".join(
                part for part in [
                    f"Perfil: {row_value(row, ['perfil_nombre'])}" if row_value(row, ["perfil_nombre"]) else "",
                    f"Score: {row_value(row, ['score_total'])}" if row_value(row, ["score_total"]) else "",
                    row_value(row, ["evidence_summary"]),
                    row_value(row, ["recommended_action"]),
                ] if part
            ),
            identificador=row_value(row, ["conv_id"]),
            url=row_value(row, ["url"]),
            fecha=row_value(row, ["cierre_iso", "last_evaluated_at"]),
            relacion_cchen=f"Evaluacion por reglas para unidad {row_value(row, ['owner_unit'])}.",
            tema=row_value(row, ["perfil_nombre", "categoria"]),
            nivel_confianza="alto",
            source_path="Data/Vigilancia/convocatorias_matching_institucional.csv",
            fetched_at=row_value(row, ["last_evaluated_at"]),
        )


def add_internal_and_patents(records: list[dict]) -> None:
    dian = read_csv("Publications/cchen_dian_publications.csv")
    for _, row in dian.iterrows():
        add_record(
            records,
            source_key="dian_publications",
            fuente="Publicaciones DIAN",
            tipo_evidencia="registro interno",
            titulo=row_value(row, ["titulo"]),
            resumen="; ".join(
                part for part in [
                    row_value(row, ["revista"]),
                    row_value(row, ["unidad"]),
                    row_value(row, ["cuartil"]),
                ] if part
            ),
            identificador=row_value(row, ["doi", "numero"]),
            url=doi_url(row_value(row, ["doi"])),
            fecha=row_value(row, ["anio", "fecha_publicacion", "fecha_aceptacion"]),
            autores=row_value(row, ["autores"]),
            relacion_cchen="Registro interno DIAN de produccion cientifica CCHEN.",
            tema=row_value(row, ["unidad", "revista"]),
            nivel_confianza="alto",
            source_path="Data/Publications/cchen_dian_publications.csv",
            fetched_at=row_value(row, ["fetched_at"]),
        )

    patents = read_csv("Patents/cchen_inapi_patents.csv")
    for _, row in patents.iterrows():
        add_record(
            records,
            source_key="inapi_patents",
            fuente=row_value(row, ["fuente"], default="INAPI"),
            tipo_evidencia="patente",
            titulo=row_value(row, ["titulo"]),
            resumen=row_value(row, ["resumen", "clasificacion_ipc", "estado"]),
            identificador=row_value(row, ["patent_id"]),
            url=row_value(row, ["url"]),
            fecha=row_value(row, ["fecha_solicitud", "fecha_concesion"]),
            autores=row_value(row, ["inventores"]),
            relacion_cchen=row_value(row, ["titular"], default="Titularidad o relacion CCHEN en registro INAPI local."),
            tema=row_value(row, ["clasificacion_ipc", "tipo"]),
            nivel_confianza="alto",
            source_path="Data/Patents/cchen_inapi_patents.csv",
            fetched_at=row_value(row, ["fetched_at"]),
        )

    convenios = read_csv("Institutional/clean_Convenios_suscritos_por_la_Com.csv")
    for _, row in convenios.iterrows():
        add_record(
            records,
            source_key="convenios_nacionales",
            fuente="Convenios CCHEN",
            tipo_evidencia="convenio",
            titulo=row_value(row, ["CONTRAPARTE DEL CONVENIO"]),
            resumen=row_value(row, ["DESCRIPCIÓN", "OTROS ANTECEDENTES", "DURACIÓN"]),
            identificador=row_value(row, ["Nº CONVENIO", "Nº RESOLUCIÓN", "Nº"]),
            fecha=row_value(row, ["FECHA RESOLUCIÓN"]),
            relacion_cchen="Convenio nacional suscrito por CCHEN.",
            tema=row_value(row, ["DESCRIPCIÓN", "CONTRAPARTE DEL CONVENIO"]),
            nivel_confianza="alto",
            source_path="Data/Institutional/clean_Convenios_suscritos_por_la_Com.csv",
        )

    acuerdos = read_csv("Institutional/clean_Acuerdos_e_instrumentos_intern.csv")
    if not acuerdos.empty:
        cols = list(acuerdos.columns)
        for _, row in acuerdos.iterrows():
            values = [row_value(row, [col]) for col in cols]
            values = [v for v in values if v]
            if len(values) < 3:
                continue
            first = values[0].lower()
            if "tabla" in first or first in {"nº", "no", "reg.no"}:
                continue
            title = values[2] if len(values) >= 3 and len(values[2]) > 20 else values[1]
            if title.lower() in {"pais", "instrumento", "titulo (title)"}:
                continue
            add_record(
                records,
                source_key="acuerdos_internacionales",
                fuente="Acuerdos internacionales CCHEN",
                tipo_evidencia="convenio",
                titulo=title,
                resumen="; ".join(values[:5]),
                identificador=values[0],
                fecha="; ".join(values[3:5]) if len(values) >= 5 else "",
                relacion_cchen="Acuerdo o instrumento internacional asociado a CCHEN o al Estado de Chile en materia nuclear.",
                tema=title,
                nivel_confianza="medio",
                source_path="Data/Institutional/clean_Acuerdos_e_instrumentos_intern.csv",
            )


def add_transferencia_seed(records: list[dict]) -> None:
    evidence = read_csv("Transferencia/evidencia_activos_transferencia.csv")
    for _, row in evidence.iterrows():
        add_record(
            records,
            source_key="evidencia_activos_transferencia",
            fuente=row_value(row, ["fuente"], default="Tabla evidencia transferencia"),
            tipo_evidencia=row_value(row, ["tipo_evidencia"], default="senal tematica"),
            titulo=row_value(row, ["titulo"]),
            resumen=row_value(row, ["resumen"]),
            identificador=row_value(row, ["identificador", "activo_id"]),
            url=row_value(row, ["url"]),
            fecha=row_value(row, ["fecha"]),
            relacion_cchen=f"Activo asociado: {row_value(row, ['activo_nombre'])}.",
            uso_observatorio=row_value(row, ["uso_transferencia"]),
            brecha=row_value(row, ["brecha"]),
            tema=row_value(row, ["activo_nombre", "tipo_evidencia"]),
            nivel_confianza="medio",
            source_path="Data/Transferencia/evidencia_activos_transferencia.csv",
        )


def build_index() -> pd.DataFrame:
    records: list[dict] = []
    add_openalex_publications(records)
    add_publication_source(
        records,
        "Publications/cchen_pubmed_works.csv",
        "pubmed_works",
        "PubMed",
        ["pmid", "pmcid"],
        ["pubmed_url"],
        "Publicacion CCHEN recuperada por afiliacion, DOI o termino institucional en PubMed.",
    )
    add_publication_source(
        records,
        "Publications/cchen_europmc_works.csv",
        "europmc_works",
        "Europe PMC",
        ["source_id", "pmid", "pmcid"],
        ["europmc_url"],
        "Publicacion CCHEN recuperada por afiliacion, DOI o termino institucional en Europe PMC.",
    )
    add_publication_source(
        records,
        "Publications/cchen_inspire_works.csv",
        "inspire_works",
        "INSPIRE-HEP",
        ["inspire_id", "arxiv_id"],
        ["inspire_url"],
        "Publicacion CCHEN recuperada en INSPIRE-HEP por busqueda controlada.",
    )
    add_publication_source(
        records,
        "Publications/cchen_arxiv_works.csv",
        "arxiv_works",
        "arXiv",
        ["arxiv_id"],
        ["arxiv_url"],
        "Preprint CCHEN recuperado por busqueda controlada en arXiv.",
    )
    add_publication_source(
        records,
        "Publications/cchen_semantic_scholar.csv",
        "semantic_scholar",
        "Semantic Scholar",
        ["ss_paper_id", "openalex_id"],
        ["openalex_id"],
        "Enriquecimiento Semantic Scholar sobre publicaciones CCHEN ya conocidas.",
    )
    add_crossref_unpaywall(records)
    add_outputs(records)
    add_radiofarmacia(records)
    add_projects_opportunities(records)
    add_internal_and_patents(records)
    add_transferencia_seed(records)

    df = pd.DataFrame(records)
    if df.empty:
        return pd.DataFrame(columns=INDEX_COLUMNS)
    df = df[INDEX_COLUMNS].copy()
    df = df.drop_duplicates(subset=["id"]).sort_values(["tipo_evidencia", "fuente", "fecha", "titulo"])
    return df.reset_index(drop=True)


def build_embeddings(df: pd.DataFrame, mode: str) -> dict:
    if df.empty:
        raise RuntimeError("No hay registros para vectorizar.")
    texts = df["texto_embedding"].fillna("").astype(str).tolist()
    requested = mode
    model_name = ""

    if mode in {"auto", "sentence-transformers"}:
        try:
            from sentence_transformers import SentenceTransformer

            model_name = "paraphrase-multilingual-MiniLM-L12-v2"
            model = SentenceTransformer(model_name)
            embeddings = model.encode(
                texts,
                batch_size=64,
                show_progress_bar=True,
                convert_to_numpy=True,
                normalize_embeddings=True,
            ).astype("float32")
            return {
                "embeddings": embeddings,
                "backend": "sentence-transformers",
                "model": model_name,
                "requested": requested,
            }
        except Exception as exc:
            if mode == "sentence-transformers":
                raise RuntimeError(f"No se pudo usar sentence-transformers: {exc}") from exc
            print(f"[WARN] sentence-transformers no disponible; usando TF-IDF + SVD. Detalle: {exc}")

    from joblib import dump
    from sklearn.decomposition import TruncatedSVD
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import Normalizer

    vectorizer = TfidfVectorizer(
        lowercase=True,
        strip_accents="unicode",
        ngram_range=(1, 2),
        min_df=2,
        max_df=0.95,
        max_features=30000,
        sublinear_tf=True,
    )
    tfidf = vectorizer.fit_transform(texts)
    max_components = max(2, min(tfidf.shape[0] - 1, tfidf.shape[1] - 1, 384))
    pipeline = make_pipeline(
        vectorizer,
        TruncatedSVD(n_components=max_components, random_state=42),
        Normalizer(copy=False),
    )
    embeddings = pipeline.fit_transform(texts).astype("float32")
    dump(pipeline, PIPELINE_PATH)
    return {
        "embeddings": embeddings,
        "backend": "tfidf-svd",
        "model": f"tfidf_svd_{max_components}",
        "requested": requested,
    }


def write_outputs(df: pd.DataFrame, *, build_vectors: bool, embedding_mode: str) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    GOVERNANCE_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(INDEX_PATH, index=False, encoding="utf-8-sig")
    summary = (
        df.groupby(["tipo_evidencia", "fuente"], dropna=False)
        .size()
        .reset_index(name="registros")
        .sort_values(["tipo_evidencia", "registros", "fuente"], ascending=[True, False, True])
    )
    summary.to_csv(SUMMARY_PATH, index=False, encoding="utf-8-sig")
    publicable_cols = [col for col in PUBLICABLE_COLUMNS if col in df.columns]
    df[publicable_cols].to_csv(PUBLICABLE_INDEX_PATH, index=False, encoding="utf-8-sig")
    summary.to_csv(PUBLICABLE_SUMMARY_PATH, index=False, encoding="utf-8-sig")

    state = {
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "records": int(len(df)),
        "sources": int(df["fuente"].nunique()) if not df.empty else 0,
        "types": df["tipo_evidencia"].value_counts().to_dict() if not df.empty else {},
        "outputs": {
            "index": str(INDEX_PATH.relative_to(ROOT)),
            "summary": str(SUMMARY_PATH.relative_to(ROOT)),
            "publicable_index": str(PUBLICABLE_INDEX_PATH.relative_to(ROOT)),
            "publicable_summary": str(PUBLICABLE_SUMMARY_PATH.relative_to(ROOT)),
        },
    }

    if build_vectors:
        result = build_embeddings(df, embedding_mode)
        np.save(EMB_PATH, result["embeddings"])
        meta_cols = [c for c in INDEX_COLUMNS if c != "texto_embedding"]
        df[meta_cols].to_csv(META_PATH, index=False, encoding="utf-8-sig")
        state["embedding"] = {
            "backend": result["backend"],
            "model": result["model"],
            "requested": result["requested"],
            "shape": list(result["embeddings"].shape),
            "embeddings": str(EMB_PATH.relative_to(ROOT)),
            "metadata": str(META_PATH.relative_to(ROOT)),
            "pipeline": str(PIPELINE_PATH.relative_to(ROOT)) if PIPELINE_PATH.exists() else "",
        }

    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-embeddings", action="store_true", help="Solo construye el CSV normalizado.")
    parser.add_argument(
        "--embedding-mode",
        choices=["auto", "sentence-transformers", "tfidf-svd"],
        default="auto",
        help="Backend para generar vectores. auto usa sentence-transformers si existe y si no TF-IDF + SVD.",
    )
    args = parser.parse_args()

    df = build_index()
    write_outputs(df, build_vectors=not args.no_embeddings, embedding_mode=args.embedding_mode)

    print(f"[OK] evidence_index: {len(df):,} registros")
    if not df.empty:
        print(df["tipo_evidencia"].value_counts().to_string())
    print(f"[OK] escrito: {INDEX_PATH}")
    if not args.no_embeddings:
        print(f"[OK] vectores: {EMB_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
