#!/usr/bin/env python3
"""
Descarga outputs DataCite asociados a CCHEN usando el ROR institucional.

Uso:
    cd /Users/bastianayalainostroza/Dropbox/CCHEN
    python3 Scripts/fetch_datacite_outputs.py
    python3 Scripts/fetch_datacite_outputs.py --raw-json Data/ResearchOutputs/datacite_raw_cchen.json
"""

from __future__ import annotations

import datetime as dt
import json
import subprocess
import argparse
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "Data" / "ResearchOutputs"
OUT_CSV = OUT_DIR / "cchen_datacite_outputs.csv"
OUT_STATE = OUT_DIR / "datacite_state.json"

DATACITE_API = "https://api.datacite.org/dois"
CCHEN_ROR = "https://ror.org/03hv95d67"
PAGE_SIZE = 100


def _join(items: list[str]) -> str:
    cleaned = [str(item).strip() for item in items if str(item).strip()]
    return "; ".join(dict.fromkeys(cleaned))


def _get_json(url: str) -> dict:
    req = Request(
        url,
        headers={
            "User-Agent": "CCHEN-Observatorio/0.2",
            "Accept": "application/vnd.api+json",
        },
    )
    try:
        with urlopen(req, timeout=60) as resp:
            return json.load(resp)
    except Exception:
        try:
            result = subprocess.run(
                ["curl", "-L", "--fail", url],
                check=True,
                capture_output=True,
                text=True,
            )
            return json.loads(result.stdout)
        except Exception as exc:
            raise RuntimeError(f"No se pudo descargar DataCite: {url} -> {exc}") from exc


def _extract_creator_names(creators: list[dict]) -> str:
    return _join([creator.get("name", "") for creator in creators])


def _extract_creator_orcids(creators: list[dict]) -> str:
    values = []
    for creator in creators:
        for identifier in creator.get("nameIdentifiers", []) or []:
            if str(identifier.get("nameIdentifierScheme", "")).upper() == "ORCID":
                values.append(identifier.get("nameIdentifier", ""))
    return _join(values)


def _extract_affiliations(creators: list[dict]) -> tuple[str, int]:
    values = []
    cchen_creators = 0
    for creator in creators:
        creator_has_cchen = False
        for affiliation in creator.get("affiliation", []) or []:
            values.append(affiliation.get("name", ""))
            if affiliation.get("affiliationIdentifier") == CCHEN_ROR:
                creator_has_cchen = True
        if creator_has_cchen:
            cchen_creators += 1
    return _join(values), cchen_creators


def _extract_related(related_items: list[dict]) -> str:
    values = []
    for rel in related_items or []:
        rel_type = rel.get("relationType", "")
        identifier = rel.get("relatedIdentifier", "")
        if rel_type or identifier:
            values.append(f"{rel_type}:{identifier}".strip(":"))
    return _join(values)


def _extract_subjects(subjects: list[dict]) -> str:
    return _join([subject.get("subject", "") for subject in subjects or []])


def _extract_rights(rights_list: list[dict]) -> str:
    return _join([right.get("rights", "") for right in rights_list or []])


def _extract_title(titles: list[dict]) -> str:
    for title in titles or []:
        if title.get("title"):
            return str(title["title"]).strip()
    return ""


def _extract_description(descriptions: list[dict]) -> str:
    for desc in descriptions or []:
        if desc.get("description"):
            return str(desc["description"]).replace("\n", " ").strip()
    return ""


def fetch_datacite_outputs() -> pd.DataFrame:
    params = {
        "affiliation-id": CCHEN_ROR,
        "affiliation": "true",
        "disable-facets": "true",
        "page[size]": str(PAGE_SIZE),
    }
    next_url = f"{DATACITE_API}?{urlencode(params, safe=':/')}"
    rows = []

    while next_url:
        try:
            payload = _get_json(next_url)
        except RuntimeError as exc:
            print(f"[WARN] Descarga DataCite interrumpida, se guardará resultado parcial: {exc}")
            break
        for item in payload.get("data", []) or []:
            attrs = item.get("attributes", {}) or {}
            creators = attrs.get("creators", []) or []
            affiliations, cchen_creators = _extract_affiliations(creators)
            rows.append({
                "doi": attrs.get("doi"),
                "title": _extract_title(attrs.get("titles", []) or []),
                "publisher": attrs.get("publisher"),
                "publication_year": attrs.get("publicationYear"),
                "resource_type_general": (attrs.get("types", {}) or {}).get("resourceTypeGeneral"),
                "resource_type": (attrs.get("types", {}) or {}).get("resourceType"),
                "client_id": ((item.get("relationships", {}) or {}).get("client", {}) or {}).get("data", {}).get("id"),
                "url": attrs.get("url"),
                "created": attrs.get("created"),
                "updated": attrs.get("updated"),
                "state": attrs.get("state"),
                "version": attrs.get("version"),
                "rights": _extract_rights(attrs.get("rightsList", []) or []),
                "subjects": _extract_subjects(attrs.get("subjects", []) or []),
                "creators": _extract_creator_names(creators),
                "creator_orcids": _extract_creator_orcids(creators),
                "creator_affiliations": affiliations,
                "cchen_affiliated_creators": cchen_creators,
                "has_cchen_ror_affiliation": bool(cchen_creators > 0),
                "related_identifiers": _extract_related(attrs.get("relatedIdentifiers", []) or []),
                "citation_count": attrs.get("citationCount"),
                "view_count": attrs.get("viewCount"),
                "download_count": attrs.get("downloadCount"),
                "description": _extract_description(attrs.get("descriptions", []) or []),
                "source": "DataCite API",
                "source_filter_ror": CCHEN_ROR,
            })
        next_url = (payload.get("links", {}) or {}).get("next")

    return _finalize_df(pd.DataFrame(rows))


