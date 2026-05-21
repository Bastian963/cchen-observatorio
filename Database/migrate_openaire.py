"""
migrate_openaire.py — Observatorio CCHEN 360°
==============================================
Migra cchen_openaire_outputs.csv → tabla openaire_outputs en Supabase.
PK: openaire_id
"""
import os, sys, math
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv

ROOT     = Path(__file__).parent.parent
CSV_PATH = ROOT / "Data" / "ResearchOutputs" / "cchen_openaire_outputs.csv"

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

def _clean(v):
    if v is None: return None
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)): return None
    if isinstance(v, bool): return bool(v)
    try:
        if pd.isna(v): return None
    except: pass
    return v.item() if hasattr(v, "item") else v

def migrate():
    if not CSV_PATH.exists():
        sys.exit(f"[ERROR] {CSV_PATH} no encontrado")
    df = pd.read_csv(CSV_PATH)
    print(f"[INFO] {len(df)} filas leídas")

    df = df[[c for c in COLS if c in df.columns]]
    df = df.dropna(subset=["openaire_id"]).drop_duplicates(subset=["openaire_id"])

    for c in ("matched_cchen_researchers_count", "query_hits"):
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)
    for c in ("publicly_funded", "is_green", "is_in_diamond_journal",
              "has_cchen_ror_org", "has_cchen_name_org"):
        if c in df.columns:
            df[c] = df[c].map(lambda x: True if str(x).lower() in ("true","1","yes") else
                              (False if str(x).lower() in ("false","0","no") else None))

    records = [{k: _clean(v) for k,v in row.items()} for row in df.to_dict("records")]
    total = len(records); batches = math.ceil(total/CHUNK); errors = 0

    print(f"[INFO] Subiendo {total} filas en {batches} batches...")
    for i in range(batches):
        chunk = records[i*CHUNK:(i+1)*CHUNK]
        try:
            sb.table("openaire_outputs").upsert(chunk, on_conflict="openaire_id").execute()
            print(f"  Batch {i+1}/{batches} OK ({len(chunk)})", flush=True)
        except Exception as e:
            errors += 1
            print(f"  [WARN] Batch {i+1}/{batches} FALLÓ: {e}", flush=True)

    print(f"\n[{'OK' if errors==0 else 'WARN'}] {total} filas, {errors} errores.")
    return errors

if __name__ == "__main__":
    sys.exit(0 if migrate() == 0 else 1)
