"""Section: Formación de Capacidades — CCHEN Observatorio"""
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from .shared import (
    BLUE, RED, GREEN, AMBER, PURPLE, PALETTE,
    kpi, kpi_row, sec, make_csv,
    semaforo_badge,
    _access_context,
)


def render(ctx: dict) -> None:
    """Render the Formación de Capacidades section."""
    ch       = ctx["ch"]
    ch_ej    = ctx["ch_ej"]
    ch_adv   = ctx["ch_adv"]
    ch_cumpl = ctx["ch_cumpl"]
    ch_trans = ctx["ch_trans"]

    cap_access = _access_context()
    st.title("Formación de Capacidades I+D")
    if cap_access["auth_enabled"] and not cap_access["can_view_sensitive"]:
        st.warning(
            "Vista protegida: estás viendo solo agregados. "
            "Inicia sesión con una cuenta autorizada para ver registros nominativos."
        )
    st.caption("Fuente: Registro interno CCHEN · 112 registros · 97 personas · 2022–2025")
    st.divider()

    with st.expander("Filtros", expanded=True):
        cols_cfg = st.columns(4 if cap_access["can_view_sensitive"] else 3)
        with cols_cfg[0]:
            anios_ch = sorted(ch["anio_hoja"].dropna().astype(int).unique())
            anio_sel = st.multiselect("Año", anios_ch, default=anios_ch)
        with cols_cfg[1]:
            tipos_ch = ["Todos"] + sorted(ch["tipo_norm"].dropna().unique())
            tipo_ch = st.selectbox("Modalidad", tipos_ch)
        with cols_cfg[2]:
            centros = ["Todos"] + sorted(ch["centro_norm"].dropna().unique())
            centro_sel = st.selectbox("Centro", centros)
        busq_ch = ""
        if cap_access["can_view_sensitive"]:
            with cols_cfg[3]:
                busq_ch = st.text_input("🔎 Nombre / universidad", placeholder="ej: USACH, Lisboa")

    df_c = ch.copy()
    if anio_sel:
        df_c = df_c[df_c["anio_hoja"].isin(anio_sel)]
    if tipo_ch != "Todos":
        df_c = df_c[df_c["tipo_norm"] == tipo_ch]
    if centro_sel != "Todos":
        df_c = df_c[df_c["centro_norm"] == centro_sel]
    if busq_ch:
        df_c = df_c[
            df_c["nombre"].str.contains(busq_ch, case=False, na=False) |
            df_c["universidad"].str.contains(busq_ch, case=False, na=False)
        ]

    # KPIs desde JSON precomputado
    kpis_c = ch_ej.get("kpis", {})
    adv_c  = ch_adv

    kpi_row(
        kpi("Registros filtrados",    f"{len(df_c)}"),
        kpi("Personas únicas",        f"{df_c['nombre'].nunique()}"),
        kpi("Universidades",          f"{df_c['universidad'].nunique()}"),
        kpi("% Ad honorem",           f"{kpis_c.get('ad_honorem_pct', 57.14)}%", "del total registros"),
        kpi("Monto total honorarios", "$64.7 MM", "CLP remunerados"),
    )

    col1, col2 = st.columns(2)

    with col1:
        sec("Por modalidad de formación")
        tc = df_c["tipo_norm"].value_counts().reset_index()
        tc.columns = ["Tipo", "N"]
        fig1 = px.bar(tc.sort_values("N"), x="N", y="Tipo", orientation="h",
                      color="Tipo", color_discrete_sequence=PALETTE, text="N", height=300)
        fig1.update_layout(showlegend=False, margin=dict(t=10, b=10))
        st.plotly_chart(fig1, width="stretch")

    with col2:
        sec("Evolución anual por modalidad")
        by_at = df_c.groupby(["anio_hoja", "tipo_norm"]).size().reset_index(name="N")
        fig2 = px.bar(by_at, x="anio_hoja", y="N", color="tipo_norm",
                      color_discrete_sequence=PALETTE, barmode="stack", height=300,
                      labels={"anio_hoja": "Año", "N": "Personas", "tipo_norm": "Modalidad"})
        fig2.update_layout(margin=dict(t=10, b=30), legend=dict(orientation="h", y=1.1))
        st.plotly_chart(fig2, width="stretch")

    col3, col4 = st.columns(2)

    with col3:
        sec("Por centro CCHEN")
        cc = df_c["centro_norm"].value_counts().reset_index()
        cc.columns = ["Centro", "N"]
        fig3 = px.bar(cc.sort_values("N"), x="N", y="Centro", orientation="h",
                      color_discrete_sequence=[BLUE], text="N", height=340)
        fig3.update_layout(showlegend=False, margin=dict(t=10, b=10))
        st.plotly_chart(fig3, width="stretch")

    with col4:
        sec("Top 10 universidades de origen")
        uc = df_c["universidad"].value_counts().head(10).reset_index()
        uc.columns = ["Universidad", "N"]
        fig4 = px.bar(uc.sort_values("N"), x="N", y="Universidad", orientation="h",
                      color_discrete_sequence=[RED], text="N", height=340)
        fig4.update_layout(showlegend=False, margin=dict(t=10, b=10))
        st.plotly_chart(fig4, width="stretch")

    # Semáforo documental (datos precomputados)
    if not ch_cumpl.empty:
        sec("🚦 Semáforo de cumplimiento documental por centro")
        cols_sem = st.columns(min(len(ch_cumpl), 5))
        for i, (_, row) in enumerate(ch_cumpl.iterrows()):
            with cols_sem[i % 5]:
                semaf = row["semaforo_documental"]
                color = {"VERDE": GREEN, "AMARILLO": AMBER, "ROJO": RED}.get(semaf, "#999")
                icon  = {"VERDE": "🟢", "AMARILLO": "🟡", "ROJO": "🔴"}.get(semaf, "⚪")
                st.markdown(
                    f"<div style='background:white;border-left:4px solid {color};padding:10px;"
                    f"border-radius:6px;box-shadow:0 1px 4px rgba(0,0,0,0.08);margin-bottom:8px'>"
                    f"<b>{row['entidad']}</b><br>{icon} {semaf}<br>"
                    f"<small>Obs: {row['obs_url_pct']}% · Inf: {row['informe_url_pct']}%</small></div>",
                    unsafe_allow_html=True
                )
        st.markdown("")

    # Funnels y trayectorias (datos precomputados)
    col5, col6 = st.columns(2)

    with col5:
        sec("Funnel de trayectoria (Práctica → otras modalidades)")
        if adv_c:
            traj = adv_c.get("trayectorias", {})
            base = traj.get("funnel_practica_base", 41)
            funnel_data = {
                "Prácticas (base)": base,
                "→ Memorista": traj.get("funnel_practica_to_memorista", 1),
                "→ Tesista":   traj.get("funnel_practica_to_tesista", 0),
                "→ Honorarios": traj.get("funnel_practica_to_honorarios", 0),
            }
            fig5 = go.Figure(go.Funnel(
                y=list(funnel_data.keys()),
                x=list(funnel_data.values()),
                textinfo="value+percent initial",
                marker=dict(color=[BLUE, GREEN, AMBER, RED]),
            ))
            fig5.update_layout(margin=dict(t=10, b=10), height=280)
            st.plotly_chart(fig5, width="stretch")

    with col6:
        sec("Transiciones observadas entre modalidades")
        if not ch_trans.empty:
            ch_trans["Transición"] = ch_trans["tipo_origen"] + " → " + ch_trans["tipo_destino"]
            fig6 = px.bar(ch_trans.sort_values("transiciones"), x="transiciones", y="Transición",
                          orientation="h", color_discrete_sequence=[PURPLE], text="transiciones",
                          height=280)
            fig6.update_layout(showlegend=False, margin=dict(t=10, b=10), xaxis_title="N° casos")
            st.plotly_chart(fig6, width="stretch")

    # Concentración (HHI)
    if adv_c:
        cap = adv_c.get("capacidad", {})
        sec("Concentración operativa (índice HHI)")
        hc1, hc2 = st.columns(2)
        with hc1:
            hhi_c = cap.get("hhi_centros", 0.17)
            pct_c = cap.get("top3_centros_share_pct", 63.4)
            nivel = "Alta" if hhi_c > 0.15 else "Moderada" if hhi_c > 0.10 else "Baja"
            _aa = "background:#FFF8E1;border-left:4px solid #F4A60D;padding:8px 12px;border-radius:4px"
            st.markdown(
                f"<div style='{_aa}'>📊 <b>Concentración centros:</b> HHI = {hhi_c} ({nivel})<br>"
                f"Top 3 centros concentran el <b>{pct_c}%</b> de la formación (P2MC, PEC, CTNEV)</div>",
                unsafe_allow_html=True,
            )
        with hc2:
            hhi_t = cap.get("hhi_tutores", 0.055)
            pct_t = cap.get("top3_tutores_share_pct", 29.5)
            nivel_t = "Alta" if hhi_t > 0.15 else "Moderada" if hhi_t > 0.10 else "Baja"
            _av = "background:#E8F5E9;border-left:4px solid #00A896;padding:8px 12px;border-radius:4px"
            st.markdown(
                f"<div style='{_av}'>📊 <b>Concentración tutores:</b> HHI = {hhi_t} ({nivel_t})<br>"
                f"Top 3 tutores concentran el <b>{pct_t}%</b> de los registros</div>",
                unsafe_allow_html=True,
            )
        st.markdown("")

    if cap_access["can_view_sensitive"]:
        sec(f"Tabla de personas — {len(df_c)} registros")
        df_cs = df_c[[
            "anio_hoja", "nombre", "tipo_norm", "centro_norm", "universidad",
            "duracion_dias", "tutor", "ad_honorem"
        ]].rename(columns={
            "anio_hoja": "Año", "nombre": "Nombre", "tipo_norm": "Modalidad",
            "centro_norm": "Centro", "universidad": "Universidad",
            "duracion_dias": "Días", "tutor": "Tutor/a", "ad_honorem": "Ad honorem"
        }).sort_values("Año", ascending=False)
        st.dataframe(df_cs, width="stretch", height=420,
                     column_config={"Ad honorem": st.column_config.CheckboxColumn("Ad honorem")})
        st.download_button("Exportar registro CSV", make_csv(df_cs),
                           "capital_humano_cchen.csv", "text/csv")
    else:
        sec("Tabla agregada — vista protegida")
        df_cs = (
            df_c.groupby(["anio_hoja", "tipo_norm", "centro_norm", "universidad"], dropna=False)
            .size()
            .reset_index(name="Registros")
            .rename(columns={
                "anio_hoja": "Año",
                "tipo_norm": "Modalidad",
                "centro_norm": "Centro",
                "universidad": "Universidad",
            })
            .sort_values(["Año", "Registros"], ascending=[False, False])
        )
        st.dataframe(df_cs, width="stretch", height=420)
        st.download_button(
            "Exportar resumen CSV",
            make_csv(df_cs),
            "capital_humano_cchen_agregado.csv",
            "text/csv",
        )
