#!/usr/bin/env python3
"""
fetch_inapi_patents.py — Observatorio CCHEN 360°
=================================================
Descarga patentes chilenas relacionadas con CCHEN desde INAPI
(Instituto Nacional de Propiedad Industrial de Chile).

Estrategia:
  1. Búsqueda por titular en el portal abierto de INAPI via su API pública.
  2. Búsqueda por palabras clave en título/resumen (nuclear, radiación, etc.).
  3. Fallback: CSV descargable de datos.inapi.cl si la API no responde.

Salida:
  Data/Patents/cchen_inapi_patents.csv
      patent_id | tipo | titulo | titular | fecha_solicitud | fecha_concesion |
      estado | clasificacion_ipc | resumen | url | fuente | fetched_at

Uso:
    python3 Scripts/fetch_inapi_patents.py
    python3 Scripts/fetch_inapi_patents.py --keywords-only
    python3 Scripts/fetch_inapi_patents.py --verbose
"""

from __future__ import annotations

import argparse
import csv
import datetime
import json
import time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from urllib.parse import quote, urlencode

import pandas as pd

ROOT     = Path(__file__).resolve().parents[1]
PAT_DIR  = ROOT / "Data" / "Patents"
PAT_DIR.mkdir(parents=True, exist_ok=True)
OUT_CSV  = PAT_DIR / "cchen_inapi_patents.csv"

CONTACT  = "observatory@cchen.cl"
TIMEOUT  = 25
SLEEP    = 1.0

# ── Queries de búsqueda ───────────────────────────────────────────────────────

# Titulares asociados a CCHEN (variantes ortográficas)
TITULAR_QUERIES = [
    "Comisión Chilena de Energía Nuclear",
    "CCHEN",
    "Chilean Nuclear Energy Commission",
]

# Palabras clave temáticas en título/resumen
KEYWORD_QUERIES = [
    "energía nuclear Chile",
    "reactor nuclear",
    "material radiactivo",
    "radiofármaco",
    "radioisótopo",
    "medicina nuclear Chile",
    "neutron activación",
    "dosimetría radiación",
    "residuo radiactivo",
    "ciclotrón Chile",
]

OUTPUT_COLUMNS = [
    "patent_id", "tipo", "titulo", "titular", "inventores",
    "fecha_solicitud", "fecha_concesion", "estado",
    "clasificacion_ipc", "pais_origen", "resumen", "url",
    "fuente", "fetched_at",
]

# ── API INAPI ─────────────────────────────────────────────────────────────────
# INAPI expone datos a través de su portal abierto: https://datos.inapi.cl
# y tiene una API de búsqueda en: https://patentes.inapi.cl/api/

INAPI_API_BASE = "https://patentes.inapi.cl"
INAPI_SEARCH   = f"{INAPI_API_BASE}/busca"

# ── Helpers ───────────────────────────────────────────────────────────────────

def _fetch(url: str, verbose: bool = False) -> dict | list | None:
    if verbose:
        print(f"  GET {url[:90]}...")
    headers = {
        "User-Agent": f"CCHEN-Observatory/1.0 (mailto:{CONTACT})",
        "Accept": "application/json",
    }
    req = Request(url, headers=headers)
    try:
        with urlopen(req, timeout=TIMEOUT) as r:
            raw = r.read().decode("utf-8", errors="replace")
            return json.loads(raw)
    except HTTPError as e:
        if e.code == 404:
            return None
        if e.code in (429, 503):
            print(f"  ⚠ HTTP {e.code} — esperando 30 s...")
            time.sleep(30)
            return None
        if verbose:
            print(f"  ⚠ HTTP {e.code}")
        return None
    except Exception as exc:
        if verbose:
            print(f"  ⚠ {exc}")
        return None


