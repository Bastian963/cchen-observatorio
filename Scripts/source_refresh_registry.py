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
        "notes": "Fuente registrada; refresh aún manual vía notebook.",
        "enabled": False,
        "runner_command": "",
        "output_targets": ["Data/Publications/cchen_openalex_works.csv"],
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
        "notes": "Fuente registrada; refresh aún manual vía notebook.",
        "enabled": False,
        "runner_command": "",
        "output_targets": ["Data/Publications/cchen_crossref_enriched.csv"],
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
        "notes": "Fuente registrada; refresh aún manual vía notebook.",
        "enabled": False,
        "runner_command": "",
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
        "notes": "Formalmente trazada; automatización pendiente.",
        "enabled": False,
        "runner_command": "",
        "output_targets": ["Data/Researchers/cchen_researchers_orcid.csv"],
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
        "notes": "Registrada pero no habilitada por dependencia de token.",
        "enabled": False,
        "runner_command": "",
        "output_targets": ["Data/Patents/cchen_patents_uspto.csv"],
        "owner": DEFAULT_OWNER,
        "visibility": "publico",
        "blocking": False,
        "job_key": "manual_patentsview",
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
        "notes": "Registrada; refresh aún manual vía notebook.",
        "enabled": False,
        "runner_command": "",
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
        "notes": "Registrada; carga sigue manual en esta fase.",
        "enabled": False,
        "runner_command": "",
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
        "notes": "Registrada; carga sigue manual en esta fase.",
        "enabled": False,
        "runner_command": "",
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
        "runner_command": "python Scripts/fetch_openaire_outputs.py",
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
        "description": "Outputs institucionales CCHEN publicados en Zenodo.",
        "url": "https://zenodo.org/api",
        "table_name": "",
        "notebook_path": "Scripts/download_zenodo_cchen_combined.py",
        "update_frequency": "semestral",
        "freshness_sla_days": 180,
        "requires_token": False,
        "token_source": "ZENODO_TOKEN",
        "notes": "Queda formalmente en catálogo operativo; automatización diferida por tamaño de descarga.",
        "enabled": False,
        "runner_command": "",
        "output_targets": ["zenodo_cchen_combined_downloads"],
        "owner": DEFAULT_OWNER,
        "visibility": "publico",
        "blocking": False,
        "job_key": "manual_zenodo_outputs",
    },
    {
        "source_key": "sjr_scimago",
        "source_name": "SJR Scimago",
        "description": "Rankings y cuartiles de revistas científicas.",
        "url": "https://www.scimagojr.com",
        "table_name": "publications_enriched",
        "notebook_path": "",
        "update_frequency": "anual",
        "freshness_sla_days": 365,
        "requires_token": False,
        "token_source": "",
        "notes": "Derivado externo aún manual.",
        "enabled": False,
        "runner_command": "",
        "output_targets": ["Data/Publications/cchen_publications_with_quartile_sjr.csv"],
        "owner": DEFAULT_OWNER,
        "visibility": "publico",
        "blocking": False,
        "job_key": "manual_sjr",
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
        "output_targets": ["Data/Vigilancia/iaea_inis_monitor.csv"],
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
        "notebook_path": "Data/Capital humano CCHEN/salida_dataset_maestro/dataset_maestro_limpio.csv",
        "update_frequency": "semestral",
        "freshness_sla_days": 180,
        "requires_token": False,
        "token_source": "",
        "notes": "Dato interno y sensible; sigue manual en esta fase.",
        "enabled": False,
        "runner_command": "",
        "output_targets": ["Data/Capital humano CCHEN/salida_dataset_maestro/dataset_maestro_limpio.csv"],
        "owner": DEFAULT_OWNER,
        "visibility": "interno",
        "blocking": False,
        "job_key": "manual_capital_humano",
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
