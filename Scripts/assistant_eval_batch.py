#!/usr/bin/env python3
"""Batch evaluation helper for Asistente I+D retrieval quality.

Input CSV columns (required):
- query_id
- query

Optional columns:
- must_include_keywords (semicolon-separated)
- expected_focus

Output CSV includes retrieval metrics and empty manual-review fields so runs can be
compared across versions.
"""

from __future__ import annotations

import argparse
import datetime as dt
import numbers
import re
from pathlib import Path
from typing import Iterable

import pandas as pd

import semantic_search as ss


DEFAULT_INPUT = Path("Docs/reports/assistant_eval_template.csv")
DEFAULT_OUT_DIR = Path("Docs/reports")


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip().lower()


def _keyword_hits(keywords_raw: str, corpus_text: str) -> tuple[int, str]:
    if not str(keywords_raw or "").strip():
        return 0, ""
    keywords = [k.strip().lower() for k in str(keywords_raw).split(";") if k.strip()]
    hits = [k for k in keywords if k in corpus_text]
    return len(hits), ";".join(hits)


def _safe_float_mean(series: pd.Series) -> float:
    s = series if isinstance(series, pd.Series) else pd.Series(dtype=object)
    if len(s) == 0:
        return 0.0
    vals = _to_float_list(s.tolist())
    return float(sum(vals) / len(vals)) if vals else 0.0


def _to_float_list(values: Iterable[object]) -> list[float]:
    out: list[float] = []
    for raw in values:
        if isinstance(raw, numbers.Real):
            out.append(float(raw))
            continue
        if isinstance(raw, str):
            try:
                out.append(float(raw.strip()))
            except ValueError:
                pass
    return out


def run_batch(input_csv: Path, output_csv: Path, top_k: int, run_label: str) -> Path:
    df = pd.read_csv(input_csv).fillna("")
    required = {"query_id", "query"}
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"Input missing required columns: {missing}")

    rows: list[dict] = []
    started_at = dt.datetime.now().isoformat(timespec="seconds")

    for _, r in df.iterrows():
        query_id = str(r.get("query_id", "")).strip()
        query = str(r.get("query", "")).strip()
        if not query_id or not query:
            continue

        t0 = dt.datetime.now()
        rag = ss.search(query, top_k=top_k)
        elapsed_ms = int((dt.datetime.now() - t0).total_seconds() * 1000)

        rag = rag if isinstance(rag, pd.DataFrame) else pd.DataFrame()
        rag = rag.where(pd.notna(rag), "")

        titles = " || ".join(str(v)[:140] for v in rag.get("title", pd.Series(dtype=str)).head(5).tolist())
        abstracts = " || ".join(str(v)[:220] for v in rag.get("abstract", pd.Series(dtype=str)).head(3).tolist())
        corpus_text = _normalize_text(titles + " " + abstracts)
        keyword_hits, keyword_hits_list = _keyword_hits(r.get("must_include_keywords", ""), corpus_text)

        n_results = int(len(rag))
        n_with_abstract = int(
            rag.get("abstract", pd.Series(dtype=str))
            .astype(str)
            .str.strip()
            .replace({"nan": "", "none": ""}, regex=False)
            .ne("")
            .sum()
        ) if n_results else 0

        score_series = rag.get("score")
        score_series = score_series if isinstance(score_series, pd.Series) else pd.Series(dtype=float)
        score_numeric = _to_float_list(score_series.tolist())
        top1_score = float(score_numeric[0]) if n_results and score_numeric else 0.0
        avg_score = _safe_float_mean(pd.Series(score_numeric, dtype=float))

        rows.append({
            "run_label": run_label,
            "run_started_at": started_at,
            "query_id": query_id,
            "query": query,
            "expected_focus": r.get("expected_focus", ""),
            "must_include_keywords": r.get("must_include_keywords", ""),
            "retrieval_top_k": top_k,
            "retrieval_ms": elapsed_ms,
            "n_results": n_results,
            "n_with_abstract": n_with_abstract,
            "top1_score": round(top1_score, 4),
            "avg_score": round(avg_score, 4),
            "keyword_hits": keyword_hits,
            "keyword_hits_list": keyword_hits_list,
            "top_titles": titles,
            "top_abstract_snippets": abstracts,
            "score_context_relevance": r.get("score_context_relevance", ""),
            "score_answer_quality": r.get("score_answer_quality", ""),
            "hallucination_flag": r.get("hallucination_flag", ""),
            "reviewer_notes": r.get("reviewer_notes", ""),
        })

    out = pd.DataFrame(rows)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(output_csv, index=False)
    return output_csv


