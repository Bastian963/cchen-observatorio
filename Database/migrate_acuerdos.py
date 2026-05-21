"""
migrate_acuerdos.py — Observatorio CCHEN 360°
===============================================
Parsea clean_Acuerdos_e_instrumentos_intern.csv (multi-sección) y sube
a la tabla acuerdos_internacionales en Supabase.
PK: id = f"{seccion_code}_{numero}"
"""
import os, sys, math
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv

ROOT     = Path(__file__).parent.parent
CSV_PATH = ROOT / "Data" / "Institutional" / "clean_Acuerdos_e_instrumentos_intern.csv"

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
    s = str(v).strip()
    return s if s and s.lower() != "nan" else None

def _str(v):
    if v is None: return None
    s = str(v).strip()
    return s if s and s.lower() not in ("nan", "") else None

def _parse_acuerdos(path: Path) -> list[dict]:
    raw = pd.read_csv(path, header=None, dtype=str)
    raw = raw.fillna("")

    # Detect section boundaries: rows where col 0 starts with "TABLA" or known headers
    records = []
    seq_id = 1  # id INTEGER secuencial para upsert idempotente

    sections = [
        ("Acuerdos bilaterales Latinoamérica",      4, 11,  ["_skip","pais","instrumento","firma","vigencia"]),
        ("Acuerdos con Organismos Internacionales", 15, 22, ["_skip","instrumento","firma","vigencia",None]),
        ("Acuerdos bilaterales otros países",       26, 36, ["_skip","instrumento","firma","vigencia",None]),
        ("Instrumentos internacionales nucleares",  40, 55, ["_skip","instrumento","firma","_skip","vigencia"]),
        ("Acuerdos multilaterales IAEA",            69, 85, ["_skip","instrumento","vigencia","_skip",None]),
        ("Acuerdos de salvaguardias IAEA",          90, 92, ["_skip","instrumento","vigencia","_skip",None]),
    ]

    for seccion, row_start, row_end, col_map in sections:
        for idx in range(row_start, min(row_end, len(raw))):
            row = raw.iloc[idx]
            vals = [_str(row[i]) for i in range(5)]
            if not vals[0] or not str(vals[0]).strip():
                continue
            rec = {"id": seq_id, "seccion": seccion, "pais": None,
                   "instrumento": None, "firma": None, "vigencia": None}
            for i, field in enumerate(col_map):
                if field and field != "_skip" and i < len(vals):
                    rec[field] = vals[i]
            records.append(rec)
            seq_id += 1

    return records


def migrate():
    if not CSV_PATH.exists():
        sys.exit(f"[ERROR] {CSV_PATH} no encontrado")

    records = _parse_acuerdos(CSV_PATH)
    # deduplicate on id
    seen = set(); unique = []
    for r in records:
        if r["id"] not in seen:
            seen.add(r["id"]); unique.append(r)
    records = unique

    total = len(records); batches = math.ceil(total / CHUNK); errors = 0
    print(f"[INFO] {total} acuerdos parseados en {batches} batches...")

    for i in range(batches):
        chunk = records[i*CHUNK:(i+1)*CHUNK]
        try:
            sb.table("acuerdos_internacionales").upsert(chunk, on_conflict="id").execute()
            print(f"  Batch {i+1}/{batches} OK ({len(chunk)})", flush=True)
        except Exception as e:
            errors += 1
            print(f"  [WARN] Batch {i+1}/{batches} FALLÓ: {e}", flush=True)

    print(f"\n[{'OK' if errors==0 else 'WARN'}] {total} filas, {errors} errores.")
    return errors

if __name__ == "__main__":
    sys.exit(0 if migrate() == 0 else 1)
