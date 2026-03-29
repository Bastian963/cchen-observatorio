#!/usr/bin/env python3
"""Smoke del dashboard en modo publico usando streamlit.testing.v1.AppTest."""

from __future__ import annotations

import os
import re
import sys
from contextlib import contextmanager
from pathlib import Path

if sys.version_info < (3, 11):
    raise SystemExit("check_dashboard_public_mode.py requiere Python 3.11+.")

from streamlit.testing.v1 import AppTest


REPO_ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_DIR = REPO_ROOT / "Dashboard"
EXPECTED_PUBLIC_SECTIONS = [
    "Plataforma Institucional",
    "Producción Científica",
    "Redes y Colaboración",
    "Vigilancia Tecnológica",
    "Financiamiento I+D",
    "Convocatorias y Matching",
    "Transferencia y Portafolio",
    "Asistente I+D",
    "Grafo de Citas",
]
DEFAULT_TIMEOUT = 120


@contextmanager
def _working_directory(path: Path):
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


@contextmanager
def _public_env():
    previous = os.environ.get("OBSERVATORIO_APP_MODE")
    os.environ["OBSERVATORIO_APP_MODE"] = "public"
    os.environ.setdefault("OBSERVATORIO_DATA_SOURCE", "local")
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop("OBSERVATORIO_APP_MODE", None)
        else:
            os.environ["OBSERVATORIO_APP_MODE"] = previous


def _test_secrets() -> dict:
    return {
        "supabase": {"data_source": "local"},
        "observatorio": {
            "app_mode": "public",
            "public_assistant_enabled": True,
        },
        "internal_auth": {
            "enabled": True,
            "beta_badge": "Beta interna",
            "beta_title": "Observatorio Tecnológico CCHEN",
            "beta_message": "No debería aparecer en modo público.",
            "users": [
                {
                    "username": "qa.public",
                    "password": "irrelevante",
                    "name": "QA Public",
                    "role": "qa",
                    "can_view_sensitive": True,
                }
            ],
        },
    }


def _collect_visible_text(app: AppTest) -> str:
    buckets = [
        app.title,
        app.header,
        app.subheader,
        app.caption,
        app.text,
        app.markdown,
        app.info,
        app.warning,
        app.success,
        app.error,
        app.sidebar.caption,
        app.sidebar.markdown,
        app.sidebar.text,
    ]
    values: list[str] = []
    for bucket in buckets:
        for element in bucket:
            value = getattr(element, "value", "")
            if value is None:
                continue
            text = str(value).strip()
            if text:
                values.append(text)
    return "\n".join(values)


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value)).strip().casefold()


def _contains(visible_text: str, marker: str) -> bool:
    return _normalize_text(marker) in _normalize_text(visible_text)


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _assert_no_exceptions(app: AppTest, context: str) -> None:
    if len(app.exception) == 0:
        return
    messages = [getattr(exc, "message", str(exc)) for exc in app.exception]
    raise AssertionError(f"{context} produjo excepciones: {' | '.join(messages)}")


def _bootstrap_app() -> AppTest:
    dashboard_path = str(DASHBOARD_DIR)
    if dashboard_path not in sys.path:
        sys.path.insert(0, dashboard_path)
    app = AppTest.from_file("app.py", default_timeout=DEFAULT_TIMEOUT)
    app.secrets = _test_secrets()
    return app


def main() -> None:
    with _public_env(), _working_directory(DASHBOARD_DIR):
        app = _bootstrap_app()
        app.run()
        _assert_no_exceptions(app, "La portada publica")

        visible = _collect_visible_text(app)
        _assert(
            not _contains(visible, "Acceso privado del observatorio"),
            "La muralla beta siguio apareciendo en modo publico.",
        )
        _assert(
            _contains(visible, "Portal público del observatorio 3 en 1"),
            "No apareció el mensaje esperado del portal público.",
        )
        _assert(len(app.sidebar.radio) == 1, "No apareció el selector de secciones en modo público.")
        options = list(app.sidebar.radio[0].options)
        _assert(
            options == EXPECTED_PUBLIC_SECTIONS,
            f"Secciones públicas inesperadas: {options}",
        )

        for section in EXPECTED_PUBLIC_SECTIONS:
            app.sidebar.radio[0].set_value(section)
            app.run()
            _assert_no_exceptions(app, f"La sección pública {section}")

        final_visible = _collect_visible_text(app)
        _assert(
            _contains(final_visible, "Asistente I+D Público") or _contains(final_visible, "Grafo de Citas"),
            "La navegación pública no dejó marcadores esperados.",
        )

    print("[dashboard-public] OK: el dashboard público carga sin muralla beta y limita las secciones visibles")


if __name__ == "__main__":
    main()
