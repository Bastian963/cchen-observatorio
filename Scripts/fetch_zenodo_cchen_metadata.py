#!/usr/bin/env python3
"""Fetch Zenodo metadata with CCHEN-only filters.

This extractor intentionally does not download record files. It queries Zenodo
with controlled institutional aliases, keeps only records where a CCHEN alias is
visible in returned metadata, and stores file inventory metadata for later
review.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import html
import json
import os
import re
import time
import unicodedata
from pathlib import Path
from typing import Any

import requests


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "Data" / "ResearchOutputs"
OUT_CSV = OUT_DIR / "cchen_zenodo_metadata.csv"
FILES_CSV = OUT_DIR / "cchen_zenodo_files.csv"
STATE_JSON = OUT_DIR / "zenodo_cchen_state.json"

ZENODO_API = "https://zenodo.org/api/records"
CONTACT_EMAIL = os.getenv("CCHEN_CONTACT_EMAIL", "observatory@cchen.cl")
USER_AGENT = f"CCHEN-Observatory/1.0 (mailto:{CONTACT_EMAIL})"
TOKEN = os.getenv("ZENODO_TOKEN", "").strip()

CCHEN_ALIASES = [
    "Comision Chilena de Energia Nuclear",
    "Comisión Chilena de Energía Nuclear",
    "Chilean Nuclear Energy Commission",
    "CCHEN",
]

METADATA_COLUMNS = [
    "record_id",
    "conceptrecid",
    "doi",
    "conceptdoi",
    "title",
    "publication_date",
    "resource_type_type",
    "resource_type_title",
    "creators",
    "affiliations",
    "matched_aliases",
    "match_scope",
    "keywords",
    "communities",
    "license",
    "access_right",
    "url",
    "api_url",
    "file_count",
    "total_file_size_bytes",
    "total_file_size_mb",
    "file_names",
    "file_links",
    "description_snippet",
    "source_system",
    "fetched_at",
]

FILE_COLUMNS = [
    "record_id",
    "doi",
    "file_key",
    "file_type",
    "size_bytes",
    "checksum",
    "link_self",
    "source_system",
    "fetched_at",
]


class ZenodoError(RuntimeError):
    """Raised when the Zenodo API cannot be queried."""


def _today() -> str:
    return dt.date.today().isoformat()


def _compact(value: Any, limit: int = 500) -> str:
    text = " ".join(str(value or "").replace("\xa0", " ").split()).strip()
    return text[:limit]


def _strip_html(value: Any, limit: int = 900) -> str:
    text = re.sub(r"<[^>]+>", " ", str(value or ""))
    return _compact(html.unescape(text), limit)


def _norm(value: Any) -> str:
    text = _compact(value, 100000)
    text = "".join(
        char
        for char in unicodedata.normalize("NFKD", text)
        if not unicodedata.combining(char)
    )
    return text.lower()


def _contains_cchen(value: Any) -> tuple[bool, list[str]]:
    normalized = _norm(value)
    found: list[str] = []
    alias_map = {
        "comision chilena de energia nuclear": "Comision Chilena de Energia Nuclear",
        "chilean nuclear energy commission": "Chilean Nuclear Energy Commission",
    }
    for needle, label in alias_map.items():
        if needle in normalized:
            found.append(label)
    if re.search(r"(?<![a-z0-9])cchen(?![a-z0-9])", normalized):
        found.append("CCHEN")
    return bool(found), sorted(set(found))


def _join_unique(values: list[Any], *, limit: int = 2000) -> str:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        text = _compact(value, 500)
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
    return _compact("; ".join(out), limit)


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _resource_type(metadata: dict[str, Any]) -> tuple[str, str]:
    value = metadata.get("resource_type") or metadata.get("resourceType") or {}
    if isinstance(value, dict):
        return str(value.get("type", "") or value.get("id", "")), str(value.get("title", ""))
    return str(value), ""


def _creator_values(metadata: dict[str, Any]) -> tuple[str, str]:
    creators = []
    affiliations = []
    for creator in _as_list(metadata.get("creators")):
        if not isinstance(creator, dict):
            continue
        creators.append(creator.get("name", ""))
        affiliations.extend(_as_list(creator.get("affiliation")))
    return _join_unique(creators), _join_unique(affiliations)


def _communities(record: dict[str, Any]) -> str:
    values = []
    for community in _as_list(record.get("owners")) + _as_list(record.get("communities")):
        if isinstance(community, dict):
            values.append(community.get("title") or community.get("identifier") or community.get("id"))
        else:
            values.append(community)
    metadata = record.get("metadata") or {}
    for community in _as_list(metadata.get("communities")):
        if isinstance(community, dict):
            values.append(community.get("title") or community.get("identifier") or community.get("id"))
        else:
            values.append(community)
    return _join_unique(values)


def _license(metadata: dict[str, Any]) -> str:
    value = metadata.get("license") or metadata.get("rights") or ""
    if isinstance(value, dict):
        return str(value.get("id") or value.get("title") or value.get("license", ""))
    return str(value)


def _record_url(record: dict[str, Any]) -> str:
    links = record.get("links") or {}
    return str(links.get("html") or links.get("self_html") or record.get("doi_url") or "")


def _files(record: dict[str, Any]) -> list[dict[str, Any]]:
    files = record.get("files") or []
    if isinstance(files, dict):
        files = list(files.values())
    return [item for item in files if isinstance(item, dict)]


def _file_values(record: dict[str, Any]) -> tuple[int, int, str, str, list[dict[str, str]]]:
    rows: list[dict[str, str]] = []
    names: list[str] = []
    links: list[str] = []
    total_size = 0
    record_id = str(record.get("id") or "")
    metadata = record.get("metadata") or {}
    doi = str(metadata.get("doi") or record.get("doi") or "")
    fetched_at = _today()

    for item in _files(record):
        key = str(item.get("key") or item.get("filename") or "")
        size = int(item.get("size") or 0)
        link_self = str((item.get("links") or {}).get("self") or item.get("url") or "")
        file_type = str(item.get("type") or item.get("mimetype") or "")
        checksum = str(item.get("checksum") or "")
        total_size += size
        names.append(key)
        links.append(link_self)
        rows.append(
            {
                "record_id": record_id,
                "doi": doi,
                "file_key": key,
                "file_type": file_type,
                "size_bytes": str(size),
                "checksum": checksum,
                "link_self": link_self,
                "source_system": "Zenodo API",
                "fetched_at": fetched_at,
            }
        )
    return len(rows), total_size, _join_unique(names), _join_unique(links, limit=3000), rows


def _metadata_text(record: dict[str, Any]) -> str:
    metadata = record.get("metadata") or {}
    return json.dumps(metadata, ensure_ascii=False, sort_keys=True)


def _match_scope(record: dict[str, Any], affiliations: str, title: str, description: str) -> tuple[str, list[str]]:
    has_affiliation, aff_aliases = _contains_cchen(affiliations)
    if has_affiliation:
        return "creator_affiliation", aff_aliases
    has_title, title_aliases = _contains_cchen(title)
    if has_title:
        return "title", title_aliases
    has_description, desc_aliases = _contains_cchen(description)
    if has_description:
        return "description", desc_aliases
    has_metadata, metadata_aliases = _contains_cchen(_metadata_text(record))
    if has_metadata:
        return "metadata_text", metadata_aliases
    return "", []


def _row_from_record(record: dict[str, Any]) -> tuple[dict[str, str] | None, list[dict[str, str]]]:
    metadata = record.get("metadata") or {}
    title = _compact(metadata.get("title", ""), 700)
    creators, affiliations = _creator_values(metadata)
    description = _strip_html(metadata.get("description", ""))
    scope, aliases = _match_scope(record, affiliations, title, description)
    if not aliases:
        return None, []

    resource_type_type, resource_type_title = _resource_type(metadata)
    file_count, total_size, file_names, file_links, file_rows = _file_values(record)
    record_id = str(record.get("id") or "")
    api_url = str((record.get("links") or {}).get("self") or f"{ZENODO_API}/{record_id}")
    keywords = _join_unique(_as_list(metadata.get("keywords")))
    row = {
        "record_id": record_id,
        "conceptrecid": str(record.get("conceptrecid") or ""),
        "doi": str(metadata.get("doi") or record.get("doi") or ""),
        "conceptdoi": str(metadata.get("conceptdoi") or record.get("conceptdoi") or ""),
        "title": title,
        "publication_date": str(metadata.get("publication_date") or ""),
        "resource_type_type": resource_type_type,
        "resource_type_title": resource_type_title,
        "creators": creators,
        "affiliations": affiliations,
        "matched_aliases": "; ".join(aliases),
        "match_scope": scope,
        "keywords": keywords,
        "communities": _communities(record),
        "license": _license(metadata),
        "access_right": str(metadata.get("access_right") or ""),
        "url": _record_url(record),
        "api_url": api_url,
        "file_count": str(file_count),
        "total_file_size_bytes": str(total_size),
        "total_file_size_mb": f"{total_size / (1024 * 1024):.3f}",
        "file_names": file_names,
        "file_links": file_links,
        "description_snippet": description,
        "source_system": "Zenodo API",
        "fetched_at": _today(),
    }
    return row, file_rows


def _session(timeout: int) -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json"})
    if TOKEN:
        session.headers.update({"Authorization": f"Bearer {TOKEN}"})
    session.request_timeout = timeout  # type: ignore[attr-defined]
    return session


def _get_json(session: requests.Session, params: dict[str, Any]) -> dict[str, Any]:
    response = session.get(ZENODO_API, params=params, timeout=session.request_timeout)  # type: ignore[attr-defined]
    if response.status_code >= 400:
        raise ZenodoError(f"HTTP {response.status_code}: {_compact(response.text, 500)}")
    try:
        return response.json()
    except ValueError as exc:
        raise ZenodoError(f"Respuesta Zenodo no JSON: {exc}") from exc


def fetch_records(session: requests.Session, max_per_query: int, sleep_seconds: float) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    records: list[dict[str, Any]] = []
    queries: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for alias in CCHEN_ALIASES:
        page = 1
        collected_for_alias = 0
        total_hits = 0
        while collected_for_alias < max_per_query:
            page_limit = 100 if TOKEN else 25
            size = min(page_limit, max_per_query - collected_for_alias)
            params = {"q": f'"{alias}"', "page": page, "size": size, "all_versions": "false", "sort": "mostrecent"}
            data = _get_json(session, params)
            hits = (data.get("hits") or {}).get("hits") or []
            total_hits = int((data.get("hits") or {}).get("total") or total_hits or 0)
            if not hits:
                break
            for record in hits:
                record_id = str(record.get("id") or "")
                if record_id and record_id not in seen_ids:
                    seen_ids.add(record_id)
                    records.append(record)
                collected_for_alias += 1
            if len(hits) < size:
                break
            page += 1
            time.sleep(sleep_seconds)
        queries.append({"alias": alias, "records_seen": collected_for_alias, "total_hits": total_hits})
        time.sleep(sleep_seconds)
    return records, queries


def _dedupe_rows(rows: list[dict[str, str]], key_fields: list[str]) -> list[dict[str, str]]:
    seen: set[str] = set()
    out: list[dict[str, str]] = []
    for row in rows:
        key = "|".join(row.get(field, "") for field in key_fields).strip("|") or "|".join(row.values())
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


def write_csv(path: Path, rows: list[dict[str, str]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extrae metadatos Zenodo CCHEN-only sin descargar archivos.")
    parser.add_argument("--max-per-query", type=int, default=100, help="Maximo de registros Zenodo revisados por alias.")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout HTTP por request.")
    parser.add_argument("--sleep", type=float, default=0.25, help="Pausa entre requests.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    session = _session(args.timeout)
    raw_records, queries = fetch_records(session, args.max_per_query, args.sleep)

    metadata_rows: list[dict[str, str]] = []
    file_rows: list[dict[str, str]] = []
    for record in raw_records:
        row, rows_files = _row_from_record(record)
        if row is None:
            continue
        metadata_rows.append(row)
        file_rows.extend(rows_files)

    metadata_rows = _dedupe_rows(metadata_rows, ["record_id"])
    file_rows = _dedupe_rows(file_rows, ["record_id", "file_key"])
    metadata_rows.sort(key=lambda row: (row.get("publication_date", ""), row.get("title", "")), reverse=True)
    file_rows.sort(key=lambda row: (row.get("record_id", ""), row.get("file_key", "")))

    write_csv(OUT_CSV, metadata_rows, METADATA_COLUMNS)
    write_csv(FILES_CSV, file_rows, FILE_COLUMNS)
    STATE_JSON.parent.mkdir(parents=True, exist_ok=True)
    STATE_JSON.write_text(
        json.dumps(
            {
                "updated": dt.datetime.now().isoformat(timespec="seconds"),
                "source": "Zenodo API",
                "api_url": ZENODO_API,
                "token_used": bool(TOKEN),
                "aliases": CCHEN_ALIASES,
                "queries": queries,
                "raw_records_seen": len(raw_records),
                "metadata_records_written": len(metadata_rows),
                "file_rows_written": len(file_rows),
                "outputs": [
                    str(OUT_CSV.relative_to(ROOT)),
                    str(FILES_CSV.relative_to(ROOT)),
                    str(STATE_JSON.relative_to(ROOT)),
                ],
                "policy": "metadata_only_no_file_download",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print(f"[OK] Zenodo metadata CCHEN -> {OUT_CSV.relative_to(ROOT)} ({len(metadata_rows)} filas)")
    print(f"[OK] Zenodo archivos asociados -> {FILES_CSV.relative_to(ROOT)} ({len(file_rows)} filas)")
    print(f"[OK] Zenodo estado -> {STATE_JSON.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
