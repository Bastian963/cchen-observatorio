#!/usr/bin/env python3
"""
fetch_europmc.py — Observatorio CCHEN 360°
==========================================
Descarga publicaciones CCHEN desde EuroPMC (PubMed + PMC + preprints bioRxiv).

EuroPMC indexa principalmente literatura biomédica/ciencias de la vida,
lo que cubre radiofarmacia, medicina nuclear, dosimetría médica y biofísica.

API: https://www.ebi.ac.uk/europepmc/webservices/rest/search
Sin API key. Rate limit: ~10 req/s.

Salidas:
  Data/Publications/cchen_europmc_works.csv
  Data/Publications/europmc_state.json

Uso:
    python3 Scripts/fetch_europmc.py
    python3 Scripts/fetch_europmc.py --limit 200
    python3 Scripts/fetch_europmc.py --reset
    python3 Scripts/fetch_europmc.py --verbose
"""
from __future__ import annotations

import argparse
import datetime
import json
import time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from urllib.parse import urlencode, quote

import pandas as pd

ROOT    = Path(__file__).resolve().parents[1]
PUB_DIR = ROOT / "Data" / "Publications"
PUB_DIR.mkdir(parents=True, exist_ok=True)
OUT_CSV    = PUB_DIR / "cchen_europmc_works.csv"
STATE_FILE = PUB_DIR / "europmc_state.json"

BASE_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
CONTACT  = "observatory@cchen.cl"
TIMEOUT  = 20
SLEEP    = 0.5  # EuroPMC allows faster rate

OUTPUT_COLUMNS = [
    "source_id", "doi", "pmid", "pmcid",
    "title", "authors", "journal",
    "year", "pub_date",
    "cited_by_count", "is_open_access",
    "abstract_available", "source",
    "keywords", "affiliation_raw",
    "europmc_url", "fetched_at",
]

# Queries para encontrar publicaciones CCHEN
# EuroPMC soporta lucene syntax
SEARCH_QUERIES = [
    'AFF:"Comision Chilena de Energia Nuclear"',
    'AFF:"Comisión Chilena de Energía Nuclear"',
    'AFF:"Chilean Nuclear Energy Commission"',
    'AFF:"CCHEN" AND AFF:Chile AND (nuclear OR radiation OR radiopharmaceutical OR dosimetry OR radioisotope OR neutron OR reactor)',
]


