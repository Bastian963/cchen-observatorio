#!/usr/bin/env python3
"""Verifica conectividad y legibilidad de las tablas públicas del observatorio en Supabase."""

from __future__ import annotations

import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Dashboard"))

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

try:
    from supabase import create_client
except ImportError as exc:  # pragma: no cover
    raise SystemExit(f"[supabase-check] falta dependencia supabase: {exc}")

if load_dotenv is not None:
    load_dotenv(ROOT / "Database" / ".env")

import data_loader  # noqa: E402


def _get_credentials() -> tuple[str, str]:
    url = (
        os.getenv("SUPABASE_URL")
        or os.getenv("SUPABASE_PUBLIC_URL")
        or ""
    ).strip()
    key = (
        os.getenv("SUPABASE_ANON_KEY")
        or os.getenv("SUPABASE_PUBLIC_ANON_KEY")
        or os.getenv("SUPABASE_KEY")
        or ""
    ).strip()
    return url, key


def _project_id_from_url(url: str) -> str:
    try:
        return url.split("//", 1)[1].split(".", 1)[0]
    except Exception:
        return "desconocido"


def _check_table(client, table_name: str, order_by: str | None) -> tuple[bool, int | None, str]:
    try:
        query = client.table(table_name).select("*", count="exact")
        if order_by:
            query = query.order(order_by)
        resp = query.range(0, 0).execute()
        count = int(resp.count or 0)
        return True, count, ""
    except Exception as exc:
        return False, None, str(exc)


def main() -> int:
    url, key = _get_credentials()
    if not url or not key:
        print("[supabase-check] faltan credenciales. Define SUPABASE_URL y SUPABASE_ANON_KEY/SUPABASE_KEY.")
        return 1

    os.environ["OBSERVATORIO_DATA_SOURCE"] = "supabase_public"

    try:
        client = create_client(url, key)
    except Exception as exc:
        print(f"[supabase-check] no se pudo crear cliente Supabase: {exc}")
        return 1

    config = data_loader.PUBLIC_TABLE_CONFIG
    print(f"[supabase-check] proyecto: {_project_id_from_url(url)}")
    print(f"[supabase-check] url: {url}")
    print(f"[supabase-check] tablas públicas esperadas: {len(config)}")

    failures = 0
    for table_name, meta in sorted(config.items()):
        ok, count, error = _check_table(client, table_name, meta.get("order_by"))
        if ok:
            print(f"  [OK] {table_name:<34} rows={count}")
        else:
            failures += 1
            print(f"  [FAIL] {table_name:<31} {error}")

    if failures:
        print(f"[supabase-check] FAIL · tablas con error: {failures}")
        return 1

    print("[supabase-check] OK · todas las tablas públicas responden")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
