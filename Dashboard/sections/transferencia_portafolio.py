"""Section: Transferencia y Portafolio — CCHEN Observatorio"""
import os
from pathlib import Path
import sys

import pandas as pd
import plotly.express as px
import streamlit as st

from .shared import (
    BLUE, GREEN, AMBER, PURPLE,
    kpi, kpi_row, sec, make_csv,
    _load_portafolio_seed,
)

_ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS_DIR = _ROOT / "Scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))
try:
    import evidence_search as _evidence_search
except Exception:
    _evidence_search = None


@st.cache_data(show_spinner=False, ttl=900)
def _load_evidence_index() -> pd.DataFrame:
    configured_path = os.getenv("EVIDENCE_SEARCH_INDEX_FILE", "").strip()
    path = Path(configured_path) if configured_path else _ROOT / "Data" / "Semantic" / "evidence_index.csv"
    if not path.is_absolute():
        path = _ROOT / path
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path, low_memory=False, encoding="utf-8-sig").fillna("")
    except Exception:
        return pd.read_csv(path, low_memory=False).fillna("")


@st.cache_data(show_spinner=False, ttl=900)
def _load_evidence_topic_index() -> pd.DataFrame:
    path = _ROOT / "Docs" / "reports" / "evidence_topics" / "indice_fichas_evidencia.csv"
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path, low_memory=False, encoding="utf-8-sig").fillna("")
    except Exception:
        return pd.read_csv(path, low_memory=False).fillna("")


def _read_topic_brief(relative_path: str) -> str:
    path = (_ROOT / str(relative_path or "")).resolve()
    if _ROOT.resolve() not in path.parents and path != _ROOT.resolve():
        return ""
    if not path.exists() or not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def _fallback_evidence_search(df: pd.DataFrame, query: str, top_k: int = 20) -> pd.DataFrame:
    query = str(query or "").strip().lower()
    if df.empty or not query:
        return pd.DataFrame()
    tokens = {tok for tok in query.replace("/", " ").split() if len(tok) >= 3}
    if not tokens:
        return pd.DataFrame()
    searchable = [c for c in ["titulo", "resumen", "tema", "relacion_cchen", "uso_observatorio", "brecha"] if c in df.columns]
    tmp = df.copy()
    text = tmp[searchable].astype(str).agg(" ".join, axis=1).str.lower()
    tmp["score"] = text.map(lambda value: float(sum(tok in value for tok in tokens)))
    return tmp[tmp["score"] > 0].sort_values("score", ascending=False).head(top_k)


def _evidence_prompt(query: str) -> str:
    return f"""Actua como asistente de evidencia para gestion de investigacion e innovacion CCHEN.

Pregunta del usuario:
\"{query}\"

Usa solo la evidencia recuperada desde la base interna.
Para cada hallazgo, indica:
1. Fuente del dato.
2. Tipo de evidencia: publicacion, patente, proyecto, dataset/output, compuesto, convenio u oportunidad.
3. Relacion con CCHEN.
4. Posible uso para gestion de investigacion o transferencia.
5. Brechas o validaciones pendientes.
6. Nivel de confianza: alto, medio o bajo.

No afirmes que una tecnologia esta lista para transferirse.
No inventes evidencia.
Si la informacion no alcanza, dilo explicitamente."""


