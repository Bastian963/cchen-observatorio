#!/usr/bin/env python3
"""
fetch_crossref.py — Observatorio CCHEN 360°
============================================
Enriquece publicaciones CCHEN con datos de CrossRef:
financiadores externos, conteo de referencias, abstract, licencia,
editorial y áreas temáticas.

Requiere: Data/Publications/cchen_openalex_works.csv (generado por fetch_openalex.py)

API: https://api.crossref.org  (sin API key; polite pool con mailto)
Rate limit: ~8 req/s — se usa 0.12s entre requests.

Salidas:
  Data/Publications/cchen_crossref_enriched.csv
  Data/Publications/crossref_state.json

Uso:
    python3 Scripts/fetch_crossref.py
    python3 Scripts/fetch_crossref.py --reset
    python3 Scripts/fetch_crossref.py --limit 200
    python3 Scripts/fetch_crossref.py --verbose
"""
from __future__ import annotations

import argparse
import datetime
import json
import re
import time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

import pandas as pd

ROOT    = Path(__file__).resolve().parents[1]
PUB_DIR = ROOT / "Data" / "Publications"
PUB_DIR.mkdir(parents=True, exist_ok=True)
SRC_CSV    = PUB_DIR / "cchen_openalex_works.csv"
OUT_CSV    = PUB_DIR / "cchen_crossref_enriched.csv"
STATE_FILE = PUB_DIR / "crossref_state.json"

BASE_URL = "https://api.crossref.org/works"
CONTACT  = "observatorio@cchen.cl"
TIMEOUT  = 15
SLEEP    = 0.12
SLEEP_429 = 60.0

OUTPUT_COLUMNS = [
    "doi", "crossref_funders", "crossref_funder_doi",
    "references_count", "cited_by_crossref",
    "abstract", "license_url", "publisher", "subject",
]


def _fetch_doi(doi: str, verbose: bool = False) -> dict | None:
    url = f"{BASE_URL}/{doi}?mailto={CONTACT}"
    req = Request(url, headers={
        "User-Agent": f"CCHEN-Observatory/1.0 (mailto:{CONTACT})",
        "Accept":     "application/json",
    })
    try:
        with urlopen(req, timeout=TIMEOUT) as r:
            data = json.load(r)
        return data.get("message", {})
    except HTTPError as e:
        if e.code == 429:
            print(f"  Rate limit (429) — esperando {SLEEP_429}s...")
            time.sleep(SLEEP_429)
            try:
                with urlopen(req, timeout=TIMEOUT) as r:
                    return json.load(r).get("message", {})
            except Exception:
                pass
        if e.code == 404:
            return {}  # DOI no indexado en CrossRef — resultado vacío
        if verbose:
            print(f"  HTTP {e.code} para {doi}: {e.reason}")
        return None
    except Exception as exc:
        if verbose:
            print(f"  Error para {doi}: {exc}")
        return None


def _normalize(doi: str, msg: dict) -> dict:
    if not msg:
        return {"doi": doi}

    funders = "; ".join(
        f.get("name", "") for f in (msg.get("funder") or []) if f.get("name")
    )
    funder_dois = "; ".join(
        f.get("DOI", "") for f in (msg.get("funder") or []) if f.get("DOI")
    )

    abstract = msg.get("abstract", "") or ""
    abstract = re.sub(r"<[^>]+>", "", abstract).strip()[:2000]

    license_url = ""
    for lic in (msg.get("license") or []):
        if lic.get("URL"):
            license_url = lic["URL"]
            break

    subjects = "; ".join(msg.get("subject") or [])

    return {
        "doi":                doi,
        "crossref_funders":   funders,
        "crossref_funder_doi": funder_dois,
        "references_count":   msg.get("references-count", 0),
        "cited_by_crossref":  msg.get("is-referenced-by-count", 0),
        "abstract":           abstract,
        "license_url":        license_url,
        "publisher":          msg.get("publisher", ""),
        "subject":            subjects,
    }


def _load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"processed_dois": []}


def _save_state(state: dict) -> None:
    state["updated"] = datetime.datetime.now().isoformat()
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2))


def _flush(rows: list[dict]) -> None:
    if not rows:
        return
    new_df = pd.DataFrame(rows, columns=OUTPUT_COLUMNS)
    if OUT_CSV.exists():
        old_df = pd.read_csv(OUT_CSV, dtype=str)
        new_df = pd.concat([old_df, new_df]).drop_duplicates(subset=["doi"], keep="last")
    new_df.to_csv(OUT_CSV, index=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="CrossRef enrichment — CCHEN Observatory")
    parser.add_argument("--limit",   type=int, default=0)
    parser.add_argument("--reset",   action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    if not SRC_CSV.exists():
        print(f"[ERROR] {SRC_CSV} no encontrado. Ejecuta primero fetch_openalex.py")
        return

    df_src = pd.read_csv(SRC_CSV)
    all_dois = df_src["doi"].dropna().str.strip().str.lower()
    all_dois = all_dois[all_dois.ne("")].drop_duplicates().tolist()
    print(f"DOIs disponibles en OpenAlex CSV: {len(all_dois)}")

    state = {"processed_dois": []} if args.reset else _load_state()
    if args.reset and OUT_CSV.exists():
        OUT_CSV.unlink()

    processed = set(state.get("processed_dois", []))
    pending   = [d for d in all_dois if d not in processed]

    if args.limit > 0:
        pending = pending[:args.limit]

    print(f"DOIs ya procesados: {len(processed)} | pendientes: {len(pending)}")

    rows: list[dict] = []
    errors = 0

    for i, doi in enumerate(pending, 1):
        msg = _fetch_doi(doi, verbose=args.verbose)
        if msg is None:
            errors += 1
            processed.add(doi)
            continue

        row = _normalize(doi, msg)
        rows.append(row)
        processed.add(doi)

        if i % 100 == 0:
            _flush(rows)
            rows = []
            _save_state({"processed_dois": sorted(processed)})
            print(f"  {i}/{len(pending)} procesados (errores: {errors})", flush=True)
        else:
            time.sleep(SLEEP)

    _flush(rows)
    _save_state({"processed_dois": sorted(processed)})

    if not OUT_CSV.exists():
        pd.DataFrame(columns=OUTPUT_COLUMNS).to_csv(OUT_CSV, index=False)

    _print_summary()


def _print_summary() -> None:
    print("\n-- Resumen --------------------------------------------------")
    if not OUT_CSV.exists():
        print("Sin datos CrossRef."); return
    df = pd.read_csv(OUT_CSV)
    if df.empty:
        print("Sin registros CrossRef."); return
    print(f"Total registros CrossRef: {len(df)}")
    print(f"Con financiadores: {df['crossref_funders'].fillna('').ne('').sum()}")
    print(f"Con abstract:      {df['abstract'].fillna('').ne('').sum()}")
    print(f"Con referencias:   {(pd.to_numeric(df['references_count'], errors='coerce') > 0).sum()}")

    top_funders = (
        df["crossref_funders"].dropna()
        .str.split("; ").explode().str.strip()
        .pipe(lambda s: s[s.ne("")].value_counts().head(5))
    )
    if not top_funders.empty:
        print(f"Top financiadores: {', '.join(top_funders.index.tolist())}")
    print(f"Guardado en: {OUT_CSV}")


if __name__ == "__main__":
    main()
