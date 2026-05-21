"""Section: Modelo y Gobernanza — CCHEN Observatorio"""
import pandas as pd
import plotly.express as px
import streamlit as st

from . import cris_rims_audit
from .shared import (
    AMBER, BLUE, GREEN, RED,
    kpi, kpi_row, sec, make_csv,
    _load_entity_model_tables,
    _build_entity_observed_counts,
)


_MATURITY_COLORS = {
    "Faltante": RED,
    "Inicial": AMBER,
    "Funcional": BLUE,
    "Robusto": GREEN,
}


def _render_cris_rims_audit_panel(ctx: dict) -> None:
    """Render the deterministic CRIS/RIMS benchmark audit."""
    if str(ctx.get("app_mode", "internal")).strip().lower() == "public":
        return

    source_registry = cris_rims_audit.load_optional_source_registry()
    audit = cris_rims_audit.build_cris_rims_audit(ctx, source_registry)
    maturity = audit["maturity"]
    gaps = audit["gaps"]
    interoperability = audit["interoperability"]
    backlog = audit["backlog"]
    agents = audit["agents"]
    benchmark = audit["benchmark"]
    summary = cris_rims_audit.audit_summary(maturity)

    sec("Auditoría CRIS/RIMS")
    st.caption(
        "Benchmark determinístico para comparar el observatorio con capacidades maduras de CRIS/RIMS. "
        "No usa LLM ni archivos externos en runtime; si faltan snapshots de datos, muestra brechas sin romper el dashboard."
    )
    if source_registry.empty:
        st.info(
            "No se encontró `Data/Gobernanza/data_sources_runtime.csv`; la auditoría usa solo el contexto cargado "
            "en esta sección y marca como faltante lo que no tenga evidencia local."
        )

    kpi_row(
        kpi("Score CRIS/RIMS", f"{summary['weighted_score']:.1f}/100", "ponderado por impacto"),
        kpi("Madurez promedio", f"{summary['average_maturity']:.2f}/3", "escala 0=faltante, 3=robusto"),
        kpi("Dimensiones robustas", f"{summary['robust_dimensions']:,}", "score igual a 3"),
        kpi("Dimensiones críticas", f"{summary['critical_dimensions']:,}", "score igual o menor a 1"),
    )

    tab_maturity, tab_gaps, tab_interop, tab_backlog, tab_agents = st.tabs(
        [
            "Madurez CRIS/RIMS",
            "Brechas críticas",
            "Interoperabilidad",
            "Backlog",
            "Agentes determinísticos",
        ]
    )

    with tab_maturity:
        left, right = st.columns([1, 1.25], gap="large")
        with left:
            fig = px.bar(
                maturity.sort_values("Puntaje ponderado"),
                x="Puntaje ponderado",
                y="Dimensión",
                orientation="h",
                text="Madurez 0-3",
                color="Estado",
                color_discrete_map=_MATURITY_COLORS,
                height=380,
            )
            fig.update_layout(showlegend=True, margin=dict(t=10, b=10, l=10, r=10))
            st.plotly_chart(fig, width="stretch")
        with right:
            st.dataframe(
                maturity.drop(columns=["dimension_key"], errors="ignore"),
                width="stretch",
                hide_index=True,
                height=380,
            )
        with st.expander("Benchmark usado como referencia", expanded=False):
            st.dataframe(benchmark, width="stretch", hide_index=True, height=320)

    with tab_gaps:
        priority_order = ["Critica", "Alta", "Media", "Deseable", "Futura"]
        gap_show = gaps.copy()
        if "Prioridad" in gap_show.columns:
            gap_show["_priority_order"] = gap_show["Prioridad"].map(
                {priority: index for index, priority in enumerate(priority_order)}
            ).fillna(99)
            gap_show = gap_show.sort_values(["_priority_order", "Estado CCHEN", "Feature"]).drop(
                columns=["_priority_order"]
            )
        st.dataframe(gap_show, width="stretch", hide_index=True, height=460)
        st.download_button(
            "Exportar brechas CRIS/RIMS CSV",
            make_csv(gap_show),
            "cris_rims_brechas_cchen.csv",
            "text/csv",
        )

    with tab_interop:
        left, right = st.columns([1.1, 1], gap="large")
        with left:
            st.dataframe(interoperability, width="stretch", hide_index=True, height=430)
        with right:
            detected = int((interoperability["Estado CCHEN"] == "Detectado").sum()) if not interoperability.empty else 0
            missing = int((interoperability["Estado CCHEN"] != "Detectado").sum()) if not interoperability.empty else 0
            fig_std = px.pie(
                pd.DataFrame(
                    [
                        {"Estado": "Detectado", "N": detected},
                        {"Estado": "No detectado", "N": missing},
                    ]
                ),
                names="Estado",
                values="N",
                color="Estado",
                color_discrete_map={"Detectado": GREEN, "No detectado": AMBER},
                height=280,
            )
            fig_std.update_layout(margin=dict(t=10, b=10, l=10, r=10))
            st.plotly_chart(fig_std, width="stretch")
            st.markdown(
                "<div class='alert-azul'><b>Canasta mínima recomendada:</b> ORCID + ROR + DOI/DataCite + "
                "Crossref + OpenAlex + REST/JSON versionado + OAI-PMH + schema.org.</div>",
                unsafe_allow_html=True,
            )

    with tab_backlog:
        st.dataframe(backlog, width="stretch", hide_index=True, height=460)
        st.download_button(
            "Exportar backlog CRIS/RIMS CSV",
            make_csv(backlog),
            "cris_rims_backlog_cchen.csv",
            "text/csv",
        )

    with tab_agents:
        st.markdown(
            "<div class='alert-amarillo'><b>Agentes determinísticos:</b> estos evaluadores no llaman a Groq, "
            "Claude ni servicios externos. Solo resumen reglas y evidencia local para orientar curaduría.</div>",
            unsafe_allow_html=True,
        )
        st.dataframe(agents, width="stretch", hide_index=True, height=360)
        st.download_button(
            "Exportar hallazgos de agentes CSV",
            make_csv(agents),
            "cris_rims_agentes_deterministicos.csv",
            "text/csv",
        )


