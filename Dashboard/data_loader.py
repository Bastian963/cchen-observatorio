"""
Carga y preprocesa los datos del Observatorio CCHEN.
Fuentes: CSVs de publicaciones, ANID, capital humano + JSONs precomputados.
"""
import json
import os
import datetime
import pandas as pd
from pathlib import Path
from functools import lru_cache

try:
    import duckdb
except ImportError:  # pragma: no cover - fallback esperado en entornos sin duckdb
    duckdb = None

try:
    from supabase import create_client
except ImportError:  # pragma: no cover - fallback esperado en entornos sin supabase-py
    create_client = None

_HERE     = Path(__file__).resolve().parent          # Dashboard/
_DEFAULT  = _HERE.parent / "Data"                    # CCHEN/Data
BASE      = Path(os.getenv("CCHEN_DATA_ROOT", str(_DEFAULT)))
BASE_CH   = BASE / "Capital humano CCHEN"
BASE_PUB  = BASE / "Publications"
BASE_ANID = BASE / "ANID"
BASE_PAT  = BASE / "Patents"
SALIDA    = BASE_CH / "salida_dataset_maestro"
AVANZADO  = SALIDA / "analisis_avanzado"
CAPITAL   = SALIDA / "analisis_capital_humano"

SUPABASE_PAGE_SIZE = 1000
TABLE_LOAD_STATUS: dict[str, dict] = {}
CAPITAL_HUMANO_COLUMNS = [
    "id",
    "anio_hoja",
    "nombre",
    "inicio",
    "termino",
    "duracion_dias",
    "tutor",
    "centro_norm",
    "tipo_norm",
    "universidad",
    "carrera",
    "monto_contrato_num",
    "ad_honorem",
    "objeto_contrato",
    "observaciones_texto",
    "informe_url_principal",
    "flag_fechas_inconsistentes",
    "flag_tipo_fuera_catalogo",
    "created_at",
]

PUBLIC_TABLE_CONFIG = {
    "publications": {"order_by": "openalex_id"},
    "publications_enriched": {"order_by": "work_id"},
    "authorships": {"order_by": "id"},
    "crossref_data": {"order_by": "doi"},
    "concepts": {"order_by": "id"},
    "patents": {"order_by": "patent_uid"},
    "datacite_outputs": {"order_by": "doi"},
    "openaire_outputs": {"order_by": "openaire_id"},
    "anid_projects": {"order_by": "proyecto"},
    "researchers_orcid": {"order_by": "orcid_id"},
    "institution_registry": {"order_by": "normalized_key"},
    "institution_registry_pending_review": {"order_by": "canonical_name"},
    "perfiles_institucionales": {"order_by": "perfil_id"},
    "convocatorias": {"order_by": "conv_id"},
    "convocatorias_matching_rules": {"order_by": "rule_id"},
    "convenios_nacionales": {"order_by": "id"},
    "acuerdos_internacionales": {"order_by": "id"},
    "entity_registry_proyectos": {"order_by": "project_id"},
    "entity_registry_convocatorias": {"order_by": "convocatoria_id"},
    "convocatorias_matching_institucional": {"order_by": "conv_id"},
    "iaea_inis_monitor": {"order_by": "inis_id"},
    "arxiv_monitor": {"order_by": "arxiv_id"},
    "news_monitor": {"order_by": "news_id"},
    "citation_graph": {"order_by": "openalex_id"},
    "europmc_works": {"order_by": "source_id"},
    "bertopic_topics": {"order_by": "openalex_id"},
    "bertopic_topic_info": {"order_by": "topic"},
    "citing_papers": {"order_by": "citing_id"},
    "data_sources": {"order_by": "source_name"},
}

SENSITIVE_TABLE_CONFIG = {
    "capital_humano": {"order_by": "id"},
    "funding_complementario": {"order_by": "funding_id"},
    "entity_registry_personas": {"order_by": "persona_id"},
    "entity_links": {"order_by": "origin_type"},
}


def get_data_backend_info() -> dict:
    """Retorna el motor de lectura disponible para el dashboard."""
    source_mode = _get_data_source_mode()
    source_detail = "solo archivos locales"
    if source_mode == "supabase_public":
        source_detail = "Supabase pública (sin fallback)"
    elif source_mode == "auto":
        source_detail = (
            "Supabase pública si está configurada; fallback local en caso contrario"
            if _supabase_client() is not None
            else "modo auto sin Supabase configurada; fallback local"
        )

    if duckdb is None:
        return {
            "engine": "pandas",
            "detail": f"duckdb no instalado; usando lectura CSV directa con pandas · fuente: {source_detail}",
            "source_mode": source_mode,
        }
    return {
        "engine": "duckdb",
        "detail": f"duckdb disponible para lectura local y consultas analíticas rápidas · fuente: {source_detail}",
        "source_mode": source_mode,
    }