def _render_evidence_search_panel(is_public_app: bool) -> None:
    sec("Buscador de evidencia para gestión de investigación e innovación")
    if is_public_app:
        st.info("El buscador de evidencia integrado queda disponible solo en la superficie interna.")
        return

    evidence = _load_evidence_index()
    if evidence.empty:
        st.warning(
            "Aún no existe `Data/Semantic/evidence_index.csv`. "
            "Ejecuta `python Scripts/build_evidence_index.py` para construirlo."
        )
        return

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Registros de evidencia", f"{len(evidence):,}")
    c2.metric("Fuentes", f"{evidence['fuente'].nunique():,}" if "fuente" in evidence.columns else "0")
    c3.metric("Tipos", f"{evidence['tipo_evidencia'].nunique():,}" if "tipo_evidencia" in evidence.columns else "0")
    c4.metric("Con brecha", f"{int(evidence.get('brecha', pd.Series(dtype=str)).astype(str).str.len().gt(0).sum()):,}")

    chart_left, chart_right = st.columns(2)
    with chart_left:
        if "tipo_evidencia" in evidence.columns:
            type_counts = evidence["tipo_evidencia"].fillna("sin tipo").value_counts().reset_index()
            type_counts.columns = ["Tipo", "Registros"]
            fig_types = px.bar(
                type_counts.sort_values("Registros"),
                x="Registros",
                y="Tipo",
                orientation="h",
                text="Registros",
                color_discrete_sequence=[PURPLE],
                height=300,
            )
            fig_types.update_layout(showlegend=False, margin=dict(t=10, b=10))
            st.plotly_chart(fig_types, width="stretch")
    with chart_right:
        if "fuente" in evidence.columns:
            source_counts = evidence["fuente"].fillna("sin fuente").value_counts().head(12).reset_index()
            source_counts.columns = ["Fuente", "Registros"]
            fig_sources = px.bar(
                source_counts.sort_values("Registros"),
                x="Registros",
                y="Fuente",
                orientation="h",
                text="Registros",
                color_discrete_sequence=[GREEN],
                height=300,
            )
            fig_sources.update_layout(showlegend=False, margin=dict(t=10, b=10))
            st.plotly_chart(fig_sources, width="stretch")

    query = st.text_input(
        "Pregunta de evidencia",
        value="radiofarmacia con potencial de transferencia",
        key="transferencia_evidence_query",
        help="Busca sobre publicaciones, datasets, patentes, proyectos, convenios, compuestos y señales temáticas.",
    )
    f1, f2, f3 = st.columns([1, 1, 1])
    with f1:
        type_filter = st.multiselect(
            "Tipo de evidencia",
            sorted(evidence["tipo_evidencia"].dropna().astype(str).unique()) if "tipo_evidencia" in evidence.columns else [],
            default=[],
            key="transferencia_evidence_type_filter",
        )
    with f2:
        source_filter = st.multiselect(
            "Fuente",
            sorted(evidence["fuente"].dropna().astype(str).unique()) if "fuente" in evidence.columns else [],
            default=[],
            key="transferencia_evidence_source_filter",
        )
    with f3:
        top_k = st.slider("Resultados", min_value=5, max_value=30, value=12, step=1)

    if _evidence_search is not None and _evidence_search.is_available():
        results = _evidence_search.search(query, top_k=max(top_k * 3, 30))
    else:
        results = _fallback_evidence_search(evidence, query, top_k=max(top_k * 3, 30))

    if type_filter and not results.empty and "tipo_evidencia" in results.columns:
        results = results[results["tipo_evidencia"].isin(type_filter)]
    if source_filter and not results.empty and "fuente" in results.columns:
        results = results[results["fuente"].isin(source_filter)]
    results = results.head(top_k).copy()

    if results.empty:
        st.info("No hay resultados para la consulta y filtros actuales.")
    else:
        show_cols = [
            c for c in [
                "score", "tipo_evidencia", "fuente", "titulo", "fecha", "tema",
                "relacion_cchen", "uso_observatorio", "brecha", "nivel_confianza", "url",
            ] if c in results.columns
        ]
        st.dataframe(
            results[show_cols].rename(
                columns={
                    "score": "Score",
                    "tipo_evidencia": "Tipo",
                    "fuente": "Fuente",
                    "titulo": "Título",
                    "fecha": "Fecha",
                    "tema": "Tema",
                    "relacion_cchen": "Relación CCHEN",
                    "uso_observatorio": "Uso en gestión",
                    "brecha": "Brecha",
                    "nivel_confianza": "Confianza",
                    "url": "URL",
                }
            ),
            width="stretch",
            hide_index=True,
            height=360,
            column_config={"URL": st.column_config.LinkColumn("URL", display_text="abrir")},
        )
        st.download_button(
            "Exportar resultados de evidencia CSV",
            make_csv(results),
            "evidencia_busqueda_cchen.csv",
            "text/csv",
        )

    with st.expander("Prompt sugerido para síntesis con Groq/LLM", expanded=False):
        st.code(_evidence_prompt(query), language="text")


