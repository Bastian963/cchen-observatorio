#!/usr/bin/env python3
"""Benchmark rapido de loaders del dashboard (cold/warm)."""

from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
import time
from pathlib import Path


def timed_call(fn):
    t0 = time.perf_counter()
    df = fn()
    t1 = time.perf_counter()
    return t1 - t0, len(df)


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark de loaders del dashboard")
    parser.add_argument(
        "--output",
        default="Docs/reports/perf_loader_post_quickwins_2026-03-23.json",
        help="Ruta de salida JSON relativa al repo",
    )
    args = parser.parse_args()

    repo = Path(__file__).resolve().parents[1]
    os.environ.setdefault("OBSERVATORIO_DATA_SOURCE", "local")
    sys.path.insert(0, str(repo / "Dashboard"))

    import data_loader as dl  # noqa: WPS433

    importlib.reload(dl)

    loaders = {
        "publications": dl.load_publications,
        "publications_enriched": dl.load_publications_enriched,
        "authorships": dl.load_authorships,
        "concepts": dl.load_concepts,
        "anid": dl.load_anid,
        "convocatorias": dl.load_convocatorias,
        "matching": dl.load_matching_institucional,
        "citation_graph": dl.load_citation_graph,
        "news_monitor": dl.load_news_monitor,
        "arxiv_monitor": dl.load_arxiv_monitor,
    }

    cold = {}
    for name, fn in loaders.items():
        sec, rows = timed_call(fn)
        cold[name] = {"seconds": round(sec, 4), "rows": rows}

    warm = {}
    for name, fn in loaders.items():
        sec, rows = timed_call(fn)
        warm[name] = {"seconds": round(sec, 4), "rows": rows}

    out = {"mode": "local", "cold": cold, "warm": warm}
    out_path = repo / args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")

    print(json.dumps(out, indent=2))
    print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
