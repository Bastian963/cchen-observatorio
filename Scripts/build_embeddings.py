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

import numpy as np
import pandas as pd

ROOT    = Path(__file__).resolve().parents[1]
PUB_DIR = ROOT / "Data" / "Publications"
OUT_EMB = PUB_DIR / "cchen_embeddings.npy"
OUT_META= PUB_DIR / "cchen_embeddings_meta.csv"

DEFAULT_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"  # 480 MB, soporta español e inglés
BATCH_SIZE    = 64

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()

    # Cargar publicaciones
    in_csv = PUB_DIR / "cchen_openalex_works.csv"
    if not in_csv.exists():
        print(f"✗ No encontrado: {in_csv}")
        return

    pub = pd.read_csv(in_csv).fillna("")

    # Columna de texto: título + abstract
    text_col = "title" if "title" in pub.columns else "display_name"
    abstract_col = "abstract" if "abstract" in pub.columns else None

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
    meta_cols = [c for c in [id_col, "doi", text_col, "year"] if c in pub.columns]
    pub[meta_cols].to_csv(OUT_META, index=False)

    print(f"\n✓ Embeddings guardados:")
    print(f"  {OUT_EMB}  ({embeddings.shape})")
    print(f"  {OUT_META}  ({len(pub)} filas)")
    print(f"  Modelo: {args.model}")
    print(f"  Fecha:  {datetime.date.today()}")

if __name__ == "__main__":
    main()