def _render_topic_briefs_panel(is_public_app: bool) -> None:
    sec("Fichas de evidencia por tema")
    if is_public_app:
        st.info("Las fichas de evidencia por tema quedan disponibles solo en la superficie interna.")
        return
    topic_index = _load_evidence_topic_index()
    if topic_index.empty:
        st.info(
            "Aún no hay fichas generadas. Ejecuta "
            "`python Scripts/generate_evidence_topic_briefs.py --top-k 12`."
        )
        return
    labels = topic_index["topic_title"].astype(str).tolist()
    selected = st.selectbox("Tema", labels, key="transferencia_topic_brief_select")
    row = topic_index[topic_index["topic_title"].astype(str).eq(selected)].iloc[0]
    brief = _read_topic_brief(str(row.get("brief_path", "")))
    c1, c2, c3 = st.columns(3)
    c1.metric("Registros ficha", f"{int(row.get('records', 0)):,}")
    c2.metric("Tipo top", str(row.get("top_type", "")) or "—")
    c3.metric("Fuente top", str(row.get("top_source", "")) or "—")
    if brief:
        with st.expander("Ver ficha Markdown", expanded=False):
            st.markdown(brief)
        st.download_button(
            "Descargar ficha Markdown",
            brief.encode("utf-8"),
            f"{row.get('topic_key', 'ficha_evidencia')}.md",
            "text/markdown",
        )
    else:
        st.warning("No se pudo abrir el archivo de ficha seleccionado.")


