#!/usr/bin/env python3
"""Valida contratos de datos para exportables CSV del Observatorio CCHEN."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONTRACTS_PATH = REPO_ROOT / "Scripts" / "data_contracts_exportables.json"


def _to_number(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def _clean_text(series: pd.Series) -> pd.Series:
    return series.fillna("").astype(str).str.strip()


def _is_boolean_like(value: str) -> bool:
    return value.lower() in {"true", "false", "1", "0", "yes", "no", "si", "no"}


def _type_ok(series: pd.Series, expected_type: str) -> bool:
    clean = _clean_text(series)
    if clean.empty:
        return True

    non_empty = clean[clean != ""]
    if non_empty.empty:
        return True

    t = expected_type.lower()
    if t == "string":
        return True
    if t == "integer":
        nums = _to_number(non_empty)
        return nums.notna().all() and (nums % 1 == 0).all()
    if t == "float":
        nums = _to_number(non_empty)
        return nums.notna().all()
    if t == "boolean":
        return non_empty.map(_is_boolean_like).all()
    if t == "date_iso":
        return non_empty.str.match(r"^\d{4}-\d{2}-\d{2}$").all()
    if t == "week_ref":
        return non_empty.str.match(r"^\d{4}-W\d{2}$").all()
    if t == "url":
        return non_empty.str.match(r"^https?://").all()
    if t == "json_str":
        def _parseable(value: str) -> bool:
            try:
                json.loads(value)
                return True
            except Exception:
                return False

        return non_empty.map(_parseable).all()

    raise ValueError(f"Tipo de dato no soportado: {expected_type}")


def _resolve_path(base_dir: Path, path_glob: str) -> Path | None:
    path = base_dir / path_glob
    if "*" not in path_glob and "?" not in path_glob and "[" not in path_glob:
        return path if path.exists() else None
    matches = sorted(base_dir.glob(path_glob), key=lambda p: p.stat().st_mtime, reverse=True)
    return matches[0] if matches else None


def _validate_contract(contract: dict[str, Any], base_dir: Path) -> tuple[list[str], dict[str, Any]]:
    errors: list[str] = []
    name = contract["name"]
    path_glob = contract["path_glob"]
    optional_if_missing = bool(contract.get("optional_if_missing", False))
    path = _resolve_path(base_dir, path_glob)
    if path is None:
        status = "skipped_missing_optional" if optional_if_missing else "missing_file"
        missing_msg = f"No se encontró archivo para patrón: {path_glob}"
        return ([] if optional_if_missing else [f"[{name}] {missing_msg}"]), {
            "name": name,
            "path": path_glob,
            "path_glob": path_glob,
            "rows": 0,
            "columns": 0,
            "status": status,
            "errors": ([] if optional_if_missing else [missing_msg]),
        }

    try:
        df = pd.read_csv(path)
    except Exception as exc:
        msg = f"No se pudo leer CSV ({path}): {exc}"
        return [f"[{name}] {msg}"], {
            "name": name,
            "path": str(path.relative_to(base_dir)),
            "rows": 0,
            "columns": 0,
            "status": "read_error",
            "errors": [msg],
        }

    required_columns = contract.get("required_columns", [])
    missing_columns = [c for c in required_columns if c not in df.columns]
    if missing_columns:
        errors.append(f"[{name}] Faltan columnas requeridas: {', '.join(missing_columns)}")

    min_rows = int(contract.get("min_rows", 0))
    if len(df) < min_rows:
        errors.append(f"[{name}] Filas insuficientes: {len(df)} < {min_rows}")

    for col in contract.get("non_empty_columns", []):
        if col not in df.columns:
            continue
        blank = _clean_text(df[col]).eq("").sum()
        if blank > 0:
            errors.append(f"[{name}] Columna con valores vacíos: {col} (vacíos={blank})")

    for col, expected in contract.get("column_types", {}).items():
        if col not in df.columns:
            continue
        if not _type_ok(df[col], expected):
            errors.append(f"[{name}] Tipo inválido en columna {col}. Esperado: {expected}")

    for col, allowed in contract.get("allowed_values", {}).items():
        if col not in df.columns:
            continue
        non_empty = _clean_text(df[col])
        non_empty = non_empty[non_empty != ""]
        invalid = sorted(set(non_empty) - set(allowed))
        if invalid:
            errors.append(
                f"[{name}] Valores fuera de catálogo en {col}: {', '.join(invalid[:8])}"
            )

    stats = {
        "name": name,
        "path": str(path.relative_to(base_dir)),
        "rows": int(len(df)),
        "columns": int(len(df.columns)),
        "validated_columns": list(df.columns),
        "status": "ok" if not errors else "fail",
        "errors": errors,
    }
    return errors, stats


def main() -> int:
    parser = argparse.ArgumentParser(description="Validador de contratos de exportables CSV")
    parser.add_argument(
        "--contracts",
        default=str(DEFAULT_CONTRACTS_PATH),
        help="Ruta JSON de contratos (default: Scripts/data_contracts_exportables.json)",
    )
    parser.add_argument(
        "--base-dir",
        default=str(REPO_ROOT),
        help="Directorio base para resolver path_glob",
    )
    parser.add_argument(
        "--report-out",
        default="",
        help="Ruta de salida para reporte JSON de validación (opcional)",
    )
    args = parser.parse_args()

    contracts_path = Path(args.contracts)
    base_dir = Path(args.base_dir)
    if not contracts_path.exists():
        print(f"[contracts] FAIL - no existe archivo de contratos: {contracts_path}")
        return 1

    payload = json.loads(contracts_path.read_text(encoding="utf-8"))
    contracts = payload.get("contracts", [])
    if not contracts:
        print("[contracts] FAIL - archivo de contratos vacío")
        return 1

    all_errors: list[str] = []
    stats_rows: list[dict[str, Any]] = []
    for contract in contracts:
        errors, stats = _validate_contract(contract, base_dir)
        all_errors.extend(errors)
        stats_rows.append(stats)

    print(f"[contracts] contratos evaluados: {len(contracts)}")
    for row in stats_rows:
        print(
            f"  - {row['name']}: rows={row.get('rows', 0)} "
            f"cols={row.get('columns', 0)} file={row.get('path', row.get('path_glob', '-'))}"
        )

    status = "ok"
    exit_code = 0
    if all_errors:
        print("[contracts] FAIL")
        for err in all_errors:
            print(f"  - {err}")
        status = "fail"
        exit_code = 1

    report = {
        "status": status,
        "contracts_evaluated": len(contracts),
        "contracts": stats_rows,
        "errors": all_errors,
    }

    if args.report_out:
        report_path = Path(args.report_out)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[contracts] reporte JSON: {report_path}")

    if status == "ok":
        print("[contracts] OK")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
