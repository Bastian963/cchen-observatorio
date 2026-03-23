#!/usr/bin/env python3
"""
Radar curado de convocatorias cientificas — CCHEN
=================================================

Objetivo:
    Generar una base limpia y util para el dashboard a partir del
    calendario oficial de ANID, priorizando convocatorias postulables
    para academicos, postdocs, doctorados y equipos cientificos.

Salida:
    Data/Vigilancia/convocatorias_curadas.csv

Uso:
    python3 Scripts/convocatorias_monitor.py
"""

import csv
import datetime as dt
import hashlib
import re
from html import unescape
from pathlib import Path
from urllib.request import Request, urlopen


BASE = Path(__file__).parent.parent
OUT_DIR = BASE / "Data" / "Vigilancia"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_CSV = OUT_DIR / "convocatorias_curadas.csv"

_YEAR = dt.datetime.now().year
ANID_CALENDAR_URL = f"https://anid.cl/calendario-concursos-{_YEAR}/"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "es-CL,es;q=0.9,en;q=0.8",
}

CSV_FIELDS = [
    "conv_id",
    "tipo_registro",
    "titulo",
    "organismo",
    "categoria",
    "estado",
    "apertura_texto",
    "cierre_texto",
    "fallo_texto",
    "apertura_iso",
    "cierre_iso",
    "perfil_objetivo",
    "relevancia_cchen",
    "fuente",
    "es_oficial",
    "postulable",
    "url",
    "notas",
]

STATUSES = {
    "Abierto",
    "Próximo",
    "En evaluación",
    "Adjudicado",
    "Suspendido",
    "Patrocinio Institucional",
    "Desierto",
}

MONTHS = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "setiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}


