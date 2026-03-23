"""Section: Redes y Colaboración — CCHEN Observatorio"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from .shared import (
    BLUE, RED, GREEN, AMBER, PURPLE, PALETTE,
    kpi, kpi_row, sec, make_csv, calc_hindex, _ISO2_ISO3,
)


def render(ctx: dict) -> None:
    """Render the Redes y Colaboración section."""
    pub          = ctx["pub"]
    auth         = ctx["auth"]
    ror_registry = ctx["ror_registry"]
    ror_pending_review = ctx["ror_pending_review"]

    st.title("Redes de Colaboración Científica")
    st.caption("Fuente: OpenAlex authorships · 7.971 autorías · Análisis de redes e impacto bibliométrico")
    st.divider()

    with st.expander("Filtros", expanded=True):
        rc1, rc2 = st.columns(2)
        with rc1:
            yr_rc = st.slider("Período", 1990, 2026, (2005, 2025), key="rc_yr")
        with rc2:
            top_n_net = st.slider("Top N instituciones en la red", 10, 60, 30, key="rc_topn")

    _auth_yr = auth.merge(
        pub[["openalex_id", "year"]].rename(columns={"openalex_id": "work_id"}),
        on="work_id", how="left"
    )
    _auth_rc = _auth_yr[_auth_yr["year"].between(*yr_rc)].copy()

    _n_papers_rc  = _auth_rc["work_id"].nunique()
    _n_auth_uniq  = _auth_rc["author_name"].nunique()
    _n_inst_uniq  = _auth_rc["institution_name"].dropna().nunique()
    _n_paises     = _auth_rc["institution_country_code"].dropna().nunique()
    _n_intl       = (_auth_rc["institution_country_code"] != "CL").sum()
    _pct_intl     = round(100 * _n_intl / len(_auth_rc), 1) if len(_auth_rc) > 0 else 0

    kpi_row(
        kpi("Papers en el período",     f"{_n_papers_rc:,}"),
        kpi("Autores únicos",           f"{_n_auth_uniq:,}"),
        kpi("Instituciones",            f"{_n_inst_uniq:,}"),
        kpi("Países",                   f"{_n_paises:,}"),
        kpi("% autorías internacionales", f"{_pct_intl}%"),
    )

    _ror_view = ror_registry.copy()
    _ror_pending_queue = ror_pending_review.copy()
    if not _ror_view.empty:
        for _col in ["authorships_count", "orcid_profiles_count", "convenios_count"]:
            if _col not in _ror_view.columns:
                _ror_view[_col] = 0
            _ror_view[_col] = pd.to_numeric(_ror_view[_col], errors="coerce").fillna(0).astype(int)
        _ror_linked = _ror_view[_ror_view["ror_id"].notna()].copy()
        if _ror_pending_queue.empty:
            _ror_pending = _ror_view[
                _ror_view["ror_id"].isna() &
                (
                    (_ror_view["authorships_count"] > 0) |
                    (_ror_view["orcid_profiles_count"] > 0) |
                    (_ror_view["convenios_count"] > 0)
                )
            ].copy()
        else:
            for _col in ["authorships_count", "orcid_profiles_count", "convenios_count", "signal_total"]:
                if _col not in _ror_pending_queue.columns:
                    _ror_pending_queue[_col] = 0
                _ror_pending_queue[_col] = pd.to_numeric(_ror_pending_queue[_col], errors="coerce").fillna(0).astype(int)
            _priority_order = {"Alta": 0, "Media": 1, "Baja": 2}
            _ror_pending_queue["_priority_order"] = _ror_pending_queue["priority_level"].map(_priority_order).fillna(9).astype(int)
            _ror_pending = _ror_pending_queue.sort_values(
                ["_priority_order", "signal_total", "authorships_count", "orcid_profiles_count", "convenios_count"],
                ascending=[True, False, False, False, False],
            ).copy()
        if "is_cchen_anchor" in _ror_view.columns:
            _ror_anchor = _ror_view[_ror_view["is_cchen_anchor"] == True].head(1)
        else:
            _ror_anchor = pd.DataFrame()
        _auth_ror_cov = round(100 * _auth_rc["institution_ror"].notna().mean(), 1) if "institution_ror" in _auth_rc.columns and len(_auth_rc) else 0
        _convenio_ror = int(((_ror_view["convenios_count"] > 0) & (_ror_view["ror_id"].notna())).sum())
        kpi_row(
            kpi("Instituciones con ROR", f"{len(_ror_linked):,}", "registro institucional consolidado"),
            kpi("% autorías con ROR", f"{_auth_ror_cov}%", "cobertura observada en OpenAlex"),
            kpi("Contrapartes con match", f"{_convenio_ror:,}", "instituciones vinculadas a convenios"),
            kpi("Pendientes revisión", f"{len(_ror_pending):,}", "instituciones aún sin ROR"),
        )

        sec("Normalización institucional con ROR")
        st.caption(
            "Esta capa usa ROR como identificador canónico para instituciones. "
            "La base actual se construye con OpenAlex authorships, ORCID, convenios y una semilla manual para CCHEN."
        )
        if not _ror_anchor.empty:
            _anchor = _ror_anchor.iloc[0]
            st.markdown(
                f"<div class='alert-azul'><b>CCHEN como institución ancla</b><br>"
                f"ROR: <a href='{_anchor['ror_id']}' target='_blank'>{_anchor['ror_id']}</a><br>"
                f"Nombre canónico: {_anchor['canonical_name']}<br>"
                f"Sitio: {_anchor.get('website') or 'sin sitio cargado'}<br>"
                f"Última modificación conocida del registro: {_anchor.get('ror_record_last_modified') or 'sin dato'}</div>",
                unsafe_allow_html=True,
            )

        _rr1, _rr2 = st.columns([2, 1])
        with _rr1:
            _top_ror = _ror_linked[
                _ror_linked["canonical_name"] != "Comisión Chilena de Energía Nuclear"
            ].sort_values(
                ["authorships_count", "orcid_profiles_count", "convenios_count"],
                ascending=False,
            ).head(20)
            st.dataframe(
                _top_ror[[
                    "canonical_name", "country_code", "authorships_count",
                    "orcid_profiles_count", "convenios_count", "ror_id",
                ]].rename(columns={
                    "canonical_name": "Institución",
                    "country_code": "País",
                    "authorships_count": "Autorías",
                    "orcid_profiles_count": "ORCID",
                    "convenios_count": "Convenios",
                    "ror_id": "ROR",
                }),
                use_container_width=True,
                hide_index=True,
                height=320,
                column_config={"ROR": st.column_config.LinkColumn("ROR")},
            )
        with _rr2:
            sec("Pendientes de revisión manual")
            if _ror_pending.empty:
                st.success("No hay instituciones observadas pendientes de revisión manual.")
            else:
                if "priority_level" in _ror_pending.columns:
                    _pending_counts = _ror_pending["priority_level"].fillna("Sin prioridad").value_counts()
                    st.caption(
                        "Cola priorizada de revisión: "
                        + " · ".join(f"{k}: {v}" for k, v in _pending_counts.items())
                    )
                st.dataframe(
                    _ror_pending.head(12)[[
                        c for c in [
                            "canonical_name", "priority_level", "recommended_resolution",
                            "authorships_count", "orcid_profiles_count", "convenios_count",
                            "signal_total", "source_evidence",
                        ] if c in _ror_pending.columns
                    ]].rename(columns={
                        "canonical_name": "Institución",
                        "priority_level": "Prioridad",
                        "recommended_resolution": "Resolución sugerida",
                        "authorships_count": "Autorías",
                        "orcid_profiles_count": "ORCID",
                        "convenios_count": "Convenios",
                        "signal_total": "Señal total",
                        "source_evidence": "Evidencia",
                    }),
                    use_container_width=True,
                    hide_index=True,
                    height=320,
                )

        st.download_button(
            "Exportar registro institucional ROR CSV",
            make_csv(_ror_view),
            "cchen_institution_registry.csv",
            "text/csv",
        )
        if not _ror_pending.empty:
            st.download_button(
                "Exportar pendientes ROR priorizados CSV",
                make_csv(_ror_pending.drop(columns=["_priority_order"], errors="ignore")),
                "ror_pending_review.csv",
                "text/csv",
            )
    st.divider()

    # ── 1. Mapa choropleth de colaboraciones internacionales ──────────────────
    sec("Mapa de colaboraciones internacionales")

    _country_counts = (
        _auth_rc[_auth_rc["institution_country_code"] != "CL"]
        ["institution_country_code"].value_counts().reset_index()
    )
    _country_counts.columns = ["iso2", "N"]
    _country_counts["iso3"] = _country_counts["iso2"].map(_ISO2_ISO3)
    _country_counts = _country_counts.dropna(subset=["iso3"])

    if not _country_counts.empty:
        map_col, bar_col = st.columns([3, 1])
        with map_col:
            fig_map = px.choropleth(
                _country_counts, locations="iso3",
                color="N",
                color_continuous_scale=[[0, "#E3EEF9"], [0.3, "#6BAED6"],
                                        [0.7, "#2171B5"], [1.0, "#08306B"]],
                projection="natural earth",
                labels={"N": "Co-autorías"},
                height=380,
            )
            fig_map.update_layout(
                margin=dict(t=0, b=0, l=0, r=0),
                coloraxis_colorbar=dict(title="Co-autorías"),
                geo=dict(showframe=False, showcoastlines=True,
                         coastlinecolor="#BBBBBB", landcolor="#F0F0F0",
                         bgcolor="#F8FAFC"),
            )
            st.plotly_chart(fig_map, use_container_width=True)

        with bar_col:
            _top10c = _country_counts.sort_values("N", ascending=False).head(12)
            fig_topc = px.bar(
                _top10c, x="N", y="iso2", orientation="h",
                color_discrete_sequence=[BLUE], text="N", height=380,
            )
            fig_topc.update_traces(textposition="outside")
            fig_topc.update_layout(
                yaxis=dict(title="", autorange="reversed"),
                xaxis_title="Co-autorías",
                margin=dict(t=5, b=5, l=5, r=30),
                plot_bgcolor="#F8FAFC",
            )
            st.plotly_chart(fig_topc, use_container_width=True)
    else:
        st.info("Sin datos de país para el período seleccionado.")

    st.divider()

    # ── 2. Red de coautoría institucional ────────────────────────────────────
    sec("Red de coautoría institucional")
    st.caption("Nodos = instituciones · Aristas = co-publicaciones · Rojo = CCHEN · Tamaño = grado de conexión")

    try:
        import networkx as nx

        _au_inst = _auth_rc[["work_id", "institution_name"]].dropna(subset=["institution_name"])
        _paper_insts = _au_inst.groupby("work_id")["institution_name"].apply(list).reset_index()

        edges: dict = {}
        for _, row in _paper_insts.iterrows():
            insts = list(set(row["institution_name"]))
            if len(insts) < 2:
                continue
            for i in range(len(insts)):
                for j in range(i + 1, len(insts)):
                    pair = tuple(sorted([insts[i], insts[j]]))
                    edges[pair] = edges.get(pair, 0) + 1

        G = nx.Graph()
        for (a, b), w in edges.items():
            G.add_edge(a, b, weight=w)

        top_nodes = sorted(G.degree(), key=lambda x: -x[1])[:top_n_net]
        top_node_names = [n for n, _ in top_nodes]
        G_sub = G.subgraph(top_node_names)
        pos = nx.spring_layout(G_sub, seed=42, k=1.5)

        edge_x, edge_y = [], []
        for (u, v) in G_sub.edges():
            x0, y0 = pos[u]; x1, y1 = pos[v]
            edge_x += [x0, x1, None]; edge_y += [y0, y1, None]
        edge_trace = go.Scatter(
            x=edge_x, y=edge_y, mode="lines",
            line=dict(width=0.6, color="#CCCCCC"), hoverinfo="none",
        )

        _is_cchen = lambda n: any(k in n.upper() for k in ("CCHEN", "COMISIÓN CHILENA", "NUCLEAR"))
        node_x   = [pos[n][0] for n in G_sub.nodes()]
        node_y   = [pos[n][1] for n in G_sub.nodes()]
        node_deg = [G_sub.degree(n) for n in G_sub.nodes()]
        node_col = [RED if _is_cchen(n) else BLUE for n in G_sub.nodes()]
        node_sz  = [10 + 3 * d for d in node_deg]
        node_lbl = [n[:28] + "…" if len(n) > 28 else n for n in G_sub.nodes()]
        node_tip = [f"<b>{n}</b><br>Conexiones: {d}" for n, d in zip(G_sub.nodes(), node_deg)]

        node_trace = go.Scatter(
            x=node_x, y=node_y, mode="markers+text",
            marker=dict(size=node_sz, color=node_col,
                        line=dict(width=1, color="white")),
            text=node_lbl, textposition="top center",
            textfont=dict(size=7, color="#333333"),
            hovertext=node_tip, hoverinfo="text",
        )

        fig_net = go.Figure(data=[edge_trace, node_trace])
        fig_net.update_layout(
            showlegend=False, height=560,
            margin=dict(t=10, b=10, l=10, r=10),
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            plot_bgcolor="#F8FAFC",
        )
        st.plotly_chart(fig_net, use_container_width=True)
        st.caption("🔴 CCHEN   🔵 Instituciones colaboradoras")

        _deg_df = pd.DataFrame(sorted(G_sub.degree(), key=lambda x: -x[1])[:15],
                               columns=["Institución", "Conexiones"])
        st.dataframe(_deg_df, use_container_width=True, hide_index=True, height=280)

    except ImportError:
        st.warning("Instala networkx: `pip install networkx`")
    except Exception as _e:
        st.warning(f"No se pudo construir la red: {_e}")

    st.divider()

    # ── 2b. Red de co-autoría entre investigadores ────────────────────────────
    sec("Red de co-autoría entre investigadores")
    st.caption("Nodos = autores · Aristas = co-publicaciones · Rojo = afiliación CCHEN · Tamaño = nº de papers")

    _top_n_authors = st.slider("Nº de autores más conectados a mostrar", 20, 80, 40,
                                key="coauth_author_top_n")

    try:
        import networkx as _nx

        _au_pairs = _auth_rc[["work_id", "author_id", "author_name", "is_cchen_affiliation"]].dropna(
            subset=["author_id", "author_name"]
        )
        _cchen_ids = set(
            _au_pairs.loc[_au_pairs["is_cchen_affiliation"] == True, "author_id"]
        )

        _paper_authors = _au_pairs.groupby("work_id").apply(
            lambda df: list(zip(df["author_id"], df["author_name"]))
        ).reset_index(name="authors_list")

        _coauth_edges: dict = {}
        for _, row in _paper_authors.iterrows():
            auths = row["authors_list"]
            if len(auths) < 2:
                continue
            for i in range(len(auths)):
                for j in range(i + 1, len(auths)):
                    a_id, a_nm = auths[i]
                    b_id, b_nm = auths[j]
                    pair = tuple(sorted([a_id, b_id]))
                    if pair not in _coauth_edges:
                        _coauth_edges[pair] = {"weight": 0,
                                               "name_a": a_nm, "name_b": b_nm,
                                               "id_a": a_id, "id_b": b_id}
                    _coauth_edges[pair]["weight"] += 1

        G_au = _nx.Graph()
        _id_to_name: dict = {}
        for (a_id, b_id), meta in _coauth_edges.items():
            G_au.add_edge(a_id, b_id, weight=meta["weight"])
            _id_to_name[a_id] = meta["name_a"]
            _id_to_name[b_id] = meta["name_b"]

        _top_au_nodes = sorted(G_au.degree(), key=lambda x: -x[1])[:_top_n_authors]
        _top_au_ids   = [n for n, _ in _top_au_nodes]
        G_au_sub = G_au.subgraph(_top_au_ids)
        pos_au   = _nx.spring_layout(G_au_sub, seed=7, k=2.2 / (_top_n_authors ** 0.5))

        _au_paper_count = _au_pairs.groupby("author_id")["work_id"].nunique().to_dict()

        _ae_x, _ae_y = [], []
        for u, v, data in G_au_sub.edges(data=True):
            x0, y0 = pos_au[u]; x1, y1 = pos_au[v]
            _ae_x += [x0, x1, None]
            _ae_y += [y0, y1, None]
        _edge_au = go.Scatter(
            x=_ae_x, y=_ae_y, mode="lines",
            line=dict(width=0.8, color="rgba(150,150,150,0.4)"),
            hoverinfo="none",
        )

        _an_x     = [pos_au[n][0] for n in G_au_sub.nodes()]
        _an_y     = [pos_au[n][1] for n in G_au_sub.nodes()]
        _an_np    = [_au_paper_count.get(n, 1) for n in G_au_sub.nodes()]
        _an_col   = [RED if n in _cchen_ids else BLUE for n in G_au_sub.nodes()]
        _an_sz    = [8 + 4 * min(p, 20) for p in _an_np]
        _an_names = [_id_to_name.get(n, n)[:25] for n in G_au_sub.nodes()]
        _an_tip   = [
            f"<b>{_id_to_name.get(n, n)}</b><br>"
            f"Papers: {_au_paper_count.get(n, '?')}<br>"
            f"Co-autores directos: {G_au_sub.degree(n)}"
            + (" 🔬 CCHEN" if n in _cchen_ids else "")
            for n in G_au_sub.nodes()
        ]
        _node_au = go.Scatter(
            x=_an_x, y=_an_y,
            mode="markers+text",
            marker=dict(size=_an_sz, color=_an_col,
                        line=dict(width=1, color="white"),
                        opacity=0.85),
            text=_an_names, textposition="top center",
            textfont=dict(size=6.5, color="#444444"),
            hovertext=_an_tip, hoverinfo="text",
        )

        fig_au_net = go.Figure(data=[_edge_au, _node_au])
        fig_au_net.update_layout(
            showlegend=False, height=620,
            margin=dict(t=10, b=10, l=10, r=10),
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            plot_bgcolor="#F8FAFC",
        )
        st.plotly_chart(fig_au_net, use_container_width=True)
        st.caption("🔴 Autores con afiliación CCHEN   🔵 Colaboradores externos   Tamaño = nº de papers")

        _au_top_df = pd.DataFrame([
            {
                "Autor": _id_to_name.get(n, n),
                "CCHEN": "✓" if n in _cchen_ids else "",
                "Co-autores": G_au.degree(n),
                "Papers": _au_paper_count.get(n, 0),
            }
            for n, _ in sorted(G_au.degree(), key=lambda x: -x[1])[:20]
        ])
        st.dataframe(_au_top_df, use_container_width=True, hide_index=True, height=320)

    except ImportError:
        st.warning("Instala networkx: `pip install networkx`")
    except Exception as _e:
        st.warning(f"No se pudo construir la red de autores: {_e}")

    st.divider()

    # ── 3. H-index institucional acumulado por año ───────────────────────────
    sec("H-index institucional — evolución histórica")
    st.caption("H-index de Hirsch calculado sobre citas acumuladas hasta cada año (ventana móvil)")

    _hyr = [
        {"Año": yr, "H-index": calc_hindex(pub[pub["year"] <= yr]["cited_by_count"])}
        for yr in range(2005, 2026)
    ]
    _hdf = pd.DataFrame(_hyr)
    _current_h = _hdf["H-index"].iloc[-1]

    h_col1, h_col2 = st.columns([2, 1])
    with h_col1:
        fig_h = go.Figure()
        fig_h.add_scatter(
            x=_hdf["Año"], y=_hdf["H-index"],
            mode="lines+markers",
            line=dict(color=BLUE, width=2.5),
            marker=dict(size=7, color=BLUE),
            fill="tozeroy", fillcolor="rgba(0,59,111,0.08)",
        )
        fig_h.update_layout(
            yaxis_title="H-index", xaxis_title="Año",
            margin=dict(t=10, b=30, l=40, r=20), height=280,
            plot_bgcolor="#F8FAFC",
        )
        st.plotly_chart(fig_h, use_container_width=True)

    with h_col2:
        st.markdown(f"""
        <div style='background:#F0F4FF;border-left:4px solid {BLUE};
                    padding:16px;border-radius:6px;margin-top:30px'>
        <div style='font-size:0.75rem;color:#555;font-weight:600'>H-INDEX CCHEN 2025</div>
        <div style='font-size:3rem;font-weight:700;color:{BLUE}'>{_current_h}</div>
        <div style='font-size:0.8rem;color:#666'>
        {_current_h} publicaciones con al menos {_current_h} citas cada una
        </div>
        </div>
        """, unsafe_allow_html=True)
        st.caption("Ref. para comparar: instituciones similares en LATAM tienen H-index 10-20")

    st.divider()

    # ── Top instituciones colaboradoras (tabla) ──────────────────────────────
    sec("Top instituciones colaboradoras (por papers co-publicados)")

    _top_inst = (
        _auth_rc[_auth_rc["is_cchen_affiliation"] == False]
        .groupby(["institution_name", "institution_country_code"])["work_id"]
        .nunique().sort_values(ascending=False).head(25).reset_index()
    )
    _top_inst.columns = ["Institución", "País", "Papers"]
    fig_inst = px.bar(
        _top_inst.sort_values("Papers").tail(20),
        x="Papers", y="Institución",
        orientation="h", color_discrete_sequence=[GREEN],
        text="Papers", height=500,
    )
    fig_inst.update_traces(textposition="outside")
    fig_inst.update_layout(yaxis_title="", margin=dict(t=0, b=0, l=10, r=30),
                           plot_bgcolor="#F8FAFC")
    st.plotly_chart(fig_inst, use_container_width=True)

    st.download_button(
        "Exportar instituciones colaboradoras CSV",
        make_csv(_top_inst), "colaboraciones_instituciones_cchen.csv", "text/csv",
    )
