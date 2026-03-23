#!/usr/bin/env python3
"""
fetch_altmetric.py — Observatorio CCHEN 360°
============================================
Descarga métricas de impacto alternativo (Altmetric) para publicaciones CCHEN.

Altmetric rastrea menciones en:
  - Noticias (news outlets)
  - Twitter/X, Facebook, Reddit
  - Documentos de política pública
  - Wikipedia
  - Mendeley (bookmarks académicos)
  - Blogs científicos

API: https://api.altmetric.com/v1/doi/{doi}
Sin API key: funciona para papers con DOI. Rate limit ~1 req/s.

Salidas:
  Data/Publications/cchen_altmetric.csv
  Data/Publications/altmetric_state.json   (cache de DOIs procesados)

Uso:
    python3 Scripts/fetch_altmetric.py
    python3 Scripts/fetch_altmetric.py --limit 50    # prueba rápida
    python3 Scripts/fetch_altmetric.py --reset       # ignorar cache
    python3 Scripts/fetch_altmetric.py --verbose
"""

from __future__ import annotations

import argparse
import datetime
import json
import time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from urllib.parse import quote

import pandas as pd

ROOT    = Path(__file__).resolve().parents[1]
PUB_DIR = ROOT / "Data" / "Publications"
PUB_DIR.mkdir(parents=True, exist_ok=True)
OUT_CSV    = PUB_DIR / "cchen_altmetric.csv"
STATE_FILE = PUB_DIR / "altmetric_state.json"

ALTMETRIC_BASE = "https://api.altmetric.com/v1"
CONTACT        = "observatory@cchen.cl"
TIMEOUT        = 15
SLEEP          = 1.1   # respetar rate limit (~1 req/s)

OUTPUT_COLUMNS = [
    "doi", "altmetric_id", "altmetric_score",
    "altmetric_score_1y", "altmetric_score_3m",
    "cited_by_posts_count",
    "cited_by_tweeters_count", "cited_by_newsoutlets_count",
    "cited_by_policies_count", "cited_by_wikipedia_count",
    "cited_by_reddits_count", "cited_by_feeds_count",
    "mendeley_readers", "is_oa", "subjects",
    "altmetric_url", "fetched_at",
]


def _fetch_doi(doi: str, verbose: bool = False) -> dict | None:
    """Consulta Altmetric para un DOI. Retorna None si 404 o error."""
    url = f"{ALTMETRIC_BASE}/doi/{quote(doi, safe='/')}"
    if verbose:
        print(f"    GET {url[:80]}")
    req = Request(
        url,
        headers={
            "User-Agent": f"CCHEN-Observatory/1.0 (mailto:{CONTACT})",
            "Accept": "application/json",
        }
    )
    try:
        with urlopen(req, timeout=TIMEOUT) as r:
            return json.load(r)
    except HTTPError as e:
        if e.code == 404:
            return None   # paper sin score — normal
        if e.code == 429:
            print("  Rate limit — esperando 60 s...")
            time.sleep(60)
            return None
        if verbose:
            print(f"    HTTP {e.code}")
        return None
    except Exception as exc:
        if verbose:
            print(f"    {exc}")
        return None


def _normalize(doi: str, data: dict) -> dict:
    today = datetime.date.today().isoformat()
    counts = data.get("cited_by_accounts_count", {})
    if isinstance(counts, int):
        counts = {}

    return {
        "doi":                        doi,
        "altmetric_id":               str(data.get("altmetric_id", "")),
        "altmetric_score":            data.get("score", 0),
        "altmetric_score_1y":         data.get("history", {}).get("1y", 0),
        "altmetric_score_3m":         data.get("history", {}).get("3m", 0),
        "cited_by_posts_count":       data.get("cited_by_posts_count", 0),
        "cited_by_tweeters_count":    data.get("cited_by_tweeters_count", 0),
        "cited_by_newsoutlets_count": data.get("cited_by_msm_count", 0),
        "cited_by_policies_count":    data.get("cited_by_policies_count", 0),
        "cited_by_wikipedia_count":   data.get("cited_by_wikipedia_count", 0),
        "cited_by_reddits_count":     data.get("cited_by_rdts_count", 0),
        "cited_by_feeds_count":       data.get("cited_by_feeds_count", 0),
        "mendeley_readers":           data.get("readers", {}).get("mendeley", 0),
        "is_oa":                      str(data.get("is_oa", "")),
        "subjects":                   "; ".join(data.get("subjects", [])[:5]),
        "altmetric_url":              data.get("details_url", ""),
        "fetched_at":                 today,
    }


