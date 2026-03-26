"""
Script robusto para descargar todos los outputs institucionales de CCHEN desde OpenAIRE.
- Descarga publicaciones, datasets, software y proyectos asociados a la institución.
- Busca por variantes de nombre y país.
- Descarga todos los resultados en formato JSON.

Requisitos:
- requests
- lxml

Uso:
python download_openaire_cchen_full.py
"""

import requests
import os
import time
from lxml import etree
import json

QUERIES = [
    'organization:"Comisión Chilena de Energía Nuclear"',
    'organization:"CCHEN"',
    'country:"Chile" AND (organization:"Comisión Chilena de Energía Nuclear" OR organization:"CCHEN")'
]
ENDPOINTS = {
    "publications": "https://api.openaire.eu/search/publications",
    "datasets": "https://api.openaire.eu/search/datasets",
    "software": "https://api.openaire.eu/search/software",
    "projects": "https://api.openaire.eu/search/projects"
}
PAGE_SIZE = 100
OUTPUT_DIR = "openaire_cchen_full_downloads"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def fetch_results(endpoint, query, page=1):
    params = {
        "query": query,
        "size": PAGE_SIZE,
        "page": page,
        "format": "xml"
    }
    resp = requests.get(endpoint, params=params)
    resp.raise_for_status()
    return resp.content

def parse_results(xml_content):
    root = etree.fromstring(xml_content)
    results = []
    for pub in root.findall(".//result"):
        record = {}
        for field in pub.iterchildren():
            record[field.tag] = field.text
        results.append(record)
    return results

def download_all(endpoint_name):
    endpoint = ENDPOINTS[endpoint_name]
    all_results = []
    for query in QUERIES:
        page = 1
        print(f"Buscando en {endpoint_name} con query: {query}")
        while True:
            xml_content = fetch_results(endpoint, query, page)
            results = parse_results(xml_content)
            if not results:
                break
            all_results.extend(results)
            print(f"  Página {page}: {len(results)} resultados")
            if len(results) < PAGE_SIZE:
                break
            page += 1
            time.sleep(1)
    # Deduplicar por id
    unique = {rec.get('id', str(i)): rec for i, rec in enumerate(all_results)}
    print(f"Total únicos en {endpoint_name}: {len(unique)}")
    # Guardar
    with open(os.path.join(OUTPUT_DIR, f"openaire_cchen_{endpoint_name}.json"), "w", encoding="utf-8") as f:
        json.dump(list(unique.values()), f, ensure_ascii=False, indent=2)
    print(f"Guardado en {OUTPUT_DIR}/openaire_cchen_{endpoint_name}.json")

def main():
    for endpoint_name in ENDPOINTS:
        download_all(endpoint_name)

if __name__ == "__main__":
    main()
