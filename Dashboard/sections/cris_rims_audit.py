"""Deterministic CRIS/RIMS maturity audit for the CCHEN observatory.

The functions in this module are intentionally Streamlit-free so they can be
tested without starting the app. The benchmark content is derived from the
CRIS/RIMS research brief accepted for this implementation.
"""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
SOURCE_REGISTRY_PATH = ROOT / "Data" / "Gobernanza" / "data_sources_runtime.csv"


BENCHMARK_PLATFORMS: tuple[dict[str, str], ...] = (
    {
        "platform": "DSpace-CRIS",
        "value": "CRIS open source con investigadores, unidades, proyectos, publicaciones, patentes y laboratorios.",
        "signal": "Import automatico, ORCID, OpenAIRE, OpenAlex, portal publico, mapas y analytics.",
        "gap_if_missing": "Claims, OpenAlex import, analytics privacy-friendly o entidades como labs/equipamiento.",
    },
    {
        "platform": "VIVO",
        "value": "Referencia para grafo semantico, perfiles de expertos y discovery por relaciones.",
        "signal": "Ontologias, RDF, SPARQL, Solr, inferencia y paginas de scholar.",
        "gap_if_missing": "Relaciones semanticas explicitas, ontologias o discovery por expertise.",
    },
    {
        "platform": "Pure",
        "value": "Single source of truth institucional, reporting ejecutivo y showcase publico.",
        "signal": "Perfiles, proyectos, outputs, datasets, actividades, analytics y fingerprint de temas.",
        "gap_if_missing": "Separacion debil entre registro canonico, portal y vistas de expertise.",
    },
    {
        "platform": "Converis",
        "value": "Benchmark para workflows administrativos, pre-award/post-award y aprobaciones.",
        "signal": "Budgeting, approvals, forecasting, ethics, matcher WoS y dashboards embebidos.",
        "gap_if_missing": "Gestion de outputs sin circuito de aprobacion, presupuesto o cuellos de botella.",
    },
    {
        "platform": "Symplectic Elements",
        "value": "Captura continua, claiming, compliance OA y reporting reutilizable.",
        "signal": "Multiples fuentes, API REST, reporting DB, ORCID, ROR/GRID, Crossref, Scopus y WoS.",
        "gap_if_missing": "Claiming automatico, OA workflows, reporting DB separado o integracion BI.",
    },
    {
        "platform": "InvenioRDM",
        "value": "Repositorio moderno con records, communities, APIs y seguridad configurable.",
        "signal": "DataCite JSON, ORCID/OAuth/Keycloak, REST APIs, typos y autocomplete.",
        "gap_if_missing": "APIs limpias, DOI self-service, vocabularios sincronizados o acceso restringido.",
    },
    {
        "platform": "Dataverse",
        "value": "Benchmark para datasets como entidades completas, no adjuntos secundarios.",
        "signal": "Metadata blocks, DOI/Handle, OAI-PMH, Search API y metricas Make Data Count.",
        "gap_if_missing": "Datasets tratados como adjuntos de publicaciones.",
    },
    {
        "platform": "CKAN",
        "value": "Patron API-first para catalogos de datos y open data.",
        "signal": "Dataset + resources + organizations, Action API, DCAT/RDF y busqueda facetada.",
        "gap_if_missing": "Catalogo de datos sin APIs, facetas o distribuciones reutilizables.",
    },
    {
        "platform": "OpenAlex",
        "value": "Grafo abierto de works, authors, institutions, funders, sources y topics.",
        "signal": "Enriquecimiento, gap detection, author disambiguation y topics.",
        "gap_if_missing": "Conector abierto para cobertura bibliografica y deteccion de faltantes.",
    },
    {
        "platform": "Research.fi",
        "value": "Hub nacional federado con perfiles, funding, datasets, infraestructuras y estadisticas.",
        "signal": "Responsabilidad por fuente, visibilidad configurable y API JSON.",
        "gap_if_missing": "Fuente de verdad poco clara o federacion debil entre actores.",
    },
    {
        "platform": "OpenAIRE Monitor",
        "value": "Monitoreo sobre grafo enriquecido, deduplicado y desambiguado.",
        "signal": "Dashboards con indicadores, Open Science, funding, colaboracion e impacto.",
        "gap_if_missing": "Analitica pegada al OLTP o indicadores no comparables.",
    },
    {
        "platform": "ORCID institutional integrations",
        "value": "Identidad persistente y trusted data para personas.",
        "signal": "Read/write de works, affiliations, funding, peer review y research resources.",
        "gap_if_missing": "ORCID como campo de texto sin autenticacion ni sincronizacion.",
    },
)