def _load_state() -> set[str]:
    if STATE_FILE.exists():
        return set(json.loads(STATE_FILE.read_text()).get("processed_dois", []))
    return set()


def _save_state(processed: set[str]) -> None:
    STATE_FILE.write_text(json.dumps(
        {"processed_dois": sorted(processed),
         "updated": datetime.datetime.now().isoformat()},
        ensure_ascii=False, indent=2
    ))


def _flush(rows: list[dict]) -> None:
    if not rows:
        return
    new_df = pd.DataFrame(rows, columns=OUTPUT_COLUMNS)
    if OUT_CSV.exists():
        old_df = pd.read_csv(OUT_CSV)
        new_df = pd.concat([old_df, new_df]).drop_duplicates(subset=["doi"], keep="last")
    new_df.to_csv(OUT_CSV, index=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Altmetric — CCHEN Observatory")
    parser.add_argument("--limit",   type=int, default=0)
    parser.add_argument("--reset",   action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    # Cargar publicaciones con DOI
    in_csv = PUB_DIR / "cchen_openalex_works.csv"
    if not in_csv.exists():
        print(f"No encontrado: {in_csv}")
        return

    pub = pd.read_csv(in_csv).fillna("")
    if "doi" not in pub.columns:
        print("Columna 'doi' no encontrada en publicaciones.")
        return

    dois = pub["doi"].dropna().str.strip().str.lower()
    dois = dois[dois.str.startswith("10.")].unique().tolist()
    print(f"DOIs disponibles: {len(dois)}")

    processed = set() if args.reset else _load_state()
    pending   = [d for d in dois if d not in processed]
    if args.limit > 0:
        pending = pending[:args.limit]

    print(f"Ya procesados: {len(processed)} | Pendientes: {len(pending)}")
    if not pending:
        print("Nada que procesar.")
        _print_summary()
        return

    rows: list[dict] = []
    n_found = 0

    for i, doi in enumerate(pending, 1):
        print(f"[{i:4d}/{len(pending)}] {doi[:40]:<40s}", end="  ")
        data = _fetch_doi(doi, args.verbose)

        if data:
            rec = _normalize(doi, data)
            rows.append(rec)
            n_found += 1
            score = rec["altmetric_score"]
            news  = rec["cited_by_newsoutlets_count"]
            pol   = rec["cited_by_policies_count"]
            print(f"score={score:.1f} | noticias={news} | policy={pol}")
        else:
            print("sin score")

        processed.add(doi)

        if i % 50 == 0:
            _flush(rows)
            rows = []
            _save_state(processed)
            print(f"  -> Guardado parcial ({i} procesados, {n_found} con score)")

        time.sleep(SLEEP)

    _flush(rows)
    _save_state(processed)
    # Garantizar que el CSV siempre exista (aunque esté vacío) para que data_loader no falle
    if not OUT_CSV.exists():
        pd.DataFrame(columns=OUTPUT_COLUMNS).to_csv(OUT_CSV, index=False)
    _print_summary()


def _print_summary() -> None:
    print("\n-- Resumen --------------------------------------------------")
    if not OUT_CSV.exists():
        print("Sin datos — CSV no generado.")
        return
    df = pd.read_csv(OUT_CSV)
    if df.empty:
        print("Procesamiento completado: 0 papers con score Altmetric.")
        print("Esto confirma que las publicaciones CCHEN no tienen presencia")
        print("medible en medios/redes sociales/política pública vía Altmetric.")
        return
    print(f"Total con score Altmetric: {len(df)}")
    print(f"Score maximo: {df['altmetric_score'].max():.1f}")
    print(f"Con menciones en noticias: {(df['cited_by_newsoutlets_count'] > 0).sum()}")
    print(f"En documentos de politica: {(df['cited_by_policies_count'] > 0).sum()}")
    print(f"En Wikipedia: {(df['cited_by_wikipedia_count'] > 0).sum()}")
    if len(df) > 0:
        top5 = df.nlargest(5, "altmetric_score")[["doi", "altmetric_score", "cited_by_newsoutlets_count"]]
        print("\nTop 5 por score Altmetric:")
        for _, row in top5.iterrows():
            print(f"  score={row['altmetric_score']:.1f} | noticias={int(row['cited_by_newsoutlets_count'])} | doi={row['doi']}")
    print(f"\nGuardado en: {OUT_CSV}")


if __name__ == "__main__":
    main()
