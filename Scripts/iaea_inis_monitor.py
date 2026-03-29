#!/usr/bin/env python3
"""
IAEA INIS Monitor — Observatorio Tecnológico CCHEN
===================================================
Monitorea el repositorio IAEA INIS para artículos recientes relevantes a CCHEN.

INIS (International Nuclear Information System) es la fuente de literatura
nuclear especializada más completa del mundo — cubre lo que arXiv y OpenAlex
no indexan: informes técnicos IAEA, tesis nucleares, actas de congresos IAEA,
documentos nacionales de regulación nuclear.

API usada: InvenioRDM REST API de INIS (https://inis.iaea.org/api/records)

Uso manual:
    python Scripts/iaea_inis_monitor.py
    python Scripts/iaea_inis_monitor.py --days-back 30

Uso automático (runner canónico):
    python Scripts/run_source_refresh.py --source-key iaea_inis_monitor
"""

from __future__ import annotations

import csv
import datetime
import html as _html_module
import json
import os
import re
import time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError

_HTML_TAG = re.compile(r"<[^>]+>")
_WHITESPACE = re.compile(r"\s+")

def _strip_html(text: str) -> str:
    """Elimina tags HTML, decodifica entidades HTML y normaliza espacios."""
    clean = _HTML_TAG.sub("", _html_module.unescape(str(text)))
    return _WHITESPACE.sub(" ", clean).strip()

ROOT    = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "Data" / "Vigilancia"
OUT_CSV = OUT_DIR / "iaea_inis_monitor.csv"
STATE   = OUT_DIR / "iaea_inis_state.json"
OUT_DIR.mkdir(parents=True, exist_ok=True)

_CONTACT = os.getenv("CCHEN_CONTACT_EMAIL", "observatory@cchen.cl")

# ── Fuentes de búsqueda ───────────────────────────────────────────────────────
# Búsquedas temáticas centradas en áreas CCHEN: medicina nuclear, protección
# radiológica, reactores, física nuclear, radiofarmacéuticos, residuos nucleares.

INIS_SEARCHES = [
    {"query": "nuclear medicine Chile",           "area": "Medicina Nuclear"},
    {"query": "radiation protection Chile",       "area": "Radioprotección"},
    {"query": "nuclear reactor physics",          "area": "Física de Reactores"},
    {"query": "radiopharmaceuticals production",  "area": "Radiofármacos"},
    {"query": "radioactive waste management",     "area": "Residuos Radiactivos"},
    {"query": "neutron activation analysis",      "area": "Activación Neutrónica"},
    {"query": "radiation dosimetry",              "area": "Dosimetría"},
    {"query": "nuclear safety regulation",        "area": "Regulación Nuclear"},
    {"query": "isotope production cyclotron",     "area": "Producción de Isótopos"},
]

# Keywords para clasificar relevancia CCHEN (mismo esquema que arxiv_monitor)
KEYWORDS_HIGH = [
    "nuclear medicine", "radiopharmaceutical", "radioactive waste", "nuclear safety",
    "radiation dosimetry", "neutron activation", "isotope production",
    "reactor physics", "nuclear fuel", "nuclear regulation",
    "gamma spectroscopy", "radioprotection", "nuclear power", "chile",
]
KEYWORDS_MEDIUM = [
    "radiation", "nuclear", "isotope", "neutron", "proton therapy",
    "brachytherapy", "cyclotron", "radioactivity", "fission", "fusion",
    "dosimeter", "shielding", "radiotracer",
]

CSV_FIELDS = [
    "inis_id", "title", "authors", "abstract_short", "link",
    "published", "subject_area", "relevance_flag", "keywords_found",
    "source_type", "fetched_at",
]

INIS_API   = "https://inis.iaea.org/api/records"
INIS_SLEEP = 1.0   # 1 seg entre queries para no sobrecargar el servidor
TIMEOUT    = 25


# ── Helpers ───────────────────────────────────────────────────────────────────

def load_state() -> set:
    if STATE.exists():
        with open(STATE) as f:
            return set(json.load(f).get("seen_ids", []))
    return set()


def save_state(seen_ids: set) -> None:
    with open(STATE, "w") as f:
        json.dump({"seen_ids": sorted(seen_ids),
                   "updated": datetime.datetime.now().isoformat()}, f)


def _relevance(title: str, abstract: str) -> tuple[str, str]:
    text = (title + " " + abstract).lower()
    found_high   = [k for k in KEYWORDS_HIGH   if k in text]
    found_medium = [k for k in KEYWORDS_MEDIUM if k in text]
    flag = "ALTA" if found_high else ("MEDIA" if found_medium else "BAJA")
    return flag, "; ".join(found_high + found_medium)[:300]


