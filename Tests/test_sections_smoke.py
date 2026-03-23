"""Smoke tests para Dashboard/sections/ — CCHEN Observatory"""
import sys
import ast
import pytest
from pathlib import Path
from unittest import mock

# Mock streamlit y otras deps pesadas antes de importar
for mod_name in [
    "streamlit", "plotly", "plotly.express", "plotly.graph_objects",
    "matplotlib", "matplotlib.pyplot", "matplotlib.figure", "matplotlib.patches",
    "reportlab", "reportlab.lib", "reportlab.lib.pagesizes",
    "reportlab.platypus", "reportlab.lib.styles", "reportlab.lib.units",
    "reportlab.lib.colors", "groq", "sentence_transformers",
    "scipy", "scipy.stats", "sklearn", "sklearn.feature_extraction",
    "sklearn.feature_extraction.text", "sklearn.metrics.pairwise",
]:
    sys.modules[mod_name] = mock.MagicMock()

SECTIONS_DIR = Path(__file__).parent.parent / "Dashboard" / "sections"
sys.path.insert(0, str(SECTIONS_DIR.parent))

SECTION_MODULES = [
    "panel_indicadores",
    "produccion_cientifica",
    "redes_colaboracion",
    "vigilancia_tecnologica",
    "financiamiento_id",
    "convocatorias_matching",
    "transferencia_portafolio",
    "modelo_gobernanza",
    "formacion_capacidades",
    "asistente_id",
]

@pytest.mark.parametrize("module_name", SECTION_MODULES)
def test_section_syntax(module_name):
    """Cada archivo de sección debe tener sintaxis Python válida."""
    fpath = SECTIONS_DIR / f"{module_name}.py"
    assert fpath.exists(), f"{module_name}.py no encontrado"
    try:
        ast.parse(fpath.read_text())
    except SyntaxError as e:
        pytest.fail(f"Error de sintaxis en {module_name}.py: {e}")

@pytest.mark.parametrize("module_name", SECTION_MODULES)
def test_section_has_render(module_name):
    """Cada módulo de sección debe exportar una función render()."""
    mod = __import__(f"sections.{module_name}", fromlist=["render"])
    assert hasattr(mod, "render"), f"{module_name} no tiene función render()"
    assert callable(mod.render), f"{module_name}.render no es callable"

def test_shared_exports_constants():
    """sections/shared.py debe exportar las constantes de color principales."""
    from sections.shared import BLUE, RED, GREEN, AMBER, PURPLE, PALETTE
    assert BLUE.startswith("#")
    assert len(PALETTE) >= 5
