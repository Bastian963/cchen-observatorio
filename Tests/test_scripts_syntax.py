"""Verifica sintaxis de todos los scripts ETL — CCHEN Observatory"""
import ast
import pytest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent.parent / "Scripts"

def _get_scripts():
    return sorted(SCRIPTS_DIR.glob("*.py"))

@pytest.mark.parametrize("script_path", _get_scripts(), ids=lambda p: p.name)
def test_script_syntax(script_path):
    """Cada script debe tener sintaxis Python válida."""
    try:
        ast.parse(script_path.read_text())
    except SyntaxError as e:
        pytest.fail(f"Error de sintaxis en {script_path.name}: {e}")
