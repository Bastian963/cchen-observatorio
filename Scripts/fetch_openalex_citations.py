#!/usr/bin/env python3
"""
fetch_openalex_citations.py — Observatorio CCHEN 360°
=====================================================
Descarga el grafo de citas de publicaciones CCHEN desde OpenAlex.

Para cada paper CCHEN obtiene:
  - cited_by_count   (ya está en openalex_works, pero se refresca)
  - referenced_works (papers que CCHEN cita)
  - citing_works     (papers externos que citan a CCHEN)

Salidas:
  Data/Publications/cchen_citation_graph.csv
      openalex_id | doi | year | cited_by_count | citing_ids_sample | referenced_ids_sample

  Data/Publications/cchen_citing_papers.csv
      citing_id | cited_cchen_id | citing_title | citing_year | citing_doi | citing_institutions

Uso:
    python3 Scripts/fetch_openalex_citations.py
    python3 Scripts/fetch_openalex_citations.py --limit 100   # prueba rápida
    python3 Scripts/fetch_openalex_citations.py --reset       # ignorar cache
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

IN_CSV          = PUB_DIR / "cchen_openalex_works.csv"
OUT_GRAPH       = PUB_DIR / "cchen_citation_graph.csv"
OUT_CITING      = PUB_DIR / "cchen_citing_papers.csv"
STATE_FILE      = PUB_DIR / "citation_graph_state.json"

OA_BASE         = "https://api.openalex.org"
CONTACT_EMAIL   = "observatory@cchen.cl"
SLEEP           = 0.15     # respeta polite pool OpenAlex (10 req/s)
TIMEOUT         = 25
CITING_PER_WORK = 50       # max external citing papers a guardar por trabajo CCHEN


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get(url: str) -> dict | None:
    req = Request(
        url,
        headers={"User-Agent": f"CCHEN-Observatory/1.0 (mailto:{CONTACT_EMAIL})"}
    )
    try:
        with urlopen(req, timeout=TIMEOUT) as r:
            return json.load(r)
    except HTTPError as e:
        if e.code == 429:
            print("  ⚠ Rate-limit — esperando 30 s...")
            time.sleep(30)
        elif e.code == 404:
            return None
        else:
            print(f"  ⚠ HTTP {e.code} en {url}")
        return None
    except Exception as exc:
        print(f"  ⚠ Error: {exc}")
        return None


def _work_url(openalex_id: str) -> str:
    wid = openalex_id.split("/")[-1]
    params = urlencode({
        "select": "id,doi,title,display_name,publication_year,cited_by_count,"
                  "referenced_works",
        "mailto": CONTACT_EMAIL,
    })
    return f"{OA_BASE}/works/{wid}?{params}"


def _citing_url(openalex_id: str) -> str:
    """Construye URL para obtener papers que citan a este trabajo."""
    wid = openalex_id.split("/")[-1]
    params = urlencode({
        "filter": f"cites:{wid}",
        "select": "id,doi,display_name,publication_year,authorships",
        "per-page": CITING_PER_WORK,
        "mailto": CONTACT_EMAIL,
    })
    return f"{OA_BASE}/works?{params}"


def _extract_institutions(authorships: list) -> str:
    """Devuelve instituciones únicas de una lista de authorships OA."""
    insts = set()
    for a in (authorships or []):
        for inst in (a.get("institutions") or []):
            name = inst.get("display_name") or inst.get("ror") or ""
            if name:
                insts.add(name)
    return "; ".join(sorted(insts)[:5])


# ── Estado / cache ────────────────────────────────────────────────────────────

def _load_state() -> set[str]:
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return set(json.load(f).get("processed_ids", []))
    return set()


def _save_state(processed: set[str]) -> None:
    with open(STATE_FILE, "w") as f:
        json.dump({"processed_ids": sorted(processed),
                   "updated": datetime.datetime.now().isoformat()}, f)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Grafo de citas OpenAlex — CCHEN")
    parser.add_argument("--limit",  type=int, default=0, help="Máx. papers a procesar (0 = todos)")
    parser.add_argument("--reset",  action="store_true",  help="Ignorar cache y reprocesar todo")
    args = parser.parse_args()

    works = pd.read_csv(IN_CSV)
    all_ids = works["openalex_id"].dropna().unique().tolist()
    print(f"Papers CCHEN totales: {len(all_ids)}")

    processed = set() if args.reset else _load_state()
    pending   = [oid for oid in all_ids if oid not in processed]
    if args.limit > 0:
        pending = pending[:args.limit]

    print(f"Ya procesados: {len(processed)} | Pendientes: {len(pending)}")
    if not pending:
        print("Nada nuevo que procesar.")
        _print_summary()
        return

    graph_rows:  list[dict] = []
    citing_rows: list[dict] = []

    for i, oid in enumerate(pending, 1):
        print(f"[{i:4d}/{len(pending)}] {oid} ...", end="  ")

        data = _get(_work_url(oid))
        if data is None:
            processed.add(oid)
            print("sin datos")
            time.sleep(SLEEP)
            continue

        cited_by_count  = data.get("cited_by_count", 0) or 0
        referenced_works = data.get("referenced_works") or []

        graph_rows.append({
            "openalex_id":            oid,
            "doi":                    data.get("doi", ""),
            "year":                   data.get("publication_year"),
            "cited_by_count":         cited_by_count,
            "referenced_works_count": len(referenced_works),
            "referenced_ids_sample":  "; ".join(referenced_works[:20]),
            "fetched_at":             datetime.date.today().isoformat(),
        })

        # Obtener papers que citan a este trabajo
        n_citing = 0
        if cited_by_count > 0:
            citing_data = _get(_citing_url(oid))
            if citing_data:
                for cw in (citing_data.get("results") or []):
                    citing_rows.append({
                        "citing_id":       cw.get("id", ""),
                        "cited_cchen_id":  oid,
                        "citing_doi":      cw.get("doi", ""),
                        "citing_title":    (cw.get("display_name") or "")[:200],
                        "citing_year":     cw.get("publication_year"),
                        "citing_institutions": _extract_institutions(
                            cw.get("authorships", [])
                        ),
                    })
                    n_citing += 1
                time.sleep(SLEEP)

        print(f"cited_by={cited_by_count} | citing_fetched={n_citing} | refs={len(referenced_works)}")

        processed.add(oid)

        # Guardar parcialmente cada 50 papers
        if i % 50 == 0:
            _flush(graph_rows, citing_rows)
            graph_rows, citing_rows = [], []
            _save_state(processed)

        time.sleep(SLEEP)

    _flush(graph_rows, citing_rows)
    _save_state(processed)
    _print_summary()


def _flush(graph_rows: list[dict], citing_rows: list[dict]) -> None:
    if graph_rows:
        new_g = pd.DataFrame(graph_rows)
        if OUT_GRAPH.exists():
            old_g = pd.read_csv(OUT_GRAPH)
            new_g = pd.concat([old_g, new_g]).drop_duplicates("openalex_id", keep="last")
        new_g.to_csv(OUT_GRAPH, index=False)

    if citing_rows:
        new_c = pd.DataFrame(citing_rows)
        if OUT_CITING.exists():
            old_c = pd.read_csv(OUT_CITING)
            new_c = pd.concat([old_c, new_c]).drop_duplicates(
                subset=["citing_id", "cited_cchen_id"], keep="last"
            )
        new_c.to_csv(OUT_CITING, index=False)


def _print_summary() -> None:
    print("\n── Resumen ──────────────────────────────────────────")
    if OUT_GRAPH.exists():
        g = pd.read_csv(OUT_GRAPH)
        total_cites = g["cited_by_count"].sum()
        top = g.nlargest(5, "cited_by_count")[["openalex_id", "year", "cited_by_count"]]
        print(f"Grafo: {len(g)} papers · {int(total_cites):,} citas totales")
        print("Top 5 más citados:")
        print(top.to_string(index=False))
    if OUT_CITING.exists():
        c = pd.read_csv(OUT_CITING)
        print(f"\nCiting papers: {len(c)} registros únicos")
        if "citing_institutions" in c.columns:
            inst = c["citing_institutions"].str.split("; ").explode().value_counts().head(5)
            print("Instituciones que más citan a CCHEN:")
            print(inst.to_string())
    print(f"\n✓ Guardado en:")
    print(f"  {OUT_GRAPH}")
    print(f"  {OUT_CITING}")


if __name__ == "__main__":
    main()
