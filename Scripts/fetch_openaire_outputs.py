#!/usr/bin/env python3
"""
Descarga outputs OpenAIRE asociados a investigadores CCHEN vía ORCID.

Uso:
    cd /Users/bastianayalainostroza/Dropbox/CCHEN
    python3 Scripts/fetch_openaire_outputs.py
    python3 Scripts/fetch_openaire_outputs.py --limit-authors 10
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import time
import unicodedata
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RESEARCHERS_CSV = ROOT / "Data" / "Researchers" / "cchen_researchers_orcid.csv"
OUT_DIR = ROOT / "Data" / "ResearchOutputs"
OUT_CSV = OUT_DIR / "cchen_openaire_outputs.csv"
OUT_STATE = OUT_DIR / "openaire_state.json"

OPENAIRE_API = "https://api.openaire.eu/graph/v2/researchProducts"
CCHEN_ROR = "https://ror.org/03hv95d67"
PAGE_SIZE = 100


def _join_unique(values) -> str:
    cleaned = []
    seen = set()
    for value in values:
        text = str(value).strip()
        if not text or text in {"nan", "None"}:
            continue
        if text not in seen:
            cleaned.append(text)
            seen.add(text)
    return "; ".join(cleaned)


def _normalize(text: str) -> str:
    base = unicodedata.normalize("NFKD", str(text or ""))
    return "".join(ch for ch in base if not unicodedata.combining(ch)).lower().strip()


def _is_cchen_name(text: str) -> bool:
    normalized = _normalize(text)
    return (
        normalized == "cchen"
        or "comision chilena de energia nuclear" in normalized
        or "comision chilena energia nuclear" in normalized
    )


def _get_json(url: str) -> dict:
    req = Request(
        url,
        headers={
            "User-Agent": "CCHEN-Observatorio/0.2",
            "Accept": "application/json",
        },
    )
    try:
        with urlopen(req, timeout=60) as resp:
            return json.load(resp)
    except Exception:
        result = subprocess.run(
            ["curl", "-L", "--fail", url],
            check=True,
            capture_output=True,
            text=True,
        )
        return json.loads(result.stdout)


def _extract_org_signals(organizations: list[dict]) -> tuple[str, str, bool, bool]:
    names = []
    rors = []
    has_cchen_ror = False
    has_cchen_name = False

    for organization in organizations or []:
        legal_name = organization.get("legalName", "")
        acronym = organization.get("acronym", "")
        names.extend([legal_name, acronym])
        has_cchen_name = has_cchen_name or _is_cchen_name(legal_name) or _is_cchen_name(acronym)
        for pid in organization.get("pids", []) or []:
            if str(pid.get("scheme", "")).upper() == "ROR":
                ror_value = pid.get("value", "")
                if ror_value:
                    rors.append(ror_value)
                if ror_value == CCHEN_ROR:
                    has_cchen_ror = True

    return _join_unique(names), _join_unique(rors), has_cchen_ror, has_cchen_name


def _extract_projects(projects: list[dict]) -> tuple[str, str, str]:
    codes = []
    acronyms = []
    funders = []
    for project in projects or []:
        codes.append(project.get("code", ""))
        acronyms.append(project.get("acronym", ""))
        for funding in project.get("fundings", []) or []:
            funders.append(funding.get("shortName", "") or funding.get("name", ""))
    return _join_unique(codes), _join_unique(acronyms), _join_unique(funders)


def _extract_instance_values(instances: list[dict]) -> tuple[str, str, str]:
    urls = []
    instance_types = []
    hosted_by = []
    for instance in instances or []:
        urls.extend(instance.get("urls", []) or [])
        instance_types.append(instance.get("type", ""))
        host = instance.get("hostedBy", {}) or {}
        hosted_by.append(host.get("value", ""))
    return _join_unique(urls), _join_unique(instance_types), _join_unique(hosted_by)


def _extract_sources(collected_from: list[dict]) -> str:
    return _join_unique(item.get("value", "") for item in collected_from or [])


def _extract_pids(pids: list[dict]) -> str:
    values = []
    for pid in pids or []:
        scheme = pid.get("scheme", "")
        value = pid.get("value", "")
        if scheme or value:
            values.append(f"{scheme}:{value}".strip(":"))
    return _join_unique(values)


def fetch_author_outputs(orcid: str, full_name: str, page_size: int, sleep_seconds: float) -> tuple[list[dict], dict]:
    rows = []
    page = 1
    num_found = 0

    while True:
        params = {"authorOrcid": orcid, "pageSize": str(page_size), "page": str(page)}
        url = f"{OPENAIRE_API}?{urlencode(params)}"
        payload = _get_json(url)
        header = payload.get("header", {}) or {}
        num_found = max(num_found, int(header.get("numFound") or 0))
        results = payload.get("results", []) or []
        if not results:
            break

        for item in results:
            org_names, org_rors, has_cchen_ror, has_cchen_name = _extract_org_signals(item.get("organizations", []) or [])
            project_codes, project_acronyms, project_funders = _extract_projects(item.get("projects", []) or [])
            instance_urls, instance_types, hosted_by = _extract_instance_values(item.get("instances", []) or [])
            best_access = item.get("bestAccessRight", {}) or {}
            language = item.get("language", {}) or {}
            if has_cchen_ror:
                match_scope = "cchen_ror_org"
            elif has_cchen_name:
                match_scope = "cchen_name_org"
            else:
                match_scope = "author_orcid_only"

            rows.append(
                {
                    "openaire_id": item.get("id"),
                    "main_title": item.get("mainTitle"),
                    "type": item.get("type"),
                    "publication_date": item.get("publicationDate"),
                    "publisher": item.get("publisher"),
                    "best_access_right_label": best_access.get("label"),
                    "open_access_color": item.get("openAccessColor"),
                    "publicly_funded": item.get("publiclyFunded"),
                    "is_green": item.get("isGreen"),
                    "is_in_diamond_journal": item.get("isInDiamondJournal"),
                    "language_code": language.get("code"),
                    "language_label": language.get("label"),
                    "sources": _join_unique(item.get("sources", []) or []),
                    "collected_from": _extract_sources(item.get("collectedFrom", []) or []),
                    "authors": _join_unique(author.get("fullName", "") for author in item.get("authors", []) or []),
                    "organization_names": org_names,
                    "organization_rors": org_rors,
                    "has_cchen_ror_org": has_cchen_ror,
                    "has_cchen_name_org": has_cchen_name,
                    "match_scope": match_scope,
                    "project_codes": project_codes,
                    "project_acronyms": project_acronyms,
                    "project_funders": project_funders,
                    "instance_urls": instance_urls,
                    "instance_types": instance_types,
                    "hosted_by": hosted_by,
                    "pids": _extract_pids(item.get("pids", []) or []),
                    "matched_orcid": orcid,
                    "matched_researcher": full_name,
                    "source": "OpenAIRE Graph API",
                }
            )

        if page * page_size >= num_found:
            break
        page += 1
        time.sleep(sleep_seconds)

    return rows, {"orcid": orcid, "full_name": full_name, "num_found": num_found, "pages": page}


def aggregate_rows(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    precedence = {"cchen_ror_org": 0, "cchen_name_org": 1, "author_orcid_only": 2}
    df = df.copy()
    df["_match_order"] = df["match_scope"].map(precedence).fillna(9).astype(int)
    df = df.sort_values(["_match_order", "publication_date", "openaire_id"], ascending=[True, False, True])

    grouped_rows = []
    for openaire_id, group in df.groupby("openaire_id", dropna=False, sort=False):
        first = group.iloc[0].to_dict()
        first["matched_orcids"] = _join_unique(group["matched_orcid"].tolist())
        first["matched_researchers"] = _join_unique(group["matched_researcher"].tolist())
        first["matched_cchen_researchers_count"] = int(group["matched_orcid"].nunique())
        first["query_hits"] = int(len(group))
        grouped_rows.append(first)

    out = pd.DataFrame(grouped_rows)
    out = out.drop(columns=["matched_orcid", "matched_researcher", "_match_order"], errors="ignore")
    out = out.sort_values(["publication_date", "matched_cchen_researchers_count", "main_title"], ascending=[False, False, True]).reset_index(drop=True)
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--page-size", type=int, default=PAGE_SIZE)
    parser.add_argument("--sleep-seconds", type=float, default=0.05)
    parser.add_argument("--limit-authors", type=int, default=None)
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    researchers = pd.read_csv(RESEARCHERS_CSV)[["orcid_id", "full_name"]].dropna().drop_duplicates()
    if args.limit_authors:
        researchers = researchers.head(args.limit_authors)

    all_rows = []
    author_stats = []
    failures = []
    for _, row in researchers.iterrows():
        orcid = str(row["orcid_id"]).strip()
        full_name = str(row["full_name"]).strip()
        try:
            rows, stats = fetch_author_outputs(orcid, full_name, page_size=args.page_size, sleep_seconds=args.sleep_seconds)
            all_rows.extend(rows)
            author_stats.append(stats)
            print(f"[OK] {full_name} ({orcid}) -> {stats['num_found']} resultados")
        except Exception as exc:
            failures.append({"orcid": orcid, "full_name": full_name, "error": str(exc)})
            print(f"[WARN] {full_name} ({orcid}) -> {exc}")

    raw_df = pd.DataFrame(all_rows)
    df = aggregate_rows(raw_df)
    df.to_csv(OUT_CSV, index=False)

    author_stats_df = pd.DataFrame(author_stats)
    state = {
        "source": "OpenAIRE Graph API",
        "endpoint": OPENAIRE_API,
        "generated_at_utc": dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "authors_queried": int(len(researchers)),
        "authors_with_results": int((author_stats_df["num_found"] > 0).sum()) if not author_stats_df.empty else 0,
        "records_raw": int(len(raw_df)),
        "records_aggregated": int(len(df)),
        "page_size": int(args.page_size),
        "match_scope_counts": df["match_scope"].value_counts().to_dict() if not df.empty else {},
        "type_counts": df["type"].value_counts().to_dict() if not df.empty else {},
        "failures": failures,
    }
    OUT_STATE.write_text(json.dumps(state, indent=2, ensure_ascii=False))
    print(f"[OK] OpenAIRE outputs guardados en: {OUT_CSV}")
    print(f"     Registros agregados: {len(df)}")


if __name__ == "__main__":
    main()