def render(ctx: dict) -> None:
    """Render the Transferencia y Portafolio section."""
    anid        = ctx.get("anid", pd.DataFrame())
    pub_enr     = ctx.get("pub_enr", pd.DataFrame())
    funding_plus = ctx.get("funding_plus", pd.DataFrame())
    patents     = ctx.get("patents", pd.DataFrame())
    acuerdos    = ctx.get("acuerdos", pd.DataFrame())
    convenios   = ctx.get("convenios", pd.DataFrame())
    orcid       = ctx.get("orcid", pd.DataFrame())
    datacite    = ctx.get("datacite", pd.DataFrame())
    openaire    = ctx.get("openaire", pd.DataFrame())

    st.title("Transferencia y Portafolio Tecnológico")
    st.caption(
        "Portafolio semilla construido desde señales observables del observatorio. "
        "No reemplaza la validación técnica, pero ordena dónde conviene profundizar primero."
    )
    st.divider()

    _portfolio = _load_portafolio_seed()
    _innovation_projects = (
        anid["instrumento_norm"].astype(str).str.contains("Idea|Tecnolog|VIU|Fonis", case=False, na=False).sum()
        if "instrumento_norm" in anid.columns else 0
    )
    _top_areas_transfer = []
    if "areas" in pub_enr.columns:
        _area_counts_transfer = {}
        for _value in pub_enr["areas"].dropna():
            for _area in str(_value).split(";"):
                _area = _area.strip()
                if _area:
                    _area_counts_transfer[_area] = _area_counts_transfer.get(_area, 0) + 1
        _top_areas_transfer = sorted(_area_counts_transfer.items(), key=lambda x: -x[1])[:6]

    kpi_row(
        kpi("Activos semilla", f"{len(_portfolio):,}", "capacidades a validar"),
        kpi("Proyectos de innovación", f"{int(_innovation_projects):,}", "ANID tipo IDeA, VIU, Fonis o afines"),
        kpi("Fondos complementarios", f"{len(funding_plus):,}", "CORFO, IAEA u otras fuentes"),
        kpi("Patentes cargadas", f"{len(patents):,}", "requiere fortalecimiento si sigue en cero"),
    )

    st.markdown(
        "<div class='alert-amarillo'><b>Estado del módulo:</b> el portafolio se deja como semilla analítica. "
        "Sirve para ordenar activos y conversaciones de transferencia, pero cada fila debe validarse con responsables técnicos, "
        "TRL y situación de propiedad intelectual.</div>",
        unsafe_allow_html=True,
    )

    _render_evidence_search_panel(bool(ctx.get("is_public_app", False)))
    _render_topic_briefs_panel(bool(ctx.get("is_public_app", False)))

    sec("Portafolio tecnológico semilla")
    if _portfolio.empty:
        st.info("Aún no existe `Data/Transferencia/portafolio_tecnologico_semilla.csv`.")
    else:
        st.dataframe(
            _portfolio.rename(columns={
                "activo_id": "ID",
                "nombre_activo": "Activo",
                "tipo_activo": "Tipo",
                "dominio_tecnologico": "Dominio",
                "descripcion_base": "Descripción base",
                "evidencia_observatorio": "Evidencia",
                "estado_portafolio": "Estado",
                "trl_estimado": "TRL estimado",
                "estado_validacion": "Validación",
                "unidad_referente": "Unidad referente",
                "potencial_transferencia": "Potencial de transferencia",
                "proximo_paso": "Próximo paso",
            }),
            width="stretch",
            hide_index=True,
            height=360,
        )
        st.download_button(
            "Exportar portafolio semilla CSV",
            make_csv(_portfolio),
            "portafolio_tecnologico_semilla.csv",
            "text/csv",
        )

    _pt1, _pt2 = st.columns(2)
    with _pt1:
        sec("Señales observables para transferencia")
        _signals = pd.DataFrame([
            {"Señal": "Proyectos de innovación / tecnologías", "Valor": int(_innovation_projects)},
            {"Señal": "Fondos complementarios registrados", "Valor": int(len(funding_plus))},
            {"Señal": "Acuerdos internacionales", "Valor": int(len(acuerdos))},
            {"Señal": "Convenios nacionales", "Valor": int(len(convenios))},
            {"Señal": "Perfiles ORCID cargados", "Valor": int(len(orcid))},
            {"Señal": "Patentes integradas", "Valor": int(len(patents))},
        ])
        fig_sig = px.bar(
            _signals.sort_values("Valor"),
            x="Valor",
            y="Señal",
            orientation="h",
            color_discrete_sequence=[BLUE],
            text="Valor",
            height=340,
        )
        fig_sig.update_layout(showlegend=False, margin=dict(t=10, b=10))
        st.plotly_chart(fig_sig, width="stretch")

    with _pt2:
        sec("Áreas científicas que alimentan el portafolio")
        if _top_areas_transfer:
            _area_df = pd.DataFrame(_top_areas_transfer, columns=["Área", "Papers"])
            fig_area = px.bar(
                _area_df.sort_values("Papers"),
                x="Papers",
                y="Área",
                orientation="h",
                color_discrete_sequence=[GREEN],
                text="Papers",
                height=340,
            )
            fig_area.update_layout(showlegend=False, margin=dict(t=10, b=10))
            st.plotly_chart(fig_area, width="stretch")
        else:
            st.info("No hay áreas enriquecidas disponibles para este resumen.")

    sec("Outputs DataCite asociados a CCHEN")
    st.caption(
        "Esta capa captura datasets y otros outputs con DOI registrados en DataCite "
        "y asociados al ROR institucional de CCHEN."
    )
    if datacite.empty:
        st.info(
            "No hay outputs DataCite cargados. Ejecuta `python3 Scripts/fetch_datacite_outputs.py` "
            "o usa `--raw-json` si trabajas desde una descarga local."
        )
    else:
        _dc = datacite.copy()
        for _col in ["publication_year", "cchen_affiliated_creators", "citation_count", "download_count", "view_count"]:
            if _col in _dc.columns:
                _dc[_col] = pd.to_numeric(_dc[_col], errors="coerce")
        _dc_direct = _dc[_dc["cchen_affiliated_creators"].fillna(0) > 0] if "cchen_affiliated_creators" in _dc.columns else _dc
        _dc_types = _dc["resource_type_general"].fillna("Sin tipo").value_counts().reset_index()
        _dc_types.columns = ["Tipo", "N"]

        kpi_row(
            kpi("Outputs DataCite", f"{len(_dc):,}", "registros vinculados al ROR CCHEN"),
            kpi("Datasets",
                f"{int((_dc['resource_type_general'] == 'Dataset').sum()):,}" if "resource_type_general" in _dc.columns else "0",
                "outputs de datos"),
            kpi("Con creador CCHEN explícito", f"{len(_dc_direct):,}", "afiliación ROR visible en creators"),
            kpi("Repositorios/publishers",
                f"{_dc['publisher'].nunique():,}" if "publisher" in _dc.columns else "0",
                "ej. Zenodo, figshare"),
        )

        _dc1, _dc2 = st.columns([1, 1.3])
        with _dc1:
            fig_dc = px.bar(
                _dc_types.sort_values("N"),
                x="N",
                y="Tipo",
                orientation="h",
                color_discrete_sequence=[PURPLE],
                text="N",
                height=260,
            )
            fig_dc.update_layout(showlegend=False, margin=dict(t=10, b=10))
            st.plotly_chart(fig_dc, width="stretch")
        with _dc2:
            _dc_show = _dc[[
                "publication_year", "resource_type_general", "publisher",
                "title", "doi", "cchen_affiliated_creators",
            ]].rename(columns={
                "publication_year": "Año",
                "resource_type_general": "Tipo",
                "publisher": "Repositorio",
                "title": "Título",
                "doi": "DOI",
                "cchen_affiliated_creators": "Creadores CCHEN",
            }).sort_values(["Año", "Tipo"], ascending=[False, True])
            st.dataframe(
                _dc_show,
                width="stretch",
                hide_index=True,
                height=280,
                column_config={"DOI": st.column_config.LinkColumn("DOI", display_text="abrir")},
            )

        st.download_button(
            "Exportar outputs DataCite CSV",
            make_csv(_dc),
            "cchen_datacite_outputs.csv",
            "text/csv",
        )

    sec("OpenAIRE Graph asociado a investigadores CCHEN")
    st.caption(
        "Esta capa usa OpenAIRE Graph para observar outputs conectados a investigadores con ORCID "
        "registrado en CCHEN y distinguir si el vínculo con CCHEN aparece por organización o solo por autor."
    )
    if openaire.empty:
        st.info(
            "No hay outputs OpenAIRE cargados. Ejecuta `python3 Scripts/fetch_openaire_outputs.py` "
            "cuando quieras poblar esta capa."
        )
    else:
        _oa = openaire.copy()
        if "matched_cchen_researchers_count" in _oa.columns:
            _oa["matched_cchen_researchers_count"] = pd.to_numeric(
                _oa["matched_cchen_researchers_count"], errors="coerce"
            ).fillna(0).astype(int)
        _oa_types = _oa["type"].fillna("Sin tipo").value_counts().reset_index()
        _oa_types.columns = ["Tipo", "N"]
        _oa_scope = _oa["match_scope"].fillna("sin clasificar").value_counts().reset_index()
        _oa_scope.columns = ["Vínculo", "N"]
        _oa_org_linked = (
            _oa[_oa["match_scope"].isin(["cchen_ror_org", "cchen_name_org"])]
            if "match_scope" in _oa.columns
            else _oa.iloc[0:0]
        )

        kpi_row(
            kpi("Outputs OpenAIRE", f"{len(_oa):,}", "registros agregados por output"),
            kpi("Publicaciones",
                f"{int((_oa['type'] == 'publication').sum()):,}" if "type" in _oa.columns else "0",
                "según clasificación OpenAIRE"),
            kpi("Con señal institucional CCHEN", f"{len(_oa_org_linked):,}", "organización explícita o nombre de CCHEN"),
            kpi("Investigadores CCHEN vinculados",
                f"{int(_oa['matched_cchen_researchers_count'].sum()):,}" if "matched_cchen_researchers_count" in _oa.columns else "0",
                "hits acumulados por ORCID"),
        )

        _oa1, _oa2 = st.columns([1, 1])
        with _oa1:
            fig_oa_type = px.bar(
                _oa_types.sort_values("N"),
                x="N",
                y="Tipo",
                orientation="h",
                color_discrete_sequence=[BLUE],
                text="N",
                height=260,
            )
            fig_oa_type.update_layout(showlegend=False, margin=dict(t=10, b=10))
            st.plotly_chart(fig_oa_type, width="stretch")
        with _oa2:
            fig_oa_scope = px.bar(
                _oa_scope.sort_values("N"),
                x="N",
                y="Vínculo",
                orientation="h",
                color_discrete_sequence=[AMBER],
                text="N",
                height=260,
            )
            fig_oa_scope.update_layout(showlegend=False, margin=dict(t=10, b=10))
            st.plotly_chart(fig_oa_scope, width="stretch")

        _oa_show = _oa[[
            c for c in [
                "publication_date", "type", "match_scope", "main_title", "publisher",
                "matched_researchers", "matched_cchen_researchers_count",
            ] if c in _oa.columns
        ]].rename(columns={
            "publication_date": "Fecha",
            "type": "Tipo",
            "match_scope": "Vínculo",
            "main_title": "Título",
            "publisher": "Publisher",
            "matched_researchers": "Investigadores CCHEN",
            "matched_cchen_researchers_count": "N investigadores",
        }).sort_values(["Fecha", "N investigadores"], ascending=[False, False])
        st.dataframe(
            _oa_show.head(40),
            width="stretch",
            hide_index=True,
            height=300,
        )

        st.download_button(
            "Exportar outputs OpenAIRE CSV",
            make_csv(_oa),
            "cchen_openaire_outputs.csv",
            "text/csv",
        )

    sec("Siguientes pasos recomendados")
    st.markdown(
        "1. Validar cada activo con investigadores, laboratorios y responsables de PI.\n"
        "2. Agregar `TRL`, equipamiento asociado, estado de madurez y contraparte interna responsable.\n"
        "3. Vincular cada activo con publicaciones, proyectos ANID, estudiantes y convenios relevantes.\n"
        "4. Incorporar patentes, secretos industriales o resultados protegibles cuando exista inventario formal."
    )
