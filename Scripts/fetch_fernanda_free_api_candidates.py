#!/usr/bin/env python3
"""Probe Fernanda's free API candidates with CCHEN-only filters.

The goal is not to harvest entire external databases. Each source is queried
only with institutional aliases or is explicitly documented as skipped when it
does not expose a safe CCHEN filter, requires credentials, or needs a thematic
decision before implementation.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import re
import time
import unicodedata
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests


ROOT = Path(__file__).resolve().parents[1]
GOV_DIR = ROOT / "Data" / "Gobernanza"
RECORDS_CSV = GOV_DIR / "fuentes_fernanda_api_cchen_records.csv"
STATUS_CSV = GOV_DIR / "fuentes_fernanda_api_cchen_status.csv"
STATE_JSON = GOV_DIR / "fuentes_fernanda_api_cchen_state.json"

CONTACT_EMAIL = os.getenv("CCHEN_CONTACT_EMAIL", "observatory@cchen.cl")
USER_AGENT = f"CCHEN-Observatory/1.0 (mailto:{CONTACT_EMAIL})"

CCHEN_ALIASES = [
    "Comisión Chilena de Energía Nuclear",
    "Comision Chilena de Energia Nuclear",
    "Chilean Nuclear Energy Commission",
    "CCHEN",
]

RECORD_COLUMNS = [
    "source_key",
    "source_name",
    "query",
    "status",
    "cchen_filter_strategy",
    "api_url",
    "record_id",
    "title",
    "url",
    "published",
    "doi",
    "snippet",
    "fetched_at",
]

STATUS_COLUMNS = [
    "source_key",
    "source_name",
    "api_url",
    "access_type",
    "cchen_filter_strategy",
    "status",
    "records_written",
    "queries_tested",
    "error_summary",
    "fetched_at",
    "notes",
]

STATIC_SKIPS = [
    {
        "source_key": "biorxiv",
        "source_name": "bioRxiv",
        "api_url": "https://api.biorxiv.org/",
        "status": "skipped_no_safe_cchen_filter",
        "notes": "API gratuita por fecha/DOI; no ofrece búsqueda institucional/texto libre segura sin crawlear ventanas amplias.",
    },
    {
        "source_key": "medrxiv",
        "source_name": "medRxiv",
        "api_url": "https://api.medrxiv.org/",
        "status": "skipped_no_safe_cchen_filter",
        "notes": "API gratuita por fecha/DOI; usar solo si aparece DOI CCHEN conocido o se define ventana acotada.",
    },
    {
        "source_key": "pubchem",
        "source_name": "PubChem",
        "api_url": "https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest",
        "status": "skipped_no_institution_filter",
        "notes": "API gratuita Bio/Farma, pero no filtra por afiliación CCHEN; requiere lista interna de moléculas/radiofármacos.",
    },
    {
        "source_key": "string_db",
        "source_name": "STRING",
        "api_url": "https://string-db.org/help/api/",
        "status": "skipped_no_institution_filter",
        "notes": "API gratuita para proteínas/interacciones; requiere semillas temáticas CCHEN antes de consultar.",
    },
    {
        "source_key": "epo_ops",
        "source_name": "EPO OPS / Espacenet",
        "api_url": "https://developers.epo.org/",
        "status": "skipped_requires_registration",
        "notes": "Candidata de patentes; priorizar después de INAPI y PatentsView. Requiere credenciales OPS.",
    },
    {
        "source_key": "wipo_patentscope",
        "source_name": "WIPO PATENTSCOPE",
        "api_url": "https://www.wipo.int/patentscope/",
        "status": "skipped_access_review",
        "notes": "Base pública útil para patentes, pero API/descarga masiva requiere validar acceso y términos.",
    },
]


class ProbeError(RuntimeError):
    """Raised when a source cannot be queried."""


def _now_date() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d")


def _norm(value: Any) -> str:
    text = " ".join(str(value or "").replace("\xa0", " ").split()).strip()
    text = "".join(
        char
        for char in unicodedata.normalize("NFKD", text)
        if not unicodedata.combining(char)
    )
    return text.lower()


def _compact(value: Any, limit: int = 500) -> str:
    text = " ".join(str(value or "").split())
    return text[:limit]


def _contains_cchen(value: Any) -> bool:
    text = _norm(value)
    if not text:
        return False
    long_aliases = [
        "comision chilena de energia nuclear",
        "chilean nuclear energy commission",
    ]
    if any(alias in text for alias in long_aliases):
        return True
    return re.search(r"(?<![a-z0-9])cchen(?![a-z0-9])", text) is not None


def _session(timeout: int) -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json"})
    session.request_timeout = timeout  # type: ignore[attr-defined]
    return session


def _get_json(session: requests.Session, url: str, *, params: dict[str, Any] | None = None) -> dict[str, Any]:
    response = session.get(url, params=params, timeout=session.request_timeout)  # type: ignore[attr-defined]
    if response.status_code >= 400:
        raise ProbeError(f"HTTP {response.status_code}: {_compact(response.text, 300)}")
    try:
        return response.json()
    except ValueError as exc:
        raise ProbeError(f"Respuesta no JSON: {exc}") from exc


def _post_json(session: requests.Session, url: str, *, payload: dict[str, Any]) -> Any:
    response = session.post(url, json=payload, timeout=session.request_timeout)  # type: ignore[attr-defined]
    if response.status_code >= 400:
        raise ProbeError(f"HTTP {response.status_code}: {_compact(response.text, 300)}")
    try:
        return response.json()
    except ValueError as exc:
        raise ProbeError(f"Respuesta no JSON: {exc}") from exc


def _record(
    *,
    source_key: str,
    source_name: str,
    query: str,
    api_url: str,
    record_id: str,
    title: str,
    url: str,
    published: str = "",
    doi: str = "",
    snippet: str = "",
) -> dict[str, str]:
    return {
        "source_key": source_key,
        "source_name": source_name,
        "query": query,
        "status": "cchen_match",
        "cchen_filter_strategy": "texto libre con aliases institucionales CCHEN; se descartan resultados sin alias visible",
        "api_url": api_url,
        "record_id": record_id,
        "title": _compact(title, 350),
        "url": url,
        "published": published,
        "doi": doi,
        "snippet": _compact(snippet, 600),
        "fetched_at": _now_date(),
    }


def probe_doaj(session: requests.Session, max_records: int) -> tuple[list[dict[str, str]], int]:
    rows: list[dict[str, str]] = []
    queries = 0
    base = "https://doaj.org/api/v4/search/articles"
    for alias in CCHEN_ALIASES:
        queries += 1
        query = f'"{alias}"'
        data = _get_json(
            session,
            f"{base}/{quote(query, safe='')}",
            params={"page": 1, "pageSize": min(max_records, 25)},
        )
        for item in data.get("results", []) or []:
            bib = item.get("bibjson", {}) or {}
            text_blob = json.dumps(bib, ensure_ascii=False)
            if not _contains_cchen(text_blob):
                continue
            identifiers = bib.get("identifier", []) or []
            doi = next((x.get("id", "") for x in identifiers if str(x.get("type", "")).lower() == "doi"), "")
            links = bib.get("link", []) or []
            url = next((x.get("url", "") for x in links if x.get("url")), "")
            if doi and not url:
                url = f"https://doi.org/{doi}"
            title = bib.get("title", "")
            record_id = doi or url or f"doaj:{hash(text_blob)}"
            rows.append(
                _record(
                    source_key="doaj",
                    source_name="DOAJ",
                    query=query,
                    api_url=base,
                    record_id=record_id,
                    title=title,
                    url=url,
                    published=str(bib.get("year", "")),
                    doi=doi,
                    snippet=text_blob,
                )
            )
            if len(rows) >= max_records:
                return rows, queries
        time.sleep(0.2)
    return rows, queries


def probe_hal(session: requests.Session, max_records: int) -> tuple[list[dict[str, str]], int]:
    rows: list[dict[str, str]] = []
    queries = 0
    base = "https://api.hal.science/search/"
    fields = "docid,title_s,label_s,uri_s,doiId_s,producedDate_s,abstract_s,structName_s,authFullName_s"
    for alias in CCHEN_ALIASES:
        queries += 1
        query = f'"{alias}"'
        data = _get_json(
            session,
            base,
            params={"q": query, "rows": min(max_records, 25), "wt": "json", "fl": fields},
        )
        docs = ((data.get("response") or {}).get("docs") or [])
        for doc in docs:
            text_blob = json.dumps(doc, ensure_ascii=False)
            if not _contains_cchen(text_blob):
                continue
            title_value = doc.get("title_s") or doc.get("label_s") or ""
            if isinstance(title_value, list):
                title_value = title_value[0] if title_value else ""
            rows.append(
                _record(
                    source_key="hal",
                    source_name="HAL",
                    query=query,
                    api_url=base,
                    record_id=str(doc.get("docid", "")),
                    title=str(title_value),
                    url=str(doc.get("uri_s", "")),
                    published=str(doc.get("producedDate_s", "")),
                    doi=str(doc.get("doiId_s", "")),
                    snippet=text_blob,
                )
            )
            if len(rows) >= max_records:
                return rows, queries
        time.sleep(0.2)
    return rows, queries


def probe_figshare(session: requests.Session, max_records: int) -> tuple[list[dict[str, str]], int]:
    rows: list[dict[str, str]] = []
    queries = 0
    base = "https://api.figshare.com/v2/articles/search"
    for alias in CCHEN_ALIASES:
        queries += 1
        payload = {
            "search_for": alias,
            "page_size": min(max_records, 25),
            "order": "published_date",
            "order_direction": "desc",
        }
        data = _post_json(session, base, payload=payload)
        if not isinstance(data, list):
            continue
        for item in data:
            text_blob = json.dumps(item, ensure_ascii=False)
            if not _contains_cchen(text_blob):
                continue
            url = str(item.get("url_public_html") or item.get("url") or "")
            doi = str(item.get("doi", ""))
            rows.append(
                _record(
                    source_key="figshare",
                    source_name="Figshare",
                    query=alias,
                    api_url=base,
                    record_id=str(item.get("id", "")),
                    title=str(item.get("title", "")),
                    url=url,
                    published=str(item.get("published_date", ""))[:10],
                    doi=doi,
                    snippet=text_blob,
                )
            )
            if len(rows) >= max_records:
                return rows, queries
        time.sleep(0.2)
    return rows, queries


def probe_core(session: requests.Session, max_records: int) -> tuple[list[dict[str, str]], int]:
    rows: list[dict[str, str]] = []
    queries = 0
    base = "https://api.core.ac.uk/v3/search/works"
    # Use long aliases first. CORE can expand "CCHEN" into noisy author-name hits.
    aliases = [alias for alias in CCHEN_ALIASES if alias != "CCHEN"] + ["CCHEN"]
    errors: list[str] = []
    for alias in aliases:
        queries += 1
        query = f'"{alias}"'
        try:
            data = _get_json(session, base, params={"q": query, "limit": min(max_records, 25)})
        except ProbeError as exc:
            errors.append(f"{query}: {exc}")
            continue
        for item in data.get("results", []) or []:
            text_blob = json.dumps(item, ensure_ascii=False)
            if not _contains_cchen(text_blob):
                continue
            doi = str(item.get("doi") or "")
            outputs = item.get("outputs") or []
            url = str(item.get("downloadUrl") or (outputs[0] if outputs else ""))
            rows.append(
                _record(
                    source_key="core",
                    source_name="CORE",
                    query=query,
                    api_url=base,
                    record_id=str(item.get("id") or item.get("oai") or doi),
                    title=str(item.get("title", "")),
                    url=url,
                    published=str(item.get("publishedDate") or item.get("yearPublished") or ""),
                    doi=doi,
                    snippet=text_blob,
                )
            )
            if len(rows) >= max_records:
                return rows, queries
        time.sleep(0.2)
    if errors and not rows:
        raise ProbeError("; ".join(errors)[:600])
    return rows, queries


def probe_base(session: requests.Session, max_records: int) -> tuple[list[dict[str, str]], int]:
    rows: list[dict[str, str]] = []
    queries = 0
    base = "https://api.base-search.net/cgi-bin/BaseHttpSearchInterface.fcgi"
    for alias in CCHEN_ALIASES[:3]:
        queries += 1
        query = f'"{alias}"'
        data = _get_json(
            session,
            base,
            params={"func": "PerformSearch", "query": query, "hits": min(max_records, 25), "format": "json"},
        )
        if data.get("error"):
            raise ProbeError(str(data["error"]))
        docs = ((data.get("response") or {}).get("docs") or data.get("docs") or [])
        for doc in docs:
            text_blob = json.dumps(doc, ensure_ascii=False)
            if not _contains_cchen(text_blob):
                continue
            doi = str(doc.get("doi", ""))
            rows.append(
                _record(
                    source_key="base",
                    source_name="BASE",
                    query=query,
                    api_url=base,
                    record_id=str(doc.get("id") or doi),
                    title=str(doc.get("title", "")),
                    url=str(doc.get("link") or doc.get("url") or ""),
                    published=str(doc.get("year") or doc.get("date") or ""),
                    doi=doi,
                    snippet=text_blob,
                )
            )
            if len(rows) >= max_records:
                return rows, queries
        time.sleep(0.2)
    return rows, queries


def probe_uniprot(session: requests.Session, max_records: int) -> tuple[list[dict[str, str]], int]:
    rows: list[dict[str, str]] = []
    queries = 0
    base = "https://rest.uniprot.org/uniprotkb/search"
    for alias in CCHEN_ALIASES:
        queries += 1
        data = _get_json(
            session,
            base,
            params={
                "query": alias,
                "fields": "accession,id,protein_name,organism_name",
                "format": "json",
                "size": min(max_records, 25),
            },
        )
        for item in data.get("results", []) or []:
            text_blob = json.dumps(item, ensure_ascii=False)
            if not _contains_cchen(text_blob):
                continue
            accession = str(item.get("primaryAccession", ""))
            rows.append(
                _record(
                    source_key="uniprot",
                    source_name="UniProt",
                    query=alias,
                    api_url=base,
                    record_id=accession,
                    title=str(item.get("uniProtkbId", "")),
                    url=f"https://www.uniprot.org/uniprotkb/{accession}/entry" if accession else "",
                    snippet=text_blob,
                )
            )
            if len(rows) >= max_records:
                return rows, queries
        time.sleep(0.2)
    return rows, queries


PROBES = [
    ("doaj", "DOAJ", "https://doaj.org/api/v4/search/articles", "abierta", probe_doaj),
    ("hal", "HAL", "https://api.hal.science/search/", "abierta", probe_hal),
    ("figshare", "Figshare", "https://api.figshare.com/v2/articles/search", "abierta", probe_figshare),
    ("core", "CORE", "https://api.core.ac.uk/v3/search/works", "abierta", probe_core),
    ("base", "BASE", "https://api.base-search.net/cgi-bin/BaseHttpSearchInterface.fcgi", "abierta_con_restriccion_ip_ua", probe_base),
    ("uniprot", "UniProt", "https://rest.uniprot.org/uniprotkb/search", "abierta", probe_uniprot),
]


def _status_row(
    *,
    source_key: str,
    source_name: str,
    api_url: str,
    access_type: str,
    status: str,
    records_written: int,
    queries_tested: int,
    error_summary: str = "",
    notes: str = "",
) -> dict[str, str]:
    return {
        "source_key": source_key,
        "source_name": source_name,
        "api_url": api_url,
        "access_type": access_type,
        "cchen_filter_strategy": "aliases institucionales CCHEN / afiliación / texto libre exacto",
        "status": status,
        "records_written": str(records_written),
        "queries_tested": str(queries_tested),
        "error_summary": _compact(error_summary, 700),
        "fetched_at": _now_date(),
        "notes": notes,
    }


def _write_csv(path: Path, rows: list[dict[str, str]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _dedupe_records(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[tuple[str, str]] = set()
    deduped: list[dict[str, str]] = []
    for row in rows:
        key = (row.get("source_key", ""), row.get("record_id", "") or row.get("url", "") or row.get("title", ""))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prueba APIs gratuitas de Fernanda con filtros CCHEN-only.")
    parser.add_argument("--max-per-source", type=int, default=25, help="Máximo de registros guardados por fuente.")
    parser.add_argument("--timeout", type=int, default=25, help="Timeout HTTP por request.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    session = _session(args.timeout)
    all_records: list[dict[str, str]] = []
    statuses: list[dict[str, str]] = []

    for source_key, source_name, api_url, access_type, probe in PROBES:
        try:
            records, queries = probe(session, args.max_per_source)
            records = _dedupe_records(records)
            all_records.extend(records)
            status = "success" if records else "success_zero_cchen_records"
            note = "API respondió; resultados guardados solo si contienen alias CCHEN visible."
            if source_key in {"uniprot"} and not records:
                note = "API respondió, pero no hay filtro institucional ni resultados CCHEN visibles; requiere semillas temáticas."
            statuses.append(
                _status_row(
                    source_key=source_key,
                    source_name=source_name,
                    api_url=api_url,
                    access_type=access_type,
                    status=status,
                    records_written=len(records),
                    queries_tested=queries,
                    notes=note,
                )
            )
        except ProbeError as exc:
            statuses.append(
                _status_row(
                    source_key=source_key,
                    source_name=source_name,
                    api_url=api_url,
                    access_type=access_type,
                    status="failed_probe",
                    records_written=0,
                    queries_tested=1,
                    error_summary=str(exc),
                    notes="No bloquear adjudicación; documentar acceso o ajustar endpoint antes de implementar.",
                )
            )

    for skipped in STATIC_SKIPS:
        statuses.append(
            _status_row(
                source_key=skipped["source_key"],
                source_name=skipped["source_name"],
                api_url=skipped["api_url"],
                access_type="candidata",
                status=skipped["status"],
                records_written=0,
                queries_tested=0,
                notes=skipped["notes"],
            )
        )

    all_records = _dedupe_records(all_records)
    _write_csv(RECORDS_CSV, all_records, RECORD_COLUMNS)
    _write_csv(STATUS_CSV, statuses, STATUS_COLUMNS)
    STATE_JSON.write_text(
        json.dumps(
            {
                "updated": dt.datetime.now().isoformat(timespec="seconds"),
                "records": len(all_records),
                "sources": len(statuses),
                "aliases": CCHEN_ALIASES,
                "outputs": [str(RECORDS_CSV.relative_to(ROOT)), str(STATUS_CSV.relative_to(ROOT))],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    ok_sources = sum(1 for row in statuses if row["status"].startswith("success"))
    print(f"[OK] registros CCHEN-only -> {RECORDS_CSV.relative_to(ROOT)} ({len(all_records)} filas)")
    print(f"[OK] estado por fuente -> {STATUS_CSV.relative_to(ROOT)} ({len(statuses)} fuentes; {ok_sources} respondieron)")
    print(f"[OK] estado JSON -> {STATE_JSON.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
