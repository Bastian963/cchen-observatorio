#!/usr/bin/env python3
"""Catálogo operativo de fuentes y snapshots locales del refresh."""

from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY_SNAPSHOT = ROOT / "Data" / "Gobernanza" / "data_sources_runtime.csv"
DEFAULT_RUNS_SNAPSHOT = ROOT / "Data" / "Gobernanza" / "data_source_runs.csv"
DEFAULT_REPORTS_DIR = ROOT / "Docs" / "reports" / "source_runs"

REGISTRY_COLUMNS = [
    "source_key",
    "source_name",
    "description",
    "url",
    "table_name",
    "notebook_path",
    "update_frequency",
    "freshness_sla_days",
    "requires_token",
    "token_source",
    "notes",
    "enabled",
    "runner_command",
    "output_targets",
    "owner",
    "visibility",
    "blocking",
    "job_key",
    "last_updated",
    "next_update_due",
    "record_count",
    "quality_score",
    "last_run_status",
    "last_run_id",
    "updated_at",
]

RUN_COLUMNS = [
    "run_id",
    "source_key",
    "trigger_kind",
    "started_at",
    "finished_at",
    "status",
    "records_written",
    "artifacts_json",
    "error_summary",
]

FREQUENCY_DAYS = {
    "diaria": 1,
    "semanal": 7,
    "quincenal": 14,
    "mensual": 30,
    "trimestral": 90,
    "semestral": 180,
    "anual": 365,
}

DEFAULT_OWNER = "observatorio-cchen"