MATURITY_DIMENSIONS: tuple[dict[str, Any], ...] = (
    {"key": "coverage", "dimension": "Cobertura funcional", "weight": 20},
    {"key": "identity", "dimension": "Calidad de identidad", "weight": 15},
    {"key": "ingestion", "dimension": "Ingestion y normalizacion", "weight": 20},
    {"key": "interoperability", "dimension": "Interoperabilidad", "weight": 10},
    {"key": "discovery", "dimension": "Discovery", "weight": 10},
    {"key": "analytics", "dimension": "Analytics", "weight": 10},
    {"key": "architecture", "dimension": "Arquitectura", "weight": 10},
    {"key": "governance", "dimension": "Seguridad y gobierno", "weight": 5},
)


CRITICAL_BACKLOG: tuple[dict[str, str], ...] = (
    {
        "priority": "Critica",
        "initiative": "Authority control + external_ids",
        "expected_result": "Una identidad por persona, organizacion, output, proyecto y funder.",
        "next_step": "Completar identificadores externos y aliases en registros canonicos.",
    },
    {
        "priority": "Critica",
        "initiative": "Dedupe pipeline + curacion",
        "expected_result": "Importaciones repetibles, merge controlado y calidad auditable.",
        "next_step": "Persistir decisiones curatoriales y confidence score por candidato.",
    },
    {
        "priority": "Critica",
        "initiative": "Projects/awards como entidad de primera clase",
        "expected_result": "Financiamiento unido a outputs, personas y metricas.",
        "next_step": "Vincular proyectos con publicaciones, datasets, estudiantes y activos.",
    },
    {
        "priority": "Critica",
        "initiative": "Datasets/software como entidad propia",
        "expected_result": "Soporte real a open science y trazabilidad de resultados no bibliograficos.",
        "next_step": "Separar datasets/software de publicaciones y agregar licencias/responsables.",
    },
    {
        "priority": "Critica",
        "initiative": "ORCID read/write + ROR",
        "expected_result": "Claiming confiable, afiliacion limpia y perfiles reutilizables.",
        "next_step": "Distinguir lectura publica actual de sincronizacion institucional trusted.",
    },
    {
        "priority": "Alta",
        "initiative": "OpenAlex + Crossref enrichment",
        "expected_result": "Cobertura bibliografica, deteccion de faltantes y updates incrementales.",
        "next_step": "Mantener refresh idempotente y alertas de calidad por DOI.",
    },
    {
        "priority": "Alta",
        "initiative": "OLTP + indice + analytics mart",
        "expected_result": "Escalabilidad, BI confiable y dashboards sin sobrecargar el modelo operativo.",
        "next_step": "Definir vistas/materializaciones analiticas separadas del registro canonico.",
    },
    {
        "priority": "Alta",
        "initiative": "Search & discovery hibrido",
        "expected_result": "Facetas, autocomplete, entity pages y claiming desde resultados.",
        "next_step": "Convertir evidencia semantica en discovery por entidad y relacion tipada.",
    },
    {
        "priority": "Alta",
        "initiative": "Compliance dashboards",
        "expected_result": "Seguimiento OA, politicas, excepciones y metadata quality.",
        "next_step": "Cruzar Unpaywall, DOI, depositos y reglas institucionales.",
    },
    {
        "priority": "Deseable",
        "initiative": "Facility/equipment/infrastructure module",
        "expected_result": "Capacidades experimentales y servicios institucionales visibles.",
        "next_step": "Levantar inventario operacional con owners, disponibilidad y reglas de acceso.",
    },
    {
        "priority": "Deseable",
        "initiative": "Impact evidence narratives",
        "expected_result": "Evidencia cualitativa y cuantitativa ligada a grants y outputs.",
        "next_step": "Normalizar casos de impacto y fuentes verificables por activo.",
    },
    {
        "priority": "Futura",
        "initiative": "Semantic discovery sobre grafo limpio",
        "expected_result": "Recomendaciones por expertise y relaciones, no solo keywords.",
        "next_step": "Agregar embeddings despues de consolidar metadatos y relaciones.",
    },
)


