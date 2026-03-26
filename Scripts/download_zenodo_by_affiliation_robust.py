"""
Script robusto para buscar y descargar todos los recursos de Zenodo donde la afiliación de algún autor contenga
"Comisión Chilena de Energía Nuclear" o "CCHEN".

Estrategia:
- Buscar por palabra clave general (q="comision chilena de energia nuclear" OR "cchen")
- Filtrar en Python solo los registros donde la afiliación de algún autor contenga exactamente esas palabras clave.

Requisitos:
- requests

Uso:
1. (Opcional) Define tu token Zenodo si quieres mayor límite de peticiones: export ZENODO_TOKEN="<tu_token>"
2. Ejecuta el script: python download_zenodo_by_affiliation_robust.py
"""

import os
import requests
import json

ZENODO_API_URL = "https://zenodo.org/api"
AFFILIATION_KEYWORDS = ["comision chilena de energia nuclear", "cchen"]
TOKEN = os.getenv("ZENODO_TOKEN")

HEADERS = {"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}

# 1. Buscar por palabra clave general (en todos los campos indexados)
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
    # Eliminar duplicados por id
    unique = {rec['id']: rec for rec in records}
    return list(unique.values())

# 2. Filtrar por afiliación en autores
def filter_by_affiliation(records):
    filtered = []
    for rec in records:
        authors = rec['metadata'].get('creators', [])
        for author in authors:
            affs = author.get('affiliation', '')
            if any(kw.lower() in affs.lower() for kw in AFFILIATION_KEYWORDS):
                filtered.append(rec)
                break
    return filtered

# 3. Descargar archivos y metadatos
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
    print("Buscando registros por palabra clave general...")
    records = search_records_general()
    print(f"Se encontraron {len(records)} registros únicos.")
    filtered = filter_by_affiliation(records)
    print(f"Se encontraron {len(filtered)} registros con afiliación relevante.")
    download_files_and_metadata(filtered)
