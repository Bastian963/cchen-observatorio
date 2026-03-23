"""
migrate_to_supabase.py — Observatorio CCHEN 360°
=================================================
Migra todos los CSVs locales a Supabase (PostgreSQL).

USO:
    cd /Users/bastianayalainostroza/Dropbox/CCHEN
    python Database/migrate_to_supabase.py

REQUISITOS:
    pip install supabase pandas openpyxl python-dotenv
    Tener configurado Database/.env con SUPABASE_URL y SUPABASE_KEY

IMPORTANTE: Este script es IDEMPOTENTE — usa upsert para poder
ejecutarlo múltiples veces sin duplicar datos.

ORDEN DE EJECUCIÓN (por dependencias FK):
    1. publications        (tabla base)
    2. publications_enriched (FK → publications)
    3. authorships         (FK → publications)
    4. crossref_data       (FK → publications.doi)
    5. concepts            (FK → publications)
    6. patents
    7. anid_projects
    8. funding_complementario
   9. capital_humano
    10. researchers_orcid
    11. institution_registry
    12. institution_registry_pending_review
   13. entity_registry_personas
   14. entity_registry_proyectos
   15. entity_registry_convocatorias
   16. entity_links
   17. convocatorias_matching_institucional
   18. datacite_outputs
   19. openaire_outputs
   20. convenios_nacionales
   21. acuerdos_internacionales
   22. data_sources        (metadatos, pre-cargado en schema.sql)
"""

import os
import sys
import math
import datetime
import warnings
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

# ─── Configuración de rutas ────────────────────────────────────────────────────

ROOT     = Path(__file__).parent.parent          # /CCHEN/
DATA     = ROOT / "Data"
PUB      = DATA / "Publications"
PAT_DIR  = DATA / "Patents"
ANID_DIR = DATA / "ANID"
INST_DIR = DATA / "Institutional"
RES_DIR  = DATA / "Researchers"
FUND_DIR = DATA / "Funding"
RO_DIR   = DATA / "ResearchOutputs"
CH_DIR   = DATA / "Capital humano CCHEN" / "salida_dataset_maestro"
GOV_DIR  = DATA / "Gobernanza"
VIG_DIR  = DATA / "Vigilancia"

# ─── Cargar credenciales ───────────────────────────────────────────────────────

load_dotenv(ROOT / "Database" / ".env")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    sys.exit(
        "\n[ERROR] Faltan credenciales.\n"
        "Crea el archivo Database/.env con:\n"
        "  SUPABASE_URL=https://xxxx.supabase.co\n"
        "  SUPABASE_KEY=eyJ...\n"
        "Ver Database/.env.example para más detalles.\n"
    )

# ─── Conexión a Supabase ───────────────────────────────────────────────────────

try:
    from supabase import create_client, Client
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print(f"[OK] Conectado a Supabase: {SUPABASE_URL}")
except ImportError:
    sys.exit("[ERROR] Instala la librería: pip install supabase")
except Exception as e:
    sys.exit(f"[ERROR] No se pudo conectar a Supabase: {e}")


# ─── Utilidades ────────────────────────────────────────────────────────────────

REPORT: list[dict] = []
CHUNK_SIZE = 500       # filas por batch (Supabase recomienda ≤1000)


def _clean(val):
    """Convierte NaN/NaT/inf a None para que Supabase los acepte como NULL."""
    if val is None:
        return None
    if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
        return None
    if isinstance(val, bool):
        return bool(val)
    # pandas Int64 → int Python
    try:
        import pandas as pd
        if pd.isna(val):
            return None
    except (TypeError, ValueError):
        pass
    if hasattr(val, 'item'):        # numpy scalars
        return val.item()
    return val


def _to_records(df: pd.DataFrame) -> list[dict]:
    """Convierte un DataFrame a lista de dicts limpios para Supabase."""
    records = []
    for row in df.to_dict(orient="records"):
        records.append({k: _clean(v) for k, v in row.items()})
    return records


def _read_csv_flexible(path: Path) -> pd.DataFrame:
    """Lee CSV con BOM tolerante y fallback simple."""
    try:
        return pd.read_csv(path, encoding="utf-8-sig")
    except Exception:
        return pd.read_csv(path)


