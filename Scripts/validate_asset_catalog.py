#!/usr/bin/env python3
"""Valida el catalogo maestro de activos institucionales 3 en 1."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = REPO_ROOT / "Data" / "Gobernanza" / "catalogo_activos_3_en_1.csv"
REQUIRED_COLUMNS = [
    "asset_id",
    "surface",
    "title",
    "local_path",
    "area_unidad",
    "tema",
    "anio",
    "responsables",
    "palabras_clave",
    "visibilidad",
    "identificador",
    "public_url",
    "vinculo_cruzado",
    "dashboard_section",
    "publication_status",
]
ALLOWED_SURFACES = {"dspace", "ckan", "dashboard"}
ALLOWED_PUBLICATION_STATUS = {"draft", "ready_for_publish", "published"}


def _is_http_url(value: str) -> bool:
    parsed = urlparse(str(value).strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _normalize_text(frame: pd.DataFrame, column: str) -> pd.Series:
    return frame[column].fillna("").astype(str).str.strip()


def _load_catalog(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"No existe el catalogo: {path}")
    return pd.read_csv(path, encoding="utf-8-sig")


def validate_catalog(path: Path) -> tuple[pd.DataFrame, list[str]]:
    frame = _load_catalog(path)
    errors: list[str] = []

    missing_columns = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
    if missing_columns:
        errors.append(f"Faltan columnas requeridas: {', '.join(missing_columns)}")
        return frame, errors

    asset_ids = _normalize_text(frame, "asset_id")
    empty_asset_ids = frame.index[asset_ids == ""].tolist()
    if empty_asset_ids:
        errors.append(f"Hay asset_id vacios en filas: {', '.join(str(i + 2) for i in empty_asset_ids)}")

    duplicated = asset_ids[asset_ids != ""].duplicated(keep=False)
    if duplicated.any():
        dup_ids = sorted(asset_ids[duplicated].unique().tolist())
        errors.append(f"Hay asset_id duplicados: {', '.join(dup_ids)}")

    surfaces = _normalize_text(frame, "surface").str.lower()
    invalid_surfaces = sorted(set(surfaces[(surfaces != "") & (~surfaces.isin(ALLOWED_SURFACES))].tolist()))
    if invalid_surfaces:
        errors.append(f"Hay surfaces invalidos: {', '.join(invalid_surfaces)}")

    statuses = _normalize_text(frame, "publication_status").str.lower()
    invalid_statuses = sorted(set(statuses[(statuses != "") & (~statuses.isin(ALLOWED_PUBLICATION_STATUS))].tolist()))
    if invalid_statuses:
        errors.append(f"Hay publication_status invalidos: {', '.join(invalid_statuses)}")

    for idx, local_path in enumerate(_normalize_text(frame, "local_path")):
        if not local_path:
            continue
        absolute_path = REPO_ROOT / local_path
        if not absolute_path.exists():
            errors.append(f"local_path inexistente en fila {idx + 2}: {local_path}")

    public_urls = _normalize_text(frame, "public_url")
    for idx, url in enumerate(public_urls):
        if url and not _is_http_url(url):
            errors.append(f"public_url invalida en fila {idx + 2}: {url}")

    crosslinks = _normalize_text(frame, "vinculo_cruzado")
    for idx, url in enumerate(crosslinks):
        if url and not _is_http_url(url):
            errors.append(f"vinculo_cruzado invalido en fila {idx + 2}: {url}")

    published_without_url = frame.index[(statuses == "published") & (public_urls == "")].tolist()
    if published_without_url:
        errors.append(
            "Hay activos published sin public_url en filas: "
            + ", ".join(str(i + 2) for i in published_without_url)
        )

    return frame, errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", default=str(DEFAULT_CATALOG), help="Ruta al catalogo CSV")
    args = parser.parse_args()

    catalog_path = Path(args.catalog).resolve()
    try:
        frame, errors = validate_catalog(catalog_path)
    except Exception as exc:
        print(f"[catalogo] error: {exc}")
        return 1

    surface_counts = (
        _normalize_text(frame, "surface").str.lower().value_counts().to_dict()
        if "surface" in frame.columns else {}
    )
    status_counts = (
        _normalize_text(frame, "publication_status").str.lower().value_counts().to_dict()
        if "publication_status" in frame.columns else {}
    )

    print(f"[catalogo] archivo: {catalog_path}")
    print(f"[catalogo] filas: {len(frame)}")
    print(f"[catalogo] superficies: {surface_counts}")
    print(f"[catalogo] estados: {status_counts}")

    if errors:
        for error in errors:
            print(f"[catalogo] error: {error}")
        return 1

    print("[catalogo] validacion ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
