#!/usr/bin/env python3
"""Seeded radio-pharmacy extraction for the CCHEN observatory.

The extractor intentionally avoids downloading broad Bio/Farma corpora. It
uses a controlled seed list of radio-pharmaceutical compounds, radionuclides,
and CCHEN-relevant topics, then queries only APIs that can be kept narrow:
PubChem for compound facts, Europe PMC and PubMed for literature.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import requests


ROOT = Path(__file__).resolve().parents[1]
GOV_DIR = ROOT / "Data" / "Gobernanza"
SEEDS_CSV = GOV_DIR / "radiofarmacia_cchen_seeds.csv"
PUBCHEM_CSV = GOV_DIR / "radiofarmacia_cchen_pubchem_compounds.csv"
LITERATURE_CSV = GOV_DIR / "radiofarmacia_cchen_literature.csv"
STATUS_CSV = GOV_DIR / "radiofarmacia_cchen_status.csv"
STATE_JSON = GOV_DIR / "radiofarmacia_cchen_state.json"

CONTACT = os.getenv("CCHEN_CONTACT_EMAIL", "observatory@cchen.cl")
USER_AGENT = f"CCHEN-Observatory/1.0 (mailto:{CONTACT})"

PUBCHEM_PROPERTIES = "Title,MolecularFormula,MolecularWeight,CanonicalSMILES,InChIKey"
PUBCHEM_BASE = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name"
EUROPEPMC_BASE = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
PUBMED_SEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_FETCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

SEED_COLUMNS = [
    "seed_key",
    "seed_label",
    "seed_type",
    "pubchem_names",
    "literature_terms",
    "scope_terms",
    "priority",
    "notes",
]

PUBCHEM_COLUMNS = [
    "seed_key",
    "seed_label",
    "compound_query",
    "cid",
    "title",
    "molecular_formula",
    "molecular_weight",
    "canonical_smiles",
    "inchi_key",
    "pubchem_url",
    "fetched_at",
]

LITERATURE_COLUMNS = [
    "seed_key",
    "seed_label",
    "source_system",
    "source_id",
    "doi",
    "pmid",
    "pmcid",
    "title",
    "authors",
    "journal",
    "year",
    "url",
    "abstract",
    "query",
    "fetched_at",
]

STATUS_COLUMNS = [
    "seed_key",
    "seed_label",
    "source_system",
    "query",
    "records_written",
    "status",
    "error_summary",
    "fetched_at",
]

DEFAULT_SEEDS = [
    {
        "seed_key": "f18_fdg",
        "seed_label": "F-18 FDG / Fludeoxyglucose",
        "seed_type": "radiofarmaco_pet",
        "pubchem_names": "Fludeoxyglucose F-18|Fluorodeoxyglucose F18",
        "literature_terms": '"Fluorodeoxyglucose F18" OR "Fludeoxyglucose F 18" OR "F-18 FDG" OR "18F-FDG" OR FDG',
        "scope_terms": 'CCHEN OR Chile OR "Latin America" OR "medical cyclotron" OR "hospital cyclotron" OR "isotope production"',
        "priority": "alta",
        "notes": "PET; producción/uso clínico; compuesto directo para PubChem.",
    },
    {
        "seed_key": "ga68_dotatate",
        "seed_label": "Ga-68 DOTATATE",
        "seed_type": "radiofarmaco_pet",
        "pubchem_names": "Gallium Ga 68 dotatate|68Ga-DOTATATE",
        "literature_terms": '"Ga-68 DOTATATE" OR "Gallium-68 DOTATATE" OR "68Ga-DOTATATE"',
        "scope_terms": 'CCHEN OR Chile OR "Latin America"',
        "priority": "alta",
        "notes": "PET neuroendocrino/teranóstico; requiere vigilancia global acotada.",
    },
    {
        "seed_key": "lu177_dotatate",
        "seed_label": "Lu-177 DOTATATE",
        "seed_type": "radioterapia_metabolica",
        "pubchem_names": "Lutetium Lu 177 dotatate|177Lu-DOTATATE",
        "literature_terms": '"Lu-177 DOTATATE" OR "Lutetium-177 DOTATATE" OR "177Lu-DOTATATE"',
        "scope_terms": 'CCHEN OR Chile OR "Latin America"',
        "priority": "alta",
        "notes": "Terapia con radionúclidos; seguimiento clínico y técnico.",
    },
    {
        "seed_key": "tc99m_sestamibi",
        "seed_label": "Tc-99m sestamibi",
        "seed_type": "radiofarmaco_spect",
        "pubchem_names": "Technetium Tc 99m sestamibi|Technetium (99mTc) sestamibi",
        "literature_terms": '"Tc-99m sestamibi" OR "Technetium Tc 99m sestamibi" OR "99mTc-sestamibi"',
        "scope_terms": 'CCHEN OR Chile OR "Latin America"',
        "priority": "media",
        "notes": "SPECT; uso clínico amplio y control de disponibilidad.",
    },
    {
        "seed_key": "i131",
        "seed_label": "I-131",
        "seed_type": "radionuclido_terapia",
        "pubchem_names": "Iodine I 131|Iodine-131",
        "literature_terms": '"I-131" OR "Iodine-131" OR radioiodine',
        "scope_terms": 'CCHEN OR Chile OR "Latin America" OR radioprotection',
        "priority": "media",
        "notes": "Terapia/diagnóstico tiroideo; vigilancia clínica y radioprotección.",
    },
    {
        "seed_key": "ciclotron_f18",
        "seed_label": "Ciclotrón / producción F-18",
        "seed_type": "capacidad_productiva",
        "pubchem_names": "",
        "literature_terms": 'cyclotron OR ciclotron OR "fluorine-18" OR "fluor-18" OR "F-18"',
        "scope_terms": 'CCHEN OR Chile OR "Latin America" OR "isotope production" OR "medical cyclotron"',
        "priority": "alta",
        "notes": "Capacidad productiva y seguridad operacional; no es compuesto PubChem.",
    },
    {
        "seed_key": "control_calidad_radiofarmacos",
        "seed_label": "Control de calidad de radiofármacos",
        "seed_type": "calidad_regulacion",
        "pubchem_names": "",
        "literature_terms": '"radiopharmaceutical quality control" OR "control de calidad de radiofarmacos" OR "good manufacturing practice"',
        "scope_terms": 'CCHEN OR Chile OR "Latin America"',
        "priority": "alta",
        "notes": "GMP, control de calidad y aseguramiento técnico.",
    },
    {
        "seed_key": "dosimetria_medicina_nuclear",
        "seed_label": "Dosimetría en medicina nuclear",
        "seed_type": "dosimetria",
        "pubchem_names": "",
        "literature_terms": '"nuclear medicine dosimetry" OR "dosimetria medicina nuclear" OR "internal dosimetry"',
        "scope_terms": 'CCHEN OR Chile OR "Latin America"',
        "priority": "alta",
        "notes": "Línea transversal con protección radiológica y uso clínico.",
    },
]


def _today() -> str:
    return dt.date.today().isoformat()


def _compact(value: Any, limit: int = 1200) -> str:
    return " ".join(str(value or "").split())[:limit]


def ensure_seed_file(path: Path = SEEDS_CSV) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=SEED_COLUMNS)
        writer.writeheader()
        writer.writerows(DEFAULT_SEEDS)


def read_seeds(path: Path = SEEDS_CSV) -> list[dict[str, str]]:
    ensure_seed_file(path)
    with path.open(newline="", encoding="utf-8") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def write_csv(path: Path, rows: list[dict[str, str]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _session(timeout: int) -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json"})
    session.request_timeout = timeout  # type: ignore[attr-defined]
    return session


def _status(seed: dict[str, str], source: str, query: str, records: int, status: str, error: str = "") -> dict[str, str]:
    return {
        "seed_key": seed["seed_key"],
        "seed_label": seed["seed_label"],
        "source_system": source,
        "query": query,
        "records_written": str(records),
        "status": status,
        "error_summary": _compact(error, 500),
        "fetched_at": _today(),
    }


def fetch_pubchem(session: requests.Session, seed: dict[str, str]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    rows: list[dict[str, str]] = []
    statuses: list[dict[str, str]] = []
    names = [name.strip() for name in seed.get("pubchem_names", "").split("|") if name.strip()]
    if not names:
        return rows, [_status(seed, "PubChem", "", 0, "skipped_no_compound_seed")]

    for name in names:
        url = f"{PUBCHEM_BASE}/{requests.utils.quote(name)}/property/{PUBCHEM_PROPERTIES}/JSON"
        try:
            response = session.get(url, timeout=session.request_timeout)  # type: ignore[attr-defined]
            if response.status_code >= 400:
                statuses.append(_status(seed, "PubChem", name, 0, "failed", response.text[:300]))
                continue
            props = response.json().get("PropertyTable", {}).get("Properties", [])
            for prop in props[:3]:
                cid = str(prop.get("CID", ""))
                rows.append(
                    {
                        "seed_key": seed["seed_key"],
                        "seed_label": seed["seed_label"],
                        "compound_query": name,
                        "cid": cid,
                        "title": str(prop.get("Title", "")),
                        "molecular_formula": str(prop.get("MolecularFormula", "")),
                        "molecular_weight": str(prop.get("MolecularWeight", "")),
                        "canonical_smiles": str(prop.get("CanonicalSMILES", "")),
                        "inchi_key": str(prop.get("InChIKey", "")),
                        "pubchem_url": f"https://pubchem.ncbi.nlm.nih.gov/compound/{cid}" if cid else "",
                        "fetched_at": _today(),
                    }
                )
            statuses.append(_status(seed, "PubChem", name, len(props[:3]), "success" if props else "success_zero_records"))
            time.sleep(0.2)
        except Exception as exc:
            statuses.append(_status(seed, "PubChem", name, 0, "failed", str(exc)))
    return rows, statuses


def _literature_query(seed: dict[str, str]) -> str:
    terms = seed.get("literature_terms", "").strip()
    scope = seed.get("scope_terms", "").strip()
    return f"({terms}) AND ({scope})" if terms and scope else terms or scope


def fetch_europepmc(session: requests.Session, seed: dict[str, str], max_results: int) -> tuple[list[dict[str, str]], dict[str, str]]:
    query = _literature_query(seed)
    if not query:
        return [], _status(seed, "EuropePMC", "", 0, "skipped_no_query")
    params = {
        "query": query,
        "format": "json",
        "pageSize": max_results,
        "resultType": "core",
    }
    try:
        response = session.get(EUROPEPMC_BASE, params=params, timeout=session.request_timeout)  # type: ignore[attr-defined]
        if response.status_code >= 400:
            return [], _status(seed, "EuropePMC", query, 0, "failed", response.text[:300])
        data = response.json()
        results = data.get("resultList", {}).get("result", []) or []
        rows = []
        for result in results[:max_results]:
            source = str(result.get("source", ""))
            source_id = str(result.get("id", ""))
            author_list = result.get("authorString", "")
            abstract = result.get("abstractText", "")
            rows.append(
                {
                    "seed_key": seed["seed_key"],
                    "seed_label": seed["seed_label"],
                    "source_system": "EuropePMC",
                    "source_id": f"{source}{source_id}",
                    "doi": str(result.get("doi", "")),
                    "pmid": str(result.get("pmid", "")),
                    "pmcid": str(result.get("pmcid", "")),
                    "title": _compact(result.get("title", ""), 500),
                    "authors": _compact(author_list, 500),
                    "journal": _compact(result.get("journalTitle", ""), 250),
                    "year": str(result.get("pubYear", "")),
                    "url": f"https://europepmc.org/article/{source}/{source_id}",
                    "abstract": _compact(abstract, 2000),
                    "query": query,
                    "fetched_at": _today(),
                }
            )
        return rows, _status(seed, "EuropePMC", query, len(rows), "success" if rows else "success_zero_records")
    except Exception as exc:
        return [], _status(seed, "EuropePMC", query, 0, "failed", str(exc))


def _pubmed_query(seed: dict[str, str]) -> str:
    terms = seed.get("literature_terms", "").strip()
    scope = seed.get("scope_terms", "").strip()
    return f"({terms}) AND ({scope})" if terms and scope else terms or scope


def pubmed_search(session: requests.Session, query: str, max_results: int) -> list[str]:
    params = {
        "db": "pubmed",
        "term": query,
        "retmax": max_results,
        "retmode": "json",
        "tool": "CCHEN-Observatory",
        "email": CONTACT,
    }
    response = session.get(PUBMED_SEARCH, params=params, timeout=session.request_timeout)  # type: ignore[attr-defined]
    if response.status_code >= 400:
        raise RuntimeError(response.text[:300])
    return response.json().get("esearchresult", {}).get("idlist", []) or []


def _xml_text(element: ET.Element, path: str) -> str:
    found = element.find(path)
    return (found.text or "").strip() if found is not None else ""


def pubmed_fetch(session: requests.Session, pmids: list[str]) -> list[dict[str, str]]:
    if not pmids:
        return []
    params = {
        "db": "pubmed",
        "id": ",".join(pmids),
        "retmode": "xml",
        "rettype": "abstract",
        "tool": "CCHEN-Observatory",
        "email": CONTACT,
    }
    response = session.get(PUBMED_FETCH, params=params, timeout=session.request_timeout)  # type: ignore[attr-defined]
    if response.status_code >= 400:
        raise RuntimeError(response.text[:300])
    root = ET.fromstring(response.content)
    rows: list[dict[str, str]] = []
    for article_node in root.findall(".//PubmedArticle"):
        citation = article_node.find("MedlineCitation")
        article = citation.find("Article") if citation is not None else None
        pubmed_data = article_node.find("PubmedData")
        if citation is None or article is None:
            continue
        pmid = _xml_text(citation, "PMID")
        title = _xml_text(article, "ArticleTitle")
        abstract_parts = []
        for item in article.findall(".//AbstractText"):
            if item.text:
                abstract_parts.append(item.text)
        authors = []
        for author in article.findall(".//Author")[:10]:
            last = _xml_text(author, "LastName")
            fore = _xml_text(author, "ForeName") or _xml_text(author, "Initials")
            name = f"{last} {fore}".strip()
            if name:
                authors.append(name)
        journal = _xml_text(article, "Journal/Title") or _xml_text(article, "Journal/ISOAbbreviation")
        year = _xml_text(article, ".//JournalIssue/PubDate/Year")
        doi = pmcid = ""
        if pubmed_data is not None:
            for article_id in pubmed_data.findall(".//ArticleId"):
                if article_id.get("IdType") == "doi":
                    doi = article_id.text or ""
                elif article_id.get("IdType") == "pmc":
                    pmcid = article_id.text or ""
        rows.append(
            {
                "source_system": "PubMed",
                "source_id": pmid,
                "doi": doi,
                "pmid": pmid,
                "pmcid": pmcid,
                "title": _compact(title, 500),
                "authors": _compact("; ".join(authors), 500),
                "journal": _compact(journal, 250),
                "year": year,
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                "abstract": _compact(" ".join(abstract_parts), 2000),
                "fetched_at": _today(),
            }
        )
    return rows


def fetch_pubmed(session: requests.Session, seed: dict[str, str], max_results: int) -> tuple[list[dict[str, str]], dict[str, str]]:
    query = _pubmed_query(seed)
    if not query:
        return [], _status(seed, "PubMed", "", 0, "skipped_no_query")
    try:
        pmids = pubmed_search(session, query, max_results)
        rows = pubmed_fetch(session, pmids)
        for row in rows:
            row["seed_key"] = seed["seed_key"]
            row["seed_label"] = seed["seed_label"]
            row["query"] = query
        return rows, _status(seed, "PubMed", query, len(rows), "success" if rows else "success_zero_records")
    except Exception as exc:
        return [], _status(seed, "PubMed", query, 0, "failed", str(exc))


def dedupe_literature(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[tuple[str, str, str]] = set()
    out: list[dict[str, str]] = []
    for row in rows:
        key = (
            row.get("source_system", ""),
            row.get("doi", "").lower(),
            row.get("source_id", ""),
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


def dedupe_compounds(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[tuple[str, str, str]] = set()
    out: list[dict[str, str]] = []
    for row in rows:
        key = (
            row.get("seed_key", ""),
            row.get("cid", ""),
            row.get("compound_query", "").lower(),
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extracción semilla de radiofarmacia CCHEN.")
    parser.add_argument("--max-literature-per-seed", type=int, default=20)
    parser.add_argument("--timeout", type=int, default=25)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    ensure_seed_file()
    seeds = read_seeds()
    session = _session(args.timeout)

    compound_rows: list[dict[str, str]] = []
    literature_rows: list[dict[str, str]] = []
    status_rows: list[dict[str, str]] = []

    for seed in seeds:
        pubchem, pubchem_status = fetch_pubchem(session, seed)
        compound_rows.extend(pubchem)
        status_rows.extend(pubchem_status)

        europmc, europmc_status = fetch_europepmc(session, seed, args.max_literature_per_seed)
        literature_rows.extend(europmc)
        status_rows.append(europmc_status)
        time.sleep(0.3)

        pubmed, pubmed_status = fetch_pubmed(session, seed, args.max_literature_per_seed)
        literature_rows.extend(pubmed)
        status_rows.append(pubmed_status)
        time.sleep(0.4)

    compound_rows = dedupe_compounds(compound_rows)
    literature_rows = dedupe_literature(literature_rows)
    write_csv(PUBCHEM_CSV, compound_rows, PUBCHEM_COLUMNS)
    write_csv(LITERATURE_CSV, literature_rows, LITERATURE_COLUMNS)
    write_csv(STATUS_CSV, status_rows, STATUS_COLUMNS)
    STATE_JSON.write_text(
        json.dumps(
            {
                "updated": dt.datetime.now().isoformat(timespec="seconds"),
                "seeds": len(seeds),
                "compound_records": len(compound_rows),
                "literature_records": len(literature_rows),
                "outputs": [
                    str(SEEDS_CSV.relative_to(ROOT)),
                    str(PUBCHEM_CSV.relative_to(ROOT)),
                    str(LITERATURE_CSV.relative_to(ROOT)),
                    str(STATUS_CSV.relative_to(ROOT)),
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print(f"[OK] semillas -> {SEEDS_CSV.relative_to(ROOT)} ({len(seeds)} filas)")
    print(f"[OK] PubChem -> {PUBCHEM_CSV.relative_to(ROOT)} ({len(compound_rows)} filas)")
    print(f"[OK] literatura -> {LITERATURE_CSV.relative_to(ROOT)} ({len(literature_rows)} filas)")
    print(f"[OK] estado -> {STATUS_CSV.relative_to(ROOT)} ({len(status_rows)} filas)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
