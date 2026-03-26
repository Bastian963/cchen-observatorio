"""CLI regression tests for Scripts/assistant_eval_batch.py."""

import sys
from pathlib import Path

# Make Scripts/ importable
_SCRIPTS = Path(__file__).resolve().parents[1] / "Scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))


import assistant_eval_batch as mod


def test_main_accepts_mode_alias(monkeypatch, tmp_path):
    captured = {}

    def _fake_run_batch(input_csv, output_csv, top_k, run_label, evaluation_mode):
        captured["evaluation_mode"] = evaluation_mode
        out = tmp_path / "out.csv"
        out.write_text("query_id,query\nQ01,test\n", encoding="utf-8")
        return out

    monkeypatch.setattr(mod, "run_batch", _fake_run_batch)

    old_argv = sys.argv[:]
    try:
        sys.argv = [
            "assistant_eval_batch.py",
            "--input",
            str(tmp_path / "in.csv"),
            "--output",
            str(tmp_path / "out.csv"),
            "--mode",
            "publication_rag",
            "--run-label",
            "cli_alias_test",
        ]
        rc = mod.main()
    finally:
        sys.argv = old_argv

    assert rc == 0
    assert captured["evaluation_mode"] == mod.PUBLICATION_RAG
