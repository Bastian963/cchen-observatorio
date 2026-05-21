"""Tests for the deterministic CRIS/RIMS audit."""

from __future__ import annotations

import sys
from pathlib import Path
import importlib.util

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_DIR = ROOT / "Dashboard"
if str(DASHBOARD_DIR) not in sys.path:
    sys.path.insert(0, str(DASHBOARD_DIR))

spec = importlib.util.spec_from_file_location(
    "cris_rims_audit",
    DASHBOARD_DIR / "sections" / "cris_rims_audit.py",
)
cris_rims_audit = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(cris_rims_audit)


def _registry(*source_keys: str) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "source_key": key,
                "enabled": "True",
                "last_run_status": "success",
                "visibility": "publico",
            }
            for key in source_keys
        ]
    )


def test_empty_audit_scores_as_missing():
    audit = cris_rims_audit.build_cris_rims_audit({}, pd.DataFrame())
    summary = cris_rims_audit.audit_summary(audit["maturity"])

    assert summary["weighted_score"] == 0.0
    assert summary["average_maturity"] == 0.0
    assert set(audit["maturity"]["Estado"]) == {"Faltante"}
    assert "Faltante" in set(audit["gaps"]["Estado CCHEN"])


def test_detects_core_pid_and_connector_coverage():
    ctx = {
        "pub": pd.DataFrame([{"doi": "10.123/example", "title": "CCHEN output"}]),
        "orcid": pd.DataFrame([{"orcid_id": "0000-0001-0000-0000"}]),
        "entity_personas": pd.DataFrame([{"persona_id": "p1"}]),
        "entity_projects": pd.DataFrame([{"project_id": "pr1"}]),
        "entity_convocatorias": pd.DataFrame([{"convocatoria_id": "c1"}]),
        "entity_links": pd.DataFrame([{"origin_type": "persona", "target_type": "proyecto"}]),
    }
    source_registry = _registry(
        "orcid",
        "ror_registry",
        "datacite_outputs",
        "openaire_outputs",
        "openalex_publicaciones",
        "crossref",
        "unpaywall_oa",
        "semantic_evidence_index",
        "matching_institucional",
        "ror_pending_review",
    )

    audit = cris_rims_audit.build_cris_rims_audit(ctx, source_registry)
    profile = audit["profile"]

    assert profile["orcid"] is True
    assert profile["ror"] is True
    assert profile["datacite"] is True
    assert profile["openaire"] is True
    assert profile["openalex"] is True
    assert profile["crossref"] is True
    assert "Detectado" in set(audit["interoperability"]["Estado CCHEN"])
    assert audit["maturity"].loc[
        audit["maturity"]["dimension_key"].eq("identity"),
        "Madurez 0-3",
    ].iloc[0] >= 2


def test_backlog_contains_required_critical_initiatives():
    audit = cris_rims_audit.build_cris_rims_audit({}, pd.DataFrame())
    initiatives = " | ".join(audit["backlog"]["Iniciativa"].str.lower().tolist())

    assert "authority control" in initiatives
    assert "dedupe pipeline" in initiatives
    assert "projects/awards" in initiatives
    assert "datasets/software" in initiatives
    assert "analytics mart" in initiatives


def test_agent_findings_have_required_structure():
    audit = cris_rims_audit.build_cris_rims_audit({}, pd.DataFrame())
    agents = audit["agents"]
    required = {"Agente", "Área", "Estado", "Evidencia", "Brecha", "Acción", "Confianza"}

    assert len(agents) == 4
    assert required.issubset(set(agents.columns))
    for column in required:
        assert agents[column].astype(str).str.len().gt(0).all()
