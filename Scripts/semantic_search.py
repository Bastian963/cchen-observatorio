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
import re
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv

ROOT    = Path(__file__).resolve().parents[1]
PUB_DIR = ROOT / "Data" / "Publications"
load_dotenv(ROOT / "Database" / ".env")

_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
_embeddings: np.ndarray | None = None
_meta: pd.DataFrame | None = None
_artifact_source: tuple[str, str] | None = None
_fixture_meta: pd.DataFrame | None = None
_fixture_source: str | None = None
_model = None
_PROFILE_QUERY_TERMS = (
    "medicina nuclear",
    "nuclear medicine",
)
_PROFILE_STRONG_TERMS = (
    "medicina nuclear",
    "nuclear medicine",
    "pet/ct",
    "dotatate",
    "177lu",
    "166ho",
    "radiopharmaceutical",
    "radiofarmaceut",
    "gamma camera",
    "99mtc",
    "18f-fdg",
)
_PROFILE_SECONDARY_TERMS = (
    "imagenologia",
    "imaginologia",
    "pet",
    "spect",
    "molecular imaging",
    "neuroendocr",
)
_PROFILE_NEGATIVE_TERMS = (
    "radiodiagnostico",
    "radiodiagnosis",
    "intervencionismo",
    "cardiologia intervencion",
)
_FIXTURE_TOKEN_PATTERN = re.compile(r"[a-z0-9]{2,}")


def _result_columns() -> list[str]:
    return ["openalex_id", "doi", "title", "year", "abstract", "score"]


def _empty_result() -> pd.DataFrame:
    return pd.DataFrame(columns=_result_columns())


def _resolve_path_env(name: str, default: Path | None = None) -> Path | None:
    raw_value = str(os.getenv(name, "")).strip()
    if raw_value:
        path = Path(raw_value)
        return path if path.is_absolute() else ROOT / path
    return default


def _emb_file() -> Path:
    return _resolve_path_env("SEMANTIC_SEARCH_EMB_FILE", PUB_DIR / "cchen_embeddings.npy")


def _meta_file() -> Path:
    return _resolve_path_env("SEMANTIC_SEARCH_META_FILE", PUB_DIR / "cchen_embeddings_meta.csv")


def _fixture_meta_file() -> Path | None:
    return _resolve_path_env("SEMANTIC_SEARCH_FIXTURE_META_FILE", None)


def _load_artifacts() -> tuple[np.ndarray, pd.DataFrame] | tuple[None, None]:
    global _embeddings, _meta, _artifact_source
    emb_file = _emb_file()
    meta_file = _meta_file()
    current_source = (str(emb_file), str(meta_file))
    if _embeddings is None or _meta is None or _artifact_source != current_source:
        if not emb_file.exists() or not meta_file.exists():
            return None, None
        try:
            emb = np.load(emb_file)
            meta = pd.read_csv(meta_file).fillna("")
            if "abstract" not in meta.columns:
                meta["abstract"] = ""
            # Only assign globals once both files loaded successfully
            _embeddings, _meta = emb, meta
            _artifact_source = current_source
        except Exception as exc:
            print(f"[semantic_search] Failed to load artifacts: {exc}")
            return None, None
    return _embeddings, _meta


def _load_fixture_meta() -> pd.DataFrame | None:
    global _fixture_meta, _fixture_source
    fixture_file = _fixture_meta_file()
    if fixture_file is None or not fixture_file.exists():
        return None

    current_source = str(fixture_file)
    if _fixture_meta is None or _fixture_source != current_source:
        try:
            meta = pd.read_csv(fixture_file).fillna("")
            for column in ("openalex_id", "doi", "title", "year", "abstract"):
                if column not in meta.columns:
                    meta[column] = ""
            _fixture_meta = meta
            _fixture_source = current_source
        except Exception as exc:
            print(f"[semantic_search] Failed to load fixture corpus: {exc}")
            return None
    return _fixture_meta


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
    except Exception as exc:
        print(f"[semantic_search] Failed to encode query: {exc}")
        return None


