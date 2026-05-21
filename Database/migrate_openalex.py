"""
migrate_openalex.py — Observatorio CCHEN 360°
===============================================
Migra cchen_openalex_works.csv → tabla openalex_publicaciones en Supabase.
PK: openalex_id
"""
import os, sys, math
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv

ROOT     = Path(__file__).parent.parent
CSV_PATH = ROOT / "Data" / "Publications" / "cchen_openalex_works.csv"

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

    COLS = ["openalex_id","doi","title","year","type","source",
            "cited_by_count","is_oa","oa_status","oa_url","pmid","pmcid","europmc_url"]
    df = df[[c for c in COLS if c in df.columns]]
    df = df.dropna(subset=["openalex_id"]).drop_duplicates(subset=["openalex_id"])

    if "year"           in df.columns: df["year"]           = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
    if "cited_by_count" in df.columns: df["cited_by_count"] = pd.to_numeric(df["cited_by_count"], errors="coerce").fillna(0).astype(int)
    if "is_oa"          in df.columns: df["is_oa"]          = df["is_oa"].map(lambda x: True if str(x).lower() in ("true","1","yes") else (False if str(x).lower() in ("false","0","no") else None))
    # pmid/pmcid pueden ser float (NaN) → str limpio
    for c in ("pmid","pmcid","europmc_url"):
        if c in df.columns: df[c] = df[c].apply(lambda x: None if (isinstance(x,float) and math.isnan(x)) else (str(x) if x is not None else None))

    records = [{k: _clean(v) for k,v in row.items()} for row in df.to_dict("records")]
    total = len(records); batches = math.ceil(total/CHUNK); errors = 0

    print(f"[INFO] Subiendo {total} filas en {batches} batches...")
    for i in range(batches):
        chunk = records[i*CHUNK:(i+1)*CHUNK]
        try:
            sb.table("openalex_publicaciones").upsert(chunk, on_conflict="openalex_id").execute()
            print(f"  Batch {i+1}/{batches} OK ({len(chunk)})", flush=True)
        except Exception as e:
            errors += 1
            print(f"  [WARN] Batch {i+1}/{batches} FALLÓ: {e}", flush=True)

    print(f"\n[{'OK' if errors==0 else 'WARN'}] {total} filas, {errors} errores.")
    return errors

if __name__ == "__main__":
    sys.exit(0 if migrate() == 0 else 1)
