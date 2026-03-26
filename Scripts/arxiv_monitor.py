#!/usr/bin/env python3
"""
arXiv RSS Monitor — Observatorio Tecnológico CCHEN
====================================================
Monitorea semanalmente los feeds RSS de arXiv en áreas relevantes para CCHEN
y guarda los papers nuevos en Data/Vigilancia/arxiv_monitor.csv.

Uso manual:
    python Scripts/arxiv_monitor.py

Uso automático (GitHub Actions):
    Ver .github/workflows/arxiv_monitor.yml

Áreas monitoreadas (ajustar en FEEDS según necesidad):
    nucl-ex      → Nuclear Experiment
    nucl-th      → Nuclear Theory
    physics.med-ph → Medical Physics
    physics.ins-det → Instrumentation and Detectors
    physics.acc-ph  → Accelerator Physics
"""

import os
import xml.etree.ElementTree as ET
import csv
import json
import datetime
import hashlib
from pathlib import Path

try:
    import urllib.request as urlreq
except ImportError:
    import urllib as urlreq

# ── Configuración ──────────────────────────────────────────────────────────────

BASE = Path(__file__).parent.parent
OUT_DIR = BASE / "Data" / "Vigilancia"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_CSV = OUT_DIR / "arxiv_monitor.csv"
STATE_FILE = OUT_DIR / "arxiv_state.json"  # guarda IDs ya vistos

# Feeds RSS de arXiv a monitorear
FEEDS = [
    {
        "url": "https://arxiv.org/rss/nucl-ex",
        "area": "Nuclear Experiment",
        "code": "nucl-ex",
    },
    {
        "url": "https://arxiv.org/rss/nucl-th",
        "area": "Nuclear Theory",
        "code": "nucl-th",
    },
    {
        "url": "https://arxiv.org/rss/physics.med-ph",
        "area": "Medical Physics",
        "code": "physics.med-ph",
    },
    {
        "url": "https://arxiv.org/rss/physics.ins-det",
        "area": "Instrumentation & Detectors",
        "code": "physics.ins-det",
    },
    {
        "url": "https://arxiv.org/rss/physics.acc-ph",
        "area": "Accelerator Physics",
        "code": "physics.acc-ph",
    },
]

# Palabras clave para marcar papers de alta relevancia CCHEN
KEYWORDS_HIGH = [
    "nuclear medicine", "radiopharmaceutical", "radioactive waste", "nuclear safety",
    "radiation dosimetry", "neutron activation", "isotope production",
    "reactor physics", "nuclear fuel", "nuclear regulation",
    "gamma spectroscopy", "radioprotection", "nuclear power",
]

KEYWORDS_MEDIUM = [
    "radiation", "nuclear", "isotope", "neutron", "proton therapy",
    "brachytherapy", "cyclotron", "radioactivity", "fission", "fusion",
    "dosimeter", "shielding", "radiotracer",
]

CSV_FIELDS = [
    "arxiv_id", "title", "authors", "abstract_short",
    "link", "published", "feed_area", "relevance_flag",
    "keywords_found", "fetched_at",
]


# ── Funciones ──────────────────────────────────────────────────────────────────

def load_state() -> set:
    """Carga el conjunto de IDs ya procesados."""
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return set(json.load(f).get("seen_ids", []))
    return set()


def save_state(seen_ids: set) -> None:
    with open(STATE_FILE, "w") as f:
        json.dump({"seen_ids": sorted(seen_ids), "updated": datetime.datetime.now().isoformat()}, f)


def fetch_feed(url: str):
    """Descarga un feed RSS y devuelve el contenido XML."""
    _contact = os.getenv("CCHEN_CONTACT_EMAIL", "observatory@cchen.cl")
    headers = {"User-Agent": f"CCHEN-Observatory-Monitor/1.0 (mailto:{_contact})"}
    try:
        req = urlreq.Request(url, headers=headers)
        with urlreq.urlopen(req, timeout=30) as r:
            return r.read().decode("utf-8")
    except Exception as e:
        print(f"  ⚠ Error descargando {url}: {e}")
        return None


def parse_feed(xml_content: str, area: str) -> list[dict]:
    """Parsea el XML del feed RSS y extrae los campos relevantes."""
    ns = {"dc": "http://purl.org/dc/elements/1.1/"}
    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as exc:
        print(f"  ⚠ XML inválido en feed {area}: {exc}")
        return []
    items = []

    for item in root.findall(".//item"):
        title   = (item.findtext("title") or "").strip()
        link    = (item.findtext("link") or "").strip()
        desc    = (item.findtext("description") or "").strip()
        pubdate = (item.findtext("pubDate") or "").strip()
        authors_el = item.find("dc:creator", ns)
        authors = authors_el.text.strip() if authors_el is not None else ""

        # arXiv ID desde el link
        arxiv_id = link.split("/abs/")[-1] if "/abs/" in link else hashlib.md5(link.encode()).hexdigest()[:12]

        # Relevancia por palabras clave
        text_lower = (title + " " + desc).lower()
        found_high   = [k for k in KEYWORDS_HIGH   if k in text_lower]
        found_medium = [k for k in KEYWORDS_MEDIUM if k in text_lower]

        if found_high:
            flag = "ALTA"
        elif found_medium:
            flag = "MEDIA"
        else:
            flag = "BAJA"

        items.append({
            "arxiv_id":       arxiv_id,
            "title":          title,
            "authors":        authors[:200],
            "abstract_short": desc[:400].replace("<p>", "").replace("</p>", "").replace("<br>", " ").strip(),
            "link":           link,
            "published":      pubdate,
            "feed_area":      area,
            "relevance_flag": flag,
            "keywords_found": "; ".join(found_high + found_medium)[:300],
            "fetched_at":     datetime.datetime.now().strftime("%Y-%m-%d"),
        })

    return items


