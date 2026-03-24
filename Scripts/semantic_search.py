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
import os
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv

ROOT    = Path(__file__).resolve().parents[1]
PUB_DIR = ROOT / "Data" / "Publications"
EMB_FILE  = PUB_DIR / "cchen_embeddings.npy"
META_FILE = PUB_DIR / "cchen_embeddings_meta.csv"
load_dotenv(ROOT / "Database" / ".env")

_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
_embeddings: np.ndarray | None = None
_meta: pd.DataFrame | None = None
_model = None


def _result_columns() -> list[str]:
    return ["openalex_id", "doi", "title", "year", "abstract", "score"]


def _empty_result() -> pd.DataFrame:
    return pd.DataFrame(columns=_result_columns())


def _load_artifacts() -> tuple[np.ndarray, pd.DataFrame] | tuple[None, None]:
    global _embeddings, _meta
    if _embeddings is None:
        if not EMB_FILE.exists() or not META_FILE.exists():
            return None, None
        _embeddings = np.load(EMB_FILE)
        _meta = pd.read_csv(META_FILE).fillna("")
        if "abstract" not in _meta.columns:
            _meta["abstract"] = ""
    return _embeddings, _meta


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(_MODEL_NAME)
    return _model


def _encode_query(query: str) -> "np.ndarray | None":
    try:
        model = _get_model()
        return model.encode([query], normalize_embeddings=True)[0]
    except Exception:
        return None


def _resolve_supabase_credentials() -> tuple[str, str]:
    url = os.getenv("SUPABASE_URL") or os.getenv("supabase_url", "")
    key = os.getenv("SUPABASE_KEY") or os.getenv("supabase_key", "")
    if url and key:
        return url, key

    try:
        import streamlit as st
        _sb_cfg = st.secrets.get("supabase", {})
        url = url or _sb_cfg.get("url", "")
        key = key or _sb_cfg.get("anon_key", "") or _sb_cfg.get("service_role_key", "")
    except Exception:
        pass
    return url, key


def _search_supabase(query: str, top_k: int) -> pd.DataFrame:
    """Búsqueda vectorial vía Supabase pgvector (fallback cuando no hay .npy local)."""
    q_vec = _encode_query(query)
    if q_vec is None:
        return _empty_result()
    try:
        from supabase import create_client
        url, key = _resolve_supabase_credentials()
        if not url or not key:
            return _empty_result()

        client = create_client(url, key)
        resp = client.rpc(
            "match_papers",
            {"query_embedding": q_vec.tolist(), "match_count": top_k},
        ).execute()
        if not resp.data:
            return _empty_result()
        df = pd.DataFrame(resp.data)
        df = df.rename(columns={"similarity": "score"})
        if "abstract" not in df.columns:
            df["abstract"] = ""
        return df[[c for c in _result_columns() if c in df.columns]]
    except Exception:
        return _empty_result()


def search(query: str, top_k: int = 10) -> pd.DataFrame:
    """
    Busca los top_k papers más similares al query.
    Retorna DataFrame con columnas: openalex_id, doi, title, year, score.
    Usa embeddings locales si están disponibles; si no, usa Supabase pgvector.
    """
    emb, meta = _load_artifacts()
    if emb is not None:
        # Ruta local: más rápida
        q_vec = _encode_query(query)
        if q_vec is None:
            return _empty_result()
        scores = emb @ q_vec
        top_idx = np.argsort(scores)[::-1][:top_k]
        result = meta.iloc[top_idx].copy()
        result["score"] = scores[top_idx].round(4)
        return result[[c for c in _result_columns() if c in result.columns]].reset_index(drop=True)

    # Ruta Supabase: cuando los archivos locales no existen (Streamlit Cloud)
    return _search_supabase(query, top_k)


def is_available() -> bool:
    """True si la búsqueda semántica está disponible (local o Supabase)."""
    if EMB_FILE.exists() and META_FILE.exists():
        return True
    url, key = _resolve_supabase_credentials()
    return bool(url and key)


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
