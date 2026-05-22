"""Regression tests for assistant retrieval degradation paths."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "Scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import evidence_search
import semantic_search


def test_semantic_search_uses_lexical_fallback_when_encoder_is_missing(tmp_path, monkeypatch):
    emb_path = tmp_path / "embeddings.npy"
    meta_path = tmp_path / "meta.csv"

    np.save(emb_path, np.zeros((2, 3), dtype="float32"))
    pd.DataFrame(
        [
            {
                "openalex_id": "W1",
                "doi": "10.123/radiofarmacia",
                "title": "Radiofarmacia CCHEN y transferencia tecnologica",
                "year": 2026,
                "abstract": "Medicina nuclear, radiofarmacos y vinculacion institucional.",
            },
            {
                "openalex_id": "W2",
                "doi": "10.123/materiales",
                "title": "Materiales estructurales",
                "year": 2025,
                "abstract": "Caracterizacion metalurgica.",
            },
        ]
    ).to_csv(meta_path, index=False)

    monkeypatch.setenv("SEMANTIC_SEARCH_EMB_FILE", str(emb_path))
    monkeypatch.setenv("SEMANTIC_SEARCH_META_FILE", str(meta_path))
    monkeypatch.delenv("SEMANTIC_SEARCH_FIXTURE_META_FILE", raising=False)
    monkeypatch.setattr(semantic_search, "_encode_query", lambda query: None)
    semantic_search._embeddings = None
    semantic_search._meta = None
    semantic_search._artifact_source = None

    result = semantic_search.search("radiofarmacia transferencia CCHEN", top_k=1)

    assert not result.empty
    assert result.iloc[0]["openalex_id"] == "W1"


def test_evidence_search_prioritizes_patents_for_ip_queries(tmp_path, monkeypatch):
    index_path = tmp_path / "evidence_index.csv"
    pd.DataFrame(
        [
            {
                "id": "publication:1",
                "titulo": "Propiedad intelectual y transferencia CCHEN",
                "resumen": "Publicacion con menciones a patente, propiedad intelectual y transferencia.",
                "tipo_evidencia": "publicacion",
                "fuente": "CrossRef",
                "fecha": "2026",
                "tema": "transferencia",
                "relacion_cchen": "CCHEN",
                "uso_observatorio": "Contexto bibliografico.",
                "brecha": "No representa un registro de propiedad industrial.",
                "nivel_confianza": "alto",
                "url": "",
                "identificador": "10.123/example",
            },
            {
                "id": "patent:1",
                "titulo": "Patente INAPI CCHEN",
                "resumen": "Registro de propiedad industrial asociado a CCHEN.",
                "tipo_evidencia": "patente",
                "fuente": "INAPI",
                "fecha": "2025",
                "tema": "patentes y transferencia",
                "relacion_cchen": "Titular institucional.",
                "uso_observatorio": "Levantar antecedentes de propiedad intelectual.",
                "brecha": "Revisar vigencia y titulares.",
                "nivel_confianza": "medio",
                "url": "",
                "identificador": "INAPI-1",
            },
        ]
    ).to_csv(index_path, index=False)

    monkeypatch.setenv("EVIDENCE_SEARCH_INDEX_FILE", str(index_path))
    monkeypatch.setenv("EVIDENCE_SEARCH_META_FILE", str(index_path))
    monkeypatch.setenv("EVIDENCE_SEARCH_EMB_FILE", str(tmp_path / "missing.npy"))
    monkeypatch.setenv("EVIDENCE_SEARCH_PIPELINE_FILE", str(tmp_path / "missing.joblib"))
    evidence_search._metadata = None
    evidence_search._embeddings = None
    evidence_search._pipeline = None
    evidence_search._runtime_embeddings = None

    result = evidence_search.search("patentes y propiedad intelectual CCHEN", top_k=2)

    assert not result.empty
    assert result.iloc[0]["tipo_evidencia"] == "patente"