SOURCE_DEFINITIONS: list[dict[str, object]] = [
    {
        "source_key": "openalex_publicaciones",
        "source_name": "OpenAlex publicaciones",
        "description": "Publicaciones científicas CCHEN indexadas en OpenAlex.",
        "url": "https://api.openalex.org",
        "table_name": "publications",
        "notebook_path": "Notebooks/01_Download_publications.ipynb",
        "update_frequency": "trimestral",
        "freshness_sla_days": 90,
        "requires_token": False,
        "token_source": "",
        "notes": "Script fetch automatizado via cursor pagination.",
        "enabled": True,
        "runner_command": "python Scripts/fetch_openalex.py && python Database/migrate_openalex.py",
        "output_targets": ["Data/Publications/cchen_openalex_works.csv",
                           "Data/Publications/openalex_state.json"],
        "owner": DEFAULT_OWNER,
        "visibility": "publico",
        "blocking": False,
        "job_key": "manual_openalex_publicaciones",
    },
    {
        "source_key": "crossref",
        "source_name": "CrossRef",
        "description": "Financiadores externos, abstracts y referencias por DOI.",
        "url": "https://api.crossref.org",
        "table_name": "crossref_data",
        "notebook_path": "Notebooks/02_CrossRef_enrichment.ipynb",
        "update_frequency": "trimestral",
        "freshness_sla_days": 90,
        "requires_token": False,
        "token_source": "",
        "notes": "Requiere fetch_openalex primero. Enriquece DOIs con CrossRef.",
        "enabled": True,
        "runner_command": "python Scripts/fetch_crossref.py && python Database/migrate_crossref.py",
        "output_targets": ["Data/Publications/cchen_crossref_enriched.csv",
                           "Data/Publications/crossref_state.json"],
        "owner": DEFAULT_OWNER,
        "visibility": "publico",
        "blocking": False,
        "job_key": "manual_crossref",
    },
    {
        "source_key": "openalex_conceptos",
        "source_name": "OpenAlex Conceptos",
        "description": "Conceptos y áreas temáticas por paper.",
        "url": "https://api.openalex.org",
        "table_name": "concepts",
        "notebook_path": "Notebooks/03_OpenAlex_concepts.ipynb",
        "update_frequency": "trimestral",
        "freshness_sla_days": 90,
        "requires_token": False,
        "token_source": "",
        "notes": "CSV generado por notebook; migrate automatizado.",
        "enabled": True,
        "runner_command": "python Database/migrate_openalex_concepts.py",
        "output_targets": ["Data/Publications/cchen_openalex_concepts.csv"],
        "owner": DEFAULT_OWNER,
        "visibility": "publico",
        "blocking": False,
        "job_key": "manual_openalex_conceptos",
    },
    {
        "source_key": "orcid",
        "source_name": "ORCID",
        "description": "Perfiles de investigadores CCHEN.",
        "url": "https://pub.orcid.org",
        "table_name": "researchers_orcid",
        "notebook_path": "Notebooks/04_ORCID_researchers.ipynb",
        "update_frequency": "semestral",
        "freshness_sla_days": 180,
        "requires_token": False,
        "token_source": "",
        "notes": "Script fetch automatizado. Búsqueda por afiliación + nombre.",
        "enabled": True,
        "runner_command": "python Scripts/fetch_orcid.py && python Database/migrate_orcid.py",
        "output_targets": ["Data/Researchers/cchen_researchers_orcid.csv",
                           "Data/Researchers/orcid_state.json"],
        "owner": DEFAULT_OWNER,
        "visibility": "publico",
        "blocking": False,
        "job_key": "manual_orcid",
    },
    {
        "source_key": "patentsview_uspto",
        "source_name": "PatentsView / USPTO",
        "description": "Patentes USPTO asociadas a CCHEN vía PatentsView.",
        "url": "https://search.patentsview.org/docs/",
        "table_name": "patents",
        "notebook_path": "Scripts/fetch_patentsview_patents.py",
        "update_frequency": "semestral",
        "freshness_sla_days": 180,
        "requires_token": True,
        "token_source": "PATENTSVIEW_API_KEY",
        "notes": "PATENTSVIEW_API_KEY configurado en GitHub Actions Secrets.",
        "enabled": True,
        "runner_command": "python Scripts/fetch_patentsview_patents.py && python Database/migrate_patentsview.py",
        "output_targets": ["Data/Patents/cchen_patents_uspto.csv"],
        "owner": DEFAULT_OWNER,
        "visibility": "publico",
        "blocking": False,
        "job_key": "fetch_patentsview",
    },
    {
        "source_key": "anid_repositorio",
        "source_name": "ANID Repositorio",
        "description": "Proyectos FONDECYT y otros fondos adjudicados.",
        "url": "https://repositorio.anid.cl",
        "table_name": "anid_projects",
        "notebook_path": "Notebooks/06_ANID_repository.ipynb",
        "update_frequency": "anual",
        "freshness_sla_days": 365,
        "requires_token": False,
        "token_source": "",
        "notes": "CSV descargado de repositorio ANID; migrate automatizado con columnas clave.",
        "enabled": True,
        "runner_command": "python Database/migrate_anid.py",
        "output_targets": ["Data/ANID/RepositorioAnid_con_monto.csv"],
        "owner": DEFAULT_OWNER,
        "visibility": "publico",
        "blocking": False,
        "job_key": "manual_anid_repositorio",
    },
    {
        "source_key": "datos_gob_convenios",
        "source_name": "datos.gob.cl convenios",
        "description": "Convenios nacionales suscritos por CCHEN.",
        "url": "https://datos.gob.cl",
        "table_name": "convenios_nacionales",
        "notebook_path": "",
        "update_frequency": "semestral",
        "freshness_sla_days": 180,
        "requires_token": False,
        "token_source": "",
        "notes": "CSV institucional curado; migrate automatizado.",
        "enabled": True,
        "runner_command": "python Database/migrate_convenios.py",
        "output_targets": ["Data/Institutional/clean_Convenios_suscritos_por_la_Com.csv"],
        "owner": DEFAULT_OWNER,
        "visibility": "publico",
        "blocking": False,
        "job_key": "manual_convenios",
    },
    {
        "source_key": "datos_gob_acuerdos",
        "source_name": "datos.gob.cl acuerdos",
        "description": "Acuerdos internacionales CCHEN.",
        "url": "https://datos.gob.cl",
        "table_name": "acuerdos_internacionales",
        "notebook_path": "",
        "update_frequency": "semestral",
        "freshness_sla_days": 180,
        "requires_token": False,
        "token_source": "",
        "notes": "CSV institucional multi-sección; migrate con parser normalizado.",
        "enabled": True,
        "runner_command": "python Database/migrate_acuerdos.py",
        "output_targets": ["Data/Institutional/clean_Acuerdos_e_instrumentos_intern.csv"],
        "owner": DEFAULT_OWNER,
        "visibility": "publico",
        "blocking": False,
        "job_key": "manual_acuerdos",
    },
    {
        "source_key": "ror_registry",
        "source_name": "ROR registry",
        "description": "Registro institucional normalizado con identificadores ROR.",
        "url": "https://ror.org",
        "table_name": "institution_registry",
        "notebook_path": "Scripts/build_ror_registry.py",
        "update_frequency": "semestral",
        "freshness_sla_days": 180,
        "requires_token": False,
        "token_source": "",
        "notes": "Comparte job con ROR pending review.",
        "enabled": True,
        "runner_command": "python Scripts/build_ror_registry.py",
        "output_targets": ["Data/Institutional/cchen_institution_registry.csv"],
        "owner": DEFAULT_OWNER,
        "visibility": "publico",
        "blocking": False,
        "job_key": "build_ror_registry",
    },
    {
        "source_key": "ror_pending_review",
        "source_name": "ROR pending review",
        "description": "Cola priorizada de instituciones sin ROR para curaduría manual.",
        "url": "https://ror.org",
        "table_name": "institution_registry_pending_review",
        "notebook_path": "Scripts/build_ror_registry.py",
        "update_frequency": "semestral",
        "freshness_sla_days": 180,
        "requires_token": False,
        "token_source": "",
        "notes": "Comparte job con ROR registry.",
        "enabled": True,
        "runner_command": "python Scripts/build_ror_registry.py",
        "output_targets": ["Data/Institutional/ror_pending_review.csv"],
        "owner": DEFAULT_OWNER,
        "visibility": "operador",
        "blocking": False,
        "job_key": "build_ror_registry",
    },
    {
        "source_key": "datacite_outputs",
        "source_name": "DataCite outputs",
        "description": "Datasets y outputs con DOI asociados a CCHEN vía ROR.",
        "url": "https://api.datacite.org",
        "table_name": "datacite_outputs",
        "notebook_path": "Scripts/fetch_datacite_outputs.py",
        "update_frequency": "semestral",
        "freshness_sla_days": 180,
        "requires_token": False,
        "token_source": "",
        "notes": "Refresh automatizable por script.",
        "enabled": True,
        "runner_command": "python Scripts/fetch_datacite_outputs.py",
        "output_targets": [
            "Data/ResearchOutputs/cchen_datacite_outputs.csv",
            "Data/ResearchOutputs/datacite_state.json",
        ],
        "owner": DEFAULT_OWNER,
        "visibility": "publico",
        "blocking": False,
        "job_key": "fetch_datacite_outputs",
    },
    {
        "source_key": "openaire_outputs",
        "source_name": "OpenAIRE outputs",
        "description": "Outputs asociados a investigadores CCHEN vía ORCID en OpenAIRE.",
        "url": "https://api.openaire.eu",
        "table_name": "openaire_outputs",
        "notebook_path": "Scripts/fetch_openaire_outputs.py",
        "update_frequency": "semestral",
        "freshness_sla_days": 180,
        "requires_token": False,
        "token_source": "",
        "notes": "Refresh automatizable por script.",
        "enabled": True,
        "runner_command": "python Scripts/fetch_openaire_outputs.py && python Database/migrate_openaire.py",
        "output_targets": [
            "Data/ResearchOutputs/cchen_openaire_outputs.csv",
            "Data/ResearchOutputs/openaire_state.json",
        ],
        "owner": DEFAULT_OWNER,
        "visibility": "publico",
        "blocking": False,
        "job_key": "fetch_openaire_outputs",
    },
    {
        "source_key": "zenodo_outputs",
        "source_name": "Zenodo outputs",
        "description": "Metadatos de outputs institucionales CCHEN publicados en Zenodo.",
        "url": "https://zenodo.org/api",
        "table_name": "zenodo_outputs",
        "notebook_path": "Scripts/fetch_zenodo_cchen_metadata.py",
        "update_frequency": "semestral",
        "freshness_sla_days": 180,
        "requires_token": False,
        "token_source": "ZENODO_TOKEN",
        "notes": "Metadata-only: busca aliases CCHEN, no descarga archivos; token opcional para limites de API.",
        "enabled": True,
        "runner_command": "python Scripts/fetch_zenodo_cchen_metadata.py && python Scripts/curate_zenodo_cchen_metadata.py",
        "output_targets": [
            "Data/ResearchOutputs/cchen_zenodo_metadata.csv",
            "Data/ResearchOutputs/cchen_zenodo_files.csv",
            "Data/ResearchOutputs/zenodo_cchen_state.json",
            "Data/Gobernanza/curaduria_zenodo_cchen.csv",
        ],
        "owner": DEFAULT_OWNER,
        "visibility": "publico",
        "blocking": False,
        "job_key": "fetch_zenodo_outputs",
    },
    {
        "source_key": "sjr_scimago",
        "source_name": "SJR Scimago",
        "description": "Rankings y cuartiles de revistas científicas (26 años, 1999-2024).",
        "url": "https://www.scimagojr.com",
        "table_name": "sjr_journal_rankings",
        "notebook_path": "Database/migrate_sjr.py",
        "update_frequency": "anual",
        "freshness_sla_days": 365,
        "requires_token": False,
        "token_source": "",
        "notes": "CSVs locales en Data/scimagojr/; migrate carga todos los años disponibles.",
        "enabled": True,
        "runner_command": "python Database/migrate_sjr.py",
        "output_targets": ["Data/scimagojr/"],
        "owner": DEFAULT_OWNER,
        "visibility": "publico",
        "blocking": False,
        "job_key": "migrate_sjr",
    },
    {
        "source_key": "perfiles_institucionales",
        "source_name": "Perfiles institucionales",
        "description": "Perfiles institucionales base para matching y priorización.",
        "url": "",
        "table_name": "perfiles_institucionales",
        "notebook_path": "Data/Vigilancia/perfiles_institucionales_cchen.csv",
        "update_frequency": "semanal",
        "freshness_sla_days": 8,
        "requires_token": False,
        "token_source": "",
        "notes": "Semilla curada; se mantiene manual en esta fase.",
        "enabled": False,
        "runner_command": "",
        "output_targets": ["Data/Vigilancia/perfiles_institucionales_cchen.csv"],
        "owner": DEFAULT_OWNER,
        "visibility": "operador",
        "blocking": False,
        "job_key": "manual_perfiles_institucionales",
    },
    {
        "source_key": "convocatorias_curadas",
        "source_name": "Convocatorias curadas",
        "description": "Calendario curado de convocatorias relevantes para CCHEN.",
        "url": "https://anid.cl/calendario-concursos-2026/",
        "table_name": "convocatorias",
        "notebook_path": "Scripts/convocatorias_monitor.py",
        "update_frequency": "semanal",
        "freshness_sla_days": 14,
        "requires_token": False,
        "token_source": "",
        "notes": "Fuente crítica para la mesa DGIn.",
        "enabled": True,
        "runner_command": "python Scripts/convocatorias_monitor.py && python Database/migrate_convocatorias.py",
        "output_targets": ["Data/Vigilancia/convocatorias_curadas.csv"],
        "owner": DEFAULT_OWNER,
        "visibility": "publico",
        "blocking": True,
        "job_key": "convocatorias_refresh",
    },
    {
        "source_key": "matching_rules",
        "source_name": "Reglas de matching",
        "description": "Reglas explícitas de elegibilidad y alias para matching institucional.",
        "url": "",
        "table_name": "convocatorias_matching_rules",
        "notebook_path": "Data/Vigilancia/convocatorias_matching_rules.csv",
        "update_frequency": "semanal",
        "freshness_sla_days": 14,
        "requires_token": False,
        "token_source": "",
        "notes": "Semilla manual; no entra al scheduler por ahora.",
        "enabled": False,
        "runner_command": "",
        "output_targets": ["Data/Vigilancia/convocatorias_matching_rules.csv"],
        "owner": DEFAULT_OWNER,
        "visibility": "operador",
        "blocking": False,
        "job_key": "manual_matching_rules",
    },
    {
        "source_key": "matching_institucional",
        "source_name": "Matching institucional",
        "description": "Scoring formal de convocatorias abiertas y próximas para CCHEN.",
        "url": "",
        "table_name": "convocatorias_matching_institucional",
        "notebook_path": "Scripts/build_operational_core.py",
        "update_frequency": "semanal",
        "freshness_sla_days": 8,
        "requires_token": False,
        "token_source": "",
        "notes": "Comparte job con entity registry y entity links.",
        "enabled": True,
        "runner_command": "python Scripts/build_operational_core.py",
        "output_targets": ["Data/Vigilancia/convocatorias_matching_institucional.csv"],
        "owner": DEFAULT_OWNER,
        "visibility": "publico",
        "blocking": True,
        "job_key": "build_operational_core",
    },
    {
        "source_key": "iaea_inis_monitor",
        "source_name": "IAEA INIS monitor",
        "description": "Monitoreo de literatura INIS relevante a CCHEN.",
        "url": "https://inis.iaea.org",
        "table_name": "iaea_inis_monitor",
        "notebook_path": "Scripts/iaea_inis_monitor.py",
        "update_frequency": "semanal",
        "freshness_sla_days": 30,
        "requires_token": False,
        "token_source": "",
        "notes": "Fuente best-effort por estabilidad externa.",
        "enabled": True,
        "runner_command": "python Scripts/iaea_inis_monitor.py && python Database/migrate_vigilancia.py",
        "output_targets": [
            "Data/Vigilancia/iaea_inis_monitor.csv",
            "Data/Vigilancia/iaea_inis_state.json",
        ],
        "owner": DEFAULT_OWNER,
        "visibility": "publico",
        "blocking": False,
        "job_key": "iaea_inis_refresh",
    },
    {
        "source_key": "arxiv_monitor",
        "source_name": "arXiv monitor",
        "description": "Monitoreo de papers arXiv relevantes al observatorio.",
        "url": "https://arxiv.org",
        "table_name": "arxiv_monitor",
        "notebook_path": "Scripts/arxiv_monitor.py",
        "update_frequency": "semanal",
        "freshness_sla_days": 8,
        "requires_token": False,
        "token_source": "",
        "notes": "Fuente crítica para vigilancia tecnológica.",
        "enabled": True,
        "runner_command": "python Scripts/arxiv_monitor.py && python Database/migrate_vigilancia.py",
        "output_targets": ["Data/Vigilancia/arxiv_monitor.csv"],
        "owner": DEFAULT_OWNER,
        "visibility": "publico",
        "blocking": True,
        "job_key": "arxiv_monitor_refresh",
    },
    {
        "source_key": "news_monitor",
        "source_name": "News monitor",
        "description": "Monitoreo de prensa y noticias sobre CCHEN y energía nuclear.",
        "url": "https://news.google.com",
        "table_name": "news_monitor",
        "notebook_path": "Scripts/news_monitor.py",
        "update_frequency": "semanal",
        "freshness_sla_days": 8,
        "requires_token": False,
        "token_source": "",
        "notes": "Fuente crítica para vigilancia tecnológica.",
        "enabled": True,
        "runner_command": "python Scripts/news_monitor.py && python Database/migrate_vigilancia.py",
        "output_targets": ["Data/Vigilancia/news_monitor.csv"],
        "owner": DEFAULT_OWNER,
        "visibility": "publico",
        "blocking": True,
        "job_key": "news_monitor_refresh",
    },
    {
        "source_key": "citation_graph",
        "source_name": "Citation graph",
        "description": "Resumen de citas y referencias de publicaciones CCHEN en OpenAlex.",
        "url": "https://api.openalex.org",
        "table_name": "citation_graph",
        "notebook_path": "Scripts/fetch_openalex_citations.py",
        "update_frequency": "trimestral",
        "freshness_sla_days": 90,
        "requires_token": False,
        "token_source": "",
        "notes": "Comparte job con OpenAlex Citations.",
        "enabled": True,
        "runner_command": "python Scripts/fetch_openalex_citations.py && python Database/migrate_vigilancia.py && python Database/migrate_citing_papers.py",
        "output_targets": ["Data/Publications/cchen_citation_graph.csv"],
        "owner": DEFAULT_OWNER,
        "visibility": "publico",
        "blocking": False,
        "job_key": "openalex_citations_refresh",
    },
    {
        "source_key": "europmc_works",
        "source_name": "EuroPMC works",
        "description": "Outputs CCHEN identificados en EuroPMC.",
        "url": "https://europepmc.org",
        "table_name": "europmc_works",
        "notebook_path": "Scripts/fetch_europmc.py",
        "update_frequency": "semestral",
        "freshness_sla_days": 180,
        "requires_token": False,
        "token_source": "",
        "notes": "Refresh automatizable por script.",
        "enabled": True,
        "runner_command": "python Scripts/fetch_europmc.py && python Database/migrate_europmc.py",
        "output_targets": [
            "Data/Publications/cchen_europmc_works.csv",
            "Data/Publications/europmc_state.json",
        ],
        "owner": DEFAULT_OWNER,
        "visibility": "publico",
        "blocking": False,
        "job_key": "fetch_europmc",
    },
    {
        "source_key": "bertopic_topics",
        "source_name": "BERTopic topics",
        "description": "Asignación temática BERTopic por publicación CCHEN.",
        "url": "",
        "table_name": "bertopic_topics",
        "notebook_path": "Scripts/run_bertopic.py",
        "update_frequency": "trimestral",
        "freshness_sla_days": 90,
        "requires_token": False,
        "token_source": "",
        "notes": "Derivado analítico; se mantiene manual para no cargar el scheduler.",
        "enabled": False,
        "runner_command": "",
        "output_targets": ["Data/Publications/cchen_bertopic_topics.csv"],
        "owner": DEFAULT_OWNER,
        "visibility": "publico",
        "blocking": False,
        "job_key": "manual_bertopic",
    },
    {
        "source_key": "bertopic_topic_info",
        "source_name": "BERTopic topic info",
        "description": "Metadatos y términos representativos de temas BERTopic.",
        "url": "",
        "table_name": "bertopic_topic_info",
        "notebook_path": "Scripts/run_bertopic.py",
        "update_frequency": "trimestral",
        "freshness_sla_days": 90,
        "requires_token": False,
        "token_source": "",
        "notes": "Derivado analítico; se mantiene manual para no cargar el scheduler.",
        "enabled": False,
        "runner_command": "",
        "output_targets": ["Data/Publications/cchen_bertopic_topic_info.csv"],
        "owner": DEFAULT_OWNER,
        "visibility": "publico",
        "blocking": False,
        "job_key": "manual_bertopic",
    },
    {
        "source_key": "openalex_citations",
        "source_name": "OpenAlex Citations",
        "description": "Papers externos que citan publicaciones CCHEN.",
        "url": "https://api.openalex.org",
        "table_name": "citing_papers",
        "notebook_path": "Scripts/fetch_openalex_citations.py",
        "update_frequency": "trimestral",
        "freshness_sla_days": 90,
        "requires_token": False,
        "token_source": "",
        "notes": "Comparte job con Citation graph.",
        "enabled": True,
        "runner_command": "python Scripts/fetch_openalex_citations.py && python Database/migrate_vigilancia.py && python Database/migrate_citing_papers.py",
        "output_targets": ["Data/Publications/cchen_citing_papers.csv"],
        "owner": DEFAULT_OWNER,
        "visibility": "publico",
        "blocking": False,
        "job_key": "openalex_citations_refresh",
    },
    {
        "source_key": "funding_complementario",
        "source_name": "Financiamiento complementario",
        "description": "CORFO, IAEA TC y otros fondos curados con elegibilidad y confianza.",
        "url": "",
        "table_name": "funding_complementario",
        "notebook_path": "Scripts/fetch_funding_plus.py",
        "update_frequency": "semestral",
        "freshness_sla_days": 180,
        "requires_token": False,
        "token_source": "",
        "notes": "Refresh automatizable por script reproducible.",
        "enabled": True,
        "runner_command": "python Scripts/fetch_funding_plus.py",
        "output_targets": ["Data/Funding/cchen_funding_complementario.csv"],
        "owner": DEFAULT_OWNER,
        "visibility": "interno",
        "blocking": False,
        "job_key": "fetch_funding_plus",
    },
    {
        "source_key": "entity_registry_personas",
        "source_name": "Entity registry personas",
        "description": "Registro canónico de personas del observatorio.",
        "url": "",
        "table_name": "entity_registry_personas",
        "notebook_path": "Scripts/build_operational_core.py",
        "update_frequency": "semanal",
        "freshness_sla_days": 14,
        "requires_token": False,
        "token_source": "",
        "notes": "Comparte job con matching institucional y demás registros operativos.",
        "enabled": True,
        "runner_command": "python Scripts/build_operational_core.py",
        "output_targets": ["Data/Gobernanza/entity_registry_personas.csv"],
        "owner": DEFAULT_OWNER,
        "visibility": "interno",
        "blocking": True,
        "job_key": "build_operational_core",
    },
    {
        "source_key": "entity_registry_proyectos",
        "source_name": "Entity registry proyectos",
        "description": "Registro canónico de proyectos adjudicados y asociados.",
        "url": "",
        "table_name": "entity_registry_proyectos",
        "notebook_path": "Scripts/build_operational_core.py",
        "update_frequency": "semanal",
        "freshness_sla_days": 14,
        "requires_token": False,
        "token_source": "",
        "notes": "Comparte job con matching institucional y demás registros operativos.",
        "enabled": True,
        "runner_command": "python Scripts/build_operational_core.py",
        "output_targets": ["Data/Gobernanza/entity_registry_proyectos.csv"],
        "owner": DEFAULT_OWNER,
        "visibility": "publico",
        "blocking": True,
        "job_key": "build_operational_core",
    },
    {
        "source_key": "entity_registry_convocatorias",
        "source_name": "Entity registry convocatorias",
        "description": "Registro canónico de convocatorias curadas.",
        "url": "",
        "table_name": "entity_registry_convocatorias",
        "notebook_path": "Scripts/build_operational_core.py",
        "update_frequency": "semanal",
        "freshness_sla_days": 14,
        "requires_token": False,
        "token_source": "",
        "notes": "Comparte job con matching institucional y demás registros operativos.",
        "enabled": True,
        "runner_command": "python Scripts/build_operational_core.py",
        "output_targets": ["Data/Gobernanza/entity_registry_convocatorias.csv"],
        "owner": DEFAULT_OWNER,
        "visibility": "publico",
        "blocking": True,
        "job_key": "build_operational_core",
    },
    {
        "source_key": "entity_links",
        "source_name": "Entity links",
        "description": "Relaciones operativas entre entidades canónicas del observatorio.",
        "url": "",
        "table_name": "entity_links",
        "notebook_path": "Scripts/build_operational_core.py",
        "update_frequency": "semanal",
        "freshness_sla_days": 14,
        "requires_token": False,
        "token_source": "",
        "notes": "Comparte job con matching institucional y demás registros operativos.",
        "enabled": True,
        "runner_command": "python Scripts/build_operational_core.py",
        "output_targets": ["Data/Gobernanza/entity_links.csv"],
        "owner": DEFAULT_OWNER,
        "visibility": "interno",
        "blocking": True,
        "job_key": "build_operational_core",
    },
    {
        "source_key": "capital_humano",
        "source_name": "Capital humano",
        "description": "Registro interno consolidado de formación de capital humano CCHEN.",
        "url": "",
        "table_name": "capital_humano",
        "notebook_path": "Scripts/build_capital_humano_dataset.py",
        "update_frequency": "semestral",
        "freshness_sla_days": 180,
        "requires_token": False,
        "token_source": "",
        "notes": "Excel interno sensible; builder local genera CSV canónico y migración usa service role.",
        "enabled": True,
        "runner_command": "python Scripts/build_capital_humano_dataset.py && python Database/migrate_capital_humano.py",
        "output_targets": [
            "Data/Capital humano CCHEN/salida_dataset_maestro/dataset_maestro_limpio.csv",
            "Data/Capital humano CCHEN/salida_dataset_maestro/resumen_ejecutivo.json",
            "Data/Capital humano CCHEN/salida_dataset_maestro/analisis_avanzado/resumen_analisis_avanzado.json",
            "Data/Capital humano CCHEN/salida_dataset_maestro/analisis_avanzado/cumplimiento_documental_centros.csv",
            "Data/Capital humano CCHEN/salida_dataset_maestro/analisis_avanzado/transiciones_modalidad.csv",
        ],
        "owner": DEFAULT_OWNER,
        "visibility": "interno",
        "blocking": False,
        "job_key": "capital_humano_refresh",
    },
    {
        "source_key": "dian_publications",
        "source_name": "Publicaciones DIAN",
        "description": "Registro interno DIAN de publicaciones científicas CCHEN.",
        "url": "",
        "table_name": "dian_publications",
        "notebook_path": "Database/migrate_dian.py",
        "update_frequency": "mensual",
        "freshness_sla_days": 30,
        "requires_token": False,
        "token_source": "",
        "notes": "Migra la hoja Consolidado del Excel interno Publicaciones DIAN.xlsx y deja CSV local canónico.",
        "enabled": True,
        "runner_command": "python Database/migrate_dian.py",
        "output_targets": ["Data/Publications/cchen_dian_publications.csv"],
        "owner": DEFAULT_OWNER,
        "visibility": "publico",
        "blocking": False,
        "job_key": "dian_publications_refresh",
    },
    {
        "source_key": "pubmed_works",
        "source_name": "PubMed works",
        "description": "Publicaciones CCHEN indexadas en PubMed (medicina nuclear, dosimetría, radiofármacos).",
        "url": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/",
        "table_name": "pubmed_works",
        "notebook_path": "Scripts/fetch_pubmed.py",
        "update_frequency": "semestral",
        "freshness_sla_days": 180,
        "requires_token": False,
        "token_source": "",
        "notes": "Refresh automatizable por script. Sin API key: límite 3 req/s.",
        "enabled": True,
        "runner_command": "python Scripts/fetch_pubmed.py && python Database/migrate_pubmed.py",
        "output_targets": [
            "Data/Publications/cchen_pubmed_works.csv",
            "Data/Publications/pubmed_state.json",
        ],
        "owner": DEFAULT_OWNER,
        "visibility": "publico",
        "blocking": False,
        "job_key": "fetch_pubmed",
    },
    {
        "source_key": "inspire_works",
        "source_name": "INSPIRE-HEP works",
        "description": "Publicaciones CCHEN en INSPIRE-HEP (física nuclear estructural, decaimiento beta).",
        "url": "https://inspirehep.net/api/literature",
        "table_name": "inspire_works",
        "notebook_path": "Scripts/fetch_inspire.py",
        "update_frequency": "semestral",
        "freshness_sla_days": 180,
        "requires_token": False,
        "token_source": "",
        "notes": "Refresh automatizable. ~21 papers; búsqueda texto libre (aff: no funciona para CCHEN).",
        "enabled": True,
        "runner_command": "python Scripts/fetch_inspire.py && python Database/migrate_inspire.py",
        "output_targets": [
            "Data/Publications/cchen_inspire_works.csv",
            "Data/Publications/inspire_state.json",
        ],
        "owner": DEFAULT_OWNER,
        "visibility": "publico",
        "blocking": False,
        "job_key": "fetch_inspire",
    },
    {
        "source_key": "arxiv_works",
        "source_name": "arXiv works",
        "description": "Preprints CCHEN en arXiv (física nuclear, medicina nuclear, dosimetría).",
        "url": "https://export.arxiv.org/api/query",
        "table_name": "arxiv_works",
        "notebook_path": "Scripts/fetch_arxiv.py",
        "update_frequency": "semestral",
        "freshness_sla_days": 180,
        "requires_token": False,
        "token_source": "",
        "notes": "Rate limit ≥3s por request. Sin API key.",
        "enabled": True,
        "runner_command": "python Scripts/fetch_arxiv.py && python Database/migrate_arxiv.py",
        "output_targets": [
            "Data/Publications/cchen_arxiv_works.csv",
            "Data/Publications/arxiv_state.json",
        ],
        "owner": DEFAULT_OWNER,
        "visibility": "publico",
        "blocking": False,
        "job_key": "fetch_arxiv",
    },
    {
        "source_key": "semantic_scholar",
        "source_name": "Semantic Scholar",
        "description": "Abstracts y TLDRs de publicaciones CCHEN vía Semantic Scholar API.",
        "url": "https://api.semanticscholar.org/graph/v1/",
        "table_name": "semantic_scholar_papers",
        "notebook_path": "Scripts/fetch_semantic_scholar.py",
        "update_frequency": "trimestral",
        "freshness_sla_days": 90,
        "requires_token": False,
        "token_source": "",
        "notes": "Sin API key: 100 req/5min (~4s entre batches). Enriquece con abstract y TLDR.",
        "enabled": True,
        "runner_command": "python Scripts/fetch_semantic_scholar.py && python Database/migrate_semantic_scholar.py",
        "output_targets": ["Data/Publications/cchen_semantic_scholar.csv"],
        "owner": DEFAULT_OWNER,
        "visibility": "publico",
        "blocking": False,
        "job_key": "fetch_semantic_scholar",
    },
    {
        "source_key": "altmetric",
        "source_name": "Altmetric",
        "description": "Métricas de impacto alternativo (noticias, redes, políticas, Wikipedia) por DOI.",
        "url": "https://api.altmetric.com/v1/",
        "table_name": "altmetric_scores",
        "notebook_path": "Scripts/fetch_altmetric.py",
        "update_frequency": "trimestral",
        "freshness_sla_days": 90,
        "requires_token": False,
        "token_source": "",
        "notes": "Sin API key: ~1 req/s. Solo papers con DOI y score Altmetric registrado.",
        "enabled": True,
        "runner_command": "python Scripts/fetch_altmetric.py && python Database/migrate_altmetric.py",
        "output_targets": [
            "Data/Publications/cchen_altmetric.csv",
            "Data/Publications/altmetric_state.json",
        ],
        "owner": DEFAULT_OWNER,
        "visibility": "publico",
        "blocking": False,
        "job_key": "fetch_altmetric",
    },
    {
        "source_key": "unpaywall_oa",
        "source_name": "Unpaywall OA",
        "description": "Estado de acceso abierto de publicaciones CCHEN por DOI.",
        "url": "https://api.unpaywall.org/v2",
        "table_name": "unpaywall_oa",
        "notebook_path": "Scripts/enrich_unpaywall.py",
        "update_frequency": "semestral",
        "freshness_sla_days": 180,
        "requires_token": False,
        "token_source": "",
        "notes": "API gratuita; requiere email de contacto. Fuente CCHEN-only porque parte de DOIs CCHEN ya conocidos.",
        "enabled": True,
        "runner_command": "python Scripts/enrich_unpaywall.py --only-missing",
        "output_targets": ["Data/Publications/cchen_unpaywall_oa.csv"],
        "owner": DEFAULT_OWNER,
        "visibility": "publico",
        "blocking": False,
        "job_key": "fetch_unpaywall_oa",
    },
    {
        "source_key": "fernanda_free_api_candidates",
        "source_name": "Fuentes Fernanda API gratuita CCHEN-only",
        "description": "Prueba controlada de APIs gratuitas de la planilla Fernanda con filtros/aliases CCHEN.",
        "url": "https://doaj.org/api/v4/; https://api.hal.science; https://api.figshare.com/v2; https://api.core.ac.uk/v3",
        "table_name": "fernanda_free_api_candidates",
        "notebook_path": "Scripts/fetch_fernanda_free_api_candidates.py",
        "update_frequency": "semestral",
        "freshness_sla_days": 180,
        "requires_token": False,
        "token_source": "",
        "notes": "Incluye DOAJ, HAL, Figshare, CORE, BASE y UniProt; documenta bioRxiv/medRxiv/PubChem/STRING/EPO/WIPO cuando no hay filtro CCHEN seguro.",
        "enabled": True,
        "runner_command": "python Scripts/fetch_fernanda_free_api_candidates.py && python Scripts/curate_fernanda_api_cchen_records.py && python Scripts/review_fernanda_api_cchen_records.py",
        "output_targets": [
            "Data/Gobernanza/fuentes_fernanda_api_cchen_records.csv",
            "Data/Gobernanza/fuentes_fernanda_api_cchen_status.csv",
            "Data/Gobernanza/fuentes_fernanda_api_cchen_state.json",
            "Data/Gobernanza/curaduria_fuentes_fernanda_api_cchen.csv",
            "Data/Gobernanza/revision_fuentes_fernanda_api_cchen.csv",
        ],
        "owner": DEFAULT_OWNER,
        "visibility": "publico",
        "blocking": False,
        "job_key": "fetch_fernanda_free_api_candidates",
    },
    {
        "source_key": "repositorios_cchen_outputs_master",
        "source_name": "Outputs repositorios CCHEN master",
        "description": "Tabla maestra auditable de outputs CCHEN desde Zenodo, DOAJ, HAL y CORE.",
        "url": "https://zenodo.org/api; https://doaj.org/api/v4/; https://api.hal.science; https://api.core.ac.uk/v3",
        "table_name": "outputs_repositorios_cchen_master",
        "notebook_path": "Scripts/build_repositorios_cchen_outputs_master.py",
        "update_frequency": "semestral",
        "freshness_sla_days": 180,
        "requires_token": False,
        "token_source": "",
        "notes": "Fuente derivada: no llama APIs externas; normaliza resultados ya extraidos/curados y separa tablero, auditoria y descartes.",
        "enabled": True,
        "runner_command": "python Scripts/build_repositorios_cchen_outputs_master.py",
        "output_targets": [
            "Data/Gobernanza/outputs_repositorios_cchen_master.csv",
            "Data/Gobernanza/outputs_repositorios_cchen_publicables.csv",
            "Data/Gobernanza/outputs_repositorios_cchen_summary.csv",
            "Docs/reports/metodologia_outputs_repositorios_cchen.md",
        ],
        "owner": DEFAULT_OWNER,
        "visibility": "publico",
        "blocking": False,
        "job_key": "build_repositorios_cchen_outputs_master",
    },
    {
        "source_key": "radiofarmacia_cchen_seeded",
        "source_name": "Radiofarmacia CCHEN seeded",
        "description": "Extracción semilla de radiofármacos, radionúclidos y literatura clínica/técnica útil para CCHEN.",
        "url": "https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest; https://europepmc.org/RestfulWebService; https://eutils.ncbi.nlm.nih.gov/entrez/eutils/",
        "table_name": "radiofarmacia_cchen_seeded",
        "notebook_path": "Scripts/fetch_radiofarmacia_cchen_seeded.py",
        "update_frequency": "trimestral",
        "freshness_sla_days": 90,
        "requires_token": False,
        "token_source": "",
        "notes": "No descarga Bio/Farma completo: usa semillas controladas F-18 FDG, Ga-68, Lu-177, Tc-99m, I-131, ciclotrón, control de calidad y dosimetría.",
        "enabled": True,
        "runner_command": "python Scripts/fetch_radiofarmacia_cchen_seeded.py --max-literature-per-seed 20 && python Scripts/curate_radiofarmacia_cchen.py && python Scripts/review_radiofarmacia_cchen.py",
        "output_targets": [
            "Data/Gobernanza/radiofarmacia_cchen_seeds.csv",
            "Data/Gobernanza/radiofarmacia_cchen_pubchem_compounds.csv",
            "Data/Gobernanza/radiofarmacia_cchen_literature.csv",
            "Data/Gobernanza/radiofarmacia_cchen_status.csv",
            "Data/Gobernanza/radiofarmacia_cchen_state.json",
            "Data/Gobernanza/radiofarmacia_cchen_literature_curated.csv",
            "Data/Gobernanza/radiofarmacia_cchen_compounds_curated.csv",
            "Data/Gobernanza/radiofarmacia_cchen_curation_summary.csv",
            "Data/Gobernanza/radiofarmacia_cchen_literature_reviewed.csv",
            "Data/Gobernanza/radiofarmacia_cchen_review_summary.csv",
            "Docs/reports/metodologia_curaduria_radiofarmacia_cchen.md",
            "Docs/reports/metodologia_revision_radiofarmacia_cchen.md",
        ],
        "owner": DEFAULT_OWNER,
        "visibility": "publico",
        "blocking": False,
        "job_key": "fetch_radiofarmacia_cchen_seeded",
    },
    {
        "source_key": "semantic_evidence_index",
        "source_name": "Índice maestro de evidencia semántica",
        "description": "Tabla unificada y vectores para búsqueda de evidencia CCHEN en gestión de investigación e innovación.",
        "url": "",
        "table_name": "semantic_evidence_index",
        "notebook_path": "Scripts/build_evidence_index.py",
        "update_frequency": "semanal",
        "freshness_sla_days": 14,
        "requires_token": False,
        "token_source": "",
        "notes": "Fuente derivada: normaliza datos CCHEN ya extraídos/curados y genera vectores para Streamlit y el asistente LLM.",
        "enabled": True,
        "runner_command": "python Scripts/build_evidence_index.py --embedding-mode auto && python Scripts/check_evidence_index.py",
        "output_targets": [
            "Data/Semantic/evidence_index.csv",
            "Data/Semantic/evidence_embeddings.npy",
            "Data/Semantic/evidence_index_state.json",
            "Data/Gobernanza/evidence_index_publicable.csv",
            "Data/Gobernanza/evidence_index_publicable_summary.csv",
        ],
        "owner": DEFAULT_OWNER,
        "visibility": "interno",
        "blocking": False,
        "job_key": "build_semantic_evidence_index",
    },
]


