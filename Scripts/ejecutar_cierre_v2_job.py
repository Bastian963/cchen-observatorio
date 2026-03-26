#!/usr/bin/env python3
"""Run cierre_v2_structured.sh with robust status logging.

This runner captures stdout/stderr to a log file and writes a status JSON with:
- start/end timestamps
- exit code
- detected status: success | rate_limited | missing_api_key | failed
- detected error signal
- log path

It does not persist secrets; GROQ_API_KEY must come from environment.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path


def _detect_status(log_text: str, exit_code: int) -> tuple[str, str]:
    text = (log_text or "").lower()
    if "groq_api_key" in text and ("debes exportar" in text or "missing" in text):
        return "missing_api_key", "GROQ_API_KEY not set"
    if "rate_limit_exceeded" in text or "rate limit reached" in text or "429" in text:
        return "rate_limited", "Groq tokens/day rate limit"
    if exit_code == 0:
        return "success", "ok"
    return "failed", "non-zero exit code"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run cierre v2 with persistent status logging")
    parser.add_argument("--run-id", default="", help="Optional run identifier; default is timestamp")
    parser.add_argument(
        "--log-dir",
        default="Docs/reports",
        help="Directory where log and status files will be written",
    )
    args = parser.parse_args()

    run_id = args.run_id or dt.datetime.now().strftime("%Y-%m-%d_%H%M%S")
    log_dir = Path(args.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    log_path = log_dir / f"cierre_v2_job_{run_id}.log"
    status_path = log_dir / f"cierre_v2_job_status_{run_id}.json"

    started_at = dt.datetime.now(dt.timezone.utc)

    cmd = ["bash", "Scripts/cerrar_v2_structured.sh"]
    env = os.environ.copy()

    with log_path.open("w", encoding="utf-8") as logf:
        logf.write(f"[job] run_id={run_id}\n")
        logf.write(f"[job] started_at_utc={started_at.isoformat()}\n")
        logf.write("[job] command=bash Scripts/cerrar_v2_structured.sh\n\n")

        proc = subprocess.run(
            cmd,
            stdout=logf,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
            check=False,
        )

    finished_at = dt.datetime.now(dt.timezone.utc)
    log_text = log_path.read_text(encoding="utf-8", errors="replace")
    status, signal = _detect_status(log_text, proc.returncode)

    payload = {
        "run_id": run_id,
        "started_at_utc": started_at.isoformat(),
        "finished_at_utc": finished_at.isoformat(),
        "duration_seconds": round((finished_at - started_at).total_seconds(), 3),
        "exit_code": int(proc.returncode),
        "status": status,
        "signal": signal,
        "log_path": str(log_path),
        "command": "bash Scripts/cerrar_v2_structured.sh",
    }

    status_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"[job] status: {status}")
    print(f"[job] status_file: {status_path}")
    print(f"[job] log_file: {log_path}")

    if status == "success":
        sys.exit(0)
    if status == "rate_limited":
        sys.exit(10)
    if status == "missing_api_key":
        sys.exit(11)
    sys.exit(1)


if __name__ == "__main__":
    main()
