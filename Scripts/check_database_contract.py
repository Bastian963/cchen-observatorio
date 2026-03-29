#!/usr/bin/env python3
"""Valida el contrato entre schema.sql y migrate_to_supabase.py."""

from __future__ import annotations

import ast
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = REPO_ROOT / "Database" / "schema.sql"
MIGRATE_PATHS = [
    REPO_ROOT / "Database" / "migrate_to_supabase.py",
    REPO_ROOT / "Database" / "migrate_dian.py",
    REPO_ROOT / "Database" / "migrate_embeddings.py",
]
DATALOADER_PATH = REPO_ROOT / "Dashboard" / "data_loader.py"
ALLOWED_SCHEMA_ONLY = {"data_sources", "data_source_runs"}


def _extract_schema_tables(schema_text: str) -> set[str]:
    return set(re.findall(r"CREATE TABLE IF NOT EXISTS\s+(\w+)\s*\(", schema_text))


def _extract_rls_tables(schema_text: str) -> set[str]:
    return set(re.findall(r"ALTER TABLE\s+(\w+)\s+ENABLE ROW LEVEL SECURITY", schema_text))


def _extract_policy_tables(schema_text: str) -> set[str]:
    return set(re.findall(r'CREATE POLICY\s+".+?"\s+ON\s+(\w+)\s+FOR', schema_text))


def _extract_migration_tables(tree: ast.AST) -> set[str]:
    tables: set[str] = set()

    class Visitor(ast.NodeVisitor):
        def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
            func = node.func
            if isinstance(func, ast.Name) and func.id == "upsert_table":
                if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                    tables.add(node.args[0].value)
            elif (
                isinstance(func, ast.Attribute)
                and func.attr == "table"
                and isinstance(func.value, ast.Name)
            ):
                if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                    tables.add(node.args[0].value)
            self.generic_visit(node)

    Visitor().visit(tree)
    return tables


def _extract_public_table_config(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "PUBLIC_TABLE_CONFIG":
                value = ast.literal_eval(node.value)
                return set(value.keys())
    raise RuntimeError("No se encontró PUBLIC_TABLE_CONFIG en Dashboard/data_loader.py")


def main() -> int:
    schema_text = SCHEMA_PATH.read_text(encoding="utf-8")
    schema_tables = _extract_schema_tables(schema_text)
    rls_tables = _extract_rls_tables(schema_text)
    policy_tables = _extract_policy_tables(schema_text)
    migration_tables: set[str] = set()
    for migrate_path in MIGRATE_PATHS:
        migrate_text = migrate_path.read_text(encoding="utf-8")
        migrate_tree = ast.parse(migrate_text, filename=str(migrate_path))
        migration_tables |= _extract_migration_tables(migrate_tree)
    public_loader_tables = _extract_public_table_config(DATALOADER_PATH)
    public_schema_tables = {
        table
        for table in policy_tables
        if table in schema_tables and table not in {"capital_humano", "funding_complementario", "entity_registry_personas", "entity_links"}
    }

    errors: list[str] = []

    missing_in_schema = sorted(migration_tables - schema_tables)
    if missing_in_schema:
        errors.append(
            "Tablas usadas por migrate_to_supabase.py que no existen en schema.sql: "
            + ", ".join(missing_in_schema)
        )

    schema_only = sorted(schema_tables - migration_tables - ALLOWED_SCHEMA_ONLY)
    if schema_only:
        errors.append(
            "Tablas definidas en schema.sql sin ruta de migración declarada: "
            + ", ".join(schema_only)
        )

    missing_rls = sorted(schema_tables - rls_tables)
    if missing_rls:
        errors.append(
            "Tablas sin ALTER TABLE ... ENABLE ROW LEVEL SECURITY: "
            + ", ".join(missing_rls)
        )

    missing_policy = sorted(schema_tables - policy_tables)
    if missing_policy:
        errors.append(
            "Tablas sin CREATE POLICY asociado: "
            + ", ".join(missing_policy)
        )

    config_missing = sorted(public_schema_tables - public_loader_tables)
    if config_missing:
        errors.append(
            "Tablas públicas del esquema ausentes en PUBLIC_TABLE_CONFIG: "
            + ", ".join(config_missing)
        )

    config_extra = sorted(public_loader_tables - public_schema_tables)
    if config_extra:
        errors.append(
            "PUBLIC_TABLE_CONFIG contiene tablas que no son públicas o no existen en el esquema: "
            + ", ".join(config_extra)
        )

    print(f"[db-contract] schema tables: {len(schema_tables)}")
    print(f"[db-contract] migration tables: {len(migration_tables)}")
    print(f"[db-contract] tables with RLS: {len(rls_tables)}")
    print(f"[db-contract] tables with policy: {len(policy_tables)}")
    print(f"[db-contract] public tables in loader config: {len(public_loader_tables)}")

    if errors:
        print("[db-contract] FAIL")
        for issue in errors:
            print(f"  - {issue}")
        return 1

    print("[db-contract] OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
