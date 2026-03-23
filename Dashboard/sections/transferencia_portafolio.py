"""Section: Transferencia y Portafolio — CCHEN Observatorio"""
import pandas as pd
import plotly.express as px
import streamlit as st

from .shared import (
    BLUE, GREEN, AMBER, PURPLE,
    kpi, kpi_row, sec, make_csv,
    _load_portafolio_seed,
)


def render(ctx: dict) -> None:
    """Render the Transferencia y Portafolio section."""
    anid        = ctx["anid"]
    pub_enr     = ctx["pub_enr"]
    funding_plus = ctx["funding_plus"]
    patents     = ctx["patents"]
    acuerdos    = ctx["acuerdos"]
    convenios   = ctx["convenios"]
    orcid       = ctx["orcid"]
    datacite    = ctx["datacite"]
    openaire    = ctx["openaire"]

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
            use_container_width=True,
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
        st.plotly_chart(fig_sig, use_container_width=True)

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
            st.plotly_chart(fig_area, use_container_width=True)
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
            st.plotly_chart(fig_dc, use_container_width=True)
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
                use_container_width=True,
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
            st.plotly_chart(fig_oa_type, use_container_width=True)
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
            st.plotly_chart(fig_oa_scope, use_container_width=True)

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
            use_container_width=True,
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
