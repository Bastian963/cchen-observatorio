"""
Script robusto para descargar todos los metadatos de publicaciones asociadas a CCHEN desde Europe PMC.
- Busca por afiliación: "comision chilena de energia nuclear" y "cchen".
- Descarga todos los resultados en formato JSON.
- Opcional: descarga PDFs de acceso abierto si están disponibles.

Requisitos:
- requests

Uso:
python download_europepmc_cchen.py
"""

import requests
import os
import time
import json

QUERY = 'AFF:"comision chilena de energia nuclear" OR AFF:"cchen"'
API_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
PAGE_SIZE = 1000  # máximo permitido
OUTPUT_DIR = "europepmc_cchen_downloads"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def fetch_results(query, page=1):
    params = {
        "query": query,
        "format": "json",
        "pageSize": PAGE_SIZE,
        "page": page
    }
    resp = requests.get(API_URL, params=params)
    resp.raise_for_status()
    return resp.json()

def download_pdf(result, output_dir):
    oa_url = result.get("fullTextUrlList", {}).get("fullTextUrl", [])
    for urlinfo in oa_url:
        if urlinfo.get("documentStyle") == "pdf" and urlinfo.get("availability") == "Open access":
            url = urlinfo.get("url")
            if url:
                pmcid = result.get("pmcid") or result.get("id")
                fname = os.path.join(output_dir, f"{pmcid}.pdf")
                print(f"Descargando PDF: {fname}")
                try:
                    with requests.get(url, stream=True, timeout=30) as r:
                        r.raise_for_status()
                        with open(fname, 'wb') as out:
                            for chunk in r.iter_content(chunk_size=8192):
                                out.write(chunk)
                except Exception as e:
                    print(f"  Error al descargar {url}: {e}")
                return True
    return False

def main():
    page = 1
    total_records = 0
    all_results = []
    print("Buscando resultados en Europe PMC...")
    while True:
        data = fetch_results(QUERY, page)
        results = data.get("resultList", {}).get("result", [])
        if not results:
            break
        all_results.extend(results)
        total_records += len(results)
        print(f"Página {page}: {len(results)} resultados")
        if total_records >= int(data.get('hitCount', 0)):
            break
        page += 1
        time.sleep(0.5)  # para evitar rate limit
    print(f"Total de resultados: {total_records}")
    # Guardar resultados
    with open(os.path.join(OUTPUT_DIR, "europepmc_cchen_results.json"), "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print(f"Resultados guardados en {OUTPUT_DIR}/europepmc_cchen_results.json")
    # Descargar PDFs de acceso abierto
    pdf_dir = os.path.join(OUTPUT_DIR, "pdfs")
    os.makedirs(pdf_dir, exist_ok=True)
    pdf_count = 0
    for result in all_results:
        if download_pdf(result, pdf_dir):
            pdf_count += 1
            time.sleep(1)  # para evitar bloqueos
    print(f"PDFs de acceso abierto descargados: {pdf_count}")

if __name__ == "__main__":
    main()