def upsert_table(table: str, records: list[dict], on_conflict: str) -> dict:
    """
    Upserta registros en una tabla Supabase en batches.
    Retorna resumen {table, rows, batches, errors}.
    """
    if not records:
        print(f"  [{table}] Sin registros — omitiendo.")
        return {"table": table, "rows": 0, "batches": 0, "errors": 0}

    total   = len(records)
    batches = math.ceil(total / CHUNK_SIZE)
    errors  = 0

    print(f"  [{table}] Subiendo {total} filas en {batches} batches...", end="", flush=True)
    for i in range(batches):
        chunk = records[i * CHUNK_SIZE: (i + 1) * CHUNK_SIZE]
        try:
            supabase.table(table).upsert(chunk, on_conflict=on_conflict).execute()
            print(".", end="", flush=True)
        except Exception as e:
            errors += 1
            print(f"\n  [WARN] Batch {i+1}/{batches} falló: {e}")

    status = "OK" if errors == 0 else f"{errors} errores"
    print(f" {status}")
    return {"table": table, "rows": total, "batches": batches, "errors": errors}


# ─── Migración tabla por tabla ─────────────────────────────────────────────────

def migrate_publications():
    """publications (PK: openalex_id)"""
    p = PUB / "cchen_openalex_works.csv"
    if not p.exists():
        print(f"  [publications] Archivo no encontrado: {p}")
        return
    df = pd.read_csv(p)
    df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
    df["cited_by_count"] = pd.to_numeric(df["cited_by_count"], errors="coerce").fillna(0).astype(int)
    df["is_oa"] = df["is_oa"].map(lambda x: bool(x) if pd.notna(x) else False)

    cols = ["openalex_id", "doi", "title", "year", "type", "source",
            "cited_by_count", "is_oa", "oa_status", "oa_url"]
    df = df[[c for c in cols if c in df.columns]].drop_duplicates(subset=["openalex_id"])

    REPORT.append(upsert_table("publications", _to_records(df), "openalex_id"))


def migrate_publications_enriched():
    """publications_enriched (PK: work_id → FK publications)"""
    p = PUB / "cchen_publications_with_quartile_sjr.csv"
    if not p.exists():
        print(f"  [publications_enriched] Archivo no encontrado: {p}")
        return
    df = pd.read_csv(p)
    df["year_num"] = pd.to_numeric(df.get("year_num", df.get("year")), errors="coerce").astype("Int64")

    cols = ["work_id", "doi", "year_num", "type_norm", "source_norm",
            "n_authorships", "n_unique_institutions",
            "has_outside_cchen_collab", "has_international_collab",
            "cchen_has_first_author", "cchen_has_last_author", "n_cchen_authors",
            "quartile", "sjr_num", "categories", "areas",
            "match_status", "is_retracted", "oa_status"]
    df = df[[c for c in cols if c in df.columns]].drop_duplicates(subset=["work_id"])

    # Solo subir work_ids que existen en publications
    REPORT.append(upsert_table("publications_enriched", _to_records(df), "work_id"))


def migrate_authorships():
    """authorships (no PK propio; upsert por work_id+author_id)"""
    p = PUB / "cchen_authorships_enriched.csv"
    if not p.exists():
        print(f"  [authorships] Archivo no encontrado: {p}")
        return
    df = pd.read_csv(p)

    cols = ["work_id", "author_id", "author_name", "author_order", "author_position",
            "is_first_author", "is_last_author", "institution_id", "institution_name",
            "institution_country_code", "institution_ror", "is_cchen_affiliation"]
    df = df[[c for c in cols if c in df.columns]]
    df = df.dropna(subset=["work_id", "author_name"])

    # Autorships no tiene PK único simple; insertamos con ignore_duplicates
    # (no es upsert real — en Supabase se usa "id" serial si existe, o insert)
    # Usamos delete-then-insert por tabla completa para idempotencia
    print(f"  [authorships] Limpiando tabla antes de re-insertar...", end="", flush=True)
    try:
        supabase.table("authorships").delete().neq("id", 0).execute()
        print(" OK")
    except Exception as e:
        print(f"\n  [WARN] No se pudo limpiar authorships: {e}")

    records = _to_records(df)
    total   = len(records)
    batches = math.ceil(total / CHUNK_SIZE)
    errors  = 0

    print(f"  [authorships] Insertando {total} filas en {batches} batches...", end="", flush=True)
    for i in range(batches):
        chunk = records[i * CHUNK_SIZE: (i + 1) * CHUNK_SIZE]
        try:
            supabase.table("authorships").insert(chunk).execute()
            print(".", end="", flush=True)
        except Exception as e:
            errors += 1
            print(f"\n  [WARN] Batch {i+1}/{batches} falló: {e}")

    status = "OK" if errors == 0 else f"{errors} errores"
    print(f" {status}")
    REPORT.append({"table": "authorships", "rows": total, "batches": batches, "errors": errors})


