"""
migrate_convocatorias.py — Observatorio CCHEN 360°
==================================================
Migra convocatorias curadas y reglas de matching a Supabase.

USO:
    cd /Users/bastianayalainostroza/Dropbox/CCHEN
    PYTHONUNBUFFERED=1 python3 -u Database/migrate_convocatorias.py
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
except Exception as e:
    sys.exit(f"[ERROR] {e}")


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


def _to_records(df):
    return [{k: _clean(v) for k, v in row.items()} for row in df.to_dict(orient="records")]


def _migrate(table, csv_path, pk, cols):
    print(f"\n── {table} ──")
    if not csv_path.exists():
        print(f"  [SKIP] No encontrado: {csv_path}")
        return 0

    df = pd.read_csv(csv_path, low_memory=False)
    print(f"  Leídas: {len(df)} filas")
    df = df[[c for c in cols if c in df.columns]]

    # pk puede ser "col1" o "col1,col2" (PK compuesta)
    pk_cols = [c.strip() for c in pk.split(",")]
    df = df.dropna(subset=pk_cols).drop_duplicates(subset=pk_cols)

    # Convertir booleanos a string para evitar conflictos de tipo
    for col in df.select_dtypes(include=["bool"]).columns:
        df[col] = df[col].astype(str)

    records = _to_records(df)
    try:
        supabase.table(table).upsert(records, on_conflict=pk).execute()
        print(f"  [OK] {len(records)} filas migradas.")
        return 0
    except Exception as e:
        print(f"  [ERROR] {e}")
        return 1


if __name__ == "__main__":
    errors = 0

    errors += _migrate(
        table    = "convocatorias",
        csv_path = ROOT / "Data" / "Vigilancia" / "convocatorias_curadas.csv",
        pk       = "conv_id",
        cols     = ["conv_id", "tipo_registro", "titulo", "organismo", "categoria",
                    "estado", "apertura_texto", "cierre_texto", "fallo_texto",
                    "apertura_iso", "cierre_iso", "perfil_objetivo", "relevancia_cchen",
                    "fuente", "es_oficial", "postulable", "url", "notas"],
    )

    errors += _migrate(
        table    = "convocatorias_matching_rules",
        csv_path = ROOT / "Data" / "Vigilancia" / "convocatorias_matching_rules.csv",
        pk       = "rule_id",
        cols     = ["rule_id", "perfil_id", "exact_aliases", "secondary_aliases",
                    "requiere_doctorado", "requiere_institucion", "requiere_transferencia",
                    "requiere_red_internacional", "requiere_capacidad_instrumental", "notes"],
    )

    errors += _migrate(
        table    = "convocatorias_matching_institucional",
        csv_path = ROOT / "Data" / "Vigilancia" / "convocatorias_matching_institucional.csv",
        pk       = "conv_id,perfil_id",
        cols     = ["conv_id", "convocatoria_titulo", "estado", "categoria", "organismo",
                    "perfil_objetivo", "perfil_id", "perfil_nombre", "owner_unit",
                    "score_total", "score_breakdown", "eligibility_status",
                    "readiness_status", "recommended_action", "deadline_class",
                    "evidence_summary", "url", "relevancia_cchen",
                    "apertura_iso", "cierre_iso", "match_type", "last_evaluated_at"],
    )

    errors += _migrate(
        table    = "perfiles_institucionales",
        csv_path = ROOT / "Data" / "Vigilancia" / "perfiles_institucionales_cchen.csv",
        pk       = "perfil_id",
        cols     = ["perfil_id", "perfil_nombre", "owner_unit", "profile_aliases",
                    "secondary_aliases", "descripcion"],
    )

    print(f"\n{'[OK] Migración completa.' if errors == 0 else f'[WARN] {errors} errores.'}")
    sys.exit(0 if errors == 0 else 1)