INTEROPERABILITY_STANDARDS: tuple[dict[str, str], ...] = (
    {"standard": "CERIF", "recommended_use": "Marco conceptual para entidades y relaciones de investigacion."},
    {"standard": "OpenAIRE Guidelines", "recommended_use": "Interoperabilidad de CRIS, repositorios y data archives."},
    {"standard": "ORCID", "recommended_use": "Identidad persistente de personas y trusted data institucional."},
    {"standard": "DOI/DataCite", "recommended_use": "PID y metadata para datasets, software, awards y outputs."},
    {"standard": "Crossref", "recommended_use": "Enriquecimiento bibliografico por DOI, funding, licencias y abstracts."},
    {"standard": "ROR", "recommended_use": "Authority control para organizaciones, afiliaciones y funders."},
    {"standard": "OpenAlex", "recommended_use": "Grafo abierto para works, authors, institutions, funders y topics."},
    {"standard": "OAI-PMH", "recommended_use": "Harvesting minimo para repositorios y agregadores."},
    {"standard": "schema.org", "recommended_use": "Metadatos embebidos en landing pages publicas."},
    {"standard": "REST/JSON versionado", "recommended_use": "Contratos de integracion con BI, ETL y sistemas institucionales."},
    {"standard": "RDF/SPARQL", "recommended_use": "Opcional para expert finding y grafo semantico avanzado."},
)


def safe_len(value: Any) -> int:
    """Return len(value), treating missing or invalid values as zero."""
    try:
        return int(len(value))
    except Exception:
        return 0


def nonempty_frame(value: Any) -> bool:
    return isinstance(value, pd.DataFrame) and not value.empty


def load_optional_source_registry(path: Path = SOURCE_REGISTRY_PATH) -> pd.DataFrame:
    """Load the optional source registry without making the dashboard depend on it."""
    if not path.exists():
        return _load_source_registry_seed()
    try:
        return pd.read_csv(path, low_memory=False, encoding="utf-8-sig").fillna("")
    except Exception:
        try:
            return pd.read_csv(path, low_memory=False).fillna("")
        except Exception:
            return _load_source_registry_seed()


def _load_source_registry_seed() -> pd.DataFrame:
    """Use the committed source registry definitions when runtime CSVs are absent."""
    scripts_dir = ROOT / "Scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    try:
        from source_refresh_registry import load_registry_snapshot

        return load_registry_snapshot().fillna("")
    except Exception:
        return pd.DataFrame()


def source_keys(source_registry: pd.DataFrame | None) -> set[str]:
    if source_registry is None or source_registry.empty or "source_key" not in source_registry.columns:
        return set()
    return {str(value).strip() for value in source_registry["source_key"].dropna() if str(value).strip()}


def source_enabled(source_registry: pd.DataFrame | None, key: str) -> bool:
    if source_registry is None or source_registry.empty or "source_key" not in source_registry.columns:
        return False
    rows = source_registry[source_registry["source_key"].astype(str).eq(key)]
    if rows.empty:
        return False
    if "enabled" not in rows.columns:
        return True
    raw = str(rows.iloc[0].get("enabled", "")).strip().lower()
    return raw in {"true", "1", "yes", "si", "sí"} or raw == ""


