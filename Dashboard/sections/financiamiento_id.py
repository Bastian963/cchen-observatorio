"""Section: Financiamiento I+D — CCHEN Observatorio"""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from .shared import (
    BLUE, RED, GREEN, AMBER, PALETTE,
    PORTALES_CIENTIFICOS,
    kpi, kpi_row, sec, make_csv,
    _load_convocatorias_data,
)


def render(ctx: dict) -> None:
    """Render the Financiamiento I+D section."""
    anid         = ctx["anid"]
    crossref     = ctx["crossref"]
    iaea_tc      = ctx["iaea_tc"]
    funding_plus = ctx["funding_plus"]
    convenios    = ctx["convenios"]
    acuerdos     = ctx["acuerdos"]

    st.title("Financiamiento I+D — Fondos ANID")
    st.caption("Fuente: Repositorio ANID · 30 proyectos adjudicados · 2000–2025")
    st.divider()

    with st.expander("Filtros", expanded=True):
        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            yr_a = st.slider("Año concurso", 2000, 2025, (2000, 2025), key="fi_yr_range")
        with fc2:
            progs = ["Todos"] + sorted(anid["programa_norm"].dropna().unique())
            prog_sel = st.selectbox("Programa", progs)
        with fc3:
            busq_a = st.text_input("🔎 Buscar en título / resumen", placeholder="ej: plasma, fusión, reactor")

    df_a = anid[anid["anio_concurso"].between(*yr_a)].copy()
    if prog_sel != "Todos":
        df_a = df_a[df_a["programa_norm"] == prog_sel]
    if busq_a:
        mask = (
            df_a["titulo"].str.contains(busq_a, case=False, na=False) |
            df_a["resumen"].str.contains(busq_a, case=False, na=False)
        )
        df_a = df_a[mask]

    monto_t   = df_a["monto_programa_num"].sum()
    con_monto = df_a["monto_programa_num"].notna().sum()

    kpi_row(
        kpi("Proyectos", f"{len(df_a)}"),
        kpi("Monto total", f"${monto_t/1e6:.1f} MM", "CLP acumulado"),
        kpi("Con info de monto", f"{con_monto}/{len(df_a)}"),
        kpi("Promedio / proyecto", f"${monto_t/con_monto/1e6:.1f} MM" if con_monto else "—"),
    )

    col1, col2 = st.columns(2)

    with col1:
        sec("Proyectos y monto por año")
        by_a = df_a.groupby("anio_concurso").agg(
            Proyectos=("titulo", "count"),
            Monto_MM=("monto_programa_num", lambda x: x.sum() / 1e6)
        ).reset_index().dropna()
        fig = go.Figure()
        fig.add_bar(x=by_a["anio_concurso"], y=by_a["Proyectos"], name="N° Proyectos", marker_color=BLUE)
        fig.add_scatter(x=by_a["anio_concurso"], y=by_a["Monto_MM"], name="MM CLP",
                        mode="lines+markers", marker_color=RED, yaxis="y2")
        fig.update_layout(
            yaxis=dict(title="N° Proyectos"),
            yaxis2=dict(title="MM CLP", overlaying="y", side="right"),
            legend=dict(orientation="h", y=1.1),
            margin=dict(t=10, b=30, l=40, r=60),
            height=320,
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        sec("Distribución por programa")
        prog_c = df_a["programa_norm"].value_counts().reset_index()
        prog_c.columns = ["Programa", "N"]
        fig2 = px.pie(prog_c, names="Programa", values="N",
                      color_discrete_sequence=PALETTE, height=320)
        fig2.update_traces(textposition="inside", textinfo="percent+label")
        fig2.update_layout(margin=dict(t=10, b=10))
        st.plotly_chart(fig2, use_container_width=True)

    col3, col4 = st.columns(2)

    with col3:
        sec("Monto por instrumento (MM CLP)")
        mi = df_a.groupby("instrumento_norm")["monto_programa_num"].sum().div(1e6).reset_index()
        mi.columns = ["Instrumento", "Monto_MM"]
        mi = mi.sort_values("Monto_MM")
        fig3 = px.bar(mi, x="Monto_MM", y="Instrumento", orientation="h",
                      color_discrete_sequence=[BLUE], text=mi["Monto_MM"].round(1), height=280)
        fig3.update_layout(showlegend=False, margin=dict(t=10, b=10), xaxis_title="MM CLP")
        st.plotly_chart(fig3, use_container_width=True)

    with col4:
        sec("Proyectos por instrumento")
        pi = df_a["instrumento_norm"].value_counts().reset_index()
        pi.columns = ["Instrumento", "N"]
        fig4 = px.bar(pi.sort_values("N"), x="N", y="Instrumento", orientation="h",
                      color_discrete_sequence=[RED], text="N", height=280)
        fig4.update_layout(showlegend=False, margin=dict(t=10, b=10))
        st.plotly_chart(fig4, use_container_width=True)

    sec(f"Tabla de proyectos — {len(df_a)} resultados")
    show_cols = ["anio_concurso", "titulo", "programa_norm", "instrumento_norm", "autor", "estado_full", "monto_programa_num"]
    df_a_s = df_a[show_cols].rename(columns={
        "anio_concurso": "Año", "titulo": "Título", "programa_norm": "Programa",
        "instrumento_norm": "Instrumento", "autor": "Investigador",
        "estado_full": "Estado", "monto_programa_num": "Monto CLP"
    }).sort_values("Año", ascending=False)
    st.dataframe(df_a_s, use_container_width=True, height=400,
                 column_config={"Monto CLP": st.column_config.NumberColumn(format="$ %,.0f")})
    st.download_button("Exportar proyectos CSV", make_csv(df_a_s),
                       "proyectos_anid_cchen.csv", "text/csv")

    # ── Financiadores externos (CrossRef) ─────────────────────────────────────
    if not crossref.empty and "crossref_funders" in crossref.columns:
        sec("Fuentes de financiamiento externas (CrossRef)")
        _all_funders = (
            crossref["crossref_funders"].dropna()
            .str.split("; ")
            .explode()
            .str.strip()
            .replace("", pd.NA)
            .dropna()
        )
        funder_counts = _all_funders.value_counts().head(15).reset_index()
        funder_counts.columns = ["Financiador", "Papers"]
        fig_funders = px.bar(
            funder_counts, x="Papers", y="Financiador",
            orientation="h", color="Papers",
            color_continuous_scale=[[0, "#F0F6FF"], [1, BLUE]],
            title="Financiadores externos en publicaciones CCHEN",
        )
        fig_funders.update_layout(showlegend=False, height=450, margin=dict(t=30, b=10))
        st.plotly_chart(fig_funders, use_container_width=True)

        n_with_funder = (
            crossref["crossref_funders"].notna() &
            (crossref["crossref_funders"] != "")
        ).sum()
        kpi_row(
            kpi("Papers con financiador externo", str(n_with_funder),
                f"{100 * n_with_funder / max(1, len(crossref)):.0f}% de los papers"),
            kpi("Financiadores únicos", str(int(_all_funders.nunique())),
                "fuentes externas identificadas"),
        )

    # ── IAEA TC ───────────────────────────────────────────────────────────────
    if not iaea_tc.empty:
        sec("Cooperación Técnica IAEA (Chile)")
        st.dataframe(
            iaea_tc, use_container_width=True,
            column_config={
                "proyecto_tc": st.column_config.TextColumn("Código TC"),
                "fuente":      st.column_config.TextColumn("Fuente"),
            },
        )

    # ── Financiamiento adicional ──────────────────────────────────────────────
    if not funding_plus.empty and len(funding_plus) > 0:
        sec("Financiamiento complementario (CORFO, FIC, IAEA)")
        st.dataframe(funding_plus, use_container_width=True, height=300)

    # ── Convenios y Acuerdos Institucionales ──────────────────────────────────
    _has_conv = not convenios.empty
    _has_acue = not acuerdos.empty
    if _has_conv or _has_acue:
        st.markdown("---")
        st.subheader("Convenios y Acuerdos Institucionales")
        st.caption("Fuente: datos.gob.cl · Transparencia CCHEN")

        kpi_row(
            kpi("Convenios nacionales", str(len(convenios)) if _has_conv else "—",
                "suscritos con entidades nacionales"),
            kpi("Acuerdos internacionales", str(len(acuerdos)) if _has_acue else "—",
                "instrumentos con organismos extranjeros"),
        )

        _cv1, _cv2 = st.columns(2)

        with _cv1:
            if _has_conv:
                sec(f"Convenios nacionales ({len(convenios)})")
                _conv_cols = [c for c in ["CONTRAPARTE DEL CONVENIO", "DESCRIPCIÓN",
                                           "DURACIÓN", "FECHA RESOLUCIÓN"] if c in convenios.columns]
                if not _conv_cols:
                    _conv_cols = convenios.columns.tolist()
                st.dataframe(convenios[_conv_cols], use_container_width=True, height=320)
                st.download_button(
                    "Exportar convenios CSV", make_csv(convenios[_conv_cols]),
                    "convenios_nacionales_cchen.csv", "text/csv",
                )

                _fecha_col = next((c for c in convenios.columns
                                   if "fecha" in c.lower()), None)
                if _fecha_col:
                    try:
                        _conv_yr = pd.to_datetime(convenios[_fecha_col], errors="coerce").dt.year
                        _conv_yr = _conv_yr.dropna().astype(int)
                        if len(_conv_yr) > 2:
                            _conv_yr_cnt = _conv_yr.value_counts().sort_index().reset_index()
                            _conv_yr_cnt.columns = ["Año", "N"]
                            fig_conv = px.bar(_conv_yr_cnt, x="Año", y="N", text="N",
                                              color_discrete_sequence=[BLUE], height=220,
                                              title="Convenios nacionales por año")
                            fig_conv.update_traces(textposition="outside")
                            fig_conv.update_layout(showlegend=False, margin=dict(t=30, b=20))
                            st.plotly_chart(fig_conv, use_container_width=True)
                    except Exception:
                        pass

        with _cv2:
            if _has_acue:
                sec(f"Acuerdos internacionales ({len(acuerdos)})")
                _acue_cols = [c for c in ["Sección", "País", "Instrumento", "Firma", "Vigencia",
                                           "PAÍS / REGIÓN", "INSTITUCIÓN", "TIPO",
                                           "DESCRIPCIÓN", "FECHA"] if c in acuerdos.columns]
                if not _acue_cols:
                    _acue_cols = acuerdos.columns.tolist()
                st.dataframe(acuerdos[_acue_cols], use_container_width=True, height=320)
                st.download_button(
                    "Exportar acuerdos CSV", make_csv(acuerdos[_acue_cols]),
                    "acuerdos_internacionales_cchen.csv", "text/csv",
                )

                _pais_col = next((c for c in acuerdos.columns
                                  if c.lower() in ("país", "pais", "country", "región")), None)
                if _pais_col:
                    try:
                        _pais_cnt = acuerdos[_pais_col].dropna().value_counts().head(12).reset_index()
                        _pais_cnt.columns = ["País", "N"]
                        fig_pais = px.bar(
                            _pais_cnt.sort_values("N"), x="N", y="País",
                            orientation="h", color_discrete_sequence=[GREEN],
                            text="N", height=320,
                            title="Acuerdos internacionales por país/región",
                        )
                        fig_pais.update_layout(showlegend=False, margin=dict(t=30, b=10))
                        st.plotly_chart(fig_pais, use_container_width=True)
                    except Exception:
                        pass

    # ── CONVOCATORIAS ABIERTAS Y PRÓXIMAS ────────────────────────────────────
    st.markdown("---")
    st.markdown("## 🎯 Convocatorias Abiertas y Próximas")
    st.caption(
        "Radar curado para académicos, postdocs y equipos científicos. "
        "Prioriza fuentes oficiales y separa convocatorias reales de portales estratégicos."
    )

    _conv, _conv_mode, _conv_path = _load_convocatorias_data()
    if _conv.empty:
        st.info(
            "Ejecuta `python3 Scripts/convocatorias_monitor.py` para generar "
            "`Data/Vigilancia/convocatorias_curadas.csv`."
        )
    else:
        if _conv_mode == "legacy":
            st.warning(
                "Se cargó el monitor legado. Esa fuente mezcla noticias y alertas RSS, "
                "así que conviene regenerar la versión curada desde ANID oficial."
            )
        else:
            st.caption(f"Fuente activa: `{_conv_path.name}`")

        _calls = _conv[_conv["tipo_registro"] != "portal"].copy()
        if not _calls.empty:
            _calls = _calls.sort_values(["cierre_dt", "apertura_dt", "orden"], na_position="last")
        _profiles = sorted([p for p in _calls["perfil_objetivo"].dropna().unique().tolist() if p])
        _default_profiles = [
            p for p in _profiles
            if p not in {"Magíster / educación", "Funcionarios públicos", "Revisión manual"}
        ] or _profiles

        _cf1, _cf2, _cf3, _cf4 = st.columns([1.1, 2.2, 1.3, 2.4])
        with _cf1:
            _estado_sel = st.selectbox(
                "Estado",
                ["Abiertas y próximas", "Solo abiertas", "Solo próximas", "Todas"],
                key="conv_clean_estado",
            )
        with _cf2:
            _perfil_sel = st.multiselect(
                "Perfil objetivo",
                _profiles,
                default=_default_profiles,
                key="conv_clean_profile",
            )
        with _cf3:
            _rel_sel = st.selectbox(
                "Relevancia CCHEN",
                ["Alta y media", "Solo alta", "Todas"],
                key="conv_clean_rel",
            )
        with _cf4:
            _conv_q = st.text_input(
                "Buscar",
                placeholder="ej: fondecyt, postdoctorado, salud, gemini, instalación",
                key="conv_clean_search",
            )

        _cshow = _calls.copy()
        if _perfil_sel:
            _cshow = _cshow[_cshow["perfil_objetivo"].isin(_perfil_sel)]
        if _estado_sel == "Solo abiertas":
            _cshow = _cshow[_cshow["estado"] == "Abierto"]
        elif _estado_sel == "Solo próximas":
            _cshow = _cshow[_cshow["estado"] == "Próximo"]
        elif _estado_sel == "Abiertas y próximas":
            _cshow = _cshow[_cshow["estado"].isin(["Abierto", "Próximo"])]
        if _rel_sel == "Solo alta":
            _cshow = _cshow[_cshow["relevancia_cchen"] == "Alta"]
        elif _rel_sel == "Alta y media":
            _cshow = _cshow[_cshow["relevancia_cchen"].isin(["Alta", "Media", ""])]
        if _conv_q:
            _q = _conv_q.strip()
            _mask = (
                _cshow["titulo"].str.contains(_q, case=False, na=False) |
                _cshow["categoria"].str.contains(_q, case=False, na=False) |
                _cshow["perfil_objetivo"].str.contains(_q, case=False, na=False) |
                _cshow["notas"].str.contains(_q, case=False, na=False)
            )
            _cshow = _cshow[_mask]

        _abiertas = _calls[_calls["estado"] == "Abierto"]
        _proximas = _calls[_calls["estado"] == "Próximo"]
        kpi_row(
            kpi("Abiertas ahora", f"{len(_abiertas):,}", "convocatorias oficiales detectadas"),
            kpi("Próximas", f"{len(_proximas):,}", "ventanas en preparación"),
            kpi("Registros oficiales", f"{int(_calls['es_oficial'].sum()):,}", "filas curadas / verificadas"),
            kpi("Portales estratégicos", f"{len(PORTALES_CIENTIFICOS):,}", "fuentes externas para ampliar radar"),
        )

        _abiertas_show = _cshow[_cshow["estado"] == "Abierto"].sort_values(
            ["cierre_dt", "orden"], na_position="last"
        )
        if not _abiertas_show.empty:
            sec(f"Abiertas ahora ({len(_abiertas_show)})")
            for _, _crow in _abiertas_show.head(10).iterrows():
                with st.expander(f"🟢 {_crow['titulo']}"):
                    st.caption(
                        f"{_crow['organismo']} · {_crow['categoria']} · "
                        f"Perfil: {_crow['perfil_objetivo']} · Relevancia: {_crow['relevancia_cchen']}"
                    )
                    _lineas = []
                    if _crow["apertura_texto"]:
                        _lineas.append(f"**Inicio:** {_crow['apertura_texto']}")
                    if _crow["cierre_texto"]:
                        _lineas.append(f"**Cierre:** {_crow['cierre_texto']}")
                    if _crow["fallo_texto"]:
                        _lineas.append(f"**Fallo:** {_crow['fallo_texto']}")
                    if _lineas:
                        st.markdown("  \n".join(_lineas))
                    if _crow["notas"]:
                        st.write(_crow["notas"])
                    if _crow["url"]:
                        st.markdown(f"[Ver convocatoria oficial →]({_crow['url']})")

        _proximas_show = _cshow[_cshow["estado"] == "Próximo"].sort_values(
            ["apertura_dt", "orden"], na_position="last"
        )
        if not _proximas_show.empty:
            sec(f"Próximas relevantes ({len(_proximas_show)})")
            for _, _crow in _proximas_show.head(14).iterrows():
                with st.expander(f"🗓️ {_crow['titulo']}"):
                    st.caption(
                        f"{_crow['organismo']} · {_crow['categoria']} · "
                        f"Perfil: {_crow['perfil_objetivo']} · Relevancia: {_crow['relevancia_cchen']}"
                    )
                    _lineas = []
                    if _crow["apertura_texto"]:
                        _lineas.append(f"**Apertura estimada:** {_crow['apertura_texto']}")
                    if _crow["cierre_texto"]:
                        _lineas.append(f"**Cierre estimado:** {_crow['cierre_texto']}")
                    if _crow["fallo_texto"]:
                        _lineas.append(f"**Fallo estimado:** {_crow['fallo_texto']}")
                    if _lineas:
                        st.markdown("  \n".join(_lineas))
                    if _crow["notas"]:
                        st.write(_crow["notas"])
                    if _crow["url"]:
                        st.markdown(f"[Ver ficha oficial →]({_crow['url']})")

        sec(f"Tabla de oportunidades ({len(_cshow)})")
        if _cshow.empty:
            st.warning("No hay convocatorias que coincidan con los filtros actuales.")
        else:
            _conv_table = _cshow[[
                "estado", "titulo", "categoria", "perfil_objetivo",
                "apertura_texto", "cierre_texto", "organismo",
                "relevancia_cchen", "url"
            ]].rename(columns={
                "estado": "Estado",
                "titulo": "Convocatoria",
                "categoria": "Categoría",
                "perfil_objetivo": "Perfil objetivo",
                "apertura_texto": "Apertura",
                "cierre_texto": "Cierre",
                "organismo": "Organismo",
                "relevancia_cchen": "Relevancia",
                "url": "Ficha oficial",
            })
            st.dataframe(
                _conv_table,
                use_container_width=True,
                height=360,
                hide_index=True,
                column_config={
                    "Ficha oficial": st.column_config.LinkColumn("Ficha oficial"),
                },
            )
            st.download_button(
                "Exportar convocatorias CSV",
                make_csv(_cshow.drop(columns=["apertura_dt", "cierre_dt", "orden", "modo_carga"], errors="ignore")),
                "cchen_convocatorias_curadas.csv",
                "text/csv",
            )

        sec("Portales científicos para ampliar el radar")
        for _portal in PORTALES_CIENTIFICOS:
            with st.expander(f"🌍 {_portal['nombre']}"):
                st.caption(f"{_portal['organismo']} · {_portal['perfil_objetivo']}")
                st.write(_portal["descripcion"])
                st.markdown(f"[Ir al portal oficial →]({_portal['url']})")
