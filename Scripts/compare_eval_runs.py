#!/usr/bin/env python3
"""Compare two evaluation run CSV files.

Usage:
    python Scripts/compare_eval_runs.py \\
        --v1 Docs/reports/assistant_eval_structured_responses_v1.csv \\
        --v2 Docs/reports/assistant_eval_structured_responses_v2.csv

Prints a side-by-side Markdown table and saves a diff CSV to Docs/reports/.

The script auto-detects available metrics in each run (retrieval and/or structured).

Optional flags:
    --output PATH   Override output CSV path (default: auto-named diff_<v1label>_vs_<v2label>.csv)
    --no-csv        Skip saving the CSV, only print the table
"""

import argparse
import sys
from pathlib import Path

import pandas as pd


# ── Known metrics (priority order) ────────────────────────────────────────────
_RETRIEVAL_METRICS = [
    "retrieval_ms",
    "n_results",
    "n_with_abstract",
    "top1_score",
    "avg_score",
    "keyword_hits",
]

_STRUCTURED_METRICS = [
    "structured_available_source_ratio",
    "structured_expected_source_count",
    "structured_available_source_count",
    "score_structured_source_grounding",
    "score_structured_synthesis",
    "score_structured_actionability",
]

_RESPONSE_METRICS = [
    "response_ms",
    "heuristic_sources_mentioned",
    "heuristic_citation_tags",
]

_METRIC_CANDIDATES = _RETRIEVAL_METRICS + _STRUCTURED_METRICS + _RESPONSE_METRICS


def _load(path: str) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        print(f"[ERROR] File not found: {path}", file=sys.stderr)
        sys.exit(1)
    df = pd.read_csv(p)
    if "query_id" not in df.columns:
        print(f"[ERROR] Missing 'query_id' column in {path}", file=sys.stderr)
        sys.exit(1)
    return df


def _run_label(df: pd.DataFrame, path: str) -> str:
    if "run_label" in df.columns and df["run_label"].notna().any():
        return str(df["run_label"].dropna().iloc[0])
    return Path(path).stem


def _delta_str(v1, v2) -> str:
    """Return a formatted delta string, or '\u2014' if either value is NaN/None."""
    try:
        f1, f2 = float(v1), float(v2)
        import math
        if math.isnan(f1) or math.isnan(f2):
            return "\u2014"
        d = f2 - f1
        if d == 0:
            return "\u00b10"
        sign = "+" if d > 0 else ""
        # Format: integers for ms / counts, 2 decimals for ratios/scores
        if abs(d) >= 10:
            return f"{sign}{int(round(d))}"
        return f"{sign}{d:.2f}"
    except (TypeError, ValueError):
        return "\u2014"


def _pick_metric_cols(v1: pd.DataFrame, v2: pd.DataFrame) -> list:
    selected = []
    for col in _METRIC_CANDIDATES:
        if col not in v1.columns and col not in v2.columns:
            continue
        s1 = pd.to_numeric(v1[col], errors="coerce") if col in v1.columns else pd.Series(dtype=float)
        s2 = pd.to_numeric(v2[col], errors="coerce") if col in v2.columns else pd.Series(dtype=float)
        if s1.notna().any() or s2.notna().any():
            selected.append(col)
    return selected


def _pick_key_cols(metric_cols: list) -> list:
    preferred = [
        "keyword_hits",
        "top1_score",
        "avg_score",
        "n_results",
        "n_with_abstract",
        "retrieval_ms",
        "heuristic_citation_tags",
        "heuristic_sources_mentioned",
        "response_ms",
        "structured_available_source_ratio",
    ]
    picked = [c for c in preferred if c in metric_cols]
    return picked[:3] if picked else metric_cols[:3]


def _fmt(v) -> str:
    try:
        f = float(v)
        if pd.isna(f):
            return "—"
        return str(int(f)) if f == int(f) else f"{f:.3f}"
    except (ValueError, TypeError):
        return str(v)


