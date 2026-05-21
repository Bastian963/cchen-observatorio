#!/usr/bin/env python3
"""Migrate the canonical capital_humano CSV into Supabase."""

from __future__ import annotations

import math
import os
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "Data" / "Capital humano CCHEN" / "salida_dataset_maestro" / "dataset_maestro_limpio.csv"
CHUNK_SIZE = 500


def _load_env() -> tuple[str, str]:
    load_dotenv(ROOT / "Database" / ".env")
    load_dotenv(ROOT / ".env")
    url = os.getenv("SUPABASE_URL", "").strip()
    key = (
        os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
        or os.getenv("SUPABASE_KEY", "").strip()
    )
    if not url or not key:
        raise SystemExit("[capital_humano] Define SUPABASE_URL y SUPABASE_SERVICE_ROLE_KEY/SUPABASE_KEY.")
    return url, key


def _to_records(df: pd.DataFrame) -> list[dict]:
    clean = df.astype(object).where(pd.notna(df), None)
    return clean.to_dict(orient="records")


def _load_frame() -> pd.DataFrame:
    if not CSV_PATH.exists():
        raise SystemExit(f"[capital_humano] Archivo no encontrado: {CSV_PATH}")
    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
    df.columns = [str(col).lstrip("\ufeff") for col in df.columns]

    for col in ("inicio", "termino"):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce").dt.strftime("%Y-%m-%d")
            df[col] = df[col].where(df[col].notna(), None)

    int_cols = [
        "anio_hoja",
        "duracion_dias",
        "flag_fechas_inconsistentes",
        "flag_tipo_fuera_catalogo",
    ]
    for col in int_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

    if "monto_contrato_num" in df.columns:
        df["monto_contrato_num"] = pd.to_numeric(df["monto_contrato_num"], errors="coerce")
    if "ad_honorem" in df.columns:
        df["ad_honorem"] = df["ad_honorem"].fillna(False).astype(bool)

    cols = [
        "anio_hoja",
        "nombre",
        "inicio",
        "termino",
        "duracion_dias",
        "tutor",
        "centro_norm",
        "tipo_norm",
        "universidad",
        "carrera",
        "monto_contrato_num",
        "ad_honorem",
        "objeto_contrato",
        "observaciones_texto",
        "informe_url_principal",
        "flag_fechas_inconsistentes",
        "flag_tipo_fuera_catalogo",
    ]
    return df[[col for col in cols if col in df.columns]].dropna(subset=["nombre"])


def main() -> int:
    url, key = _load_env()
    from supabase import create_client

    client = create_client(url, key)
    df = _load_frame()
    records = _to_records(df)

    print(f"[capital_humano] Limpiando tabla capital_humano...")
    client.table("capital_humano").delete().neq("id", 0).execute()

    batches = math.ceil(len(records) / CHUNK_SIZE) if records else 0
    errors = 0
    for idx in range(batches):
        batch = records[idx * CHUNK_SIZE : (idx + 1) * CHUNK_SIZE]
        try:
            client.table("capital_humano").insert(batch).execute()
            print(f"  Batch {idx + 1}/{batches} OK ({len(batch)} filas)")
        except Exception as exc:
            errors += 1
            print(f"  [ERROR] Batch {idx + 1}/{batches}: {exc}")
    if errors:
        return 1
    print(f"[capital_humano] OK: {len(records)} registros migrados.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