def frequency_to_days(value: object) -> int | None:
    text = str(value or "").strip().lower()
    return FREQUENCY_DAYS.get(text)


def registry_snapshot_path() -> Path:
    override = os.getenv("OBSERVATORIO_SOURCE_REGISTRY_CSV", "").strip()
    return Path(override) if override else DEFAULT_REGISTRY_SNAPSHOT


def runs_snapshot_path() -> Path:
    override = os.getenv("OBSERVATORIO_SOURCE_RUNS_CSV", "").strip()
    return Path(override) if override else DEFAULT_RUNS_SNAPSHOT


def reports_dir() -> Path:
    override = os.getenv("OBSERVATORIO_SOURCE_REPORTS_DIR", "").strip()
    return Path(override) if override else DEFAULT_REPORTS_DIR


def _coerce_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if pd.isna(value):
        return False
    return str(value).strip().lower() in {"1", "true", "t", "yes", "y", "si", "sí"}


def _serialize_targets(value: object) -> str:
    if isinstance(value, str):
        text = value.strip()
        if text.startswith("["):
            return text
        if not text:
            return "[]"
        return json.dumps([text], ensure_ascii=False)
    if isinstance(value, (list, tuple, set)):
        return json.dumps([str(item) for item in value], ensure_ascii=False)
    return "[]"


