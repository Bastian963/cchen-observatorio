#!/usr/bin/env python3
"""
fetch_orcid.py — Observatorio CCHEN 360°
=========================================
Descarga perfiles ORCID de investigadores CCHEN.

Estrategias:
  1. Búsqueda por afiliación en ORCID Public API
  2. Búsqueda por nombre (autores CCHEN en OpenAlex)

Para cada ORCID: descarga nombre, empleadores, educación y conteo de obras.

API: https://pub.orcid.org/v3.0  (pública, sin autenticación)
Rate limit: conservador 0.4s entre requests.

Salidas:
  Data/Researchers/cchen_researchers_orcid.csv
  Data/Researchers/orcid_state.json

Uso:
    python3 Scripts/fetch_orcid.py
    python3 Scripts/fetch_orcid.py --reset
    python3 Scripts/fetch_orcid.py --verbose
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

ROOT        = Path(__file__).resolve().parents[1]
OUT_DIR     = ROOT / "Data" / "Researchers"
PUB_DIR     = ROOT / "Data" / "Publications"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_CSV     = OUT_DIR / "cchen_researchers_orcid.csv"
STATE_FILE  = OUT_DIR / "orcid_state.json"

ORCID_SEARCH = "https://pub.orcid.org/v3.0/search/"
ORCID_BASE   = "https://pub.orcid.org/v3.0"
CONTACT      = "observatorio@cchen.cl"
TIMEOUT      = 15
SLEEP        = 0.4

AFFILIATION_QUERIES = [
    'affiliation-org-name:"Comision Chilena de Energia Nuclear"',
    'affiliation-org-name:"CCHEN"',
    'affiliation-org-name:"Chilean Nuclear Energy Commission"',
]

OUTPUT_COLUMNS = [
    "orcid_id", "orcid_profile_url",
    "given_name", "family_name", "full_name",
    "employers", "education", "orcid_works_count",
]


def _get(url: str, verbose: bool = False) -> dict | None:
    req = Request(url, headers={
        "Accept":     "application/json",
        "User-Agent": f"CCHEN-Observatory/1.0 (mailto:{CONTACT})",
    })
    try:
        with urlopen(req, timeout=TIMEOUT) as r:
            return json.load(r)
    except HTTPError as e:
        if verbose:
            print(f"    HTTP {e.code}: {url[:80]}")
        return None
    except Exception as exc:
        if verbose:
            print(f"    Error: {exc}")
        return None


def _search_by_affiliation(verbose: bool = False) -> dict[str, str]:
    """Devuelve {orcid_id: nombre_aproximado} desde búsqueda por afiliación."""
    found: dict[str, str] = {}
    for query in AFFILIATION_QUERIES:
        url = f"{ORCID_SEARCH}?{urlencode({'q': query, 'rows': 200})}"
        data = _get(url, verbose=verbose)
        if not data:
            continue
        results = data.get("result") or data.get("expanded-result") or []
        if verbose:
            print(f"  Afiliación '{query[:55]}': {len(results)} resultados")
        for res in results:
            oid = (res.get("orcid-identifier") or {}).get("path", "")
            if not oid or oid in found:
                continue
            name_parts = res.get("personal-details") or {}
            given  = _val(name_parts.get("given-names"))
            family = _val(name_parts.get("family-name"))
            found[oid] = f"{given} {family}".strip()
        time.sleep(SLEEP)
    return found


def _search_by_name(full_name: str, verbose: bool = False) -> list[str]:
    """Devuelve lista de ORCIDs para un nombre dado."""
    parts = full_name.strip().split()
    if len(parts) < 2:
        return []
    family = parts[-1]
    given  = parts[0]
    query  = f"family-name:{family} AND given-names:{given}"
    url    = f"{ORCID_SEARCH}?{urlencode({'q': query, 'rows': 5})}"
    data   = _get(url, verbose=verbose)
    if not data:
        return []
    return [
        (res.get("orcid-identifier") or {}).get("path", "")
        for res in (data.get("result") or [])
        if (res.get("orcid-identifier") or {}).get("path")
    ]


def _val(obj) -> str:
    if isinstance(obj, dict):
        return str(obj.get("value", "") or "")
    return ""


def _fetch_profile(oid: str, verbose: bool = False) -> dict:
    rec = {
        "orcid_id":         oid,
        "orcid_profile_url": f"https://orcid.org/{oid}",
        "given_name":       "",
        "family_name":      "",
        "full_name":        "",
        "employers":        "",
        "education":        "",
        "orcid_works_count": 0,
    }

    # Nombre
    data = _get(f"{ORCID_BASE}/{oid}/person", verbose=verbose)
    if data:
        name = data.get("name") or {}
        rec["given_name"]  = _val(name.get("given-names"))
        rec["family_name"] = _val(name.get("family-name"))
        rec["full_name"]   = f"{rec['given_name']} {rec['family_name']}".strip()
    time.sleep(SLEEP)

    # Empleadores
    data = _get(f"{ORCID_BASE}/{oid}/employments", verbose=verbose)
    if data:
        orgs = []
        for eg in (data.get("affiliation-group") or []):
            for s in (eg.get("summaries") or []):
                org = (s.get("employment-summary") or {}).get("organization") or {}
                if org.get("name"):
                    orgs.append(org["name"])
        rec["employers"] = "; ".join(orgs[:5])
    time.sleep(SLEEP)

    # Educación
    data = _get(f"{ORCID_BASE}/{oid}/educations", verbose=verbose)
    if data:
        degrees = []
        for eg in (data.get("affiliation-group") or []):
            for s in (eg.get("summaries") or []):
                es   = s.get("education-summary") or {}
                org  = (es.get("organization") or {}).get("name", "")
                role = es.get("role-title", "") or ""
                entry = f"{role} — {org}".strip(" —")
                if entry:
                    degrees.append(entry)
        rec["education"] = "; ".join(degrees[:4])
    time.sleep(SLEEP)

    # Conteo de obras
    data = _get(f"{ORCID_BASE}/{oid}/works", verbose=verbose)
    if data:
        rec["orcid_works_count"] = len(data.get("group") or [])
    time.sleep(SLEEP)

    return rec


def _openalex_author_names() -> list[str]:
    """Extrae nombres de autores CCHEN del CSV de OpenAlex (columna authors si existe)."""
    openalex_csv = PUB_DIR / "cchen_openalex_works.csv"
    if not openalex_csv.exists():
        return []
    # No tenemos columna authors en openalex_works — usamos CSV existente de ORCID
    # como semilla de nombres adicionales
    if OUT_CSV.exists():
        df = pd.read_csv(OUT_CSV)
        if "full_name" in df.columns:
            return df["full_name"].dropna().str.strip().tolist()
    return []


def _load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"fetched_orcids": []}


def _save_state(state: dict) -> None:
    state["updated"] = datetime.datetime.now().isoformat()
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="ORCID — CCHEN Observatory")
    parser.add_argument("--reset",   action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    state = {"fetched_orcids": []} if args.reset else _load_state()
    fetched_orcids = set(state.get("fetched_orcids", []))

    # Estrategia 1: búsqueda por afiliación
    print("Buscando por afiliación...")
    orcid_map = _search_by_affiliation(verbose=args.verbose)
    print(f"  {len(orcid_map)} ORCIDs encontrados por afiliación")

    # Estrategia 2: búsqueda por nombre (semilla del CSV existente)
    seed_names = _openalex_author_names()
    named_already = set(orcid_map.values())
    nuevos = 0
    if seed_names:
        print(f"Buscando por nombre ({len(seed_names)} nombres semilla)...")
        for name in seed_names:
            if name in named_already:
                continue
            ids = _search_by_name(name, verbose=args.verbose)
            for oid in ids[:1]:
                if oid and oid not in orcid_map:
                    orcid_map[oid] = name
                    nuevos += 1
            time.sleep(SLEEP)
        if nuevos:
            print(f"  +{nuevos} ORCIDs nuevos por búsqueda de nombre")

    # Descargar perfiles de los que aún no están en el state
    pending = {oid: name for oid, name in orcid_map.items() if oid not in fetched_orcids}
    print(f"\nPerfiles a descargar: {len(pending)} (ya en estado: {len(fetched_orcids)})")

    profiles: list[dict] = []
    for i, (oid, name) in enumerate(pending.items(), 1):
        if args.verbose:
            print(f"  [{i}/{len(pending)}] {oid} ({name})")
        profile = _fetch_profile(oid, verbose=args.verbose)
        profiles.append(profile)
        fetched_orcids.add(oid)

    if not profiles and OUT_CSV.exists():
        print("Sin perfiles nuevos — estado ya actualizado.")
        _print_summary()
        return

    # Merge con CSV existente
    new_df = pd.DataFrame(profiles, columns=OUTPUT_COLUMNS)
    if OUT_CSV.exists() and not args.reset:
        old_df = pd.read_csv(OUT_CSV, dtype=str)
        # normalizar orcid_works_count a int antes de concat
        new_df = pd.concat([old_df, new_df]).drop_duplicates(subset=["orcid_id"], keep="last")

    if "orcid_works_count" in new_df.columns:
        new_df["orcid_works_count"] = pd.to_numeric(
            new_df["orcid_works_count"], errors="coerce"
        ).fillna(0).astype(int)

    new_df.to_csv(OUT_CSV, index=False)
    _save_state({"fetched_orcids": sorted(fetched_orcids)})
    _print_summary()


def _print_summary() -> None:
    print("\n-- Resumen --------------------------------------------------")
    if not OUT_CSV.exists():
        print("Sin datos ORCID."); return
    df = pd.read_csv(OUT_CSV)
    print(f"Total investigadores ORCID: {len(df)}")
    print(f"Con empleadores:   {df['employers'].fillna('').ne('').sum()}")
    print(f"Con educación:     {df['education'].fillna('').ne('').sum()}")
    works = pd.to_numeric(df.get("orcid_works_count", pd.Series()), errors="coerce")
    print(f"Con obras (>0):    {(works > 0).sum()}")
    print(f"Guardado en: {OUT_CSV}")
    print("\nMuestra (5 con más obras):")
    df["orcid_works_count"] = works
    for _, r in df.nlargest(5, "orcid_works_count").iterrows():
        print(f"  {r['full_name']:<35} obras={int(r['orcid_works_count'])}  {r['employers'][:50]}")


if __name__ == "__main__":
    main()
