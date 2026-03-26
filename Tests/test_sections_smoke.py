"""Smoke tests para Dashboard/sections/ — CCHEN Observatory"""
import sys
import ast
import types
import pytest
import pandas as pd
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


class _SessionState(dict):
    """Simple session_state replacement supporting dict and attribute access."""

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError as exc:
            raise AttributeError(key) from exc

    def __setattr__(self, key, value):
        self[key] = value


class _UIBlock:
    """Context manager used for chat_message, spinner, expander and columns."""

    def __init__(self):
        self.button_calls = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def button(self, *args, **kwargs):
        self.button_calls += 1
        return False

    def markdown(self, *args, **kwargs):
        return None


class _FakeStreamlit:
    def __init__(self):
        self.session_state = _SessionState()
        self.secrets = {}
        self.expander_calls = 0
        self.download_calls = 0

    def title(self, *args, **kwargs):
        return None

    def caption(self, *args, **kwargs):
        return None

    def divider(self, *args, **kwargs):
        return None

    def warning(self, *args, **kwargs):
        return None

    def info(self, *args, **kwargs):
        return None

    def code(self, *args, **kwargs):
        return None

    def markdown(self, *args, **kwargs):
        return None

    def button(self, *args, **kwargs):
        return False

    def login(self, *args, **kwargs):
        return None

    def stop(self):
        raise RuntimeError("st.stop should not be called in this test")

    def columns(self, spec):
        n = len(spec) if isinstance(spec, (list, tuple)) else int(spec)
        return [_UIBlock() for _ in range(n)]

    def chat_message(self, *args, **kwargs):
        return _UIBlock()

    def chat_input(self, *args, **kwargs):
        return "consulta de prueba"

    def spinner(self, *args, **kwargs):
        return _UIBlock()

    def write_stream(self, _iterable):
        # Simula stream vacío para validar guard `reply or ""`.
        return None

    def download_button(self, *args, **kwargs):
        self.download_calls += 1
        return None

    def expander(self, *args, **kwargs):
        self.expander_calls += 1
        return _UIBlock()

    def rerun(self):
        return None


def test_asistente_id_render_smoke_with_mocks(monkeypatch):
    """render() debe ejecutar sin crash con stream vacío y mostrar fuentes RAG."""
    mod = __import__("sections.asistente_id", fromlist=["render"])

    fake_st = _FakeStreamlit()
    monkeypatch.setattr(mod, "st", fake_st)

    monkeypatch.setattr(mod, "_access_context", lambda: {
        "auth_enabled": False,
        "can_view_sensitive": True,
        "auth_supported": False,
        "is_logged_in": True,
        "auth_mode": "none",
    })
    monkeypatch.setattr(mod, "_build_assistant_system_prompt", lambda ctx, patents_key="": ("SYSTEM", {}))
    monkeypatch.setattr(mod, "generate_pdf_report", lambda *args, **kwargs: b"%PDF-test")

    monkeypatch.setattr(mod, "_SEM_AVAILABLE", True)
    monkeypatch.setattr(
        mod,
        "_ss",
        types.SimpleNamespace(
            search=lambda *args, **kwargs: pd.DataFrame([
                {
                    "title": "Paper de prueba",
                    "year": 2025,
                    "score": 0.91,
                    "doi": "https://doi.org/10.0000/test",
                    "abstract": "Resumen corto",
                }
            ])
        ),
    )

    class _FakeGroq:
        def __init__(self, api_key):
            self.api_key = api_key
            self.chat = types.SimpleNamespace(
                completions=types.SimpleNamespace(create=self._create)
            )

        @staticmethod
        def _create(*args, **kwargs):
            if kwargs.get("stream"):
                chunk = types.SimpleNamespace(
                    choices=[types.SimpleNamespace(delta=types.SimpleNamespace(content=""))]
                )
                return [chunk]
            return types.SimpleNamespace(
                choices=[types.SimpleNamespace(message=types.SimpleNamespace(content="{}"))]
            )

    fake_groq_mod = types.ModuleType("groq")
    fake_groq_mod.Groq = _FakeGroq
    monkeypatch.setitem(sys.modules, "groq", fake_groq_mod)
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test")

    empty = pd.DataFrame()
    ctx = {
        "pub": empty,
        "pub_enr": empty,
        "auth": empty,
        "anid": empty,
        "ch": empty,
        "ch_ej": {},
        "ch_adv": {},
        "orcid": empty,
        "ror_registry": empty,
        "ror_pending_review": empty,
        "funding_plus": empty,
        "iaea_tc": empty,
        "matching_inst": empty,
        "entity_personas": empty,
        "entity_projects": empty,
        "entity_convocatorias": empty,
        "entity_links": empty,
        "acuerdos": empty,
        "convenios": empty,
        "patents": empty,
        "datacite": empty,
        "openaire": empty,
    }

    mod.render(ctx)

    assert "messages" in fake_st.session_state
    assert len(fake_st.session_state.messages) == 2
    assert fake_st.session_state.messages[0]["role"] == "user"
    assert fake_st.session_state.messages[1]["role"] == "assistant"
    assert fake_st.session_state.messages[1]["content"] == ""
    assert fake_st.expander_calls >= 1
    assert fake_st.download_calls == 1
