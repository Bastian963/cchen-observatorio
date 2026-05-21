"""
migrate_sjr.py — Observatorio CCHEN 360°
=========================================
Migra los 26 CSVs anuales de SJR Scimago (Data/scimagojr/)
a la tabla sjr_journal_rankings en Supabase.

PK: (sourceid, year)

Uso:
    python3 Database/migrate_sjr.py
    python3 Database/migrate_sjr.py --year 2024     # solo un año
    python3 Database/migrate_sjr.py --dry-run
"""
import os
import re
import sys
import math
import argparse
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

ROOT     = Path(__file__).parent.parent
SJR_DIR  = ROOT / "Data" / "scimagojr"

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

CHUNK = 200

# Columnas de salida fijas → nombre de columna en Supabase
COL_MAP = {
    "Rank":                     "rank",
    "Sourceid":                 "sourceid",
    "Title":                    "title",
    "Type":                     "type",
    "Issn":                     "issn",
    "Publisher":                "publisher",
    "Open Access":              "open_access",
    "Open Access Diamond":      "open_access_diamond",
    "SJR":                      "sjr",
    "SJR Best Quartile":        "sjr_best_quartile",
    "H index":                  "h_index",
    "total_docs_year":          "total_docs_year",    # renombrado dinámicamente
    "Total Docs. (3years)":     "total_docs_3years",
    "Total Refs.":              "total_refs",
    "Total Citations (3years)": "total_citations_3years",
    "Citable Docs. (3years)":   "citable_docs_3years",
    "Citations / Doc. (2years)": "citations_per_doc_2y",
    "Ref. / Doc.":              "ref_per_doc",
    "%Female":                  "pct_female",
    "Country":                  "country",
    "Region":                   "region",
    "Coverage":                 "coverage",
    "Categories":               "categories",
    "Areas":                    "areas",
}

OUTPUT_COLS = [
    "sourceid", "year", "rank", "title", "type", "issn", "publisher",
    "open_access", "open_access_diamond", "sjr", "sjr_best_quartile",
    "h_index", "total_docs_year", "total_docs_3years", "total_refs",
    "total_citations_3years", "citable_docs_3years",
    "citations_per_doc_2y", "ref_per_doc", "pct_female",
    "country", "region", "coverage", "categories", "areas",
]


def _comma_to_float(series: pd.Series) -> pd.Series:
    """Convierte decimales con coma europea a float ('145,004' → 145.004)."""
    return (
        series.astype(str)
        .str.replace(",", ".", regex=False)
        .pipe(pd.to_numeric, errors="coerce")
    )


def _clean(v):
    if v is None:
        return None
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None
    if isinstance(v, bool):
        return bool(v)
    try:
        if pd.isna(v):
            return None
    except Exception:
        pass
    return v.item() if hasattr(v, "item") else v


def _read_sjr_csv(path: Path, year: int) -> pd.DataFrame:
    df = pd.read_csv(path, sep=";", dtype=str, encoding="utf-8-sig")

    # Renombrar columna dinámica "Total Docs. (YYYY)"
    for col in df.columns:
        if re.match(r"Total Docs\. \(\d{4}\)", col):
            df = df.rename(columns={col: "total_docs_year"})
            break

    # Eliminar columna Publisher duplicada si existe
    dupes = [c for c in df.columns if c == "Publisher"]
    if len(dupes) > 1:
        df = df.loc[:, ~df.columns.duplicated(keep="first")]

    # Renombrar a snake_case
    df = df.rename(columns={k: v for k, v in COL_MAP.items() if k in df.columns})

    df["year"] = year

    # Conversiones numéricas con decimal europeo
    for col in ("sjr", "citations_per_doc_2y", "ref_per_doc", "pct_female"):
        if col in df.columns:
            df[col] = _comma_to_float(df[col])

    for col in ("rank", "h_index", "total_docs_year", "total_docs_3years",
                "total_refs", "total_citations_3years", "citable_docs_3years"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

    for col in ("open_access", "open_access_diamond"):
        if col in df.columns:
            df[col] = df[col].map(lambda x: True if str(x).strip().lower() == "yes"
                                  else (False if str(x).strip().lower() == "no" else None))

    # Asegurar que están todas las columnas de salida
    for col in OUTPUT_COLS:
        if col not in df.columns:
            df[col] = None

    return df[OUTPUT_COLS].dropna(subset=["sourceid"])


def migrate(only_year: int | None = None, dry_run: bool = False) -> int:
    csv_files = sorted(SJR_DIR.glob("scimagojr *.csv"))
    if not csv_files:
        sys.exit(f"[ERROR] No se encontraron CSVs en {SJR_DIR}")

    if only_year:
        csv_files = [f for f in csv_files if str(only_year) in f.name]
        if not csv_files:
            sys.exit(f"[ERROR] No hay CSV para el año {only_year}")

    print(f"[INFO] {len(csv_files)} archivos SJR a procesar")

    total_errors = 0
    for path in csv_files:
        m = re.search(r"(\d{4})", path.stem)
        if not m:
            print(f"[WARN] No se pudo extraer año de: {path.name}")
            continue
        year = int(m.group(1))

        try:
            df = _read_sjr_csv(path, year)
        except Exception as exc:
            print(f"[ERROR] Leyendo {path.name}: {exc}")
            total_errors += 1
            continue

        print(f"  {path.name}: {len(df)} filas (año {year})")
        if dry_run:
            print(f"    [dry-run] Se cargarían {len(df)} registros para {year}")
            continue

        records = [{k: _clean(v) for k, v in row.items()}
                   for row in df.to_dict("records")]
        batches = math.ceil(len(records) / CHUNK)
        for i in range(batches):
            chunk = records[i * CHUNK:(i + 1) * CHUNK]
            try:
                sb.table("sjr_journal_rankings").upsert(
                    chunk, on_conflict="sourceid,year"
                ).execute()
            except Exception as exc:
                total_errors += 1
                print(f"    [WARN] Batch {i+1}/{batches} año {year} FALLÓ: {exc}")

    print(f"\n[{'OK' if total_errors == 0 else 'WARN'}] Finalizado. Errores: {total_errors}")
    return total_errors


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrar SJR Scimago → Supabase")
    parser.add_argument("--year", type=int, default=None, help="Solo migrar este año")
    parser.add_argument("--dry-run", action="store_true", help="No subir a Supabase")
    args = parser.parse_args()
    sys.exit(0 if migrate(only_year=args.year, dry_run=args.dry_run) == 0 else 1)
