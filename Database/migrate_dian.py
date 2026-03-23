#!/usr/bin/env python3
"""
migrate_dian.py — Migra Publicaciones DIAN.xlsx → Supabase (tabla dian_publications)
=====================================================================================
Uso:
    python3 Database/migrate_dian.py
"""
from __future__ import annotations
import os, sys
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv

ROOT    = Path(__file__).resolve().parents[1]
EXCEL   = ROOT / "Data" / "Publicaciones DIAN CCHEN" / "Publicaciones DIAN.xlsx"

load_dotenv(ROOT / "Database" / ".env")
load_dotenv(ROOT / ".env")

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

if not SUPABASE_URL or not SUPABASE_KEY:
    sys.exit("[ERROR] Define SUPABASE_URL y SUPABASE_KEY como variables de entorno")
if not EXCEL.exists():
    sys.exit(f"[ERROR] No se encontró: {EXCEL}")

from supabase import create_client
client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ── Cargar y limpiar ────────────────────────────────────────────────────────────
df = pd.read_excel(EXCEL, sheet_name="Consolidado", header=0, engine="openpyxl")
df = df.dropna(how="all").dropna(axis=1, how="all")
df.columns = [str(c).strip() for c in df.columns]

col_map = {
    "N°":                    "numero",
    "Unidad":                "unidad",
    "Nombre del Artículo":   "titulo",
    "Autores":               "autores",
    "Revista":               "revista",
    "Fecha de envío":        "fecha_envio",
    "Fecha de Aceptación":   "fecha_aceptacion",
    "Fecha de publicación":  "fecha_publicacion",
    "DOI":                   "doi",
    "Cuartil":               "cuartil",
    "Participación DRTeC":   "participacion_drtec",
    "Año de aceptación":     "anio",
}
df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

# Mantener solo columnas del esquema
keep = [c for c in col_map.values() if c in df.columns]
df = df[keep].copy()

# Normalizar cuartil → Q1-Q4
if "cuartil" in df.columns:
    df["cuartil"] = df["cuartil"].astype(str).str.extract(r"(Q[1-4])", expand=False)

# Normalizar año
if "anio" in df.columns:
    df["anio"] = pd.to_numeric(df["anio"], errors="coerce").astype("Int64")

# Normalizar fechas → ISO string o None
for dcol in ("fecha_envio", "fecha_aceptacion", "fecha_publicacion"):
    if dcol in df.columns:
        df[dcol] = pd.to_datetime(df[dcol], errors="coerce").dt.strftime("%Y-%m-%d")
        df[dcol] = df[dcol].where(df[dcol].notna(), other=None)

# Filtrar sin título
df = df[df["titulo"].notna() & (df["titulo"].str.strip() != "")]

# Convertir Int64 → native int / None para JSON
df["anio"] = df["anio"].apply(lambda x: int(x) if pd.notna(x) else None)
if "numero" in df.columns:
    df["numero"] = pd.to_numeric(df["numero"], errors="coerce")
    df["numero"] = df["numero"].apply(lambda x: int(x) if pd.notna(x) else None)

records = df.where(df.notna(), other=None).to_dict(orient="records")
print(f"[INFO] {len(records)} registros DIAN a migrar.")

# ── Truncate + Insert (idempotente) ─────────────────────────────────────────────
print("[INFO] Limpiando tabla dian_publications...")
client.table("dian_publications").delete().neq("dian_id", 0).execute()

BATCH = 50
errors = 0
for i in range(0, len(records), BATCH):
    batch = records[i:i + BATCH]
    try:
        client.table("dian_publications").insert(batch).execute()
        print(f"  Batch {i // BATCH + 1}/{(len(records) - 1) // BATCH + 1} OK ({len(batch)} filas)")
    except Exception as e:
        print(f"  [ERROR] Batch {i // BATCH + 1}: {e}")
        errors += 1

print(f"\n[OK] Migración completada: {len(records)} registros DIAN, {errors} errores.")