def append_to_csv(rows: list[dict]) -> int:
    """Agrega filas al CSV, creando el archivo si no existe."""
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


# ── Main ───────────────────────────────────────────────────────────────────────

def fetch_api_search(category: str, area: str, days_back: int = 7, max_results: int = 50) -> list[dict]:
    """Consulta la API de búsqueda arXiv para papers recientes en una categoría.
    Útil como fallback cuando el RSS está vacío (fines de semana, festivos).
    """
    import datetime as _dt
    since = (_dt.datetime.now() - _dt.timedelta(days=days_back)).strftime("%Y%m%d")
    query = f"cat:{category}"
    url = (
        f"https://export.arxiv.org/api/query"
        f"?search_query={query}"
        f"&sortBy=submittedDate&sortOrder=descending"
        f"&max_results={max_results}"
    )
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    try:
        req = urlreq.Request(url, headers={"User-Agent": "CCHEN-Observatory/1.0"})
        with urlreq.urlopen(req, timeout=20) as r:
            root = ET.fromstring(r.read())
    except Exception as e:
        print(f"  ⚠ API error {category}: {e}")
        return []

    items = []
    for entry in root.findall("atom:entry", ns):
        try:
            arxiv_id_raw = entry.find("atom:id", ns).text
            arxiv_id = arxiv_id_raw.split("/abs/")[-1].split("v")[0]
            title    = entry.find("atom:title", ns).text.strip().replace("\n", " ")
            summary  = (entry.find("atom:summary", ns).text or "").strip().replace("\n", " ")
            pub_date = entry.find("atom:published", ns).text[:10]
            authors  = "; ".join(
                a.find("atom:name", ns).text
                for a in entry.findall("atom:author", ns)
            )[:200]
            link = f"https://arxiv.org/abs/{arxiv_id}"

            text_lower = (title + " " + summary).lower()
            found_high   = [k for k in KEYWORDS_HIGH   if k in text_lower]
            found_medium = [k for k in KEYWORDS_MEDIUM if k in text_lower]
            flag = "ALTA" if found_high else ("MEDIA" if found_medium else "BAJA")

            items.append({
                "arxiv_id":       arxiv_id,
                "title":          title,
                "authors":        authors,
                "abstract_short": summary[:400],
                "link":           link,
                "published":      pub_date,
                "feed_area":      area,
                "relevance_flag": flag,
                "keywords_found": "; ".join(found_high + found_medium)[:300],
                "fetched_at":     datetime.datetime.now().strftime("%Y-%m-%d"),
            })
        except Exception:
            continue
    return items


def main():
    print(f"arXiv Monitor — CCHEN Observatorio Tecnológico")
    print(f"Fecha: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"Salida: {OUT_CSV}\n")

    seen_ids = load_state()
    all_new = []
    summary = {}

    for feed_cfg in FEEDS:
        print(f"→ {feed_cfg['area']} ({feed_cfg['code']}) ...", end=" ")
        xml = fetch_feed(feed_cfg["url"])
        items = parse_feed(xml, feed_cfg["area"]) if xml else []

        # Fallback: si el RSS está vacío (fin de semana / festivo), usar API de búsqueda
        if not items:
            print(f"RSS vacío → usando API de búsqueda (últimos 7 días)...", end=" ")
            items = fetch_api_search(feed_cfg["code"], feed_cfg["area"], days_back=7)

        new_items = [it for it in items if it["arxiv_id"] not in seen_ids]
        for it in new_items:
            seen_ids.add(it["arxiv_id"])

        all_new.extend(new_items)
        summary[feed_cfg["code"]] = {
            "total": len(items),
            "new": len(new_items),
            "high": sum(1 for x in new_items if x["relevance_flag"] == "ALTA"),
        }
        print(f"{len(new_items)} nuevos (de {len(items)} en fuente)")

    # Guardar
    if all_new:
        written = append_to_csv(all_new)
        save_state(seen_ids)
        print(f"\n✓ {written} papers guardados en {OUT_CSV}")
    else:
        print("\n✓ Sin papers nuevos.")

    # Resumen
    print("\n─── Resumen ────────────────────────────────")
    for code, s in summary.items():
        print(f"  {code:20s}  {s['new']:3d} nuevos  {s['high']:3d} alta relevancia")

    # Alerta de alta relevancia
    high_papers = [p for p in all_new if p["relevance_flag"] == "ALTA"]
    if high_papers:
        print(f"\n⭐ PAPERS DE ALTA RELEVANCIA ({len(high_papers)}):")
        for p in high_papers:
            print(f"  [{p['feed_area']}] {p['title'][:80]}")
            if p["keywords_found"]:
                print(f"    Keywords: {p['keywords_found'][:100]}")
            print(f"    {p['link']}")

    return len(all_new)


if __name__ == "__main__":
    n = main()
    exit(0 if n >= 0 else 1)