def _record_table_load_status(table_name: str, source: str, detail: str = "") -> None:
    TABLE_LOAD_STATUS[table_name] = {
        "source": source,
        "detail": detail,
        "recorded_at": datetime.datetime.now().isoformat(timespec="seconds"),
    }


def get_table_load_status() -> dict[str, dict]:
    """Retorna un snapshot del origen de lectura por tabla en la sesión actual."""
    return {k: v.copy() for k, v in TABLE_LOAD_STATUS.items()}


def _read_csv_fast(path: Path) -> pd.DataFrame:
    """Lee CSVs con DuckDB si está disponible; si no, usa pandas."""
    if duckdb is None:
        return pd.read_csv(path)

    con = duckdb.connect(database=":memory:")
    try:
        quoted_path = str(path).replace("'", "''")
        return con.execute(
            f"SELECT * FROM read_csv_auto('{quoted_path}', HEADER=TRUE, SAMPLE_SIZE=-1)"
        ).fetchdf()
    except Exception:
        return pd.read_csv(path)
    finally:
        con.close()


def _get_data_source_mode() -> str:
    mode = str(os.getenv("OBSERVATORIO_DATA_SOURCE", "auto")).strip().lower()
    if mode not in {"auto", "local", "supabase_public"}:
        return "auto"
    return mode


def _get_supabase_credentials() -> tuple[str, str]:
    url = (
        os.getenv("SUPABASE_URL")
        or os.getenv("SUPABASE_PUBLIC_URL")
        or ""
    ).strip()
    key = (
        os.getenv("SUPABASE_ANON_KEY")
        or os.getenv("SUPABASE_PUBLIC_ANON_KEY")
        or os.getenv("SUPABASE_KEY")
        or ""
    ).strip()
    return url, key


def _get_supabase_service_role_credentials() -> tuple[str, str]:
    url = (
        os.getenv("SUPABASE_URL")
        or os.getenv("SUPABASE_PUBLIC_URL")
        or ""
    ).strip()
    key = (
        os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        or os.getenv("SUPABASE_SERVICE_ROLE")
        or ""
    ).strip()
    return url, key


@lru_cache(maxsize=1)
def _supabase_client():
    url, key = _get_supabase_credentials()
    if create_client is None or not url or not key:
        return None
    try:
        return create_client(url, key)
    except Exception:
        return None


@lru_cache(maxsize=1)
def _supabase_service_role_client():
    url, key = _get_supabase_service_role_credentials()
    if create_client is None or not url or not key:
        return None
    try:
        return create_client(url, key)
    except Exception:
        return None


def _fetch_supabase_table(table_name: str, use_service_role: bool = False) -> pd.DataFrame:
    client = _supabase_service_role_client() if use_service_role else _supabase_client()
    if client is None:
        raise RuntimeError("Supabase no configurado o cliente no disponible")

    table_config = SENSITIVE_TABLE_CONFIG if use_service_role else PUBLIC_TABLE_CONFIG
    order_by = table_config.get(table_name, {}).get("order_by")
    query = client.table(table_name).select("*", count="exact")
    if order_by:
        query = query.order(order_by)

    first = query.range(0, SUPABASE_PAGE_SIZE - 1).execute()
    rows = list(first.data or [])
    total = int(first.count or len(rows))

    start = SUPABASE_PAGE_SIZE
    while start < total:
        page = client.table(table_name).select("*")
        if order_by:
            page = page.order(order_by)
        resp = page.range(start, start + SUPABASE_PAGE_SIZE - 1).execute()
        batch = list(resp.data or [])
        if not batch:
            break
        rows.extend(batch)
        start += SUPABASE_PAGE_SIZE

    return pd.DataFrame(rows)


def _load_public_table(table_name: str, local_path: Path) -> pd.DataFrame:
    mode = _get_data_source_mode()

    if mode == "local":
        _record_table_load_status(table_name, "local_only", str(local_path))
        return _read_csv_fast(local_path)

    if table_name in PUBLIC_TABLE_CONFIG:
        try:
            df = _fetch_supabase_table(table_name)
            _record_table_load_status(table_name, "supabase_public", table_name)
            return df
        except Exception:
            if mode == "supabase_public":
                raise
            _record_table_load_status(table_name, "local_fallback", str(local_path))
            return _read_csv_fast(local_path)

    _record_table_load_status(table_name, "local_only", str(local_path))
    return _read_csv_fast(local_path)


def _load_sensitive_table(table_name: str, local_path: Path) -> pd.DataFrame:
    mode = _get_data_source_mode()

    if mode == "local":
        _record_table_load_status(table_name, "local_only", str(local_path))
        return _read_csv_fast(local_path)

    try:
        df = _fetch_supabase_table(table_name, use_service_role=True)
        _record_table_load_status(table_name, "supabase_private", table_name)
        return df
    except Exception:
        if local_path.exists():
            _record_table_load_status(table_name, "local_fallback", str(local_path))
            return _read_csv_fast(local_path)
        raise