def parse_datacite_payloads(payloads: list[dict]) -> pd.DataFrame:
    rows = []
    for payload in payloads:
        for item in payload.get("data", []) or []:
            attrs = item.get("attributes", {}) or {}
            creators = attrs.get("creators", []) or []
            affiliations, cchen_creators = _extract_affiliations(creators)
            rows.append({
                "doi": attrs.get("doi"),
                "title": _extract_title(attrs.get("titles", []) or []),
                "publisher": attrs.get("publisher"),
                "publication_year": attrs.get("publicationYear"),
                "resource_type_general": (attrs.get("types", {}) or {}).get("resourceTypeGeneral"),
                "resource_type": (attrs.get("types", {}) or {}).get("resourceType"),
                "client_id": ((item.get("relationships", {}) or {}).get("client", {}) or {}).get("data", {}).get("id"),
                "url": attrs.get("url"),
                "created": attrs.get("created"),
                "updated": attrs.get("updated"),
                "state": attrs.get("state"),
                "version": attrs.get("version"),
                "rights": _extract_rights(attrs.get("rightsList", []) or []),
                "subjects": _extract_subjects(attrs.get("subjects", []) or []),
                "creators": _extract_creator_names(creators),
                "creator_orcids": _extract_creator_orcids(creators),
                "creator_affiliations": affiliations,
                "cchen_affiliated_creators": cchen_creators,
                "has_cchen_ror_affiliation": bool(cchen_creators > 0),
                "related_identifiers": _extract_related(attrs.get("relatedIdentifiers", []) or []),
                "citation_count": attrs.get("citationCount"),
                "view_count": attrs.get("viewCount"),
                "download_count": attrs.get("downloadCount"),
                "description": _extract_description(attrs.get("descriptions", []) or []),
                "source": "DataCite API",
                "source_filter_ror": CCHEN_ROR,
            })
    return _finalize_df(pd.DataFrame(rows))


def _finalize_df(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    for col in ["publication_year", "cchen_affiliated_creators", "citation_count", "view_count", "download_count"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.sort_values(["publication_year", "updated", "doi"], ascending=[False, False, True]).reset_index(drop=True)
    if "doi" in df.columns:
        df = df.drop_duplicates(subset=["doi"], keep="first").reset_index(drop=True)
    return df


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--raw-json",
        action="append",
        default=[],
        help="Ruta a un archivo JSON ya descargado desde DataCite API. Se puede repetir.",
    )
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if args.raw_json:
        payloads = []
        for raw_path in args.raw_json:
            payloads.append(json.loads(Path(raw_path).read_text()))
        df = parse_datacite_payloads(payloads)
    else:
        df = fetch_datacite_outputs()
    df.to_csv(OUT_CSV, index=False)
    state = {
        "source": "DataCite API",
        "filter_ror": CCHEN_ROR,
        "generated_at_utc": dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "records": int(len(df)),
        "resource_types": sorted(df["resource_type_general"].dropna().astype(str).unique().tolist()) if not df.empty else [],
        "publishers": (
            df["publisher"].dropna().astype(str).value_counts().head(10).to_dict()
            if not df.empty and "publisher" in df.columns else {}
        ),
    }
    OUT_STATE.write_text(json.dumps(state, indent=2, ensure_ascii=False))
    print(f"[OK] DataCite outputs guardados en: {OUT_CSV}")
    print(f"     Registros: {len(df)}")
    if not df.empty:
        print(f"     Tipos: {', '.join(sorted(df['resource_type_general'].dropna().astype(str).unique().tolist()))}")


if __name__ == "__main__":
    main()