def evidence_profile(ctx: dict[str, Any], source_registry: pd.DataFrame | None = None) -> dict[str, Any]:
    keys = source_keys(source_registry)

    pub = ctx.get("pub", pd.DataFrame())
    auth = ctx.get("auth", pd.DataFrame())
    orcid = ctx.get("orcid", pd.DataFrame())
    patents = ctx.get("patents", pd.DataFrame())
    convenios = ctx.get("convenios", pd.DataFrame())
    acuerdos = ctx.get("acuerdos", pd.DataFrame())
    matching_inst = ctx.get("matching_inst", pd.DataFrame())
    entity_personas = ctx.get("entity_personas", pd.DataFrame())
    entity_projects = ctx.get("entity_projects", pd.DataFrame())
    entity_convocatorias = ctx.get("entity_convocatorias", pd.DataFrame())
    entity_links = ctx.get("entity_links", pd.DataFrame())

    doi_in_publications = (
        nonempty_frame(pub)
        and "doi" in pub.columns
        and pub["doi"].dropna().astype(str).str.strip().ne("").any()
    )
    has_successful_sources = (
        source_registry is not None
        and not source_registry.empty
        and "last_run_status" in source_registry.columns
        and source_registry["last_run_status"].astype(str).str.lower().isin({"success", "seeded_from_outputs"}).any()
    )
    has_visibility_policy = (
        source_registry is not None
        and not source_registry.empty
        and "visibility" in source_registry.columns
        and source_registry["visibility"].astype(str).str.strip().ne("").any()
    )

    return {
        "publications": nonempty_frame(pub) or "openalex_publicaciones" in keys,
        "authorships": nonempty_frame(auth),
        "orcid": nonempty_frame(orcid) or "orcid" in keys,
        "ror": "ror_registry" in keys or "ror_pending_review" in keys,
        "doi": bool(doi_in_publications or {"crossref", "datacite_outputs"} & keys),
        "openalex": bool({"openalex_publicaciones", "openalex_conceptos", "openalex_citations"} & keys),
        "crossref": "crossref" in keys,
        "datacite": "datacite_outputs" in keys,
        "openaire": "openaire_outputs" in keys,
        "zenodo": "zenodo_outputs" in keys,
        "unpaywall": "unpaywall_oa" in keys,
        "altmetric": "altmetric" in keys,
        "citation_graph": bool({"citation_graph", "openalex_citations"} & keys),
        "semantic_evidence_index": "semantic_evidence_index" in keys,
        "source_registry": source_registry is not None and not source_registry.empty,
        "successful_sources": has_successful_sources,
        "visibility_policy": has_visibility_policy,
        "persons_canonical": nonempty_frame(entity_personas),
        "projects_canonical": nonempty_frame(entity_projects),
        "calls_canonical": nonempty_frame(entity_convocatorias),
        "typed_relations": nonempty_frame(entity_links),
        "matching": nonempty_frame(matching_inst) or "matching_institucional" in keys,
        "patents": nonempty_frame(patents) or "patentsview_uspto" in keys,
        "agreements": nonempty_frame(convenios) or nonempty_frame(acuerdos),
        "funding": "anid_repositorio" in keys or "funding_complementario" in keys,
        "ror_review_queue": "ror_pending_review" in keys,
        "enabled_source_count": sum(1 for key in keys if source_enabled(source_registry, key)),
        "source_count": len(keys),
        "entity_link_count": safe_len(entity_links),
        "person_count": safe_len(entity_personas),
        "project_count": safe_len(entity_projects),
        "publication_count": safe_len(pub),
        "orcid_count": safe_len(orcid),
        "patent_count": safe_len(patents),
    }


def _score_by_count(count: int, thresholds: tuple[int, int, int]) -> int:
    if count >= thresholds[2]:
        return 3
    if count >= thresholds[1]:
        return 2
    if count >= thresholds[0]:
        return 1
    return 0


def _status_from_score(score: int) -> str:
    return {0: "Faltante", 1: "Inicial", 2: "Funcional", 3: "Robusto"}.get(int(score), "Faltante")


def _feature_state(full: bool, partial: bool = False) -> str:
    if full:
        return "Implementado"
    if partial:
        return "Parcial"
    return "Faltante"


