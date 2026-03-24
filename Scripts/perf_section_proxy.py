#!/usr/bin/env python3
"""Calcula tiempos proxy por seccion usando benchmark de loaders."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Proxy de tiempos por seccion")
    parser.add_argument(
        "--input",
        default="Docs/reports/perf_loader_post_quickwins_2026-03-23.json",
        help="Benchmark de loaders (JSON)",
    )
    args = parser.parse_args()

    repo = Path(__file__).resolve().parents[1]
    post = json.loads((repo / args.input).read_text(encoding="utf-8"))
    warm = post["warm"]

    keymap = {
        "pub": "publications",
        "pub_enr": "publications_enriched",
        "auth": "authorships",
        "anid": "anid",
        "concepts": "concepts",
        "matching_inst": "matching",
        "citation_graph": "citation_graph",
        "news_monitor": "news_monitor",
        "arxiv_monitor": "arxiv_monitor",
    }

    sections = {
        "Panel de Indicadores": ("pub", "pub_enr", "anid"),
        "Producción Científica": ("pub", "pub_enr", "auth", "anid", "concepts"),
        "Redes y Colaboración": ("auth", "pub"),
        "Vigilancia Tecnológica": ("arxiv_monitor", "news_monitor", "pub", "pub_enr"),
        "Financiamiento I+D": ("anid",),
        "Convocatorias y Matching": ("matching_inst",),
        "Transferencia y Portafolio": ("pub_enr", "anid"),
        "Modelo y Gobernanza": ("pub", "auth", "matching_inst"),
        "Asistente I+D": ("pub", "pub_enr", "auth", "anid", "matching_inst"),
        "Grafo de Citas": ("pub", "pub_enr", "citation_graph"),
    }

    print("section,warm_proxy_seconds")
    for name, keys in sections.items():
        total = 0.0
        for key in keys:
            loader_key = keymap.get(key)
            if loader_key and loader_key in warm:
                total += float(warm[loader_key]["seconds"])
        print(f"{name},{total:.4f}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
