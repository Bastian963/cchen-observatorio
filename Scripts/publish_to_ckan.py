#!/usr/bin/env python3
"""Publica datasets CKAN a partir del catalogo maestro del observatorio."""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

import pandas as pd
import requests


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = REPO_ROOT / "Data" / "Gobernanza" / "catalogo_activos_3_en_1.csv"
DEFAULT_CKAN_URL = "http://localhost:5001"
TIMEOUT_SECONDS = 30
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


class CkanError(RuntimeError):
    """Error de accion CKAN."""


def _slugify(value: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9_-]+", "-", str(value).strip().lower())
    text = re.sub(r"-{2,}", "-", text).strip("-")
    return text or "dataset"


def _split_values(value: object) -> list[str]:
    text = "" if pd.isna(value) else str(value).strip()
    if not text:
        return []
    return [chunk.strip() for chunk in re.split(r"[;,]\s*", text) if chunk.strip()]


def _notes_from_row(row: pd.Series) -> str:
    lines = [
        f"Activo institucional del observatorio 3 en 1: {row['title']}.",
        f"Tema: {row['tema'] or 'sin tema declarado'}.",
        f"Area o unidad responsable: {row['area_unidad'] or 'sin area declarada'}.",
        f"Responsables: {row['responsables'] or 'sin responsables declarados'}.",
        (
            "Fuente operativa: catalogo maestro del observatorio "
            "`Data/Gobernanza/catalogo_activos_3_en_1.csv`."
        ),
    ]
    return "\n".join(lines)


def _extras_from_row(row: pd.Series) -> list[dict[str, str]]:
    return [
        {"key": "area_unidad", "value": str(row["area_unidad"] or "")},
        {"key": "tema", "value": str(row["tema"] or "")},
        {"key": "anio", "value": str("" if pd.isna(row["anio"]) else int(row["anio"]))},
        {"key": "responsables", "value": str(row["responsables"] or "")},
        {"key": "visibilidad", "value": str(row["visibilidad"] or "")},
        {"key": "identificador", "value": str(row["identificador"] or "")},
        {"key": "dashboard_section", "value": str(row["dashboard_section"] or "")},
        {"key": "vinculo_cruzado", "value": str(row["vinculo_cruzado"] or "")},
        {"key": "asset_id", "value": str(row["asset_id"] or "")},
    ]


def _tags_from_row(row: pd.Series) -> list[dict[str, str]]:
    tags = []
    seen: set[str] = set()
    for value in _split_values(row["palabras_clave"]):
        slug = _slugify(value)[:100]
        if not slug or slug in seen:
            continue
        seen.add(slug)
        tags.append({"name": slug})
    return tags


def _read_catalog(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path, encoding="utf-8-sig")
    missing = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
    if missing:
        raise CkanError(f"El catalogo no contiene columnas requeridas: {', '.join(missing)}")
    return frame


def _build_session(api_key: str) -> requests.Session:
    session = requests.Session()
    session.headers.update({"Authorization": api_key})
    return session


def _ckan_action(
    session: requests.Session,
    base_url: str,
    action: str,
    *,
    payload: dict | None = None,
    files: dict | None = None,
) -> dict:
    url = f"{base_url.rstrip('/')}/api/3/action/{action}"
    if files:
        response = session.post(url, data=payload or {}, files=files, timeout=TIMEOUT_SECONDS)
    else:
        response = session.post(url, json=payload or {}, timeout=TIMEOUT_SECONDS)

    try:
        data = response.json()
    except Exception as exc:
        raise CkanError(f"Respuesta invalida desde CKAN en {action}: {exc}") from exc

    if response.ok and data.get("success"):
        return data["result"]

    error_text = data.get("error") or data
    raise CkanError(f"CKAN action {action} fallo: {error_text}")


def _package_show(session: requests.Session, base_url: str, dataset_name: str) -> dict | None:
    try:
        return _ckan_action(session, base_url, "package_show", payload={"id": dataset_name})
    except CkanError as exc:
        if "Not found" in str(exc) or "No se pudo encontrar" in str(exc):
            return None
        raise


def _organization_show(session: requests.Session, base_url: str, org_name: str) -> dict | None:
    try:
        return _ckan_action(session, base_url, "organization_show", payload={"id": org_name})
    except CkanError as exc:
        if "Not found" in str(exc) or "No se pudo encontrar" in str(exc):
            return None
        raise


def _ensure_organization(
    session: requests.Session,
    base_url: str,
    org_name: str,
    *,
    dry_run: bool,
) -> dict:
    existing = _organization_show(session, base_url, org_name)
    if existing is not None or dry_run:
        return existing or {"name": org_name, "id": org_name}

    payload = {
        "name": org_name,
        "title": "CCHEN Observatorio",
        "description": "Organizacion operativa para la primera ola de datasets del observatorio 3 en 1.",
    }
    return _ckan_action(session, base_url, "organization_create", payload=payload)


def _package_upsert(
    session: requests.Session,
    base_url: str,
    dataset_name: str,
    row: pd.Series,
    *,
    owner_org: str,
    dry_run: bool,
) -> dict:
    payload = {
        "name": dataset_name,
        "title": str(row["title"]),
        "notes": _notes_from_row(row),
        "tags": _tags_from_row(row),
        "extras": _extras_from_row(row),
        "private": str(row["visibilidad"]).strip().lower() == "interno",
        "owner_org": owner_org,
    }

    existing = _package_show(session, base_url, dataset_name)
    if dry_run:
        if existing is None:
            return {"id": dataset_name, "name": dataset_name, "resources": []}
        return existing

    if existing is None:
        return _ckan_action(session, base_url, "package_create", payload=payload)

    payload["id"] = existing["id"]
    return _ckan_action(session, base_url, "package_patch", payload=payload)


