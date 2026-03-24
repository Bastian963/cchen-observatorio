#!/usr/bin/env python3
"""
build_embeddings.py — Observatorio CCHEN 360°
=============================================
Pre-calcula embeddings semánticos de títulos + abstracts de publicaciones CCHEN
usando sentence-transformers (modelo multilingüe).

Salidas:
  Data/Publications/cchen_embeddings.npy     — matriz (N, 384) float32
  Data/Publications/cchen_embeddings_meta.csv — openalex_id | doi | title | year

Uso:
    python3 Scripts/build_embeddings.py
    python3 Scripts/build_embeddings.py --model paraphrase-multilingual-MiniLM-L12-v2
    python3 Scripts/build_embeddings.py --reset   # recalcular todo
"""

from __future__ import annotations
import argparse
import datetime
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT    = Path(__file__).resolve().parents[1]
PUB_DIR = ROOT / "Data" / "Publications"
WORKS_CSV = PUB_DIR / "cchen_openalex_works.csv"
ABS_CSV   = PUB_DIR / "cchen_abstracts_merged.csv"
OUT_EMB = PUB_DIR / "cchen_embeddings.npy"
OUT_META= PUB_DIR / "cchen_embeddings_meta.csv"
_DASHBOARD_DIR = ROOT / "Dashboard"
if str(_DASHBOARD_DIR) not in sys.path:
    sys.path.insert(0, str(_DASHBOARD_DIR))

DEFAULT_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"  # 480 MB, soporta español e inglés
BATCH_SIZE    = 64


def _load_embedding_corpus_from_data_loader() -> pd.DataFrame:
    try:
        import data_loader
    except Exception:
        return pd.DataFrame()

    try:
        pub = data_loader.load_publications().copy().fillna("")
    except Exception:
        return pd.DataFrame()

    try:
        bertopic_docs = data_loader.load_bertopic_topics().copy().fillna("")
    except Exception:
        bertopic_docs = pd.DataFrame()

    if not bertopic_docs.empty and "openalex_id" in bertopic_docs.columns:
        abstract_cols = [c for c in ["abstract_best", "abstract"] if c in bertopic_docs.columns]
        if abstract_cols:
            bertopic_docs = (
                bertopic_docs[["openalex_id", *abstract_cols]]
                .drop_duplicates(subset=["openalex_id"])
            )
            pub = pub.merge(bertopic_docs, on="openalex_id", how="left", suffixes=("", "_bt"))

    if "abstract_best" in pub.columns and pub["abstract_best"].astype(str).str.strip().ne("").any():
        pub["abstract_for_embeddings"] = pub["abstract_best"]
    elif "abstract" in pub.columns:
        pub["abstract_for_embeddings"] = pub["abstract"]
    else:
        pub["abstract_for_embeddings"] = ""

    return pub


def _load_embedding_corpus() -> pd.DataFrame:
    if ABS_CSV.exists():
        abs_df = pd.read_csv(ABS_CSV, low_memory=False).fillna("")
        abs_df = abs_df.drop_duplicates(subset=["openalex_id"])

        if WORKS_CSV.exists():
            works_df = pd.read_csv(WORKS_CSV, low_memory=False).fillna("")
            works_df = works_df.drop_duplicates(subset=["openalex_id"])
            merge_cols = [c for c in ["openalex_id", "doi", "title", "year"] if c in works_df.columns]
            abs_df = abs_df.merge(
                works_df[merge_cols],
                on="openalex_id",
                how="left",
                suffixes=("", "_works"),
            )
            for col in ["doi", "title", "year"]:
                works_col = f"{col}_works"
                if works_col in abs_df.columns:
                    if col not in abs_df.columns:
                        abs_df[col] = ""
                    abs_df[col] = abs_df[col].where(abs_df[col].astype(str).str.strip() != "", abs_df[works_col])
                    abs_df = abs_df.drop(columns=[works_col])

        if "abstract_best" in abs_df.columns and abs_df["abstract_best"].astype(str).str.strip().ne("").any():
            abs_df["abstract_for_embeddings"] = abs_df["abstract_best"]
        elif "abstract" in abs_df.columns:
            abs_df["abstract_for_embeddings"] = abs_df["abstract"]
        else:
            abs_df["abstract_for_embeddings"] = ""

        return abs_df

    if not WORKS_CSV.exists():
        return _load_embedding_corpus_from_data_loader()

    works_df = pd.read_csv(WORKS_CSV, low_memory=False).fillna("")
    works_df["abstract_for_embeddings"] = ""
    return works_df

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()

    # Cargar publicaciones
    pub = _load_embedding_corpus()
    if pub.empty:
        print(f"✗ No encontrado: {ABS_CSV} ni {WORKS_CSV}")
        return

    # Columna de texto: título + abstract
    text_col = "title" if "title" in pub.columns else "display_name"
    abstract_col = "abstract_for_embeddings" if "abstract_for_embeddings" in pub.columns else None

    if abstract_col and abstract_col in pub.columns:
        pub["_text"] = (pub[text_col] + " " + pub[abstract_col]).str.strip()
    else:
        pub["_text"] = pub[text_col].str.strip()

    # Filtrar filas con texto vacío
    pub = pub[pub["_text"].str.len() > 5].reset_index(drop=True)
    print(f"Papers a embedder: {len(pub)}")

    # Verificar si ya existen y no se pidió reset
    if OUT_EMB.exists() and OUT_META.exists() and not args.reset:
        meta = pd.read_csv(OUT_META)
        if len(meta) == len(pub):
            print(f"✓ Embeddings ya existen ({len(meta)} filas). Usa --reset para recalcular.")
            return
        print(f"  Tamaño diferente ({len(meta)} vs {len(pub)}), recalculando...")

    # Cargar modelo
    print(f"Cargando modelo: {args.model} ...")
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        print("✗ sentence_transformers no instalado. Instala con: pip install sentence-transformers")
        return

    model = SentenceTransformer(args.model)

    # Calcular embeddings en batches con barra de progreso
    texts = pub["_text"].tolist()
    print(f"Calculando embeddings en batches de {BATCH_SIZE}...")

    embeddings = model.encode(
        texts,
        batch_size=BATCH_SIZE,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,  # cosine similarity → dot product
    )

    # Guardar
    np.save(OUT_EMB, embeddings.astype("float32"))

    id_col = "openalex_id" if "openalex_id" in pub.columns else "id"
    pub["abstract"] = pub[abstract_col] if abstract_col in pub.columns else ""
    meta_cols = [c for c in [id_col, "doi", text_col, "year", "abstract"] if c in pub.columns]
    pub[meta_cols].to_csv(OUT_META, index=False)

    print(f"\n✓ Embeddings guardados:")
    print(f"  {OUT_EMB}  ({embeddings.shape})")
    print(f"  {OUT_META}  ({len(pub)} filas)")
    print(f"  Modelo: {args.model}")
    print(f"  Fecha:  {datetime.date.today()}")

if __name__ == "__main__":
    main()
