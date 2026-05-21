#!/usr/bin/env python3
"""
fetch_pubmed.py — Observatorio CCHEN 360°
=========================================
Descarga publicaciones CCHEN desde PubMed vía NCBI E-utilities.

Cubre literatura biomédica: medicina nuclear, dosimetría, radiofármacos,
radiobiología y biofísica de radiaciones. Complementa EuroPMC con mayor
cobertura de revistas clínicas y biomedicas norteamericanas.

API: https://eutils.ncbi.nlm.nih.gov/entrez/eutils/
Sin API key (límite 3 req/s). Con API key NCBI: 10 req/s.

Salidas:
  Data/Publications/cchen_pubmed_works.csv
  Data/Publications/pubmed_state.json

Uso:
    python3 Scripts/fetch_pubmed.py
    python3 Scripts/fetch_pubmed.py --limit 200
    python3 Scripts/fetch_pubmed.py --reset
    python3 Scripts/fetch_pubmed.py --verbose
"""
from __future__ import annotations

import argparse
import datetime
import json
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from urllib.parse import urlencode, quote_plus

import pandas as pd

ROOT    = Path(__file__).resolve().parents[1]
PUB_DIR = ROOT / "Data" / "Publications"
PUB_DIR.mkdir(parents=True, exist_ok=True)
OUT_CSV    = PUB_DIR / "cchen_pubmed_works.csv"
STATE_FILE = PUB_DIR / "pubmed_state.json"

BASE_SEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
BASE_FETCH  = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
CONTACT     = "observatory@cchen.cl"
TIMEOUT     = 30
SLEEP       = 0.4   # respeta límite 3 req/s sin API key
BATCH_FETCH = 100   # IDs por llamada a efetch

OUTPUT_COLUMNS = [
    "pmid", "doi", "pmcid",
    "title", "authors", "journal",
    "year", "pub_date",
    "abstract", "keywords",
    "is_open_access", "affiliation_raw",
    "pubmed_url", "fetched_at",
]

SEARCH_QUERIES = [
    '"Comision Chilena de Energia Nuclear"[Affiliation]',
    '"Comisión Chilena de Energía Nuclear"[Affiliation]',
    '"Chilean Nuclear Energy Commission"[Affiliation]',
    'CCHEN[Affiliation] AND Chile[Affiliation] AND (nuclear OR radiation OR radiopharmaceutical OR dosimetry OR reactor)',
]


def _get_pmids(query: str, verbose: bool = False) -> list[str]:
    """Devuelve todos los PMIDs para un query usando esearch con usehistory."""
    params = {
        "db": "pubmed", "term": query,
        "retmax": 10000, "retmode": "json",
        "usehistory": "y", "tool": "CCHEN-Observatory",
        "email": CONTACT,
    }
    url = f"{BASE_SEARCH}?{urlencode(params)}"
    if verbose:
        print(f"  esearch: {url[:100]}")
    req = Request(url, headers={"User-Agent": f"CCHEN-Observatory/1.0 (mailto:{CONTACT})"})
    try:
        with urlopen(req, timeout=TIMEOUT) as r:
            data = json.load(r)
        ids = data.get("esearchresult", {}).get("idlist", [])
        count = data.get("esearchresult", {}).get("count", "?")
        if verbose:
            print(f"  → {count} resultados, {len(ids)} IDs recibidos")
        return ids
    except Exception as exc:
        if verbose:
            print(f"  esearch error: {exc}")
        return []