def _fetch_page(query: str, page: int = 1, page_size: int = 100,
                cursor: str = "*", verbose: bool = False) -> dict | None:
    """Consulta EuroPMC REST API con cursor-based pagination."""
    params = {
        "query": query,
        "format": "json",
        "pageSize": page_size,
        "cursorMark": cursor,
        "resultType": "core",
    }
    url = f"{BASE_URL}?{urlencode(params)}"
    if verbose:
        print(f"  GET {url[:100]}")
    req = Request(url, headers={
        "User-Agent": f"CCHEN-Observatory/1.0 (mailto:{CONTACT})",
        "Accept": "application/json",
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


def _normalize(result: dict) -> dict:
    today = datetime.date.today().isoformat()
    # Extract authors
    author_list = result.get("authorList", {}).get("author", [])
    if isinstance(author_list, list):
        authors = "; ".join(
            f"{a.get('lastName','')} {a.get('initials','')}"
            for a in author_list[:10]
        ).strip()
    else:
        authors = ""

    # Extract affiliations from author list
    aff_raw = ""
    for a in (author_list if isinstance(author_list, list) else []):
        affs = a.get("affiliationInfo", [])
        if isinstance(affs, list) and affs:
            aff_raw = affs[0].get("affiliation", "") if isinstance(affs[0], dict) else str(affs[0])
            break

    # Keywords
    kw_list = result.get("keywordList", {}).get("keyword", [])
    keywords = "; ".join(kw_list[:8]) if isinstance(kw_list, list) else ""

    source_id = f"{result.get('source','')}{result.get('id','')}"
    pmid = str(result.get("pmid", ""))
    pmcid = str(result.get("pmcid", ""))
    doi = result.get("doi", "")
    europmc_url = f"https://europepmc.org/article/{result.get('source','')}/{result.get('id','')}"

    return {
        "source_id":          source_id,
        "doi":                doi,
        "pmid":               pmid,
        "pmcid":              pmcid,
        "title":              result.get("title", "").rstrip("."),
        "authors":            authors,
        "journal":            result.get("journalTitle", ""),
        "year":               result.get("pubYear", ""),
        "pub_date":           result.get("firstPublicationDate", ""),
        "cited_by_count":     result.get("citedByCount", 0),
        "is_open_access":     result.get("isOpenAccess", "N"),
        "abstract_available": "Y" if result.get("abstractText") else "N",
        "source":             result.get("source", ""),
        "keywords":           keywords,
        "affiliation_raw":    aff_raw[:300],
        "europmc_url":        europmc_url,
        "fetched_at":         today,
    }


def _load_state() -> set[str]:
    if STATE_FILE.exists():
        return set(json.loads(STATE_FILE.read_text()).get("processed_queries", []))
    return set()


def _save_state(processed: set[str]) -> None:
    STATE_FILE.write_text(json.dumps(
        {"processed_queries": sorted(processed),
         "updated": datetime.datetime.now().isoformat()},
        ensure_ascii=False, indent=2
    ))


def _flush(rows: list[dict]) -> None:
    if not rows:
        return
    new_df = pd.DataFrame(rows, columns=OUTPUT_COLUMNS)
    if OUT_CSV.exists():
        old_df = pd.read_csv(OUT_CSV)
        new_df = pd.concat([old_df, new_df]).drop_duplicates(
            subset=["source_id"], keep="last"
        )
    new_df.to_csv(OUT_CSV, index=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="EuroPMC — CCHEN Observatory")
    parser.add_argument("--limit",   type=int, default=0, help="Límite de resultados por query")
    parser.add_argument("--reset",   action="store_true", help="Ignorar cache de queries procesadas")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    processed = set() if args.reset else _load_state()
    all_rows: list[dict] = []
    total_found = 0

    for qi, query in enumerate(SEARCH_QUERIES, 1):
        if query in processed:
            print(f"[{qi}/{len(SEARCH_QUERIES)}] Skipping (ya procesada): {query[:70]}")
            continue

        print(f"\n[{qi}/{len(SEARCH_QUERIES)}] Query: {query[:70]}")
        cursor = "*"
        page = 0
        q_found = 0

        while True:
            data = _fetch_page(query, page=page+1, cursor=cursor, verbose=args.verbose)
            if not data:
                break

            results = data.get("resultList", {}).get("result", [])
            if not results:
                break

            for res in results:
                row = _normalize(res)
                all_rows.append(row)
                q_found += 1
                if args.verbose:
                    print(f"  + {row['year']} | {row['title'][:60]}")

            total_found += len(results)
            print(f"  Página {page+1}: {len(results)} resultados (total acum: {total_found})")

            # Cursor pagination
            next_cursor = data.get("nextCursorMark", "")
            if not next_cursor or next_cursor == cursor:
                break
            cursor = next_cursor
            page += 1

            if args.limit > 0 and q_found >= args.limit:
                break

            time.sleep(SLEEP)

        print(f"  -> Query completada: {q_found} papers encontrados")
        processed.add(query)
        time.sleep(SLEEP)

    _flush(all_rows)
    _save_state(processed)

    # Garantizar CSV (aunque vacío)
    if not OUT_CSV.exists():
        pd.DataFrame(columns=OUTPUT_COLUMNS).to_csv(OUT_CSV, index=False)

    _print_summary()


def _print_summary() -> None:
    print("\n-- Resumen --------------------------------------------------")
    if not OUT_CSV.exists() or pd.read_csv(OUT_CSV).empty:
        print("Sin publicaciones EuroPMC encontradas.")
        return
    df = pd.read_csv(OUT_CSV)
    print(f"Total publicaciones EuroPMC: {len(df)}")
    print(f"Con DOI: {df['doi'].ne('').sum()}")
    print(f"Open Access: {(df['is_open_access']=='Y').sum()}")
    if "year" in df.columns:
        df["year"] = pd.to_numeric(df["year"], errors="coerce")
        print(f"Rango de años: {int(df['year'].min())} – {int(df['year'].max())}")
    print(f"Guardado en: {OUT_CSV}")
    if len(df) > 0:
        print("\nMuestra (5 más recientes):")
        for _, r in df.nlargest(5, "year").iterrows():
            print(f"  [{r['year']}] {str(r['title'])[:70]} — {r['journal']}")


if __name__ == "__main__":
    main()
