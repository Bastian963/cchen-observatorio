"""
migrate_vigilancia.py — Observatorio CCHEN 360°
===============================================
Migra los datos de vigilancia tecnológica y grafo de citas a Supabase.

Tablas:
  - citation_graph      ← Data/Publications/cchen_citation_graph.csv
  - arxiv_monitor       ← Data/Vigilancia/arxiv_monitor.csv
  - iaea_inis_monitor   ← Data/Vigilancia/iaea_inis_monitor.csv
  - news_monitor        ← Data/Vigilancia/news_monitor.csv

USO:
    cd /Users/bastianayalainostroza/Dropbox/CCHEN
    PYTHONUNBUFFERED=1 python3 -u Database/migrate_vigilancia.py
"""

import os
import sys
import math
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

ROOT = Path(__file__).parent.parent

load_dotenv(ROOT / "Database" / ".env")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    sys.exit("[ERROR] Faltan credenciales en Database/.env")

try:
    from supabase import create_client, Client
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print(f"[OK] Conectado a Supabase: {SUPABASE_URL}")
except ImportError:
    sys.exit("[ERROR] pip install supabase")
except Exception as e:
    sys.exit(f"[ERROR] {e}")

CHUNK_SIZE = 200


def _clean(val):
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
    return [{k: _clean(v) for k, v in row.items()} for row in df.to_dict(orient="records")]


def _migrate(table: str, csv_path: Path, pk: str, cols: list[str],
             int_cols: list[str] = None):
    print(f"\n── {table} ──")
    if not csv_path.exists():
        print(f"  [SKIP] No encontrado: {csv_path}")
        return

    df = pd.read_csv(csv_path, low_memory=False)
    print(f"  Leídas: {len(df)} filas")

    df = df[[c for c in cols if c in df.columns]]
    df = df.dropna(subset=[pk]).drop_duplicates(subset=[pk])

    for col in (int_cols or []):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

    records = _to_records(df)
    total   = len(records)
    batches = math.ceil(total / CHUNK_SIZE)
    errors  = 0

    print(f"  Subiendo {total} filas en {batches} batches...")
    for i in range(batches):
        chunk = records[i * CHUNK_SIZE: (i + 1) * CHUNK_SIZE]
        try:
            supabase.table(table).upsert(chunk, on_conflict=pk).execute()
            print(f"    Batch {i+1}/{batches} OK ({len(chunk)} filas)", flush=True)
        except Exception as e:
            errors += 1
            print(f"    [WARN] Batch {i+1}/{batches} FALLÓ: {e}", flush=True)

    status = "OK" if errors == 0 else f"WARN ({errors} errores)"
    print(f"  [{status}] {total} filas migradas.")
    return errors


if __name__ == "__main__":
    total_errors = 0

    total_errors += _migrate(
        table    = "citation_graph",
        csv_path = ROOT / "Data" / "Publications" / "cchen_citation_graph.csv",
        pk       = "openalex_id",
        cols     = ["openalex_id", "doi", "year", "cited_by_count",
                    "referenced_works_count", "referenced_ids_sample", "fetched_at"],
        int_cols = ["cited_by_count", "referenced_works_count"],
    ) or 0

    total_errors += _migrate(
        table    = "arxiv_monitor",
        csv_path = ROOT / "Data" / "Vigilancia" / "arxiv_monitor.csv",
        pk       = "arxiv_id",
        cols     = ["arxiv_id", "title", "authors", "abstract_short",
                    "link", "published", "feed_area", "relevance_flag",
                    "keywords_found", "fetched_at"],
    ) or 0

    total_errors += _migrate(
        table    = "iaea_inis_monitor",
        csv_path = ROOT / "Data" / "Vigilancia" / "iaea_inis_monitor.csv",
        pk       = "inis_id",
        cols     = ["inis_id", "title", "authors", "abstract_short",
                    "link", "published", "subject_area", "relevance_flag",
                    "keywords_found", "source_type", "fetched_at"],
    ) or 0

    total_errors += _migrate(
        table    = "news_monitor",
        csv_path = ROOT / "Data" / "Vigilancia" / "news_monitor.csv",
        pk       = "news_id",
        cols     = ["news_id", "title", "source_name", "link", "published",
                    "snippet", "query_label", "topic_flag", "fetched_at"],
    ) or 0

    print(f"\n{'[OK] Migración completa.' if total_errors == 0 else f'[WARN] {total_errors} errores en total.'}")
    sys.exit(0 if total_errors == 0 else 1)
