"""
migrate_europmc.py — Observatorio CCHEN 360°
============================================
Migra cchen_europmc_works.csv a la tabla europmc_works en Supabase.

Tabla destino (debe existir en Supabase):
    CREATE TABLE IF NOT EXISTS europmc_works (
      source_id         TEXT PRIMARY KEY,
      doi               TEXT,
      pmid              TEXT,
      pmcid             TEXT,
      title             TEXT,
      authors           TEXT,
      journal           TEXT,
      year              INTEGER,
      pub_date          TEXT,
      cited_by_count    INTEGER DEFAULT 0,
      is_open_access    TEXT,
      abstract_available TEXT,
      source            TEXT,
      keywords          TEXT,
      affiliation_raw   TEXT,
      europmc_url       TEXT,
      fetched_at        TEXT
    );

USO:
    cd /Users/bastianayalainostroza/Dropbox/CCHEN
    PYTHONUNBUFFERED=1 python3 -u Database/migrate_europmc.py
"""

import os
import sys
import math
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

# ─── Rutas ─────────────────────────────────────────────────────────────────────

ROOT     = Path(__file__).parent.parent          # /CCHEN/
CSV_PATH = ROOT / "Data" / "Publications" / "cchen_europmc_works.csv"

# ─── Credenciales ──────────────────────────────────────────────────────────────

load_dotenv(ROOT / "Database" / ".env")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    sys.exit(
        "\n[ERROR] Faltan credenciales.\n"
        "Crea el archivo Database/.env con:\n"
        "  SUPABASE_URL=https://xxxx.supabase.co\n"
        "  SUPABASE_KEY=eyJ...\n"
    )

# ─── Conexión ──────────────────────────────────────────────────────────────────

try:
    from supabase import create_client, Client
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print(f"[OK] Conectado a Supabase: {SUPABASE_URL}")
except ImportError:
    sys.exit("[ERROR] Instala la librería: pip install supabase")
except Exception as e:
    sys.exit(f"[ERROR] No se pudo conectar a Supabase: {e}")

# ─── Constantes ────────────────────────────────────────────────────────────────

CHUNK_SIZE = 100   # tabla pequeña; chunks menores para mayor robustez


def _clean(val):
    """Convierte NaN/NaT/inf a None para que Supabase los acepte como NULL."""
    if val is None:
        return None
    if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
        return None
    if isinstance(val, bool):
        return bool(val)
    try:
        if pd.isna(val):
            return None
    except (TypeError, ValueError):
        pass
    if hasattr(val, 'item'):
        return val.item()
    return val


def _to_records(df: pd.DataFrame) -> list[dict]:
    """Convierte un DataFrame a lista de dicts limpios para Supabase."""
    records = []
    for row in df.to_dict(orient="records"):
        records.append({k: _clean(v) for k, v in row.items()})
    return records


def migrate_europmc():
    """europmc_works (PK: source_id)"""
    if not CSV_PATH.exists():
        sys.exit(f"[ERROR] Archivo no encontrado: {CSV_PATH}")

    print(f"[INFO] Leyendo {CSV_PATH} ...")
    df = pd.read_csv(CSV_PATH)
    print(f"[INFO] Filas leídas: {len(df)}")

    cols = [
        "source_id", "doi", "pmid", "pmcid", "title", "authors",
        "journal", "year", "pub_date", "cited_by_count",
        "is_open_access", "abstract_available", "source",
        "keywords", "affiliation_raw", "europmc_url", "fetched_at",
    ]
    df = df[[c for c in cols if c in df.columns]]
    df = df.dropna(subset=["source_id"])
    df = df.drop_duplicates(subset=["source_id"])

    # Tipos numéricos
    if "year" in df.columns:
        df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
    if "cited_by_count" in df.columns:
        df["cited_by_count"] = pd.to_numeric(df["cited_by_count"], errors="coerce").fillna(0).astype(int)

    records = _to_records(df)
    total   = len(records)
    batches = math.ceil(total / CHUNK_SIZE)
    errors  = 0

    print(f"[INFO] Subiendo {total} filas en {batches} batches (tamaño {CHUNK_SIZE})...")

    for i in range(batches):
        chunk = records[i * CHUNK_SIZE: (i + 1) * CHUNK_SIZE]
        try:
            supabase.table("europmc_works").upsert(
                chunk, on_conflict="source_id"
            ).execute()
            print(f"  Batch {i + 1}/{batches} OK ({len(chunk)} filas)", flush=True)
        except Exception as e:
            errors += 1
            print(f"  [WARN] Batch {i + 1}/{batches} FALLÓ: {e}", flush=True)

    print()
    if errors == 0:
        print(f"[OK] Migración completada: {total} filas, 0 errores.")
    else:
        print(f"[WARN] Migración completada: {total} filas intentadas, {errors} batches con error.")

    return {"table": "europmc_works", "rows": total, "batches": batches, "errors": errors}


if __name__ == "__main__":
    result = migrate_europmc()
    sys.exit(0 if result["errors"] == 0 else 1)
