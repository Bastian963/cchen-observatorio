"""Unit tests for pure functions in the eval pipeline.

Covers:
- _normalize_kw (Scripts/assistant_eval_batch.py)
- _keyword_hits (Scripts/assistant_eval_batch.py)
- _count_citation_tags (Scripts/assistant_eval_structured_responses.py)
- _delta_str (Scripts/compare_eval_runs.py)

All functions are free of I/O and external dependencies — no mocks needed.
"""

import sys
from pathlib import Path

# Make Scripts/ importable
_SCRIPTS = Path(__file__).resolve().parents[1] / "Scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import importlib
import types


# ── Lazy-import helpers (avoid executing module-level code in the scripts) ─────

def _get_normalize_kw():
    mod = importlib.import_module("assistant_eval_batch")
    return mod._normalize_kw


def _get_keyword_hits():
    mod = importlib.import_module("assistant_eval_batch")
    return mod._keyword_hits


def _get_count_citation_tags():
    mod = importlib.import_module("assistant_eval_structured_responses")
    return mod._count_citation_tags


def _get_delta_str():
    mod = importlib.import_module("compare_eval_runs")
    return mod._delta_str


# ─────────────────────────────────────────────────────────────────────────────
# _normalize_kw
# ─────────────────────────────────────────────────────────────────────────────

class TestNormalizeKw:
    def test_strip_accent_acute(self):
        f = _get_normalize_kw()
        assert f("dosimetría") == "dosimetria"

    def test_strip_accent_tilde(self):
        f = _get_normalize_kw()
        assert f("colaboración") == "colaboracion"

    def test_lowercase(self):
        f = _get_normalize_kw()
        assert f("CCHEN") == "cchen"

    def test_ascii_passthrough(self):
        f = _get_normalize_kw()
        assert f("nuclear") == "nuclear"

    def test_empty_string(self):
        f = _get_normalize_kw()
        assert f("") == ""

    def test_mixed(self):
        f = _get_normalize_kw()
        assert f("Física Nuclear") == "fisica nuclear"


# ─────────────────────────────────────────────────────────────────────────────
# _keyword_hits
# ─────────────────────────────────────────────────────────────────────────────

class TestKeywordHits:
    def test_exact_match(self):
        f = _get_keyword_hits()
        count, hits = f("nuclear", "La fisica nuclear es clave")
        assert count == 1
        assert "nuclear" in hits

    def test_unicode_match(self):
        f = _get_keyword_hits()
        # keyword without accent, corpus with accent
        count, hits = f("dosimetria", "El valor de dosimetría es alto")
        assert count == 1
        assert "dosimetria" in hits

    def test_unicode_match_reversed(self):
        f = _get_keyword_hits()
        # keyword with accent, corpus without
        count, hits = f("dosimetría", "El valor de dosimetria es alto")
        assert count == 1

    def test_multiple_keywords_partial_hit(self):
        f = _get_keyword_hits()
        count, hits = f("nuclear;plasma;ciclotrón", "El reactor nuclear es seguro")
        assert count == 1
        assert "nuclear" in hits

    def test_multiple_keywords_all_hit(self):
        f = _get_keyword_hits()
        count, hits = f("nuclear;reactor", "reactor nuclear de alta potencia")
        assert count == 2

    def test_no_hit(self):
        f = _get_keyword_hits()
        count, hits = f("plasma", "El reactor nuclear es seguro")
        assert count == 0
        assert hits == ""

    def test_empty_keywords(self):
        f = _get_keyword_hits()
        count, hits = f("", "El reactor nuclear es seguro")
        assert count == 0
        assert hits == ""

    def test_none_keywords(self):
        f = _get_keyword_hits()
        count, hits = f(None, "El reactor nuclear es seguro")
        assert count == 0

    def test_semicolon_separated(self):
        f = _get_keyword_hits()
        count, hits = f("reactor;nuclear;fuel", "nuclear fuel cycle in reactor")
        assert count == 3

    def test_whitespace_trimmed(self):
        f = _get_keyword_hits()
        count, hits = f("  nuclear ;  plasma  ", "fisica nuclear aplicada")
        assert count == 1
        assert "nuclear" in hits


# ─────────────────────────────────────────────────────────────────────────────
# _count_citation_tags
# ─────────────────────────────────────────────────────────────────────────────

class TestCountCitationTags:
    def test_zero_when_no_tags(self):
        f = _get_count_citation_tags()
        assert f("El total de publicaciones es 826.") == 0

    def test_single_tag(self):
        f = _get_count_citation_tags()
        assert f("826 publicaciones (fuente: OpenAlex) en total.") == 1

    def test_multiple_tags(self):
        f = _get_count_citation_tags()
        text = (
            "826 publicaciones (fuente: OpenAlex). "
            "24 proyectos ANID (fuente: ANID). "
            "48 perfiles (fuente: ORCID)."
        )
        assert f(text) == 3

    def test_case_insensitive(self):
        f = _get_count_citation_tags()
        assert f("dato (Fuente: OpenAlex) y otro (FUENTE: ANID)") == 2

    def test_empty_string(self):
        f = _get_count_citation_tags()
        assert f("") == 0

    def test_partial_tag_not_counted(self):
        f = _get_count_citation_tags()
        # no closing paren
        assert f("dato (fuente: OpenAlex sin cerrar") == 0

    def test_tag_with_spaces(self):
        f = _get_count_citation_tags()
        assert f("total (fuente:  registros internos CCHEN)") == 1


# ─────────────────────────────────────────────────────────────────────────────
# _delta_str
# ─────────────────────────────────────────────────────────────────────────────

class TestDeltaStr:
    def test_zero_delta(self):
        f = _get_delta_str()
        assert f(5, 5) == "±0"

    def test_positive_small(self):
        f = _get_delta_str()
        result = f(0, 3)
        assert result.startswith("+")

    def test_negative_small(self):
        f = _get_delta_str()
        result = f(3, 0)
        assert result.startswith("-") or result == "-3.00"

    def test_large_integer_formatted(self):
        f = _get_delta_str()
        result = f(100, 1200)
        assert result == "+1100"

    def test_nan_returns_dash(self):
        f = _get_delta_str()
        assert f(float("nan"), 5) == "\u2014"
        assert f(5, float("nan")) == "\u2014"

    def test_none_returns_dash(self):
        f = _get_delta_str()
        assert f(None, 5) == "—"

    def test_float_precision(self):
        f = _get_delta_str()
        result = f(0.0, 0.5)
        assert result == "+0.50"
