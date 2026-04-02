"""Section: Convocatorias y Matching — CCHEN Observatorio"""
import datetime as dt
from pathlib import Path

import pandas as pd
import streamlit as st

from .shared import (
    asset_catalog_frame,
    filter_asset_catalog,
    kpi, kpi_row, sec, make_csv,
    render_asset_links_table,
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
    asset_catalog = asset_catalog_frame(ctx)

    st.title("Convocatorias y Matching CCHEN")
    st.caption(
        "Cruza el radar curado de oportunidades con perfiles institucionales, reglas explícitas "
        "de elegibilidad y un scoring formal para apoyar una mesa de pre-postulación seria."
    )
    st.divider()

    related_assets = filter_asset_catalog(
        asset_catalog,
        section_name="Convocatorias y Matching",
        require_public_url=True,
        limit=6,
    )
    render_asset_links_table(
        related_assets,
        "Activos institucionales vinculados",
        "Aún no hay activos publicados enlazados a esta sección; usa la cola editorial para completar DSpace.",
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

        sec("Panel operativo DGIn")
        st.caption(
            "Vista de operación para seguimiento semanal: oportunidades activables, próximas a cierre y cola de gestión."
        )

        _ops_df = _matching.copy()
        _ops_df["score_total"] = pd.to_numeric(_ops_df.get("score_total", 0), errors="coerce").fillna(0)
        _ops_df["cierre_dt"] = pd.to_datetime(_ops_df.get("cierre_iso", ""), errors="coerce")
        _today = pd.Timestamp.utcnow().tz_localize(None)
        _ops_df["dias_al_cierre"] = (_ops_df["cierre_dt"] - _today).dt.days

        _unit_options = sorted([
            _text_or_empty(v) for v in _ops_df.get("owner_unit", pd.Series(dtype=str)).dropna().unique().tolist()
            if _text_or_empty(v)
        ])
        _default_unit = [u for u in _unit_options if "dgin" in u.lower()]
        _default_unit = _default_unit[:1] if _default_unit else []
        _unit_selected = st.multiselect(
            "Unidad objetivo",
            _unit_options,
            default=_default_unit,
            key="matching_dgin_unit_select",
        )

        _ops_view = _ops_df.copy()
        if _unit_selected:
            _ops_view = _ops_view[_ops_view["owner_unit"].isin(_unit_selected)]

        _activables = _ops_view[
            (_ops_view["estado"] == "Abierto") &
            (_ops_view["readiness_status"] == "Listo para activar")
        ]
        _proximas_45 = _ops_view[
            (_ops_view["estado"].isin(["Abierto", "Próximo"])) &
            (_ops_view["dias_al_cierre"].notna()) &
            (_ops_view["dias_al_cierre"] >= 0) &
            (_ops_view["dias_al_cierre"] <= 45)
        ]
        _requiere_prep = _ops_view[_ops_view["readiness_status"] == "Requiere preparación"]
        _score_abiertas = _ops_view[_ops_view["estado"] == "Abierto"]["score_total"]

        kpi_row(
            kpi("Activables hoy", f"{len(_activables):,}", "abiertas + listas"),
            kpi("Cierre ≤45 días", f"{len(_proximas_45):,}", "abiertas o próximas"),
            kpi("Requieren preparación", f"{len(_requiere_prep):,}", "para planificación de pre-postulación"),
            kpi("Score medio abiertas", f"{_score_abiertas.mean():.1f}" if not _score_abiertas.empty else "0.0", "unidades filtradas"),
        )

        _seguimiento_cols = [
            "conv_id", "convocatoria_titulo", "perfil_nombre", "owner_unit", "estado",
            "score_total", "eligibility_status", "readiness_status", "deadline_class",
            "dias_al_cierre", "recommended_action", "url",
        ]
        _seguimiento_df = _ops_view[[c for c in _seguimiento_cols if c in _ops_view.columns]].copy()
        _seguimiento_df.insert(len(_seguimiento_df.columns), "estado_gestion", "Pendiente")
        _seguimiento_df.insert(len(_seguimiento_df.columns), "responsable_dgin", "")
        _seguimiento_df.insert(len(_seguimiento_df.columns), "fecha_revision", "")
        _seguimiento_df.insert(len(_seguimiento_df.columns), "comentarios", "")
        _seguimiento_df = _seguimiento_df.sort_values(
            ["score_total", "dias_al_cierre"],
            ascending=[False, True],
            na_position="last",
        )

        st.dataframe(
            _seguimiento_df.head(30).rename(columns={
                "convocatoria_titulo": "Convocatoria",
                "perfil_nombre": "Perfil",
                "owner_unit": "Unidad",
                "score_total": "Score",
                "eligibility_status": "Elegibilidad",
                "readiness_status": "Preparación",
                "deadline_class": "Ventana",
                "dias_al_cierre": "Días al cierre",
                "recommended_action": "Acción sugerida",
                "url": "Ficha oficial",
            }),
            width="stretch",
            hide_index=True,
            height=320,
            column_config={"Ficha oficial": st.column_config.LinkColumn("Ficha oficial")},
        )

        _export_stamp = dt.datetime.now().strftime("%Y%m%d_%H%M")
        _d1, _d2 = st.columns(2)
        with _d1:
            st.download_button(
                "Exportar cola operativa DGIn CSV",
                make_csv(_seguimiento_df),
                f"dgin_cola_operativa_convocatorias_{_export_stamp}.csv",
                "text/csv",
                disabled=_seguimiento_df.empty,
            )
        with _d2:
            st.download_button(
                "Exportar base convocatorias curada CSV",
                make_csv(_conv),
                f"convocatorias_curadas_{_export_stamp}.csv",
                "text/csv",
                disabled=_conv.empty,
            )

        _plantilla_cols = [
            "conv_id", "convocatoria_titulo", "perfil_nombre", "owner_unit", "estado",
            "score_total", "eligibility_status", "readiness_status", "deadline_class",
            "dias_al_cierre", "recommended_action", "url",
            "estado_gestion", "responsable_dgin", "fecha_revision", "comentarios",
        ]
        _plantilla_df = pd.DataFrame(columns=_plantilla_cols)
        st.download_button(
            "Descargar plantilla vacía DGIn CSV",
            make_csv(_plantilla_df),
            "dgin_cola_operativa_template.csv",
            "text/csv",
        )

        with st.expander("Diccionario de campos (CSV exportables)", expanded=False):
            _dict_rows = [
                {
                    "dataset_csv": f"dgin_cola_operativa_convocatorias_{_export_stamp}.csv",
                    "campo": "conv_id",
                    "descripcion": "Identificador unico de convocatoria en el sistema de matching.",
                    "tipo_dato_esperado": "string",
                    "ejemplo": "ANID-2026-001",
                },
                {
                    "dataset_csv": f"dgin_cola_operativa_convocatorias_{_export_stamp}.csv",
                    "campo": "convocatoria_titulo",
                    "descripcion": "Nombre oficial de la convocatoria.",
                    "tipo_dato_esperado": "string",
                    "ejemplo": "FONIS 2026",
                },
                {
                    "dataset_csv": f"dgin_cola_operativa_convocatorias_{_export_stamp}.csv",
                    "campo": "owner_unit",
                    "descripcion": "Unidad institucional sugerida como responsable de gestion.",
                    "tipo_dato_esperado": "string",
                    "ejemplo": "Gestion I+D",
                },
                {
                    "dataset_csv": f"dgin_cola_operativa_convocatorias_{_export_stamp}.csv",
                    "campo": "score_total",
                    "descripcion": "Puntaje de matching institucional para priorizacion operativa.",
                    "tipo_dato_esperado": "float",
                    "ejemplo": "95.0",
                },
                {
                    "dataset_csv": f"dgin_cola_operativa_convocatorias_{_export_stamp}.csv",
                    "campo": "estado_gestion",
                    "descripcion": "Estado manual de seguimiento DGIn (pendiente, evaluacion, postulacion, cerrada).",
                    "tipo_dato_esperado": "string (catalogo)",
                    "ejemplo": "Postulacion en curso",
                },
                {
                    "dataset_csv": f"dgin_cola_operativa_convocatorias_{_export_stamp}.csv",
                    "campo": "responsable_dgin",
                    "descripcion": "Responsable nominal para seguimiento de la convocatoria.",
                    "tipo_dato_esperado": "string",
                    "ejemplo": "Nombre Apellido",
                },
                {
                    "dataset_csv": f"convocatorias_curadas_{_export_stamp}.csv",
                    "campo": "estado",
                    "descripcion": "Estado de apertura de la convocatoria (Abierto o Proximo).",
                    "tipo_dato_esperado": "string (catalogo)",
                    "ejemplo": "Abierto",
                },
                {
                    "dataset_csv": f"convocatorias_curadas_{_export_stamp}.csv",
                    "campo": "relevancia_cchen",
                    "descripcion": "Nivel de relevancia institucional definido en curaduria.",
                    "tipo_dato_esperado": "string",
                    "ejemplo": "Alta",
                },
                {
                    "dataset_csv": f"convocatorias_matching_rules_{_export_stamp}.csv",
                    "campo": "perfil_id",
                    "descripcion": "Identificador del perfil institucional asociado a reglas.",
                    "tipo_dato_esperado": "string",
                    "ejemplo": "perfil_gestion_id",
                },
                {
                    "dataset_csv": f"convocatorias_matching_rules_{_export_stamp}.csv",
                    "campo": "notes",
                    "descripcion": "Notas operativas y criterios complementarios de matching.",
                    "tipo_dato_esperado": "string",
                    "ejemplo": "Priorizar cuando cierre <= 45 dias",
                },
            ]
            _dict_df = pd.DataFrame(_dict_rows)
            st.dataframe(_dict_df, width="stretch", hide_index=True, height=280)
            st.download_button(
                "Descargar diccionario de campos CSV (Convocatorias)",
                make_csv(_dict_df),
                "diccionario_campos_convocatorias_matching.csv",
                "text/csv",
            )

        with st.expander("Guía semanal DGIn (3 pasos)", expanded=False):
            st.markdown(
                "1. **Priorizar**: filtrar por unidad, revisar `Activables hoy` y `Cierre <= 45 días`.\n"
                "2. **Gestionar**: exportar cola DGIn y completar `estado_gestion`, `responsable_dgin`, `fecha_revision`, `comentarios`.\n"
                "3. **Cerrar**: definir top oportunidades de la semana, responsables y fecha de control siguiente."
            )

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
            st.download_button(
                "Exportar reglas de matching CSV",
                make_csv(_rules),
                f"convocatorias_matching_rules_{_export_stamp}.csv",
                "text/csv",
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