def run_compare(current_csv: Path, previous_csv: Path, compare_out_csv: Path) -> Path:
    cur = pd.read_csv(current_csv).fillna("")
    prev = pd.read_csv(previous_csv).fillna("")

    merge_cols = [
        "query_id",
        "n_results",
        "n_with_abstract",
        "top1_score",
        "avg_score",
        "keyword_hits",
        "retrieval_ms",
    ]
    prev = prev[[c for c in merge_cols if c in prev.columns]].rename(columns={
        "n_results": "prev_n_results",
        "n_with_abstract": "prev_n_with_abstract",
        "top1_score": "prev_top1_score",
        "avg_score": "prev_avg_score",
        "keyword_hits": "prev_keyword_hits",
        "retrieval_ms": "prev_retrieval_ms",
    })

    merged = cur.merge(prev, on="query_id", how="left")

    def delta(col: str, prev_col: str) -> pd.Series:
        return pd.to_numeric(merged.get(col), errors="coerce") - pd.to_numeric(merged.get(prev_col), errors="coerce")

    merged["delta_n_results"] = delta("n_results", "prev_n_results")
    merged["delta_n_with_abstract"] = delta("n_with_abstract", "prev_n_with_abstract")
    merged["delta_top1_score"] = delta("top1_score", "prev_top1_score")
    merged["delta_avg_score"] = delta("avg_score", "prev_avg_score")
    merged["delta_keyword_hits"] = delta("keyword_hits", "prev_keyword_hits")
    merged["delta_retrieval_ms"] = delta("retrieval_ms", "prev_retrieval_ms")

    compare_out_csv.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(compare_out_csv, index=False)
    return compare_out_csv


def main() -> int:
    parser = argparse.ArgumentParser(description="Batch evaluator for Asistente I+D retrieval")
    parser.add_argument("--input", default=str(DEFAULT_INPUT), help="Input CSV with prompts")
    parser.add_argument("--output", default="", help="Output CSV path")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--run-label", default=f"run_{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}")
    parser.add_argument("--compare-with", default="", help="Previous run CSV to compare against")
    parser.add_argument("--compare-output", default="", help="Comparison output CSV path")
    args = parser.parse_args()

    input_csv = Path(args.input)
    if args.output:
        output_csv = Path(args.output)
    else:
        output_csv = DEFAULT_OUT_DIR / f"assistant_eval_run_{dt.datetime.now().strftime('%Y-%m-%d_%H%M%S')}.csv"

    out_path = run_batch(input_csv=input_csv, output_csv=output_csv, top_k=args.top_k, run_label=args.run_label)
    print(f"[OK] Batch guardado en: {out_path}")

    if args.compare_with:
        prev = Path(args.compare_with)
        if args.compare_output:
            cmp_out = Path(args.compare_output)
        else:
            cmp_out = DEFAULT_OUT_DIR / f"assistant_eval_compare_{dt.datetime.now().strftime('%Y-%m-%d_%H%M%S')}.csv"
        cmp_path = run_compare(current_csv=out_path, previous_csv=prev, compare_out_csv=cmp_out)
        print(f"[OK] Comparacion guardada en: {cmp_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
