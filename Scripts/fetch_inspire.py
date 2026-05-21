#!/usr/bin/env python3
"""
fetch_inspire.py — Observatorio CCHEN 360°
==========================================
Descarga publicaciones CCHEN desde INSPIRE-HEP.

INSPIRE indexa física de alta energía, física nuclear, instrumentación y
ciencias relacionadas. Es fuente secundaria para CCHEN: la institución
publica principalmente en journals de física aplicada/médica (PubMed,
EuroPMC), no en HEP. Útil si CCHEN amplía colaboraciones en física nuclear
fundamental o de reactores avanzados.

CCHEN institution ID en INSPIRE: 1607622

API: https://inspirehep.net/api/literature
Sin API key. Rate limit: ~10 req/s (respetar 1 req/s para queries pesadas).

Salidas:
  Data/Publications/cchen_inspire_works.csv
  Data/Publications/inspire_state.json

Uso:
    python3 Scripts/fetch_inspire.py
    python3 Scripts/fetch_inspire.py --limit 200
    python3 Scripts/fetch_inspire.py --reset
    python3 Scripts/fetch_inspire.py --verbose
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

import pandas as pd

ROOT    = Path(__file__).resolve().parents[1]
PUB_DIR = ROOT / "Data" / "Publications"
PUB_DIR.mkdir(parents=True, exist_ok=True)
OUT_CSV    = PUB_DIR / "cchen_inspire_works.csv"
STATE_FILE = PUB_DIR / "inspire_state.json"

BASE_URL = "https://inspirehep.net/api/literature"
CONTACT  = "observatory@cchen.cl"
TIMEOUT  = 30
SLEEP    = 1.0   # conservador para no saturar INSPIRE
PAGE_SIZE = 25   # máximo estable sin cursor; para >1000 usar link pagination

OUTPUT_COLUMNS = [
    "inspire_id", "arxiv_id", "doi",
    "title", "authors", "journal",
    "year", "pub_date",
    "abstract", "keywords",
    "citation_count", "document_type",
    "inspire_categories", "affiliation_raw",
    "inspire_url", "fetched_at",
]

# Queries INSPIRE usan sintaxis Lucene/SPIRES
# aff = affiliation, cn = collaboration name, a = author
CCHEN_INSPIRE_ID = "1607622"  # ID oficial institución en INSPIRE

# INSPIRE indexa 16-19 papers con "CCHEN, Santiago" como afiliación
# (física nuclear estructural: decaimiento beta, isóbaros, radioactividad de protones)
# El operador aff: no funciona para CCHEN — usar búsqueda de texto libre.
SEARCH_QUERIES = [
    "CCHEN",                                     # texto libre — captura "CCHEN, Santiago"
    '"Comision Chilena de Energia Nuclear"',      # nombre completo sin acentos
    '"Chilean Nuclear Energy Commission"',
]


def _fetch_page(query: str, page: int = 1, size: int = PAGE_SIZE,
                verbose: bool = False) -> dict | None:
    """Consulta INSPIRE API con paginación por página."""
    params = {
        "q":    query,
        "sort": "mostrecent",
        "size": size,
        "page": page,
        "fields": "arxiv_eprints,authors,dois,titles,abstracts,publication_info,"
                  "keywords,inspire_categories,citation_count,document_type,id",
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
        return None
    except Exception as exc:
        if verbose:
            print(f"  Error: {exc}")
        return None


def _normalize(hit: dict) -> dict:
    today    = datetime.date.today().isoformat()
    meta     = hit.get("metadata", {})
    inspire_id = str(hit.get("id", ""))

    # arXiv IDs
    arxiv_eprints = meta.get("arxiv_eprints", [])
    arxiv_id = arxiv_eprints[0].get("value", "") if arxiv_eprints else ""

    # DOIs
    dois = meta.get("dois", [])
    doi  = dois[0].get("value", "") if dois else ""

    # Titles
    titles = meta.get("titles", [])
    title  = titles[0].get("title", "") if titles else ""

    # Abstracts
    abstracts = meta.get("abstracts", [])
    abstract  = abstracts[0].get("value", "") if abstracts else ""

    # Authors + affiliation
    authors_list = []
    aff_raw = ""
    for au in meta.get("authors", [])[:10]:
        full = au.get("full_name", "")
        if full:
            authors_list.append(full)
        if not aff_raw:
            raw_affs = au.get("raw_affiliations", [])
            if raw_affs:
                aff_raw = raw_affs[0].get("value", "")[:300]

    # Publication info (journal, year)
    pub_info = meta.get("publication_info", [{}])
    journal  = pub_info[0].get("journal_title", "") if pub_info else ""
    year     = str(pub_info[0].get("year", "")) if pub_info else ""
    pub_date = year

    # Keywords
    kws = [kw.get("value", "") for kw in meta.get("keywords", [])[:10] if kw.get("value")]
    keywords = "; ".join(kws)

    # Categories
    cats = [c.get("term", "") for c in meta.get("inspire_categories", []) if c.get("term")]
    inspire_cats = "; ".join(cats)

    doc_types = meta.get("document_type", [])
    doc_type  = "; ".join(doc_types) if isinstance(doc_types, list) else str(doc_types)

    return {
        "inspire_id":          inspire_id,
        "arxiv_id":            arxiv_id,
        "doi":                 doi,
        "title":               title,
        "authors":             "; ".join(authors_list),
        "journal":             journal,
        "year":                year,
        "pub_date":            pub_date,
        "abstract":            abstract[:2000],
        "keywords":            keywords,
        "citation_count":      meta.get("citation_count", 0),
        "document_type":       doc_type,
        "inspire_categories":  inspire_cats,
        "affiliation_raw":     aff_raw,
        "inspire_url":         f"https://inspirehep.net/literature/{inspire_id}",
        "fetched_at":          today,
    }


def _load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"processed_queries": [], "fetched_ids": []}


def _save_state(state: dict) -> None:
    state["updated"] = datetime.datetime.now().isoformat()
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2))


def _flush(rows: list[dict]) -> None:
    if not rows:
        return
    new_df = pd.DataFrame(rows, columns=OUTPUT_COLUMNS)
    if OUT_CSV.exists():
        old_df = pd.read_csv(OUT_CSV, dtype=str)
        new_df = pd.concat([old_df, new_df]).drop_duplicates(
            subset=["inspire_id"], keep="last"
        )
    new_df.to_csv(OUT_CSV, index=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="INSPIRE-HEP — CCHEN Observatory")
    parser.add_argument("--limit",   type=int, default=0)
    parser.add_argument("--reset",   action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    state = {"processed_queries": [], "fetched_ids": []} if args.reset else _load_state()
    processed = set(state.get("processed_queries", []))
    fetched   = set(state.get("fetched_ids", []))
    all_rows: list[dict] = []
    total_new = 0

    for qi, query in enumerate(SEARCH_QUERIES, 1):
        if query in processed:
            print(f"[{qi}/{len(SEARCH_QUERIES)}] Skipping (ya procesada): {query}")
            continue

        print(f"\n[{qi}/{len(SEARCH_QUERIES)}] Query: {query}")
        page = 1
        q_found = 0

        while True:
            data = _fetch_page(query, page=page, verbose=args.verbose)
            if not data:
                break

            hits  = data.get("hits", {})
            raw_total = hits.get("total", 0)
            total = raw_total.get("value", 0) if isinstance(raw_total, dict) else int(raw_total or 0)
            items = hits.get("hits", [])
            if not items:
                break

            for hit in items:
                inspire_id = str(hit.get("id", ""))
                if inspire_id in fetched:
                    continue
                row = _normalize(hit)
                all_rows.append(row)
                fetched.add(inspire_id)
                q_found += 1
                total_new += 1

            print(f"  Página {page}: {len(items)} resultados (total query: {total}, nuevos acum: {total_new})")

            if len(items) < PAGE_SIZE:
                break
            if args.limit > 0 and q_found >= args.limit:
                break
            page += 1
            time.sleep(SLEEP)

        processed.add(query)
        time.sleep(SLEEP)

    _flush(all_rows)
    _save_state({
        "processed_queries": sorted(processed),
        "fetched_ids":       sorted(fetched),
    })

    if not OUT_CSV.exists():
        pd.DataFrame(columns=OUTPUT_COLUMNS).to_csv(OUT_CSV, index=False)

    _print_summary()


def _print_summary() -> None:
    print("\n-- Resumen --------------------------------------------------")
    if not OUT_CSV.exists():
        print("Sin datos INSPIRE."); return
    df = pd.read_csv(OUT_CSV)
    if df.empty:
        print("Sin publicaciones INSPIRE encontradas."); return
    print(f"Total publicaciones INSPIRE: {len(df)}")
    print(f"Con DOI:      {df['doi'].fillna('').ne('').sum()}")
    print(f"Con arXiv:    {df['arxiv_id'].fillna('').ne('').sum()}")
    print(f"Con abstract: {df['abstract'].fillna('').ne('').sum()}")
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    vy = df["year"].dropna()
    if not vy.empty:
        print(f"Rango de años: {int(vy.min())} – {int(vy.max())}")
    if "inspire_categories" in df.columns:
        cats = df["inspire_categories"].fillna("").str.split(";").explode().str.strip()
        top = cats[cats != ""].value_counts().head(5)
        if not top.empty:
            print(f"Top categorías INSPIRE: {', '.join(top.index.tolist())}")
    print(f"Guardado en: {OUT_CSV}")
    print("\nMuestra (5 más recientes):")
    for _, r in df.nlargest(5, "year").iterrows():
        print(f"  [{r['year']}] {str(r['title'])[:70]} — {r['journal']}")


if __name__ == "__main__":
    main()
