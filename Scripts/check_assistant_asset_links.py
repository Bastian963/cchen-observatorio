#!/usr/bin/env python3
"""Valida que el matching de activos del Asistente I+D cite URLs institucionales reales."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = REPO_ROOT / "Data" / "Gobernanza" / "catalogo_activos_3_en_1.csv"
QUERIES = [
    "Que documentos institucionales describen la arquitectura metodologica del observatorio?",
    "Muestrame datasets de convocatorias y matching para DGIn.",
    "Que evidencia documental existe del piloto DGIn?",
    "Donde puedo ver outputs de investigacion CCHEN publicados?",
    "Que documentacion tecnica del observatorio esta publicada?",
]


def _load_catalog() -> pd.DataFrame:
    frame = pd.read_csv(CATALOG_PATH, encoding="utf-8-sig").fillna("")
    for col in (
        "asset_id",
        "surface",
        "title",
        "local_path",
        "area_unidad",
        "tema",
        "responsables",
        "palabras_clave",
        "visibilidad",
        "identificador",
        "public_url",
        "vinculo_cruzado",
        "dashboard_section",
        "publication_status",
    ):
        frame[col] = frame[col].astype(str).str.strip()
    frame["surface"] = frame["surface"].str.lower()
    frame["publication_status"] = frame["publication_status"].str.lower()
    return frame


def _filter_published(frame: pd.DataFrame) -> pd.DataFrame:
    published = frame[
        (frame["publication_status"] == "published")
        & (frame["public_url"].str.strip() != "")
    ].copy()
    published = published.sort_values(["surface", "title"], ascending=[True, True], na_position="last")
    return published.reset_index(drop=True)


def _is_local_url(value: str) -> bool:
    parsed = urlparse(str(value).strip())
    hostname = (parsed.hostname or "").strip().lower()
    return hostname in {"localhost", "127.0.0.1"}


def _match_assets_to_query(frame: pd.DataFrame, query: str, limit: int = 4) -> pd.DataFrame:
    terms = [term for term in re.findall(r"\w+", str(query).lower()) if len(term) >= 3]
    if not terms:
        return frame.head(limit).reset_index(drop=True)

    def _score(row: pd.Series) -> int:
        score = 0
        title = str(row.get("title", "")).lower()
        tema = str(row.get("tema", "")).lower()
        keywords = str(row.get("palabras_clave", "")).lower()
        section = str(row.get("dashboard_section", "")).lower()
        area = str(row.get("area_unidad", "")).lower()
        for term in terms:
            if term in title:
                score += 4
            if term in tema:
                score += 3
            if term in keywords:
                score += 3
            if term in section:
                score += 2
            if term in area:
                score += 2
        if row.get("publication_status") == "published":
            score += 3
        if str(row.get("public_url", "")).strip():
            score += 2
        return score

    ranked = frame.assign(_score=frame.apply(_score, axis=1))
    ranked = ranked[ranked["_score"] > 0].sort_values(
        ["_score", "publication_status", "title"],
        ascending=[False, True, True],
        na_position="last",
    )
    return ranked.drop(columns=["_score"]).head(limit).reset_index(drop=True)


def main() -> int:
    catalog = _load_catalog()
    published = _filter_published(catalog)
    hits = 0
    local_hits = 0

    print(f"[assistant-assets] catalogo: {CATALOG_PATH}")
    print(f"[assistant-assets] activos publicados con URL: {len(published)}")

    for idx, query in enumerate(QUERIES, start=1):
        related = _match_assets_to_query(published, query, limit=4)
        print(f"\n[{idx}] {query}")
        if related.empty:
            print("  sin activos relacionados")
            continue

        hits += 1
        for _, row in related.iterrows():
            if _is_local_url(row["public_url"]):
                local_hits += 1
            print(f"  - {row['title']} | {row['surface']} | {row['public_url']}")

    print(f"\n[assistant-assets] queries con links: {hits}/{len(QUERIES)}")
    if hits < 4:
        print("[assistant-assets] ERROR: menos de 4 consultas devuelven URLs institucionales.")
        return 1

    if local_hits > 0:
        print(f"[assistant-assets] ERROR: se detectaron {local_hits} links locales en resultados publicados.")
        return 1

    print("[assistant-assets] validacion ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