def _fetch_batch(pmids: list[str], verbose: bool = False) -> list[dict]:
    """Descarga registros completos (con abstract) para un lote de PMIDs vía efetch XML."""
    params = {
        "db": "pubmed", "id": ",".join(pmids),
        "retmode": "xml", "rettype": "abstract",
        "tool": "CCHEN-Observatory", "email": CONTACT,
    }
    url = f"{BASE_FETCH}?{urlencode(params)}"
    req = Request(url, headers={"User-Agent": f"CCHEN-Observatory/1.0 (mailto:{CONTACT})"})
    try:
        with urlopen(req, timeout=TIMEOUT) as r:
            raw = r.read()
        root = ET.fromstring(raw)
        return [_parse_article(art) for art in root.findall(".//PubmedArticle")]
    except HTTPError as e:
        if verbose:
            print(f"  efetch HTTP {e.code}: {e.reason}")
        return []
    except Exception as exc:
        if verbose:
            print(f"  efetch error: {exc}")
        return []


def _text(element, path: str, default: str = "") -> str:
    el = element.find(path)
    return (el.text or "").strip() if el is not None else default


def _parse_article(art: ET.Element) -> dict:
    today = datetime.date.today().isoformat()
    mc  = art.find("MedlineCitation")
    pd_ = art.find("PubmedData")
    if mc is None:
        return {}

    pmid = _text(mc, "PMID")
    article = mc.find("Article")
    if article is None:
        return {"pmid": pmid, "fetched_at": today}

    # Title
    title = _text(article, "ArticleTitle")

    # Abstract (puede tener múltiples AbstractText con Label)
    abs_parts = []
    for ab in article.findall(".//AbstractText"):
        label = ab.get("Label", "")
        text  = (ab.text or "").strip()
        if text:
            abs_parts.append(f"{label}: {text}" if label else text)
    abstract = " ".join(abs_parts)

    # Authors + affiliation
    authors_list = []
    aff_raw = ""
    for au in article.findall(".//Author"):
        last  = _text(au, "LastName")
        fore  = _text(au, "ForeName") or _text(au, "Initials")
        name  = f"{last} {fore}".strip()
        if name:
            authors_list.append(name)
        if not aff_raw:
            aff_el = au.find(".//AffiliationInfo/Affiliation")
            if aff_el is not None and aff_el.text:
                aff_raw = (aff_el.text or "")[:300]

    # Journal
    journal  = _text(article, "Journal/Title") or _text(article, "Journal/ISOAbbreviation")
    year_el  = article.find(".//Journal/JournalIssue/PubDate/Year")
    med_year = article.find(".//Journal/JournalIssue/PubDate/MedlineDate")
    year     = (year_el.text if year_el is not None else "") or (
                med_year.text[:4] if med_year is not None and med_year.text else "")
    pub_date = year  # enriquecer con mes si se necesita

    # Keywords (MeSH)
    kws = [kw.text.strip() for kw in mc.findall(".//MeshHeading/DescriptorName") if kw.text]
    keywords = "; ".join(kws[:10])

    # IDs del PubmedData
    doi = pmcid = ""
    if pd_ is not None:
        for aid in pd_.findall(".//ArticleId"):
            id_type = aid.get("IdType", "")
            if id_type == "doi":
                doi = aid.text or ""
            elif id_type == "pmc":
                pmcid = aid.text or ""

    # Open Access: si tiene PMC, se considera OA (heurística razonable)
    is_oa = "Y" if pmcid else "N"

    return {
        "pmid":            pmid,
        "doi":             doi,
        "pmcid":           pmcid,
        "title":           title,
        "authors":         "; ".join(authors_list[:10]),
        "journal":         journal,
        "year":            year,
        "pub_date":        pub_date,
        "abstract":        abstract[:2000],
        "keywords":        keywords,
        "is_open_access":  is_oa,
        "affiliation_raw": aff_raw,
        "pubmed_url":      f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        "fetched_at":      today,
    }


def _load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"processed_queries": [], "fetched_pmids": []}


def _save_state(state: dict) -> None:
    state["updated"] = datetime.datetime.now().isoformat()
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2))


