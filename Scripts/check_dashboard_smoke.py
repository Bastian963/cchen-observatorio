#!/usr/bin/env python3
"""Smoke tests ligeros para el dashboard Streamlit del observatorio."""

from __future__ import annotations

import ast
import os
import sys
from pathlib import Path

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_DIR = REPO_ROOT / "Dashboard"
SECTIONS_DIR = DASHBOARD_DIR / "sections"
DATA_LOADER_PATH = DASHBOARD_DIR / "data_loader.py"


def _parse_imports_from_data_loader(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "data_loader":
            imported.update(alias.name for alias in node.names if alias.name != "*")
    return imported


def _collect_loader_exports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
    exports: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            exports.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    exports.add(target.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            exports.add(node.target.id)
    return exports


def _assert_import_contract() -> None:
    importers = [DASHBOARD_DIR / "app.py", *sorted(p for p in SECTIONS_DIR.glob("*.py") if p.name != "__init__.py")]
    exports = _collect_loader_exports(DATA_LOADER_PATH)
    missing_by_file: dict[Path, list[str]] = {}

    for path in importers:
        imported = sorted(name for name in _parse_imports_from_data_loader(path) if name not in exports)
        if imported:
            missing_by_file[path] = imported

    if missing_by_file:
        details = "\n".join(
            f"- {path.relative_to(REPO_ROOT)}: {', '.join(names)}"
            for path, names in sorted(missing_by_file.items())
        )
        raise AssertionError(f"Import contract app/sections -> data_loader roto:\n{details}")


def _load_data_loader_module():
    os.environ.setdefault("OBSERVATORIO_DATA_SOURCE", "local")
    sys.path.insert(0, str(DASHBOARD_DIR))
    import data_loader  # noqa: WPS433

    return data_loader


def _assert_dataframe(name: str, df: pd.DataFrame, required_columns: list[str], allow_empty: bool = False) -> None:
    if not isinstance(df, pd.DataFrame):
        raise AssertionError(f"{name} no retornó un pandas.DataFrame")
    missing = [column for column in required_columns if column not in df.columns]
    if missing:
        raise AssertionError(f"{name} no contiene columnas requeridas: {', '.join(missing)}")
    if not allow_empty and df.empty:
        raise AssertionError(f"{name} está vacío")


def _assert_loader_smoke() -> None:
    data_loader = _load_data_loader_module()

    checks = [
        ("load_convocatorias", ["conv_id", "titulo", "estado"]),
        ("load_convocatorias_matching_rules", ["rule_id", "perfil_id"]),
        ("load_matching_institucional", ["conv_id", "perfil_id", "score_total"]),
        ("load_funding_complementario", ["funding_id", "fuente", "source_confidence"]),
        ("load_perfiles_institucionales", ["perfil_id", "perfil_nombre", "owner_unit"]),
        ("load_entity_registry_personas", ["persona_id", "canonical_name", "institution_id"]),
        ("load_entity_registry_proyectos", ["project_id", "titulo", "institucion_id"]),
        ("load_entity_registry_convocatorias", ["convocatoria_id", "titulo", "perfil_id"]),
        ("load_entity_links", ["origin_type", "origin_id", "target_type"]),
    ]

    for loader_name, required_columns in checks:
        loader = getattr(data_loader, loader_name, None)
        if loader is None:
            raise AssertionError(f"data_loader no expone {loader_name}")
        frame = loader()
        _assert_dataframe(loader_name, frame, required_columns)


def main() -> int:
    print("[smoke] verificando contrato de imports del dashboard...")
    _assert_import_contract()
    print("[smoke] verificando loaders criticos en modo local...")
    _assert_loader_smoke()
    print("[smoke] dashboard ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
