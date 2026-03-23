#!/usr/bin/env python3
"""E2E mínimo del dashboard Streamlit usando streamlit.testing.v1.AppTest."""

from __future__ import annotations

import os
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Iterable


if sys.version_info < (3, 11):
    raise SystemExit(
        "check_dashboard_e2e.py requiere Python 3.11+ para ejecutar Dashboard/app.py. "
        "Usa `python3.11` o `uv run --python 3.11 --with-requirements requirements.txt "
        "python Scripts/check_dashboard_e2e.py`."
    )

from streamlit.testing.v1 import AppTest


REPO_ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_DIR = REPO_ROOT / "Dashboard"
TEST_USERNAME = "qa.e2e"
TEST_PASSWORD = "observatorio-e2e"
DEFAULT_TIMEOUT = 120
SECTION_EXPECTATIONS: dict[str, tuple[str, ...]] = {
    "Panel de Indicadores": (
        "CCHEN — Observatorio Tecnológico I+D+i+Tt",
        "Panel consolidado de indicadores de Vigilancia Tecnológica",
    ),
    "Convocatorias y Matching": (
        "Convocatorias y Matching CCHEN",
        "Ranking por perfil / unidad",
    ),
    "Grafo de Citas": (
        "Grafo de Citas — Red de Impacto Científico CCHEN",
        "Red interactiva de citas CCHEN",
    ),
}


@contextmanager
def _working_directory(path: Path):
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


def _test_secrets() -> dict:
    return {
        "supabase": {
            "data_source": "local",
        },
        "internal_auth": {
            "enabled": True,
            "beta_badge": "Beta interna",
            "beta_title": "Observatorio Tecnológico CCHEN",
            "beta_message": "Acceso privado para revisión funcional y validación e2e.",
            "users": [
                {
                    "username": TEST_USERNAME,
                    "password": TEST_PASSWORD,
                    "name": "QA E2E",
                    "role": "qa",
                    "can_view_sensitive": True,
                }
            ],
        },
    }


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _values(elements: Iterable) -> list[str]:
    values: list[str] = []
    for element in elements:
        value = getattr(element, "value", "")
        if value is None:
            continue
        text = str(value).strip()
        if text:
            values.append(text)
    return values


def _collect_visible_text(app: AppTest) -> str:
    buckets = [
        _values(app.title),
        _values(app.header),
        _values(app.subheader),
        _values(app.caption),
        _values(app.text),
        _values(app.markdown),
        _values(app.info),
        _values(app.warning),
        _values(app.success),
        _values(app.error),
        _values(app.sidebar.caption),
        _values(app.sidebar.markdown),
        _values(app.sidebar.text),
    ]
    return "\n".join(item for bucket in buckets for item in bucket)


def _assert_no_exceptions(app: AppTest, context: str) -> None:
    if len(app.exception) == 0:
        return
    messages = [getattr(exc, "message", str(exc)) for exc in app.exception]
    details = " | ".join(messages)
    raise AssertionError(f"{context} produjo excepciones en la app: {details}")


def _bootstrap_app() -> AppTest:
    os.environ.setdefault("OBSERVATORIO_DATA_SOURCE", "local")
    dashboard_path = str(DASHBOARD_DIR)
    if dashboard_path not in sys.path:
        sys.path.insert(0, dashboard_path)
    app = AppTest.from_file("app.py", default_timeout=DEFAULT_TIMEOUT)
    app.secrets = _test_secrets()
    return app


def _assert_access_gate(app: AppTest) -> None:
    app.run()
    _assert_no_exceptions(app, "La muralla beta")
    labels = [widget.label for widget in app.text_input]
    _assert(labels == ["Usuario", "Clave"], f"Labels inesperados en login beta: {labels}")
    visible = _collect_visible_text(app)
    _assert("Acceso privado del observatorio" in visible, "No apareció la muralla beta esperada.")
    _assert("Ingreso beta" in visible, "No apareció el bloque de ingreso beta.")


def _login(app: AppTest) -> None:
    app.text_input[0].input(TEST_USERNAME)
    app.text_input[1].input(TEST_PASSWORD)
    app.button[0].click()
    app.run()
    _assert_no_exceptions(app, "El login beta")

    username = app.session_state["observatorio_internal_auth_username"]
    _assert(username == TEST_USERNAME, "La sesión interna no quedó autenticada tras el login.")
    _assert(len(app.sidebar.radio) == 1, "El sidebar no mostró el selector de secciones tras login.")


def _assert_section(app: AppTest, section_name: str, expected_markers: tuple[str, ...]) -> None:
    app.sidebar.radio[0].set_value(section_name)
    app.run()
    _assert_no_exceptions(app, f"La sección {section_name}")
    _assert(
        app.sidebar.radio[0].value == section_name,
        f"El sidebar no quedó posicionado en {section_name!r}.",
    )

    visible = _collect_visible_text(app)
    missing = [marker for marker in expected_markers if marker not in visible]
    _assert(
        not missing,
        f"La sección {section_name!r} no mostró marcadores esperados: {', '.join(missing)}",
    )


def main() -> int:
    print("[e2e] iniciando app test del dashboard...")
    with _working_directory(DASHBOARD_DIR):
        app = _bootstrap_app()
        print("[e2e] validando muralla beta...")
        _assert_access_gate(app)
        print("[e2e] validando login interno...")
        _login(app)

        for section_name, markers in SECTION_EXPECTATIONS.items():
            print(f"[e2e] validando seccion: {section_name}...")
            _assert_section(app, section_name, markers)

    print("[e2e] dashboard ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
