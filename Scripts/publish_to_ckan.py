"""
Script para publicar automáticamente datasets en CKAN desde archivos locales.
Documenta errores y resultados en logs.
Requiere: requests, CKAN API Key, y CKAN corriendo en http://localhost:5000
"""
import os
import requests
import logging

# Configuración
CKAN_URL = os.getenv("CKAN_URL", "http://localhost:5000")
CKAN_API_KEY = os.getenv("CKAN_API_KEY", "<REEMPLAZA_CON_TU_API_KEY>")
DATA_DIR = os.getenv("DATA_DIR", "../Data/Publications")  # Cambia según tu estructura
LOG_FILE = os.getenv("CKAN_LOG_FILE", "publish_to_ckan.log")

logging.basicConfig(filename=LOG_FILE, level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s')

def create_package(title, name=None, notes=None):
    url = f"{CKAN_URL}/api/3/action/package_create"
    headers = {"Authorization": CKAN_API_KEY}
    data = {"title": title, "name": name or title.lower().replace(" ", "-"), "notes": notes or ""}
    r = requests.post(url, headers=headers, json=data)
    if r.status_code == 200 and r.json().get("success"):
        logging.info(f"Dataset creado: {title}")
        return r.json()["result"]["id"]
    else:
        logging.error(f"Error creando dataset {title}: {r.text}")
        return None

def upload_resource(package_id, filepath):
    url = f"{CKAN_URL}/api/3/action/resource_create"
    headers = {"Authorization": CKAN_API_KEY}
    files = {"upload": open(filepath, "rb")}
    data = {"package_id": package_id, "name": os.path.basename(filepath)}
    r = requests.post(url, headers=headers, data=data, files=files)
    if r.status_code == 200 and r.json().get("success"):
        logging.info(f"Archivo subido: {filepath}")
        return True
    else:
        logging.error(f"Error subiendo {filepath}: {r.text}")
        return False

def main():
    for fname in os.listdir(DATA_DIR):
        fpath = os.path.join(DATA_DIR, fname)
        if not os.path.isfile(fpath):
            continue
        title = os.path.splitext(fname)[0]
        pkg_id = create_package(title)
        if pkg_id:
            upload_resource(pkg_id, fpath)

if __name__ == "__main__":
    main()
