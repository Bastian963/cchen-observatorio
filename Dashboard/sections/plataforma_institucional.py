"""Section: Plataforma Institucional — Observatorio CCHEN."""

from __future__ import annotations

import os
from typing import Any

import pandas as pd
import requests
import streamlit as st

from .shared import (
    AMBER,
    BLUE,
    GREEN,
    RED,
    _get_secret_block,
    asset_catalog_frame,
    filter_asset_catalog,
    kpi,
    kpi_row,
    render_asset_links_table,
    sec,
)


_DEFAULT_LINKS = {
    "dashboard_url": "http://localhost:8501",
    "dspace_ui_url": "http://localhost:4000",
    "dspace_api_url": "http://localhost:8080/server/api",
    "ckan_url": "http://localhost:5001",
    "ckan_api_url": "http://localhost:5001/api/3/action/status_show",
}


def _platform_links() -> dict[str, str]:
    secrets = _get_secret_block("platform")
    resolved: dict[str, str] = {}
    for key, default in _DEFAULT_LINKS.items():
        env_key = f"OBSERVATORIO_{key.upper()}"
        resolved[key] = str(os.getenv(env_key) or secrets.get(key) or default).strip()
    return resolved


@st.cache_data(show_spinner=False, ttl=30)
def _probe_service(name: str, url: str, expected_text: str | None = None) -> dict[str, str]:
    try:
        response = requests.get(url, timeout=3)
        body = response.text[:500]
        if response.ok and (expected_text is None or expected_text.lower() in body.lower()):
            return {
                "service": name,
                "status": "Operativo",
                "detail": f"HTTP {response.status_code}",
                "color": GREEN,
                "url": url,
            }
        return {
            "service": name,
            "status": "Degradado",
            "detail": f"HTTP {response.status_code}",
            "color": AMBER,
            "url": url,
        }
    except requests.RequestException as exc:
        return {
            "service": name,
            "status": "Sin respuesta",
            "detail": type(exc).__name__,
            "color": RED,
            "url": url,
        }


def _status_badge(label: str, color: str) -> str:
    return (
        f"<span style='display:inline-block;padding:0.18rem 0.55rem;border-radius:999px;"
        f"background:{color}15;border:1px solid {color}40;color:{color};"
        f"font-size:0.74rem;font-weight:700'>{label}</span>"
    )


def _link_card(title: str, body: str, url: str, badge: str, color: str) -> str:
    return f"""
    <a href="{url}" target="_blank" style="
        display:block;
        text-decoration:none;
        color:inherit;
        background:white;
        border:1px solid rgba(15,23,42,0.08);
        border-top:4px solid {color};
        border-radius:18px;
        padding:1.1rem 1.15rem;
        box-shadow:0 12px 30px rgba(15,23,42,0.06);
        min-height:220px;
    ">
        <div style="display:flex;justify-content:space-between;gap:0.8rem;align-items:flex-start">
            <div style="font-size:1.05rem;font-weight:800;color:#0F172A;line-height:1.2">{title}</div>
            {_status_badge(badge, color)}
        </div>
        <div style="margin-top:0.75rem;font-size:0.92rem;color:#334155;line-height:1.6">{body}</div>
        <div style="margin-top:1rem;font-size:0.8rem;color:#64748B">
            Entrada actual: <span style="color:{color};font-weight:700">{url}</span>
        </div>
    </a>
    """


def _service_rows(links: dict[str, str]) -> list[dict[str, str]]:
    rows = [
        {
            "service": "Observatorio Analítico",
            "status": "Sesión activa",
            "detail": "Dashboard Streamlit en ejecución",
            "color": GREEN,
            "url": links["dashboard_url"],
        },
        _probe_service("DSpace UI", links["dspace_ui_url"]),
        _probe_service("DSpace REST", links["dspace_api_url"], expected_text="_links"),
        _probe_service("CKAN UI", links["ckan_url"]),
        _probe_service("CKAN Action API", links["ckan_api_url"], expected_text="success"),
    ]
    return rows


