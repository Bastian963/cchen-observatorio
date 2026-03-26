"""
Script mínimo para probar la API de Zenodo: buscar y mostrar los títulos de los primeros 10 registros que contengan 'cchen' en cualquier campo indexado.

Requisitos:
- requests

Uso:
python test_zenodo_api_basic.py
"""

import requests

ZENODO_API_URL = "https://zenodo.org/api"

resp = requests.get(f"{ZENODO_API_URL}/records", params={"q": "cchen", "size": 10})
resp.raise_for_status()
data = resp.json()
hits = data.get('hits', {}).get('hits', [])

print(f"Se encontraron {len(hits)} registros.")
for i, rec in enumerate(hits, 1):
    title = rec['metadata'].get('title', 'Sin título')
    print(f"{i}. {title}")
