#!/usr/bin/env python3
"""Runner canónico para refresco de fuentes del observatorio."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
import uuid
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from source_refresh_registry import (
    REGISTRY_COLUMNS,
    RUN_COLUMNS,
    build_registry_frame,
    frequency_to_days,
    load_registry_snapshot,
    load_runs_snapshot,
    parse_output_targets,
    reports_dir,
    registry_snapshot_path,
    runs_snapshot_path,
    save_registry_snapshot,
    save_runs_snapshot,
)


ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / "Database" / ".env")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Orquestador único de refresh de fuentes.")
    parser.add_argument("--source-key", help="Ejecuta una fuente específica por source_key.")
    parser.add_argument("--all-due", action="store_true", help="Ejecuta todas las fuentes habilitadas y vencidas.")
    parser.add_argument("--force", action="store_true", help="Fuerza la ejecución aunque la fuente no esté vencida.")
    parser.add_argument("--dry-run", action="store_true", help="Enumera fuentes y comandos sin ejecutar mutaciones.")
    args = parser.parse_args()
    if bool(args.source_key) == bool(args.all_due):
        parser.error("Debes indicar exactamente una de estas opciones: --source-key o --all-due.")
    return args


def parse_iso_date(value: object) -> dt.date | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return dt.date.fromisoformat(text[:10])
    except ValueError:
        return None


def compute_next_due(last_updated: dt.date | None, frequency: str, freshness_sla_days: int | None) -> str:
    if last_updated is None:
        return ""
    delta_days = frequency_to_days(frequency) or freshness_sla_days or 0
    if delta_days <= 0:
        return ""
    return (last_updated + dt.timedelta(days=delta_days)).isoformat()


def is_source_due(row: pd.Series, reference_date: dt.date | None = None, *, force: bool = False) -> bool:
    if force:
        return True
    if not bool(row.get("enabled")):
        return False
    today = reference_date or dt.date.today()
    next_due = parse_iso_date(row.get("next_update_due"))
    if next_due is not None:
        return next_due <= today
    last_updated = parse_iso_date(row.get("last_updated"))
    if last_updated is None:
        return True
    delta_days = frequency_to_days(str(row.get("update_frequency", ""))) or row.get("freshness_sla_days") or 0
    try:
        delta_days = int(delta_days)
    except Exception:
        delta_days = 0
    if delta_days <= 0:
        return False
    return last_updated + dt.timedelta(days=delta_days) <= today


def select_due_sources(registry_df: pd.DataFrame, *, force: bool = False, reference_date: dt.date | None = None) -> pd.DataFrame:
    today = reference_date or dt.date.today()
    mask = registry_df.apply(lambda row: is_source_due(row, today, force=force), axis=1)
    selected = registry_df.loc[mask].copy()
    if selected.empty:
        return selected
    return selected.sort_values(["blocking", "update_frequency", "source_key"], ascending=[False, True, True])


def _command_for_log(command: str) -> str:
    return " ".join(command.split())


def _normalize_command_for_execution(command: str) -> str:
    python_bin = sys.executable or "python3"
    return re.sub(r"(?<![\w/.-])python(?=\s)", python_bin, command)


def _count_records(path: Path) -> int:
    if not path.exists():
        return 0
    if path.is_dir():
        return sum(1 for _ in path.iterdir())
    if path.suffix.lower() != ".csv":
        return int(path.stat().st_size > 0)
    try:
        with path.open("r", encoding="utf-8-sig") as handle:
            return max(sum(1 for _ in handle) - 1, 0)
    except UnicodeDecodeError:
        with path.open("r", encoding="utf-8") as handle:
            return max(sum(1 for _ in handle) - 1, 0)


def collect_artifacts(targets: list[str]) -> list[dict[str, object]]:
    artifacts: list[dict[str, object]] = []
    for target in targets:
        target_path = Path(target)
        absolute = target_path if target_path.is_absolute() else ROOT / target_path
        exists = absolute.exists()
        modified_at = ""
        if exists:
            try:
                modified_at = dt.datetime.fromtimestamp(absolute.stat().st_mtime).isoformat(timespec="seconds")
            except OSError:
                modified_at = ""
        artifacts.append(
            {
                "path": str(target),
                "exists": exists,
                "kind": "directory" if absolute.is_dir() else "file",
                "records": _count_records(absolute) if exists else 0,
                "modified_at": modified_at,
            }
        )
    return artifacts


def _run_data_quality_report(report_path: Path) -> pd.DataFrame:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    command = [sys.executable, "Database/data_quality.py", "--output", str(report_path)]
    subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    if not report_path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(report_path, encoding="utf-8-sig").fillna("")
    except Exception:
        return pd.DataFrame()


def score_artifacts(artifacts: list[dict[str, object]], quality_df: pd.DataFrame) -> float | None:
    if not artifacts:
        return None
    score_by_state = {"OK": 1.0, "ADVERTENCIA": 0.6, "CRITICO": 0.0}
    quality_lookup = {}
    if not quality_df.empty and {"archivo", "estado"}.issubset(quality_df.columns):
        quality_lookup = {
            str(row["archivo"]).strip(): score_by_state.get(str(row["estado"]).strip(), 0.5)
            for _, row in quality_df.iterrows()
        }

    scores: list[float] = []
    for artifact in artifacts:
        path = str(artifact.get("path", "")).strip()
        if not path:
            continue
        if path in quality_lookup:
            scores.append(quality_lookup[path])
        elif artifact.get("exists"):
            scores.append(1.0)
        else:
            scores.append(0.0)
    if not scores:
        return None
    return round(sum(scores) / len(scores), 3)


def _sanitize_error(text: str) -> str:
    clean = " ".join(str(text or "").split())
    return clean[:1000]


def _maybe_get_supabase_client():
    url = str(os.getenv("SUPABASE_URL", "")).strip()
    key = (
        str(os.getenv("SUPABASE_KEY", "")).strip()
        or str(os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")).strip()
    )
    if not url or not key:
        return None
    try:
        from supabase import create_client

        return create_client(url, key)
    except Exception:
        return None


def _upsert_supabase_state(source_rows: list[dict[str, object]], run_rows: list[dict[str, object]]) -> None:
    client = _maybe_get_supabase_client()
    if client is None:
        return

    registry_payload = []
    for row in source_rows:
        payload = {
            "source_key": row.get("source_key"),
            "source_name": row.get("source_name"),
            "description": row.get("description"),
            "url": row.get("url"),
            "table_name": row.get("table_name") or None,
            "notebook_path": row.get("notebook_path") or None,
            "last_updated": row.get("last_updated") or None,
            "next_update_due": row.get("next_update_due") or None,
            "update_frequency": row.get("update_frequency"),
            "record_count": int(row.get("record_count") or 0),
            "quality_score": float(row.get("quality_score")) if pd.notna(row.get("quality_score")) else None,
            "requires_token": bool(row.get("requires_token")),
            "token_source": row.get("token_source") or None,
            "notes": row.get("notes") or None,
            "enabled": bool(row.get("enabled")),
            "runner_command": row.get("runner_command") or None,
            "output_targets": parse_output_targets(row.get("output_targets")),
            "owner": row.get("owner") or None,
            "visibility": row.get("visibility") or None,
            "blocking": bool(row.get("blocking")),
            "freshness_sla_days": int(row.get("freshness_sla_days") or 0),
            "last_run_status": row.get("last_run_status") or None,
            "last_run_id": row.get("last_run_id") or None,
            "updated_at": row.get("updated_at") or None,
        }
        registry_payload.append(payload)

    if registry_payload:
        try:
            client.table("data_sources").upsert(registry_payload, on_conflict="source_key").execute()
        except Exception as exc:
            print(f"[WARN] No se pudo sincronizar data_sources en Supabase: {exc}")

    run_payload = []
    for row in run_rows:
        run_payload.append(
            {
                "run_id": row.get("run_id"),
                "source_key": row.get("source_key"),
                "trigger_kind": row.get("trigger_kind"),
                "started_at": row.get("started_at"),
                "finished_at": row.get("finished_at"),
                "status": row.get("status"),
                "records_written": int(row.get("records_written") or 0),
                "artifacts_json": json.loads(str(row.get("artifacts_json") or "[]")),
                "error_summary": row.get("error_summary") or None,
            }
        )

    if run_payload:
        try:
            client.table("data_source_runs").upsert(run_payload, on_conflict="run_id,source_key").execute()
        except Exception as exc:
            print(f"[WARN] No se pudo sincronizar data_source_runs en Supabase: {exc}")


def _write_run_report(run_id: str, row: pd.Series, run_row: dict[str, object]) -> Path:
    report_root = reports_dir()
    report_root.mkdir(parents=True, exist_ok=True)
    started = str(run_row.get("started_at", "")).replace(":", "").replace("-", "")
    report_path = report_root / f"{started[:15]}_{row['source_key']}.json"
    report_payload = {
        "run_id": run_id,
        "source_key": row["source_key"],
        "source_name": row["source_name"],
        "trigger_kind": run_row["trigger_kind"],
        "started_at": run_row["started_at"],
        "finished_at": run_row["finished_at"],
        "status": run_row["status"],
        "records_written": run_row["records_written"],
        "artifacts": json.loads(run_row["artifacts_json"]),
        "error_summary": run_row["error_summary"],
        "runner_command": row["runner_command"],
        "update_frequency": row["update_frequency"],
        "next_update_due": row["next_update_due"],
    }
    report_path.write_text(json.dumps(report_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return report_path


def _run_job(command: str) -> tuple[int, str, str]:
    normalized_command = _normalize_command_for_execution(command)
    result = subprocess.run(
        normalized_command,
        cwd=ROOT,
        shell=True,
        executable="/bin/bash",
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode, result.stdout, result.stderr


def execute_group(
    registry_df: pd.DataFrame,
    group_df: pd.DataFrame,
    runs_df: pd.DataFrame,
    *,
    trigger_kind: str,
    dry_run: bool,
) -> tuple[pd.DataFrame, pd.DataFrame, bool]:
    representative = group_df.iloc[0]
    command = str(representative.get("runner_command", "")).strip()
    group_label = str(representative.get("job_key") or representative.get("source_key"))
    selected_keys = ", ".join(group_df["source_key"].astype(str).tolist())

    if dry_run:
        print(f"[dry-run] job={group_label} -> {selected_keys}")
        if command:
            print(f"          command={_command_for_log(command)}")
        else:
            print("          command=<sin comando>")
        return registry_df, runs_df, True

    started_at = dt.datetime.now().isoformat(timespec="seconds")
    run_id = f"{dt.datetime.now().strftime('%Y%m%dT%H%M%S')}_{uuid.uuid4().hex[:8]}"
    quality_report_path = reports_dir() / f"quality_{run_id}.csv"

    if not command:
        status = "disabled"
        stdout = ""
        stderr = "Fuente registrada sin runner_command; automatización pendiente."
        return_code = 1
    else:
        print(f"[run] job={group_label} -> {selected_keys}")
        print(f"      command={_command_for_log(command)}")
        return_code, stdout, stderr = _run_job(command)
        status = "success" if return_code == 0 else "failed"

    finished_at = dt.datetime.now().isoformat(timespec="seconds")
    quality_df = _run_data_quality_report(quality_report_path)
    blocking_failed = False
    source_rows_to_upsert: list[dict[str, object]] = []
    run_rows_to_upsert: list[dict[str, object]] = []

    for _, row in group_df.iterrows():
        targets = parse_output_targets(row.get("output_targets"))
        artifacts = collect_artifacts(targets)
        records_written = sum(int(artifact.get("records") or 0) for artifact in artifacts)
        artifact_dates = [parse_iso_date(artifact.get("modified_at")) for artifact in artifacts if artifact.get("modified_at")]
        freshest = max((date for date in artifact_dates if date is not None), default=None)
        if freshest is None and status == "success":
            freshest = dt.date.today()

        quality_score = score_artifacts(artifacts, quality_df)
        next_due = compute_next_due(
            freshest,
            str(row.get("update_frequency", "")),
            int(row.get("freshness_sla_days") or 0),
        )

        registry_df.loc[registry_df["source_key"] == row["source_key"], [
            "last_updated",
            "next_update_due",
            "record_count",
            "quality_score",
            "last_run_status",
            "last_run_id",
            "updated_at",
        ]] = [
            freshest.isoformat() if freshest else "",
            next_due,
            records_written,
            quality_score,
            status,
            run_id,
            finished_at,
        ]

        run_row = {
            "run_id": run_id,
            "source_key": row["source_key"],
            "trigger_kind": trigger_kind,
            "started_at": started_at,
            "finished_at": finished_at,
            "status": status,
            "records_written": records_written,
            "artifacts_json": json.dumps(artifacts, ensure_ascii=False),
            "error_summary": _sanitize_error(stderr) if return_code != 0 else "",
        }
        runs_df = pd.concat([runs_df, pd.DataFrame([run_row], columns=RUN_COLUMNS)], ignore_index=True)
        _write_run_report(run_id, row, run_row)

        source_rows_to_upsert.append(registry_df.loc[registry_df["source_key"] == row["source_key"]].iloc[0].to_dict())
        run_rows_to_upsert.append(run_row)

        if return_code != 0 and bool(row.get("blocking")):
            blocking_failed = True

    _upsert_supabase_state(source_rows_to_upsert, run_rows_to_upsert)
    if quality_report_path.exists():
        try:
            quality_report_path.unlink()
        except OSError:
            pass
    return registry_df, runs_df, not blocking_failed


def main() -> int:
    args = parse_args()
    registry_df = load_registry_snapshot()
    runs_df = load_runs_snapshot()
    trigger_kind = "manual"

    if args.source_key:
        selected = registry_df[registry_df["source_key"] == args.source_key].copy()
        if selected.empty:
            print(f"[source-refresh] source_key no encontrado: {args.source_key}")
            return 1
        trigger_kind = "manual_force" if args.force else "manual_source"
    else:
        selected = select_due_sources(registry_df, force=args.force)
        trigger_kind = "scheduled_force" if args.force else "scheduled_due"

    if selected.empty:
        print("[source-refresh] No hay fuentes seleccionadas para ejecutar.")
        return 0

    if args.dry_run:
        print(f"[source-refresh] dry-run | fuentes seleccionadas: {len(selected)}")

    success = True
    for _, group_df in selected.groupby(selected["job_key"].fillna(selected["source_key"]), sort=False):
        registry_df, runs_df, group_ok = execute_group(
            registry_df,
            group_df,
            runs_df,
            trigger_kind=trigger_kind,
            dry_run=args.dry_run,
        )
        success = success and group_ok

    if not args.dry_run:
        save_registry_snapshot(build_registry_frame(registry_df), registry_snapshot_path())
        save_runs_snapshot(runs_df, runs_snapshot_path())
        print(f"[source-refresh] registry snapshot -> {registry_snapshot_path()}")
        print(f"[source-refresh] runs snapshot -> {runs_snapshot_path()}")

    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