def _empty_capital_humano_frame() -> pd.DataFrame:
    """Retorna un DataFrame vacío con el esquema mínimo esperado por la app."""
    return pd.DataFrame(columns=CAPITAL_HUMANO_COLUMNS)


# ─── Gobernanza: timestamps de fuentes ────────────────────────────────────────

def _mtime(path: Path) -> str:
    """Devuelve la fecha de última modificación de un archivo como string."""
    try:
        ts = os.path.getmtime(path)
        return datetime.datetime.fromtimestamp(ts).strftime("%d/%m/%Y")
    except Exception:
        return "—"


def get_source_timestamps() -> dict:
    """Retorna un dict con la fecha de actualización de cada fuente de datos."""
    return {
        "OpenAlex (publicaciones)": _mtime(BASE_PUB / "cchen_openalex_works.csv"),
        "SJR / cuartiles": _mtime(BASE_PUB / "cchen_publications_with_quartile_sjr.csv"),
        "Autorías": _mtime(BASE_PUB / "cchen_authorships_enriched.csv"),
        "ANID": _mtime(BASE_ANID / "RepositorioAnid_con_monto.csv"),
        "Capital Humano": _mtime(SALIDA / "dataset_maestro_limpio.csv"),
        "Patentes (Lens.org)": _mtime(BASE_PAT / "cchen_patents.csv"),
        "CrossRef (financiadores)": _mtime(BASE_PUB / "cchen_crossref_enriched.csv"),
        "OpenAlex Conceptos":       _mtime(BASE_PUB / "cchen_openalex_concepts.csv"),
        "DataCite outputs":         _mtime(BASE / "ResearchOutputs" / "cchen_datacite_outputs.csv"),
        "OpenAIRE outputs":         _mtime(BASE / "ResearchOutputs" / "cchen_openaire_outputs.csv"),
        "ORCID Investigadores":     _mtime(BASE / "Researchers" / "cchen_researchers_orcid.csv"),
        "Registro institucional ROR": _mtime(BASE / "Institutional" / "cchen_institution_registry.csv"),
        "Pendientes ROR priorizados": _mtime(BASE / "Institutional" / "ror_pending_review.csv"),
        "Financiamiento adicional": _mtime(BASE / "Funding" / "cchen_funding_complementario.csv"),
        "Perfiles institucionales": _mtime(BASE / "Vigilancia" / "perfiles_institucionales_cchen.csv"),
        "Matching institucional": _mtime(BASE / "Vigilancia" / "convocatorias_matching_institucional.csv"),
        "Entidades persona": _mtime(BASE / "Gobernanza" / "entity_registry_personas.csv"),
        "Entidades proyecto": _mtime(BASE / "Gobernanza" / "entity_registry_proyectos.csv"),
        "Entidades convocatoria": _mtime(BASE / "Gobernanza" / "entity_registry_convocatorias.csv"),
        "Enlaces entre entidades": _mtime(BASE / "Gobernanza" / "entity_links.csv"),
        "Convenios nacionales":     _mtime(BASE / "Institutional" / "clean_Convenios_suscritos_por_la_Com.csv"),
        "Acuerdos internacionales": _mtime(BASE / "Institutional" / "clean_Acuerdos_e_instrumentos_intern.csv"),
        "Altmetric": _mtime(BASE_PUB / "cchen_altmetric.csv"),
    }


# ─── Publicaciones ────────────────────────────────────────────────────────────

def load_publications():
    df = _load_public_table("publications", BASE_PUB / "cchen_openalex_works.csv")
    df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
    df["cited_by_count"] = df["cited_by_count"].fillna(0).astype(int)
    return df[df["year"].notna() & (df["year"] >= 1990)].copy()


def load_publications_enriched():
    df = _load_public_table("publications_enriched", BASE_PUB / "cchen_publications_with_quartile_sjr.csv")
    df["year_num"] = pd.to_numeric(df["year_num"], errors="coerce").astype("Int64")
    return df[df["year_num"].notna() & (df["year_num"] >= 1990)].copy()


def load_authorships():
    return _load_public_table("authorships", BASE_PUB / "cchen_authorships_enriched.csv")


# ─── ANID ─────────────────────────────────────────────────────────────────────

