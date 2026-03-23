#!/usr/bin/env python3
"""
Monitor de Noticias CCHEN — Observatorio Tecnológico
=====================================================
Busca menciones de CCHEN en Google News y guarda los resultados
en Data/Vigilancia/news_monitor.csv.

Uso manual:
    python3 Scripts/news_monitor.py
    python3 Scripts/news_monitor.py --log              # escribe log en Data/Vigilancia/news_monitor.log
    python3 Scripts/news_monitor.py --log Docs/news.log  # ruta personalizada

Uso automático (GitHub Actions):
    Configurable junto a arxiv_monitor.yml
"""

import argparse
import xml.etree.ElementTree as ET
import csv
import json
import datetime
import hashlib
import re
import sys
from html import unescape as html_unescape
from pathlib import Path

try:
    import urllib.request as urlreq
    from urllib.parse import quote
except ImportError:
    import urllib as urlreq

# ── Configuración ──────────────────────────────────────────────────────────────

BASE      = Path(__file__).parent.parent
OUT_DIR   = BASE / "Data" / "Vigilancia"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_CSV    = OUT_DIR / "news_monitor.csv"
STATE_FILE = OUT_DIR / "news_state.json"

# Queries para Google News RSS
# Formato: ?q=QUERY&hl=LANG&gl=REGION&ceid=REGION:LANG
QUERIES = [
    {
        "q":    '"CCHEN" energía nuclear Chile',
        "hl":   "es-419",
        "gl":   "CL",
        "label": "CCHEN · español",
    },
    {
        "q":    '"Comisión Chilena de Energía Nuclear"',
        "hl":   "es-419",
        "gl":   "CL",
        "label": "Nombre completo · español",
    },
    {
        "q":    "CCHEN nuclear Chile",
        "hl":   "en-US",
        "gl":   "US",
        "label": "CCHEN · inglés",
    },
    {
        "q":    '"La Reina" reactor nuclear Chile CCHEN',
        "hl":   "es-419",
        "gl":   "CL",
        "label": "Reactor La Reina · español",
    },
]

GNEWS_BASE = "https://news.google.com/rss/search"

# Categorías temáticas para clasificar noticias
TOPICS_SCIENCE = [
    "investigación", "research", "estudio", "study", "publicación",
    "científico", "científica", "ciencia", "nuclear", "radiación",
    "dosimetría", "isótopo", "reactor", "acelerador",
]
TOPICS_POLICY = [
    "regulación", "normativa", "ley", "decreto", "ministerio", "gobierno",
    "política", "plan", "presupuesto", "concurso", "licitación",
]
TOPICS_INSTITUTIONAL = [
    "director", "directora", "nombramiento", "renuncia", "cargo",
    "comisión", "institución", "convenio", "acuerdo", "alianza",
]

CSV_FIELDS = [
    "news_id", "title", "source_name", "link",
    "published", "snippet", "query_label", "topic_flag", "fetched_at",
]


# ── Funciones ──────────────────────────────────────────────────────────────────

def load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return set(json.load(f).get("seen_ids", []))
    return set()


def save_state(seen_ids):
    with open(STATE_FILE, "w") as f:
        json.dump(
            {"seen_ids": sorted(seen_ids),
             "updated": datetime.datetime.now().isoformat()},
            f
        )


def build_url(q, hl, gl):
    return f"{GNEWS_BASE}?q={quote(q)}&hl={hl}&gl={gl}&ceid={gl}:{hl.split('-')[0]}"


def fetch_feed(url):
    headers = {"User-Agent": "Mozilla/5.0 (compatible; CCHEN-Observatory/1.0)"}
    try:
        req = urlreq.Request(url, headers=headers)
        with urlreq.urlopen(req, timeout=20) as r:
            return r.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"  ⚠ Error: {e}")
        return None


RELEVANCE_TERMS = [
    "cchen", "comisión chilena de energía nuclear", "energía nuclear",
    "reactor nuclear", "la reina", "nuclear chile", "comisión de energía nuclear",
]


def is_relevant(text):
    """Verifica que la noticia realmente mencione a CCHEN o energía nuclear en Chile."""
    t = text.lower()
    return any(k in t for k in RELEVANCE_TERMS)


def classify_topic(text):
    t = text.lower()
    if any(k in t for k in TOPICS_SCIENCE):
        return "CIENCIA"
    if any(k in t for k in TOPICS_POLICY):
        return "POLÍTICA"
    if any(k in t for k in TOPICS_INSTITUTIONAL):
        return "INSTITUCIONAL"
    return "GENERAL"


_HTML_TAG_RE = re.compile(r"<[^>]+>")
_HTML_ATTR_RE = re.compile(r"(href|target)\s*=\s*\"[^\"]*\"?", re.IGNORECASE)
_URL_RE = re.compile(r"https?://\S+")


def clean_feed_text(value):
    text = html_unescape(str(value or ""))
    text = text.replace("\xa0", " ")
    text = re.sub(r"<a\b[^>]*", " ", text, flags=re.IGNORECASE)
    text = _HTML_ATTR_RE.sub(" ", text)
    text = _URL_RE.sub(" ", text)
    text = text.replace("<a", " ").replace("</a", " ").replace(">", " ")
    text = _HTML_TAG_RE.sub(" ", text)
    text = re.sub(r"\s+", " ", text).strip(" -\n\t")
    return text