def _resource_upsert(
    session: requests.Session,
    base_url: str,
    package: dict,
    row: pd.Series,
    *,
    local_path: Path,
    dry_run: bool,
) -> dict:
    resource_name = local_path.name
    existing = next(
        (resource for resource in package.get("resources", []) if resource.get("name") == resource_name),
        None,
    )

    if dry_run:
        return existing or {"name": resource_name}

    with local_path.open("rb") as handle:
        payload = {
            "package_id": package["id"],
            "name": resource_name,
            "description": f"Recurso publicado desde {row['asset_id']}",
            "format": local_path.suffix.lstrip(".").upper() or "FILE",
        }
        if existing is not None:
            payload["id"] = existing["id"]
            return _ckan_action(
                session,
                base_url,
                "resource_update",
                payload=payload,
                files={"upload": handle},
            )
        return _ckan_action(
            session,
            base_url,
            "resource_create",
            payload=payload,
            files={"upload": handle},
        )


def _update_catalog_row(
    catalog_df: pd.DataFrame,
    *,
    row_index: int,
    dataset_url: str,
) -> None:
    catalog_df.loc[row_index, "public_url"] = dataset_url
    catalog_df.loc[row_index, "publication_status"] = "published"


def _save_catalog(path: Path, catalog_df: pd.DataFrame) -> None:
    catalog_df.to_csv(path, index=False, encoding="utf-8-sig")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", default=str(DEFAULT_CATALOG), help="Ruta al catalogo CSV")
    parser.add_argument("--ckan-url", default=os.getenv("CKAN_URL", DEFAULT_CKAN_URL), help="URL base de CKAN")
    parser.add_argument("--api-key", default=os.getenv("CKAN_API_KEY", ""), help="API key CKAN")
    parser.add_argument("--owner-org", default="cchen-observatorio", help="Organizacion CKAN duena del dataset")
    parser.add_argument("--surface", default="ckan", help="Superficie a publicar")
    parser.add_argument("--status", default="ready_for_publish", help="Estado del catalogo a publicar")
    parser.add_argument("--dry-run", action="store_true", help="No publica ni escribe cambios")
    parser.add_argument(
        "--no-write-back",
        action="store_true",
        help="Publica pero no escribe public_url ni publication_status de vuelta en el catalogo",
    )
    args = parser.parse_args()

    catalog_path = Path(args.catalog).resolve()
    api_key = str(args.api_key).strip()
    if not api_key and not args.dry_run:
        print("[ckan] error: falta CKAN_API_KEY o --api-key")
        return 1

    try:
        catalog_df = _read_catalog(catalog_path)
    except Exception as exc:
        print(f"[ckan] error leyendo catalogo: {exc}")
        return 1

    for column in REQUIRED_COLUMNS:
        if column == "anio":
            continue
        catalog_df[column] = catalog_df[column].fillna("").astype(str).str.strip()
    catalog_df["surface"] = catalog_df["surface"].str.lower()
    catalog_df["publication_status"] = catalog_df["publication_status"].str.lower()
    catalog_df["anio"] = pd.to_numeric(catalog_df["anio"], errors="coerce").astype("Int64")

    candidates = catalog_df[
        (catalog_df["surface"] == str(args.surface).strip().lower()) &
        (catalog_df["publication_status"] == str(args.status).strip().lower())
    ].copy()

    if candidates.empty:
        print("[ckan] no hay filas del catalogo para publicar con esos filtros")
        return 0

    session = _build_session(api_key) if not args.dry_run else requests.Session()
    try:
        _ensure_organization(
            session,
            args.ckan_url,
            _slugify(args.owner_org),
            dry_run=args.dry_run,
        )
    except Exception as exc:
        print(f"[ckan] error creando/verificando organizacion: {exc}")
        return 1
    published = 0
    failed = 0

    for row_index, row in candidates.iterrows():
        dataset_name = _slugify(row["asset_id"])
        local_path = REPO_ROOT / str(row["local_path"])
        if not local_path.exists():
            print(f"[ckan] skip {row['asset_id']}: local_path no existe -> {local_path}")
            failed += 1
            continue

        try:
            package = _package_upsert(
                session,
                args.ckan_url,
                dataset_name,
                row,
                owner_org=_slugify(args.owner_org),
                dry_run=args.dry_run,
            )
            _resource_upsert(
                session,
                args.ckan_url,
                package,
                row,
                local_path=local_path,
                dry_run=args.dry_run,
            )
            dataset_url = f"{args.ckan_url.rstrip('/')}/dataset/{dataset_name}"
            print(f"[ckan] ok {row['asset_id']} -> {dataset_url}")
            if not args.dry_run and not args.no_write_back:
                _update_catalog_row(catalog_df, row_index=row_index, dataset_url=dataset_url)
            published += 1
        except Exception as exc:
            print(f"[ckan] error {row['asset_id']}: {exc}")
            failed += 1

    if not args.dry_run and not args.no_write_back and published > 0:
        _save_catalog(catalog_path, catalog_df)
        print(f"[ckan] catalogo actualizado: {catalog_path}")

    print(f"[ckan] resumen -> publicados: {published} | errores: {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