def _flush(rows: list[dict]) -> None:
    if not rows:
        return
    new_df = pd.DataFrame([r for r in rows if r.get("pmid")], columns=OUTPUT_COLUMNS)
    if OUT_CSV.exists():
        old_df = pd.read_csv(OUT_CSV, dtype=str)
        new_df = pd.concat([old_df, new_df]).drop_duplicates(subset=["pmid"], keep="last")
    new_df.to_csv(OUT_CSV, index=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="PubMed — CCHEN Observatory")
    parser.add_argument("--limit",   type=int, default=0)
    parser.add_argument("--reset",   action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    state = {"processed_queries": [], "fetched_pmids": []} if args.reset else _load_state()
    processed_queries = set(state.get("processed_queries", []))
    fetched_pmids     = set(state.get("fetched_pmids", []))

    all_pmids: set[str] = set()
    for qi, query in enumerate(SEARCH_QUERIES, 1):
        if query in processed_queries:
            print(f"[{qi}/{len(SEARCH_QUERIES)}] Skipping (ya procesada): {query[:70]}")
            continue
        print(f"\n[{qi}/{len(SEARCH_QUERIES)}] Query: {query[:70]}")
        ids = _get_pmids(query, verbose=args.verbose)
        new_ids = [i for i in ids if i not in fetched_pmids]
        print(f"  → {len(ids)} PMIDs ({len(new_ids)} nuevos)")
        all_pmids.update(new_ids)
        processed_queries.add(query)
        time.sleep(SLEEP)

    if not all_pmids:
        print("\nNada nuevo que descargar.")
        _save_state({
            "processed_queries": sorted(processed_queries),
            "fetched_pmids": sorted(fetched_pmids),
        })
        _print_summary()
        return

    pmids_list = sorted(all_pmids)
    if args.limit > 0:
        pmids_list = pmids_list[:args.limit]

    print(f"\nDescargando registros completos para {len(pmids_list)} PMIDs...")
    all_rows: list[dict] = []
    total_batches = (len(pmids_list) + BATCH_FETCH - 1) // BATCH_FETCH

    for bi, i in enumerate(range(0, len(pmids_list), BATCH_FETCH), 1):
        batch = pmids_list[i:i + BATCH_FETCH]
        print(f"  Batch {bi}/{total_batches} ({len(batch)} IDs)...", end=" ")
        rows = _fetch_batch(batch, verbose=args.verbose)
        n_abs = sum(1 for r in rows if r.get("abstract"))
        print(f"{len(rows)} artículos, {n_abs} con abstract")
        all_rows.extend(rows)
        fetched_pmids.update(batch)
        time.sleep(SLEEP)

    _flush(all_rows)
    _save_state({
        "processed_queries": sorted(processed_queries),
        "fetched_pmids":     sorted(fetched_pmids),
    })

    if not OUT_CSV.exists():
        pd.DataFrame(columns=OUTPUT_COLUMNS).to_csv(OUT_CSV, index=False)

    _print_summary()


def _print_summary() -> None:
    print("\n-- Resumen --------------------------------------------------")
    if not OUT_CSV.exists():
        print("Sin datos PubMed."); return
    df = pd.read_csv(OUT_CSV)
    if df.empty:
        print("Sin publicaciones PubMed encontradas."); return
    print(f"Total publicaciones PubMed: {len(df)}")
    print(f"Con DOI:     {df['doi'].fillna('').ne('').sum()}")
    print(f"Con abstract:{df['abstract'].fillna('').ne('').sum()}")
    print(f"Open Access: {(df['is_open_access']=='Y').sum()}")
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    vy = df["year"].dropna()
    if not vy.empty:
        print(f"Rango de años: {int(vy.min())} – {int(vy.max())}")
    print(f"Guardado en: {OUT_CSV}")
    print("\nMuestra (5 más recientes):")
    for _, r in df.nlargest(5, "year").iterrows():
        print(f"  [{r['year']}] {str(r['title'])[:70]} — {r['journal']}")


if __name__ == "__main__":
    main()