def render(ctx: dict) -> None:
    """Render the Modelo y Gobernanza section."""
    pub              = ctx["pub"]
    ch               = ctx["ch"]
    auth             = ctx["auth"]
    entity_personas  = ctx["entity_personas"]
    entity_projects  = ctx["entity_projects"]
    entity_convocatorias = ctx["entity_convocatorias"]
    entity_links     = ctx["entity_links"]
    acuerdos         = ctx["acuerdos"]
    convenios        = ctx["convenios"]
    orcid            = ctx["orcid"]
    patents          = ctx["patents"]
    matching_inst    = ctx["matching_inst"]

    st.title("Modelo Unificado y Gobernanza de Datos")
    st.caption(
        "Ordena las entidades críticas del observatorio, sus relaciones y la prioridad de gobierno "
        "para que la plataforma pueda crecer sin perder trazabilidad."
    )
    st.divider()

    _entity_df, _rel_df = _load_entity_model_tables()
    _observed_counts = _build_entity_observed_counts(
        pub=pub,
        ch=ch,
        auth=auth,
        entity_personas=entity_personas,
        entity_projects=entity_projects,
        entity_convocatorias=entity_convocatorias,
        entity_links=entity_links,
        acuerdos=acuerdos,
        convenios=convenios,
        orcid=orcid,
        patents=patents,
    )

    kpi_row(
        kpi("Entidades modeladas", f"{len(_entity_df):,}", "catálogo base del observatorio"),
        kpi("Relaciones definidas", f"{len(_rel_df):,}", "enlaces críticos entre entidades"),
        kpi("Entidades con datos observados",
            f"{sum(1 for _v in _observed_counts.values() if _v > 0):,}",
            "capas con evidencia cargada"),
        kpi("Fuentes integradas", "11", "publicaciones, ANID, capital humano, convenios, ORCID y más"),
    )

    st.markdown(
        "<div class='alert-azul'><b>Objetivo:</b> pasar de datasets aislados a un modelo estable de entidades "
        "(`persona`, `investigador`, `proyecto`, `publicación`, `convocatoria`, `activo tecnológico`, `institución`) "
        "que permita matching, trazabilidad y mejores respuestas del asistente.</div>",
        unsafe_allow_html=True,
    )

    _render_cris_rims_audit_panel(ctx)

    sec("Catálogo de entidades")
    if _entity_df.empty:
        st.info("Aún no existe el catálogo de entidades del observatorio.")
    else:
        _entity_show = _entity_df.copy()
        _entity_show["registros_observados"] = _entity_show["entidad"].map(_observed_counts).fillna(0).astype(int)
        st.dataframe(
            _entity_show.rename(columns={
                "entidad": "Entidad",
                "descripcion": "Descripción",
                "fuente_principal": "Fuente principal",
                "identificador_clave": "Identificador",
                "nivel_sensibilidad": "Sensibilidad",
                "prioridad_gobernanza": "Prioridad",
                "steward_sugerido": "Steward sugerido",
                "estado_modelado": "Estado modelado",
                "registros_observados": "Registros observados",
            }),
            width="stretch",
            hide_index=True,
            height=340,
        )

    sec("Registros operativos canónicos")
    _op1, _op2, _op3, _op4 = st.columns(4)
    with _op1:
        kpi("Personas canónicas", f"{len(entity_personas):,}", "registro operativo fase 1")
    with _op2:
        kpi("Proyectos canónicos", f"{len(entity_projects):,}", "registro operativo fase 1")
    with _op3:
        kpi("Convocatorias canónicas", f"{len(entity_convocatorias):,}", "registro operativo fase 1")
    with _op4:
        kpi("Enlaces entre entidades", f"{len(entity_links):,}", "relaciones operativas generadas")

    _tab_p, _tab_proj, _tab_conv, _tab_links = st.tabs([
        "Personas", "Proyectos", "Convocatorias", "Links"
    ])
    with _tab_p:
        if entity_personas.empty:
            st.info("No existe aún `entity_registry_personas.csv`.")
        else:
            st.dataframe(
                entity_personas[[
                    "persona_id", "canonical_name", "orcid_id", "author_id",
                    "is_cchen_investigator", "appears_in_capital_humano",
                    "institution_name", "cchen_publications_count",
                ]].rename(columns={
                    "persona_id": "Persona ID",
                    "canonical_name": "Nombre canónico",
                    "orcid_id": "ORCID",
                    "author_id": "Author ID",
                    "is_cchen_investigator": "Investigador CCHEN",
                    "appears_in_capital_humano": "En capital humano",
                    "institution_name": "Institución",
                    "cchen_publications_count": "Papers CCHEN",
                }),
                width="stretch",
                hide_index=True,
                height=280,
            )
    with _tab_proj:
        if entity_projects.empty:
            st.info("No existe aún `entity_registry_proyectos.csv`.")
        else:
            st.dataframe(
                entity_projects[[
                    "project_id", "titulo", "autor", "institucion_name",
                    "instrumento", "estado", "strategic_profile_id",
                ]].rename(columns={
                    "project_id": "Proyecto ID",
                    "titulo": "Título",
                    "autor": "IR / Responsable",
                    "institucion_name": "Institución",
                    "instrumento": "Instrumento",
                    "estado": "Estado",
                    "strategic_profile_id": "Perfil estratégico",
                }),
                width="stretch",
                hide_index=True,
                height=280,
            )
    with _tab_conv:
        if entity_convocatorias.empty:
            st.info("No existe aún `entity_registry_convocatorias.csv`.")
        else:
            st.dataframe(
                entity_convocatorias[[
                    "convocatoria_id", "titulo", "estado", "perfil_id", "owner_unit", "relevancia_cchen"
                ]].rename(columns={
                    "convocatoria_id": "Convocatoria ID",
                    "titulo": "Título",
                    "estado": "Estado",
                    "perfil_id": "Perfil",
                    "owner_unit": "Unidad responsable",
                    "relevancia_cchen": "Relevancia",
                }),
                width="stretch",
                hide_index=True,
                height=280,
            )
    with _tab_links:
        if entity_links.empty:
            st.info("No existe aún `entity_links.csv`.")
        else:
            st.dataframe(
                entity_links.rename(columns={
                    "origin_type": "Origen",
                    "origin_id": "ID origen",
                    "relation": "Relación",
                    "target_type": "Destino",
                    "target_id": "ID destino",
                    "source_evidence": "Evidencia",
                    "confidence": "Confianza",
                }),
                width="stretch",
                hide_index=True,
                height=280,
            )

    sec("Relaciones críticas entre entidades")
    if _rel_df.empty:
        st.info("Aún no existe el mapa de relaciones del observatorio.")
    else:
        st.dataframe(
            _rel_df.rename(columns={
                "origen": "Origen",
                "relacion": "Relación",
                "destino": "Destino",
                "descripcion": "Descripción",
                "fuente_evidencia": "Fuente de evidencia",
                "prioridad": "Prioridad",
            }),
            width="stretch",
            hide_index=True,
            height=320,
        )

    sec("Prioridades inmediatas de gobernanza")
    _gov = pd.DataFrame([
        {
            "Prioridad": "1. Resolver identificadores",
            "Acción": "Definir claves maestras para persona, proyecto, publicación, convocatoria e institución.",
            "Impacto": "Evita duplicados y habilita joins estables.",
        },
        {
            "Prioridad": "2. Marcar sensibilidad",
            "Acción": "Separar explícitamente capas públicas, internas y sensibles para aplicar RLS con criterio.",
            "Impacto": "Protege capital humano y datos institucionales.",
        },
        {
            "Prioridad": "3. Trazabilidad de actualización",
            "Acción": "Registrar fecha, fuente, script y responsable de cada tabla integrada.",
            "Impacto": "Mejora auditoría y confianza en el observatorio.",
        },
        {
            "Prioridad": "4. Enlace con asistencia IA",
            "Acción": "Usar este modelo como base del contexto y luego como recuperación temática.",
            "Impacto": "Hace que el asistente responda con más precisión y menos prompt manual.",
        },
    ])
    st.dataframe(_gov, width="stretch", hide_index=True, height=220)

    _g1, _g2, _g3, _g4 = st.columns(4)
    with _g1:
        st.download_button(
            "Exportar entidades CSV",
            make_csv(_entity_df if not _entity_df.empty else pd.DataFrame()),
            "modelo_entidades_observatorio.csv",
            "text/csv",
        )
    with _g2:
        st.download_button(
            "Exportar relaciones CSV",
            make_csv(_rel_df if not _rel_df.empty else pd.DataFrame()),
            "relaciones_entidades_observatorio.csv",
            "text/csv",
        )
    with _g3:
        st.download_button(
            "Exportar entidades operativas",
            make_csv(entity_personas if not entity_personas.empty else pd.DataFrame()),
            "entity_registry_personas.csv",
            "text/csv",
        )
    with _g4:
        st.download_button(
            "Exportar matching formal",
            make_csv(matching_inst if matching_inst is not None and not matching_inst.empty else pd.DataFrame()),
            "convocatorias_matching_institucional.csv",
            "text/csv",
        )