def compare(v1_path: str, v2_path: str, output, no_csv: bool) -> None:
    v1 = _load(v1_path)
    v2 = _load(v2_path)
    metric_cols = _pick_metric_cols(v1, v2)
    if not metric_cols:
        print("[ERROR] No known comparable metrics found in input files.", file=sys.stderr)
        sys.exit(1)

    label_v1 = _run_label(v1, v1_path)
    label_v2 = _run_label(v2, v2_path)
    # Avoid duplicate column names when comparing a run against itself
    if label_v1 == label_v2:
        label_v1 = label_v1 + "_a"
        label_v2 = label_v2.rstrip("_a") + "_b"

    # Align on query_id
    all_ids = sorted(set(v1["query_id"]) | set(v2["query_id"]))
    v1 = v1.set_index("query_id")
    v2 = v2.set_index("query_id")

    rows = []
    for qid in all_ids:
        row: dict = {"query_id": qid}
        in_v1 = qid in v1.index
        in_v2 = qid in v2.index

        # Short query text (from whichever run has it)
        q_text = ""
        if in_v1 and "query" in v1.columns:
            q_text = str(v1.at[qid, "query"])[:60]
        elif in_v2 and "query" in v2.columns:
            q_text = str(v2.at[qid, "query"])[:60]
        row["query_short"] = q_text

        for col in metric_cols:
            val_v1 = v1.at[qid, col] if (in_v1 and col in v1.columns) else float("nan")
            val_v2 = v2.at[qid, col] if (in_v2 and col in v2.columns) else float("nan")
            row[f"{col}_v1"] = val_v1
            row[f"{col}_v2"] = val_v2
            row[f"{col}_delta"] = _delta_str(val_v1, val_v2)

        rows.append(row)

    diff = pd.DataFrame(rows)

    # ── Summary aggregates ──────────────────────────────────────────────────
    summary_rows = []
    for col in metric_cols:
        c1 = f"{col}_v1"
        c2 = f"{col}_v2"
        if c1 not in diff.columns:
            continue
        s1 = pd.to_numeric(diff[c1], errors="coerce").mean()
        s2 = pd.to_numeric(diff[c2], errors="coerce").mean()
        summary_rows.append({
            "metric": col,
            f"mean_{label_v1}": round(s1, 3) if pd.notna(s1) else "—",
            f"mean_{label_v2}": round(s2, 3) if pd.notna(s2) else "—",
            "delta_mean": _delta_str(s1, s2),
        })
    summary = pd.DataFrame(summary_rows)

    # ── Print Markdown tables ────────────────────────────────────────────────
    print(f"\n## Comparación: `{label_v1}` vs `{label_v2}`\n")

    # Per-query table for key metrics
    key_cols = _pick_key_cols(metric_cols)
    print("### Por query — métricas clave\n")
    header_parts = ["query_id", "query (truncada)"]
    for c in key_cols:
        header_parts += [f"{c} v1", f"{c} v2", "Δ"]
    print("| " + " | ".join(header_parts) + " |")
    print("|" + "|".join(["---"] * len(header_parts)) + "|")

    for _, r in diff.iterrows():
        row_parts = [str(r["query_id"]), str(r["query_short"])[:45]]
        for c in key_cols:
            v1_val = r.get(f"{c}_v1", "")
            v2_val = r.get(f"{c}_v2", "")
            delta  = r.get(f"{c}_delta", "")
            row_parts += [_fmt(v1_val), _fmt(v2_val), str(delta)]
        print("| " + " | ".join(row_parts) + " |")

    print()
    print("### Resumen agregado (media sobre todas las queries)\n")
    # Manual markdown table (no tabulate dependency)
    cols = list(summary.columns)
    print("| " + " | ".join(cols) + " |")
    print("|" + "|".join(["---"] * len(cols)) + "|")
    for _, r in summary.iterrows():
        print("| " + " | ".join(str(r[c]) for c in cols) + " |")
    print()

    # Citation instruction effectiveness
    if "heuristic_citation_tags_v1" in diff.columns and "heuristic_citation_tags_v2" in diff.columns:
        tags_v1_series = pd.to_numeric(diff["heuristic_citation_tags_v1"], errors="coerce")
        tags_v2_series = pd.to_numeric(diff["heuristic_citation_tags_v2"], errors="coerce")
        if not tags_v1_series.notna().any() and not tags_v2_series.notna().any():
            print("**Instrucción de citación:** no aplica a estos runs (sin columnas pobladas).")
            print()
        else:
            tags_v1 = tags_v1_series.sum()
            tags_v2 = tags_v2_series.sum()
            n_queries = len(diff)
            print(f"**Instrucción de citación:** total tags v1={int(tags_v1 or 0)}, v2={int(tags_v2 or 0)} "
                  f"sobre {n_queries} queries.")
            if (tags_v2 or 0) > (tags_v1 or 0):
                print("→ ✅ La instrucción de citación incrementó los tags `(fuente: X)` en v2.")
            elif (tags_v2 or 0) == (tags_v1 or 0) == 0:
                print("→ ⚠️  Ambas versiones tienen citation_tags=0. El LLM ignoró la instrucción.")
            else:
                print("→ ➡️  Sin cambio claro en citation_tags entre versiones.")
            print()

    # ── Save CSV ─────────────────────────────────────────────────────────────
    if not no_csv:
        if output:
            out_path = Path(output)
        else:
            out_path = Path("Docs/reports") / f"diff_{label_v1}_vs_{label_v2}.csv"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        diff.to_csv(out_path, index=False)
        print(f"[saved] {out_path}")


def main():
    parser = argparse.ArgumentParser(description="Compare two eval runs CSV files.")
    parser.add_argument("--v1", required=True, help="Path to v1 CSV")
    parser.add_argument("--v2", required=True, help="Path to v2 CSV")
    parser.add_argument("--output", default=None, help="Override output CSV path")
    parser.add_argument("--no-csv", action="store_true", help="Skip saving CSV")
    args = parser.parse_args()
    compare(args.v1, args.v2, args.output, args.no_csv)


if __name__ == "__main__":
    main()
