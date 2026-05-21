#!/usr/bin/env python3
"""
fetch_arxiv.py — Observatorio CCHEN 360°
=========================================
Descarga preprints CCHEN desde arXiv vía API Atom.

arXiv publica preprints 6–12 meses antes de la versión final en revista.
Permite a CCHEN monitorear tendencias emergentes en física nuclear, medicina
nuclear, dosimetría y ciencias relacionadas antes de su indexación formal.

API: https://export.arxiv.org/api/query (Atom/XML, sin API key)
Rate limit recomendado: 1 req / 3s.

Salidas:
  Data/Publications/cchen_arxiv_works.csv
  Data/Publications/arxiv_state.json

Uso:
    python3 Scripts/fetch_arxiv.py
    python3 Scripts/fetch_arxiv.py --limit 100
    python3 Scripts/fetch_arxiv.py --reset
    python3 Scripts/fetch_arxiv.py --verbose
"""
from __future__ import annotations

import argparse
import datetime
import json
import re
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from urllib.parse import urlencode

import pandas as pd

ROOT    = Path(__file__).resolve().parents[1]
PUB_DIR = ROOT / "Data" / "Publications"
PUB_DIR.mkdir(parents=True, exist_ok=True)
OUT_CSV    = PUB_DIR / "cchen_arxiv_works.csv"
STATE_FILE = PUB_DIR / "arxiv_state.json"

BASE_URL  = "https://export.arxiv.org/api/query"
CONTACT   = "observatory@cchen.cl"
TIMEOUT   = 30
SLEEP     = 4.0   # arXiv pide explícitamente ≥ 3s entre requests; 4s por seguridad
SLEEP_429 = 60.0  # espera tras HTTP 429
MAX_BATCH = 100   # max resultados por request arXiv

NS = {
    "atom":   "http://www.w3.org/2005/Atom",
    "arxiv":  "http://arxiv.org/schemas/atom",
    "opensearch": "http://a9.com/-/spec/opensearch/1.1/",
}

OUTPUT_COLUMNS = [
    "arxiv_id", "doi",
    "title", "authors", "categories",
    "year", "pub_date", "updated_date",
    "abstract", "primary_category",
    "journal_ref", "comment",
    "arxiv_url", "fetched_at",
]

# arXiv soporta búsqueda por afiliación en el campo all:
# Las queries se escapan automáticamente vía urlencode
SEARCH_QUERIES = [
    'all:"Comision Chilena de Energia Nuclear"',
    'all:"Chilean Nuclear Energy Commission"',
    'all:CCHEN AND all:Chile AND all:nuclear',
    'cat:physics.med-ph AND all:Chile',
]


def _fetch_page(query: str, start: int = 0, max_results: int = MAX_BATCH,
                verbose: bool = False) -> ET.Element | None:
    """Descarga una página de resultados arXiv (formato Atom XML)."""
    params = {
        "search_query": query,
        "start":        start,
        "max_results":  max_results,
        "sortBy":       "submittedDate",
        "sortOrder":    "descending",
    }
    url = f"{BASE_URL}?{urlencode(params)}"
    if verbose:
        print(f"  GET {url[:120]}")
    req = Request(url, headers={
        "User-Agent": f"CCHEN-Observatory/1.0 (mailto:{CONTACT})",
        "Accept":     "application/atom+xml",
    })
    try:
        with urlopen(req, timeout=TIMEOUT) as r:
            raw = r.read()
        root = ET.fromstring(raw)
        return root
    except HTTPError as e:
        if e.code == 429:
            print(f"  Rate limit (429) — esperando {SLEEP_429}s...")
            time.sleep(SLEEP_429)
            # un reintento
            try:
                with urlopen(req, timeout=TIMEOUT) as r:
                    raw = r.read()
                return ET.fromstring(raw)
            except Exception:
                pass
        if verbose:
            print(f"  HTTP {e.code}: {e.reason}")
        return None
    except Exception as exc:
        if verbose:
            print(f"  Error: {exc}")
        return None


def _get_total(root: ET.Element) -> int:
    el = root.find("opensearch:totalResults", NS)
    try:
        return int(el.text) if el is not None else 0
    except (TypeError, ValueError):
        return 0