def _normalize(row: dict, fuente: str) -> dict:
    """Normaliza un registro crudo al esquema de salida."""
    today = datetime.date.today().isoformat()
    return {
        "patent_id":          str(row.get("numero_solicitud") or row.get("id") or ""),
        "tipo":               str(row.get("tipo_propiedad") or row.get("tipo") or "Patente"),
        "titulo":             str(row.get("titulo") or row.get("title") or "")[:300],
        "titular":            str(row.get("titular") or row.get("titulares") or "")[:200],
        "inventores":         str(row.get("inventores") or row.get("inventor") or "")[:200],
        "fecha_solicitud":    str(row.get("fecha_solicitud") or row.get("filing_date") or ""),
        "fecha_concesion":    str(row.get("fecha_concesion") or row.get("grant_date") or ""),
        "estado":             str(row.get("estado") or row.get("status") or ""),
        "clasificacion_ipc":  str(row.get("clasificacion_ipc") or row.get("ipc") or ""),
        "pais_origen":        str(row.get("pais_origen") or "CL"),
        "resumen":            str(row.get("resumen") or row.get("abstract") or "")[:600],
        "url":                str(row.get("url") or row.get("link") or ""),
        "fuente":             fuente,
        "fetched_at":         today,
    }


def _is_relevant(rec: dict) -> bool:
    """Filtra registros no relacionados con CCHEN / nuclear."""
    combined = (
        (rec.get("titular") or "").lower() + " " +
        (rec.get("titulo") or "").lower() + " " +
        (rec.get("resumen") or "").lower()
    )
    nuclear_terms = [
        "nuclear", "cchen", "comisión chilena de energía",
        "radiactiv", "radiofármac", "radioisótop", "reactor",
        "neutron", "dosimetría", "ciclotrón", "ciclotron",
        "radiación", "radiacion", "isótopo", "isotopo",
    ]
    return any(t in combined for t in nuclear_terms)


# ── Búsqueda por titular ──────────────────────────────────────────────────────

def search_by_titular(query: str, verbose: bool) -> list[dict]:
    """Busca patentes por nombre de titular vía API INAPI."""
    params = urlencode({"titular": query, "formato": "json", "cantidad": 200})
    url = f"{INAPI_SEARCH}?{params}"
    data = _fetch(url, verbose)
    results = []
    if isinstance(data, list):
        raw_list = data
    elif isinstance(data, dict):
        raw_list = data.get("resultados") or data.get("results") or data.get("items") or []
    else:
        return results

    for item in raw_list:
        rec = _normalize(item, f"INAPI_titular:{query}")
        if rec["patent_id"]:
            results.append(rec)
    return results


# ── Búsqueda por keywords ─────────────────────────────────────────────────────

def search_by_keyword(query: str, verbose: bool) -> list[dict]:
    """Busca patentes por palabras clave en título/resumen."""
    params = urlencode({"texto": query, "formato": "json", "cantidad": 100})
    url = f"{INAPI_SEARCH}?{params}"
    data = _fetch(url, verbose)
    results = []
    if isinstance(data, list):
        raw_list = data
    elif isinstance(data, dict):
        raw_list = data.get("resultados") or data.get("results") or data.get("items") or []
    else:
        return results

    for item in raw_list:
        rec = _normalize(item, f"INAPI_keyword:{query}")
        if _is_relevant(rec):
            results.append(rec)
    return results


# ── Fallback: CSV público INAPI ───────────────────────────────────────────────

