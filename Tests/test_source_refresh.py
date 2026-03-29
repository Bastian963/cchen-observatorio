"""Tests para la capa canónica de refresh de fuentes."""

from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "Scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from run_source_refresh import compute_next_due, select_due_sources
from source_refresh_registry import SOURCE_DEFINITIONS, build_registry_frame


def test_registry_has_unique_source_keys():
    keys = [definition["source_key"] for definition in SOURCE_DEFINITIONS]
    assert len(keys) == len(set(keys))
    assert "zenodo_outputs" in keys


def test_build_registry_frame_contains_runtime_columns():
    df = build_registry_frame()
    assert isinstance(df, pd.DataFrame)
    assert "source_key" in df.columns
    assert "last_run_status" in df.columns
    assert "next_update_due" in df.columns


def test_compute_next_due_uses_frequency_days():
    last_updated = dt.date(2026, 3, 1)
    assert compute_next_due(last_updated, "semanal", None) == "2026-03-08"
    assert compute_next_due(last_updated, "mensual", None) == "2026-03-31"


def test_select_due_sources_filters_enabled_and_due():
    registry = pd.DataFrame(
        [
            {
                "source_key": "due_source",
                "enabled": True,
                "blocking": False,
                "update_frequency": "semanal",
                "freshness_sla_days": 8,
                "last_updated": "2026-03-01",
                "next_update_due": "2026-03-08",
            },
            {
                "source_key": "future_source",
                "enabled": True,
                "blocking": False,
                "update_frequency": "semanal",
                "freshness_sla_days": 8,
                "last_updated": "2026-03-20",
                "next_update_due": "2026-04-05",
            },
            {
                "source_key": "disabled_source",
                "enabled": False,
                "blocking": False,
                "update_frequency": "semanal",
                "freshness_sla_days": 8,
                "last_updated": "2026-03-01",
                "next_update_due": "2026-03-08",
            },
        ]
    )

    selected = select_due_sources(
        registry,
        reference_date=dt.date(2026, 3, 29),
    )

    assert selected["source_key"].tolist() == ["due_source"]
