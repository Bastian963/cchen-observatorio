#!/usr/bin/env python3
"""
Descarga patentes USPTO asociadas a CCHEN usando PatentsView PatentSearch API.

Uso:
    cd /Users/bastianayalainostroza/Dropbox/CCHEN
    export PATENTSVIEW_API_KEY="..."
    python3 Scripts/fetch_patentsview_patents.py

Opcional:
    python3 Scripts/fetch_patentsview_patents.py --query-name "Chilean Nuclear Energy Commission"
    python3 Scripts/fetch_patentsview_patents.py --size 1000
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
INST_DIR = ROOT / "Data" / "Institutional"
PAT_DIR = ROOT / "Data" / "Patents"
OUT_CSV = PAT_DIR / "cchen_patents_uspto.csv"
OUT_STATE = PAT_DIR / "patentsview_state.json"

PV_URL = "https://search.patentsview.org/api/v1/patent/"
DEFAULT_SIZE = 1000
MAX_SIZE = 1000
DEFAULT_SLEEP_SECONDS = 1.4

DEFAULT_QUERIES = [
    "Comision Chilena de Energia Nuclear",
    "Comisión Chilena de Energía Nuclear",
    "Chilean Nuclear Energy Commission",
    "Chilean Commission for Nuclear Energy",
    "CCHEN",
]

PATENT_FIELDS = [
    "patent_id",
    "patent_title",
    "patent_date",
    "patent_num_cited_by_us_patents",
    "inventors.inventor_first_name",
    "inventors.inventor_last_name",
    "inventors.inventor_country",
    "assignees.assignee_organization",
    "assignees.assignee_country",
    "ipcs.ipc_class",
    "ipcs.ipc_subclass",
]


def _join_unique(values) -> str:
    out = []
    seen = set()
    for value in values:
        text = str(value).strip()
        if not text or text in {"nan", "None"}:
            continue
        if text not in seen:
            out.append(text)
            seen.add(text)
    return "; ".join(out)


def load_cchen_queries(extra_names: list[str]) -> list[str]:
    names = list(DEFAULT_QUERIES)
    seed_path = INST_DIR / "ror_seed_institutions.csv"
    if seed_path.exists():
        try:
            seed = pd.read_csv(seed_path)
            if "is_cchen_anchor" in seed.columns:
                anchor = seed[seed["is_cchen_anchor"] == True]
            else:
                anchor = pd.DataFrame()
            if not anchor.empty and "aliases_seed" in anchor.columns:
                aliases = str(anchor.iloc[0].get("aliases_seed") or "")
                names.extend(part.strip() for part in aliases.split(";") if part.strip())
        except Exception:
            pass
    names.extend(extra_names)
    return list(dict.fromkeys(name for name in names if str(name).strip()))


def patentsview_get(api_key: str, query: dict, fields: list[str], size: int) -> dict:
    params = {
        "q": json.dumps(query, ensure_ascii=False),
        "f": json.dumps(fields, ensure_ascii=False),
        "o": json.dumps(
            {
                "size": min(int(size), MAX_SIZE),
                "exclude_withdrawn": True,
            },
            ensure_ascii=False,
        ),
    }
    req = Request(
        f"{PV_URL}?{urlencode(params)}",
        headers={
            "X-Api-Key": api_key,
            "Accept": "application/json",
            "User-Agent": "CCHEN-Observatorio/0.2",
        },
    )
    try:
        with urlopen(req, timeout=60) as resp:
            return json.load(resp)
    except HTTPError as exc:
        detail = exc.reason
        try:
            body = exc.read().decode("utf-8", errors="replace").strip()
            if body:
                detail = f"{detail} | {body[:300]}"
        except Exception:
            pass
        raise RuntimeError(f"PatentsView API error {exc.code}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"PatentsView connection error: {exc.reason}") from exc


def normalize_response(payload: dict) -> tuple[list[dict], int]:
    patents = payload.get("patents")
    if patents is None and isinstance(payload.get("data"), list):
        patents = payload.get("data")
    if patents is None and isinstance(payload.get("results"), list):
        patents = payload.get("results")
    patents = patents or []

    total = payload.get("total_patent_count")
    if total is None:
        total = payload.get("count")
    if total is None:
        total = len(patents)
    return patents, int(total)


def fetch_patentsview(org_names: list[str], api_key: str, size: int, sleep_seconds: float) -> tuple[pd.DataFrame, list[dict]]:
    rows = []
    stats = []
    for idx, org in enumerate(org_names, start=1):
        query = {"assignees.assignee_organization": org}
        try:
            payload = patentsview_get(api_key=api_key, query=query, fields=PATENT_FIELDS, size=size)
        except RuntimeError as exc:
            print(f"[ERROR] {org} -> {exc}")
            stats.append(
                {
                    "query_org": org,
                    "total_results": 0,
                    "returned_records": 0,
                    "truncated": False,
                    "error": str(exc),
                }
            )
            if idx < len(org_names):
                time.sleep(sleep_seconds)
            continue
        patents, total = normalize_response(payload)
        print(f"[OK] {org} -> {total} resultados")
        for patent in patents:
            patent["_query_org"] = org
        rows.extend(patents)
        stats.append(
            {
                "query_org": org,
                "total_results": total,
                "returned_records": len(patents),
                "truncated": bool(total > len(patents)),
                "error": "",
            }
        )
        if idx < len(org_names):
            time.sleep(sleep_seconds)
    return pd.DataFrame(rows), stats


def flatten_patentsview_patent(row: dict) -> dict:
    inventors = row.get("inventors") or []
    assignees = row.get("assignees") or []
    ipcs = row.get("ipcs") or []

    inventor_names = _join_unique(
        f"{inv.get('inventor_first_name', '').strip()} {inv.get('inventor_last_name', '').strip()}".strip()
        for inv in inventors
    )
    inventor_countries = _join_unique(inv.get("inventor_country", "") for inv in inventors)
    n_inventors_cl = sum(1 for inv in inventors if str(inv.get("inventor_country", "")).strip().upper() == "CL")

    assignee_names = _join_unique(assignee.get("assignee_organization", "") for assignee in assignees)
    assignee_countries = _join_unique(assignee.get("assignee_country", "") for assignee in assignees)
    ipc_symbols = _join_unique(
        f"{ipc.get('ipc_class', '')}{ipc.get('ipc_subclass', '')}".strip()
        for ipc in ipcs
    )

    patent_date = row.get("patent_date")
    grant_year = None
    if patent_date:
        try:
            grant_year = int(str(patent_date)[:4])
        except ValueError:
            grant_year = None

    patent_id = row.get("patent_id")
    patent_url = f"https://patents.google.com/patent/US{patent_id}" if patent_id else ""

    return {
        "patent_id": patent_id,
        "title": row.get("patent_title"),
        "patent_date": patent_date,
        "grant_year": grant_year,
        "cited_by_count": row.get("patent_num_cited_by_us_patents") or 0,
        "assignees": assignee_names,
        "assignee_countries": assignee_countries,
        "inventors": inventor_names,
        "inventor_countries": inventor_countries,
        "n_inventors_cl": n_inventors_cl,
        "ipc_symbols": ipc_symbols,
        "source": "PatentsView/USPTO",
        "query_org": row.get("_query_org", ""),
        "patent_url": patent_url,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-key", default="", help="API key de PatentsView. Si se omite, usa PATENTSVIEW_API_KEY.")
    parser.add_argument("--query-name", action="append", default=[], help="Nombre adicional de organización para consultar.")
    parser.add_argument("--size", type=int, default=DEFAULT_SIZE, help="Máximo de resultados por consulta (1-1000).")
    parser.add_argument("--sleep-seconds", type=float, default=DEFAULT_SLEEP_SECONDS, help="Pausa entre consultas para respetar rate limit.")
    args = parser.parse_args()

    api_key = (args.api_key or os.getenv("PATENTSVIEW_API_KEY") or "").strip()
    if not api_key:
        raise SystemExit(
            "[ERROR] Falta PATENTSVIEW_API_KEY. "
            "Configura la variable de entorno o usa --api-key.\n"
            "Registro/API key: https://patentsview.org/apis/keyrequest"
        )

    query_names = load_cchen_queries(args.query_name)
    PAT_DIR.mkdir(parents=True, exist_ok=True)

    raw_df, query_stats = fetch_patentsview(
        org_names=query_names,
        api_key=api_key,
        size=args.size,
        sleep_seconds=args.sleep_seconds,
    )

    if raw_df.empty:
        out_df = pd.DataFrame(
            columns=[
                "patent_id", "title", "patent_date", "grant_year", "cited_by_count",
                "assignees", "assignee_countries", "inventors", "inventor_countries",
                "n_inventors_cl", "ipc_symbols", "source", "query_org", "patent_url",
            ]
        )
    else:
        out_df = pd.DataFrame(flatten_patentsview_patent(rec) for rec in raw_df.to_dict(orient="records"))
        out_df["cited_by_count"] = pd.to_numeric(out_df["cited_by_count"], errors="coerce").fillna(0).astype(int)
        out_df["grant_year"] = pd.to_numeric(out_df["grant_year"], errors="coerce").astype("Int64")
        out_df = out_df.sort_values(["grant_year", "patent_date", "patent_id"], ascending=[False, False, True])
        out_df = out_df.drop_duplicates(subset=["patent_id"], keep="first").reset_index(drop=True)

    out_df.to_csv(OUT_CSV, index=False)

    query_stats_df = pd.DataFrame(query_stats)
    state = {
        "source": "PatentsView PatentSearch API",
        "endpoint": PV_URL,
        "generated_at_utc": dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "queries": query_names,
        "records_raw": int(len(raw_df)),
        "records_unique": int(len(out_df)),
        "query_totals": query_stats_df.to_dict(orient="records") if not query_stats_df.empty else [],
        "notes": [
            "Consulta basada en assignees.assignee_organization para variantes de CCHEN.",
            "PatentsView advierte que el índice de assignees es poco confiable tras la actualización del 2025-03-31; validar resultados manualmente.",
            "Si total_results > returned_records en una consulta, aumentar --size o implementar paginación adicional.",
        ],
    }
    OUT_STATE.write_text(json.dumps(state, indent=2, ensure_ascii=False))

    print(f"[OK] Patentes USPTO guardadas en: {OUT_CSV}")
    print(f"     Registros únicos: {len(out_df)}")
    print(f"[OK] Estado guardado en: {OUT_STATE}")


if __name__ == "__main__":
    main()