def clean_feed_title(title, source_name=""):
    clean_title = clean_feed_text(title)
    clean_source = clean_feed_text(source_name)
    if clean_source:
        for sep in [" - ", " | ", " — ", " – "]:
            suffix = f"{sep}{clean_source}"
            if clean_title.lower().endswith(suffix.lower()):
                clean_title = clean_title[:-len(suffix)].strip()
                break
    return clean_title


def clean_feed_snippet(snippet, title=""):
    clean_snippet = clean_feed_text(snippet)
    clean_title = clean_feed_text(title)
    if clean_title and clean_snippet.lower().startswith(clean_title.lower()):
        clean_snippet = clean_snippet[len(clean_title):].lstrip(" .:-")
    if clean_snippet.lower().startswith("leer noticia completa"):
        return ""
    return clean_snippet


def parse_feed(xml_content, label):
    root = ET.fromstring(xml_content)
    items = []
    now_str = datetime.datetime.now().strftime("%Y-%m-%d")

    for item in root.findall(".//item"):
        title   = clean_feed_text(item.findtext("title") or "")
        link    = (item.findtext("link") or "").strip()
        pubdate = (item.findtext("pubDate") or "").strip()
        desc    = item.findtext("description") or ""

        source_el = item.find("source")
        source    = clean_feed_text(source_el.text.strip() if source_el is not None else "")

        title = clean_feed_title(title, source)
        snippet = clean_feed_snippet(desc, title)

        # Filtrar falsos positivos — debe mencionar CCHEN o energía nuclear
        if not is_relevant(title + " " + snippet):
            continue

        # ID único: hash de título+fuente
        news_id = hashlib.md5((title + source).encode()).hexdigest()[:12]

        topic = classify_topic(title + " " + snippet)

        items.append({
            "news_id":     news_id,
            "title":       title[:200],
            "source_name": source[:100],
            "link":        link,
            "published":   pubdate,
            "snippet":     snippet[:400],
            "query_label": label,
            "topic_flag":  topic,
            "fetched_at":  now_str,
        })

    return items


def append_to_csv(rows):
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


# ── Logging ────────────────────────────────────────────────────────────────────

_DEFAULT_LOG = OUT_DIR / "news_monitor.log"

class _Tee:
    """Escribe simultáneamente a stdout y a un archivo de log."""
    def __init__(self, log_path: Path):
        self._file = open(log_path, "a", encoding="utf-8")
        self._stdout = sys.stdout
    def write(self, msg: str):
        self._stdout.write(msg)
        self._file.write(msg)
    def flush(self):
        self._stdout.flush()
        self._file.flush()
    def close(self):
        self._file.close()


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Monitor de Noticias CCHEN")
    parser.add_argument(
        "--log", nargs="?", const=str(_DEFAULT_LOG), default=None,
        metavar="RUTA",
        help="Guardar salida en log persistente (ruta opcional, default: Data/Vigilancia/news_monitor.log)",
    )
    args = parser.parse_args()

    tee = None
    if args.log:
        log_path = Path(args.log)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        tee = _Tee(log_path)
        sys.stdout = tee

    print("Monitor de Noticias CCHEN — Observatorio Tecnológico")
    print(f"Fecha: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"Salida: {OUT_CSV}\n")

    seen_ids = load_state()
    all_new  = []
    summary  = {}

    for cfg in QUERIES:
        print(f"→ {cfg['label']} ...", end=" ")
        url  = build_url(cfg["q"], cfg["hl"], cfg["gl"])
        xml  = fetch_feed(url)

        if not xml:
            print("sin respuesta")
            summary[cfg["label"]] = {"total": 0, "new": 0}
            continue

        items    = parse_feed(xml, cfg["label"])
        new_items = [it for it in items if it["news_id"] not in seen_ids]
        for it in new_items:
            seen_ids.add(it["news_id"])

        all_new.extend(new_items)
        summary[cfg["label"]] = {"total": len(items), "new": len(new_items)}
        print(f"{len(new_items)} nuevas (de {len(items)} en feed)")

    if all_new:
        written = append_to_csv(all_new)
        save_state(seen_ids)
        print(f"\n✓ {written} noticias guardadas en {OUT_CSV}")
    else:
        print("\n✓ Sin noticias nuevas.")

    print("\n─── Resumen ────────────────────────────────")
    for label, s in summary.items():
        print(f"  {label:40s}  {s['new']:3d} nuevas  (de {s['total']:3d})")

    # Mostrar últimas noticias de ciencia
    science = [n for n in all_new if n["topic_flag"] == "CIENCIA"]
    if science:
        print(f"\n🔬 NOTICIAS DE CIENCIA/INVESTIGACIÓN ({len(science)}):")
        for n in science[:5]:
            print(f"  [{n['source_name']}] {n['title'][:80]}")
            print(f"    {n['published']}")

    if tee is not None:
        sys.stdout = tee._stdout
        tee.close()

    return len(all_new)


if __name__ == "__main__":
    n = main()
    exit(0 if n >= 0 else 1)
