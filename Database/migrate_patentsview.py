"""
migrate_patentsview.py — Observatorio CCHEN 360°
=================================================
Migra cchen_patents_uspto.csv → tabla patents en Supabase.
PK: patent_id

Requiere:
    export PATENTSVIEW_API_KEY="..."
    python3 Scripts/fetch_patentsview_patents.py

Uso:
    python3 Database/migrate_patentsview.py
"""
import os
import sys
import math
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

ROOT     = Path(__file__).parent.parent
CSV_PATH = ROOT / "Data" / "Patents" / "cchen_patents_uspto.csv"

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
    "patent_id", "title", "patent_date", "grant_year",
    "cited_by_count", "assignees", "assignee_countries",
    "inventors", "inventor_countries", "n_inventors_cl",
    "ipc_symbols", "source", "query_org", "patent_url",
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
        sys.exit(f"[ERROR] {CSV_PATH} no encontrado. Ejecuta primero fetch_patentsview_patents.py")

    df = pd.read_csv(CSV_PATH, dtype=str)
    print(f"[INFO] {len(df)} filas leídas")

    df = df[[c for c in COLS if c in df.columns]]
    df = df.dropna(subset=["patent_id"]).drop_duplicates(subset=["patent_id"])

    for c in ("cited_by_count", "n_inventors_cl"):
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)
    if "grant_year" in df.columns:
        df["grant_year"] = pd.to_numeric(df["grant_year"], errors="coerce").astype("Int64")

    records = [{k: _clean(v) for k, v in row.items()} for row in df.to_dict("records")]
    total   = len(records)
    batches = math.ceil(total / CHUNK)
    errors  = 0

    print(f"[INFO] Subiendo {total} filas en {batches} batches...")
    for i in range(batches):
        chunk = records[i * CHUNK:(i + 1) * CHUNK]
        try:
            sb.table("patents").upsert(
                chunk, on_conflict="patent_id"
            ).execute()
            print(f"  Batch {i+1}/{batches} OK ({len(chunk)})", flush=True)
        except Exception as exc:
            errors += 1
            print(f"  [WARN] Batch {i+1}/{batches} FALLÓ: {exc}", flush=True)

    print(f"\n[{'OK' if errors == 0 else 'WARN'}] {total} filas, {errors} errores.")
    return errors


if __name__ == "__main__":
    sys.exit(0 if migrate() == 0 else 1)
