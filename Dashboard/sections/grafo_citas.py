"""Section: Grafo de Citas — CCHEN Observatorio"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from .shared import BLUE, RED, GREEN, AMBER, PURPLE, PALETTE, sec, kpi, kpi_row, make_csv


def render(ctx: dict) -> None:
    """Visualización del grafo de citas OpenAlex."""
    pub         = ctx["pub"]
    pub_enr     = ctx.get("pub_enr", pd.DataFrame())
    citation_graph  = ctx.get("citation_graph", pd.DataFrame())
    citing_papers   = ctx.get("citing_papers", pd.DataFrame())

    st.title("Grafo de Citas — Red de Impacto Científico CCHEN")
    st.markdown("Análisis del grafo de citas OpenAlex: quién cita a CCHEN y qué cita CCHEN.")
    st.divider()

    # ── Estado de datos ──────────────────────────────────────────────────────
    if citation_graph.empty:
        st.info(
            "**Datos de citas no disponibles aún.**\n\n"
            "Genera el grafo de citas ejecutando:\n"
            "```bash\npython3 Scripts/fetch_openalex_citations.py\n```\n"
            "El proceso toma ~15 minutos para los 877 papers CCHEN."
        )
        # Mostrar igual los datos de cited_by_count que ya están en pub
        st.divider()
        _render_from_pub(pub, pub_enr)
        return

    # ── KPIs del grafo ────────────────────────────────────────────────────────
    total_cites   = int(citation_graph["cited_by_count"].sum()) if "cited_by_count" in citation_graph.columns else 0
    total_refs    = int(citation_graph["referenced_works_count"].sum()) if "referenced_works_count" in citation_graph.columns else 0
    n_citing_ext  = len(citing_papers["citing_id"].unique()) if not citing_papers.empty else 0

    n_inst = 0
    if not citing_papers.empty and "citing_institutions" in citing_papers.columns:
        all_inst = citing_papers["citing_institutions"].dropna().str.split("; ").explode()
        n_inst = all_inst[all_inst.str.len() > 0].nunique()

    kpi_row(
        kpi("Citas totales (grafo)",    f"{total_cites:,}",   "suma de cited_by_count"),
        kpi("Papers citantes externos", f"{n_citing_ext:,}",  "que citan al menos 1 paper CCHEN"),
        kpi("Referencias totales",      f"{total_refs:,}",    "papers que CCHEN cita"),
        kpi("Instituciones citantes",   f"{n_inst:,}",        "instituciones únicas"),
    )
    st.divider()

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📈 Distribución de citas",
        "🏛️ Instituciones citantes",
        "📅 Citas por año",
        "🔗 Papers más citados",
        "🕸️ Red interactiva",
    ])

    with tab1:
        _render_citation_distribution(citation_graph)

    with tab2:
        _render_citing_institutions(citing_papers)

    with tab3:
        _render_cites_by_year(citation_graph, citing_papers)

    with tab4:
        _render_top_cited(citation_graph, pub)

    with tab5:
        _render_interactive_network(citation_graph, citing_papers, pub)


def _render_interactive_network(cg: pd.DataFrame, cp: pd.DataFrame, pub: pd.DataFrame) -> None:
    """Red interactiva de citas usando plotly + networkx."""
    import networkx as nx
    import plotly.graph_objects as go

    sec("Red interactiva de citas CCHEN")

    st.markdown(
        "Visualización de los **top papers CCHEN** y sus relaciones de cita. "
        "**Azul** = papers CCHEN · **Gris** = papers externos citantes. "
        "Hover para detalles, scroll para zoom."
    )

    col1, col2 = st.columns(2)
    with col1:
        top_n = st.slider("Top N papers CCHEN (por citas)", 5, 50, 20, key="net_top_n")
    with col2:
        max_citing = st.slider("Máx. citantes externos por paper", 1, 20, 5, key="net_max_citing")

    if cg.empty or "cited_by_count" not in cg.columns:
        st.info("Sin datos de grafo. Ejecuta `fetch_openalex_citations.py`.")
        return

    top_papers = cg.nlargest(top_n, "cited_by_count")

    if not pub.empty and "openalex_id" in pub.columns and "title" in pub.columns:
        top_papers = top_papers.merge(pub[["openalex_id", "title"]], on="openalex_id", how="left")
    if "title" not in top_papers.columns:
        top_papers["title"] = top_papers["openalex_id"]

    G = nx.DiGraph()
    cchen_ids: set = set()
    node_info: dict = {}

    for _, row in top_papers.iterrows():
        nid = str(row["openalex_id"])
        cchen_ids.add(nid)
        cites = int(row.get("cited_by_count", 0))
        G.add_node(nid, node_type="cchen")
        node_info[nid] = {
            "hover": f"<b>{str(row.get('title', ''))[:80]}</b><br>Año: {row.get('year', '')}<br>Citas: {cites}",
            "label": str(row.get("title", nid))[:45] + "…",
            "color": "#3b82f6",
            "size": max(12, min(40, 10 + cites // 20)),
        }

    if not cp.empty and "citing_id" in cp.columns and "cited_cchen_id" in cp.columns:
        cp_filt = (
            cp[cp["cited_cchen_id"].isin(cchen_ids)]
            .groupby("cited_cchen_id").head(max_citing)
            .reset_index(drop=True)
        )
        for _, erow in cp_filt.iterrows():
            eid = str(erow["citing_id"])
            cited = str(erow["cited_cchen_id"])
            if eid not in node_info:
                G.add_node(eid, node_type="external")
                node_info[eid] = {
                    "hover": f"{str(erow.get('citing_title', ''))[:80]}<br>Año: {erow.get('citing_year', '')}<br>Inst: {str(erow.get('citing_institutions', ''))[:60]}",
                    "label": "",
                    "color": "#64748b",
                    "size": 7,
                }
            G.add_edge(eid, cited)
    else:
        st.caption("Sin datos de papers citantes externos.")

    if len(G.nodes) == 0:
        st.info("Sin nodos para mostrar.")
        return

    pos = nx.spring_layout(G, seed=42, k=2.0 / max(len(G.nodes) ** 0.5, 1))

    edge_x, edge_y = [], []
    for u, v in G.edges():
        if u in pos and v in pos:
            x0, y0 = pos[u]
            x1, y1 = pos[v]
            edge_x += [x0, x1, None]
            edge_y += [y0, y1, None]

    traces = [go.Scatter(
        x=edge_x, y=edge_y, mode="lines",
        line=dict(width=0.5, color="#475569"),
        hoverinfo="none", showlegend=False,
    )]

    for ntype, name in [("cchen", "Papers CCHEN"), ("external", "Papers citantes")]:
        nodes = [n for n, d in G.nodes(data=True) if d.get("node_type") == ntype and n in pos]
        if not nodes:
            continue
        traces.append(go.Scatter(
            x=[pos[n][0] for n in nodes],
            y=[pos[n][1] for n in nodes],
            mode="markers+text" if ntype == "cchen" else "markers",
            marker=dict(
                size=[node_info[n]["size"] for n in nodes],
                color=[node_info[n]["color"] for n in nodes],
                line=dict(width=1, color="white"),
            ),
            text=[node_info[n]["label"] for n in nodes] if ntype == "cchen" else None,
            textposition="top center",
            textfont=dict(size=8, color="#e2e8f0"),
            hovertext=[node_info[n]["hover"] for n in nodes],
            hoverinfo="text",
            name=name,
        ))

    fig = go.Figure(
        data=traces,
        layout=go.Layout(
            paper_bgcolor="#0f172a", plot_bgcolor="#0f172a",
            font=dict(color="#e2e8f0"),
            legend=dict(bgcolor="#1e293b", bordercolor="#334155", x=0.01, y=0.99),
            hovermode="closest",
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            height=560,
            margin=dict(l=10, r=10, t=10, b=10),
        ),
    )
    st.plotly_chart(fig, width="stretch")

    st.caption(
        f"**{len(cchen_ids)}** papers CCHEN (azul) · "
        f"hasta {max_citing} citantes externos por paper (gris)."
    )


def _render_from_pub(pub: pd.DataFrame, pub_enr: pd.DataFrame) -> None:
    """Fallback: muestra citas desde datos de OpenAlex (ya disponibles)."""
    sec("Distribución de citas (OpenAlex)")
    if pub.empty or "cited_by_count" not in pub.columns:
        st.caption("Sin datos.")
        return

    col1, col2 = st.columns(2)
    with col1:
        fig = px.histogram(
            pub[pub["cited_by_count"] > 0],
            x="cited_by_count", nbins=40,
            title="Distribución de citas (papers con ≥1 cita)",
            labels={"cited_by_count": "Citas"},
            color_discrete_sequence=[BLUE],
        )
        fig.update_layout(height=300, margin=dict(t=40,b=20,l=10,r=10))
        st.plotly_chart(fig, width="stretch")

    with col2:
        top10 = pub.nlargest(10, "cited_by_count")[["title","year","cited_by_count"]].copy()
        top10["title"] = top10["title"].str[:60] + "…"
        fig2 = px.bar(
            top10.sort_values("cited_by_count"),
            x="cited_by_count", y="title",
            orientation="h",
            title="Top 10 más citados",
            labels={"cited_by_count": "Citas", "title": ""},
            color_discrete_sequence=[RED],
        )
        fig2.update_layout(height=300, margin=dict(t=40,b=20,l=10,r=10))
        st.plotly_chart(fig2, width="stretch")


def _render_citation_distribution(cg: pd.DataFrame) -> None:
    sec("Distribución de citas en el grafo")
    if "cited_by_count" not in cg.columns:
        st.caption("Sin datos de citas.")
        return
    col1, col2 = st.columns(2)
    with col1:
        fig = px.histogram(
            cg[cg["cited_by_count"] > 0],
            x="cited_by_count", nbins=50,
            title="Histograma de citas por paper (escala log)",
            labels={"cited_by_count": "Citas"},
            color_discrete_sequence=[BLUE],
            log_y=True,
        )
        fig.update_layout(height=350, margin=dict(t=40,b=20,l=10,r=10))
        st.plotly_chart(fig, width="stretch")
    with col2:
        # Percentiles
        desc = cg["cited_by_count"].describe(percentiles=[.5,.75,.9,.95,.99])
        st.markdown("**Estadísticas de citas**")
        st.dataframe(
            desc.rename("valor").reset_index().rename(columns={"index": "percentil"}),
            hide_index=True, width="stretch", height=220,
        )


def _render_citing_institutions(cp: pd.DataFrame) -> None:
    sec("Instituciones que más citan a CCHEN")
    if cp.empty or "citing_institutions" not in cp.columns:
        st.info("Ejecuta `fetch_openalex_citations.py` para obtener datos de instituciones citantes.")
        return
    inst_series = (
        cp["citing_institutions"].dropna()
        .str.split("; ")
        .explode()
        .str.strip()
    )
    inst_series = inst_series[inst_series.str.len() > 2]
    top_inst = inst_series.value_counts().head(20).reset_index()
    top_inst.columns = ["institucion", "n_citas"]

    fig = px.bar(
        top_inst.sort_values("n_citas"),
        x="n_citas", y="institucion",
        orientation="h",
        title="Top 20 instituciones citantes",
        labels={"n_citas": "Veces que citan a CCHEN", "institucion": ""},
        color_discrete_sequence=[GREEN],
    )
    fig.update_layout(height=500, margin=dict(t=40,b=20,l=10,r=10))
    st.plotly_chart(fig, width="stretch")

    st.download_button(
        "Descargar CSV instituciones citantes",
        make_csv(top_inst), "instituciones_citantes_cchen.csv", "text/csv",
        key="dl_citing_inst",
    )


def _render_cites_by_year(cg: pd.DataFrame, cp: pd.DataFrame) -> None:
    sec("Citas recibidas por año de publicación")
    if "year" not in cg.columns or "cited_by_count" not in cg.columns:
        st.caption("Sin datos.")
        return
    cg_y = cg.copy()
    cg_y["year"] = pd.to_numeric(cg_y["year"], errors="coerce")
    by_year = cg_y.groupby("year")["cited_by_count"].sum().reset_index()
    by_year = by_year[(by_year["year"] >= 1990) & (by_year["year"] <= 2025)]

    fig = px.bar(
        by_year, x="year", y="cited_by_count",
        title="Suma de citas por año de publicación del paper citado",
        labels={"year": "Año publicación", "cited_by_count": "Citas totales"},
        color_discrete_sequence=[AMBER],
    )
    fig.update_layout(height=350, margin=dict(t=40,b=20,l=10,r=10))
    st.plotly_chart(fig, width="stretch")

    if not cp.empty and "citing_year" in cp.columns:
        st.markdown("#### Año de los papers que citan a CCHEN")
        cp_y = cp.copy()
        cp_y["citing_year"] = pd.to_numeric(cp_y["citing_year"], errors="coerce")
        citing_by_year = cp_y.groupby("citing_year").size().reset_index(name="n_papers")
        citing_by_year = citing_by_year[
            (citing_by_year["citing_year"] >= 1995) & (citing_by_year["citing_year"] <= 2025)
        ]
        fig2 = px.area(
            citing_by_year, x="citing_year", y="n_papers",
            title="Papers externos citantes por año",
            labels={"citing_year": "Año", "n_papers": "Papers citantes"},
            color_discrete_sequence=[PURPLE],
        )
        fig2.update_layout(height=300, margin=dict(t=40,b=20,l=10,r=10))
        st.plotly_chart(fig2, width="stretch")


def _render_top_cited(cg: pd.DataFrame, pub: pd.DataFrame) -> None:
    sec("Papers CCHEN más citados (grafo)")
    if "cited_by_count" not in cg.columns:
        st.caption("Sin datos.")
        return
    top = cg.nlargest(20, "cited_by_count").copy()
    # Enriquecer con títulos desde pub si disponible
    if not pub.empty and "openalex_id" in pub.columns and "title" in pub.columns:
        top = top.merge(
            pub[["openalex_id","title"]],
            on="openalex_id", how="left"
        )
        if "title" in top.columns:
            top["titulo"] = top["title"].fillna(top["openalex_id"]).str[:80]
        else:
            top["titulo"] = top["openalex_id"]
    else:
        top["titulo"] = top["openalex_id"]

    show_cols = ["titulo","year","cited_by_count","referenced_works_count"]
    show_cols = [c for c in show_cols if c in top.columns]
    st.dataframe(
        top[show_cols].rename(columns={
            "titulo": "Título",
            "year": "Año",
            "cited_by_count": "Citas",
            "referenced_works_count": "Referencias",
        }),
        hide_index=True,
        width="stretch",
        height=450,
    )
    st.download_button(
        "Descargar CSV top citados",
        make_csv(top[show_cols]),
        "cchen_top_citados.csv", "text/csv",
        key="dl_top_citados",
    )
