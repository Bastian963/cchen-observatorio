#!/usr/bin/env python3
"""
refresh_semantic_index.py — Observatorio CCHEN 360°
===================================================
Verifica si `paper_embeddings` está desfasada respecto de `publications` en
Supabase. Si detecta diferencias, reconstruye embeddings y los vuelve a subir.

Uso:
    python3 Scripts/refresh_semantic_index.py
    python3 Scripts/refresh_semantic_index.py --force
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / "Database" / ".env")


def _get_client():
    url = os.getenv("SUPABASE_URL", "").strip()
    key = os.getenv("SUPABASE_KEY", "").strip()
    if not url or not key:
        raise RuntimeError("Faltan SUPABASE_URL y/o SUPABASE_KEY")
    from supabase import create_client
    return create_client(url, key)


def _fetch_ids(client, table: str, id_col: str) -> set[str]:
    page_size = 1000
    start = 0
    ids: set[str] = set()

    while True:
        end = start + page_size - 1
        resp = (
            client.table(table)
            .select(id_col)
            .order(id_col)
            .range(start, end)
            .execute()
        )
        rows = resp.data or []
        if not rows:
            break
        for row in rows:
            value = str(row.get(id_col) or "").strip()
            if value:
                ids.add(value)
        if len(rows) < page_size:
            break
        start += page_size

    return ids


def _run_step(command: list[str], extra_env: dict[str, str] | None = None) -> None:
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    result = subprocess.run(command, cwd=ROOT, env=env)
    if result.returncode != 0:
        raise RuntimeError(f"Falló comando: {' '.join(command)}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Recalcular y migrar aunque no se detecten diferencias")
    args = parser.parse_args()

    client = _get_client()
    pub_ids = _fetch_ids(client, "publications", "openalex_id")
    emb_ids = _fetch_ids(client, "paper_embeddings", "openalex_id")

    only_publications = sorted(pub_ids - emb_ids)[:10]
    only_embeddings = sorted(emb_ids - pub_ids)[:10]

    print(f"publications: {len(pub_ids)}")
    print(f"paper_embeddings: {len(emb_ids)}")

    if only_publications:
        print(f"[INFO] IDs sin embedding (muestra): {only_publications}")
    if only_embeddings:
        print(f"[INFO] Embeddings huérfanos (muestra): {only_embeddings}")

    needs_refresh = args.force or pub_ids != emb_ids
    if not needs_refresh:
        print("[OK] Índice semántico al día. No se requiere refresco.")
        return 0

    print("[INFO] Reconstruyendo embeddings desde Supabase/data_loader...")
    _run_step(
        [sys.executable, "Scripts/build_embeddings.py", "--reset"],
        extra_env={"OBSERVATORIO_DATA_SOURCE": "supabase_public"},
    )

    print("[INFO] Subiendo embeddings actualizados a Supabase pgvector...")
    _run_step([sys.executable, "Database/migrate_embeddings.py"])

    print("[OK] Refresco del índice semántico completado.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())