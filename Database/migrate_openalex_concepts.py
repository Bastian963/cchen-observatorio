"""
migrate_openalex_concepts.py — Observatorio CCHEN 360°
=======================================================
Migra cchen_openalex_concepts.csv → tabla openalex_conceptos en Supabase.
PK compuesta: (work_id, concept_name)
"""
import os, sys, math
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv

ROOT     = Path(__file__).parent.parent
CSV_PATH = ROOT / "Data" / "Publications" / "cchen_openalex_concepts.csv"

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

CHUNK = 200  # tabla grande: batches más grandes

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

    COLS = ["work_id","concept_name","concept_level","concept_score","source"]
    df = df[[c for c in COLS if c in df.columns]]
    df = df.dropna(subset=["work_id","concept_name"])
    df = df.drop_duplicates(subset=["work_id","concept_name"])

    if "concept_level" in df.columns:
        df["concept_level"] = pd.to_numeric(df["concept_level"], errors="coerce").astype("Int64")
    if "concept_score" in df.columns:
        df["concept_score"] = pd.to_numeric(df["concept_score"], errors="coerce")

    records = [{k: _clean(v) for k,v in row.items()} for row in df.to_dict("records")]
    total = len(records); batches = math.ceil(total/CHUNK); errors = 0

    print(f"[INFO] Subiendo {total} filas en {batches} batches...")
    for i in range(batches):
        chunk = records[i*CHUNK:(i+1)*CHUNK]
        try:
            sb.table("openalex_conceptos").upsert(chunk, on_conflict="work_id,concept_name").execute()
            print(f"  Batch {i+1}/{batches} OK ({len(chunk)})", flush=True)
        except Exception as e:
            errors += 1
            print(f"  [WARN] Batch {i+1}/{batches} FALLÓ: {e}", flush=True)

    print(f"\n[{'OK' if errors==0 else 'WARN'}] {total} filas, {errors} errores.")
    return errors

if __name__ == "__main__":
    sys.exit(0 if migrate() == 0 else 1)
