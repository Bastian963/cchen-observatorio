"""Section: Producción Científica — CCHEN Observatorio"""
import math
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from .shared import (
    BLUE, RED, GREEN, AMBER, PURPLE, PALETTE,
    kpi, kpi_row, sec, make_csv, calc_hindex, _ISO2_ISO3,
)


def render(ctx: dict) -> None:
    """Render the Producción Científica section."""
    pub      = ctx["pub"]
    pub_enr  = ctx["pub_enr"]
    auth     = ctx["auth"]
    dian     = ctx["dian"]
    concepts = ctx["concepts"]
    orcid    = ctx["orcid"]
    unpaywall = ctx["unpaywall"]
    europmc  = ctx.get("europmc", __import__("pandas").DataFrame())

    from data_loader import BASE

    st.title("Producción Científica CCHEN")
    st.caption("Fuente: OpenAlex · 877 trabajos · Indicadores bibliométricos I+D")
    st.divider()

    # Calcular áreas únicas para el filtro
    _all_areas = sorted(set(
        a.strip()
        for row in pub_enr["areas"].dropna()
        for a in str(row).split(";")
        if a.strip()
    ))

    with st.expander("Filtros", expanded=True):
        fc1,fc2,fc3,fc4 = st.columns(4)
        with fc1:
            yr_range = st.slider("Período", 1990, 2026, (2000, 2025), key="pc_yr_range")
        with fc2:
            tipos = ["Todos"] + sorted(pub["type"].dropna().unique().tolist())
            tipo_sel = st.selectbox("Tipo publicación", tipos)
        with fc3:
            oa_sel = st.selectbox("Acceso Abierto", ["Todos","Sí","No"])
        with fc4:
            busqueda = st.text_input("🔎 Buscar título / tema", placeholder="ej: plasma, fusión, reactor")
        area_sel = st.multiselect("🏷️ Filtrar por área temática", _all_areas,
                                  help="Las áreas provienen de Scimago/SJR vía OpenAlex")

    df = pub[pub["year"].between(*yr_range)].copy()
    if tipo_sel != "Todos":  df = df[df["type"] == tipo_sel]
    if oa_sel == "Sí":       df = df[df["is_oa"] == True]
    elif oa_sel == "No":     df = df[df["is_oa"] == False]
    if busqueda:             df = df[df["title"].str.contains(busqueda, case=False, na=False)]

    df_enr = pub_enr[pub_enr["year_num"].between(*yr_range)].copy()
    if area_sel:
        mask_area = df_enr["areas"].apply(
            lambda x: any(a in str(x).split(";") or a in [s.strip() for s in str(x).split(";")]
                         for a in area_sel) if pd.notna(x) else False
        )
        df_enr = df_enr[mask_area]
        if "doi" in df.columns and "doi" in df_enr.columns:
            df = df[df["doi"].isin(df_enr["doi"].dropna())]

    # KPIs
    n_q1q2  = len(df_enr[df_enr["quartile"].isin(["Q1","Q2"])])
    n_q_tot = len(df_enr[df_enr["quartile"].notna()])
    pct_q   = round(100*n_q1q2/n_q_tot, 1) if n_q_tot > 0 else 0
    pct_collab = round(100*df_enr["has_international_collab"].mean(), 1) if len(df_enr) > 0 else 0
    _hindex_inst = calc_hindex(df["cited_by_count"])

    kpi_row(
        kpi("Papers", f"{len(df):,}"),
        kpi("Citas totales", f"{int(df['cited_by_count'].sum()):,}"),
        kpi("Citas / paper", f"{df['cited_by_count'].mean():.1f}"),
        kpi("H-index CCHEN", f"{_hindex_inst}", "índice Hirsch institucional"),
    )
    # KPI: papers con PDF libre (Unpaywall)
    _n_pdf = 0
    _pct_pdf = 0.0
    if not unpaywall.empty and "doi" in unpaywall.columns:
        _uw_doi = unpaywall["doi"].dropna()
        _df_with_doi = df["doi"].dropna()
        _matched_uw = unpaywall[unpaywall["doi"].isin(_df_with_doi)]
        _has_pdf = _matched_uw["oa_pdf_url"].fillna("").str.startswith("http") if "oa_pdf_url" in _matched_uw.columns else pd.Series([], dtype=bool)
        _has_oa_url = _matched_uw["oa_url"].fillna("").str.startswith("http") if "oa_url" in _matched_uw.columns else pd.Series([], dtype=bool)
        _n_pdf = int((_has_pdf | _has_oa_url).sum())
        _pct_pdf = 100 * _n_pdf / len(df) if len(df) > 0 else 0.0

    kpi_row(
        kpi("% Q1+Q2", f"{pct_q}%", f"{n_q1q2} de {n_q_tot} con cuartil"),
        kpi("% Acceso Abierto", f"{100*df['is_oa'].mean():.0f}%"),
        kpi("% Collab. Intl.", f"{pct_collab}%", "papers enriquecidos"),
        kpi("PDF libre", f"{_n_pdf}", f"{_pct_pdf:.0f}% de papers con PDF/OA"),
    )

    col1, col2 = st.columns(2)

    with col1:
        sec("Papers y citas por año")
        by_yr = df.groupby("year").agg(Papers=("openalex_id","count"), Citas=("cited_by_count","sum")).reset_index()
        fig = go.Figure()
        fig.add_bar(x=by_yr["year"], y=by_yr["Papers"], name="Papers", marker_color=BLUE)
        fig.add_scatter(x=by_yr["year"], y=by_yr["Citas"], name="Citas",
                        mode="lines+markers", marker_color=RED, yaxis="y2")
        fig.update_layout(yaxis=dict(title="Papers"), yaxis2=dict(title="Citas", overlaying="y", side="right"),
                          legend=dict(orientation="h", y=1.1), margin=dict(t=10,b=30,l=40,r=60), height=330)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        sec("Tendencia Q1-Q2 por año")
        q12 = df_enr[df_enr["quartile"].isin(["Q1","Q2"])].groupby("year_num").size().reset_index(name="Q1+Q2")
        qtot = df_enr[df_enr["quartile"].notna()].groupby("year_num").size().reset_index(name="Total_Q")
        qt = q12.merge(qtot, on="year_num")
        qt["pct_Q1Q2"] = 100 * qt["Q1+Q2"] / qt["Total_Q"]
        fig2 = go.Figure()
        fig2.add_bar(x=qt["year_num"], y=qt["Q1+Q2"], name="Papers Q1+Q2", marker_color=BLUE)
        fig2.add_scatter(x=qt["year_num"], y=qt["pct_Q1Q2"], name="% Q1+Q2",
                         mode="lines+markers", marker_color=GREEN, yaxis="y2")
        fig2.update_layout(yaxis=dict(title="N° papers"), yaxis2=dict(title="%", overlaying="y", side="right"),
                           legend=dict(orientation="h", y=1.1), margin=dict(t=10,b=30,l=40,r=60), height=330)
        st.plotly_chart(fig2, use_container_width=True)

    col3, col4 = st.columns(2)

    with col3:
        sec("Distribución por cuartil SJR")
        q_f = df_enr["quartile"].value_counts().reset_index()
        q_f.columns = ["Cuartil","N"]
        q_f["Cuartil"] = pd.Categorical(q_f["Cuartil"],["Q1","Q2","Q3","Q4"],ordered=True)
        q_f = q_f.sort_values("Cuartil")
        fig3 = px.bar(q_f, x="Cuartil", y="N", text="N",
                      color="Cuartil", color_discrete_map={"Q1":BLUE,"Q2":GREEN,"Q3":AMBER,"Q4":RED},
                      height=280)
        fig3.update_traces(textposition="outside")
        fig3.update_layout(showlegend=False, margin=dict(t=10,b=30))
        st.plotly_chart(fig3, use_container_width=True)

    with col4:
        sec("Colaboración internacional vs. solo CCHEN")
        cats = pd.DataFrame({
            "Tipo": ["Solo CCHEN", "Collab. nacional", "Collab. internacional"],
            "N": [
                len(df_enr[~df_enr["has_outside_cchen_collab"]]),
                len(df_enr[df_enr["has_outside_cchen_collab"] & ~df_enr["has_international_collab"]]),
                len(df_enr[df_enr["has_international_collab"]]),
            ]
        })
        fig4 = px.pie(cats, names="Tipo", values="N",
                      color_discrete_map={"Solo CCHEN":BLUE,"Collab. nacional":GREEN,"Collab. internacional":RED},
                      height=280)
        fig4.update_traces(textposition="inside", textinfo="percent+label")
        fig4.update_layout(margin=dict(t=10,b=10))
        st.plotly_chart(fig4, use_container_width=True)

    # ── OA breakdown + H-index por investigador ──────────────────────────────
    col_oa, col_hinv = st.columns(2)

    with col_oa:
        sec("Acceso Abierto por tipo (OA status)")
        if "oa_status" in df_enr.columns:
            oa_counts = df_enr["oa_status"].fillna("closed").value_counts().reset_index()
            oa_counts.columns = ["Tipo OA", "N"]
            oa_color_map = {
                "gold": "#F4A60D", "green": "#00A896", "bronze": "#CD7F32",
                "hybrid": "#7B2D8B", "diamond": "#003B6F", "closed": "#CCCCCC",
            }
            fig_oa = px.pie(
                oa_counts, names="Tipo OA", values="N",
                color="Tipo OA", color_discrete_map=oa_color_map,
                height=300,
            )
            fig_oa.update_traces(textposition="inside", textinfo="percent+label")
            fig_oa.update_layout(margin=dict(t=10, b=10), showlegend=True,
                                 legend=dict(orientation="h", y=-0.15))
            st.plotly_chart(fig_oa, use_container_width=True)
        else:
            st.info("Campo oa_status no disponible en este dataset.")
        # Unpaywall enrichment note
        if not unpaywall.empty and "is_oa" in unpaywall.columns:
            _uw_oa = unpaywall["is_oa"].sum()
            _uw_total = len(unpaywall)
            _uw_green = (unpaywall["oa_status"] == "green").sum() if "oa_status" in unpaywall.columns else 0
            st.caption(
                f"Unpaywall ({_uw_total} DOIs verificados): "
                f"{_uw_oa} con copia OA · {_uw_green} green OA (repositorio)"
            )

    with col_hinv:
        sec("H-index por investigador CCHEN (top 15)")
        _auth_c = auth[auth["is_cchen_affiliation"] == True]
        _pub_cites = pub[["openalex_id", "cited_by_count"]].rename(columns={"openalex_id": "work_id"})
        _auth_cites = _auth_c.merge(_pub_cites, on="work_id", how="left")
        def _hindex_group(g):
            return calc_hindex(g["cited_by_count"])
        _hinv_df = (_auth_cites.groupby("author_name")
                    .apply(_hindex_group, include_groups=False)
                    .reset_index()
                    .rename(columns={0: "H-index"})
                    .sort_values("H-index", ascending=False)
                    .head(15))
        fig_hinv = px.bar(
            _hinv_df.sort_values("H-index"), x="H-index", y="author_name",
            orientation="h", color_discrete_sequence=[GREEN], text="H-index",
            height=300, labels={"author_name": ""},
        )
        fig_hinv.update_layout(showlegend=False, margin=dict(t=10, b=10))
        st.plotly_chart(fig_hinv, use_container_width=True)

    # ── Mapa de colaboración internacional ────────────────────────────────────
    sec("Mapa de colaboración internacional")
    _collab_ext = auth[auth["is_cchen_affiliation"] == False].copy()
    _collab_ext["iso3"] = _collab_ext["institution_country_code"].map(_ISO2_ISO3)
    _country_cnt = (
        _collab_ext[_collab_ext["iso3"].notna()]
        .groupby(["iso3", "institution_country_code"])["work_id"]
        .nunique().reset_index()
        .rename(columns={"work_id": "Papers", "institution_country_code": "iso2"})
        .sort_values("Papers", ascending=False)
    )
    if not _country_cnt.empty:
        fig_map = px.choropleth(
            _country_cnt, locations="iso3", color="Papers",
            hover_name="iso3", hover_data={"Papers": True, "iso3": False},
            color_continuous_scale=[[0, "#D6E4F0"], [0.4, "#5B9BD5"], [1, "#003B6F"]],
            projection="natural earth", height=380,
        )
        fig_map.update_layout(
            margin=dict(t=0, b=0, l=0, r=0),
            coloraxis_colorbar=dict(title="Papers", len=0.6),
            geo=dict(showframe=False, showcoastlines=True, coastlinecolor="#CCCCCC"),
        )
        fig_map.add_scattergeo(
            locations=["CHL"], locationmode="ISO-3",
            marker=dict(size=8, color=RED, symbol="star"),
            hoverinfo="text", text=["CCHEN (Chile)"], showlegend=False,
        )
        st.plotly_chart(fig_map, use_container_width=True)
        _top10_paises = _country_cnt.head(10)
        st.caption(f"Top 10 países: " + " · ".join(
            f"{r.iso2} ({r.Papers})" for _, r in _top10_paises.iterrows()
        ))
    else:
        st.info("Sin datos de países colaboradores para el filtro seleccionado.")

    col5, col6 = st.columns(2)

    with col5:
        sec("Top 10 journals / fuentes")
        top_j = df["source"].value_counts().head(10).reset_index()
        top_j.columns = ["Journal","N"]
        fig5 = px.bar(top_j.sort_values("N"), x="N", y="Journal", orientation="h",
                      color_discrete_sequence=[BLUE], text="N", height=300)
        fig5.update_layout(showlegend=False, margin=dict(t=10,b=10))
        st.plotly_chart(fig5, use_container_width=True)

    with col6:
        sec("Áreas temáticas (papers con cuartil)")
        areas_raw = df_enr["areas"].dropna()
        area_counts = {}
        for a in areas_raw:
            for item in str(a).split(";"):
                item = item.strip()
                if item:
                    area_counts[item] = area_counts.get(item, 0) + 1
        area_df = pd.DataFrame(list(area_counts.items()), columns=["Área","N"]).sort_values("N", ascending=False).head(10)
        fig6 = px.bar(area_df.sort_values("N"), x="N", y="Área", orientation="h",
                      color_discrete_sequence=[GREEN], text="N", height=300)
        fig6.update_layout(showlegend=False, margin=dict(t=10,b=10))
        st.plotly_chart(fig6, use_container_width=True)

    # Top investigadores CCHEN
    sec("🔬 Top investigadores CCHEN por producción (afiliación verificada OpenAlex)")
    _auth_f = auth[auth["is_cchen_affiliation"] == True]
    if area_sel and "doi" in auth.columns:
        _auth_f = _auth_f[_auth_f["doi"].isin(df["doi"].dropna())] if "doi" in df.columns else _auth_f
    _top_inv_df = (_auth_f.groupby("author_name")["work_id"]
                   .nunique().sort_values(ascending=False).head(15)
                   .reset_index().rename(columns={"author_name": "Investigador/a", "work_id": "Papers"}))
    fig_inv = px.bar(_top_inv_df.sort_values("Papers"), x="Papers", y="Investigador/a",
                     orientation="h", color_discrete_sequence=[BLUE], text="Papers",
                     height=400, labels={"Papers": "N° papers"})
    fig_inv.update_layout(showlegend=False, margin=dict(t=10, b=10))
    st.plotly_chart(fig_inv, use_container_width=True)

    # Tabla
    sec(f"Tabla de publicaciones — {len(df)} resultados")

    def _pub_url(row):
        oid = str(row.get("openalex_id", "") or "")
        if oid.startswith("http"):
            return oid
        doi = str(row.get("doi", "") or "")
        if doi.startswith("10."):
            return f"https://doi.org/{doi}"
        oa = str(row.get("oa_url", "") or "")
        if oa.startswith("http"):
            return oa
        return None

    _url_col = df.apply(_pub_url, axis=1)
    df_show = df[["year","title","type","source","cited_by_count","is_oa","doi"]].copy()
    df_show["Enlace"] = _url_col.values

    if not unpaywall.empty and "doi" in unpaywall.columns:
        _uw_cols = ["doi"]
        if "oa_pdf_url" in unpaywall.columns:
            _uw_cols.append("oa_pdf_url")
        if "oa_url" in unpaywall.columns:
            _uw_cols.append("oa_url")
        _uw_merge = unpaywall[_uw_cols].dropna(subset=["doi"]).copy()
        df_show = df_show.merge(_uw_merge, on="doi", how="left")
        _pdf_series = df_show["oa_pdf_url"].where(
            df_show["oa_pdf_url"].fillna("").str.startswith("http"), other=None
        ) if "oa_pdf_url" in df_show.columns else pd.Series([None] * len(df_show), dtype=object)
        _oa_series = df_show["oa_url"].where(
            df_show["oa_url"].fillna("").str.startswith("http"), other=None
        ) if "oa_url" in df_show.columns else pd.Series([None] * len(df_show), dtype=object)
        df_show["pdf_link"] = _pdf_series.combine_first(_oa_series)
        _drop_cols = [c for c in ["oa_pdf_url", "oa_url"] if c in df_show.columns]
        if _drop_cols:
            df_show = df_show.drop(columns=_drop_cols)
    else:
        df_show["pdf_link"] = None

    df_show = df_show.drop(columns=["doi"]).rename(columns={
        "year":"Año","title":"Título","type":"Tipo","source":"Journal",
        "cited_by_count":"Citas","is_oa":"OA",
    }).sort_values("Año", ascending=False)

    st.dataframe(df_show, use_container_width=True, height=400,
                 column_config={
                     "OA": st.column_config.CheckboxColumn("OA"),
                     "Enlace": st.column_config.LinkColumn("Enlace", display_text="🔗"),
                     "pdf_link": st.column_config.LinkColumn("PDF/OA", display_text="🔓 PDF"),
                 })
    st.download_button("Exportar publicaciones CSV", make_csv(df_show),
                       "publicaciones_cchen.csv", "text/csv")

    # ── Red de co-autoría ─────────────────────────────────────────────────────
    with st.expander("Red de co-autoría CCHEN (top 25 investigadores)", expanded=False):
        _TOP_N = 25
        _cchen_a = auth[auth["is_cchen_affiliation"] == True]
        _top_nodes = (_cchen_a.groupby("author_name")["work_id"]
                      .nunique().sort_values(ascending=False).head(_TOP_N).index.tolist())
        _by_paper = (_cchen_a[_cchen_a["author_name"].isin(_top_nodes)]
                     .groupby("work_id")["author_name"].apply(list))
        _edges: dict = {}
        for _pauthors in _by_paper:
            if len(_pauthors) > 1:
                for _i in range(len(_pauthors)):
                    for _j in range(_i + 1, len(_pauthors)):
                        _e = tuple(sorted([_pauthors[_i], _pauthors[_j]]))
                        _edges[_e] = _edges.get(_e, 0) + 1

        _paper_cnt = (_cchen_a[_cchen_a["author_name"].isin(_top_nodes)]
                      .groupby("author_name")["work_id"].nunique())

        _n = len(_top_nodes)
        import math as _math
        _pos = {nd: (_math.cos(2*_math.pi*i/_n), _math.sin(2*_math.pi*i/_n))
                for i, nd in enumerate(_top_nodes)}

        _fig_net = go.Figure()
        _max_w = max(_edges.values()) if _edges else 1
        for (_a, _b), _w in _edges.items():
            _x0, _y0 = _pos[_a]; _x1, _y1 = _pos[_b]
            _fig_net.add_trace(go.Scatter(
                x=[_x0, _x1, None], y=[_y0, _y1, None], mode="lines",
                line=dict(width=max(0.5, 3 * _w / _max_w), color=f"rgba(0,59,111,{0.15 + 0.5*_w/_max_w})"),
                hoverinfo="none", showlegend=False,
            ))
        _xn = [_pos[n][0] for n in _top_nodes]
        _yn = [_pos[n][1] for n in _top_nodes]
        _sz = [max(10, _paper_cnt.get(n, 1) * 0.8) for n in _top_nodes]
        _fig_net.add_trace(go.Scatter(
            x=_xn, y=_yn, mode="markers+text",
            text=[n.split()[-1] for n in _top_nodes],
            textposition="top center", textfont=dict(size=9),
            marker=dict(size=_sz, color=BLUE, line=dict(width=1.5, color="white"), opacity=0.9),
            hovertext=[f"{n}: {_paper_cnt.get(n,0)} papers" for n in _top_nodes],
            hoverinfo="text", showlegend=False,
        ))
        _fig_net.update_layout(
            height=480, showlegend=False,
            xaxis=dict(visible=False, range=[-1.35, 1.35]),
            yaxis=dict(visible=False, range=[-1.35, 1.35]),
            margin=dict(t=10, b=10, l=10, r=10),
            plot_bgcolor="white",
        )
        st.plotly_chart(_fig_net, use_container_width=True)
        if _edges:
            st.caption(f"{len(_edges)} pares de co-autoría detectados entre los top {_TOP_N} investigadores CCHEN. "
                       f"Grosor del enlace = frecuencia de co-autoría.")
        else:
            st.info("No se detectaron co-autorías entre los investigadores seleccionados.")

    # ── Mapa de áreas temáticas (concepts) ───────────────────────────────────
    if not concepts.empty:
        with st.expander("Mapa de áreas temáticas — OpenAlex Concepts", expanded=False):
            sec("Distribución temática de la producción CCHEN")
            top_concepts = (
                concepts[concepts["concept_level"].between(0, 1)]
                .groupby("concept_name")["work_id"]
                .nunique()
                .sort_values(ascending=False)
                .head(20)
                .reset_index()
            )
            top_concepts.columns = ["Área", "Papers"]
            fig_concepts = px.treemap(
                top_concepts, path=["Área"], values="Papers",
                color="Papers",
                color_continuous_scale=[[0, "#EEF4FF"], [1, BLUE]],
                title="Áreas temáticas principales (OpenAlex L0-L1)",
            )
            fig_concepts.update_layout(margin=dict(t=30, b=0, l=0, r=0), height=400)
            st.plotly_chart(fig_concepts, use_container_width=True)

            sub_concepts = (
                concepts[concepts["concept_level"] == 2]
                .groupby("concept_name")["work_id"]
                .nunique()
                .sort_values(ascending=False)
                .head(30)
                .reset_index()
            )
            sub_concepts.columns = ["Sub-área", "Papers"]
            fig_sub = px.bar(
                sub_concepts.head(15), x="Papers", y="Sub-área",
                orientation="h", color="Papers",
                color_continuous_scale=[[0, "#EEF4FF"], [1, BLUE]],
                title="Sub-áreas más frecuentes (OpenAlex L2)",
            )
            fig_sub.update_layout(showlegend=False, height=450, margin=dict(t=30, b=0))
            st.plotly_chart(fig_sub, use_container_width=True)

    # ── Investigadores CCHEN con perfil ORCID ─────────────────────────────────
    if not orcid.empty:
        with st.expander(f"Investigadores CCHEN — Perfiles ORCID ({len(orcid)})", expanded=False):
            sec("Investigadores CCHEN — Perfil ORCID")
            _orcid_display = orcid[[
                c for c in ["full_name", "employers", "education",
                             "orcid_works_count", "orcid_profile_url"]
                if c in orcid.columns
            ]].copy()
            _col_rename = {
                "full_name":          "Investigador",
                "employers":          "Empleadores",
                "education":          "Educación",
                "orcid_works_count":  "Obras ORCID",
                "orcid_profile_url":  "Perfil ORCID",
            }
            _orcid_display = _orcid_display.rename(
                columns={k: v for k, v in _col_rename.items() if k in _orcid_display.columns}
            )
            _col_cfg = {}
            if "Perfil ORCID" in _orcid_display.columns:
                _col_cfg["Perfil ORCID"] = st.column_config.LinkColumn("Perfil ORCID")
            st.dataframe(
                _orcid_display,
                use_container_width=True,
                column_config=_col_cfg,
                height=350,
            )

    # ── Registro DIAN ─────────────────────────────────────────────────────────
    with st.expander(f"Registro interno DIAN CCHEN ({len(dian)} publicaciones)", expanded=False):
        if dian.empty:
            st.warning("No se pudo cargar el archivo Publicaciones DIAN.xlsx")
        else:
            dc1, dc2, dc3 = st.columns(3)
            with dc1:
                st.metric("Total DIAN", len(dian))
            with dc2:
                n_q1_dian = len(dian[dian["cuartil"] == "Q1"]) if "cuartil" in dian.columns else 0
                st.metric("Q1", n_q1_dian)
            with dc3:
                n_unidades = dian["unidad"].nunique() if "unidad" in dian.columns else 0
                st.metric("Unidades CCHEN", n_unidades)

            if "cuartil" in dian.columns and "anio" in dian.columns:
                _dcol1, _dcol2 = st.columns(2)
                with _dcol1:
                    _dq = dian["cuartil"].value_counts().reset_index()
                    _dq.columns = ["Cuartil", "N"]
                    _dq["Cuartil"] = pd.Categorical(_dq["Cuartil"], ["Q1","Q2","Q3","Q4"], ordered=True)
                    _dq = _dq.sort_values("Cuartil")
                    fig_dq = px.bar(_dq, x="Cuartil", y="N", text="N",
                                    color="Cuartil",
                                    color_discrete_map={"Q1":BLUE,"Q2":GREEN,"Q3":AMBER,"Q4":RED},
                                    height=250, title="Cuartiles DIAN")
                    fig_dq.update_traces(textposition="outside")
                    fig_dq.update_layout(showlegend=False, margin=dict(t=30, b=10))
                    st.plotly_chart(fig_dq, use_container_width=True)
                with _dcol2:
                    if "unidad" in dian.columns:
                        _du = dian["unidad"].value_counts().reset_index()
                        _du.columns = ["Unidad", "N"]
                        fig_du = px.bar(_du.sort_values("N"), x="N", y="Unidad",
                                        orientation="h", color_discrete_sequence=[PURPLE],
                                        text="N", height=250, title="Por unidad CCHEN")
                        fig_du.update_layout(showlegend=False, margin=dict(t=30, b=10))
                        st.plotly_chart(fig_du, use_container_width=True)

            _dian_cols = [c for c in ["anio","titulo","autores","revista","cuartil","unidad","doi"] if c in dian.columns]
            _dian_show = dian[_dian_cols].sort_values("anio", ascending=False) if "anio" in dian.columns else dian[_dian_cols]
            if "doi" in _dian_show.columns:
                _dian_show = _dian_show.copy()
                _dian_show["doi"] = _dian_show["doi"].apply(
                    lambda d: f"https://doi.org/{d}" if pd.notna(d) and str(d).startswith("10.") else None
                )
                _dian_show = _dian_show.rename(columns={"doi": "Enlace"})
                _dian_cfg = {"Enlace": st.column_config.LinkColumn("Enlace")}
            else:
                _dian_cfg = {}
            st.dataframe(_dian_show, use_container_width=True, height=320, column_config=_dian_cfg)
            st.download_button("Exportar DIAN CSV", make_csv(_dian_show),
                               "publicaciones_dian_cchen.csv", "text/csv")

    # ── EuroPMC ───────────────────────────────────────────────────────────────
    _europmc_label = f"Publicaciones CCHEN en EuroPMC ({len(europmc)} registros)" if not europmc.empty else "Publicaciones CCHEN en EuroPMC (sin datos)"
    with st.expander(_europmc_label, expanded=False):
        if europmc.empty:
            st.info("No se encontró el archivo cchen_europmc_works.csv o está vacío.")
        else:
            st.metric("Papers indexados en EuroPMC", len(europmc))

            # Build display table using only columns that actually exist
            _epmc_desired = ["title", "year", "pmid", "pmcid", "europmc_url",
                             "doi", "journal_title", "cited_by_count"]
            _epmc_cols = [c for c in _epmc_desired if c in europmc.columns]
            _epmc_show = europmc[_epmc_cols].copy()

            # Sort by year descending if available
            if "year" in _epmc_show.columns:
                _epmc_show = _epmc_show.sort_values("year", ascending=False)

            # Build column config for link/special columns
            _epmc_cfg = {}
            _epmc_rename = {
                "title":         "Título",
                "year":          "Año",
                "pmid":          "PMID",
                "pmcid":         "PMCID",
                "europmc_url":   "EuroPMC",
                "doi":           "DOI",
                "journal_title": "Revista",
                "cited_by_count": "Citas",
            }
            _epmc_show = _epmc_show.rename(columns={k: v for k, v in _epmc_rename.items() if k in _epmc_show.columns})

            if "EuroPMC" in _epmc_show.columns:
                _epmc_cfg["EuroPMC"] = st.column_config.LinkColumn("EuroPMC", display_text="Ver")
            if "DOI" in _epmc_show.columns:
                _epmc_show["DOI"] = _epmc_show["DOI"].apply(
                    lambda d: f"https://doi.org/{d}" if pd.notna(d) and str(d).startswith("10.") else None
                )
                _epmc_cfg["DOI"] = st.column_config.LinkColumn("DOI", display_text="DOI")
            if "Título" in _epmc_show.columns:
                _epmc_cfg["Título"] = st.column_config.TextColumn("Título", width="large")

            st.dataframe(_epmc_show, use_container_width=True, height=400,
                         hide_index=True, column_config=_epmc_cfg)
            st.download_button(
                "Exportar EuroPMC CSV",
                make_csv(_epmc_show),
                "publicaciones_europmc_cchen.csv",
                "text/csv",
                key="dl_europmc",
            )

    # ── PERFIL DE INVESTIGADOR ────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("## 👤 Perfil de Investigador")
    st.caption("Producción científica individual · Fuente: OpenAlex")

    _auth_path = BASE / "Publications" / "cchen_authorships_enriched.csv"
    _oa_path_p = BASE / "Publications" / "cchen_openalex_works.csv"

    if not _auth_path.exists():
        st.info("No se encontró cchen_authorships_enriched.csv.")
    else:
        _auth_all = pd.read_csv(_auth_path, low_memory=False)
        _oa_all   = pd.read_csv(_oa_path_p, low_memory=False)

        _cchen_auth = _auth_all[_auth_all["is_cchen_affiliation"] == True].copy()
        _inv_counts = (
            _cchen_auth.groupby(["author_id", "author_name"])
            .size().reset_index(name="n_papers")
            .sort_values("n_papers", ascending=False)
        )

        _inv_sel = st.selectbox(
            "Seleccionar investigador",
            _inv_counts["author_name"].tolist(),
            format_func=lambda n: f"{n}  ({int(_inv_counts.loc[_inv_counts['author_name']==n,'n_papers'].values[0])} papers)",
            key="inv_perfil_sel",
        )

        _inv_id = _inv_counts.loc[_inv_counts["author_name"] == _inv_sel, "author_id"].values[0]
        _inv_works_ids = _cchen_auth.loc[_cchen_auth["author_id"] == _inv_id, "work_id"].unique()
        _inv_papers = _oa_all[_oa_all["openalex_id"].isin(_inv_works_ids)].copy()
        _inv_papers["year"] = pd.to_numeric(_inv_papers["year"], errors="coerce")
        _inv_papers = _inv_papers.sort_values("cited_by_count", ascending=False)

        _cites_sorted = sorted(_inv_papers["cited_by_count"].dropna().astype(int).tolist(), reverse=True)
        _inv_h = sum(1 for i, c in enumerate(_cites_sorted, 1) if c >= i)
        _inv_total_cites = int(_inv_papers["cited_by_count"].sum())
        _inv_n = len(_inv_papers)
        _inv_yr_min = int(_inv_papers["year"].min()) if _inv_papers["year"].notna().any() else "?"
        _inv_yr_max = int(_inv_papers["year"].max()) if _inv_papers["year"].notna().any() else "?"
        _inv_oa_pct = 100 * _inv_papers["is_oa"].sum() / _inv_n if _inv_n > 0 else 0

        kpi_row(
            kpi("Papers", f"{_inv_n}"),
            kpi("Citaciones totales", f"{_inv_total_cites:,}"),
            kpi("H-index", f"{_inv_h}"),
            kpi("Período activo", f"{_inv_yr_min}–{_inv_yr_max}"),
            kpi("Acceso abierto", f"{_inv_oa_pct:.0f}%"),
        )
        st.divider()

        _ip1, _ip2 = st.columns(2)

        with _ip1:
            sec("Publicaciones por año")
            _by_yr = _inv_papers.groupby("year").agg(
                papers=("openalex_id","count"),
                cites=("cited_by_count","sum")
            ).reset_index().dropna(subset=["year"])
            _by_yr["year"] = _by_yr["year"].astype(int)
            fig_inv_yr = go.Figure()
            fig_inv_yr.add_bar(x=_by_yr["year"], y=_by_yr["papers"],
                               name="Papers", marker_color=BLUE)
            fig_inv_yr.add_scatter(x=_by_yr["year"], y=_by_yr["cites"],
                                   name="Citas", mode="lines+markers",
                                   marker_color=RED, yaxis="y2")
            fig_inv_yr.update_layout(
                height=260, plot_bgcolor="#F8FAFC",
                yaxis=dict(title="Papers"),
                yaxis2=dict(title="Citas", overlaying="y", side="right"),
                legend=dict(orientation="h", y=1.1),
                margin=dict(t=10, b=10, l=0, r=0),
            )
            st.plotly_chart(fig_inv_yr, use_container_width=True)

        with _ip2:
            sec("Revistas más frecuentes")
            _by_src = _inv_papers["source"].value_counts().head(8).reset_index()
            _by_src.columns = ["Revista", "N"]
            fig_inv_src = px.bar(_by_src.sort_values("N"), x="N", y="Revista",
                                 orientation="h", color_discrete_sequence=[BLUE],
                                 text="N", height=260)
            fig_inv_src.update_traces(textposition="outside")
            fig_inv_src.update_layout(yaxis_title="", plot_bgcolor="#F8FAFC",
                                      margin=dict(t=5, b=5, l=5, r=30))
            st.plotly_chart(fig_inv_src, use_container_width=True)

        sec("Principales colaboradores")
        _colabs = _auth_all[
            (_auth_all["work_id"].isin(_inv_works_ids)) &
            (_auth_all["author_id"] != _inv_id)
        ].groupby("author_name").size().reset_index(name="papers_juntos")
        _colabs = _colabs.sort_values("papers_juntos", ascending=False).head(10)
        if not _colabs.empty:
            fig_col = px.bar(_colabs.sort_values("papers_juntos"),
                             x="papers_juntos", y="author_name", orientation="h",
                             color_discrete_sequence=[GREEN], text="papers_juntos",
                             height=max(200, len(_colabs)*28))
            fig_col.update_traces(textposition="outside")
            fig_col.update_layout(yaxis_title="", xaxis_title="Papers en coautoría",
                                  plot_bgcolor="#F8FAFC", margin=dict(t=5,b=5,l=5,r=30))
            st.plotly_chart(fig_col, use_container_width=True)

        st.divider()
        sec(f"Todos los papers de {_inv_sel} ({_inv_n})")
        _inv_show = _inv_papers[["title","year","source","cited_by_count","is_oa","doi"]].copy()
        _inv_show.columns = ["Título","Año","Revista","Citas","OA","DOI"]
        _inv_show["Año"] = _inv_show["Año"].fillna(0).astype(int)
        _inv_show["Citas"] = _inv_show["Citas"].fillna(0).astype(int)
        _inv_cfg = {
            "Título": st.column_config.TextColumn(width="large"),
            "DOI":    st.column_config.LinkColumn(display_text="Ver"),
            "OA":     st.column_config.CheckboxColumn("OA"),
        }
        _inv_show["DOI"] = _inv_show["DOI"].apply(
            lambda d: f"https://doi.org/{d}" if pd.notna(d) and d else None
        )
        st.dataframe(_inv_show, use_container_width=True, height=340,
                     hide_index=True, column_config=_inv_cfg)

    # ══════════════════════════════════════════════════════════════════════
    #  BÚSQUEDA SEMÁNTICA
    # ══════════════════════════════════════════════════════════════════════
    st.markdown("---")
    st.markdown("## 🔍 Búsqueda Semántica")
    st.caption("Encuentra papers CCHEN por similitud de contenido · Modelo multilingüe (español + inglés)")

    import sys as _sys
    import os as _os
    _scripts_dir = str((BASE / ".." / "Scripts").resolve())
    if _scripts_dir not in _sys.path:
        _sys.path.insert(0, _scripts_dir)

    try:
        import semantic_search as _ss
        _sem_available = _ss.is_available()
    except ImportError:
        _sem_available = False

    if not _sem_available:
        st.info(
            "**Búsqueda semántica no disponible.**\n\n"
            "Genera los embeddings ejecutando:\n"
            "```bash\npython3 Scripts/build_embeddings.py\n```"
        )
    else:
        _col_q, _col_n = st.columns([4, 1])
        with _col_q:
            _sem_query = st.text_input(
                "Buscar por concepto o frase:",
                placeholder="ej: dosimetría neutrones reactor · radiopharmaceutical imaging · litio materiales",
                key="sem_search_query",
            )
        with _col_n:
            _sem_top = st.number_input("Resultados", min_value=3, max_value=30, value=10, key="sem_top_k")

        if _sem_query and _sem_query.strip():
            with st.spinner("Buscando…"):
                _sem_results = _ss.search(_sem_query.strip(), top_k=int(_sem_top))

            if _sem_results.empty:
                st.warning("Sin resultados. Verifica que los embeddings estén generados.")
            else:
                st.success(f"{len(_sem_results)} papers más similares a **\"{_sem_query}\"**")
                _sem_show = _sem_results.copy()
                _sem_show["doi_link"] = _sem_show["doi"].apply(
                    lambda d: f"https://doi.org/{d}" if str(d).startswith("10.") else None
                )
                title_col = "title" if "title" in _sem_show.columns else _sem_show.columns[2]
                _sem_cfg = {
                    "score":    st.column_config.NumberColumn("Similitud", format="%.4f"),
                    "doi_link": st.column_config.LinkColumn("DOI", display_text="🔗"),
                    title_col:  st.column_config.TextColumn("Título", width="large"),
                }
                st.dataframe(
                    _sem_show[[title_col, "year", "score", "doi_link"]],
                    use_container_width=True,
                    hide_index=True,
                    height=min(40 + len(_sem_results) * 35, 420),
                    column_config=_sem_cfg,
                )
                st.download_button(
                    "Descargar resultados CSV",
                    make_csv(_sem_show[[title_col, "year", "score", "doi"]]),
                    f"busqueda_{_sem_query[:30].replace(' ','_')}.csv",
                    "text/csv",
                    key="dl_sem_search",
                )