def _service_table(rows: list[dict[str, str]]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Servicio": row["service"],
                "Estado": row["status"],
                "Detalle": row["detail"],
                "URL": row["url"],
            }
            for row in rows
        ]
    )


def _surface_matrix() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Superficie": "Repositorio Institucional DSpace",
                "Fuente de verdad": "Publicaciones, informes, policy briefs y memoria técnica",
                "Interfaz canónica": "REST API y OAI-PMH",
                "Regla operativa": "Conserva y publica objetos documentales institucionales",
            },
            {
                "Superficie": "Portal de Datos CKAN",
                "Fuente de verdad": "Datasets, series, recursos descargables y metadatos de distribución",
                "Interfaz canónica": "CKAN Action API",
                "Regla operativa": "Conserva y publica datos reutilizables",
            },
            {
                "Superficie": "Observatorio Analítico",
                "Fuente de verdad": "Indicadores derivados, análisis, vigilancia y narrativa ejecutiva",
                "Interfaz canónica": "Dashboard Streamlit y asistente",
                "Regla operativa": "Consume, relaciona y explica; no reemplaza al repositorio ni al portal",
            },
        ]
    )


def _metadata_matrix() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"Campo": "area_unidad", "Uso mínimo": "Unidad o centro responsable", "Aplica en": "DSpace, CKAN y dashboard"},
            {"Campo": "tema", "Uso mínimo": "Tema institucional o línea I+D", "Aplica en": "DSpace, CKAN y dashboard"},
            {"Campo": "anio", "Uso mínimo": "Año principal del activo", "Aplica en": "DSpace, CKAN y dashboard"},
            {"Campo": "responsables", "Uso mínimo": "Autoría, responsable técnico o unidad", "Aplica en": "DSpace, CKAN y dashboard"},
            {"Campo": "palabras_clave", "Uso mínimo": "Términos de descubrimiento", "Aplica en": "DSpace, CKAN y dashboard"},
            {"Campo": "visibilidad", "Uso mínimo": "Interno, mixto o público", "Aplica en": "DSpace, CKAN y dashboard"},
            {"Campo": "identificador", "Uso mínimo": "DOI, handle, slug o id estable", "Aplica en": "DSpace, CKAN y dashboard"},
            {"Campo": "vinculo_cruzado", "Uso mínimo": "URL a dataset, publicación o vista analítica relacionada", "Aplica en": "DSpace, CKAN y dashboard"},
        ]
    )


def _render_quick_links(links: dict[str, str]) -> None:
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(
            _link_card(
                "Observatorio Analítico",
                (
                    "Capa de inteligencia para gestión y contexto institucional. Aquí viven las "
                    "vistas ejecutivas, la vigilancia, el asistente y la narrativa analítica."
                ),
                links["dashboard_url"],
                "Interno / mixto",
                BLUE,
            ),
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            _link_card(
                "Repositorio Institucional DSpace",
                (
                    "Superficie documental para publicaciones, informes, policy briefs y memoria "
                    "técnica. Debe ser la referencia pública de los objetos académicos e institucionales."
                ),
                links["dspace_ui_url"],
                "Público documental",
                GREEN,
            ),
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            _link_card(
                "Portal de Datos CKAN",
                (
                    "Superficie de distribución para datasets, series, archivos reutilizables y APIs. "
                    "Aquí deben publicarse los recursos descargables y sus metadatos."
                ),
                links["ckan_url"],
                "Público datos",
                AMBER,
            ),
            unsafe_allow_html=True,
        )


def _safe_len(value: Any) -> int:
    try:
        return int(len(value))
    except Exception:
        return 0