def build_maturity_assessment(profile: dict[str, Any]) -> pd.DataFrame:
    coverage_count = sum(
        bool(profile.get(key))
        for key in [
            "publications",
            "persons_canonical",
            "projects_canonical",
            "calls_canonical",
            "datacite",
            "openaire",
            "patents",
            "agreements",
        ]
    )
    identity_count = sum(
        bool(profile.get(key))
        for key in ["orcid", "ror", "doi", "openalex", "crossref", "persons_canonical"]
    )
    ingestion_count = sum(
        bool(profile.get(key))
        for key in [
            "source_registry",
            "successful_sources",
            "semantic_evidence_index",
            "ror_review_queue",
            "typed_relations",
        ]
    )
    interoperability_count = sum(
        bool(profile.get(key))
        for key in ["orcid", "ror", "doi", "datacite", "crossref", "openalex", "openaire", "unpaywall"]
    )
    discovery_count = sum(
        bool(profile.get(key))
        for key in ["semantic_evidence_index", "typed_relations", "publications", "openalex", "matching"]
    )
    analytics_count = sum(
        bool(profile.get(key))
        for key in ["source_registry", "semantic_evidence_index", "citation_graph", "altmetric", "unpaywall"]
    )
    architecture_count = sum(
        bool(profile.get(key))
        for key in ["source_registry", "persons_canonical", "projects_canonical", "typed_relations", "semantic_evidence_index"]
    )
    governance_count = sum(
        bool(profile.get(key))
        for key in ["visibility_policy", "ror_review_queue", "matching", "typed_relations"]
    )

    raw_scores = {
        "coverage": _score_by_count(coverage_count, (2, 4, 6)),
        "identity": _score_by_count(identity_count, (1, 3, 5)),
        "ingestion": _score_by_count(ingestion_count, (1, 3, 5)),
        "interoperability": _score_by_count(interoperability_count, (2, 4, 6)),
        "discovery": _score_by_count(discovery_count, (1, 3, 5)),
        "analytics": _score_by_count(analytics_count, (1, 3, 5)),
        "architecture": _score_by_count(architecture_count, (1, 3, 5)),
        "governance": _score_by_count(governance_count, (1, 2, 4)),
    }
    evidence = {
        "coverage": f"{coverage_count}/8 capacidades observadas",
        "identity": f"{identity_count}/6 senales de PID/autoridad",
        "ingestion": f"{ingestion_count}/5 senales de ingestión y curación",
        "interoperability": f"{interoperability_count}/8 estándares/conectores detectados",
        "discovery": f"{discovery_count}/5 senales de discovery",
        "analytics": f"{analytics_count}/5 senales analíticas",
        "architecture": f"{architecture_count}/5 separaciones arquitectónicas",
        "governance": f"{governance_count}/4 controles de gobierno",
    }
    gaps = {
        "coverage": "Completar datasets/software, equipment/facilities y lifecycle de awards.",
        "identity": "Distinguir IDs internos de external IDs y cerrar read/write ORCID.",
        "ingestion": "Persistir source records, hashes, confidence y decisiones curatoriales.",
        "interoperability": "Exponer contratos versionados, OAI-PMH/schema.org y DataCite mas completo.",
        "discovery": "Pasar de búsqueda de evidencia a discovery por entidad, facetas y claiming.",
        "analytics": "Separar un mart analítico/reporting DB de las tablas operativas.",
        "architecture": "Formalizar boundaries entre conectores, dominio, índice y dashboards.",
        "governance": "Completar RBAC, auditoría de cambios y políticas de visibilidad por atributo.",
    }

    rows: list[dict[str, Any]] = []
    for dimension in MATURITY_DIMENSIONS:
        key = str(dimension["key"])
        score = int(raw_scores[key])
        weight = int(dimension["weight"])
        rows.append(
            {
                "dimension_key": key,
                "Dimensión": dimension["dimension"],
                "Peso": weight,
                "Madurez 0-3": score,
                "Estado": _status_from_score(score),
                "Puntaje ponderado": round(score / 3 * weight, 2),
                "Evidencia CCHEN": evidence[key],
                "Brecha principal": gaps[key],
            }
        )
    return pd.DataFrame(rows)


