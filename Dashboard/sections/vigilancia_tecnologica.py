"""Section: Vigilancia Tecnológica — CCHEN Observatorio"""
import datetime as _dtlib
import subprocess
import sys

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from .shared import (
    BLUE, RED, GREEN, AMBER,
    kpi, kpi_row, sec, make_csv,
    _clean_html_text, _clean_news_title, _clean_news_snippet,
    _build_topic_label, _topic_terms_preview,
)


def render(ctx: dict) -> None:
    """Render the Vigilancia Tecnológica section."""
    from data_loader import BASE

    _VT_BASE = BASE / "Publications"
    _VT_VIG  = BASE / "Vigilancia"

    _arxiv_data = ctx.get("arxiv_monitor", __import__("pandas").DataFrame())
    _news_data  = ctx.get("news_monitor",  __import__("pandas").DataFrame())
    _iaea_data  = ctx.get("iaea_inis",     __import__("pandas").DataFrame())

    st.title("Vigilancia Tecnológica CCHEN")
    st.caption("Actividad publicadora institucional · Monitoreo de tendencias · Temas de investigación")
    st.divider()

    _vt_tabs = st.tabs([
        "📅 Publicaciones CCHEN",
        "📰 En la prensa",
        "📋 Boletín semanal",
        "📡 Monitor arXiv",
        "⚛️ Monitor IAEA INIS",
        "🔬 Temas de investigación",
    ])

    # ── TAB 1: Publicaciones CCHEN ───────────────────────────────────────────
    with _vt_tabs[0]:
        _abs_path = _VT_BASE / "cchen_abstracts_merged.csv"

        _pub_ctx = ctx.get("pub", __import__("pandas").DataFrame())
        _enr_ctx = ctx.get("pub_enr", __import__("pandas").DataFrame())

        if _pub_ctx.empty:
            st.info("No se encontraron publicaciones CCHEN en la base de datos.")
        else:
            _pub = _pub_ctx.copy()
            if not _enr_ctx.empty and "publication_date" in _enr_ctx.columns:
                _merge_cols = [c for c in ["work_id", "openalex_id"] if c in _enr_ctx.columns]
                if _merge_cols:
                    _key = _merge_cols[0]
                    _pub = _pub.merge(
                        _enr_ctx[[_key, "publication_date"]].rename(columns={_key: "openalex_id"}),
                        on="openalex_id", how="left"
                    )
            if "publication_date" not in _pub.columns:
                _pub["publication_date"] = None

            _pub["publication_date"] = pd.to_datetime(_pub["publication_date"], errors="coerce")
            _pub["year"] = pd.to_numeric(_pub["year"], errors="coerce")
            _pub = _pub.sort_values("publication_date", ascending=False, na_position="last")

            _total       = len(_pub)
            _latest_year = int(_pub["year"].max()) if _pub["year"].notna().any() else "—"
            _n_latest    = int((_pub["year"] == float(_latest_year)).sum()) if isinstance(_latest_year, int) else 0
            _last_date   = _pub["publication_date"].dropna().iloc[0] if _pub["publication_date"].notna().any() else None
            _total_cites = int(_pub["cited_by_count"].sum()) if "cited_by_count" in _pub.columns else 0

            kpi_row(
                kpi("Papers totales", f"{_total:,}"),
                kpi(f"En {_latest_year}", f"{_n_latest:,}", "año más reciente"),
                kpi("Último paper", str(_last_date.date()) if _last_date else str(_latest_year)),
                kpi("Total citaciones", f"{_total_cites:,}"),
            )
            st.divider()

            # ── Último paper publicado ──────────────────────────────────────
            sec("Último paper publicado")
            _last = _pub.iloc[0]
            with st.container(border=True):
                _lc1, _lc2 = st.columns([3, 1])
                with _lc1:
                    _last_title = str(_last.get("title") or "Sin título")
                    st.markdown(f"#### {_last_title}")
                    _last_src = str(_last.get("source") or "")
                    _last_dt  = str(_last.get("publication_date", "") or _last.get("year", ""))
                    st.caption(f"📅 {_last_dt}  ·  🏛 {_last_src[:90]}")
                    _last_type = str(_last.get("type") or "")
                    if _last_type:
                        st.caption(f"Tipo: {_last_type}")
                with _lc2:
                    _last_doi = _last.get("doi")
                    if pd.notna(_last_doi) and _last_doi:
                        st.link_button("Ver DOI →", f"https://doi.org/{_last_doi}",
                                       use_container_width=True)
                    _last_cites = _last.get("cited_by_count", 0)
                    st.metric("Citaciones", int(_last_cites) if pd.notna(_last_cites) else 0)
                    _last_oa = _last.get("is_oa", False)
                    if _last_oa:
                        st.success("Acceso Abierto")

            st.divider()

            # ── Calendario de publicaciones (heatmap año × mes) ─────────────
            sec("Calendario de publicaciones")
            _cal = _pub.dropna(subset=["publication_date"]).copy()
            if _cal.empty:
                st.info("No hay publicaciones con fecha exacta para construir el calendario.")
            else:
                _cal["yr"] = _cal["publication_date"].dt.year.astype(int)
                _cal["mo"] = _cal["publication_date"].dt.month.astype(int)
                _cal["pub_day"] = _cal["publication_date"].dt.normalize()
                _cal_grp = _cal.groupby(["yr", "mo"]).size().reset_index(name="n")

                _yrs = sorted(_cal_grp["yr"].unique())
                _month_names = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
                _cal_tabs = st.tabs(["Último mes", "Por año", "Todos los años"])

                with _cal_tabs[0]:
                    _end_date = _cal["pub_day"].max()
                    _start_date = _end_date - pd.Timedelta(days=29)
                    _day_order = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
                    _day_map = dict(enumerate(_day_order))
                    _full_days = pd.DataFrame({"date": pd.date_range(_start_date, _end_date, freq="D")})
                    _day_counts = _cal[_cal["pub_day"].between(_start_date, _end_date)]["pub_day"].value_counts()
                    _full_days["n"] = _full_days["date"].map(_day_counts).fillna(0).astype(int)
                    _full_days["dow"] = _full_days["date"].dt.dayofweek.map(_day_map)
                    _full_days["week_start"] = _full_days["date"] - pd.to_timedelta(_full_days["date"].dt.dayofweek, unit="D")
                    _full_days["week_label"] = _full_days["week_start"].dt.strftime("%d %b")
                    _pivot_last = _full_days.pivot(index="dow", columns="week_label", values="n").reindex(_day_order)
                    _last_text = _pivot_last.applymap(lambda v: str(int(v)) if pd.notna(v) and int(v) > 0 else "")
                    fig_last = go.Figure(go.Heatmap(
                        x=_pivot_last.columns.tolist(),
                        y=_pivot_last.index.tolist(),
                        z=_pivot_last.fillna(0).values,
                        text=_last_text.values,
                        texttemplate="%{text}",
                        colorscale=[[0, "#F8FAFC"], [0.25, "#BFDBFE"], [1.0, "#1D4ED8"]],
                        hovertemplate="%{y} · semana %{x}<br>%{z} publicaciones<extra></extra>",
                        colorbar=dict(title="N° papers", thickness=14, len=0.8),
                        xgap=3, ygap=3,
                    ))
                    fig_last.update_layout(
                        height=320,
                        plot_bgcolor="#F8FAFC",
                        paper_bgcolor="#F8FAFC",
                        xaxis=dict(side="top", tickfont=dict(size=11)),
                        yaxis=dict(autorange="reversed", tickfont=dict(size=11)),
                        margin=dict(t=50, b=10, l=40, r=10),
                    )
                    st.caption(
                        f"Últimos 30 días disponibles en la base: "
                        f"{_start_date.strftime('%d %b %Y')} → {_end_date.strftime('%d %b %Y')}"
                    )
                    st.plotly_chart(fig_last, use_container_width=True)

                with _cal_tabs[1]:
                    _year_sel = st.selectbox(
                        "Año a visualizar",
                        sorted(_yrs, reverse=True),
                        index=0,
                        key="vt_calendar_year_select",
                    )
                    _year_view = (
                        _cal[_cal["yr"] == _year_sel]
                        .groupby("mo")
                        .size()
                        .reindex(range(1, 13), fill_value=0)
                        .reset_index(name="n")
                    )
                    _year_view["Mes"] = _year_view["mo"].map(lambda m: _month_names[m - 1])
                    fig_year = px.bar(
                        _year_view,
                        x="Mes",
                        y="n",
                        text="n",
                        color_discrete_sequence=[BLUE],
                        height=280,
                    )
                    fig_year.update_traces(textposition="outside")
                    fig_year.update_layout(
                        showlegend=False,
                        plot_bgcolor="#F8FAFC",
                        paper_bgcolor="#F8FAFC",
                        margin=dict(t=10, b=10, l=10, r=10),
                        yaxis_title="Publicaciones",
                        xaxis_title="",
                    )
                    st.plotly_chart(fig_year, use_container_width=True)

                with _cal_tabs[2]:
                    _z = []
                    _text_z = []
                    for yr in _yrs:
                        row = []
                        trow = []
                        for mo in range(1, 13):
                            v = _cal_grp[(_cal_grp["yr"] == yr) & (_cal_grp["mo"] == mo)]["n"].values
                            val = int(v[0]) if len(v) > 0 else 0
                            row.append(val)
                            trow.append(str(val) if val > 0 else "")
                        _z.append(row)
                        _text_z.append(trow)

                    fig_cal = go.Figure(go.Heatmap(
                        x=_month_names,
                        y=[str(y) for y in _yrs],
                        z=_z,
                        text=_text_z,
                        texttemplate="%{text}",
                        colorscale=[[0, "#EFF6FF"], [0.3, "#93C5FD"], [1.0, "#1E40AF"]],
                        hoverongaps=False,
                        colorbar=dict(title="N° papers", thickness=14, len=0.8),
                        xgap=2, ygap=2,
                    ))
                    fig_cal.update_layout(
                        height=max(320, len(_yrs) * 26 + 100),
                        plot_bgcolor="#F8FAFC",
                        paper_bgcolor="#F8FAFC",
                        xaxis=dict(side="top", tickfont=dict(size=11)),
                        yaxis=dict(autorange="reversed", tickfont=dict(size=11)),
                        margin=dict(t=50, b=10, l=60, r=10),
                    )
                    st.plotly_chart(fig_cal, use_container_width=True)

            # Nota: papers sin fecha exacta
            _no_date = _pub["publication_date"].isna().sum()
            if _no_date > 0:
                st.caption(f"ℹ {_no_date} papers sin fecha exacta de publicación no aparecen en el calendario.")

            st.divider()

            # ── Lista de publicaciones recientes ────────────────────────────
            sec("Publicaciones recientes")
            _yr_opts = ["Todos"] + sorted(
                _pub["year"].dropna().astype(int).unique().tolist(), reverse=True
            )
            _yr_sel = st.selectbox("Filtrar por año", _yr_opts, key="vt_yr_sel")
            _busq   = st.text_input("Buscar en título", placeholder="ej: plasma, reactor, dosimetry", key="vt_busq")

            _show_pub = _pub.copy()
            if _yr_sel != "Todos":
                _show_pub = _show_pub[_show_pub["year"] == float(_yr_sel)]
            if _busq:
                _show_pub = _show_pub[
                    _show_pub["title"].str.contains(_busq, case=False, na=False)
                ]

            st.caption(f"{len(_show_pub)} publicaciones")
            for _, _row in _show_pub.head(40).iterrows():
                _yr_s  = str(int(_row["year"])) if pd.notna(_row.get("year")) else "?"
                _src_s = str(_row.get("source") or "")[:70]
                _ttl_s = str(_row.get("title") or "Sin título")
                _doi_s = _row.get("doi")
                _c_s   = int(_row.get("cited_by_count", 0)) if pd.notna(_row.get("cited_by_count")) else 0
                _oa_s  = _row.get("is_oa", False)

                with st.expander(f"**{_yr_s}** · {_ttl_s[:90]}"):
                    st.caption(f"🏛 {_src_s}")
                    _meta_cols = st.columns([2, 1, 1])
                    if pd.notna(_doi_s) and _doi_s:
                        _meta_cols[0].markdown(f"[DOI: {_doi_s}](https://doi.org/{_doi_s})")
                    _meta_cols[1].metric("Citaciones", _c_s)
                    if _oa_s:
                        _meta_cols[2].success("OA")

                    # Show abstract if available
                    if not _abs_path.exists():
                        pass
                    else:
                        _abs_df = st.session_state.get("_abs_cache")
                        if _abs_df is None:
                            _abs_df = pd.read_csv(_abs_path, low_memory=False)
                            st.session_state["_abs_cache"] = _abs_df
                        _abs_col = "abstract_best" if "abstract_best" in _abs_df.columns else "abstract"
                        _match = _abs_df[_abs_df["openalex_id"] == _row.get("openalex_id", "")]
                        if not _match.empty and pd.notna(_match.iloc[0].get(_abs_col)):
                            st.caption(_match.iloc[0][_abs_col][:500])

    # ── TAB 2: En la prensa ──────────────────────────────────────────────────
    with _vt_tabs[1]:
        if _news_data.empty:
            st.info("Ejecuta `python3 Scripts/news_monitor.py` para obtener noticias.")
        else:
            _news = _news_data.copy()
            _news["published_dt"] = pd.to_datetime(_news["published"], errors="coerce", utc=True).dt.tz_convert(None)
            _news["title_clean"] = _news.apply(
                lambda r: _clean_news_title(r.get("title", ""), r.get("source_name", "")),
                axis=1,
            )
            _news["snippet_clean"] = _news.apply(
                lambda r: _clean_news_snippet(r.get("snippet", ""), r.get("title", "")),
                axis=1,
            )
            _news = _news.drop_duplicates(subset=["news_id"]).sort_values("published_dt", ascending=False)

            # ── KPIs ───────────────────────────────────────────────────────
            _n_total  = len(_news)
            _n_sci    = (_news["topic_flag"] == "CIENCIA").sum()
            _n_sources = _news["source_name"].nunique()
            _latest_news = str(_news["published_dt"].max().date()) if _news["published_dt"].notna().any() else "—"

            kpi_row(
                kpi("Noticias encontradas", f"{_n_total:,}"),
                kpi("Ciencia / investigación", f"{_n_sci}",
                    f"{100*_n_sci/_n_total:.0f}% del total"),
                kpi("Medios distintos", f"{_n_sources}"),
                kpi("Noticia más reciente", _latest_news),
            )
            st.divider()

            # ── Filtros ────────────────────────────────────────────────────
            _nf1, _nf2, _nf3 = st.columns([1, 1, 2])
            with _nf1:
                _topic_opts = ["Todos"] + sorted(_news["topic_flag"].dropna().unique().tolist())
                _topic_sel  = st.selectbox("Categoría", _topic_opts, key="news_topic")
            with _nf2:
                _src_opts = ["Todos"] + sorted(_news["source_name"].dropna().unique().tolist())
                _src_sel  = st.selectbox("Medio", _src_opts, key="news_src")
            with _nf3:
                _news_q = st.text_input("Buscar en títulos", placeholder="ej: reactor, director, acuerdo", key="news_q")

            _nshow = _news.copy()
            if _topic_sel != "Todos":
                _nshow = _nshow[_nshow["topic_flag"] == _topic_sel]
            if _src_sel != "Todos":
                _nshow = _nshow[_nshow["source_name"] == _src_sel]
            if _news_q:
                _nshow = _nshow[_nshow["title_clean"].str.contains(_news_q, case=False, na=False)]

            st.divider()

            # ── Gráficos ───────────────────────────────────────────────────
            _gc1, _gc2 = st.columns(2)
            with _gc1:
                sec("Noticias por categoría")
                _tc = _news["topic_flag"].value_counts().reset_index()
                _tc.columns = ["Categoría", "N"]
                _topic_colors = {
                    "CIENCIA": BLUE, "POLÍTICA": AMBER,
                    "INSTITUCIONAL": GREEN, "GENERAL": "#94A3B8"
                }
                fig_tc = px.bar(_tc, x="N", y="Categoría", orientation="h",
                                color="Categoría", color_discrete_map=_topic_colors,
                                text="N", height=220)
                fig_tc.update_traces(textposition="outside")
                fig_tc.update_layout(yaxis_title="", showlegend=False,
                                     plot_bgcolor="#F8FAFC", margin=dict(t=5, b=5, l=5, r=30))
                st.plotly_chart(fig_tc, use_container_width=True)

            with _gc2:
                sec("Principales medios")
                _sc = _news["source_name"].value_counts().head(8).reset_index()
                _sc.columns = ["Medio", "N"]
                fig_sc = px.bar(_sc.sort_values("N"), x="N", y="Medio", orientation="h",
                                color_discrete_sequence=[BLUE], text="N", height=220)
                fig_sc.update_traces(textposition="outside")
                fig_sc.update_layout(yaxis_title="", plot_bgcolor="#F8FAFC",
                                     margin=dict(t=5, b=5, l=5, r=30))
                st.plotly_chart(fig_sc, use_container_width=True)

            # Línea de tiempo mensual
            _news_ts = _news.copy()
            _news_ts["ym"] = _news_ts["published_dt"].dt.to_period("M").astype(str)
            _ts = _news_ts.groupby("ym").size().reset_index(name="n").sort_values("ym")
            if len(_ts) > 1:
                st.divider()
                sec("Menciones por mes")
                fig_ts = px.bar(_ts, x="ym", y="n",
                                color_discrete_sequence=[BLUE],
                                labels={"ym": "", "n": "Noticias"},
                                height=200)
                fig_ts.update_layout(plot_bgcolor="#F8FAFC", margin=dict(t=5, b=5))
                st.plotly_chart(fig_ts, use_container_width=True)

            st.divider()

            # ── Lista de noticias ──────────────────────────────────────────
            sec(f"Noticias ({len(_nshow)})")
            _TOPIC_BADGE = {
                "CIENCIA": "🔬", "POLÍTICA": "🏛",
                "INSTITUCIONAL": "🏢", "GENERAL": "📰"
            }
            for _, _nrow in _nshow.head(50).iterrows():
                _badge  = _TOPIC_BADGE.get(_nrow.get("topic_flag", ""), "📰")
                _nt     = _clean_news_title(_nrow.get("title_clean", ""), _nrow.get("source_name", ""))
                _nsrc   = _clean_html_text(_nrow.get("source_name", ""))
                _ndate  = _nrow["published_dt"].strftime("%d %b %Y") \
                          if pd.notna(_nrow.get("published_dt")) else ""
                _nsnip  = _clean_news_snippet(_nrow.get("snippet_clean", ""), _nt)
                _nlink  = str(_nrow.get("link", ""))

                with st.expander(f"{_badge} **{_nsrc}** · {_nt[:96]}"):
                    st.caption(
                        f"📅 {_ndate}  ·  🏷 {_clean_html_text(_nrow.get('topic_flag', ''))}  ·  "
                        f"🔍 {_clean_html_text(_nrow.get('query_label', ''))}"
                    )
                    if _nsnip:
                        st.write(_nsnip[:350])
                    if _nlink:
                        st.link_button("Leer noticia completa →", _nlink, use_container_width=False)

            st.divider()
            st.download_button("Exportar noticias CSV", make_csv(_news),
                               "cchen_noticias.csv", "text/csv")

    # ── TAB 3: Boletín Semanal ───────────────────────────────────────────────
    with _vt_tabs[2]:
        _bol_dir = BASE / "Boletines"
        _bol_dir.mkdir(parents=True, exist_ok=True)

        st.markdown("### Generador de Boletín Científico Semanal")
        st.caption(
            "Compila automáticamente las noticias de prensa, papers del entorno y "
            "publicaciones CCHEN de la semana en un HTML listo para enviar por correo."
        )
        st.divider()

        _bc1, _bc2 = st.columns([1, 2])
        with _bc1:
            _bol_weeks = st.slider("Semanas a incluir", 1, 4, 1,
                                   key="vt_bol_weeks", help="Cuántas semanas hacia atrás cubrir")
        with _bc2:
            _bol_npub = st.slider("N° publicaciones CCHEN recientes", 3, 10, 5, key="vt_bol_npub")

        if st.button("⚡ Generar boletín ahora", type="primary", use_container_width=True):
            with st.spinner("Generando boletín..."):
                _bol_script = BASE.parent / "Scripts" / "generar_boletin.py"
                _now = _dtlib.datetime.now()
                _yr, _wk, _ = _now.isocalendar()
                _out = _bol_dir / f"boletin_{_yr}-S{_wk:02d}.html"
                result = subprocess.run(
                    [sys.executable, str(_bol_script),
                     "--weeks", str(_bol_weeks),
                     "--output", str(_out)],
                    capture_output=True, text=True
                )
            if _out.exists():
                st.success(f"Boletín generado: {_out.name}")
            else:
                st.error("Error al generar el boletín.")
                if result.stderr:
                    st.code(result.stderr[:500])

        st.divider()

        # Lista de boletines existentes
        _boletines = sorted(_bol_dir.glob("boletin_*.html"), reverse=True)
        if not _boletines:
            st.info("Aún no hay boletines generados. Haz clic en el botón de arriba.")
        else:
            sec(f"Boletines disponibles ({len(_boletines)})")
            for _bf in _boletines:
                _html_bytes = _bf.read_bytes()
                _size_kb    = len(_html_bytes) / 1024
                _mtime      = _dtlib.datetime.fromtimestamp(_bf.stat().st_mtime)
                _bc_a, _bc_b, _bc_c = st.columns([2, 1, 1])
                _bc_a.markdown(f"**{_bf.stem}**  \n_{_mtime.strftime('%d %b %Y %H:%M')}_")
                _bc_b.caption(f"{_size_kb:.1f} KB")
                _bc_c.download_button(
                    "⬇ Descargar",
                    data=_html_bytes,
                    file_name=_bf.name,
                    mime="text/html",
                    key=f"dl_{_bf.stem}",
                    use_container_width=True,
                )

            # Preview del boletín más reciente
            st.divider()
            sec("Vista previa — boletín más reciente")
            _latest_bol = _boletines[0]
            _html_content = _latest_bol.read_text(encoding="utf-8")
            st.components.v1.html(_html_content, height=700, scrolling=True)

    # ── TAB 4: Monitor entorno arXiv ─────────────────────────────────────────
    with _vt_tabs[3]:
        if _arxiv_data.empty:
            st.info(
                "Aún no hay datos de monitoreo arXiv. "
                "Ejecuta `python3 Scripts/arxiv_monitor.py` para la primera captura."
            )
        else:
            _arxiv = _arxiv_data.copy()
            _arxiv["fetched_at"] = pd.to_datetime(_arxiv["fetched_at"], errors="coerce")

            kpi_row(
                kpi("Papers monitoreados", f"{len(_arxiv):,}"),
                kpi("Alta relevancia", f"{(_arxiv['relevance_flag']=='ALTA').sum()}",
                    "keywords nucleares directas"),
                kpi("Áreas cubiertas", f"{_arxiv['feed_area'].nunique()}"),
                kpi("Última captura",
                    str(_arxiv["fetched_at"].max().date()) if _arxiv["fetched_at"].notna().any() else "—"),
            )
            st.divider()

            vc1, vc2 = st.columns(2)
            with vc1:
                sec("Papers por área temática")
                _area_c = _arxiv["feed_area"].value_counts().reset_index()
                _area_c.columns = ["Área", "N"]
                fig_area = px.bar(_area_c, x="N", y="Área", orientation="h",
                                  color_discrete_sequence=[BLUE], text="N", height=280)
                fig_area.update_traces(textposition="outside")
                fig_area.update_layout(yaxis_title="", plot_bgcolor="#F8FAFC",
                                       margin=dict(t=5, b=5, l=5, r=30))
                st.plotly_chart(fig_area, use_container_width=True)

            with vc2:
                sec("Relevancia para CCHEN")
                _rel_c = _arxiv["relevance_flag"].value_counts().reset_index()
                _rel_c.columns = ["Relevancia", "N"]
                _colors_rel = {"ALTA": RED, "MEDIA": AMBER, "BAJA": GREEN}
                fig_rel = px.pie(_rel_c, names="Relevancia", values="N",
                                 color="Relevancia",
                                 color_discrete_map=_colors_rel, height=280)
                fig_rel.update_traces(textposition="inside", textinfo="percent+label")
                fig_rel.update_layout(margin=dict(t=5, b=5))
                st.plotly_chart(fig_rel, use_container_width=True)

            st.divider()
            sec("Papers de alta relevancia")
            _high = _arxiv[_arxiv["relevance_flag"] == "ALTA"].sort_values("fetched_at", ascending=False)
            if _high.empty:
                st.info("No hay papers de alta relevancia en el registro actual.")
            else:
                for _, row in _high.head(20).iterrows():
                    with st.expander(f"[{row['feed_area']}] {row['title'][:90]}"):
                        st.markdown(f"**Área:** {row['feed_area']}  ·  **Fecha:** {row.get('fetched_at', '')}")
                        if row.get("keywords_found"):
                            st.markdown(f"**Keywords:** `{row['keywords_found']}`")
                        if row.get("abstract_short"):
                            st.caption(row["abstract_short"][:500])
                        if row.get("link"):
                            st.markdown(f"[Ver en arXiv →]({row['link']})")

            st.divider()
            st.download_button("Exportar monitor arXiv CSV", make_csv(_arxiv),
                               "arxiv_monitor_cchen.csv", "text/csv")

    # ── TAB 5: Monitor IAEA INIS ──────────────────────────────────────────────
    with _vt_tabs[4]:
        _inis_df = _iaea_data.copy() if not _iaea_data.empty else _iaea_data
        if _inis_df.empty:
            st.info(
                "Aún no hay datos de monitoreo IAEA INIS. "
                "Ejecuta `python3 Scripts/iaea_inis_monitor.py` para la primera captura."
            )
        else:
            if "fetched_at" in _inis_df.columns:
                _inis_df["fetched_at"] = pd.to_datetime(_inis_df["fetched_at"], errors="coerce")
            kpi_row(
                kpi("Documentos INIS", f"{len(_inis_df):,}", "literatura nuclear especializada"),
                kpi("Alta relevancia", f"{(_inis_df.get('relevance_flag', '') == 'ALTA').sum()}",
                    "match con keywords CCHEN"),
                kpi("Áreas cubiertas",
                    f"{_inis_df['subject_area'].nunique() if 'subject_area' in _inis_df.columns else '—'}"),
                kpi("Última captura",
                    str(_inis_df["fetched_at"].max().date())
                    if "fetched_at" in _inis_df.columns and _inis_df["fetched_at"].notna().any() else "—"),
            )
            st.divider()

            _ic1, _ic2 = st.columns(2)
            with _ic1:
                if "subject_area" in _inis_df.columns:
                    sec("Documentos por área temática INIS")
                    _inis_area = _inis_df["subject_area"].value_counts().reset_index()
                    _inis_area.columns = ["Área", "N"]
                    fig_ia = px.bar(_inis_area, x="N", y="Área", orientation="h",
                                    color_discrete_sequence=[BLUE], text="N", height=320)
                    fig_ia.update_traces(textposition="outside")
                    fig_ia.update_layout(yaxis_title="", plot_bgcolor="#F8FAFC",
                                         margin=dict(t=5, b=5, l=5, r=30))
                    st.plotly_chart(fig_ia, use_container_width=True)

            with _ic2:
                if "relevance_flag" in _inis_df.columns:
                    sec("Relevancia para CCHEN")
                    _inis_rel = _inis_df["relevance_flag"].value_counts().reset_index()
                    _inis_rel.columns = ["Relevancia", "N"]
                    _colors_rel_inis = {"ALTA": RED, "MEDIA": AMBER, "BAJA": GREEN}
                    fig_ir = px.pie(_inis_rel, names="Relevancia", values="N",
                                    color="Relevancia",
                                    color_discrete_map=_colors_rel_inis, height=320)
                    fig_ir.update_traces(textposition="inside", textinfo="percent+label")
                    fig_ir.update_layout(margin=dict(t=5, b=5))
                    st.plotly_chart(fig_ir, use_container_width=True)

            st.divider()
            sec("Documentos INIS de alta relevancia para CCHEN")
            _inis_high = (
                _inis_df[_inis_df["relevance_flag"] == "ALTA"]
                if "relevance_flag" in _inis_df.columns
                else _inis_df.head(20)
            )
            if _inis_high.empty:
                st.info("No hay documentos de alta relevancia en el registro actual.")
            else:
                for _, _irow in _inis_high.head(25).iterrows():
                    with st.expander(f"[{_irow.get('subject_area', '')}] {str(_irow.get('title', ''))[:90]}"):
                        st.markdown(f"**Área:** {_irow.get('subject_area', '')}  ·  **Publicado:** {_irow.get('published', '')}")
                        if _irow.get("keywords_found"):
                            st.markdown(f"**Keywords:** `{_irow['keywords_found']}`")
                        if _irow.get("abstract_short"):
                            st.caption(str(_irow["abstract_short"])[:500])
                        if _irow.get("source_type"):
                            st.caption(f"Tipo: {_irow['source_type']}")
                        if _irow.get("link"):
                            st.markdown(f"[Ver en IAEA INIS →]({_irow['link']})")
            st.divider()
            st.download_button("Exportar monitor IAEA INIS CSV", make_csv(_inis_df),
                               "iaea_inis_monitor_cchen.csv", "text/csv")

    # ── TAB 6: Temas de Investigación (BERTopic) ─────────────────────────────
    with _vt_tabs[5]:
        _bt_info_path = _VT_BASE / "cchen_bertopic_topic_info.csv"
        _bt_docs_path = _VT_BASE / "cchen_bertopic_topics.csv"
        _bt_viz_path  = BASE.parent / "Notebooks" / "analysis"

        if not _bt_info_path.exists():
            st.info("Ejecuta `python3 Scripts/run_bertopic.py` para generar el análisis de temas.")
        else:
            _bt_info = pd.read_csv(_bt_info_path)
            _bt_docs = pd.read_csv(_bt_docs_path) if _bt_docs_path.exists() else pd.DataFrame()
            _bt_real = _bt_info[_bt_info["Topic"] != -1]

            kpi_row(
                kpi("Temas identificados", f"{len(_bt_real)}"),
                kpi("Papers analizados",   f"{len(_bt_docs):,}" if not _bt_docs.empty else "—"),
                kpi("Outliers",
                    f"{(_bt_docs['topic_id'] == -1).sum()}" if not _bt_docs.empty and 'topic_id' in _bt_docs.columns else "—",
                    "sin tema asignado"),
            )
            st.divider()

            sec("Distribución de papers por tema")
            _bt_plot = _bt_real.sort_values("Count", ascending=False).head(20).copy()
            _bt_plot["label"] = _bt_plot.apply(
                lambda r: _build_topic_label(r.get("Topic"), r.get("Name", ""), r.get("Representation", ""), max_terms=3),
                axis=1,
            )
            fig_bt = px.bar(_bt_plot.sort_values("Count"), x="Count", y="label",
                            orientation="h", color_discrete_sequence=[BLUE],
                            text="Count", height=max(420, len(_bt_plot) * 34))
            fig_bt.update_traces(textposition="outside")
            fig_bt.update_layout(yaxis_title="", plot_bgcolor="#F8FAFC",
                                 margin=dict(t=5, b=5, l=5, r=30))
            st.plotly_chart(fig_bt, use_container_width=True)

            with st.expander("Ver términos representativos por tema"):
                _topic_terms = _bt_real.copy()
                _topic_terms["Tema"] = _topic_terms.apply(
                    lambda r: _build_topic_label(r.get("Topic"), r.get("Name", ""), r.get("Representation", ""), max_terms=4),
                    axis=1,
                )
                _topic_terms["Términos representativos"] = _topic_terms["Representation"].apply(_topic_terms_preview)
                st.dataframe(
                    _topic_terms[["Tema", "Count", "Términos representativos"]].rename(columns={"Count": "Papers"}),
                    use_container_width=True,
                    hide_index=True,
                    height=320,
                )

            # Visualizaciones interactivas guardadas
            _html_files = list(_bt_viz_path.glob("bertopic_*.html")) if _bt_viz_path.exists() else []
            if _html_files:
                st.divider()
                sec("Visualizaciones interactivas")
                st.caption("Abre estos archivos en tu navegador para explorarlos:")
                for hf in sorted(_html_files):
                    st.markdown(f"- [{hf.name}](Notebooks/analysis/{hf.name})")

            if not _bt_docs.empty and "topic_id" in _bt_docs.columns:
                st.divider()
                sec("Papers por tema — tabla detallada")
                _tema_sel = st.selectbox(
                    "Seleccionar tema",
                    sorted(_bt_real["Topic"].tolist()),
                    format_func=lambda t: (
                        f"{_build_topic_label(t, _bt_real[_bt_real['Topic']==t]['Name'].iloc[0], _bt_real[_bt_real['Topic']==t]['Representation'].iloc[0], max_terms=3)} "
                        f"({int(_bt_real[_bt_real['Topic']==t]['Count'].values[0])} papers)"
                    ) if t in _bt_real["Topic"].values else f"Tema {t}",
                )
                _tema_papers = (
                    _bt_docs[_bt_docs["topic_id"] == _tema_sel][["title", "year", "abstract_best"]].rename(
                        columns={"abstract_best": "abstract"}
                    )
                    if "abstract_best" in _bt_docs.columns
                    else _bt_docs[_bt_docs["topic_id"] == _tema_sel][["title", "year"]]
                )
                st.dataframe(_tema_papers, use_container_width=True, hide_index=True, height=300)