def render(ctx: dict) -> None:
    """Render the institutional 3-in-1 home section."""
    pub = ctx.get("pub", pd.DataFrame())
    anid = ctx.get("anid", pd.DataFrame())
    datacite = ctx.get("datacite", pd.DataFrame())
    openaire = ctx.get("openaire", pd.DataFrame())
    patents = ctx.get("patents", pd.DataFrame())
    asset_catalog = asset_catalog_frame(ctx)

    links = _platform_links()
    service_rows = _service_rows(links)
    published_assets = filter_asset_catalog(
        asset_catalog,
        section_name="Plataforma Institucional",
        publication_status="published",
        require_public_url=True,
        limit=8,
    )
    editorial_queue = filter_asset_catalog(
        asset_catalog,
        section_name="Plataforma Institucional",
        publication_status="ready_for_publish",
        limit=8,
    )

    st.title("Plataforma Institucional CCHEN")
    st.markdown(
        """
        **Modelo operativo 3 en 1**: el observatorio deja de presentarse como un dashboard aislado y pasa
        a operar como una plataforma institucional de conocimiento con tres superficies coordinadas.
        """
    )
    st.info(
        "Regla operativa: DSpace conserva publicaciones y documentos; CKAN conserva datos publicables; "
        "el dashboard consume, relaciona y explica."
    )

    kpi_row(
        kpi("Publicaciones candidatas a repositorio", f"{_safe_len(pub):,}", "base analítica utilizable por DSpace"),
        kpi("Datasets / outputs detectados", f"{_safe_len(datacite) + _safe_len(openaire):,}", "activos reutilizables para CKAN"),
        kpi("Proyectos ANID trazables", f"{_safe_len(anid):,}", "insumo para vistas ejecutivas y catálogo"),
        kpi("Patentes / PI indexadas", f"{_safe_len(patents):,}", "capa de transferencia y portafolio"),
    )

    st.divider()
    sec("Entradas principales")
    _render_quick_links(links)

    st.divider()
    left, right = st.columns([1.1, 1], gap="large")

    with left:
        sec("Estado operativo del stack")
        st.dataframe(_service_table(service_rows), width="stretch", hide_index=True)
        st.caption(
            "Las URLs se configuran con variables `OBSERVATORIO_*` o con el bloque `[platform]` en "
            "`Dashboard/.streamlit/secrets.toml`."
        )

    with right:
        sec("Fuente de verdad por superficie")
        st.dataframe(_surface_matrix(), width="stretch", hide_index=True)

    st.divider()
    left, right = st.columns([1.15, 1], gap="large")
    with left:
        render_asset_links_table(
            published_assets,
            "Activos institucionales publicados",
            "Aún no hay activos publicados con URL pública para esta portada.",
        )
    with right:
        render_asset_links_table(
            editorial_queue,
            "Cola editorial inmediata",
            "No hay activos marcados como listos para publicar en esta ola.",
        )

    st.divider()
    left, right = st.columns([1, 1], gap="large")
    with left:
        sec("Metadatos mínimos comunes")
        st.dataframe(_metadata_matrix(), width="stretch", hide_index=True)
    with right:
        sec("Ruta editorial mínima")
        st.markdown(
            """
            1. Si el activo es un documento institucional o publicación final, su hogar canónico es `DSpace`.
            2. Si el activo es un dataset o recurso descargable, su hogar canónico es `CKAN`.
            3. Si el activo es un indicador derivado, comparación o narrativa ejecutiva, su hogar canónico es el `dashboard`.
            4. Cada activo relevante debe incluir un `vínculo cruzado` hacia la otra superficie cuando exista relación documental o analítica.
            5. El asistente y la búsqueda semántica deben descubrir las tres superficies, pero respetando su fuente de verdad.
            """
        )
        st.caption(
            "Documentos recomendados del repo: `README.md`, `ARCHITECTURE.md`, "
            "`Docs/matriz_publicacion_3_en_1.md` y `Docs/operations/runbook_plataforma_3_en_1.md`."
        )
