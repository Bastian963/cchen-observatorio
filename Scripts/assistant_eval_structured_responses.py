#!/usr/bin/env python3
"""Structured-response evaluation layer for Asistente I+D.

For each structured_or_hybrid query in the template CSV this script:
  1. Computes structural metrics (reused from assistant_eval_batch._structured_metrics).
  2. Builds the full assistant system prompt via _build_assistant_system_prompt().
  3. Calls the Groq API (no streaming) to obtain an actual assistant response.
  4. Records response text, latency, and a transparent heuristic source-mention count.

Output CSV columns:
  run_label, run_started_at, query_id, query, evaluation_mode, expected_focus,
  expected_data_sources,
  <all structured_* metrics>,
  assistant_response, context_trace, response_ms, heuristic_sources_mentioned,
  score_structured_source_grounding (empty — human review),
  score_structured_synthesis       (empty — human review),
  score_structured_actionability   (empty — human review),
  structured_review_notes          (empty — human review).

Usage:
  cd /Users/bastianayalainostroza/Dropbox/CCHEN
  python3 Scripts/assistant_eval_structured_responses.py [--input ...] [--output ...]

Environment variables required:
  GROQ_API_KEY  — Groq API key for LLM calls.

Optional env vars consumed by data_loader:
  SUPABASE_URL, SUPABASE_ANON_KEY (or SUPABASE_PUBLIC_ANON_KEY), SUPABASE_SERVICE_ROLE_KEY
  OBSERVATORIO_DATA_SOURCE  (auto | local | supabase_public)
"""

from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
import os
import sys
from pathlib import Path

import pandas as pd

# ── Path setup ──────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[1]          # CCHEN/
DASHBOARD_DIR = ROOT / "Dashboard"
SECTIONS_DIR = DASHBOARD_DIR / "sections"
SCRIPTS_DIR = ROOT / "Scripts"

