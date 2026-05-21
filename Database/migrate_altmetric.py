"""
migrate_altmetric.py — Observatorio CCHEN 360°
===============================================
Migra cchen_altmetric.csv → tabla altmetric_scores en Supabase.
PK: doi

Requiere: python3 Scripts/fetch_altmetric.py (genera el CSV)

Uso:
    python3 Database/migrate_altmetric.py
"""
import os
import sys
import math
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

ROOT     = Path(__file__).parent.parent
CSV_PATH = ROOT / "Data" / "Publications" / "cchen_altmetric.csv"

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
    "doi", "altmetric_id", "altmetric_score",
    "altmetric_score_1y", "altmetric_score_3m",
    "cited_by_posts_count", "cited_by_tweeters_count",
    "cited_by_newsoutlets_count", "cited_by_policies_count",
    "cited_by_wikipedia_count", "cited_by_reddits_count",
    "cited_by_feeds_count", "mendeley_readers",
    "is_oa", "subjects", "altmetric_url", "fetched_at",
]

INT_COLS = [
    "cited_by_posts_count", "cited_by_tweeters_count",
    "cited_by_newsoutlets_count", "cited_by_policies_count",
    "cited_by_wikipedia_count", "cited_by_reddits_count",
    "cited_by_feeds_count", "mendeley_readers",
]

FLOAT_COLS = ["altmetric_score", "altmetric_score_1y", "altmetric_score_3m"]


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
        sys.exit(f"[ERROR] {CSV_PATH} no encontrado. Ejecuta primero fetch_altmetric.py")

    df = pd.read_csv(CSV_PATH, dtype=str)
    print(f"[INFO] {len(df)} filas leídas")

    df = df[[c for c in COLS if c in df.columns]]
    df = df.dropna(subset=["doi"]).drop_duplicates(subset=["doi"])

    for c in INT_COLS:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)
    for c in FLOAT_COLS:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    records = [{k: _clean(v) for k, v in row.items()} for row in df.to_dict("records")]
    total   = len(records)
    batches = math.ceil(total / CHUNK)
    errors  = 0

    print(f"[INFO] Subiendo {total} filas en {batches} batches...")
    for i in range(batches):
        chunk = records[i * CHUNK:(i + 1) * CHUNK]
        try:
            sb.table("altmetric_scores").upsert(
                chunk, on_conflict="doi"
            ).execute()
            print(f"  Batch {i+1}/{batches} OK ({len(chunk)})", flush=True)
        except Exception as exc:
            errors += 1
            print(f"  [WARN] Batch {i+1}/{batches} FALLÓ: {exc}", flush=True)

    print(f"\n[{'OK' if errors == 0 else 'WARN'}] {total} filas, {errors} errores.")
    return errors


if __name__ == "__main__":
    sys.exit(0 if migrate() == 0 else 1)