def build_gap_matrix(profile: dict[str, Any]) -> pd.DataFrame:
    rows = [
        {
            "Feature": "Authority layer de personas y organizaciones",
            "Prioridad": "Critica",
            "Estado CCHEN": _feature_state(
                bool(profile.get("persons_canonical") and profile.get("ror") and profile.get("orcid")),
                bool(profile.get("persons_canonical") or profile.get("ror") or profile.get("orcid")),
            ),
            "Evidencia": f"{profile.get('person_count', 0):,} personas canonicas; ORCID={profile.get('orcid')}; ROR={profile.get('ror')}",
            "Siguiente paso": "Separar external_ids, aliases y afiliaciones históricas por entidad.",
        },
        {
            "Feature": "Source records + provenance",
            "Prioridad": "Critica",
            "Estado CCHEN": _feature_state(bool(profile.get("source_registry") and profile.get("successful_sources"))),
            "Evidencia": f"{profile.get('source_count', 0):,} fuentes registradas; {profile.get('enabled_source_count', 0):,} habilitadas",
            "Siguiente paso": "Guardar payload/hash/source_record_id por registro importado.",
        },
        {
            "Feature": "Motor de dedupe/merge con cola de curacion",
            "Prioridad": "Critica",
            "Estado CCHEN": _feature_state(False, bool(profile.get("ror_review_queue") or profile.get("typed_relations"))),
            "Evidencia": "Cola ROR y relaciones operativas detectadas" if profile.get("ror_review_queue") or profile.get("typed_relations") else "Sin cola detectada",
            "Siguiente paso": "Persistir merges, rechazos, confidence score y responsable curatorial.",
        },
        {
            "Feature": "Graph de relaciones tipadas",
            "Prioridad": "Critica",
            "Estado CCHEN": _feature_state(bool(profile.get("typed_relations"))),
            "Evidencia": f"{profile.get('entity_link_count', 0):,} enlaces operativos",
            "Siguiente paso": "Agregar temporalidad, rol, fuente y confianza por edge.",
        },
        {
            "Feature": "Integracion ORCID read/write",
            "Prioridad": "Critica",
            "Estado CCHEN": _feature_state(False, bool(profile.get("orcid"))),
            "Evidencia": f"{profile.get('orcid_count', 0):,} perfiles ORCID o fuente ORCID detectada",
            "Siguiente paso": "Separar lectura Public API de flujo trusted read/write institucional.",
        },
        {
            "Feature": "Integracion ROR",
            "Prioridad": "Critica",
            "Estado CCHEN": _feature_state(bool(profile.get("ror"))),
            "Evidencia": "Registro ROR o cola ROR detectada" if profile.get("ror") else "Sin ROR detectado",
            "Siguiente paso": "Conectar afiliaciones, funders y org units a ROR normalizado.",
        },
        {
            "Feature": "Crossref + OpenAlex enrichment",
            "Prioridad": "Alta",
            "Estado CCHEN": _feature_state(
                bool(profile.get("crossref") and profile.get("openalex")),
                bool(profile.get("crossref") or profile.get("openalex")),
            ),
            "Evidencia": f"Crossref={profile.get('crossref')}; OpenAlex={profile.get('openalex')}",
            "Siguiente paso": "Asegurar refresh incremental y alertas por DOI sin match.",
        },
        {
            "Feature": "Modulo project/award de primera clase",
            "Prioridad": "Critica",
            "Estado CCHEN": _feature_state(bool(profile.get("projects_canonical")), bool(profile.get("funding"))),
            "Evidencia": f"{profile.get('project_count', 0):,} proyectos canonicos",
            "Siguiente paso": "Vincular award lifecycle, funder, monto, fechas y outputs.",
        },
        {
            "Feature": "Modulo dataset/software",
            "Prioridad": "Critica",
            "Estado CCHEN": _feature_state(False, bool(profile.get("datacite") or profile.get("openaire") or profile.get("zenodo"))),
            "Evidencia": f"DataCite={profile.get('datacite')}; OpenAIRE={profile.get('openaire')}; Zenodo={profile.get('zenodo')}",
            "Siguiente paso": "Crear entidad dataset/software con licencia, responsables y relaciones.",
        },
        {
            "Feature": "Search stack hibrido",
            "Prioridad": "Alta",
            "Estado CCHEN": _feature_state(False, bool(profile.get("semantic_evidence_index"))),
            "Evidencia": "Indice semantico de evidencia detectado" if profile.get("semantic_evidence_index") else "Sin indice detectado",
            "Siguiente paso": "Agregar facetas, autocomplete por entidad y páginas navegables.",
        },
        {
            "Feature": "Analytics mart / reporting DB",
            "Prioridad": "Alta",
            "Estado CCHEN": _feature_state(False, bool(profile.get("source_registry") or profile.get("semantic_evidence_index"))),
            "Evidencia": "Hay snapshots y derivados analiticos, no mart formal" if profile.get("source_registry") else "Sin evidencia",
            "Siguiente paso": "Crear capa analitica desacoplada del modelo transaccional.",
        },
        {
            "Feature": "Open access/compliance monitor",
            "Prioridad": "Alta",
            "Estado CCHEN": _feature_state(False, bool(profile.get("unpaywall"))),
            "Evidencia": "Unpaywall OA detectado" if profile.get("unpaywall") else "Sin monitor OA detectado",
            "Siguiente paso": "Cruzar politicas, versiones depositadas, excepciones y evidencia.",
        },
        {
            "Feature": "Impact/evidence module",
            "Prioridad": "Media",
            "Estado CCHEN": _feature_state(False, bool(profile.get("altmetric") or profile.get("citation_graph"))),
            "Evidencia": f"Altmetric={profile.get('altmetric')}; citas={profile.get('citation_graph')}",
            "Siguiente paso": "Unir metricas con narrativas de impacto y grants.",
        },
        {
            "Feature": "Equipment/facilities/infrastructures",
            "Prioridad": "Media",
            "Estado CCHEN": "Faltante",
            "Evidencia": "No hay entidad operacional detectada para equipamiento/facilities",
            "Siguiente paso": "Levantar inventario con owner, servicio, acceso y disponibilidad.",
        },
        {
            "Feature": "Funding opportunities / calls",
            "Prioridad": "Media",
            "Estado CCHEN": _feature_state(bool(profile.get("matching") or profile.get("calls_canonical"))),
            "Evidencia": f"Matching={profile.get('matching')}; convocatorias canonicas={profile.get('calls_canonical')}",
            "Siguiente paso": "Conectar oportunidades a perfiles, capacidades y proyectos postulables.",
        },
    ]
    return pd.DataFrame(rows)