def try_open_data_csv(verbose: bool) -> list[dict]:
    """
    Intenta descargar el dataset abierto de INAPI desde datos.inapi.cl.
    El portal CKAN de INAPI publica archivos CSV descargables.
    """
    # URL del recurso CSV de patentes concedidas (actualizado anualmente)
    candidates = [
        "https://datos.inapi.cl/dataset/patentes-concedidas/resource/patentes-csv",
        "https://datos.inapi.cl/datastore/dump/patentes_concedidas",
    ]
    results = []
    for url in candidates:
        if verbose:
            print(f"  Intentando CSV abierto: {url}")
        try:
            req = Request(url, headers={"User-Agent": f"CCHEN-Observatory/1.0 (mailto:{CONTACT})"})
            with urlopen(req, timeout=40) as r:
                content = r.read().decode("utf-8", errors="replace")
            # Parsear CSV
            lines = content.splitlines()
            if len(lines) < 2:
                continue
            reader = csv.DictReader(lines)
            nuclear_keywords = [
                "nuclear", "cchen", "comisión chilena",
                "radiactiv", "radiofármac", "reactor",
                "neutron", "radiación", "isótopo",
            ]
            for row in reader:
                combined = " ".join(str(v) for v in row.values()).lower()
                if any(k in combined for k in nuclear_keywords):
                    results.append(_normalize(
                        {
                            "numero_solicitud": row.get("numero_solicitud") or row.get("id", ""),
                            "titulo": row.get("titulo") or row.get("nombre", ""),
                            "titular": row.get("titular") or row.get("solicitante", ""),
                            "inventores": row.get("inventores", ""),
                            "fecha_solicitud": row.get("fecha_solicitud", ""),
                            "fecha_concesion": row.get("fecha_concesion", ""),
                            "estado": row.get("estado", "Concedida"),
                            "clasificacion_ipc": row.get("clasificacion_ipc") or row.get("ipc", ""),
                            "resumen": row.get("resumen") or row.get("abstract", ""),
                            "url": row.get("url", ""),
                        },
                        "INAPI_CSV_abierto"
                    ))
            if results:
                print(f"  CSV abierto: {len(results)} registros nucleares encontrados")
                return results
        except Exception as exc:
            if verbose:
                print(f"  ⚠ CSV fallback falló: {exc}")
    return results


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Patentes INAPI — CCHEN Observatory")
    parser.add_argument("--keywords-only", action="store_true",
                        help="Solo búsqueda por keywords (no titular)")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    print("Patentes CCHEN — INAPI Chile")
    print(f"Fecha: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n")

    all_records: dict[str, dict] = {}  # patent_id → record

    # 1. Búsqueda por titular
    if not args.keywords_only:
        print("── Búsqueda por titular ──────────────────────────────")
        for q in TITULAR_QUERIES:
            print(f"  Titular: '{q}' ...", end="  ")
            recs = search_by_titular(q, args.verbose)
            n_new = 0
            for r in recs:
                pid = r["patent_id"]
                if pid and pid not in all_records:
                    all_records[pid] = r
                    n_new += 1
            print(f"{n_new} nuevas (de {len(recs)})")
            time.sleep(SLEEP)

    # 2. Búsqueda por keywords
    print("\n── Búsqueda por keywords ─────────────────────────────")
    for q in KEYWORD_QUERIES:
        print(f"  Keyword: '{q}' ...", end="  ")
        recs = search_by_keyword(q, args.verbose)
        n_new = 0
        for r in recs:
            pid = r["patent_id"]
            if pid and pid not in all_records:
                all_records[pid] = r
                n_new += 1
        print(f"{n_new} nuevas (de {len(recs)})")
        time.sleep(SLEEP)

    # 3. Fallback CSV abierto
    if not all_records:
        print("\n── Fallback: CSV abierto INAPI ───────────────────────")
        csv_recs = try_open_data_csv(args.verbose)
        for r in csv_recs:
            pid = r["patent_id"] or f"csv_{hash(r['titulo'])}"
            if pid not in all_records:
                all_records[pid] = r

    # 4. Guardar resultados
    print(f"\n── Resultados ───────────────────────────────────────")
    print(f"  Total registros únicos: {len(all_records)}")

    if not all_records:
        print(
            "\n⚠ No se encontraron patentes.\n"
            "  Esto puede indicar:\n"
            "  a) CCHEN no tiene patentes registradas en INAPI bajo variantes conocidas\n"
            "  b) La API de INAPI no está disponible en este momento\n"
            "  c) Las patentes están bajo nombre de investigadores individuales\n\n"
            "  Recomendación: verificar manualmente en https://patentes.inapi.cl\n"
            "  buscando 'comisión chilena' o 'nuclear'"
        )
        # Guardar CSV vacío con headers para que data_loader no falle
        pd.DataFrame(columns=OUTPUT_COLUMNS).to_csv(OUT_CSV, index=False)
        return

    df = pd.DataFrame(list(all_records.values()), columns=OUTPUT_COLUMNS)
    df = df.drop_duplicates(subset=["patent_id"])
    df.to_csv(OUT_CSV, index=False)

    print(f"\n  Por tipo:")
    if "tipo" in df.columns:
        for tipo, n in df["tipo"].value_counts().items():
            print(f"    {tipo}: {n}")
    print(f"\n  Por estado:")
    if "estado" in df.columns:
        for est, n in df["estado"].value_counts().items():
            print(f"    {est}: {n}")

    print(f"\n✓ Guardado en: {OUT_CSV}  ({len(df)} registros)")


if __name__ == "__main__":
    main()
