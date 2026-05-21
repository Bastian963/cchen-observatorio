#!/usr/bin/env python3
"""
Search over the unified CCHEN evidence index.

The preferred backend is Data/Semantic/evidence_embeddings.npy. When those
local artifacts are absent, Streamlit Cloud can still read the publicable
governance CSV and build in-memory sentence-transformer vectors. A small
lexical fallback is kept for degraded local environments.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "Data"
SEM_DIR = DATA / "Semantic"
GOVERNANCE_DIR = DATA / "Gobernanza"

INDEX_PATH = SEM_DIR / "evidence_index.csv"
EMB_PATH = SEM_DIR / "evidence_embeddings.npy"
META_PATH = SEM_DIR / "evidence_embeddings_meta.csv"
PIPELINE_PATH = SEM_DIR / "evidence_embedding_pipeline.joblib"
STATE_PATH = SEM_DIR / "evidence_index_state.json"
PUBLICABLE_INDEX_PATH = GOVERNANCE_DIR / "evidence_index_publicable.csv"

RESULT_COLUMNS = [
    "id",
    "titulo",
    "tipo_evidencia",
    "fuente",
    "fecha",
    "tema",
    "relacion_cchen",
    "uso_observatorio",
    "brecha",
    "nivel_confianza",
    "url",
    "identificador",
    "score",
]

_embeddings: np.ndarray | None = None
_metadata: pd.DataFrame | None = None
_runtime_embeddings: np.ndarray | None = None
_pipeline = None
_model = None


def _resolve_path(env_name: str, default: Path) -> Path:
    raw = os.getenv(env_name, "").strip()
    if not raw:
        return default
    path = Path(raw)
    return path if path.is_absolute() else ROOT / path


def _index_path() -> Path:
    return _resolve_path("EVIDENCE_SEARCH_INDEX_FILE", INDEX_PATH)


def _emb_path() -> Path:
    return _resolve_path("EVIDENCE_SEARCH_EMB_FILE", EMB_PATH)


def _meta_path() -> Path:
    return _resolve_path("EVIDENCE_SEARCH_META_FILE", META_PATH)


def _pipeline_path() -> Path:
    return _resolve_path("EVIDENCE_SEARCH_PIPELINE_FILE", PIPELINE_PATH)


def _state_path() -> Path:
    return _resolve_path("EVIDENCE_SEARCH_STATE_FILE", STATE_PATH)


def _publicable_index_path() -> Path:
    return _resolve_path("EVIDENCE_SEARCH_PUBLICABLE_INDEX_FILE", PUBLICABLE_INDEX_PATH)


def _empty_result() -> pd.DataFrame:
    return pd.DataFrame(columns=RESULT_COLUMNS)


def _load_state() -> dict:
    path = _state_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _load_metadata() -> pd.DataFrame:
    meta_path = _meta_path()
    index_path = _index_path()
    publicable_path = _publicable_index_path()
    path = meta_path if meta_path.exists() else index_path if index_path.exists() else publicable_path
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path, low_memory=False, encoding="utf-8-sig").fillna("")
    except Exception:
        return pd.read_csv(path, low_memory=False).fillna("")


def _load_artifacts() -> tuple[np.ndarray | None, pd.DataFrame]:
    global _embeddings, _metadata
    emb_path = _emb_path()
    if _metadata is None:
        _metadata = _load_metadata()
    if _embeddings is None and emb_path.exists():
        try:
            _embeddings = np.load(emb_path)
        except Exception as exc:
            print(f"[evidence_search] No se pudieron cargar vectores: {exc}")
            _embeddings = None
    return _embeddings, _metadata


def _load_pipeline():
    global _pipeline
    if _pipeline is not None:
        return _pipeline
    path = _pipeline_path()
    if not path.exists():
        return None
    try:
        from joblib import load

        _pipeline = load(path)
    except Exception as exc:
        print(f"[evidence_search] No se pudo cargar pipeline TF-IDF: {exc}")
        _pipeline = None
    return _pipeline


def _get_sentence_model(model_name: str):
    global _model
    if _model is not None:
        return _model
    from sentence_transformers import SentenceTransformer

    _model = SentenceTransformer(model_name)
    return _model


def _sentence_model_name() -> str:
    state = _load_state().get("embedding", {})
    model_name = str(state.get("model", "") or "").strip()
    if model_name and not model_name.startswith("tfidf_svd_"):
        return model_name
    return os.getenv("EVIDENCE_SEARCH_SENTENCE_MODEL", "paraphrase-multilingual-MiniLM-L12-v2")


def _embedding_text(row: pd.Series) -> str:
    if str(row.get("texto_embedding", "") or "").strip():
        return str(row.get("texto_embedding", ""))
    cols = [
        "titulo",
        "resumen",
        "tipo_evidencia",
        "fuente",
        "tema",
        "relacion_cchen",
        "uso_observatorio",
        "brecha",
    ]
    return " | ".join(str(row.get(col, "") or "") for col in cols)


def _encode_sentence_query(query: str) -> np.ndarray | None:
    try:
        model = _get_sentence_model(_sentence_model_name())
        return model.encode([query], normalize_embeddings=True)[0].astype("float32")
    except Exception as exc:
        print(f"[evidence_search] No se pudo codificar query con sentence-transformers: {exc}")
        return None


def _build_runtime_embeddings(meta: pd.DataFrame) -> np.ndarray | None:
    global _runtime_embeddings
    if os.getenv("EVIDENCE_SEARCH_DISABLE_RUNTIME_EMBEDDINGS", "").strip().lower() in {"1", "true", "yes"}:
        return None
    if _runtime_embeddings is not None:
        return _runtime_embeddings
    if meta.empty:
        return None
    try:
        model = _get_sentence_model(_sentence_model_name())
        texts = meta.apply(_embedding_text, axis=1).fillna("").astype(str).tolist()
        _runtime_embeddings = model.encode(
            texts,
            batch_size=64,
            show_progress_bar=False,
            normalize_embeddings=True,
        ).astype("float32")
        return _runtime_embeddings
    except Exception as exc:
        print(f"[evidence_search] No se pudieron generar vectores en memoria: {exc}")
        _runtime_embeddings = None
        return None


def _encode_query(query: str) -> np.ndarray | None:
    state = _load_state().get("embedding", {})
    backend = state.get("backend", "")
    model_name = state.get("model", "")

    if backend == "tfidf-svd":
        pipeline = _load_pipeline()
        if pipeline is None:
            return None
        return pipeline.transform([query])[0].astype("float32")

    if backend == "sentence-transformers" or model_name:
        return _encode_sentence_query(query)

    return None


def _normalize(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", text).strip().lower()


def _tokens(value: object) -> set[str]:
    return set(re.findall(r"[a-z0-9]{3,}", _normalize(value)))


def _profile_bonus(row: pd.Series, query: str) -> float:
    q = _normalize(query)
    text = _normalize(
        " ".join(
            str(row.get(col, "") or "")
            for col in ["titulo", "resumen", "tipo_evidencia", "fuente", "tema", "uso_observatorio", "brecha"]
        )
    )
    evidence_type = _normalize(row.get("tipo_evidencia", ""))
    source = _normalize(row.get("fuente", ""))
    bonus = 0.0

    if any(term in q for term in ["output", "dataset", "repositorio", "zenodo", "datacite", "openaire"]):
        if evidence_type == "dataset/output":
            bonus += 0.80
        if any(term in source for term in ["zenodo", "datacite", "openaire", "core", "hal", "doaj", "figshare"]):
            bonus += 0.30
        if evidence_type in {"proyecto", "oportunidad"}:
            bonus -= 0.40

    if any(term in q for term in ["radiofarm", "fdg", "lu-177", "ga-68", "tc-99m", "medicina nuclear"]):
        has_radio_signal = any(
            term in text
            for term in ["radiofarm", "medicina nuclear", "nuclear medicine", "fdg", "lu-177", "ga-68", "tc-99m", "i-131"]
        )
        if "radiofarm" in text:
            bonus += 0.35
        if "medicina nuclear" in text or "nuclear medicine" in text:
            bonus += 0.20
        if evidence_type in {"compuesto", "senal tematica"}:
            bonus += 0.12
        if any(term in source for term in ["radiofarmacia", "pubchem curado", "portafolio semilla"]):
            bonus += 0.25
        if not has_radio_signal:
            bonus -= 0.60

    if any(term in q for term in ["patente", "propiedad intelectual", "transferencia", "licenciamiento"]):
        radio_query = any(term in q for term in ["radiofarm", "medicina nuclear", "nuclear medicine"])
        radio_text = any(term in text for term in ["radiofarm", "medicina nuclear", "nuclear medicine", "fdg", "lu-177", "ga-68", "tc-99m", "i-131"])
        if evidence_type == "patente" and (not radio_query or radio_text):
            bonus += 0.85
        if "transferencia" in text or "propiedad intelectual" in text:
            bonus += 0.16
        if evidence_type != "patente" and any(term in q for term in ["patente", "propiedad intelectual"]):
            bonus -= 0.25

    if any(term in q for term in ["convocatoria", "oportunidad", "financiamiento", "fondo"]):
        if evidence_type == "oportunidad":
            bonus += 0.80
        if evidence_type == "proyecto":
            bonus += 0.30
        if evidence_type not in {"oportunidad", "proyecto"}:
            bonus -= 0.20

    if any(term in q for term in ["convenio", "acuerdo", "colaboracion", "cooperacion"]):
        if evidence_type == "convenio":
            bonus += 0.65
        if any(term in source for term in ["convenio", "acuerdo"]):
            bonus += 0.20
        if evidence_type not in {"convenio", "proyecto"}:
            bonus -= 0.15

    return bonus


def _rerank(df: pd.DataFrame, query: str, top_k: int) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    out["_base_score"] = pd.to_numeric(out.get("score", 0), errors="coerce").fillna(0.0)
    out["_profile_bonus"] = out.apply(lambda row: _profile_bonus(row, query), axis=1)
    out["score"] = (out["_base_score"] + out["_profile_bonus"]).round(4)
    out["_dedupe_key"] = (
        out.get("tipo_evidencia", "").astype(str).map(_normalize)
        + "|"
        + out.get("fuente", "").astype(str).map(_normalize)
        + "|"
        + out.get("titulo", "").astype(str).map(_normalize)
    )
    out = out.sort_values(
        ["score", "_profile_bonus", "_base_score", "titulo"],
        ascending=[False, False, False, True],
    ).drop_duplicates("_dedupe_key")
    return out.head(top_k)


def _candidate_pool_size(query: str, top_k: int, total: int) -> int:
    q = _normalize(query)
    type_sensitive_terms = [
        "patente",
        "propiedad intelectual",
        "inapi",
        "convenio",
        "acuerdo",
        "convocatoria",
        "oportunidad",
        "dataset",
        "output",
        "repositorio",
    ]
    if any(term in q for term in type_sensitive_terms):
        return total
    return min(total, max(top_k * 25, 200))


def _lexical_search(query: str, meta: pd.DataFrame, top_k: int) -> pd.DataFrame:
    if meta.empty:
        return _empty_result()
    query_tokens = _tokens(query)
    if not query_tokens:
        return _empty_result()
    searchable_cols = [
        col for col in ["titulo", "resumen", "tema", "relacion_cchen", "uso_observatorio", "brecha"]
        if col in meta.columns
    ]
    tmp = meta.copy()
    combined = tmp[searchable_cols].astype(str).agg(" ".join, axis=1)
    tmp["score"] = combined.map(lambda text: float(len(query_tokens & _tokens(text))))
    tmp = tmp[tmp["score"] > 0].sort_values(["score", "fecha", "titulo"], ascending=[False, False, True])
    candidate_count = _candidate_pool_size(query, top_k, len(tmp))
    return _shape_result(_rerank(tmp.head(candidate_count), query, top_k))


def _shape_result(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return _empty_result()
    out = df.copy()
    for col in RESULT_COLUMNS:
        if col not in out.columns:
            out[col] = ""
    return out[RESULT_COLUMNS].reset_index(drop=True)


def search(query: str, top_k: int = 10) -> pd.DataFrame:
    """Return top evidence records for a natural-language query."""
    query = str(query or "").strip()
    if not query:
        return _empty_result()

    emb, meta = _load_artifacts()
    if meta.empty:
        return _empty_result()

    if emb is not None and len(emb) == len(meta):
        q_vec = _encode_query(query)
        if q_vec is not None:
            scores = emb @ q_vec
            candidate_count = _candidate_pool_size(query, top_k, len(meta))
            top_idx = np.argsort(scores)[::-1][:candidate_count]
            result = meta.iloc[top_idx].copy()
            result["score"] = scores[top_idx].round(4)
            return _shape_result(_rerank(result, query, top_k))

    runtime_emb = _build_runtime_embeddings(meta)
    if runtime_emb is not None and len(runtime_emb) == len(meta):
        q_vec = _encode_sentence_query(query)
        if q_vec is not None:
            scores = runtime_emb @ q_vec
            candidate_count = _candidate_pool_size(query, top_k, len(meta))
            top_idx = np.argsort(scores)[::-1][:candidate_count]
            result = meta.iloc[top_idx].copy()
            result["score"] = scores[top_idx].round(4)
            return _shape_result(_rerank(result, query, top_k))

    return _lexical_search(query, meta, top_k)


def is_available() -> bool:
    return _meta_path().exists() or _index_path().exists() or _publicable_index_path().exists()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("query", nargs="+")
    parser.add_argument("--top", type=int, default=10)
    args = parser.parse_args()
    q = " ".join(args.query)
    results = search(q, args.top)
    if results.empty:
        print("Sin resultados. Ejecuta: python Scripts/build_evidence_index.py")
    else:
        for _, row in results.iterrows():
            print(f"[{row.get('score', 0):.4f}] {row.get('tipo_evidencia','')} | {row.get('fuente','')}")
            print(f"  {row.get('titulo','')[:120]}")
            print(f"  brecha: {row.get('brecha','')[:120]}")
