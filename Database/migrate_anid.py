"""
migrate_anid.py — Observatorio CCHEN 360°
==========================================
Migra RepositorioAnid_con_monto.csv → tabla anid_projects en Supabase.
PK: proyecto (folio ANID, integer)
Solo se sube el subconjunto de columnas relevantes para el observatorio.
"""
import os, sys, math
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv

ROOT     = Path(__file__).parent.parent
CSV_PATH = ROOT / "Data" / "ANID" / "RepositorioAnid_con_monto.csv"

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

# Columnas del CSV original → nombre en tabla Supabase
# Mapeado a las columnas que realmente existen en la tabla anid_projects:
# proyecto, titulo, resumen, autor, institucion, programa, instrumento,
# estado, estado_full, anio_concurso, monto_programa_num, link, oecd_area
COL_MAP = {
    "proyecto":           "proyecto",
    "titulo":             "titulo",
    "resumen":            "resumen",
    "autor":              "autor",
    "institucion":        "institucion",
    "programa":           "programa",
    "instrumento":        "instrumento",
    "estado":             "estado",
    "estado_full":        "estado_full",
    "anio_concurso_full": "anio_concurso",
    "monto_programa_num": "monto_programa_num",
    "link":               "link",
    "dc.subject.oecd1n":  "oecd_area",
}

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
    df = pd.read_csv(CSV_PATH, low_memory=False)
    print(f"[INFO] {len(df)} filas leídas")

    # Select and rename available columns
    available = {orig: dest for orig, dest in COL_MAP.items() if orig in df.columns}
    df = df[list(available.keys())].rename(columns=available)
    df = df.dropna(subset=["proyecto"]).drop_duplicates(subset=["proyecto"])

    df["proyecto"] = pd.to_numeric(df["proyecto"], errors="coerce")
    df = df.dropna(subset=["proyecto"])  # elimina filas donde proyecto no es numérico
    df["proyecto"] = df["proyecto"].astype("Int64")
    if "anio_concurso" in df.columns:
        df["anio_concurso"] = pd.to_numeric(df["anio_concurso"], errors="coerce").astype("Int64")
    if "monto_programa_num" in df.columns:
        df["monto_programa_num"] = pd.to_numeric(df["monto_programa_num"], errors="coerce").astype("Int64")

    records = [{k: _clean(v) for k,v in row.items()} for row in df.to_dict("records")]
    total = len(records); batches = math.ceil(total/CHUNK); errors = 0

    print(f"[INFO] Subiendo {total} filas en {batches} batches...")
    for i in range(batches):
        chunk = records[i*CHUNK:(i+1)*CHUNK]
        try:
            sb.table("anid_projects").upsert(chunk, on_conflict="proyecto").execute()
            print(f"  Batch {i+1}/{batches} OK ({len(chunk)})", flush=True)
        except Exception as e:
            errors += 1
            print(f"  [WARN] Batch {i+1}/{batches} FALLÓ: {e}", flush=True)

    print(f"\n[{'OK' if errors==0 else 'WARN'}] {total} filas, {errors} errores.")
    return errors

if __name__ == "__main__":
    sys.exit(0 if migrate() == 0 else 1)
