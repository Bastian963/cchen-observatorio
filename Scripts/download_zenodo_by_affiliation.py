"""
Script para buscar y descargar todos los recursos de Zenodo donde la afiliación de algún autor contenga
"Comisión Chilena de Energía Nuclear" o "CCHEN" (en cualquier campo de afiliación).
Descarga archivos y metadatos de cada resultado.

Requisitos:
- requests

Uso:
1. (Opcional) Define tu token Zenodo si quieres mayor límite de peticiones: export ZENODO_TOKEN="<tu_token>"
2. Ejecuta el script: python download_zenodo_by_affiliation.py
"""

import os
import requests
import json

ZENODO_API_URL = "https://zenodo.org/api"
AFFILIATION_KEYWORDS = ["comision chilena de energia nuclear", "cchen"]
TOKEN = os.getenv("ZENODO_TOKEN")

HEADERS = {"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}

# 1. Buscar por palabra clave en afiliación (usando búsqueda general)
def search_records_by_affiliation():
    records = []
    for keyword in AFFILIATION_KEYWORDS:
        print(f"Buscando registros con afiliación: {keyword}")
        page = 1
        while True:
            resp = requests.get(
                f"{ZENODO_API_URL}/records",
                params={"q": f"affiliations:\"{keyword}\"", "page": page, "size": 100},
                headers=HEADERS
            )
            resp.raise_for_status()
            data = resp.json()
            hits = data.get('hits', {}).get('hits', [])
            if not hits:
                break
            records.extend(hits)
            page += 1
    # Eliminar duplicados por id
    unique = {rec['id']: rec for rec in records}
    return list(unique.values())

# 2. Descargar archivos y metadatos
def download_files_and_metadata(records, output_dir="zenodo_affiliation_downloads"):
    os.makedirs(output_dir, exist_ok=True)
    for rec in records:
        rec_id = rec['id']
        title = rec['metadata'].get('title', f"record_{rec_id}").replace('/', '_')
        rec_dir = os.path.join(output_dir, f"{rec_id}_{title}")
        os.makedirs(rec_dir, exist_ok=True)
        # Guardar metadatos
        with open(os.path.join(rec_dir, "metadata.json"), "w", encoding="utf-8") as f:
            json.dump(rec, f, ensure_ascii=False, indent=2)
        # Descargar archivos
        files = rec.get('files', [])
        for fobj in files:
            url = fobj['links']['self']
            fname = os.path.join(rec_dir, fobj['key'])
            print(f"Descargando {fname} ...")
            with requests.get(url, stream=True) as r:
                r.raise_for_status()
                with open(fname, 'wb') as out:
                    for chunk in r.iter_content(chunk_size=8192):
                        out.write(chunk)
    print(f"Descarga completa en: {output_dir}")

if __name__ == "__main__":
    records = search_records_by_affiliation()
    print(f"Se encontraron {len(records)} registros únicos.")
    download_files_and_metadata(records)
