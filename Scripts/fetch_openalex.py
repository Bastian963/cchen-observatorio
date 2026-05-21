#!/usr/bin/env python3
"""
fetch_openalex.py — Observatorio CCHEN 360°
============================================
Descarga publicaciones CCHEN desde OpenAlex vía cursor pagination.

CCHEN en OpenAlex:
  institution ID : I4210133321
  ROR            : https://ror.org/03hv95d67

API: https://api.openalex.org  (sin API key; polite pool con mailto)
Rate limit recomendado: ≤10 req/s; se usa 0.12s entre requests.

Salidas:
  Data/Publications/cchen_openalex_works.csv
  Data/Publications/openalex_state.json

Uso:
    python3 Scripts/fetch_openalex.py
    python3 Scripts/fetch_openalex.py --reset
    python3 Scripts/fetch_openalex.py --verbose
"""
from __future__ import annotations

import argparse
import datetime
import json
import time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from urllib.parse import urlencode
import re

import pandas as pd

ROOT    = Path(__file__).resolve().parents[1]
PUB_DIR = ROOT / "Data" / "Publications"
PUB_DIR.mkdir(parents=True, exist_ok=True)
OUT_CSV    = PUB_DIR / "cchen_openalex_works.csv"
STATE_FILE = PUB_DIR / "openalex_state.json"

BASE_URL       = "https://api.openalex.org/works"
CONTACT        = "observatorio@cchen.cl"
INSTITUTION_ID = "I4210133321"
TIMEOUT        = 45
SLEEP          = 0.12
PER_PAGE       = 200

OUTPUT_COLUMNS = [
    "openalex_id", "doi", "title", "year", "type", "source",
    "cited_by_count", "is_oa", "oa_status", "oa_url",
    "pmid", "pmcid", "europmc_url",
]


def _fetch_page(cursor: str, verbose: bool = False) -> dict | None:
    params = {
        "filter":   f"institutions.id:{INSTITUTION_ID},is_paratext:false",
        "select":   "id,doi,title,publication_year,type,primary_location,"
                    "cited_by_count,open_access,ids",
        "per_page": PER_PAGE,
        "cursor":   cursor,
        "mailto":   CONTACT,
    }
    url = f"{BASE_URL}?{urlencode(params)}"
    if verbose:
        print(f"  GET {url[:120]}")
    req = Request(url, headers={
        "User-Agent": f"CCHEN-Observatory/1.0 (mailto:{CONTACT})",
        "Accept":     "application/json",
    })
    try:
        with urlopen(req, timeout=TIMEOUT) as r:
            return json.load(r)
    except HTTPError as e:
        if verbose:
            print(f"  HTTP {e.code}: {e.reason}")
        if e.code == 429:
            print("  Rate limit — esperando 30s...")
            time.sleep(30)
        return None
    except Exception as exc:
        if verbose:
            print(f"  Error: {exc}")
        return None


def _normalize(work: dict) -> dict:
    today = datetime.date.today().isoformat()

    loc    = work.get("primary_location") or {}
    source = (loc.get("source") or {}).get("display_name", "")
    oa     = work.get("open_access") or {}
    ids    = work.get("ids") or {}

    doi = (work.get("doi") or "").replace("https://doi.org/", "").lower().strip()

    # pmid / pmcid desde ids
    pmid  = str(ids.get("pmid", "")).replace("https://pubmed.ncbi.nlm.nih.gov/", "").strip() or ""
    pmcid = str(ids.get("pmcid", "") or "").strip()

    europmc_url = f"https://europepmc.org/abstract/MED/{pmid}" if pmid else ""

    return {
        "openalex_id":   work.get("id", ""),
        "doi":           doi,
        "title":         (work.get("title") or "").strip(),
        "year":          work.get("publication_year"),
        "type":          work.get("type", ""),
        "source":        source,
        "cited_by_count": work.get("cited_by_count", 0),
        "is_oa":         oa.get("is_oa"),
        "oa_status":     oa.get("oa_status", ""),
        "oa_url":        oa.get("oa_url", ""),
        "pmid":          pmid,
        "pmcid":         pmcid,
        "europmc_url":   europmc_url,
    }


def _load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {}


def _save_state(state: dict) -> None:
    state["updated"] = datetime.datetime.now().isoformat()
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="OpenAlex — CCHEN Observatory")
    parser.add_argument("--reset",   action="store_true", help="Forzar re-descarga completa")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    if args.reset and STATE_FILE.exists():
        STATE_FILE.unlink()

    cursor  = "*"
    rows: list[dict] = []
    page = 0
    total_api = 0

    print(f"Descargando publicaciones CCHEN desde OpenAlex (institution: {INSTITUTION_ID})...")

    while cursor:
        data = _fetch_page(cursor, verbose=args.verbose)
        if not data:
            print("  Error al obtener página — abortando.")
            break

        if page == 0:
            total_api = int((data.get("meta") or {}).get("count", 0))
            print(f"  Total reportado por OpenAlex: {total_api}")

        results = data.get("results", [])
        if not results:
            break

        for work in results:
            rows.append(_normalize(work))

        page += 1
        print(f"  Página {page}: {len(results)} works (acum: {len(rows)})")

        cursor = (data.get("meta") or {}).get("next_cursor")
        if cursor:
            time.sleep(SLEEP)

    if not rows:
        print("Sin resultados.")
        return

    df = pd.DataFrame(rows, columns=OUTPUT_COLUMNS)
    df["year"]           = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
    df["cited_by_count"] = pd.to_numeric(df["cited_by_count"], errors="coerce").fillna(0).astype(int)
    df["doi"]            = df["doi"].fillna("").str.strip()
    df["title"]          = df["title"].fillna("").str.strip()

    # Deduplicar: primero por openalex_id, luego por doi
    df = df.drop_duplicates(subset=["openalex_id"], keep="first")
    with_doi    = df[df["doi"].ne("")].drop_duplicates(subset=["doi"], keep="first")
    without_doi = df[df["doi"].eq("")]
    df = pd.concat([with_doi, without_doi], ignore_index=True)
    df = df.sort_values(["year", "cited_by_count"], ascending=[False, False], na_position="last")

    df.to_csv(OUT_CSV, index=False)

    _save_state({"total_works": len(df), "openalex_total": total_api})
    _print_summary(df)


def _print_summary(df: pd.DataFrame) -> None:
    print("\n-- Resumen --------------------------------------------------")
    print(f"Total publicaciones OpenAlex: {len(df)}")
    print(f"Con DOI:      {df['doi'].ne('').sum()}")
    print(f"Con PMID:     {df['pmid'].fillna('').ne('').sum()}")
    print(f"Open Access:  {df['is_oa'].eq(True).sum()}")
    y = df["year"].dropna()
    if not y.empty:
        print(f"Rango de años: {int(y.min())} – {int(y.max())}")
    top_types = df["type"].value_counts().head(5)
    print(f"Top tipos: {', '.join(f'{t} ({n})' for t,n in top_types.items())}")
    print(f"Guardado en: {OUT_CSV}")
    print("\nMuestra (5 más recientes):")
    for _, r in df.nlargest(5, "year").iterrows():
        print(f"  [{r['year']}] {str(r['title'])[:65]} — {r['source']}")


if __name__ == "__main__":
    main()