def build_interoperability_matrix(profile: dict[str, Any]) -> pd.DataFrame:
    detected = {
        "CERIF": bool(profile.get("typed_relations") and profile.get("persons_canonical") and profile.get("projects_canonical")),
        "OpenAIRE Guidelines": bool(profile.get("openaire")),
        "ORCID": bool(profile.get("orcid")),
        "DOI/DataCite": bool(profile.get("doi") or profile.get("datacite")),
        "Crossref": bool(profile.get("crossref")),
        "ROR": bool(profile.get("ror")),
        "OpenAlex": bool(profile.get("openalex")),
        "OAI-PMH": False,
        "schema.org": False,
        "REST/JSON versionado": bool(profile.get("source_registry")),
        "RDF/SPARQL": False,
    }
    rows = []
    for item in INTEROPERABILITY_STANDARDS:
        standard = item["standard"]
        is_detected = detected.get(standard, False)
        rows.append(
            {
                "Estándar": standard,
                "Uso recomendado": item["recommended_use"],
                "Estado CCHEN": "Detectado" if is_detected else "No detectado",
                "Acción": "Mantener y documentar contrato operativo" if is_detected else "Evaluar implementación o evidencia técnica",
            }
        )
    return pd.DataFrame(rows)


def build_backlog(profile: dict[str, Any], gap_matrix: pd.DataFrame | None = None) -> pd.DataFrame:
    gap_status = {}
    if gap_matrix is not None and not gap_matrix.empty:
        for _, row in gap_matrix.iterrows():
            gap_status[str(row.get("Feature", ""))] = str(row.get("Estado CCHEN", ""))

    def status_for(initiative: str) -> str:
        initiative_l = initiative.lower()
        if "authority" in initiative_l:
            return gap_status.get("Authority layer de personas y organizaciones", "Faltante")
        if "dedupe" in initiative_l:
            return gap_status.get("Motor de dedupe/merge con cola de curacion", "Faltante")
        if "projects" in initiative_l:
            return gap_status.get("Modulo project/award de primera clase", "Faltante")
        if "datasets" in initiative_l:
            return gap_status.get("Modulo dataset/software", "Faltante")
        if "orcid" in initiative_l:
            return gap_status.get("Integracion ORCID read/write", "Faltante")
        if "openalex" in initiative_l:
            return gap_status.get("Crossref + OpenAlex enrichment", "Faltante")
        if "analytics" in initiative_l:
            return gap_status.get("Analytics mart / reporting DB", "Faltante")
        if "search" in initiative_l:
            return gap_status.get("Search stack hibrido", "Faltante")
        if "compliance" in initiative_l:
            return gap_status.get("Open access/compliance monitor", "Faltante")
        if "facility" in initiative_l:
            return gap_status.get("Equipment/facilities/infrastructures", "Faltante")
        if "impact" in initiative_l:
            return gap_status.get("Impact/evidence module", "Faltante")
        if "semantic" in initiative_l:
            return "Futura"
        return "Pendiente"

    rows = []
    for item in CRITICAL_BACKLOG:
        rows.append(
            {
                "Prioridad": item["priority"],
                "Iniciativa": item["initiative"],
                "Estado CCHEN": status_for(item["initiative"]),
                "Resultado esperado": item["expected_result"],
                "Próximo paso": item["next_step"],
            }
        )
    return pd.DataFrame(rows)


