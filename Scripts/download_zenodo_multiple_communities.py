"""
Script para descargar todos los recursos públicos de varias comunidades en Zenodo (por ejemplo, 'cchen' y 'comision-chilena-energia-nuclear').
Descarga archivos y metadatos de todos los depósitos asociados a cada comunidad.

Requisitos:
- requests

Uso:
1. (Opcional) Define tu token Zenodo si quieres mayor límite de peticiones: export ZENODO_TOKEN="<tu_token>"
2. Ejecuta el script: python download_zenodo_multiple_communities.py
"""

import os
import requests

ZENODO_API_URL = "https://zenodo.org/api"
COMMUNITIES = ["cchen", "comision-chilena-energia-nuclear"]  # Puedes agregar más slugs si existen
TOKEN = os.getenv("ZENODO_TOKEN")

HEADERS = {"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}

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

def download_files_and_metadata(deposits, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    for dep in deposits:
        rec_id = dep['id']
        title = dep['metadata'].get('title', f"record_{rec_id}").replace('/', '_')
        rec_dir = os.path.join(output_dir, f"{rec_id}_{title}")
        os.makedirs(rec_dir, exist_ok=True)
        # Guardar metadatos
        with open(os.path.join(rec_dir, "metadata.json"), "w", encoding="utf-8") as f:
            import json
            json.dump(dep, f, ensure_ascii=False, indent=2)
        # Descargar archivos
        files = dep.get('files', [])
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
    for community in COMMUNITIES:
        print(f"Listando depósitos públicos de la comunidad '{community}'...")
        deposits = list_community_deposits(community)
        print(f"Se encontraron {len(deposits)} depósitos en '{community}'.")
        output_dir = f"zenodo_{community}_downloads"
        download_files_and_metadata(deposits, output_dir)