def _normalize(entry: ET.Element) -> dict:
    today = datetime.date.today().isoformat()

    # arXiv ID from <id> — formato: http://arxiv.org/abs/XXXX.XXXXXX
    id_el  = entry.find("atom:id", NS)
    raw_id = (id_el.text or "").strip() if id_el is not None else ""
    arxiv_id = raw_id.split("/abs/")[-1].replace("v1","").strip() if "/abs/" in raw_id else raw_id

    # DOI
    doi_el = entry.find("arxiv:doi", NS)
    doi    = (doi_el.text or "").strip() if doi_el is not None else ""

    # Title
    title_el = entry.find("atom:title", NS)
    title = " ".join((title_el.text or "").split()) if title_el is not None else ""

    # Abstract
    summary_el = entry.find("atom:summary", NS)
    abstract   = " ".join((summary_el.text or "").split()) if summary_el is not None else ""

    # Authors
    authors = []
    for au in entry.findall("atom:author", NS):
        name_el = au.find("atom:name", NS)
        if name_el is not None and name_el.text:
            authors.append(name_el.text.strip())

    # Dates
    pub_el     = entry.find("atom:published", NS)
    upd_el     = entry.find("atom:updated", NS)
    pub_date   = (pub_el.text or "")[:10] if pub_el is not None else ""
    upd_date   = (upd_el.text or "")[:10] if upd_el is not None else ""
    year       = pub_date[:4]

    # Categories
    primary_cat = ""
    pcat_el = entry.find("arxiv:primary_category", NS)
    if pcat_el is not None:
        primary_cat = pcat_el.get("term", "")

    cats = [c.get("term", "") for c in entry.findall("atom:category", NS) if c.get("term")]
    categories = "; ".join(cats)

    # Journal reference and comment (optional metadata)
    jr_el = entry.find("arxiv:journal_ref", NS)
    journal_ref = (jr_el.text or "").strip() if jr_el is not None else ""

    cm_el   = entry.find("arxiv:comment", NS)
    comment = (cm_el.text or "").strip() if cm_el is not None else ""

    return {
        "arxiv_id":        arxiv_id,
        "doi":             doi,
        "title":           title,
        "authors":         "; ".join(authors[:10]),
        "categories":      categories,
        "year":            year,
        "pub_date":        pub_date,
        "updated_date":    upd_date,
        "abstract":        abstract[:2000],
        "primary_category": primary_cat,
        "journal_ref":     journal_ref,
        "comment":         comment[:300],
        "arxiv_url":       f"https://arxiv.org/abs/{arxiv_id}",
        "fetched_at":      today,
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
            subset=["arxiv_id"], keep="last"
        )
    new_df.to_csv(OUT_CSV, index=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="arXiv — CCHEN Observatory")
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
            print(f"[{qi}/{len(SEARCH_QUERIES)}] Skipping (ya procesada): {query[:70]}")
            continue

        print(f"\n[{qi}/{len(SEARCH_QUERIES)}] Query: {query[:70]}")
        start   = 0
        q_found = 0

        while True:
            root = _fetch_page(query, start=start, verbose=args.verbose)
            if root is None:
                break

            total = _get_total(root)
            entries = root.findall("atom:entry", NS)
            if not entries:
                break

            for entry in entries:
                row       = _normalize(entry)
                arxiv_id  = row.get("arxiv_id", "")
                if not arxiv_id or arxiv_id in fetched:
                    continue
                all_rows.append(row)
                fetched.add(arxiv_id)
                q_found += 1
                total_new += 1

            print(f"  start={start}: {len(entries)} entradas (total: {total}, nuevos acum: {total_new})")

            start += len(entries)
            if start >= total:
                break
            if args.limit > 0 and q_found >= args.limit:
                break

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
        print("Sin datos arXiv."); return
    df = pd.read_csv(OUT_CSV)
    if df.empty:
        print("Sin preprints arXiv encontrados."); return
    print(f"Total preprints arXiv: {len(df)}")
    print(f"Con DOI:       {df['doi'].fillna('').ne('').sum()}")
    print(f"Con journal:   {df['journal_ref'].fillna('').ne('').sum()}")
    print(f"Con abstract:  {df['abstract'].fillna('').ne('').sum()}")
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    vy = df["year"].dropna()
    if not vy.empty:
        print(f"Rango de años: {int(vy.min())} – {int(vy.max())}")
    if "primary_category" in df.columns:
        top = df["primary_category"].fillna("").value_counts().head(5)
        if not top.empty:
            print(f"Top categorías: {', '.join(top.index.tolist())}")
    print(f"Guardado en: {OUT_CSV}")
    print("\nMuestra (5 más recientes):")
    for _, r in df.nlargest(5, "year").iterrows():
        print(f"  [{r['year']}] {str(r['title'])[:70]} — {r.get('primary_category','')}")


if __name__ == "__main__":
    main()
