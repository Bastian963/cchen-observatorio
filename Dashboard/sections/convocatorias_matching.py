"""Section: Convocatorias y Matching — CCHEN Observatorio"""
from pathlib import Path

import pandas as pd
import streamlit as st

from .shared import (
    kpi, kpi_row, sec, make_csv,
    _text_or_empty,
    _load_convocatorias_data,
    _build_matching_profiles_summary,
)


def render(ctx: dict) -> None:
    """Render the Convocatorias y Matching section."""
    import data_loader as _data_loader

    base = getattr(_data_loader, "BASE", Path(__file__).resolve().parents[2] / "Data")
    load_convocatorias_matching_rules = getattr(_data_loader, "load_convocatorias_matching_rules", None)

    matching_inst = ctx["matching_inst"]
    perfiles_inst = ctx["perfiles_inst"]

    st.title("Convocatorias y Matching CCHEN")
    st.caption(
        "Cruza el radar curado de oportunidades con perfiles institucionales, reglas explícitas "
        "de elegibilidad y un scoring formal para apoyar una mesa de pre-postulación seria."
    )
    st.divider()

    _conv, _conv_mode, _conv_path = _load_convocatorias_data()
    _matching = matching_inst.copy() if matching_inst is not None else pd.DataFrame()
    _profiles = perfiles_inst.copy() if perfiles_inst is not None else pd.DataFrame()
    rules_path = base / "Vigilancia" / "convocatorias_matching_rules.csv"
    if callable(load_convocatorias_matching_rules):
        _rules = load_convocatorias_matching_rules()
    else:
        _rules = pd.read_csv(rules_path, encoding="utf-8-sig") if rules_path.exists() else pd.DataFrame()

    if _conv.empty or _matching.empty:
        st.info(
            "Falta la capa formal de matching. Ejecuta en orden:\n"
            "1. `python3 Scripts/fetch_funding_plus.py`\n"
            "2. `python3 Scripts/build_operational_core.py`\n"
            "3. `python3 Scripts/convocatorias_monitor.py` si necesitas regenerar la base curada."
        )
    else:
        st.caption(
            f"Fuentes activas: `{_conv_path.name}` + `convocatorias_matching_institucional.csv`"
        )
        _profile_summary = _build_matching_profiles_summary(_matching)
        _strength_order = {"Alta": 3, "Media": 2, "Inicial": 1}

        kpi_row(
            kpi("Convocatorias evaluadas", f"{_matching['conv_id'].nunique():,}", "matching institucional generado"),
            kpi("Abiertas", f"{int((_matching['estado'] == 'Abierto').sum()):,}", "evaluadas para activar hoy"),
            kpi("Próximas", f"{int((_matching['estado'] == 'Próximo').sum()):,}", "pipeline de preparación"),
            kpi("Cumplen base", f"{int((_matching['eligibility_status'] == 'Cumple base observada').sum()):,}", "elegibilidad institucional observable"),
        )

        sec("Ranking por perfil / unidad")
        st.caption(
            "El ranking ya no se calcula al vuelo con heurísticas del dashboard. "
            "Se lee desde una salida formal basada en reglas, evidencias y scoring reproducible."
        )
        if _profile_summary.empty:
            st.warning("No fue posible construir perfiles con la base actual.")
        else:
            _matching_show = _profile_summary.copy()
            _matching_show.insert(
                0,
                "Ranking",
                _matching_show["fuerza_interna"].map(_strength_order).fillna(0).astype(int),
            )
            st.dataframe(
                _matching_show.rename(columns={
                    "perfil": "Perfil CCHEN",
                    "fuerza_interna": "Fuerza interna",
                    "evidencia": "Evidencia observada",
                    "senal": "Lectura",
                    "abiertas": "Abiertas",
                    "proximas": "Próximas",
                    "oportunidades_destacadas": "Oportunidades destacadas",
                    "unidad_responsable": "Unidad responsable",
                }),
                width="stretch",
                hide_index=True,
                height=320,
            )

        _mf1, _mf2, _mf3, _mf4 = st.columns([1.4, 1.3, 1.3, 1.8])
        with _mf1:
            _profile_options = (
                _profiles["perfil_nombre"].dropna().tolist()
                if not _profiles.empty
                else sorted(_matching["perfil_nombre"].dropna().unique().tolist())
            )
            _profile_selected = st.selectbox("Perfil a revisar", _profile_options, index=0, key="matching_profile_select")
        with _mf2:
            _state_selected = st.selectbox(
                "Estado",
                ["Abierto y próximo", "Solo abiertas", "Solo próximas", "Todos"],
                key="matching_state_select",
            )
        with _mf3:
            _readiness_selected = st.selectbox(
                "Preparación",
                ["Todas", "Listo para activar", "Requiere preparación", "Exploratorio", "No listo"],
                key="matching_readiness_select",
            )
        with _mf4:
            _owner_options = sorted([o for o in _matching["owner_unit"].dropna().unique().tolist() if _text_or_empty(o)])
            _owners_selected = st.multiselect("Unidad responsable", _owner_options, default=_owner_options, key="matching_owner_select")

        _match_show = _matching.copy()
        if _profile_selected:
            _match_show = _match_show[_match_show["perfil_nombre"] == _profile_selected]
        if _state_selected == "Solo abiertas":
            _match_show = _match_show[_match_show["estado"] == "Abierto"]
        elif _state_selected == "Solo próximas":
            _match_show = _match_show[_match_show["estado"] == "Próximo"]
        elif _state_selected == "Abierto y próximo":
            _match_show = _match_show[_match_show["estado"].isin(["Abierto", "Próximo"])]
        if _readiness_selected != "Todas":
            _match_show = _match_show[_match_show["readiness_status"] == _readiness_selected]
        if _owners_selected:
            _match_show = _match_show[_match_show["owner_unit"].isin(_owners_selected)]
        _match_show = _match_show.sort_values(
            ["score_total", "estado", "cierre_iso", "apertura_iso"],
            ascending=[False, True, True, True],
            na_position="last",
        )

        sec(f"Oportunidades priorizadas para {_profile_selected}")
        if _match_show.empty:
            st.info("No hay oportunidades que coincidan con los filtros actuales.")
        else:
            st.dataframe(
                _match_show[[
                    "score_total", "convocatoria_titulo", "estado", "categoria", "owner_unit",
                    "eligibility_status", "readiness_status", "deadline_class", "recommended_action", "url",
                ]].rename(columns={
                    "score_total": "Score",
                    "convocatoria_titulo": "Convocatoria",
                    "estado": "Estado",
                    "categoria": "Categoría",
                    "owner_unit": "Unidad responsable",
                    "eligibility_status": "Elegibilidad",
                    "readiness_status": "Preparación",
                    "deadline_class": "Ventana",
                    "recommended_action": "Acción sugerida",
                    "url": "Ficha oficial",
                }),
                width="stretch",
                hide_index=True,
                height=320,
                column_config={"Ficha oficial": st.column_config.LinkColumn("Ficha oficial")},
            )
            st.download_button(
                "Exportar matching institucional CSV",
                make_csv(_match_show),
                "cchen_matching_convocatorias.csv",
                "text/csv",
            )

        _open_top = _matching[_matching["estado"] == "Abierto"].sort_values("score_total", ascending=False).head(6)
        if not _open_top.empty:
            sec("Abiertas con mejor score")
            for _, _row in _open_top.iterrows():
                with st.expander(f"🟢 {_row['convocatoria_titulo']} · score {_row['score_total']}"):
                    st.caption(
                        f"{_row['perfil_nombre']} · {_row['owner_unit']} · "
                        f"Elegibilidad: {_row['eligibility_status']} · Preparación: {_row['readiness_status']}"
                    )
                    st.write(_row["evidence_summary"])
                    st.markdown(f"**Acción sugerida:** {_row['recommended_action']}")
                    if _row["url"]:
                        st.markdown(f"[Ver ficha oficial →]({_row['url']})")

        sec("Reglas activas de matching")
        if _rules.empty:
            st.info("No se encontró el archivo de reglas formales de matching.")
        else:
            st.dataframe(
                _rules.rename(columns={
                    "perfil_id": "Perfil ID",
                    "exact_aliases": "Aliases exactos",
                    "secondary_aliases": "Aliases secundarios",
                    "requiere_doctorado": "Req. doctorado",
                    "requiere_institucion": "Req. institución",
                    "requiere_transferencia": "Req. transferencia",
                    "requiere_red_internacional": "Req. red internacional",
                    "requiere_capacidad_instrumental": "Req. capacidad instrumental",
                    "notes": "Notas",
                }),
                width="stretch",
                hide_index=True,
                height=250,
            )

        sec("Lectura operativa")
        _msg = (
            _profile_summary[_profile_summary["perfil"] == _profile_selected]
            if not _profile_summary.empty
            else pd.DataFrame()
        )
        if not _msg.empty:
            _row = _msg.iloc[0]
            st.markdown(
                f"<div class='alert-azul'><b>{_profile_selected}</b><br>"
                f"Fuerza interna: <b>{_row['fuerza_interna']}</b><br>"
                f"Unidad responsable: <b>{_row['unidad_responsable']}</b><br>"
                f"{_row['evidencia']}<br>"
                f"<small>{_row['senal']}</small></div>",
                unsafe_allow_html=True,
            )
        st.markdown(
            "<div class='alert-verde'><b>Recomendación operativa:</b> usar esta sección como mesa institucional de pre-postulación. "
            "El score no reemplaza la decisión final, pero sí ordena perfiles, elegibilidad observable y unidad responsable.</div>",
            unsafe_allow_html=True,
        )