def migrate_crossref():
    """crossref_data (PK: doi → FK publications.doi)"""
    p = PUB / "cchen_crossref_enriched.csv"
    if not p.exists():
        print(f"  [crossref_data] Archivo no encontrado: {p}")
        return
    df = pd.read_csv(p)
    df = df.drop_duplicates(subset=["doi"]).dropna(subset=["doi"])

    cols = ["doi", "crossref_funders", "crossref_funder_doi",
            "references_count", "cited_by_crossref", "abstract",
            "license_url", "publisher", "subject"]
    df = df[[c for c in cols if c in df.columns]]
    for int_col in ("references_count", "cited_by_crossref"):
        if int_col in df.columns:
            df[int_col] = pd.to_numeric(df[int_col], errors="coerce").astype("Int64")

    REPORT.append(upsert_table("crossref_data", _to_records(df), "doi"))


def migrate_concepts():
    """concepts (delete-then-insert para idempotencia)"""
    p = PUB / "cchen_openalex_concepts.csv"
    if not p.exists():
        print(f"  [concepts] Archivo no encontrado: {p}")
        return
    df = pd.read_csv(p)
    df["concept_score"] = pd.to_numeric(df["concept_score"], errors="coerce")
    df = df.dropna(subset=["work_id", "concept_name"])

    cols = ["work_id", "concept_name", "concept_level", "concept_score", "source"]
    df = df[[c for c in cols if c in df.columns]]

    # Delete-then-insert (tabla grande, serial PK)
    print(f"  [concepts] Limpiando tabla antes de re-insertar...", end="", flush=True)
    try:
        supabase.table("concepts").delete().neq("id", 0).execute()
        print(" OK")
    except Exception as e:
        print(f"\n  [WARN] No se pudo limpiar concepts: {e}")

    records = _to_records(df)
    total   = len(records)
    batches = math.ceil(total / CHUNK_SIZE)
    errors  = 0
    print(f"  [concepts] Insertando {total} filas en {batches} batches...", end="", flush=True)
    for i in range(batches):
        chunk = records[i * CHUNK_SIZE: (i + 1) * CHUNK_SIZE]
        try:
            supabase.table("concepts").insert(chunk).execute()
            print(".", end="", flush=True)
        except Exception as e:
            errors += 1
            print(f"\n  [WARN] Batch {i+1}/{batches} falló: {e}")
    status = "OK" if errors == 0 else f"{errors} errores"
    print(f" {status}")
    REPORT.append({"table": "concepts", "rows": total, "batches": batches, "errors": errors})


