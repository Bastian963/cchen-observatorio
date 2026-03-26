"""
Script para estimar el tamaño total de descarga de todos los recursos de Zenodo donde la afiliación de algún autor contenga
"Comisión Chilena de Energía Nuclear" o "CCHEN".
No descarga archivos, solo suma el tamaño total en GB.

Requisitos:
- requests

Uso:
1. (Opcional) Define tu token Zenodo si quieres mayor límite de peticiones: export ZENODO_TOKEN="<tu_token>"
2. Ejecuta el script: python estimate_zenodo_affiliation_size.py
"""

import os
import requests

ZENODO_API_URL = "https://zenodo.org/api"
AFFILIATION_KEYWORDS = ["comision chilena de energia nuclear", "cchen"]
TOKEN = os.getenv("ZENODO_TOKEN")
HEADERS = {"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}

def search_records_general():
    records = []
    page = 1
    query = '"comision chilena de energia nuclear" OR "cchen"'
    while True:
        resp = requests.get(
            f"{ZENODO_API_URL}/records",
            params={"q": query, "page": page, "size": 100},
            headers=HEADERS
        )
        resp.raise_for_status()
        data = resp.json()
        hits = data.get('hits', {}).get('hits', [])
        if not hits:
            break
        records.extend(hits)
        page += 1
    unique = {rec['id']: rec for rec in records}
    return list(unique.values())

def filter_by_affiliation(records):
    filtered = []
    for rec in records:
        authors = rec['metadata'].get('creators', [])
        for author in authors:
            affs = author.get('affiliation')
            if affs is None:
                continue
            if any(kw.lower() in affs.lower() for kw in AFFILIATION_KEYWORDS):
                filtered.append(rec)
                break
    return filtered

def estimate_total_size(records):
    total_bytes = 0
    for rec in records:
        files = rec.get('files', [])
        for f in files:
            total_bytes += f.get('size', 0)
    return total_bytes

if __name__ == "__main__":
    print("Buscando registros por palabra clave general...")
    records = search_records_general()
    print(f"Se encontraron {len(records)} registros únicos.")
    filtered = filter_by_affiliation(records)
    print(f"Se encontraron {len(filtered)} registros con afiliación relevante.")
    total_bytes = estimate_total_size(filtered)
    total_gb = total_bytes / (1024 ** 3)
    print(f"Tamaño total estimado a descargar: {total_gb:.2f} GB")
