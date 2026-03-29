#!/usr/bin/env python3
"""Gate de consolidacion previa a la beta publica del observatorio."""

from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PUBLIC_DOCS = [
    REPO_ROOT / "README.md",
    REPO_ROOT / "Docs" / "index.html",
    REPO_ROOT / "Docs" / "operations" / "playbook_operaciones.md",
    REPO_ROOT / "Docs" / "operations" / "runbook_publicacion_portal_publico_3en1.md",
]
FORBIDDEN_LOCAL_MARKERS = [
    "http://localhost:",
    "https://localhost:",
    "http://127.0.0.1",
    "https://127.0.0.1",
]
REQUIRED_PUBLIC_HOSTS = [
    "https://observatorio.cchen.cl",
    "https://repo.cchen.cl",
    "https://datos.cchen.cl",
]


def main() -> int:
    errors: list[str] = []

    for path in PUBLIC_DOCS:
        content = path.read_text(encoding="utf-8")
        for marker in FORBIDDEN_LOCAL_MARKERS:
            if marker in content:
                errors.append(f"{path.relative_to(REPO_ROOT)} contiene referencia local: {marker}")

    readme_content = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    for host in REQUIRED_PUBLIC_HOSTS:
        if host not in readme_content:
            errors.append(f"README.md no menciona la superficie publica requerida: {host}")

    if errors:
        for error in errors:
            print(f"[public-beta] ERROR: {error}")
        return 1

    print("[public-beta] OK: documentacion publica sin localhost y con superficies canonicas")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
