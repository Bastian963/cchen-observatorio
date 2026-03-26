"""
Script para probar variantes de búsqueda en Zenodo:
- "Comisión Chilena de Energía Nuclear"
- "comision chilena de energia nuclear"
- "CCHEN"

Muestra los títulos de los primeros 10 resultados para cada variante.

Requisitos:
- requests

Uso:
python test_zenodo_api_variants.py
"""

import requests

ZENODO_API_URL = "https://zenodo.org/api"
QUERIES = [
    "Comisión Chilena de Energía Nuclear",
    "comision chilena de energia nuclear",
    "CCHEN"
]

for q in QUERIES:
    print(f"\n=== Resultados para: '{q}' ===")
    resp = requests.get(f"{ZENODO_API_URL}/records", params={"q": q, "size": 10})
    resp.raise_for_status()
    data = resp.json()
    hits = data.get('hits', {}).get('hits', [])
    print(f"Se encontraron {len(hits)} registros.")
    for i, rec in enumerate(hits, 1):
        title = rec['metadata'].get('title', 'Sin título')
        print(f"{i}. {title}")
