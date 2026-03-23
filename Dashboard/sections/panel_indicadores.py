"""Section: Panel de Indicadores — CCHEN Observatorio"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from .shared import (
    BLUE, RED, GREEN, AMBER, PURPLE, PALETTE,
    kpi, kpi_row, sec, make_csv,
)


def render(ctx: dict) -> None:
    """Render the Panel de Indicadores section."""
    pub          = ctx["pub"]
    pub_enr      = ctx["pub_enr"]
    anid         = ctx["anid"]
    ch           = ctx["ch"]
    ch_ej        = ctx["ch_ej"]
    ch_adv       = ctx["ch_adv"]
    ror_pending_review = ctx["ror_pending_review"]
    patents      = ctx["patents"]

    # render_operational_strip is defined in app.py and passed via ctx
    render_operational_strip = ctx.get("render_operational_strip")

    st.title("CCHEN — Observatorio Tecnológico I+D+i+Tt")
    st.markdown("**Panel consolidado de indicadores de Vigilancia Tecnológica** · Beta interna")
    st.divider()
    if render_operational_strip is not None:
        render_operational_strip()
    st.divider()

    # KPIs principales
    kpis_ch = ch_ej.get("kpis", {})
    total_papers = len(pub[pub["year"] >= 2000])
    total_citas  = int(pub["cited_by_count"].sum())
    n_q1q2_tot   = len(pub_enr[pub_enr["quartile"].notna()])
    pct_q1q2     = round(100 * len(pub_enr[pub_enr["quartile"].isin(["Q1","Q2"])]) / n_q1q2_tot, 1) if n_q1q2_tot > 0 else 0
    monto_mm     = anid["monto_programa_num"].sum() / 1e6
    n_proyectos  = len(anid)
    n_personas   = kpis_ch.get("personas_unicas", ch["nombre"].nunique())
    # YoY papers
    _p24 = len(pub[pub["year"] == 2024]); _p23 = len(pub[pub["year"] == 2023])
    _delta_p = _p24 - _p23; _ds = ("+" if _delta_p >= 0 else "") + str(_delta_p)
    # YoY citas
    _c24 = int(pub[pub["year"] == 2024]["cited_by_count"].sum()); _c23 = int(pub[pub["year"] == 2023]["cited_by_count"].sum())
    _delta_c = _c24 - _c23; _dcs = ("+" if _delta_c >= 0 else "") + str(_delta_c)

    _n_pat = len(patents) if not patents.empty else 0
    _pat_label = f"{_n_pat}" if _n_pat > 0 else "⚙ Sin datos"
    _pat_sub   = (
        "Requiere PATENTSVIEW_API_KEY — ver Scripts/fetch_patentsview_patents.py"
        if _n_pat == 0
        else "patentes USPTO indexadas"
    )

    kpi_row(
        kpi("Papers (2000–2026)",  f"{total_papers:,}",    f"{_ds} vs 2023 (2024 vs 2023)"),
        kpi("Citas totales",        f"{total_citas:,}",     f"{_dcs} citas · 2024 vs 2023"),
        kpi("% Q1+Q2",             f"{pct_q1q2}%",         f"{len(pub_enr[pub_enr['quartile'].isin(['Q1','Q2'])])} de {n_q1q2_tot} papers con cuartil"),
        kpi("Proyectos ANID",       f"{n_proyectos}",       "fondos adjudicados"),
        kpi("Monto total ANID",     f"${monto_mm:.0f} MM",  f"CLP · {anid['monto_programa_num'].notna().sum()} con dato"),
        kpi("Patentes USPTO",       _pat_label,             _pat_sub, color=PURPLE if _n_pat == 0 else BLUE),
    )
    kpi_row(
        kpi("Personas formadas",    f"{n_personas}",        "capital humano I+D"),
    )

    # ── Alertas de gobernanza ────────────────────────────────────────────────────
    _ror_alta = (
        ror_pending_review[ror_pending_review["priority_level"] == "Alta"]
        if not ror_pending_review.empty and "priority_level" in ror_pending_review.columns
        else ror_pending_review
    )
    if not _ror_alta.empty:
        _names = ", ".join(_ror_alta["canonical_name"].head(4).tolist()) if "canonical_name" in _ror_alta.columns else ""
        st.warning(
            f"**Gobernanza ROR:** {len(_ror_alta)} institución(es) con prioridad Alta pendientes de revisión manual"
            + (f": {_names}" if _names else "")
            + ". Ve a **Modelo y Gobernanza → Registro Institucional ROR** para resolverlas."
        )

    # Gráficos principales
    col1, col2 = st.columns(2)

    with col1:
        sec("Producción científica por año (2000–2025)")
        by_yr = pub[pub["year"].between(2000, 2025)].groupby("year").agg(
            Papers=("openalex_id","count"), Citas=("cited_by_count","sum")
        ).reset_index()
        fig = go.Figure()
        fig.add_bar(x=by_yr["year"], y=by_yr["Papers"], name="Papers", marker_color=BLUE)
        fig.add_scatter(x=by_yr["year"], y=by_yr["Citas"], name="Citas (eje der.)",
                        mode="lines+markers", marker_color=RED, yaxis="y2")
        fig.update_layout(
            yaxis=dict(title="N° Papers"), yaxis2=dict(title="Citas", overlaying="y", side="right"),
            legend=dict(orientation="h", y=1.08), margin=dict(t=10,b=30,l=40,r=60), height=310,
        )
        st.plotly_chart(fig, width="stretch")

    with col2:
        sec("Calidad de publicaciones: cuartiles SJR")
        q_c = pub_enr["quartile"].value_counts().reset_index()
        q_c.columns = ["Cuartil","N"]
        q_c["Cuartil"] = pd.Categorical(q_c["Cuartil"],["Q1","Q2","Q3","Q4"],ordered=True)
        q_c = q_c.sort_values("Cuartil")
        fig2 = px.bar(q_c, x="Cuartil", y="N", text="N",
                      color="Cuartil",
                      color_discrete_map={"Q1":BLUE,"Q2":GREEN,"Q3":AMBER,"Q4":RED},
                      height=310)
        fig2.update_traces(textposition="outside")
        fig2.update_layout(showlegend=False, margin=dict(t=10,b=30))
        st.plotly_chart(fig2, width="stretch")

    col3, col4 = st.columns(2)

    with col3:
        sec("Financiamiento I+D por año (MM CLP)")
        by_a = anid.groupby("anio_concurso").agg(
            Proyectos=("titulo","count"),
            Monto_MM=("monto_programa_num", lambda x: x.sum()/1e6)
        ).reset_index().dropna()
        fig3 = go.Figure()
        fig3.add_bar(x=by_a["anio_concurso"], y=by_a["Proyectos"], name="N° Proyectos", marker_color=BLUE)
        fig3.add_scatter(x=by_a["anio_concurso"], y=by_a["Monto_MM"], name="MM CLP (eje der.)",
                         mode="lines+markers", marker_color=AMBER, yaxis="y2")
        fig3.update_layout(
            yaxis=dict(title="N° Proyectos"), yaxis2=dict(title="MM CLP", overlaying="y", side="right"),
            legend=dict(orientation="h", y=1.08), margin=dict(t=10,b=30,l=40,r=60), height=310,
        )
        st.plotly_chart(fig3, width="stretch")

    with col4:
        sec("Formación capital humano por tipo (2022–2025)")
        tc = ch["tipo_norm"].value_counts().reset_index()
        tc.columns = ["Tipo","N"]
        fig4 = px.bar(tc.sort_values("N"), x="N", y="Tipo", orientation="h",
                      color="Tipo", color_discrete_sequence=PALETTE, text="N", height=310)
        fig4.update_layout(showlegend=False, margin=dict(t=10,b=10))
        st.plotly_chart(fig4, width="stretch")

    # Alerta riesgo documental
    if ch_adv:
        cumpl = ch_adv.get("cumplimiento", {})
        rojo_c  = cumpl.get("centros_rojo", 0)
        rojo_t  = cumpl.get("tutores_rojo", 0)
        inf_pct = ch_ej.get("kpis", {}).get("documentacion_informe_pct", 7.14)
        st.markdown("")
        sec("⚠️ Alertas operativas")
        ac1, ac2, ac3 = st.columns(3)
        _ar = "background:#FDECEA;border-left:4px solid #C8102E;padding:8px 12px;border-radius:4px"
        _aa = "background:#FFF8E1;border-left:4px solid #F4A60D;padding:8px 12px;border-radius:4px"
        with ac1:
            st.markdown(f"<div style='{_ar}'>🔴 <b>{rojo_c} centros</b> con semáforo ROJO documental<br><small>Informe URL &lt; umbral mínimo</small></div>", unsafe_allow_html=True)
        with ac2:
            st.markdown(f"<div style='{_aa}'>🟡 <b>{rojo_t} tutores</b> en semáforo ROJO documental<br><small>de 36 tutores activos</small></div>", unsafe_allow_html=True)
        with ac3:
            st.markdown(f"<div style='{_aa}'>📋 Solo <b>{inf_pct}%</b> de registros tienen URL de informe<br><small>Meta mínima: 50%</small></div>", unsafe_allow_html=True)
