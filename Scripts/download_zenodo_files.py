"""
Script para listar y descargar todos los depósitos y archivos de ZENODO usando un token personal.

Requisitos:
- requests

Uso:
1. Guarda tu token en una variable de entorno: export ZENODO_TOKEN="<tu_token>"
2. Ejecuta el script: python download_zenodo_files.py
"""

import os
import requests

ZENODO_API_URL = "https://zenodo.org/api"
TOKEN = os.getenv("ZENODO_TOKEN")

if not TOKEN:
    raise RuntimeError("Debes definir la variable de entorno ZENODO_TOKEN con tu token personal.")

HEADERS = {"Authorization": f"Bearer {TOKEN}"}

# 1. Listar todos los depósitos del usuario
def list_deposits():
    deposits = []
    page = 1
    while True:
        resp = requests.get(f"{ZENODO_API_URL}/deposit/depositions", headers=HEADERS, params={"page": page, "size": 100})
        resp.raise_for_status()
        data = resp.json()
        if not data:
            break
        deposits.extend(data)
        page += 1
    return deposits

# 2. Descargar todos los archivos de cada depósito
def download_files(deposits, output_dir="zenodo_downloads"):
    os.makedirs(output_dir, exist_ok=True)
    for dep in deposits:
        title = dep['metadata'].get('title', f"deposit_{dep['id']}").replace('/', '_')
        dep_dir = os.path.join(output_dir, f"{dep['id']}_{title}")
        os.makedirs(dep_dir, exist_ok=True)
        files = dep.get('files', [])
        for f in files:
            url = f['links']['download']
            fname = os.path.join(dep_dir, f['filename'])
            print(f"Descargando {fname} ...")
            with requests.get(url, headers=HEADERS, stream=True) as r:
                r.raise_for_status()
                with open(fname, 'wb') as out:
                    for chunk in r.iter_content(chunk_size=8192):
                        out.write(chunk)
    print(f"Descarga completa en: {output_dir}")

if __name__ == "__main__":
    print("Listando depósitos...")
    deposits = list_deposits()
    print(f"Se encontraron {len(deposits)} depósitos.")
    download_files(deposits)