def load_anid():
    df = _load_public_table("anid_projects", BASE_ANID / "RepositorioAnid_con_monto.csv")
    df["anio_concurso"] = pd.to_numeric(df["anio_concurso"], errors="coerce").astype("Int64")
    df["monto_programa_num"] = pd.to_numeric(df["monto_programa_num"], errors="coerce")
    # Supabase guarda programa_full→programa, instrumento_full→instrumento
    if "programa_full" not in df.columns and "programa" in df.columns:
        df = df.rename(columns={"programa": "programa_full"})
    if "instrumento_full" not in df.columns and "instrumento" in df.columns:
        df = df.rename(columns={"instrumento": "instrumento_full"})

    def norm_programa(p):
        if pd.isna(p):
            return "Sin clasificar"
        p = str(p)
        if "FONDECYT" in p.upper():
            return "FONDECYT"
        if "ASOCIATIVA" in p.upper() or "ANILLOS" in p.upper() or "PIA" in p.upper():
            return "Investigación Asociativa"
        if "INVESTIGACI" in p.upper():
            return "Proyectos de Investigación"
        return p.split("|")[0].strip()

    def norm_instrumento(i):
        if pd.isna(i):
            return "Sin clasificar"
        i = str(i).strip().upper()
        if "REGULAR" in i:
            return "Fondecyt Regular"
        if "INICIACI" in i:
            return "Fondecyt Iniciación"
        if "POSDOC" in i:
            return "Fondecyt Postdoctorado"
        if "ANILLO" in i:
            return "Anillos de Investigación"
        return str(i).title()

    df["programa_norm"]    = df["programa_full"].apply(norm_programa)
    df["instrumento_norm"] = df["instrumento_full"].apply(norm_instrumento)
    return df


# ─── Capital Humano ───────────────────────────────────────────────────────────

def load_capital_humano():
    path = SALIDA / "dataset_maestro_limpio.csv"
    try:
        df = _load_sensitive_table("capital_humano", path)
    except Exception:
        # En Streamlit Cloud no desplegamos este CSV sensible; la app debe seguir operativa.
        _record_table_load_status("capital_humano", "unavailable", str(path))
        df = _empty_capital_humano_frame()

    for col in CAPITAL_HUMANO_COLUMNS:
        if col not in df.columns:
            df[col] = pd.Series(dtype="object")

    if "anio_hoja" in df.columns:
        df["anio_hoja"] = pd.to_numeric(df["anio_hoja"], errors="coerce").astype("Int64")
    if "duracion_dias" in df.columns:
        df["duracion_dias"] = pd.to_numeric(df["duracion_dias"], errors="coerce")
    if "monto_contrato_num" in df.columns:
        df["monto_contrato_num"] = pd.to_numeric(df["monto_contrato_num"], errors="coerce")
    return df


def load_ch_resumen_ejecutivo():
    """JSON con KPIs ejecutivos ya calculados."""
    p = SALIDA / "resumen_ejecutivo.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {}


def load_ch_analisis_avanzado():
    """JSON con análisis avanzado: cohortes, trayectorias, concentración, semáforo."""
    p = AVANZADO / "resumen_analisis_avanzado.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {}


def load_ch_cumplimiento_centros():
    p = AVANZADO / "cumplimiento_documental_centros.csv"
    if p.exists():
        try: return _read_csv_fast(p)
        except Exception: pass
    return pd.DataFrame()


def load_ch_transiciones():
    p = AVANZADO / "transiciones_modalidad.csv"
    if p.exists():
        try: return _read_csv_fast(p)
        except Exception: pass
    return pd.DataFrame()


def load_ch_participacion_tipo_anio():
    p = CAPITAL / "participacion_tipo_anio.csv"
    if p.exists():
        try: return _read_csv_fast(p)
        except Exception: pass
    return pd.DataFrame()


# ─── Publicaciones DIAN ───────────────────────────────────────────────────────

def load_dian_publications():
    """Carga el registro interno de publicaciones DIAN CCHEN.
    Prioridad: Supabase → Excel local → DataFrame vacío.
    """
    # 1. Intentar Supabase (tabla dian_publications)
    try:
        sb = _supabase_client()
        if sb is not None:
            resp = sb.table("dian_publications").select("*").execute()
            if resp.data:
                df = pd.DataFrame(resp.data)
                if "anio" in df.columns:
                    df["anio"] = pd.to_numeric(df["anio"], errors="coerce").astype("Int64")
                return df[df["titulo"].notna()].copy()
    except Exception:
        pass

    # 2. Excel local
    p = BASE / "Publicaciones DIAN CCHEN" / "Publicaciones DIAN.xlsx"
    if not p.exists():
        return pd.DataFrame()
    try:
        df = pd.read_excel(p, sheet_name="Consolidado", header=0, engine="openpyxl")
        df = df.dropna(how="all").dropna(axis=1, how="all")
        df.columns = [str(c).strip() for c in df.columns]
        col_map = {
            "Nombre del Artículo": "titulo",
            "Autores": "autores",
            "Revista": "revista",
            "Cuartil": "cuartil",
            "DOI": "doi",
            "Unidad": "unidad",
            "Fecha de publicación": "fecha_publicacion",
            "Año de aceptación": "anio",
        }
        df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})
        if "anio" not in df.columns and "fecha_publicacion" in df.columns:
            df["anio"] = pd.to_datetime(df["fecha_publicacion"], errors="coerce").dt.year
        if "anio" in df.columns:
            df["anio"] = pd.to_numeric(df["anio"], errors="coerce").astype("Int64")
        if "cuartil" in df.columns:
            df["cuartil"] = df["cuartil"].astype(str).str.extract(r"(Q[1-4])", expand=False)
        return df[df["titulo"].notna()].copy()
    except Exception:
        return pd.DataFrame()