def build_agent_findings(profile: dict[str, Any], maturity: pd.DataFrame, gap_matrix: pd.DataFrame) -> pd.DataFrame:
    maturity_by_key = {
        str(row.get("dimension_key")): int(row.get("Madurez 0-3", 0))
        for _, row in maturity.iterrows()
    }

    rows = [
        {
            "Agente": "Auditor de Identidad",
            "Área": "ORCID/ROR/DOI/external IDs",
            "Estado": _status_from_score(maturity_by_key.get("identity", 0)),
            "Evidencia": f"ORCID={profile.get('orcid')}; ROR={profile.get('ror')}; DOI={profile.get('doi')}",
            "Brecha": "ORCID read/write y external_ids canonicos aun deben explicitarse.",
            "Acción": "Crear submodelo ExternalIdentifier por entidad y registrar validacion por fuente.",
            "Confianza": "alta" if profile.get("orcid") or profile.get("ror") else "media",
        },
        {
            "Agente": "Auditor de Ingesta",
            "Área": "Fuentes, refresh, provenance y curacion",
            "Estado": _status_from_score(maturity_by_key.get("ingestion", 0)),
            "Evidencia": f"{profile.get('source_count', 0):,} fuentes; semantic index={profile.get('semantic_evidence_index')}",
            "Brecha": "Faltan source records con payload/hash/confidence por registro.",
            "Acción": "Persistir raw payload normalizado y bitacora por job antes del merge canonico.",
            "Confianza": "alta" if profile.get("source_registry") else "media",
        },
        {
            "Agente": "Auditor de Modelo",
            "Área": "Entidades canonicas y relaciones tipadas",
            "Estado": _status_from_score(maturity_by_key.get("architecture", 0)),
            "Evidencia": f"personas={profile.get('person_count', 0):,}; proyectos={profile.get('project_count', 0):,}; links={profile.get('entity_link_count', 0):,}",
            "Brecha": "Falta temporalidad, rol, fuente y confianza en relaciones de negocio.",
            "Acción": "Ampliar entity_links a TypedRelation con start/end date y confidence.",
            "Confianza": "alta" if profile.get("typed_relations") else "media",
        },
        {
            "Agente": "Auditor de Discovery/Analytics",
            "Área": "Busqueda, facetas, perfiles y mart analitico",
            "Estado": _status_from_score(min(maturity_by_key.get("discovery", 0), maturity_by_key.get("analytics", 0))),
            "Evidencia": f"indice evidencia={profile.get('semantic_evidence_index')}; citas={profile.get('citation_graph')}; OA={profile.get('unpaywall')}",
            "Brecha": "El indice semantico aun no reemplaza facetas, entity pages ni reporting DB separado.",
            "Acción": "Crear documentos de indice por entidad y una capa de mart para BI/reporting.",
            "Confianza": "alta" if profile.get("semantic_evidence_index") else "media",
        },
    ]
    return pd.DataFrame(rows)


def build_cris_rims_audit(
    ctx: dict[str, Any],
    source_registry: pd.DataFrame | None = None,
) -> dict[str, Any]:
    """Build all audit tables from app context and optional source registry."""
    registry = source_registry if source_registry is not None else pd.DataFrame()
    profile = evidence_profile(ctx, registry)
    maturity = build_maturity_assessment(profile)
    gaps = build_gap_matrix(profile)
    interoperability = build_interoperability_matrix(profile)
    backlog = build_backlog(profile, gaps)
    agents = build_agent_findings(profile, maturity, gaps)
    benchmark = pd.DataFrame(BENCHMARK_PLATFORMS).rename(
        columns={
            "platform": "Benchmark",
            "value": "Valor comparativo",
            "signal": "Señal madura",
            "gap_if_missing": "Brecha si falta",
        }
    )
    return {
        "profile": profile,
        "maturity": maturity,
        "gaps": gaps,
        "interoperability": interoperability,
        "backlog": backlog,
        "agents": agents,
        "benchmark": benchmark,
    }


def audit_summary(maturity: pd.DataFrame) -> dict[str, Any]:
    if maturity.empty:
        return {
            "weighted_score": 0.0,
            "max_score": 100,
            "average_maturity": 0.0,
            "robust_dimensions": 0,
            "critical_dimensions": 0,
        }
    weighted_score = float(pd.to_numeric(maturity["Puntaje ponderado"], errors="coerce").fillna(0).sum())
    avg = float(pd.to_numeric(maturity["Madurez 0-3"], errors="coerce").fillna(0).mean())
    return {
        "weighted_score": round(weighted_score, 1),
        "max_score": 100,
        "average_maturity": round(avg, 2),
        "robust_dimensions": int((maturity["Madurez 0-3"] >= 3).sum()),
        "critical_dimensions": int((maturity["Madurez 0-3"] <= 1).sum()),
    }
