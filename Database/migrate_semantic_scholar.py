"""
migrate_semantic_scholar.py — Observatorio CCHEN 360°
======================================================
Migra cchen_semantic_scholar.csv → tabla semantic_scholar_papers en Supabase.
PK: openalex_id

Requiere: python3 Scripts/fetch_semantic_scholar.py (genera el CSV)

Uso:
    python3 Database/migrate_semantic_scholar.py
"""
import os
import sys
import math
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

ROOT     = Path(__file__).parent.parent
CSV_PATH = ROOT / "Data" / "Publications" / "cchen_semantic_scholar.csv"

load_dotenv(ROOT / "Database" / ".env")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
if not SUPABASE_URL or not SUPABASE_KEY:
    sys.exit("[ERROR] Faltan credenciales en Database/.env")

try:
    from supabase import create_client
    sb = create_client(SUPABASE_URL, SUPABASE_KEY)
    print(f"[OK] Conectado: {SUPABASE_URL}")
except Exception as e:
    sys.exit(f"[ERROR] Conexión: {e}")

CHUNK = 100

COLS = [
    "openalex_id", "doi", "ss_paper_id", "title", "year",
    "abstract", "tldr", "citation_count", "is_oa", "fields_of_study",
]


def _clean(v):
    if v is None:
        return None
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None
    if isinstance(v, bool):
        return bool(v)
    try:
        if pd.isna(v):
            return None
    except Exception:
        pass
    return v.item() if hasattr(v, "item") else v


def migrate() -> int:
    if not CSV_PATH.exists():
        sys.exit(f"[ERROR] {CSV_PATH} no encontrado. Ejecuta primero fetch_semantic_scholar.py")

    df = pd.read_csv(CSV_PATH, dtype=str)
    print(f"[INFO] {len(df)} filas leídas")

    df = df[[c for c in COLS if c in df.columns]]
    df = df.dropna(subset=["openalex_id"]).drop_duplicates(subset=["openalex_id"])

    for c in ("citation_count",):
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)
    if "year" in df.columns:
        df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
    if "is_oa" in df.columns:
        df["is_oa"] = df["is_oa"].map(
            lambda x: True if str(x).lower() in ("true", "1", "yes")
            else (False if str(x).lower() in ("false", "0", "no") else None)
        )

    records = [{k: _clean(v) for k, v in row.items()} for row in df.to_dict("records")]
    total   = len(records)
    batches = math.ceil(total / CHUNK)
    errors  = 0

    print(f"[INFO] Subiendo {total} filas en {batches} batches...")
    for i in range(batches):
        chunk = records[i * CHUNK:(i + 1) * CHUNK]
        try:
            sb.table("semantic_scholar_papers").upsert(
                chunk, on_conflict="openalex_id"
            ).execute()
            print(f"  Batch {i+1}/{batches} OK ({len(chunk)})", flush=True)
        except Exception as exc:
            errors += 1
            print(f"  [WARN] Batch {i+1}/{batches} FALLÓ: {exc}", flush=True)

    print(f"\n[{'OK' if errors == 0 else 'WARN'}] {total} filas, {errors} errores.")
    return errors


if __name__ == "__main__":
    sys.exit(0 if migrate() == 0 else 1)