# ─── Patentes ─────────────────────────────────────────────────────────────────

def _normalize_patents_frame(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    if "year" not in df.columns:
        for col in ("publication_year", "grant_year", "fecha_solicitud"):
            if col in df.columns:
                df["year"] = pd.to_numeric(
                    df[col].astype(str).str[:4], errors="coerce"
                ).astype("Int64")
                break
    if "cited_by_count" not in df.columns:
        df["cited_by_count"] = 0
    df["cited_by_count"] = pd.to_numeric(df["cited_by_count"], errors="coerce").fillna(0).astype(int)
    return df


def _load_patents_local() -> pd.DataFrame:
    """Carga patentes descargadas vía script o notebook (Lens.org / PatentsView)."""
    dfs = []
    for fname in ("cchen_patents.csv", "cchen_patents_uspto.csv", "cchen_patents_manual.csv",
                  "cchen_inapi_patents.csv"):
        p = BASE_PAT / fname
        if not p.exists():
            continue
        df = _read_csv_fast(p)
        dfs.append(_normalize_patents_frame(df))
    if dfs:
        return pd.concat(dfs, ignore_index=True)
    return pd.DataFrame()


def load_patents():
    """Carga patentes desde Supabase público si está disponible; si no, usa archivos locales."""
    mode = _get_data_source_mode()
    if mode != "local":
        try:
            remote = _fetch_supabase_table("patents")
            if not remote.empty or mode == "supabase_public":
                _record_table_load_status("patents", "supabase_public", "patents")
                return _normalize_patents_frame(remote)
        except Exception:
            if mode == "supabase_public":
                raise
    local = _load_patents_local()
    if not local.empty:
        source = "local_only" if mode == "local" else "local_fallback"
        _record_table_load_status("patents", source, str(BASE_PAT))
        return local
    _record_table_load_status("patents", "unavailable", str(BASE_PAT))
    return local


# ─── CrossRef enrichment ──────────────────────────────────────────────────────

def load_crossref_enriched():
    """Datos CrossRef: financiadores externos, referencias, abstracts."""
    p = BASE_PUB / "cchen_crossref_enriched.csv"
    if not p.exists():
        return pd.DataFrame()
    df = _load_public_table("crossref_data", p)
    return df.drop_duplicates(subset=["doi"])


def load_publications_full():
    """Publicaciones con CrossRef + OpenAlex combinados."""
    p = BASE_PUB / "cchen_publications_full.csv"
    if p.exists():
        df = _read_csv_fast(p)
        df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
        df["cited_by_count"] = df["cited_by_count"].fillna(0).astype(int)
        return df[df["year"].notna() & (df["year"] >= 1990)].copy()
    return load_publications()  # fallback


# ─── OpenAlex Concepts ────────────────────────────────────────────────────────

def load_concepts():
    """Conceptos/áreas temáticas por paper (OpenAlex concepts + topics)."""
    p = BASE_PUB / "cchen_openalex_concepts.csv"
    if not p.exists():
        return pd.DataFrame()
    df = _load_public_table("concepts", p)
    df["concept_score"] = pd.to_numeric(df["concept_score"], errors="coerce")
    return df


def load_grants_openalex():
    """Financiamiento detectado por OpenAlex en los papers."""
    p = BASE_PUB / "cchen_openalex_grants.csv"
    if not p.exists():
        return pd.DataFrame()
    try:
        return _read_csv_fast(p)
    except Exception:
        return pd.DataFrame()


def load_publications_with_concepts():
    """Publicaciones con columna top_concepts agregada."""
    p = BASE_PUB / "cchen_publications_with_concepts.csv"
    if p.exists():
        df = _read_csv_fast(p)
        df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
        df["cited_by_count"] = df["cited_by_count"].fillna(0).astype(int)
        return df[df["year"].notna() & (df["year"] >= 1990)].copy()
    return load_publications()


# ─── ORCID Researchers ────────────────────────────────────────────────────────

def load_orcid_researchers():
    """Perfiles ORCID de investigadores CCHEN."""
    p = BASE / "Researchers" / "cchen_researchers_orcid.csv"
    if not p.exists():
        if _get_data_source_mode() in {"auto", "supabase_public"}:
            try:
                return _fetch_supabase_table("researchers_orcid")
            except Exception:
                if _get_data_source_mode() == "supabase_public":
                    raise
        return pd.DataFrame()
    try:
        return _load_public_table("researchers_orcid", p)
    except Exception:
        return pd.DataFrame()


# ─── DataCite outputs ────────────────────────────────────────────────────────

def load_datacite_outputs():
    """Outputs DataCite asociados a CCHEN vía ROR institucional."""
    p = BASE / "ResearchOutputs" / "cchen_datacite_outputs.csv"
    if not p.exists():
        if _get_data_source_mode() in {"auto", "supabase_public"}:
            try:
                return _fetch_supabase_table("datacite_outputs")
            except Exception:
                if _get_data_source_mode() == "supabase_public":
                    raise
        return pd.DataFrame()
    try:
        df = _load_public_table("datacite_outputs", p)
        if "publication_year" in df.columns:
            df["publication_year"] = pd.to_numeric(df["publication_year"], errors="coerce").astype("Int64")
        return df
    except Exception:
        return pd.DataFrame()


# ─── OpenAIRE outputs ────────────────────────────────────────────────────────

def load_openaire_outputs():
    """Outputs OpenAIRE asociados a investigadores CCHEN vía ORCID."""
    p = BASE / "ResearchOutputs" / "cchen_openaire_outputs.csv"
    if not p.exists():
        if _get_data_source_mode() in {"auto", "supabase_public"}:
            try:
                return _fetch_supabase_table("openaire_outputs")
            except Exception:
                if _get_data_source_mode() == "supabase_public":
                    raise
        return pd.DataFrame()
    try:
        df = _load_public_table("openaire_outputs", p)
        if "matched_cchen_researchers_count" in df.columns:
            df["matched_cchen_researchers_count"] = pd.to_numeric(
                df["matched_cchen_researchers_count"], errors="coerce"
            ).fillna(0).astype(int)
        return df
    except Exception:
        return pd.DataFrame()


# ─── Registro institucional ROR ──────────────────────────────────────────────

def load_ror_registry():
    """Registro institucional consolidado con ancla ROR para CCHEN y colaboradoras."""
    p = BASE / "Institutional" / "cchen_institution_registry.csv"
    if not p.exists():
        if _get_data_source_mode() in {"auto", "supabase_public"}:
            try:
                return _fetch_supabase_table("institution_registry")
            except Exception:
                if _get_data_source_mode() == "supabase_public":
                    raise
        return pd.DataFrame()
    try:
        return _load_public_table("institution_registry", p)
    except Exception:
        return pd.DataFrame()


def load_ror_pending_review():
    """Cola priorizada de instituciones pendientes de revisión manual en ROR."""
    p = BASE / "Institutional" / "ror_pending_review.csv"
    if not p.exists():
        if _get_data_source_mode() in {"auto", "supabase_public"}:
            try:
                return _fetch_supabase_table("institution_registry_pending_review")
            except Exception:
                if _get_data_source_mode() == "supabase_public":
                    raise
        return pd.DataFrame()
    try:
        df = _load_public_table("institution_registry_pending_review", p)
        for col in ["authorships_count", "orcid_profiles_count", "convenios_count", "signal_total"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
        return df
    except Exception:
        return pd.DataFrame()


# ─── Financiamiento complementario ───────────────────────────────────────────

def load_funding_complementario():
    """Proyectos de financiamiento más allá de ANID (CORFO, IAEA TC, etc.)."""
    p = BASE / "Funding" / "cchen_funding_complementario.csv"
    try:
        df = _load_sensitive_table("funding_complementario", p)
        if "anio" in df.columns:
            df["anio"] = pd.to_numeric(df["anio"], errors="coerce").astype("Int64")
        return df
    except Exception:
        return pd.DataFrame()


def load_iaea_tc():
    """Proyectos de Cooperación Técnica IAEA con Chile."""
    p = BASE / "Funding" / "cchen_iaea_tc.csv"
    if not p.exists():
        return pd.DataFrame()
    try:
        return _read_csv_fast(p)
    except Exception:
        return pd.DataFrame()


def load_perfiles_institucionales():
    """Perfiles institucionales curados para matching de convocatorias."""
    p = BASE / "Vigilancia" / "perfiles_institucionales_cchen.csv"
    return _load_public_table("perfiles_institucionales", p)


def load_convocatorias() -> pd.DataFrame:
    """Convocatorias de financiamiento curadas."""
    p = BASE / "Vigilancia" / "convocatorias_curadas.csv"
    if not p.exists():
        p = BASE / "Vigilancia" / "convocatorias.csv"
    return _load_public_table("convocatorias", p)


def load_convocatorias_matching_rules() -> pd.DataFrame:
    """Reglas explícitas de elegibilidad para matching de convocatorias."""
    p = BASE / "Vigilancia" / "convocatorias_matching_rules.csv"
    return _load_public_table("convocatorias_matching_rules", p)


def load_matching_institucional():
    """Matching institucional formal de convocatorias abiertas y próximas."""
    p = BASE / "Vigilancia" / "convocatorias_matching_institucional.csv"
    try:
        df = _load_public_table("convocatorias_matching_institucional", p)
        if "score_total" in df.columns:
            df["score_total"] = pd.to_numeric(df["score_total"], errors="coerce").fillna(0).astype(int)
        return df
    except Exception:
        return pd.DataFrame()


def _load_governance_csv(filename: str) -> pd.DataFrame:
    p = BASE / "Gobernanza" / filename
    if not p.exists():
        return pd.DataFrame()
    try:
        return _read_csv_fast(p)
    except Exception:
        return pd.DataFrame()


def load_entity_registry_personas():
    """Registro canónico de personas del observatorio."""
    p = BASE / "Gobernanza" / "entity_registry_personas.csv"
    try:
        return _load_sensitive_table("entity_registry_personas", p)
    except Exception:
        return pd.DataFrame()


def load_entity_registry_proyectos():
    """Registro canónico de proyectos del observatorio."""
    p = BASE / "Gobernanza" / "entity_registry_proyectos.csv"
    try:
        return _load_public_table("entity_registry_proyectos", p)
    except Exception:
        return pd.DataFrame()


def load_entity_registry_convocatorias():
    """Registro canónico de convocatorias del observatorio."""
    p = BASE / "Gobernanza" / "entity_registry_convocatorias.csv"
    try:
        return _load_public_table("entity_registry_convocatorias", p)
    except Exception:
        return pd.DataFrame()


def load_entity_links():
    """Enlaces operativos entre entidades canónicas del observatorio."""
    p = BASE / "Gobernanza" / "entity_links.csv"
    try:
        return _load_sensitive_table("entity_links", p)
    except Exception:
        return pd.DataFrame()


# ─── Datos institucionales (datos.gob.cl) ────────────────────────────────────

BASE_INST = BASE / "Institutional"

def load_convenios_nacionales():
    """Convenios nacionales suscritos por CCHEN (datos.gob.cl)."""
    source_mode = _get_data_source_mode()
    if source_mode in {"auto", "supabase_public"}:
        try:
            df = _fetch_supabase_table("convenios_nacionales")
            if source_mode == "supabase_public" or not df.empty:
                return df
        except Exception:
            if source_mode == "supabase_public":
                raise
    for fname in ("clean_Convenios_suscritos_por_la_Com.csv",
                  "Convenios_suscritos_por_la_Com.csv"):
        p = BASE_INST / fname
        if p.exists():
            try:
                df = pd.read_csv(p, encoding="utf-8", on_bad_lines="skip")
                df.columns = [str(c).strip() for c in df.columns]
                return df.dropna(how="all")
            except Exception:
                pass
    return pd.DataFrame()


def load_acuerdos_internacionales():
    """Acuerdos internacionales CCHEN (datos.gob.cl).
    Parsea el archivo multi-sección para extraer los registros reales.
    """
    source_mode = _get_data_source_mode()
    if source_mode in {"auto", "supabase_public"}:
        try:
            df = _fetch_supabase_table("acuerdos_internacionales")
            if source_mode == "supabase_public" or not df.empty:
                return df
        except Exception:
            if source_mode == "supabase_public":
                raise
    for fname in ("clean_Acuerdos_e_instrumentos_intern.csv",
                  "Acuerdos_e_instrumentos_intern.csv"):
        p = BASE_INST / fname
        if not p.exists():
            continue
        try:
            raw = pd.read_csv(p, encoding="utf-8", on_bad_lines="skip", header=None)
            rows = []
            current_section = ""
            for _, row in raw.iterrows():
                v0 = str(row.iloc[0]) if pd.notna(row.iloc[0]) else ""
                vals = [str(v).strip() if pd.notna(v) else "" for v in row.values]
                if "TABLA" in v0.upper():
                    current_section = v0.strip()
                    continue
                if v0 == "Nº" or (len(vals) > 1 and vals[0] == "Nº"):
                    continue
                if v0.strip().isdigit() and len(vals) >= 2 and vals[1]:
                    rows.append({
                        "Sección":     current_section,
                        "N":           v0.strip(),
                        "País":        vals[1],
                        "Instrumento": vals[2] if len(vals) > 2 else "",
                        "Firma":       vals[3] if len(vals) > 3 else "",
                        "Vigencia":    vals[4] if len(vals) > 4 else "",
                    })
            if rows:
                return pd.DataFrame(rows)
        except Exception:
            pass
    return pd.DataFrame()


# ─── Unpaywall OA enrichment ──────────────────────────────────────────────────

def load_unpaywall_oa():
    """Datos de acceso abierto desde Unpaywall (enriquecimiento por DOI)."""
    p = BASE_PUB / "cchen_unpaywall_oa.csv"
    if not p.exists():
        return pd.DataFrame()
    try:
        df = _read_csv_fast(p)
        for col in ("is_oa", "journal_is_oa"):
            if col in df.columns:
                df[col] = df[col].map({"True": True, "False": False, True: True, False: False}).fillna(False)
        return df
    except Exception:
        return pd.DataFrame()


# ─── IAEA INIS vigilancia ─────────────────────────────────────────────────────

def load_iaea_inis():
    """Documentos IAEA INIS de vigilancia tecnológica nuclear."""
    p = BASE / "Vigilancia" / "iaea_inis_monitor.csv"
    return _load_public_table("iaea_inis_monitor", p)


def load_arxiv_monitor() -> pd.DataFrame:
    """Papers arXiv monitoreados en áreas relevantes para CCHEN."""
    p = BASE / "Vigilancia" / "arxiv_monitor.csv"
    return _load_public_table("arxiv_monitor", p)


def load_news_monitor() -> pd.DataFrame:
    """Noticias de prensa sobre CCHEN (Google News RSS)."""
    p = BASE / "Vigilancia" / "news_monitor.csv"
    return _load_public_table("news_monitor", p)


def load_citation_graph() -> pd.DataFrame:
    """Grafo de citas OpenAlex — openalex_id, cited_by_count, referenced_works_count, year"""
    p = BASE_PUB / "cchen_citation_graph.csv"
    df = _load_public_table("citation_graph", p)
    if df.empty:
        return pd.DataFrame(columns=["openalex_id","doi","year","cited_by_count",
                                      "referenced_works_count","referenced_ids_sample","fetched_at"])
    for col in ("cited_by_count", "referenced_works_count"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
    return df


def load_citing_papers() -> pd.DataFrame:
    """Papers externos que citan publicaciones CCHEN"""
    p = BASE_PUB / "cchen_citing_papers.csv"
    try:
        return _load_public_table("citing_papers", p).fillna("")
    except Exception:
        return pd.DataFrame(columns=["citing_id","cited_cchen_id","citing_doi",
                                      "citing_title","citing_year","citing_institutions"])


# ─── Altmetric ────────────────────────────────────────────────────────────────

def load_altmetric() -> pd.DataFrame:
    """Métricas de impacto alternativo (Altmetric) por DOI.
    Retorna DataFrame vacío si aún no se ha ejecutado fetch_altmetric.py.
    """
    p = BASE_PUB / "cchen_altmetric.csv"
    if not p.exists():
        return pd.DataFrame()
    try:
        df = _read_csv_fast(p)
        if df.empty:
            return df
        for col in ("altmetric_score", "altmetric_score_1y", "altmetric_score_3m",
                    "cited_by_posts_count", "cited_by_tweeters_count",
                    "cited_by_newsoutlets_count", "cited_by_policies_count",
                    "cited_by_wikipedia_count", "cited_by_reddits_count",
                    "cited_by_feeds_count", "mendeley_readers"):
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
        return df
    except Exception:
        return pd.DataFrame()


# ─── BERTopic ─────────────────────────────────────────────────────────────────

def load_bertopic_topics() -> pd.DataFrame:
    """Asignación de topics BERTopic por paper CCHEN."""
    p = BASE_PUB / "cchen_bertopic_topics.csv"
    df = _load_public_table("bertopic_topics", p)
    if not df.empty:
        for col in ("topic_id",):
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
    return df


def load_bertopic_topic_info() -> pd.DataFrame:
    """Metadatos de topics BERTopic (nombre, palabras clave, docs representativos)."""
    p = BASE_PUB / "cchen_bertopic_topic_info.csv"
    df = _load_public_table("bertopic_topic_info", p)
    if not df.empty:
        rename = {c: c.capitalize() for c in df.columns}
        # Normalizar nombres al formato que usa el dashboard (Topic, Count, Name, ...)
        col_map = {
            "topic": "Topic", "count": "Count", "name": "Name",
            "representation": "Representation", "representative_docs": "Representative_Docs",
        }
        df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})
        if "Topic" in df.columns:
            df["Topic"] = pd.to_numeric(df["Topic"], errors="coerce").astype("Int64")
    return df


# ─── EuroPMC ──────────────────────────────────────────────────────────────────

def load_europmc() -> pd.DataFrame:
    """Publicaciones CCHEN indexadas en EuroPMC (PubMed/PMC/bioRxiv)."""
    p = BASE_PUB / "cchen_europmc_works.csv"
    df = _load_public_table("europmc_works", p)
    if df.empty:
        return df
    if "year" in df.columns:
        df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
    if "cited_by_count" in df.columns:
        df["cited_by_count"] = pd.to_numeric(df["cited_by_count"], errors="coerce").fillna(0).astype(int)
    return df