def parse_output_targets(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value or "").strip()
    if not text:
        return []
    if text.startswith("["):
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                return [str(item).strip() for item in parsed if str(item).strip()]
        except json.JSONDecodeError:
            pass
    return [chunk.strip() for chunk in text.split(";") if chunk.strip()]


def _path_for(target: str) -> Path:
    path = Path(target)
    return path if path.is_absolute() else ROOT / path


def _freshest_output_date(targets: list[str]) -> dt.date | None:
    dates: list[dt.date] = []
    for target in targets:
        path = _path_for(target)
        if not path.exists():
            continue
        try:
            mtime = dt.datetime.fromtimestamp(path.stat().st_mtime)
            dates.append(mtime.date())
        except OSError:
            continue
    return max(dates) if dates else None


def _estimate_output_records(targets: list[str]) -> int:
    total = 0
    for target in targets:
        path = _path_for(target)
        if not path.exists():
            continue
        if path.is_dir():
            total += sum(1 for _ in path.iterdir())
            continue
        if path.suffix.lower() != ".csv":
            continue
        try:
            total += max(sum(1 for _ in path.open("r", encoding="utf-8-sig")) - 1, 0)
        except UnicodeDecodeError:
            try:
                total += max(sum(1 for _ in path.open("r", encoding="utf-8")) - 1, 0)
            except OSError:
                continue
        except OSError:
            continue
    return total


