"""
Script robusto para descargar y/o estimar el tamaño total de todos los outputs institucionales de CCHEN en Zenodo,
combinando búsqueda por comunidad y por afiliación.

- Descarga todos los registros de las comunidades 'cchen' y 'comision-chilena-energia-nuclear'.
- Busca por afiliación ('comision chilena de energia nuclear', 'cchen').
- Une ambos resultados y elimina duplicados.
- Permite estimar el tamaño total antes de descargar.
- Descarga archivos y metadatos organizados por registro.

Requisitos:
- requests

Uso:
1. (Opcional) export ZENODO_TOKEN="<tu_token>"
2. Ejecuta: python download_zenodo_cchen_combined.py [--estimate-only]
"""

import os
import sys
import requests
import json

ZENODO_API_URL = "https://zenodo.org/api"
COMMUNITIES = ["cchen", "comision-chilena-energia-nuclear"]
AFFILIATION_KEYWORDS = ["comision chilena de energia nuclear", "cchen"]
TOKEN = os.getenv("ZENODO_TOKEN")
HEADERS = {"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}

# 1. Listar todos los depósitos públicos de las comunidades

def list_community_deposits(community):
    deposits = []
    page = 1
    while True:
        resp = requests.get(f"{ZENODO_API_URL}/records", params={"communities": community, "page": page, "size": 100}, headers=HEADERS)
        resp.raise_for_status()
        data = resp.json()
        hits = data.get('hits', {}).get('hits', [])
        if not hits:
            break
        deposits.extend(hits)
        page += 1
    return deposits

# 2. Buscar por palabra clave general (en todos los campos indexados)
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

# 3. Filtrar por afiliación en autores
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

# 4. Unir y deduplicar por ID
def merge_and_deduplicate(*lists):
    merged = {}
    for l in lists:
        for rec in l:
            merged[rec['id']] = rec
    return list(merged.values())

# 5. Estimar tamaño total
def estimate_total_size(records):
    total_bytes = 0
    for rec in records:
        files = rec.get('files', [])
        for f in files:
            total_bytes += f.get('size', 0)
    return total_bytes

# 6. Descargar archivos y metadatos
def download_files_and_metadata(records, output_dir="zenodo_cchen_combined_downloads"):
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
    estimate_only = "--estimate-only" in sys.argv
    print("Listando depósitos de comunidades...")
    community_records = []
    for community in COMMUNITIES:
        recs = list_community_deposits(community)
        print(f"  {community}: {len(recs)} registros")
        community_records.extend(recs)
    print("Buscando registros por palabra clave general...")
    general_records = search_records_general()
    print(f"  Registros únicos por búsqueda general: {len(general_records)}")
    filtered_aff = filter_by_affiliation(general_records)
    print(f"  Registros con afiliación relevante: {len(filtered_aff)}")
    all_records = merge_and_deduplicate(community_records, filtered_aff)
    print(f"Total de registros únicos combinados: {len(all_records)}")
    total_bytes = estimate_total_size(all_records)
    total_gb = total_bytes / (1024 ** 3)
    print(f"Tamaño total estimado a descargar: {total_gb:.2f} GB")
    if not estimate_only:
        download_files_and_metadata(all_records)