def fetch_html(url: str) -> str:
    req = Request(url, headers=HEADERS)
    with urlopen(req, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def clean_html_text(html: str) -> str:
    html = re.sub(r"<br\s*/?>", "\n", html, flags=re.I)
    html = re.sub(r"</p>", "\n", html, flags=re.I)
    html = re.sub(r"</div>", "\n", html, flags=re.I)
    html = re.sub(r"<[^>]+>", "", html)
    html = unescape(html)
    html = html.replace("\xa0", " ")
    html = re.sub(r"\r", "", html)
    html = re.sub(r"[ \t]+", " ", html)
    html = re.sub(r"\n+", "\n", html)
    return html.strip()


def extract_label_value(lines, label: str) -> str:
    for line in lines:
        if line.startswith(label):
            return line.split(":", 1)[1].strip()
    return ""


def parse_exact_spanish_date(value: str) -> str:
    if not value:
        return ""
    txt = value.strip().lower()
    match = re.search(r"(\d{1,2})\s+de\s+([a-záéíóú]+)\s*,?\s*(\d{4})", txt)
    if not match:
        return ""
    day = int(match.group(1))
    month = MONTHS.get(match.group(2))
    year = int(match.group(3))
    if not month:
        return ""
    return dt.date(year, month, day).isoformat()


def infer_profile(title: str, category: str) -> str:
    text = f"{title} {category}".lower()
    if "postdoctorado" in text:
        return "Postdoctorado"
    if "doctorado" in text or "tesis" in text:
        return "Doctorado"
    if "magíster" in text or "magister" in text:
        if "educación" in text or "funcionarios" in text:
            return "Magíster / educación"
        return "Magíster"
    if "instalación en la academia" in text or "fondecyt" in text or "exploración" in text:
        return "Académicos / PI"
    if "anillos" in text or "núcleos" in text or "nucleos" in text or "equipamiento" in text:
        return "Infraestructura / consorcios"
    if "viu" in text or "idea" in text or "inserción en el sector productivo" in text:
        return "Innovación / transferencia"
    if "gemini" in text or "alma" in text or "ecos" in text or "amsud" in text or "vinculación internacional" in text:
        return "Colaboración / movilidad"
    if "beneficios complementarios" in text:
        return "Becarios / doctorado"
    return "Institucional / I+D"


def infer_relevance(title: str, category: str) -> str:
    text = f"{title} {category}".lower()
    low_keywords = [
        "profesionales de la educación",
        "funcionarios",
        "pluralismo",
    ]
    if any(k in text for k in low_keywords):
        return "Baja"

    high_keywords = [
        "postdoctorado",
        "doctorado",
        "fondecyt",
        "exploración",
        "exploracion",
        "anillos",
        "núcleos",
        "nucleos",
        "equipamiento",
        "fonis",
        "idea",
        "instalación en la academia",
        "instalacion en la academia",
        "gemini",
        "alma",
        "quimal",
        "ecos",
        "viu",
    ]
    if any(k in text for k in high_keywords):
        return "Alta"

    medium_keywords = [
        "vinculación internacional",
        "vinculacion internacional",
        "inés",
        "ines",
        "beneficios complementarios",
        "asignación rápida",
        "asignacion rapida",
        "stic-amsud",
        "math-amsud",
        "climat-amsud",
    ]
    if any(k in text for k in medium_keywords):
        return "Media"
    return "Media"


def infer_notes(title: str, category: str, raw_lines) -> str:
    notes = []
    text = f"{title} {category}".lower()
    if "cgr" in " ".join(raw_lines).lower():
        notes.append("Sujeta a toma de razón o trámite administrativo informado por ANID.")
    if "por definir" in " ".join(raw_lines).lower():
        notes.append("Fechas exactas aún no publicadas en la ficha concursal.")
    if "viu" in text:
        notes.append("Relevante para valorización y transferencia tecnológica.")
    if "gemini" in text or "alma" in text or "quimal" in text:
        notes.append("Línea particularmente relevante para instrumentación o colaboración científica avanzada.")
    if "instalación en la academia" in text or "inserción en el sector productivo" in text:
        notes.append("Convocatoria especialmente relevante para trayectorias postdoctorales y de inserción.")
    return " ".join(notes)


def parse_anid_calendar(html: str):
    sections = re.split(
        r"<p>\s*<strong>(.*?)</strong>\s*</p>",
        html,
        flags=re.I | re.S,
    )
    rows = []

    for idx in range(1, len(sections), 2):
        category = clean_html_text(sections[idx])
        chunk = sections[idx + 1]
        items = re.split(r'<div class="jet-listing-grid__item\b[^>]*>', chunk, flags=re.I)[1:]

        for item_html in items:
            text = clean_html_text(item_html)
            if not text:
                continue
            lines = [line.strip() for line in text.split("\n") if line.strip()]
            if not lines:
                continue

            title = lines[0]
            status = next((line for line in lines if line in STATUSES), "Revisar")
            apertura = extract_label_value(lines, "Inicio")
            cierre = extract_label_value(lines, "Cierre")
            fallo = extract_label_value(lines, "Fallo")
            link_match = re.search(r'<a[^>]+href="([^"]+/concursos/[^"]+)"', item_html, flags=re.I)
            url = link_match.group(1) if link_match else ANID_CALENDAR_URL

            rows.append({
                "conv_id": hashlib.md5(f"{title}|{url}".encode("utf-8")).hexdigest()[:12],
                "tipo_registro": "convocatoria",
                "titulo": title,
                "organismo": "ANID",
                "categoria": category,
                "estado": status,
                "apertura_texto": apertura,
                "cierre_texto": cierre,
                "fallo_texto": fallo,
                "apertura_iso": parse_exact_spanish_date(apertura),
                "cierre_iso": parse_exact_spanish_date(cierre),
                "perfil_objetivo": infer_profile(title, category),
                "relevancia_cchen": infer_relevance(title, category),
                "fuente": f"ANID calendario {_YEAR}",
                "es_oficial": True,
                "postulable": status in {"Abierto", "Próximo"},
                "url": url,
                "notas": infer_notes(title, category, lines),
            })

    dedup = {}
    for row in rows:
        dedup[row["conv_id"]] = row
    return list(dedup.values())


def main():
    print("Radar curado de convocatorias — CCHEN")
    print(f"Fecha de ejecucion: {dt.datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"Fuente principal: {ANID_CALENDAR_URL}")

    html = fetch_html(ANID_CALENDAR_URL)
    rows = parse_anid_calendar(html)

    if not rows:
        raise RuntimeError("No se pudieron extraer convocatorias desde el calendario oficial de ANID.")

    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    abiertos = [r for r in rows if r["estado"] == "Abierto"]
    proximos = [r for r in rows if r["estado"] == "Próximo"]
    altas = [r for r in rows if r["relevancia_cchen"] == "Alta"]

    print(f"\nArchivo generado: {OUT_CSV}")
    print(f"Total convocatorias: {len(rows)}")
    print(f"Abiertas: {len(abiertos)}")
    print(f"Proximas: {len(proximos)}")
    print(f"Alta relevancia CCHEN: {len(altas)}")

    print("\nAbiertas detectadas:")
    for row in abiertos:
        print(f"  - [{row['categoria']}] {row['titulo']}")


if __name__ == "__main__":
    main()