def migrate_patents():
    """patents (PK lógico: patent_uid)"""
    frames = []
    for fname in ("cchen_patents.csv", "cchen_patents_uspto.csv", "cchen_patents_manual.csv"):
        p = PAT_DIR / fname
        if not p.exists():
            continue
        try:
            df = pd.read_csv(p)
            df["source_file"] = fname
            frames.append(df)
        except Exception as e:
            print(f"  [patents] Error leyendo {fname}: {e}")
    if not frames:
        print(f"  [patents] No se encontraron archivos en: {PAT_DIR}")
        return

    df = pd.concat(frames, ignore_index=True, sort=False)

    if "publication_date" in df.columns:
        df["publication_date"] = pd.to_datetime(df["publication_date"], errors="coerce").dt.strftime("%Y-%m-%d")
        df["publication_date"] = df["publication_date"].where(df["publication_date"].notna(), None)
    if "filing_date" in df.columns:
        df["filing_date"] = pd.to_datetime(df["filing_date"], errors="coerce").dt.strftime("%Y-%m-%d")
        df["filing_date"] = df["filing_date"].where(df["filing_date"].notna(), None)

    for col in ["publication_year", "grant_year", "n_inventors_cl", "cited_by_count"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "applicants" in df.columns and "assignees" not in df.columns:
        df["assignees"] = df["applicants"]
    if "_query_org" in df.columns and "query_org" not in df.columns:
        df["query_org"] = df["_query_org"]

    patent_id = df["patent_id"] if "patent_id" in df.columns else pd.Series(index=df.index, dtype="object")
    lens_id = df["lens_id"] if "lens_id" in df.columns else pd.Series(index=df.index, dtype="object")
    doc_number = df["doc_number"] if "doc_number" in df.columns else pd.Series(index=df.index, dtype="object")
    df["patent_uid"] = patent_id.fillna(lens_id).fillna(doc_number).astype(str).str.strip()
    df = df[(df["patent_uid"] != "") & (df["patent_uid"] != "nan")].copy()

    cols = [
        "patent_uid", "lens_id", "patent_id", "doc_number", "doc_key", "title",
        "abstract", "jurisdiction", "publication_date", "filing_date",
        "publication_year", "grant_year", "publication_type", "assignees",
        "assignee_countries", "inventors", "inventor_countries", "n_inventors_cl",
        "ipc_symbols", "cited_by_count", "source", "query_org", "patent_url",
    ]
    df = df[[c for c in cols if c in df.columns]].drop_duplicates(subset=["patent_uid"], keep="first")
    REPORT.append(upsert_table("patents", _to_records(df), "patent_uid"))


def migrate_anid():
    """anid_projects (PK: proyecto — código ANID)"""
    p = ANID_DIR / "RepositorioAnid_con_monto.csv"
    if not p.exists():
        print(f"  [anid_projects] Archivo no encontrado: {p}")
        return
    df = pd.read_csv(p)
    df["anio_concurso"] = pd.to_numeric(df.get("anio_concurso"), errors="coerce").astype("Int64")
    df["monto_programa_num"] = pd.to_numeric(df.get("monto_programa_num"), errors="coerce")

    # Normalización (misma lógica que data_loader.py)
    def norm_programa(p_val):
        if pd.isna(p_val):
            return "Sin clasificar"
        s = str(p_val).upper()
        if "FONDECYT" in s:
            return "FONDECYT"
        if "ASOCIATIVA" in s or "ANILLOS" in s or "PIA" in s:
            return "Investigación Asociativa"
        if "INVESTIGACI" in s:
            return "Proyectos de Investigación"
        return str(p_val).split("|")[0].strip()

    def norm_instrumento(i_val):
        if pd.isna(i_val):
            return "Sin clasificar"
        s = str(i_val).strip().upper()
        if "REGULAR" in s:
            return "Fondecyt Regular"
        if "INICIACI" in s:
            return "Fondecyt Iniciación"
        if "POSDOC" in s:
            return "Fondecyt Postdoctorado"
        if "ANILLO" in s:
            return "Anillos de Investigación"
        return str(i_val).title()

    df["programa_norm"]    = df["programa_full"].apply(norm_programa)
    df["instrumento_norm"] = df["instrumento_full"].apply(norm_instrumento)

    col_map = {
        "titulo": "titulo", "resumen": "resumen",
        "autor": "autor", "institucion": "institucion", "proyecto": "proyecto",
        "programa_full": "programa", "programa_norm": "programa_norm",
        "instrumento_full": "instrumento", "instrumento_norm": "instrumento_norm",
        "estado_full": "estado_full", "anio_concurso": "anio_concurso",
        "monto_programa_num": "monto_programa_num", "link": "link",
    }
    # Columna estado
    for col_name in ("estado", "Estado"):
        if col_name in df.columns:
            col_map[col_name] = "estado"
            break

    df2 = pd.DataFrame()
    for src, dst in col_map.items():
        if src in df.columns:
            df2[dst] = df[src]

    df2 = df2.dropna(subset=["proyecto"]).drop_duplicates(subset=["proyecto"])
    REPORT.append(upsert_table("anid_projects", _to_records(df2), "proyecto"))


def migrate_funding_complementario():
    """funding_complementario (PK: funding_id)"""
    p = FUND_DIR / "cchen_funding_complementario.csv"
    if not p.exists():
        print(f"  [funding_complementario] Archivo no encontrado: {p}")
        return
    df = _read_csv_flexible(p)
    cols = [
        "funding_id", "fuente", "instrumento", "titulo", "anio", "investigador_principal",
        "institucion", "monto", "moneda", "estado", "programa", "url", "area_cchen",
        "elegibilidad_base", "source_confidence", "last_verified_at", "observaciones",
    ]
    df = df[[c for c in cols if c in df.columns]].dropna(subset=["funding_id"])
    for col in ["anio", "monto"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "last_verified_at" in df.columns:
        df["last_verified_at"] = pd.to_datetime(df["last_verified_at"], errors="coerce").dt.strftime("%Y-%m-%d")
        df["last_verified_at"] = df["last_verified_at"].where(df["last_verified_at"].notna(), None)
    REPORT.append(upsert_table("funding_complementario", _to_records(df), "funding_id"))


def migrate_capital_humano():
    """capital_humano (delete-then-insert, serial PK)"""
    p = CH_DIR / "dataset_maestro_limpio.csv"
    if not p.exists():
        print(f"  [capital_humano] Archivo no encontrado: {p}")
        return
    df = pd.read_csv(p)
    # Eliminar BOM si existe
    df.columns = [c.lstrip('\ufeff') for c in df.columns]

    # Parsear fechas
    for col in ("inicio", "termino"):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce").dt.strftime("%Y-%m-%d")
            df[col] = df[col].where(df[col].notna(), None)

    if "duracion_dias" in df.columns:
        df["duracion_dias"] = pd.to_numeric(df["duracion_dias"], errors="coerce").astype("Int64")
    if "anio_hoja" in df.columns:
        df["anio_hoja"] = pd.to_numeric(df["anio_hoja"], errors="coerce").astype("Int64")

    cols = ["anio_hoja", "nombre", "inicio", "termino", "duracion_dias",
            "tutor", "centro_norm", "tipo_norm", "universidad", "carrera",
            "monto_contrato_num", "ad_honorem", "objeto_contrato",
            "observaciones_texto", "informe_url_principal",
            "flag_fechas_inconsistentes", "flag_tipo_fuera_catalogo"]
    df = df[[c for c in cols if c in df.columns]].dropna(subset=["nombre"])

    # Limpiar tabla antes de insertar (serial PK, sin clave natural única)
    print(f"  [capital_humano] Limpiando tabla antes de re-insertar...", end="", flush=True)
    try:
        supabase.table("capital_humano").delete().neq("id", 0).execute()
        print(" OK")
    except Exception as e:
        print(f"\n  [WARN] No se pudo limpiar capital_humano: {e}")

    records = _to_records(df)
    total   = len(records)
    batches = math.ceil(total / CHUNK_SIZE)
    errors  = 0
    print(f"  [capital_humano] Insertando {total} filas en {batches} batches...", end="", flush=True)
    for i in range(batches):
        chunk = records[i * CHUNK_SIZE: (i + 1) * CHUNK_SIZE]
        try:
            supabase.table("capital_humano").insert(chunk).execute()
            print(".", end="", flush=True)
        except Exception as e:
            errors += 1
            print(f"\n  [WARN] Batch {i+1}/{batches} falló: {e}")
    status = "OK" if errors == 0 else f"{errors} errores"
    print(f" {status}")
    REPORT.append({"table": "capital_humano", "rows": total, "batches": batches, "errors": errors})


def migrate_researchers_orcid():
    """researchers_orcid (PK: orcid_id)"""
    p = RES_DIR / "cchen_researchers_orcid.csv"
    if not p.exists():
        print(f"  [researchers_orcid] Archivo no encontrado: {p}")
        return
    df = pd.read_csv(p)
    cols = ["orcid_id", "orcid_profile_url", "given_name", "family_name",
            "full_name", "employers", "education", "orcid_works_count"]
    df = df[[c for c in cols if c in df.columns]].dropna(subset=["orcid_id"])
    REPORT.append(upsert_table("researchers_orcid", _to_records(df), "orcid_id"))


def migrate_institution_registry():
    """institution_registry (PK lógico: normalized_key)"""
    p = INST_DIR / "cchen_institution_registry.csv"
    if not p.exists():
        print(f"  [institution_registry] Archivo no encontrado: {p}")
        return
    df = pd.read_csv(p)
    cols = [
        "canonical_name", "normalized_key", "ror_id", "openalex_institution_id",
        "organization_type", "city", "country_name", "country_code",
        "website", "grid_id", "isni", "aliases_observed",
        "authorships_count", "orcid_profiles_count", "convenios_count",
        "is_cchen_anchor", "match_status", "source_evidence",
        "ror_record_last_modified",
    ]
    df = df[[c for c in cols if c in df.columns]].dropna(subset=["normalized_key"])
    if "ror_record_last_modified" in df.columns:
        df["ror_record_last_modified"] = pd.to_datetime(
            df["ror_record_last_modified"], errors="coerce"
        ).dt.strftime("%Y-%m-%d")
        df["ror_record_last_modified"] = df["ror_record_last_modified"].where(
            df["ror_record_last_modified"].notna(), None
        )
    REPORT.append(upsert_table("institution_registry", _to_records(df), "normalized_key"))


def migrate_institution_registry_pending_review():
    """institution_registry_pending_review (PK lógico: canonical_name)"""
    p = INST_DIR / "ror_pending_review.csv"
    if not p.exists():
        print(f"  [institution_registry_pending_review] Archivo no encontrado: {p}")
        return
    df = pd.read_csv(p)
    cols = [
        "canonical_name", "authorships_count", "orcid_profiles_count", "convenios_count",
        "signal_total", "source_evidence", "priority_level", "recommended_resolution",
        "api_candidate", "rationale", "aliases_observed",
    ]
    df = df[[c for c in cols if c in df.columns]].dropna(subset=["canonical_name"])
    REPORT.append(upsert_table("institution_registry_pending_review", _to_records(df), "canonical_name"))


def migrate_entity_registry_personas():
    """entity_registry_personas (PK: persona_id)"""
    p = GOV_DIR / "entity_registry_personas.csv"
    if not p.exists():
        print(f"  [entity_registry_personas] Archivo no encontrado: {p}")
        return
    df = _read_csv_flexible(p)
    cols = [
        "persona_id", "canonical_name", "normalized_name", "orcid_id", "author_id",
        "source_anchor", "source_coverage", "is_cchen_investigator",
        "appears_in_capital_humano", "appears_in_orcid", "appears_in_authorships",
        "institution_id", "institution_name", "cchen_publications_count",
        "orcid_works_count", "capital_humano_records", "employers", "education",
        "sensitivity_level",
    ]
    df = df[[c for c in cols if c in df.columns]].dropna(subset=["persona_id"])
    for col in ["cchen_publications_count", "orcid_works_count", "capital_humano_records"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    REPORT.append(upsert_table("entity_registry_personas", _to_records(df), "persona_id"))


def migrate_entity_registry_proyectos():
    """entity_registry_proyectos (PK: project_id)"""
    p = GOV_DIR / "entity_registry_proyectos.csv"
    if not p.exists():
        print(f"  [entity_registry_proyectos] Archivo no encontrado: {p}")
        return
    df = _read_csv_flexible(p)
    cols = [
        "project_id", "proyecto_codigo", "titulo", "anio_concurso", "autor",
        "autor_persona_id", "institucion_id", "institucion_name", "programa",
        "instrumento", "estado", "monto_programa_num", "strategic_profile_id",
        "data_source",
    ]
    df = df[[c for c in cols if c in df.columns]].dropna(subset=["project_id"])
    if "anio_concurso" in df.columns:
        df["anio_concurso"] = pd.to_numeric(df["anio_concurso"], errors="coerce").astype("Int64")
    if "monto_programa_num" in df.columns:
        df["monto_programa_num"] = pd.to_numeric(df["monto_programa_num"], errors="coerce")
    REPORT.append(upsert_table("entity_registry_proyectos", _to_records(df), "project_id"))


def migrate_entity_registry_convocatorias():
    """entity_registry_convocatorias (PK: convocatoria_id)"""
    p = GOV_DIR / "entity_registry_convocatorias.csv"
    if not p.exists():
        print(f"  [entity_registry_convocatorias] Archivo no encontrado: {p}")
        return
    df = _read_csv_flexible(p)
    cols = [
        "convocatoria_id", "titulo", "organismo", "categoria", "estado",
        "perfil_objetivo", "perfil_id", "owner_unit", "relevancia_cchen",
        "es_oficial", "postulable", "apertura_iso", "cierre_iso", "url",
        "last_evaluated_at",
    ]
    df = df[[c for c in cols if c in df.columns]].dropna(subset=["convocatoria_id"])
    for col in ["apertura_iso", "cierre_iso", "last_evaluated_at"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce").dt.strftime("%Y-%m-%d")
            df[col] = df[col].where(df[col].notna(), None)
    REPORT.append(upsert_table("entity_registry_convocatorias", _to_records(df), "convocatoria_id"))


def migrate_entity_links():
    """entity_links (PK compuesto)"""
    p = GOV_DIR / "entity_links.csv"
    if not p.exists():
        print(f"  [entity_links] Archivo no encontrado: {p}")
        return
    df = _read_csv_flexible(p)
    cols = [
        "origin_type", "origin_id", "relation", "target_type", "target_id",
        "source_evidence", "confidence",
    ]
    df = df[[c for c in cols if c in df.columns]].dropna(
        subset=["origin_type", "origin_id", "relation", "target_type", "target_id"]
    )
    REPORT.append(
        upsert_table(
            "entity_links",
            _to_records(df),
            "origin_type,origin_id,relation,target_type,target_id",
        )
    )


def migrate_matching_institucional():
    """convocatorias_matching_institucional (PK compuesto: conv_id, perfil_id)"""
    p = VIG_DIR / "convocatorias_matching_institucional.csv"
    if not p.exists():
        print(f"  [convocatorias_matching_institucional] Archivo no encontrado: {p}")
        return
    df = _read_csv_flexible(p)
    cols = [
        "conv_id", "convocatoria_titulo", "estado", "categoria", "organismo",
        "perfil_objetivo", "perfil_id", "perfil_nombre", "owner_unit",
        "score_total", "score_breakdown", "eligibility_status", "readiness_status",
        "recommended_action", "deadline_class", "evidence_summary", "url",
        "relevancia_cchen", "apertura_iso", "cierre_iso", "match_type",
        "last_evaluated_at",
    ]
    df = df[[c for c in cols if c in df.columns]].dropna(subset=["conv_id", "perfil_id"])
    if "score_total" in df.columns:
        df["score_total"] = pd.to_numeric(df["score_total"], errors="coerce")
    for col in ["apertura_iso", "cierre_iso", "last_evaluated_at"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce").dt.strftime("%Y-%m-%d")
            df[col] = df[col].where(df[col].notna(), None)
    REPORT.append(
        upsert_table(
            "convocatorias_matching_institucional",
            _to_records(df),
            "conv_id,perfil_id",
        )
    )


def migrate_datacite_outputs():
    """datacite_outputs (PK: doi)"""
    p = RO_DIR / "cchen_datacite_outputs.csv"
    if not p.exists():
        print(f"  [datacite_outputs] Archivo no encontrado: {p}")
        return
    df = pd.read_csv(p)
    cols = [
        "doi", "title", "publisher", "publication_year", "resource_type_general",
        "resource_type", "client_id", "url", "created", "updated", "state",
        "version", "rights", "subjects", "creators", "creator_orcids",
        "creator_affiliations", "cchen_affiliated_creators", "has_cchen_ror_affiliation",
        "related_identifiers", "citation_count", "view_count", "download_count",
        "description", "source", "source_filter_ror",
    ]
    df = df[[c for c in cols if c in df.columns]].dropna(subset=["doi"])
    for col in ["publication_year", "cchen_affiliated_creators", "citation_count", "view_count", "download_count"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    for col in ["created", "updated"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce", utc=True).dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            df[col] = df[col].where(df[col].notna(), None)
    REPORT.append(upsert_table("datacite_outputs", _to_records(df), "doi"))


def migrate_openaire_outputs():
    """openaire_outputs (PK: openaire_id)"""
    p = RO_DIR / "cchen_openaire_outputs.csv"
    if not p.exists():
        print(f"  [openaire_outputs] Archivo no encontrado: {p}")
        return
    df = pd.read_csv(p)
    cols = [
        "openaire_id", "main_title", "type", "publication_date", "publisher",
        "best_access_right_label", "open_access_color", "publicly_funded",
        "is_green", "is_in_diamond_journal", "language_code", "language_label",
        "sources", "collected_from", "authors", "organization_names",
        "organization_rors", "has_cchen_ror_org", "has_cchen_name_org",
        "match_scope", "project_codes", "project_acronyms", "project_funders",
        "instance_urls", "instance_types", "hosted_by", "pids",
        "matched_orcids", "matched_researchers", "matched_cchen_researchers_count",
        "query_hits", "source",
    ]
    df = df[[c for c in cols if c in df.columns]].dropna(subset=["openaire_id"])
    if "publication_date" in df.columns:
        df["publication_date"] = pd.to_datetime(df["publication_date"], errors="coerce").dt.strftime("%Y-%m-%d")
        df["publication_date"] = df["publication_date"].where(df["publication_date"].notna(), None)
    for col in ["matched_cchen_researchers_count", "query_hits"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    REPORT.append(upsert_table("openaire_outputs", _to_records(df), "openaire_id"))


def migrate_convenios():
    """convenios_nacionales (delete-then-insert, serial PK)"""
    for fname in ("clean_Convenios_suscritos_por_la_Com.csv",
                  "Convenios_suscritos_por_la_Com.csv"):
        p = INST_DIR / fname
        if not p.exists():
            continue
        try:
            df = pd.read_csv(p, encoding="utf-8", on_bad_lines="skip")
            df.columns = [str(c).strip() for c in df.columns]
            df = df.dropna(how="all")
        except Exception as e:
            print(f"  [convenios_nacionales] Error leyendo {fname}: {e}")
            continue

        # Mapear columnas del CSV al esquema
        col_map = {
            "CONTRAPARTE DEL CONVENIO": "contraparte",
            "Nº RESOLUCIÓN": "n_resolucion",
            "FECHA RESOLUCIÓN": "fecha_resolucion",
            "Nº CONVENIO": "n_convenio",
            "DESCRIPCIÓN": "descripcion",
            "DURACIÓN": "duracion",
            "OTROS ANTECEDENTES": "otros_antecedentes",
        }
        df = df.rename(columns=col_map)
        # Parsear fecha si existe
        if "fecha_resolucion" in df.columns:
            df["fecha_resolucion"] = pd.to_datetime(
                df["fecha_resolucion"], dayfirst=True, errors="coerce"
            ).dt.strftime("%Y-%m-%d")
            df["fecha_resolucion"] = df["fecha_resolucion"].where(
                df["fecha_resolucion"].notna(), None
            )

        keep = [v for v in col_map.values() if v in df.columns]
        df = df[keep].dropna(subset=["contraparte"])

        print(f"  [convenios_nacionales] Limpiando tabla...", end="", flush=True)
        try:
            supabase.table("convenios_nacionales").delete().neq("id", 0).execute()
            print(" OK")
        except Exception as e:
            print(f"\n  [WARN] {e}")

        records = _to_records(df)
        REPORT.append(upsert_table("convenios_nacionales", records, "id"))
        return

    print("  [convenios_nacionales] Archivo no encontrado.")


def migrate_acuerdos():
    """acuerdos_internacionales (delete-then-insert, multi-section CSV)"""
    for fname in ("clean_Acuerdos_e_instrumentos_intern.csv",
                  "Acuerdos_e_instrumentos_intern.csv"):
        p = INST_DIR / fname
        if not p.exists():
            continue
        try:
            raw = pd.read_csv(p, encoding="utf-8", on_bad_lines="skip", header=None)
            rows = []
            current_section = ""
            for _, row in raw.iterrows():
                v0   = str(row.iloc[0]) if pd.notna(row.iloc[0]) else ""
                vals = [str(v).strip() if pd.notna(v) else "" for v in row.values]
                if "TABLA" in v0.upper():
                    current_section = v0.strip()
                    continue
                if v0 == "Nº" or (vals and vals[0] == "Nº"):
                    continue
                if v0.strip().isdigit() and len(vals) >= 2 and vals[1]:
                    rows.append({
                        "seccion":     current_section,
                        "pais":        vals[1],
                        "instrumento": vals[2] if len(vals) > 2 else "",
                        "firma":       vals[3] if len(vals) > 3 else "",
                        "vigencia":    vals[4] if len(vals) > 4 else "",
                    })
        except Exception as e:
            print(f"  [acuerdos_internacionales] Error leyendo {fname}: {e}")
            continue

        if not rows:
            print("  [acuerdos_internacionales] Sin filas parseadas.")
            return

        print(f"  [acuerdos_internacionales] Limpiando tabla...", end="", flush=True)
        try:
            supabase.table("acuerdos_internacionales").delete().neq("id", 0).execute()
            print(" OK")
        except Exception as e:
            print(f"\n  [WARN] {e}")

        REPORT.append(upsert_table("acuerdos_internacionales", rows, "id"))
        return

    print("  [acuerdos_internacionales] Archivo no encontrado.")


# ─── Main ──────────────────────────────────────────────────────────────────────

def main():
    warnings.filterwarnings("ignore")
    start = datetime.datetime.now()
    print("\n" + "=" * 60)
    print("  MIGRACIÓN CCHEN → SUPABASE")
    print(f"  {start.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60 + "\n")

    steps = [
        ("1. publications",             migrate_publications),
        ("2. publications_enriched",    migrate_publications_enriched),
        ("3. authorships",              migrate_authorships),
        ("4. crossref_data",            migrate_crossref),
        ("5. concepts",                 migrate_concepts),
        ("6. patents",                  migrate_patents),
        ("7. anid_projects",            migrate_anid),
        ("8. funding_complementario",   migrate_funding_complementario),
        ("9. capital_humano",           migrate_capital_humano),
        ("10. researchers_orcid",       migrate_researchers_orcid),
        ("11. institution_registry",    migrate_institution_registry),
        ("12. institution_registry_pending_review", migrate_institution_registry_pending_review),
        ("13. entity_registry_personas", migrate_entity_registry_personas),
        ("14. entity_registry_proyectos", migrate_entity_registry_proyectos),
        ("15. entity_registry_convocatorias", migrate_entity_registry_convocatorias),
        ("16. entity_links",            migrate_entity_links),
        ("17. convocatorias_matching_institucional", migrate_matching_institucional),
        ("18. datacite_outputs",        migrate_datacite_outputs),
        ("19. openaire_outputs",        migrate_openaire_outputs),
        ("20. convenios_nacionales",    migrate_convenios),
        ("21. acuerdos_internacionales", migrate_acuerdos),
    ]

    for label, fn in steps:
        print(f"\n── {label}")
        try:
            fn()
        except Exception as e:
            print(f"  [ERROR] {e}")
            REPORT.append({"table": label, "rows": 0, "batches": 0, "errors": 1})

    # ── Reporte final ──────────────────────────────────────────────────────────
    elapsed = (datetime.datetime.now() - start).total_seconds()
    total_rows   = sum(r.get("rows", 0) for r in REPORT)
    total_errors = sum(r.get("errors", 0) for r in REPORT)

    print("\n" + "=" * 60)
    print("  RESUMEN DE MIGRACIÓN")
    print("=" * 60)
    print(f"  {'Tabla':<30} {'Filas':>7}  {'Errores':>7}")
    print(f"  {'-'*30} {'-'*7}  {'-'*7}")
    for r in REPORT:
        tbl  = r.get("table", "?")
        rows = r.get("rows", 0)
        err  = r.get("errors", 0)
        flag = " ⚠" if err else ""
        print(f"  {tbl:<30} {rows:>7}  {err:>7}{flag}")
    print(f"  {'-'*30} {'-'*7}  {'-'*7}")
    print(f"  {'TOTAL':<30} {total_rows:>7}  {total_errors:>7}")
    print(f"\n  Tiempo: {elapsed:.1f}s")
    status_msg = "COMPLETADA SIN ERRORES" if total_errors == 0 else f"COMPLETADA CON {total_errors} ERRORES"
    print(f"  Estado: {status_msg}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