def _normalize_match_text(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", text).strip().lower()


def _tokenize_fixture_text(value: object) -> set[str]:
    normalized = _normalize_match_text(value)
    return set(_FIXTURE_TOKEN_PATTERN.findall(normalized))


def _uses_nuclear_medicine_profile(query: str) -> bool:
    normalized_query = _normalize_match_text(query)
    return any(term in normalized_query for term in _PROFILE_QUERY_TERMS)


def _candidate_count(top_k: int, query: str) -> int:
    if _uses_nuclear_medicine_profile(query):
        return max(top_k, top_k * 5, 15)
    return top_k


def _profile_bonus(title: str, abstract: str) -> float:
    title_text = _normalize_match_text(title)
    combined_text = _normalize_match_text(f"{title} {abstract}")

    strong_hits = sum(term in combined_text for term in _PROFILE_STRONG_TERMS)
    secondary_hits = sum(term in combined_text for term in _PROFILE_SECONDARY_TERMS)
    negative_hits = sum(term in combined_text for term in _PROFILE_NEGATIVE_TERMS)
    title_has_strong_signal = any(term in title_text for term in _PROFILE_STRONG_TERMS)

    positive_bonus = (strong_hits * 0.06) + (secondary_hits * 0.02)
    if title_has_strong_signal:
        positive_bonus += 0.04

    if strong_hits:
        negative_penalty = min(negative_hits, 1) * 0.01
    else:
        negative_penalty = negative_hits * 0.03

    return positive_bonus - negative_penalty


def _rerank_profile_results(results: pd.DataFrame, query: str, top_k: int) -> pd.DataFrame:
    if results.empty or not _uses_nuclear_medicine_profile(query):
        return results.head(top_k).reset_index(drop=True)

    reranked = results.copy()
    reranked["base_score"] = pd.to_numeric(reranked.get("score", 0), errors="coerce").fillna(0.0)
    reranked["title"] = reranked.get("title", "").fillna("").astype(str)
    reranked["abstract"] = reranked.get("abstract", "").fillna("").astype(str)
    reranked["profile_bonus"] = reranked.apply(
        lambda row: _profile_bonus(row["title"], row["abstract"]),
        axis=1,
    )
    reranked["score"] = (reranked["base_score"] + reranked["profile_bonus"]).round(4)
    reranked = reranked.sort_values(
        by=["score", "profile_bonus", "base_score"],
        ascending=[False, False, False],
    )
    return reranked.head(top_k)[[c for c in _result_columns() if c in reranked.columns]].reset_index(drop=True)


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
        candidate_count = _candidate_count(top_k, query)
        resp = client.rpc(
            "match_papers",
            {"query_embedding": q_vec.tolist(), "match_count": candidate_count},
        ).execute()
        if not resp.data:
            return _empty_result()
        df = pd.DataFrame(resp.data)
        df = df.rename(columns={"similarity": "score"})
        if "abstract" not in df.columns:
            df["abstract"] = ""
        df = df[[c for c in _result_columns() if c in df.columns]]
        return _rerank_profile_results(df, query=query, top_k=top_k)
    except Exception:
        return _empty_result()


def _search_fixture(query: str, top_k: int) -> pd.DataFrame:
    """Versioned mini-corpus for reproducible CI sanity checks."""
    meta = _load_fixture_meta()
    if meta is None or meta.empty:
        return _empty_result()

    query_tokens = _tokenize_fixture_text(query)
    if not query_tokens:
        return _empty_result()

    fixture = meta.copy()
    combined_text = fixture["title"].astype(str) + " " + fixture["abstract"].astype(str)
    fixture["score"] = combined_text.map(
        lambda text: float(len(query_tokens & _tokenize_fixture_text(text)))
    )
    fixture = fixture[fixture["score"] > 0].copy()
    if fixture.empty:
        return _empty_result()

    fixture["_year_sort"] = pd.to_numeric(fixture["year"], errors="coerce").fillna(0)
    fixture = fixture.sort_values(
        by=["score", "_year_sort", "title"],
        ascending=[False, False, True],
    )
    fixture = fixture.head(top_k)
    fixture = fixture[[c for c in _result_columns() if c in fixture.columns]].reset_index(drop=True)
    return _rerank_profile_results(fixture, query=query, top_k=top_k)


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
        candidate_count = _candidate_count(top_k, query)
        top_idx = np.argsort(scores)[::-1][:candidate_count]
        result = meta.iloc[top_idx].copy()
        result["score"] = scores[top_idx].round(4)
        result = result[[c for c in _result_columns() if c in result.columns]].reset_index(drop=True)
        return _rerank_profile_results(result, query=query, top_k=top_k)

    if _fixture_meta_file() is not None:
        return _search_fixture(query, top_k)

    # Ruta Supabase: cuando los archivos locales no existen (Streamlit Cloud)
    return _search_supabase(query, top_k)


def is_available() -> bool:
    """True si la búsqueda semántica está disponible (local o Supabase)."""
    emb_file = _emb_file()
    meta_file = _meta_file()
    fixture_file = _fixture_meta_file()
    if emb_file.exists() and meta_file.exists():
        return True
    if fixture_file is not None and fixture_file.exists():
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
