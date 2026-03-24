#!/usr/bin/env python3
"""Batch evaluation helper for Asistente I+D retrieval quality.

Input CSV columns (required):
- query_id
- query

Optional columns:
- evaluation_mode
- must_include_keywords (semicolon-separated)
- expected_focus
- expected_data_sources

Output CSV includes retrieval metrics and empty manual-review fields so runs can be
compared across versions.
"""

from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import numbers
import os
import re
import sys
from functools import lru_cache
from pathlib import Path
from typing import Iterable

import pandas as pd

import semantic_search as ss


DEFAULT_INPUT = Path("Docs/reports/assistant_eval_template.csv")
DEFAULT_OUT_DIR = Path("Docs/reports")
PUBLICATION_RAG = "publication_rag"
STRUCTURED_OR_HYBRID = "structured_or_hybrid"
VALID_EVALUATION_MODES = {PUBLICATION_RAG, STRUCTURED_OR_HYBRID}
ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_DIR = ROOT / "Dashboard"
SECTIONS_DIR = DASHBOARD_DIR / "sections"

for _path in (DASHBOARD_DIR, SECTIONS_DIR):
    path_str = str(_path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

def _load_module(module_name: str, file_path: Path):
    try:
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except Exception:
        return None


_data_loader_module = _load_module("assistant_eval_data_loader", DASHBOARD_DIR / "data_loader.py")
_shared_module = _load_module("assistant_eval_shared", SECTIONS_DIR / "shared.py")
dl = _data_loader_module
_load_portafolio_seed = getattr(_shared_module, "_load_portafolio_seed", None) if _shared_module is not None else None


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


def _normalize_mode(value: object) -> str:
    raw = str(value or "").strip().lower()
    return raw if raw in VALID_EVALUATION_MODES else STRUCTURED_OR_HYBRID


def _filter_rows_by_mode(df: pd.DataFrame, evaluation_mode: str) -> pd.DataFrame:
    if evaluation_mode == "all":
        return df
    modes = df["evaluation_mode"].map(_normalize_mode) if "evaluation_mode" in df.columns else pd.Series(STRUCTURED_OR_HYBRID, index=df.index)
    filtered = df.loc[modes == evaluation_mode].copy()
    return pd.DataFrame(filtered)


def _parse_expected_sources(value: object) -> list[str]:
    return [item.strip().lower() for item in str(value or "").split(";") if item.strip()]


def _safe_loader_call(loader) -> pd.DataFrame:
    if not callable(loader):
        return pd.DataFrame()
    try:
        result = loader()
        return result if isinstance(result, pd.DataFrame) else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


def _source_loader_map() -> dict[str, object]:
    if dl is None:
        return {}
    return {
        "publications": getattr(dl, "load_publications", None),
        "bertopic_topics": getattr(dl, "load_bertopic_topics", None),
        "convocatorias": getattr(dl, "load_convocatorias", None),
        "convocatorias_matching_institucional": getattr(dl, "load_matching_institucional", None),
        "perfiles_institucionales": getattr(dl, "load_perfiles_institucionales", None),
        "researchers": getattr(dl, "load_orcid_researchers", None),
        "capital_humano": getattr(dl, "load_capital_humano", None),
        "patents": getattr(dl, "load_patents", None),
        "transferencia": _load_portafolio_seed,
        "paper_embeddings": ss.search if _normalize_mode(PUBLICATION_RAG) == PUBLICATION_RAG else None,
    }


@lru_cache(maxsize=1)
def _structured_source_inventory() -> dict[str, dict[str, object]]:
    inventory: dict[str, dict[str, object]] = {}
    for source_name, loader in _source_loader_map().items():
        if source_name == "paper_embeddings":
            available = bool(ss.is_available())
            inventory[source_name] = {
                "available": available,
                "rows": "semantic_index" if available else 0,
                "detail": "semantic_search.is_available",
            }
            continue

        df = _safe_loader_call(loader)
        inventory[source_name] = {
            "available": not df.empty,
            "rows": int(len(df)) if not df.empty else 0,
            "detail": "data_loader" if callable(loader) else "missing_loader",
        }
    return inventory


def _structured_metrics(expected_sources_raw: object, expected_focus: str) -> dict[str, object]:
    expected_sources = _parse_expected_sources(expected_sources_raw)
    inventory = _structured_source_inventory()
    available_sources: list[str] = []
    missing_sources: list[str] = []
    source_rows_summary: list[str] = []

    for source_name in expected_sources:
        item = inventory.get(source_name, {"available": False, "rows": 0, "detail": "unmapped"})
        rows = item.get("rows", 0)
        if item.get("available"):
            available_sources.append(source_name)
        else:
            missing_sources.append(source_name)
        source_rows_summary.append(f"{source_name}:{rows}")

    expected_count = len(expected_sources)
    available_count = len(available_sources)
    availability_ratio = round(available_count / expected_count, 4) if expected_count else ""

    if expected_count >= 3:
        synthesis_type = "multi_source_synthesis"
    elif expected_count == 2:
        synthesis_type = "cross_source_synthesis"
    elif expected_count == 1:
        synthesis_type = "single_source_summary"
    else:
        synthesis_type = ""

    actionability_expected = str(expected_focus or "").strip().lower() in {
        "financiamiento_y_matching",
        "convocatorias_matching",
        "resumen_ejecutivo",
        "transferencia",
    }

    return {
        "structured_eval_applicable": bool(expected_count),
        "structured_expected_source_count": expected_count,
        "structured_available_source_count": available_count,
        "structured_available_source_ratio": availability_ratio,
        "structured_available_sources": ";".join(available_sources),
        "structured_missing_sources": ";".join(missing_sources),
        "structured_source_rows": ";".join(source_rows_summary),
        "structured_synthesis_type": synthesis_type,
        "structured_actionability_expected": actionability_expected,
    }


def run_batch(input_csv: Path, output_csv: Path, top_k: int, run_label: str, evaluation_mode: str) -> Path:
    df = pd.read_csv(input_csv).fillna("")
    required = {"query_id", "query"}
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"Input missing required columns: {missing}")
    df = _filter_rows_by_mode(df, evaluation_mode)

    rows: list[dict] = []
    started_at = dt.datetime.now().isoformat(timespec="seconds")

    for _, r in df.iterrows():
        query_id = str(r.get("query_id", "")).strip()
        query = str(r.get("query", "")).strip()
        row_mode = _normalize_mode(r.get("evaluation_mode", ""))
        retrieval_applicable = row_mode == PUBLICATION_RAG
        if not query_id or not query:
            continue

        elapsed_ms = ""
        n_results = ""
        n_with_abstract = ""
        top1_score = ""
        avg_score = ""
        keyword_hits = ""
        keyword_hits_list = ""
        titles = ""
        abstracts = ""
        structured_metrics = {
            "structured_eval_applicable": False,
            "structured_expected_source_count": "",
            "structured_available_source_count": "",
            "structured_available_source_ratio": "",
            "structured_available_sources": "",
            "structured_missing_sources": "",
            "structured_source_rows": "",
            "structured_synthesis_type": "",
            "structured_actionability_expected": "",
        }

        if retrieval_applicable:
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
            top1_score = round(float(score_numeric[0]), 4) if n_results and score_numeric else 0.0
            avg_score = round(_safe_float_mean(pd.Series(score_numeric, dtype=float)), 4)
        else:
            structured_metrics = _structured_metrics(
                expected_sources_raw=r.get("expected_data_sources", ""),
                expected_focus=str(r.get("expected_focus", "")),
            )

        rows.append({
            "run_label": run_label,
            "run_started_at": started_at,
            "query_id": query_id,
            "query": query,
            "evaluation_mode": row_mode,
            "retrieval_eval_applicable": retrieval_applicable,
            "expected_focus": r.get("expected_focus", ""),
            "expected_data_sources": r.get("expected_data_sources", ""),
            "must_include_keywords": r.get("must_include_keywords", ""),
            "retrieval_top_k": top_k,
            "retrieval_ms": elapsed_ms,
            "n_results": n_results,
            "n_with_abstract": n_with_abstract,
            "top1_score": top1_score,
            "avg_score": avg_score,
            "keyword_hits": keyword_hits,
            "keyword_hits_list": keyword_hits_list,
            "top_titles": titles,
            "top_abstract_snippets": abstracts,
            "structured_eval_applicable": structured_metrics["structured_eval_applicable"],
            "structured_expected_source_count": structured_metrics["structured_expected_source_count"],
            "structured_available_source_count": structured_metrics["structured_available_source_count"],
            "structured_available_source_ratio": structured_metrics["structured_available_source_ratio"],
            "structured_available_sources": structured_metrics["structured_available_sources"],
            "structured_missing_sources": structured_metrics["structured_missing_sources"],
            "structured_source_rows": structured_metrics["structured_source_rows"],
            "structured_synthesis_type": structured_metrics["structured_synthesis_type"],
            "structured_actionability_expected": structured_metrics["structured_actionability_expected"],
            "score_context_relevance": r.get("score_context_relevance", ""),
            "score_answer_quality": r.get("score_answer_quality", ""),
            "hallucination_flag": r.get("hallucination_flag", ""),
            "score_structured_source_grounding": r.get("score_structured_source_grounding", ""),
            "score_structured_synthesis": r.get("score_structured_synthesis", ""),
            "score_structured_actionability": r.get("score_structured_actionability", ""),
            "structured_review_notes": r.get("structured_review_notes", ""),
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
        "evaluation_mode",
        "retrieval_eval_applicable",
        "structured_eval_applicable",
        "structured_expected_source_count",
        "structured_available_source_count",
        "structured_available_source_ratio",
        "n_results",
        "n_with_abstract",
        "top1_score",
        "avg_score",
        "keyword_hits",
        "retrieval_ms",
    ]
    prev = prev[[c for c in merge_cols if c in prev.columns]].rename(columns={
        "evaluation_mode": "prev_evaluation_mode",
        "retrieval_eval_applicable": "prev_retrieval_eval_applicable",
        "structured_eval_applicable": "prev_structured_eval_applicable",
        "structured_expected_source_count": "prev_structured_expected_source_count",
        "structured_available_source_count": "prev_structured_available_source_count",
        "structured_available_source_ratio": "prev_structured_available_source_ratio",
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
    merged["delta_structured_expected_source_count"] = delta("structured_expected_source_count", "prev_structured_expected_source_count")
    merged["delta_structured_available_source_count"] = delta("structured_available_source_count", "prev_structured_available_source_count")
    merged["delta_structured_available_source_ratio"] = delta("structured_available_source_ratio", "prev_structured_available_source_ratio")

    compare_out_csv.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(compare_out_csv, index=False)
    return compare_out_csv


def main() -> int:
    parser = argparse.ArgumentParser(description="Batch evaluator for Asistente I+D retrieval")
    parser.add_argument("--input", default=str(DEFAULT_INPUT), help="Input CSV with prompts")
    parser.add_argument("--output", default="", help="Output CSV path")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--run-label", default=f"run_{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}")
    parser.add_argument(
        "--evaluation-mode",
        choices=["all", PUBLICATION_RAG, STRUCTURED_OR_HYBRID],
        default="all",
        help="Filter prompts by evaluation mode",
    )
    parser.add_argument("--compare-with", default="", help="Previous run CSV to compare against")
    parser.add_argument("--compare-output", default="", help="Comparison output CSV path")
    args = parser.parse_args()

    input_csv = Path(args.input)
    if args.output:
        output_csv = Path(args.output)
    else:
        output_csv = DEFAULT_OUT_DIR / f"assistant_eval_run_{dt.datetime.now().strftime('%Y-%m-%d_%H%M%S')}.csv"

    out_path = run_batch(
        input_csv=input_csv,
        output_csv=output_csv,
        top_k=args.top_k,
        run_label=args.run_label,
        evaluation_mode=args.evaluation_mode,
    )
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
