#!/usr/bin/env python3
"""
semantic_search.py — Utilidad de búsqueda semántica CCHEN
=========================================================
Función search() que recibe un query de texto y retorna los N papers más similares.
Cargable desde el dashboard sin necesidad de sentence_transformers en runtime
(usa numpy directamente si los embeddings ya están calculados).

Uso como script:
    python3 Scripts/semantic_search.py "dosimetría radiación reactores"
    python3 Scripts/semantic_search.py "nuclear medicine imaging" --top 10
"""
from __future__ import annotations
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

ROOT    = Path(__file__).resolve().parents[1]
PUB_DIR = ROOT / "Data" / "Publications"
EMB_FILE  = PUB_DIR / "cchen_embeddings.npy"
META_FILE = PUB_DIR / "cchen_embeddings_meta.csv"

_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
_embeddings: np.ndarray | None = None
_meta: pd.DataFrame | None = None


def _load_artifacts() -> tuple[np.ndarray, pd.DataFrame] | tuple[None, None]:
    global _embeddings, _meta
    if _embeddings is None:
        if not EMB_FILE.exists() or not META_FILE.exists():
            return None, None
        _embeddings = np.load(EMB_FILE)
        _meta = pd.read_csv(META_FILE).fillna("")
    return _embeddings, _meta


def search(query: str, top_k: int = 10) -> pd.DataFrame:
    """
    Busca los top_k papers más similares al query.
    Retorna DataFrame con columnas: openalex_id, doi, title, year, score.
    Si los embeddings no están disponibles, retorna DataFrame vacío.
    """
    emb, meta = _load_artifacts()
    if emb is None:
        return pd.DataFrame(columns=["openalex_id", "doi", "title", "year", "score"])

    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer(_MODEL_NAME)
        q_vec = model.encode([query], normalize_embeddings=True)[0]
    except Exception:
        return pd.DataFrame(columns=["openalex_id", "doi", "title", "year", "score"])

    scores = emb @ q_vec  # dot product (cosine similarity, ya normalizados)
    top_idx = np.argsort(scores)[::-1][:top_k]

    result = meta.iloc[top_idx].copy()
    result["score"] = scores[top_idx].round(4)
    return result.reset_index(drop=True)


def is_available() -> bool:
    """True si los embeddings están pre-calculados y listos."""
    return EMB_FILE.exists() and META_FILE.exists()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("query", nargs="+")
    parser.add_argument("--top", type=int, default=10)
    args = parser.parse_args()
    q = " ".join(args.query)
    print(f"\nQuery: '{q}'\n")
    results = search(q, args.top)
    if results.empty:
        print("No hay embeddings. Corre primero: python3 Scripts/build_embeddings.py")
    else:
        for _, row in results.iterrows():
            print(f"  [{row.get('year','')}] {row.get('title','')[:80]}")
            print(f"    score={row['score']:.4f}  doi={row.get('doi','')}")
