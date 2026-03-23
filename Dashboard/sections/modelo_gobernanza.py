"""Section: Modelo y Gobernanza — CCHEN Observatorio"""
import pandas as pd
import streamlit as st

from .shared import (
    kpi, kpi_row, sec, make_csv,
    _load_entity_model_tables,
    _build_entity_observed_counts,
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
            use_container_width=True,
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
                use_container_width=True,
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
                use_container_width=True,
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
                use_container_width=True,
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
                use_container_width=True,
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
            use_container_width=True,
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
    st.dataframe(_gov, use_container_width=True, hide_index=True, height=220)

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