for _p in (str(DASHBOARD_DIR), str(SECTIONS_DIR), str(SCRIPTS_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# ── Constants ────────────────────────────────────────────────────────────────
DEFAULT_INPUT = ROOT / "Docs" / "reports" / "assistant_eval_template.csv"
DEFAULT_OUT_DIR = ROOT / "Docs" / "reports"
STRUCTURED_OR_HYBRID = "structured_or_hybrid"
PUBLICATION_RAG = "publication_rag"


# ── Module loading helpers ───────────────────────────────────────────────────

def _load_module(module_name: str, file_path: Path):
    try:
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except Exception as exc:
        print(f"[WARN] Could not load module {module_name} from {file_path}: {exc}")
        return None


# ── Load dependency modules ──────────────────────────────────────────────────

_dl = _load_module("eval_data_loader", DASHBOARD_DIR / "data_loader.py")
_batch_module = _load_module("eval_batch", SCRIPTS_DIR / "assistant_eval_batch.py")

# Import _structured_metrics from assistant_eval_batch (reuse, do not copy)
_structured_metrics = getattr(_batch_module, "_structured_metrics", None)
_normalize_mode = getattr(_batch_module, "_normalize_mode", None)
_parse_expected_sources = getattr(_batch_module, "_parse_expected_sources", None)

if _structured_metrics is None:
    raise ImportError(
        "Could not import _structured_metrics from Scripts/assistant_eval_batch.py. "
        "Make sure the file exists and is importable."
    )

# ── Load _build_assistant_system_prompt from asistente_id ────────────────────
# asistente_id.py imports streamlit at module level; we need to stub it so the
# module can be imported in a headless / non-Streamlit context.

def _ensure_streamlit_stub() -> None:
    """Insert a minimal st stub into sys.modules if streamlit is not importable."""
    try:
        import streamlit  # noqa: F401 — real Streamlit available
        return
    except ImportError:
        pass

    import types
    _stub = types.ModuleType("streamlit")

    # Provide every attribute that asistente_id.py touches at import time or
    # inside _build_assistant_system_prompt (which must be st-free, but the
    # module-level import still runs).
    for _attr in (
        "title", "caption", "divider", "warning", "info", "button",
        "login", "stop", "chat_input", "chat_message", "columns",
        "markdown", "write_stream", "session_state", "rerun",
        "download_button", "code", "write",
    ):
        setattr(_stub, _attr, lambda *a, **kw: None)

    class _FakeSecrets(dict):
        def get(self, key, default=""):
            return default

    _stub.secrets = _FakeSecrets()
    sys.modules["streamlit"] = _stub


def _load_module_as_package_member(module_name: str, file_path: Path, package: str):
    """Load a module file while supplying a package context so relative imports work.

    The parent package and any already-loaded siblings must be registered in
    sys.modules *before* exec_module is called; otherwise `from .sibling import`
    raises "attempted relative import with no known parent package".
    """
    try:
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        module.__package__ = package
        # Register before exec so intra-package relative imports can resolve.
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module
    except Exception as exc:
        print(f"[WARN] Could not load {module_name} from {file_path}: {exc}")
        sys.modules.pop(module_name, None)
        return None


def _ensure_sections_package() -> None:
    """Register Dashboard/sections as a Python package with shared.py pre-loaded.

    This lets asistente_id.py's `from .shared import ...` resolve correctly when
    the file is loaded outside the normal Streamlit package context.
    """
    import types

    pkg_name = "sections"
    if pkg_name not in sys.modules:
        pkg = types.ModuleType(pkg_name)
        pkg.__path__ = [str(SECTIONS_DIR)]
        pkg.__package__ = pkg_name
        pkg.__file__ = str(SECTIONS_DIR / "__init__.py")
        sys.modules[pkg_name] = pkg

    shared_name = "sections.shared"
    if shared_name not in sys.modules:
        _load_module_as_package_member(shared_name, SECTIONS_DIR / "shared.py", package=pkg_name)


_ensure_streamlit_stub()
_ensure_sections_package()

_asistente_module = _load_module_as_package_member(
    "sections.asistente_id",
    SECTIONS_DIR / "asistente_id.py",
    package="sections",
)
_build_assistant_system_prompt = getattr(_asistente_module, "_build_assistant_system_prompt", None)

if _build_assistant_system_prompt is None:
    raise ImportError(
        "Could not import _build_assistant_system_prompt from "
        "Dashboard/sections/asistente_id.py. "
        "Make sure the _build_assistant_system_prompt refactor has been applied."
    )


# ── Data loading helpers ─────────────────────────────────────────────────────

def _safe_call(fn, default=None):
    """Call fn() with a safe fallback."""
    if default is None:
        default = pd.DataFrame()
    if not callable(fn):
        return default
    try:
        result = fn()
        if isinstance(result, pd.DataFrame):
            return result
        if result is None:
            return default
        return result
    except Exception as exc:
        print(f"[WARN] Loader {getattr(fn, '__name__', fn)} failed: {exc}")
        return default


def _safe_call_dict(fn):
    """Like _safe_call but returns {} on failure (for ch_ej / ch_adv)."""
    if not callable(fn):
        return {}
    try:
        result = fn()
        return result if result is not None else {}
    except Exception as exc:
        print(f"[WARN] Dict loader {getattr(fn, '__name__', fn)} failed: {exc}")
        return {}


def _build_ctx() -> dict:
    """Load all DataFrames required by _build_assistant_system_prompt."""
    if _dl is None:
        print("[WARN] data_loader module could not be loaded. ctx will be all empty.")
        return {}

    def _get(name):
        return getattr(_dl, name, None)

    ctx = {
        "pub":                  _safe_call(_get("load_publications")),
        "pub_enr":              _safe_call(_get("load_publications_enriched")),
        "auth":                 _safe_call(_get("load_authorships")),
        "anid":                 _safe_call(_get("load_anid")),
        "ch":                   _safe_call(_get("load_capital_humano")),
        "ch_ej":                _safe_call_dict(_get("load_ch_resumen_ejecutivo")),
        "ch_adv":               _safe_call_dict(_get("load_ch_analisis_avanzado")),
        "orcid":                _safe_call(_get("load_orcid_researchers")),
        "ror_registry":         _safe_call(_get("load_ror_registry")),
        "ror_pending_review":   _safe_call(_get("load_ror_pending_review")),
        "funding_plus":         _safe_call(_get("load_funding_complementario")),
        "iaea_tc":              _safe_call(_get("load_iaea_tc")),
        "matching_inst":        _safe_call(_get("load_matching_institucional")),
        "entity_personas":      _safe_call(_get("load_entity_registry_personas")),
        "entity_projects":      _safe_call(_get("load_entity_registry_proyectos")),
        "entity_convocatorias": _safe_call(_get("load_entity_registry_convocatorias")),
        "entity_links":         _safe_call(_get("load_entity_links")),
        "acuerdos":             _safe_call(_get("load_acuerdos_internacionales")),
        "convenios":            _safe_call(_get("load_convenios_nacionales")),
        "patents":              _safe_call(_get("load_patents")),
        "datacite":             _safe_call(_get("load_datacite_outputs")),
        "openaire":             _safe_call(_get("load_openaire_outputs")),
    }
    return ctx


# ── Heuristic source mention count ──────────────────────────────────────────

def _count_source_mentions(expected_sources_raw: str, response_text: str) -> int:
    """Count how many expected_data_sources names appear as substrings in the response.

    This is a transparent heuristic count — NOT a quality score.
    Each unique source name is counted at most once (present or not).
    """
    if not str(expected_sources_raw or "").strip():
        return 0
    response_lower = response_text.lower()
    sources = [s.strip().lower() for s in str(expected_sources_raw).split(";") if s.strip()]
    return sum(1 for s in sources if s in response_lower)


# ── Main batch runner ────────────────────────────────────────────────────────

def run_structured_responses(
    input_csv: Path,
    output_csv: Path,
    run_label: str,
    groq_model: str,
    max_tokens: int,
    api_key: str,
) -> Path:
    df = pd.read_csv(input_csv).fillna("")
    required = {"query_id", "query"}
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"Input CSV missing required columns: {missing}")

    # Filter to structured_or_hybrid only
    if "evaluation_mode" in df.columns:
        df = df[df["evaluation_mode"].map(
            lambda v: str(v or "").strip().lower()
        ) == STRUCTURED_OR_HYBRID].copy()
    # If evaluation_mode column is missing, treat all rows as structured
    df = df.reset_index(drop=True)

    if df.empty:
        print("[INFO] No structured_or_hybrid queries found in input CSV. Nothing to evaluate.")
        output_csv.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame().to_csv(output_csv, index=False)
        return output_csv

    print(f"[INFO] Loading data context...")
    ctx = _build_ctx()
    print(f"[INFO] ctx loaded: pub={len(ctx.get('pub', pd.DataFrame()))}, "
          f"anid={len(ctx.get('anid', pd.DataFrame()))}, "
          f"orcid={len(ctx.get('orcid', pd.DataFrame()))}")

    print(f"[INFO] Building system prompt...")
    patents_key = os.environ.get("PATENTSVIEW_API_KEY", "")
    try:
        system_prompt, context_trace = _build_assistant_system_prompt(ctx, patents_key=patents_key)
    except Exception as exc:
        print(f"[ERROR] _build_assistant_system_prompt failed: {exc}")
        raise

    context_trace_json = json.dumps(context_trace, ensure_ascii=False)
    print(f"[INFO] System prompt built ({len(system_prompt)} chars). Context trace: {context_trace}")

    from groq import Groq
    client = Groq(api_key=api_key)

    started_at = dt.datetime.now().isoformat(timespec="seconds")
    rows: list[dict] = []

    for idx, row in df.iterrows():
        query_id = str(row.get("query_id", "")).strip()
        query = str(row.get("query", "")).strip()
        if not query_id or not query:
            continue

        expected_sources_raw = str(row.get("expected_data_sources", ""))
        expected_focus = str(row.get("expected_focus", ""))

        print(f"[INFO] Evaluating {query_id}: {query[:60]}...")

        # Structural metrics (reused from assistant_eval_batch)
        struct_metrics = _structured_metrics(
            expected_sources_raw=expected_sources_raw,
            expected_focus=expected_focus,
        )

        # Groq API call
        t0 = dt.datetime.now()
        try:
            response = client.chat.completions.create(
                model=groq_model,
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query},
                ],
            )
            reply = response.choices[0].message.content
        except Exception as exc:
            print(f"[ERROR] Groq call failed for {query_id}: {exc}")
            reply = f"[ERROR] Groq call failed: {exc}"
        response_ms = int((dt.datetime.now() - t0).total_seconds() * 1000)

        heuristic_sources_mentioned = _count_source_mentions(expected_sources_raw, reply)

        rows.append({
            "run_label": run_label,
            "run_started_at": started_at,
            "query_id": query_id,
            "query": query,
            "evaluation_mode": STRUCTURED_OR_HYBRID,
            "expected_focus": expected_focus,
            "expected_data_sources": expected_sources_raw,
            # Structured metrics
            "structured_eval_applicable": struct_metrics["structured_eval_applicable"],
            "structured_expected_source_count": struct_metrics["structured_expected_source_count"],
            "structured_available_source_count": struct_metrics["structured_available_source_count"],
            "structured_available_source_ratio": struct_metrics["structured_available_source_ratio"],
            "structured_available_sources": struct_metrics["structured_available_sources"],
            "structured_missing_sources": struct_metrics["structured_missing_sources"],
            "structured_source_rows": struct_metrics["structured_source_rows"],
            "structured_synthesis_type": struct_metrics["structured_synthesis_type"],
            "structured_actionability_expected": struct_metrics["structured_actionability_expected"],
            # LLM response and metadata
            "assistant_response": reply,
            "context_trace": context_trace_json,
            "response_ms": response_ms,
            "heuristic_sources_mentioned": heuristic_sources_mentioned,
            # Human review columns (empty)
            "score_structured_source_grounding": "",
            "score_structured_synthesis": "",
            "score_structured_actionability": "",
            "structured_review_notes": "",
        })

        print(f"[OK] {query_id} — {response_ms}ms — sources_mentioned: {heuristic_sources_mentioned}/{len([s for s in expected_sources_raw.split(';') if s.strip()])}")

    out = pd.DataFrame(rows)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(output_csv, index=False)
    return output_csv


