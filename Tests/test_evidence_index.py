"""Tests for the unified CCHEN evidence index."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "Scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import build_evidence_index
import evidence_search
from source_refresh_registry import SOURCE_DEFINITIONS


def test_source_registry_contains_semantic_evidence_index():
    keys = {definition["source_key"] for definition in SOURCE_DEFINITIONS}
    assert "semantic_evidence_index" in keys


def test_build_index_normalizes_minimal_publication(tmp_path, monkeypatch):
    data_dir = tmp_path / "Data"
    pub_dir = data_dir / "Publications"
    pub_dir.mkdir(parents=True)
    pd.DataFrame(
        [
            {
                "openalex_id": "https://openalex.org/W1",
                "doi": "10.123/example",
                "title": "Radiofarmacia y medicina nuclear en CCHEN",
                "year": 2026,
                "abstract_best": "Evidencia institucional para gestion de investigacion.",
            }
        ]
    ).to_csv(pub_dir / "cchen_abstracts_merged.csv", index=False)

    monkeypatch.setattr(build_evidence_index, "DATA", data_dir)
    df = build_evidence_index.build_index()

    assert len(df) == 1
    assert df.iloc[0]["tipo_evidencia"] == "publicacion"
    assert df.iloc[0]["nivel_confianza"] == "alto"
    assert "radiofarmacia" in df.iloc[0]["tema"]
    assert df.iloc[0]["uso_observatorio"]
    assert df.iloc[0]["brecha"]


def test_evidence_search_lexical_fallback(tmp_path, monkeypatch):
    index_path = tmp_path / "evidence_index.csv"
    pd.DataFrame(
        [
            {
                "id": "dataset:1",
                "titulo": "Dataset CCHEN en Zenodo",
                "resumen": "Output institucional asociado a CCHEN.",
                "tipo_evidencia": "dataset/output",
                "fuente": "Zenodo",
                "fecha": "2026",
                "tema": "datos y repositorios",
                "relacion_cchen": "Output asociado a CCHEN.",
                "uso_observatorio": "Identificar resultados reutilizables.",
                "brecha": "Clasificar utilidad.",
                "nivel_confianza": "medio",
                "url": "https://zenodo.org",
                "identificador": "10.5281/example",
            },
            {
                "id": "project:1",
                "titulo": "Proyecto ANID CCHEN",
                "resumen": "Proyecto de investigacion.",
                "tipo_evidencia": "proyecto",
                "fuente": "ANID",
                "fecha": "2025",
                "tema": "financiamiento",
                "relacion_cchen": "Proyecto asociado a CCHEN.",
                "uso_observatorio": "Conectar financiamiento.",
                "brecha": "Vincular resultados.",
                "nivel_confianza": "alto",
                "url": "",
                "identificador": "ANID-1",
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

    result = evidence_search.search("outputs o datasets asociados a CCHEN", top_k=2)
    assert not result.empty
    assert result.iloc[0]["tipo_evidencia"] == "dataset/output"