def _compute_next_due(last_updated: dt.date | None, frequency: str, freshness_sla_days: int | None) -> str:
    if last_updated is None:
        return ""
    delta_days = frequency_to_days(frequency) or freshness_sla_days or 0
    if delta_days <= 0:
        return ""
    return (last_updated + dt.timedelta(days=delta_days)).isoformat()


def _normalize_registry_frame(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for column in REGISTRY_COLUMNS:
        if column not in out.columns:
            out[column] = pd.Series(dtype="object")
    for column in ("enabled", "blocking", "requires_token"):
        out[column] = out[column].map(_coerce_bool)
    out["freshness_sla_days"] = pd.to_numeric(out["freshness_sla_days"], errors="coerce").astype("Int64")
    out["record_count"] = pd.to_numeric(out["record_count"], errors="coerce").fillna(0).astype(int)
    out["quality_score"] = pd.to_numeric(out["quality_score"], errors="coerce")
    out["output_targets"] = out["output_targets"].map(_serialize_targets)
    return out[REGISTRY_COLUMNS]


def build_registry_frame(existing_df: pd.DataFrame | None = None) -> pd.DataFrame:
    existing_lookup = {}
    if existing_df is not None and not existing_df.empty and "source_key" in existing_df.columns:
        normalized_existing = _normalize_registry_frame(existing_df)
        existing_lookup = {
            str(row["source_key"]).strip(): row
            for _, row in normalized_existing.iterrows()
        }

    now_iso = dt.datetime.now().isoformat(timespec="seconds")
    rows: list[dict[str, object]] = []
    for definition in SOURCE_DEFINITIONS:
        row = {column: definition.get(column, "") for column in REGISTRY_COLUMNS}
        row["output_targets"] = _serialize_targets(definition.get("output_targets", []))

        existing = existing_lookup.get(str(definition["source_key"]))
        if existing is not None:
            for runtime_field in (
                "last_updated",
                "next_update_due",
                "record_count",
                "quality_score",
                "last_run_status",
                "last_run_id",
                "updated_at",
            ):
                row[runtime_field] = existing.get(runtime_field, row.get(runtime_field, ""))
        else:
            targets = parse_output_targets(row["output_targets"])
            freshest = _freshest_output_date(targets)
            row["last_updated"] = freshest.isoformat() if freshest else ""
            row["next_update_due"] = _compute_next_due(
                freshest,
                str(row.get("update_frequency", "")),
                int(row["freshness_sla_days"]) if pd.notna(row["freshness_sla_days"]) else None,
            )
            row["record_count"] = _estimate_output_records(targets)
            row["quality_score"] = 1.0 if freshest else None
            row["last_run_status"] = "seeded_from_outputs" if freshest else "not_run"
            row["last_run_id"] = ""
            row["updated_at"] = now_iso

        rows.append(row)

    return _normalize_registry_frame(pd.DataFrame(rows))


def load_registry_snapshot(path: Path | None = None) -> pd.DataFrame:
    snapshot_path = path or registry_snapshot_path()
    if snapshot_path.exists():
        try:
            existing = pd.read_csv(snapshot_path, encoding="utf-8-sig").fillna("")
            return build_registry_frame(existing)
        except Exception:
            return build_registry_frame()
    return build_registry_frame()


def save_registry_snapshot(df: pd.DataFrame, path: Path | None = None) -> Path:
    snapshot_path = path or registry_snapshot_path()
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    _normalize_registry_frame(df).to_csv(snapshot_path, index=False, encoding="utf-8-sig")
    return snapshot_path


def empty_runs_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=RUN_COLUMNS)


def load_runs_snapshot(path: Path | None = None) -> pd.DataFrame:
    snapshot_path = path or runs_snapshot_path()
    if not snapshot_path.exists():
        return empty_runs_frame()
    try:
        df = pd.read_csv(snapshot_path, encoding="utf-8-sig").fillna("")
    except Exception:
        return empty_runs_frame()
    for column in RUN_COLUMNS:
        if column not in df.columns:
            df[column] = pd.Series(dtype="object")
    return df[RUN_COLUMNS]


def save_runs_snapshot(df: pd.DataFrame, path: Path | None = None) -> Path:
    snapshot_path = path or runs_snapshot_path()
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    out = df.copy()
    for column in RUN_COLUMNS:
        if column not in out.columns:
            out[column] = pd.Series(dtype="object")
    out[RUN_COLUMNS].to_csv(snapshot_path, index=False, encoding="utf-8-sig")
    return snapshot_path


def source_definitions_frame() -> pd.DataFrame:
    return build_registry_frame()


if __name__ == "__main__":
    registry = save_registry_snapshot(build_registry_frame())
    save_runs_snapshot(load_runs_snapshot())
    print(f"[source-registry] snapshot listo en {registry}")
