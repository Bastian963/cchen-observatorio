#!/usr/bin/env python3
"""Contract checks for the unified evidence index."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SEM_DIR = ROOT / "Data" / "Semantic"
PUBLICABLE_INDEX_PATH = ROOT / "Data" / "Gobernanza" / "evidence_index_publicable.csv"

REQUIRED_COLUMNS = [
    "id",
    "titulo",
    "resumen",
    "tipo_evidencia",
    "fuente",
    "url",
    "fecha",
    "relacion_cchen",
    "tema",
    "uso_observatorio",
    "brecha",
    "nivel_confianza",
    "source_path",
    "texto_embedding",
]

PUBLICABLE_REQUIRED_COLUMNS = [col for col in REQUIRED_COLUMNS if col != "texto_embedding"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-records", type=int, default=100)
    parser.add_argument("--require-embeddings", action="store_true", default=True)
    args = parser.parse_args()

    index_path = SEM_DIR / "evidence_index.csv"
    meta_path = SEM_DIR / "evidence_embeddings_meta.csv"
    emb_path = SEM_DIR / "evidence_embeddings.npy"
    state_path = SEM_DIR / "evidence_index_state.json"
    required_columns = REQUIRED_COLUMNS
    using_publicable_fallback = False

    errors: list[str] = []
    warnings: list[str] = []

    if not index_path.exists():
        if PUBLICABLE_INDEX_PATH.exists():
            index_path = PUBLICABLE_INDEX_PATH
            required_columns = PUBLICABLE_REQUIRED_COLUMNS
            using_publicable_fallback = True
            args.require_embeddings = False
            warnings.append(
                f"No existe indice semantico completo; usando indice publicable {PUBLICABLE_INDEX_PATH}"
            )
        else:
            errors.append(f"No existe {index_path} ni {PUBLICABLE_INDEX_PATH}")
            print("\n".join(errors))
            return 1

    df = pd.read_csv(index_path, low_memory=False).fillna("")
    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        errors.append(f"Columnas faltantes: {missing}")
    if len(df) < args.min_records:
        errors.append(f"Registros insuficientes: {len(df)} < {args.min_records}")
    if df["id"].duplicated().any():
        errors.append("Hay IDs duplicados en evidence_index.csv")

    must_not_be_blank = ["id", "titulo", "tipo_evidencia", "fuente", "relacion_cchen", "uso_observatorio", "brecha"]
    for col in must_not_be_blank:
        if col in df.columns:
            blank_count = int(df[col].astype(str).str.strip().eq("").sum())
            if blank_count:
                errors.append(f"Columna {col} tiene {blank_count} vacios")

    if "nivel_confianza" in df.columns:
        allowed = {"alto", "medio", "bajo"}
        unexpected = sorted(set(df["nivel_confianza"].astype(str).str.lower()) - allowed)
        if unexpected:
            warnings.append(f"Niveles de confianza no estandar: {unexpected}")

    if args.require_embeddings:
        if not emb_path.exists():
            errors.append(f"No existe {emb_path}")
        else:
            emb = np.load(emb_path)
            if len(emb) != len(df):
                errors.append(f"Vectores desalineados: {len(emb)} != {len(df)}")
        if not meta_path.exists():
            errors.append(f"No existe {meta_path}")
        else:
            meta = pd.read_csv(meta_path, low_memory=False).fillna("")
            if len(meta) != len(df):
                errors.append(f"Metadata de vectores desalineada: {len(meta)} != {len(df)}")

    if state_path.exists() and not using_publicable_fallback:
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state_records = int(state.get("records", 0) or 0)
        if state_records != len(df):
            errors.append(f"State records desalineado: {state_records} != {len(df)}")
    else:
        warnings.append(f"No existe {state_path}")

    print(f"evidence_index rows: {len(df):,}")
    print(f"types: {df['tipo_evidencia'].nunique() if 'tipo_evidencia' in df.columns else 0}")
    print(f"sources: {df['fuente'].nunique() if 'fuente' in df.columns else 0}")
    for warning in warnings:
        print(f"[WARN] {warning}")
    for error in errors:
        print(f"[ERROR] {error}")
    if errors:
        return 1
    print("[OK] evidence_index contract validado")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
