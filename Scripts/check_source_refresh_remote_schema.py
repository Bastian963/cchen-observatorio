#!/usr/bin/env python3
"""Verifica el contrato remoto de data_sources + data_source_runs en Supabase."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / "Database" / ".env")
load_dotenv(ROOT / ".env", override=False)


def main() -> int:
    try:
        from supabase import create_client
    except Exception as exc:  # pragma: no cover
        print(f"[remote-schema] FAIL · supabase-py no disponible: {exc}")
        return 1

    url = str(os.getenv("SUPABASE_URL", "")).strip()
    key = (
        str(os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")).strip()
        or str(os.getenv("SUPABASE_KEY", "")).strip()
    )
    if not url or not key:
        print("[remote-schema] FAIL · faltan SUPABASE_URL y/o SUPABASE_KEY")
        return 1

    client = create_client(url, key)

    checks = [
        ("data_sources", "source_key,blocking,last_run_status,last_run_id"),
        ("data_source_runs", "run_id,source_key,status,finished_at"),
    ]

    failures: list[str] = []
    for table, columns in checks:
        try:
            client.table(table).select(columns).limit(1).execute()
            print(f"[remote-schema] OK  · {table} -> {columns}")
        except Exception as exc:
            print(f"[remote-schema] FAIL · {table} -> {exc}")
            failures.append(table)

    if failures:
        print("[remote-schema] schema remoto incompleto para:", ", ".join(failures))
        return 1

    print("[remote-schema] contrato remoto del refresh OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
