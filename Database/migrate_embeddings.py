"""
migrate_embeddings.py — Observatorio CCHEN 360°
===============================================
Sube los embeddings semánticos (877×384 float32) a Supabase pgvector.

USO:
    cd /Users/bastianayalainostroza/Dropbox/CCHEN
    PYTHONUNBUFFERED=1 python3 -u Database/migrate_embeddings.py
"""

import os
import sys
import math
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv

ROOT     = Path(__file__).parent.parent
EMB_FILE = ROOT / "Data" / "Publications" / "cchen_embeddings.npy"
META_FILE= ROOT / "Data" / "Publications" / "cchen_embeddings_meta.csv"

load_dotenv(ROOT / "Database" / ".env")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    sys.exit("[ERROR] Faltan credenciales en Database/.env")

try:
    from supabase import create_client, Client
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print(f"[OK] Conectado a Supabase: {SUPABASE_URL}")
except Exception as e:
    sys.exit(f"[ERROR] {e}")

CHUNK_SIZE = 50   # vectors son grandes, batches pequeños


def _clean(val):
    if val is None:
        return None
    if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
        return None
    try:
        if pd.isna(val):
            return None
    except (TypeError, ValueError):
        pass
    if hasattr(val, 'item'):
        return val.item()
    return val


if __name__ == "__main__":
    if not EMB_FILE.exists() or not META_FILE.exists():
        sys.exit(f"[ERROR] No encontrado: {EMB_FILE} o {META_FILE}")

    print(f"[INFO] Cargando embeddings...")
    emb  = np.load(EMB_FILE)          # (877, 384) float32
    meta = pd.read_csv(META_FILE).fillna("")

    assert len(emb) == len(meta), "Mismatch entre embeddings y metadata"
    print(f"[INFO] {len(emb)} embeddings × {emb.shape[1]} dims")

    records = []
    for i, row in meta.iterrows():
        records.append({
            "openalex_id": str(row["openalex_id"]),
            "doi":         _clean(row.get("doi", "")),
            "title":       _clean(row.get("title", "")),
            "year":        _clean(pd.to_numeric(row.get("year"), errors="coerce")),
            "embedding":   emb[i].astype(float).tolist(),  # list[float] → pgvector
        })

    total   = len(records)
    batches = math.ceil(total / CHUNK_SIZE)
    errors  = 0

    print(f"[INFO] Subiendo {total} filas en {batches} batches (tamaño {CHUNK_SIZE})...")
    for i in range(batches):
        chunk = records[i * CHUNK_SIZE: (i + 1) * CHUNK_SIZE]
        try:
            supabase.table("paper_embeddings").upsert(
                chunk, on_conflict="openalex_id"
            ).execute()
            print(f"  Batch {i+1}/{batches} OK ({len(chunk)} filas)", flush=True)
        except Exception as e:
            errors += 1
            print(f"  [WARN] Batch {i+1}/{batches} FALLÓ: {e}", flush=True)

    print()
    if errors == 0:
        print(f"[OK] Migración completada: {total} embeddings, 0 errores.")
    else:
        print(f"[WARN] {total} intentados, {errors} batches con error.")
    sys.exit(0 if errors == 0 else 1)