# ── CLI ──────────────────────────────────────────────────────────────────────

def main() -> int:
    _ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    parser = argparse.ArgumentParser(
        description="Structured-response evaluation layer for Asistente I+D"
    )
    parser.add_argument(
        "--input",
        default=str(DEFAULT_INPUT),
        help="Input CSV with evaluation queries (default: Docs/reports/assistant_eval_template.csv)",
    )
    parser.add_argument(
        "--output",
        default="",
        help="Output CSV path (default: auto-named in Docs/reports/)",
    )
    parser.add_argument(
        "--run-label",
        default=f"structured_responses_{_ts}",
        help="Label for this evaluation run",
    )
    parser.add_argument(
        "--groq-model",
        default="llama-3.3-70b-versatile",
        help="Groq model ID to use for assistant responses",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=1500,
        help="Max tokens for each LLM response",
    )
    args = parser.parse_args()

    api_key = os.environ.get("GROQ_API_KEY", "").strip()
    if not api_key:
        print("[ERROR] GROQ_API_KEY environment variable is not set.")
        return 1

    input_csv = Path(args.input)
    if not input_csv.exists():
        print(f"[ERROR] Input CSV not found: {input_csv}")
        return 1

    if args.output:
        output_csv = Path(args.output)
    else:
        output_csv = DEFAULT_OUT_DIR / f"assistant_eval_structured_responses_{_ts}.csv"

    print(f"[INFO] Input:       {input_csv}")
    print(f"[INFO] Output:      {output_csv}")
    print(f"[INFO] Run label:   {args.run_label}")
    print(f"[INFO] Groq model:  {args.groq_model}")
    print(f"[INFO] Max tokens:  {args.max_tokens}")

    out_path = run_structured_responses(
        input_csv=input_csv,
        output_csv=output_csv,
        run_label=args.run_label,
        groq_model=args.groq_model,
        max_tokens=args.max_tokens,
        api_key=api_key,
    )
    print(f"[OK] Results saved to: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
