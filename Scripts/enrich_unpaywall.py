#!/usr/bin/env python3
"""
enrich_unpaywall.py — Observatorio CCHEN 360°
==============================================
Enriquece publicaciones con datos de acceso abierto desde Unpaywall por DOI.
Complementa los campos is_oa / oa_url que OpenAlex ya provee, y puede detectar
copias OA (green, bronze) que OpenAlex marca como "closed".

Salida:  Data/Publications/cchen_unpaywall_oa.csv

Uso:
    python Scripts/enrich_unpaywall.py
    python Scripts/enrich_unpaywall.py --email observatory@cchen.cl
    python Scripts/enrich_unpaywall.py --only-missing   # solo DOIs sin OA en OpenAlex

API Unpaywall: https://unpaywall.org/products/api
  - Sin autenticación — solo requiere un email de contacto en la URL
  - Rate limit: ~10 req/seg recomendado
"""

from __future__ import annotations

import argparse
import csv
import datetime
import json
import os
import time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

import pandas as pd

ROOT    = Path(__file__).resolve().parents[1]
PUB_DIR = ROOT / "Data" / "Publications"
IN_CSV  = PUB_DIR / "cchen_openalex_works.csv"
OUT_CSV = PUB_DIR / "cchen_unpaywall_oa.csv"

UNPAYWALL_BASE  = "https://api.unpaywall.org/v2"
DEFAULT_EMAIL   = os.getenv("CCHEN_CONTACT_EMAIL", "observatory@cchen.cl")
SLEEP_BETWEEN   = 0.12   # ~8 req/seg, por debajo del límite de 10/seg
TIMEOUT_SECONDS = 20


# ── Campos de salida ──────────────────────────────────────────────────────────

OA_STATUS_ORDER = ["gold", "hybrid", "bronze", "green", "closed"]

FIELDS = [
    "doi",
    "is_oa",
    "oa_status",          # gold | hybrid | bronze | green | closed
    "oa_url",             # URL de la mejor copia OA disponible
    "oa_pdf_url",         # URL directa al PDF OA (si existe)
    "journal_is_oa",      # si la revista es completamente OA
    "journal_name",
    "publisher",
    "published_date",
    "updated",            # última actualización en Unpaywall
    "fetched_at",
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fetch_unpaywall(doi: str, email: str) -> dict | None:
    """Consulta Unpaywall para un DOI. Devuelve el JSON o None si falla."""
    doi_enc = doi.strip().replace(" ", "%20")
    url = f"{UNPAYWALL_BASE}/{doi_enc}?email={email}"
    req = Request(url, headers={"User-Agent": f"CCHEN-Observatory/1.0 (mailto:{email})"})
    try:
        with urlopen(req, timeout=TIMEOUT_SECONDS) as r:
            return json.load(r)
    except HTTPError as e:
        if e.code == 404:
            return None          # DOI no indexado en Unpaywall
        if e.code == 429:
            print("  ⚠ Rate limit — esperando 5 s...")
            time.sleep(5)
            return None
        print(f"  ⚠ HTTP {e.code} para {doi}")
        return None
    except Exception as exc:
        print(f"  ⚠ Error para {doi}: {exc}")
        return None


def _extract_best_oa(data: dict) -> dict:
    """Extrae los campos relevantes del JSON de Unpaywall."""
    best = data.get("best_oa_location") or {}
    return {
        "is_oa":         data.get("is_oa", False),
        "oa_status":     data.get("oa_status", "closed"),
        "oa_url":        best.get("url_for_landing_page") or best.get("url") or "",
        "oa_pdf_url":    best.get("url_for_pdf") or "",
        "journal_is_oa": data.get("journal_is_oa", False),
        "journal_name":  data.get("journal_name", ""),
        "publisher":     data.get("publisher", ""),
        "published_date": data.get("published_date", ""),
        "updated":       data.get("updated", ""),
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Enriquecimiento OA con Unpaywall")
    parser.add_argument("--email",        default=DEFAULT_EMAIL, help="Email de contacto para la API")
    parser.add_argument("--only-missing", action="store_true",
                        help="Solo consultar DOIs donde OpenAlex marca is_oa=False o oa_url vacío")
    parser.add_argument("--max",          type=int, default=0,
                        help="Límite de DOIs a procesar (0 = todos)")
    args = parser.parse_args()

    if not IN_CSV.exists():
        raise SystemExit(f"[ERROR] No se encontró {IN_CSV}")

    works = pd.read_csv(IN_CSV)
    dois_all = works["doi"].dropna().unique().tolist()

    if args.only_missing:
        # Solo los DOIs donde OpenAlex no tiene OA confirmado
        _missing_mask = (
            works["doi"].notna() &
            (~works["is_oa"].fillna(False).astype(bool) | works["oa_url"].fillna("").eq(""))
        )
        dois = works.loc[_missing_mask, "doi"].dropna().unique().tolist()
        print(f"Modo --only-missing: {len(dois)} DOIs sin OA en OpenAlex (de {len(dois_all)} totales)")
    else:
        dois = dois_all
        print(f"Procesando todos los DOIs: {len(dois)}")

    if args.max > 0:
        dois = dois[: args.max]
        print(f"Limitado a los primeros {args.max}")

    # Cargar estado previo para no re-consultar lo ya procesado
    existing: dict[str, dict] = {}
    if OUT_CSV.exists():
        prev = pd.read_csv(OUT_CSV)
        for _, r in prev.iterrows():
            existing[str(r["doi"])] = r.to_dict()
        print(f"  {len(existing)} DOIs ya procesados en cache — se omitirán")

    dois_to_fetch = [d for d in dois if str(d) not in existing]
    print(f"  Consultando {len(dois_to_fetch)} DOIs nuevos...")

    new_rows: list[dict] = []
    now_str = datetime.datetime.now().strftime("%Y-%m-%d")

    for i, doi in enumerate(dois_to_fetch, 1):
        data = _fetch_unpaywall(doi, args.email)
        if data:
            row = {"doi": doi, "fetched_at": now_str}
            row.update(_extract_best_oa(data))
        else:
            row = {"doi": doi, "is_oa": False, "oa_status": "not_found",
                   "oa_url": "", "oa_pdf_url": "", "journal_is_oa": False,
                   "journal_name": "", "publisher": "", "published_date": "",
                   "updated": "", "fetched_at": now_str}
        new_rows.append(row)

        if i % 50 == 0:
            print(f"  ... {i}/{len(dois_to_fetch)}")
        time.sleep(SLEEP_BETWEEN)

    # Combinar con existentes y guardar
    all_rows = list(existing.values()) + new_rows
    out_df = pd.DataFrame(all_rows, columns=FIELDS).drop_duplicates(subset=["doi"])
    out_df.to_csv(OUT_CSV, index=False, encoding="utf-8")

    oa_new = sum(1 for r in new_rows if r.get("is_oa"))
    print(f"\n✓ {len(new_rows)} DOIs nuevos consultados  ({oa_new} OA encontrados)")
    print(f"  Distribución OA status:")
    for status in OA_STATUS_ORDER:
        n = out_df[out_df["oa_status"] == status].shape[0]
        if n:
            print(f"    {status:<10} {n:>5}")
    print(f"\n✓ Guardado en: {OUT_CSV}  ({len(out_df)} registros totales)")


if __name__ == "__main__":
    main()
