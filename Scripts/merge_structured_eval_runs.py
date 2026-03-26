#!/usr/bin/env python3
"""Merge two structured-response eval CSVs into one final report-ready file.

Typical use case:
- head: run parcial con Q01-Q02 exitosas
- tail: rerun posterior con Q03-Q10

The script merges by query_id, resolves duplicates, optionally validates against
a template, and writes one consolidated CSV.

Example:
    .venv/bin/python Scripts/merge_structured_eval_runs.py \
      --head Docs/reports/assistant_eval_structured_responses_v2_head_q01_q02.csv \
      --tail Docs/reports/assistant_eval_structured_responses_v2_pending.csv \
      --template Docs/reports/assistant_eval_template.csv \
      --run-label structured_responses_v2_final \
      --output Docs/reports/assistant_eval_structured_responses_v2_final.csv
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Tuple

import pandas as pd


def _load_csv(path: str) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {path}")
    df = pd.read_csv(p)
    if "query_id" not in df.columns:
        raise ValueError(f"Missing 'query_id' column in: {path}")
    if df.empty:
        raise ValueError(f"Input CSV is empty: {path}")
    return df


def _expected_query_ids(template_path: str) -> List[str]:
    template = _load_csv(template_path)
    return [str(x) for x in template["query_id"].dropna().astype(str).tolist()]


def _merge_by_query_id(
    head: pd.DataFrame,
    tail: pd.DataFrame,
    prefer: str,
) -> Tuple[pd.DataFrame, List[str]]:
    h = head.copy()
    t = tail.copy()
    h["_merge_source"] = "head"
    t["_merge_source"] = "tail"

    combined = pd.concat([h, t], ignore_index=True)

    dup_mask = combined["query_id"].duplicated(keep=False)
    duplicated_ids = sorted(combined.loc[dup_mask, "query_id"].astype(str).unique().tolist())

    keep = "last" if prefer == "tail" else "first"
    merged = combined.drop_duplicates(subset=["query_id"], keep=keep).copy()

    return merged, duplicated_ids


def _order_by_template(merged: pd.DataFrame, expected_ids: List[str]) -> pd.DataFrame:
    merged = merged.copy()
    merged["query_id"] = merged["query_id"].astype(str)
    order = {qid: i for i, qid in enumerate(expected_ids)}
    merged["_order"] = merged["query_id"].map(order).fillna(10**9).astype(int)
    merged = merged.sort_values(["_order", "query_id"], ascending=[True, True])
    return merged.drop(columns=["_order"], errors="ignore")


def main() -> None:
    parser = argparse.ArgumentParser(description="Merge structured eval CSV runs by query_id")
    parser.add_argument("--head", required=True, help="CSV with first successful chunk (e.g., Q01-Q02)")
    parser.add_argument("--tail", required=True, help="CSV with rerun chunk (e.g., Q03-Q10)")
    parser.add_argument(
        "--output",
        default="Docs/reports/assistant_eval_structured_responses_v2_final.csv",
        help="Output CSV path",
    )
    parser.add_argument(
        "--template",
        default="",
        help="Optional template CSV to validate completeness and enforce final ordering",
    )
    parser.add_argument(
        "--prefer",
        choices=["head", "tail"],
        default="tail",
        help="When query_id appears in both files, keep value from this side",
    )
    parser.add_argument(
        "--run-label",
        default="",
        help="Optional run_label value to set on all merged rows",
    )
    parser.add_argument(
        "--strict-complete",
        action="store_true",
        help="Exit with code 2 if any template query_id is missing in merged output",
    )
    args = parser.parse_args()

    try:
        head = _load_csv(args.head)
        tail = _load_csv(args.tail)
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        sys.exit(1)

    merged, duplicated_ids = _merge_by_query_id(head, tail, prefer=args.prefer)

    expected_ids: List[str] = []
    missing: List[str] = []
    extra: List[str] = []

    if args.template:
        try:
            expected_ids = _expected_query_ids(args.template)
        except Exception as exc:
            print(f"[ERROR] Template validation failed: {exc}", file=sys.stderr)
            sys.exit(1)

        merged_ids = set(merged["query_id"].astype(str).tolist())
        expected_set = set(expected_ids)
        missing = sorted(expected_set - merged_ids)
        extra = sorted(merged_ids - expected_set)
        merged = _order_by_template(merged, expected_ids)

    if args.run_label:
        merged["run_label"] = args.run_label

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    merged = merged.drop(columns=["_merge_source"], errors="ignore")
    merged.to_csv(out_path, index=False)

    print("[OK] Merge completed")
    print(f"  head rows: {len(head)}")
    print(f"  tail rows: {len(tail)}")
    print(f"  merged rows (unique query_id): {len(merged)}")
    if duplicated_ids:
        print(f"  duplicate query_id resolved with --prefer={args.prefer}: {', '.join(duplicated_ids)}")

    if args.template:
        print(f"  expected query_id from template: {len(expected_ids)}")
        print(f"  missing query_id: {len(missing)}")
        if missing:
            print(f"    -> {', '.join(missing)}")
        print(f"  extra query_id: {len(extra)}")
        if extra:
            print(f"    -> {', '.join(extra)}")

    print(f"  output: {out_path}")

    if args.strict_complete and missing:
        print("[ERROR] strict-complete enabled and merged output is missing query_id(s)", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