def _parse_invenio_hits(hits: list, area: str) -> list[dict]:
    """Parsea resultados de la API InvenioRDM de INIS."""
    rows = []
    now = datetime.datetime.now().strftime("%Y-%m-%d")
    for h in hits:
        meta = h.get("metadata", {})
        rec_id = h.get("id", "")

        # Título (puede venir con tags HTML desde INIS)
        title = meta.get("title", "")
        if isinstance(title, list):
            title = title[0] if title else ""
        title = _strip_html(title)

        # Autores / creators
        creators = meta.get("creators", []) or meta.get("authors", []) or []
        authors_str = "; ".join(
            c.get("name", "") or
            (c.get("given_name", "") + " " + c.get("family_name", "")).strip()
            for c in creators[:8] if isinstance(c, dict)
        )[:200]

        # Abstract / description (también puede tener HTML)
        desc = meta.get("description", "") or meta.get("abstract", "") or ""
        if isinstance(desc, list):
            desc = " ".join(str(d) for d in desc)
        abstract_short = _strip_html(str(desc))[:400]

        # Fecha de publicación
        pub_date = (
            meta.get("publication_date") or
            meta.get("imprint", {}).get("year", "") or
            h.get("created", "")[:10]
        )

        # Tipo de documento
        source_type = meta.get("resource_type", {}).get("subtype", "") or \
                      meta.get("resource_type", {}).get("type", "") or ""

        link = h.get("links", {}).get("self_html", f"https://inis.iaea.org/records/{rec_id}")

        flag, kw_found = _relevance(title, abstract_short)

        rows.append({
            "inis_id":        rec_id,
            "title":          str(title)[:250],
            "authors":        authors_str,
            "abstract_short": abstract_short,
            "link":           link,
            "published":      str(pub_date),
            "subject_area":   area,
            "relevance_flag": flag,
            "keywords_found": kw_found,
            "source_type":    str(source_type)[:80],
            "fetched_at":     now,
        })
    return rows


def fetch_inis_search(query: str, area: str, size: int = 25) -> list[dict]:
    """Consulta la API InvenioRDM de INIS."""
    params = {
        "q":    query,
        "sort": "newest",
        "size": size,
        "page": 1,
    }
    url = f"{INIS_API}?{urlencode(params)}"
    req = Request(url, headers={
        "Accept":     "application/json",
        "User-Agent": f"CCHEN-Observatory/1.0 (mailto:{_CONTACT})",
    })
    try:
        with urlopen(req, timeout=TIMEOUT) as r:
            data = json.load(r)
        hits = (data.get("hits") or {}).get("hits", [])
        return _parse_invenio_hits(hits, area)
    except HTTPError as e:
        if e.code == 422:
            # La API rechazó el query — intentar sin parámetros de fecha
            print(f"  ⚠ INIS 422 para '{query}' — query syntax issue")
        else:
            print(f"  ⚠ INIS HTTP {e.code} para '{query}'")
        return []
    except Exception as exc:
        print(f"  ⚠ INIS error para '{query}': {exc}")
        return []


def append_to_csv(rows: list[dict]) -> int:
    file_exists = OUT_CSV.exists()
    written = 0
    with open(OUT_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        if not file_exists:
            writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in CSV_FIELDS})
            written += 1
    return written


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    print("IAEA INIS Monitor — CCHEN Observatorio Tecnológico")
    print(f"Fecha: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"Salida: {OUT_CSV}\n")

    seen_ids  = load_state()
    all_new   = []
    summary   = {}

    for cfg in INIS_SEARCHES:
        print(f"→ {cfg['area']}: '{cfg['query']}' ...", end=" ", flush=True)
        items = fetch_inis_search(cfg["query"], cfg["area"])
        time.sleep(INIS_SLEEP)

        new_items = [it for it in items if it["inis_id"] not in seen_ids]
        for it in new_items:
            seen_ids.add(it["inis_id"])

        all_new.extend(new_items)
        summary[cfg["area"]] = {
            "total": len(items),
            "new":   len(new_items),
            "high":  sum(1 for x in new_items if x["relevance_flag"] == "ALTA"),
        }
        print(f"{len(new_items)} nuevos (de {len(items)} en INIS)")

    if all_new:
        written = append_to_csv(all_new)
        save_state(seen_ids)
        print(f"\n✓ {written} documentos guardados en {OUT_CSV}")
    else:
        print("\n✓ Sin documentos nuevos en INIS.")

    # Resumen
    print("\n─── Resumen INIS ────────────────────────────────")
    for area, s in summary.items():
        print(f"  {area:<35}  {s['new']:>3} nuevos  {s['high']:>3} alta relevancia")

    # Alertas alta relevancia
    high = [p for p in all_new if p["relevance_flag"] == "ALTA"]
    if high:
        print(f"\n⭐ DOCUMENTOS INIS DE ALTA RELEVANCIA ({len(high)}):")
        for p in high:
            print(f"  [{p['subject_area']}] {p['title'][:80]}")
            if p["keywords_found"]:
                print(f"    Keywords: {p['keywords_found'][:100]}")
            print(f"    {p['link']}")

    return len(all_new)


if __name__ == "__main__":
    n = main()
    exit(0 if n >= 0 else 1)
