"""Section: Asistente I+D — CCHEN Observatorio"""
import datetime as _dt
import json as _json
import os
import re as _re

import pandas as pd
import streamlit as st

from .shared import (
    PORTALES_CIENTIFICOS,
    kpi, kpi_row, sec,
    _access_context,
    _load_convocatorias_data,
    _load_portafolio_seed,
    _load_entity_model_tables,
    _build_entity_observed_counts,
    _build_matching_profiles_summary,
    _extract_agreement_country_counts,
    generate_pdf_report,
)

import sys as _sys
import os as _os
_SCRIPTS_DIR = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))), "Scripts")
if _SCRIPTS_DIR not in _sys.path:
    _sys.path.insert(0, _SCRIPTS_DIR)
try:
    import semantic_search as _ss
    _SEM_AVAILABLE = _ss.is_available()
except Exception:
    _ss = None
    _SEM_AVAILABLE = False


def _build_assistant_system_prompt(ctx: dict, patents_key: str = "") -> tuple:
    """Build the assistant system prompt from context data.

    Returns (system_prompt_str, context_trace_dict).
    Callable outside Streamlit — does not import st or use st.secrets/st.session_state.
    """
    pub              = ctx.get("pub", pd.DataFrame())
    pub_enr          = ctx.get("pub_enr", pd.DataFrame())
    auth             = ctx.get("auth", pd.DataFrame())
    anid             = ctx.get("anid", pd.DataFrame())
    ch               = ctx.get("ch", pd.DataFrame())
    ch_ej            = ctx.get("ch_ej", {})
    ch_adv           = ctx.get("ch_adv", {})
    orcid            = ctx.get("orcid", pd.DataFrame())
    ror_registry     = ctx.get("ror_registry", pd.DataFrame())
    ror_pending_review = ctx.get("ror_pending_review", pd.DataFrame())
    funding_plus     = ctx.get("funding_plus", pd.DataFrame())
    iaea_tc          = ctx.get("iaea_tc", pd.DataFrame())
    matching_inst    = ctx.get("matching_inst", pd.DataFrame())
    entity_personas  = ctx.get("entity_personas", pd.DataFrame())
    entity_projects  = ctx.get("entity_projects", pd.DataFrame())
    entity_convocatorias = ctx.get("entity_convocatorias", pd.DataFrame())
    entity_links     = ctx.get("entity_links", pd.DataFrame())
    acuerdos         = ctx.get("acuerdos", pd.DataFrame())
    convenios        = ctx.get("convenios", pd.DataFrame())
    patents          = ctx.get("patents", pd.DataFrame())
    datacite         = ctx.get("datacite", pd.DataFrame())
    openaire         = ctx.get("openaire", pd.DataFrame())

    # ── Contexto de datos para el sistema ──
    _kpis_ch  = ch_ej.get("kpis", {}) if isinstance(ch_ej, dict) else {}
    _adv      = ch_adv if isinstance(ch_adv, dict) else {}
    _cap      = _adv.get("concentracion", {}) if _adv else {}
    _monto_mm = anid["monto_programa_num"].sum() / 1e6 if not anid.empty and "monto_programa_num" in anid.columns else 0.0
    _top_areas_raw = {}
    if not pub_enr.empty and "areas" in pub_enr.columns:
        for _row in pub_enr["areas"].dropna():
            for _a in str(_row).split(";"):
                _a = _a.strip()
                if _a:
                    _top_areas_raw[_a] = _top_areas_raw.get(_a, 0) + 1
    _top_areas = sorted(_top_areas_raw.items(), key=lambda x: -x[1])[:8]
    _top_journals = (
        pub_enr["source_title"].value_counts().head(5).to_dict()
        if not pub_enr.empty and "source_title" in pub_enr.columns
        else (pub["source"].value_counts().head(5).to_dict() if not pub.empty and "source" in pub.columns else {})
    )

    # Investigadores con afiliación CCHEN (desde authorships)
    if not auth.empty and "is_cchen_affiliation" in auth.columns:
        _auth_cchen = auth[auth["is_cchen_affiliation"] == True]
    else:
        _auth_cchen = pd.DataFrame()
    _top_inv = (
        _auth_cchen.groupby("author_name")["work_id"].nunique().sort_values(ascending=False).head(25)
        if not _auth_cchen.empty and "author_name" in _auth_cchen.columns and "work_id" in _auth_cchen.columns
        else pd.Series(dtype=int)
    )
    _inv_lista = ", ".join(f"{n} ({p} papers)" for n, p in _top_inv.items())
    _n_inv_unicos = _auth_cchen["author_name"].nunique() if not _auth_cchen.empty and "author_name" in _auth_cchen.columns else 0

    # Datos adicionales para el contexto
    if not pub.empty and "cited_by_count" in pub.columns:
        _top_papers = pub.nlargest(10, "cited_by_count")[["title", "year", "source", "cited_by_count"]]
        _papers_ctx = "\n".join(
            f"  - ({r.year}) {str(r.title)[:90]} | {int(r.cited_by_count)} citas | {r.source}"
            for _, r in _top_papers.iterrows()
        )
    else:
        _papers_ctx = "  - Sin datos de publicaciones disponibles."
    _anid_ctx = "\n".join(
        f"  - ({int(r.anio_concurso) if pd.notna(r.anio_concurso) else 'sin año'}) "
        f"{str(r.titulo)[:80]} | {r.instrumento_norm} | "
        f"{'$'+str(round(r.monto_programa_num/1e6,1))+'MM' if pd.notna(r.monto_programa_num) and r.monto_programa_num > 0 else 'sin monto'}"
        for _, r in anid.iterrows()
    ) if not anid.empty else "  - Sin proyectos ANID cargados."
    _collab_inst = (
        auth[auth["is_cchen_affiliation"] == False]["institution_name"].value_counts().head(12)
        if not auth.empty and "is_cchen_affiliation" in auth.columns and "institution_name" in auth.columns
        else pd.Series(dtype=int)
    )
    _collab_ctx = ", ".join(f"{i} ({n})" for i, n in _collab_inst.items()) if not _collab_inst.empty else "Sin colaboraciones registradas"
    _tutores_ctx = (
        ", ".join(f"{t} ({n} alumnos)" for t, n in ch["tutor"].value_counts().head(10).items())
        if not ch.empty and "tutor" in ch.columns else "Sin tutores registrados"
    )
    _centros_ctx = (
        ", ".join(f"{c} ({n})" for c, n in ch["centro_norm"].value_counts().items())
        if not ch.empty and "centro_norm" in ch.columns else "Sin centros registrados"
    )
    _univs_ctx = (
        ", ".join(f"{u} ({n})" for u, n in ch["universidad"].value_counts().head(10).items())
        if not ch.empty and "universidad" in ch.columns else "Sin universidades registradas"
    )

    try:
        _conv_df, _conv_mode_assistant, _conv_path_assistant = _load_convocatorias_data()
    except Exception:
        _conv_df, _conv_mode_assistant, _conv_path_assistant = pd.DataFrame(), "sin_datos", None
    _conv_calls = _conv_df[_conv_df["tipo_registro"] == "convocatoria"].copy() if not _conv_df.empty else pd.DataFrame()
    if not _conv_calls.empty:
        _conv_calls = _conv_calls.sort_values(["estado", "cierre_dt", "apertura_dt", "orden"], na_position="last")
    _conv_open = _conv_calls[_conv_calls["estado"] == "Abierto"] if not _conv_calls.empty else pd.DataFrame()
    _conv_next = _conv_calls[_conv_calls["estado"] == "Próximo"] if not _conv_calls.empty else pd.DataFrame()
    _conv_ctx_rows = []
    if not _conv_open.empty:
        for _, r in _conv_open.head(6).iterrows():
            _conv_ctx_rows.append(
                f"  - [Abierta] {str(r.titulo)[:88]} | {r.perfil_objetivo} | Cierre: {r.cierre_texto or 'por definir'}"
            )
    if not _conv_next.empty:
        for _, r in _conv_next.head(6).iterrows():
            _conv_ctx_rows.append(
                f"  - [Próxima] {str(r.titulo)[:88]} | {r.perfil_objetivo} | Apertura: {r.apertura_texto or 'por definir'}"
            )
    _conv_ctx = "\n".join(_conv_ctx_rows) if _conv_ctx_rows else "  - Sin convocatorias curadas disponibles."

    _matching_formal = matching_inst.copy() if matching_inst is not None and not (isinstance(matching_inst, pd.DataFrame) and matching_inst.empty) else pd.DataFrame()
    if not _matching_formal.empty and "score_total" in _matching_formal.columns:
        _matching_formal["score_total"] = pd.to_numeric(_matching_formal["score_total"], errors="coerce").fillna(0)
    _matching_summary_df = _build_matching_profiles_summary(_matching_formal) if not _matching_formal.empty else pd.DataFrame()
    _matching_ctx = "\n".join(
        f"  - {r.perfil}: unidad {r.unidad_responsable}; fuerza {r.fuerza_interna}; abiertas {int(r.abiertas)}; "
        f"próximas {int(r.proximas)}; señal {r.senal}; evidencia: {r.evidencia}"
        for _, r in _matching_summary_df.iterrows()
    ) if not _matching_summary_df.empty else "  - Sin matching institucional formal cargado."
    _matching_top_df = (
        _matching_formal.sort_values(["score_total", "estado"], ascending=[False, True]).head(8)
        if not _matching_formal.empty else pd.DataFrame()
    )
    _matching_top_ctx = "\n".join(
        f"  - [{r.estado}] {str(r.convocatoria_titulo)[:88]} | perfil {r.perfil_nombre} | unidad {r.owner_unit} | "
        f"score {int(round(r.score_total))} | elegibilidad {r.eligibility_status} | preparación {r.readiness_status} | "
        f"acción: {r.recommended_action}"
        for _, r in _matching_top_df.iterrows()
    ) if not _matching_top_df.empty else "  - Sin oportunidades formales priorizadas."
    _matching_updated = (
        str(_matching_formal["last_evaluated_at"].dropna().astype(str).max())
        if not _matching_formal.empty and "last_evaluated_at" in _matching_formal.columns
        and _matching_formal["last_evaluated_at"].notna().any()
        else "sin fecha"
    )

    try:
        _portfolio_df = _load_portafolio_seed()
    except Exception:
        _portfolio_df = pd.DataFrame()
    _portfolio_ctx = "\n".join(
        f"  - {r.nombre_activo} | TRL estimado {r.trl_estimado} | {r.potencial_transferencia}"
        for _, r in _portfolio_df.head(6).iterrows()
    ) if not _portfolio_df.empty else "  - No hay portafolio tecnológico cargado."

    try:
        _entity_df, _rel_df = _load_entity_model_tables()
    except Exception:
        _entity_df, _rel_df = pd.DataFrame(), pd.DataFrame()
    _entity_counts = _build_entity_observed_counts(
        pub=pub, ch=ch, auth=auth,
        entity_personas=entity_personas,
        entity_projects=entity_projects,
        entity_convocatorias=entity_convocatorias,
        entity_links=entity_links,
        acuerdos=acuerdos,
        convenios=convenios,
        orcid=orcid,
        patents=patents,
    )
    _entity_ctx = ", ".join(
        f"{row.entidad} ({int(_entity_counts.get(row.entidad, 0))})"
        for _, row in _entity_df.iterrows()
    ) if not _entity_df.empty else "Sin modelo de entidades cargado"
    _entity_operational_ctx = (
        f"personas canónicas {len(entity_personas)}, "
        f"proyectos canónicos {len(entity_projects)}, "
        f"convocatorias canónicas {len(entity_convocatorias)}, "
        f"enlaces operativos {len(entity_links)}"
    )
    _entity_relation_ctx = ", ".join(
        f"{rel} ({cnt})"
        for rel, cnt in entity_links["relation"].value_counts().head(6).items()
    ) if entity_links is not None and not entity_links.empty and "relation" in entity_links.columns else "Sin relaciones operativas resumidas"

    _orcid_top = (
        orcid.sort_values("orcid_works_count", ascending=False)
        [["full_name", "orcid_works_count"]]
        .head(10)
    ) if not orcid.empty and "orcid_works_count" in orcid.columns else pd.DataFrame()
    _orcid_ctx = ", ".join(
        f"{r.full_name} ({int(r.orcid_works_count)} works)"
        for _, r in _orcid_top.iterrows()
    ) if not _orcid_top.empty else "Sin top ORCID disponible"

    _conv_counterparties = (
        convenios["CONTRAPARTE DEL CONVENIO"].dropna().astype(str).value_counts().head(8)
        if not convenios.empty and "CONTRAPARTE DEL CONVENIO" in convenios.columns
        else pd.Series(dtype="int64")
    )
    _convenios_ctx = (
        ", ".join(f"{i} ({n})" for i, n in _conv_counterparties.items())
        if not _conv_counterparties.empty else "Sin contraparte resumida"
    )

    _agreement_countries = _extract_agreement_country_counts(acuerdos)
    _agreements_ctx = (
        ", ".join(f"{i} ({n})" for i, n in _agreement_countries.head(8).items())
        if not _agreement_countries.empty else "Sin países resumidos"
    )

    _funding_ctx = "\n".join(
        f"  - [{str(r.get('fuente') or 'Fuente complementaria')}] "
        f"{str(r.get('titulo') or r.get('programa') or 'Sin título')[:88]} | "
        f"instrumento: {str(r.get('instrumento') or 'sin instrumento')} | "
        f"área: {str(r.get('area_cchen') or 'sin área')} | "
        f"elegibilidad: {str(r.get('elegibilidad_base') or 'sin elegibilidad base')[:90]} | "
        f"confianza: {str(r.get('source_confidence') or 'sin clasificar')} | "
        f"verificado: {str(r.get('last_verified_at') or 'sin fecha')}"
        for _, r in funding_plus.head(8).iterrows()
    ) if not funding_plus.empty else "  - Sin financiamiento complementario estructurado cargado."
    _iaea_ctx = "\n".join(
        f"  - {str(r.get('proyecto_tc') or r.get('titulo') or r.get('fuente') or 'Proyecto TC')}"
        for _, r in iaea_tc.head(8).iterrows()
    ) if not iaea_tc.empty else "  - Sin registros IAEA TC cargados."
    _patents_ctx = (
        f"Se detectaron {len(patents)} patentes o registros de PI cargados."
        if not patents.empty else (
            "No hay patentes integradas en la base actual; la ruta oficial existe en "
            "`Scripts/fetch_patentsview_patents.py`, pero sigue pendiente la credencial `PATENTSVIEW_API_KEY`."
            if not patents_key else
            "No hay patentes integradas en la base actual; no se debe inferir un portafolio de PI todavía."
        )
    )
    _datacite_df = datacite.copy()
    if not _datacite_df.empty:
        if "publication_year" in _datacite_df.columns:
            _datacite_df["publication_year"] = pd.to_numeric(_datacite_df["publication_year"], errors="coerce")
        if "cchen_affiliated_creators" in _datacite_df.columns:
            _datacite_df["cchen_affiliated_creators"] = (
                pd.to_numeric(_datacite_df["cchen_affiliated_creators"], errors="coerce").fillna(0).astype(int)
            )
        _datacite_types_ctx = ", ".join(
            f"{k} ({v})" for k, v in _datacite_df["resource_type_general"].fillna("Sin tipo").value_counts().items()
        )
        _datacite_titles_ctx = "\n".join(
            f"  - ({int(r.publication_year) if pd.notna(r.publication_year) else 'sin año'}) "
            f"{str(r.title)[:100]} | {r.resource_type_general} | {r.publisher}"
            for _, r in _datacite_df.head(8).iterrows()
        )
        _datacite_direct = int((_datacite_df["cchen_affiliated_creators"] > 0).sum())
    else:
        _datacite_types_ctx = "Sin outputs DataCite cargados"
        _datacite_titles_ctx = "  - Sin outputs DataCite cargados."
        _datacite_direct = 0
    _openaire_df = openaire.copy()
    if not _openaire_df.empty:
        if "matched_cchen_researchers_count" in _openaire_df.columns:
            _openaire_df["matched_cchen_researchers_count"] = (
                pd.to_numeric(_openaire_df["matched_cchen_researchers_count"], errors="coerce").fillna(0).astype(int)
            )
        _openaire_scope_ctx = (
            ", ".join(f"{k} ({v})" for k, v in _openaire_df["match_scope"].fillna("sin clasificar").value_counts().items())
            if "match_scope" in _openaire_df.columns else "Sin clasificación de vínculo"
        )
        _openaire_types_ctx = (
            ", ".join(f"{k} ({v})" for k, v in _openaire_df["type"].fillna("Sin tipo").value_counts().items())
            if "type" in _openaire_df.columns else "Sin tipos OpenAIRE"
        )
        _openaire_titles_ctx = "\n".join(
            f"  - ({str(r.publication_date)[:10] if pd.notna(r.publication_date) else 'sin fecha'}) "
            f"{str(r.main_title)[:100]} | {r.type} | {r.match_scope}"
            for _, r in _openaire_df.head(8).iterrows()
        )
        _openaire_org_linked = (
            int(_openaire_df["match_scope"].isin(["cchen_ror_org", "cchen_name_org"]).sum())
            if "match_scope" in _openaire_df.columns else 0
        )
    else:
        _openaire_scope_ctx = "Sin outputs OpenAIRE cargados"
        _openaire_types_ctx = "Sin tipos OpenAIRE cargados"
        _openaire_titles_ctx = "  - Sin outputs OpenAIRE cargados."
        _openaire_org_linked = 0
    _ror_df = ror_registry.copy()
    _ror_pending_df = ror_pending_review.copy()
    if not _ror_df.empty:
        for _col in ["authorships_count", "orcid_profiles_count", "convenios_count"]:
            if _col in _ror_df.columns:
                _ror_df[_col] = pd.to_numeric(_ror_df[_col], errors="coerce").fillna(0).astype(int)
        _ror_total_linked = int(_ror_df["ror_id"].notna().sum()) if "ror_id" in _ror_df.columns else 0
        _ror_anchor_df = _ror_df[_ror_df["is_cchen_anchor"] == True] if "is_cchen_anchor" in _ror_df.columns else pd.DataFrame()
        _ror_anchor_ctx = (
            f"{_ror_anchor_df.iloc[0]['canonical_name']} | {_ror_anchor_df.iloc[0]['ror_id']} | "
            f"sitio: {_ror_anchor_df.iloc[0].get('website') or 'sin sitio'}"
            if not _ror_anchor_df.empty else "Sin institución ancla ROR cargada"
        )
        _ror_top_df = _ror_df[
            _ror_df["ror_id"].notna() &
            (_ror_df["canonical_name"] != "Comisión Chilena de Energía Nuclear")
        ].sort_values(["authorships_count", "orcid_profiles_count", "convenios_count"], ascending=False).head(10)
        _ror_top_ctx = ", ".join(
            f"{r.canonical_name} ({int(r.authorships_count)} autorías)"
            for _, r in _ror_top_df.iterrows()
        ) if not _ror_top_df.empty else "Sin instituciones colaboradoras con ROR resumidas"
    else:
        _ror_anchor_ctx = "Sin registro institucional ROR cargado"
        _ror_top_ctx = "Sin instituciones colaboradoras con ROR resumidas"
        _ror_total_linked = 0
    if not _ror_pending_df.empty:
        for _col in ["authorships_count", "orcid_profiles_count", "convenios_count", "signal_total"]:
            if _col in _ror_pending_df.columns:
                _ror_pending_df[_col] = pd.to_numeric(_ror_pending_df[_col], errors="coerce").fillna(0).astype(int)
        _ror_pending_count = len(_ror_pending_df)
        _ror_pending_priority_ctx = (
            ", ".join(
                f"{k} ({v})"
                for k, v in _ror_pending_df["priority_level"].fillna("Sin prioridad").value_counts().items()
            )
            if "priority_level" in _ror_pending_df.columns else "Sin prioridades clasificadas"
        )
        _ror_pending_top_ctx = (
            ", ".join(
                f"{r.canonical_name} [{r.priority_level}]"
                for _, r in _ror_pending_df.head(8).iterrows()
            )
            if "priority_level" in _ror_pending_df.columns
            else ", ".join(str(name) for name in _ror_pending_df["canonical_name"].head(8).tolist())
        )
    else:
        if not _ror_df.empty:
            _ror_pending_count = int(_ror_df[
                _ror_df["ror_id"].isna() &
                (
                    (_ror_df["authorships_count"] > 0) |
                    (_ror_df["orcid_profiles_count"] > 0) |
                    (_ror_df["convenios_count"] > 0)
                )
            ].shape[0])
        else:
            _ror_pending_count = 0
        _ror_pending_priority_ctx = "Sin cola priorizada cargada"
        _ror_pending_top_ctx = "Sin instituciones priorizadas resumidas"

    _cited_by_total = int(pub["cited_by_count"].sum()) if not pub.empty and "cited_by_count" in pub.columns else 0
    _cited_by_mean = pub["cited_by_count"].mean() if not pub.empty and "cited_by_count" in pub.columns else 0.0
    _oa_mean = round(100 * pub["is_oa"].mean(), 1) if not pub.empty and "is_oa" in pub.columns else 0.0
    _pub_enr_q1 = len(pub_enr[pub_enr["quartile"] == "Q1"]) if not pub_enr.empty and "quartile" in pub_enr.columns else 0
    _pub_enr_q2 = len(pub_enr[pub_enr["quartile"] == "Q2"]) if not pub_enr.empty and "quartile" in pub_enr.columns else 0
    _pub_enr_q3 = len(pub_enr[pub_enr["quartile"] == "Q3"]) if not pub_enr.empty and "quartile" in pub_enr.columns else 0
    _pub_enr_q4 = len(pub_enr[pub_enr["quartile"] == "Q4"]) if not pub_enr.empty and "quartile" in pub_enr.columns else 0
    _pub_enr_q12_pct = (
        round(100 * len(pub_enr[pub_enr["quartile"].isin(["Q1", "Q2"])]) / max(1, len(pub_enr[pub_enr["quartile"].notna()])), 1)
        if not pub_enr.empty and "quartile" in pub_enr.columns else 0.0
    )
    _ch_nombre_nunique = ch["nombre"].nunique() if not ch.empty and "nombre" in ch.columns else 0
    _ch_universidad_nunique = ch["universidad"].nunique() if not ch.empty and "universidad" in ch.columns else 0
    _ch_tipo_norm_ctx = (
        ", ".join(f"{k} ({v})" for k, v in ch["tipo_norm"].value_counts().items())
        if not ch.empty and "tipo_norm" in ch.columns else "Sin modalidades registradas"
    )

    _system_prompt = f"""Eres el asistente del Observatorio Tecnológico de la Comisión Chilena de Energía Nuclear (CCHEN), Chile. Apoyas al equipo de I+D con análisis de datos, redacción de informes técnicos y vigilancia tecnológica.

## Datos actuales del observatorio (cifras reales, extraídas de OpenAlex + ANID + registros internos)

### Producción Científica
- Total publicaciones: {len(pub)} trabajos (1990–2025)
- Citas totales: {_cited_by_total:,} | Promedio: {_cited_by_mean:.1f} citas/paper
- Papers con cuartil SJR: {len(pub_enr)} → Q1: {_pub_enr_q1}, Q2: {_pub_enr_q2}, Q3: {_pub_enr_q3}, Q4: {_pub_enr_q4}
- % Q1+Q2: {_pub_enr_q12_pct}%
- Acceso Abierto: {_oa_mean}%
- Top áreas: {', '.join(f"{a} ({n} papers)" for a,n in _top_areas)}
- Top journals: {', '.join(f"{j} ({n})" for j,n in list(_top_journals.items())[:5])}

### 10 Papers más citados de CCHEN
{_papers_ctx}

### Investigadores con afiliación CCHEN confirmada (fuente: OpenAlex)
- Total investigadores únicos: {_n_inv_unicos}
- Top 25 por producción: {_inv_lista}
- Instituciones colaboradoras frecuentes: {_collab_ctx}

### Proyectos ANID adjudicados (todos)
{_anid_ctx}
- Monto total: ${_monto_mm:.0f} MM CLP

### Capital Humano I+D (2022–2025)
- Registros: {len(ch)} | Personas únicas: {_ch_nombre_nunique} | Universidades: {_ch_universidad_nunique}
- Modalidades: {_ch_tipo_norm_ctx}
- Centros receptores: {_centros_ctx}
- Tutores principales: {_tutores_ctx}
- Universidades de origen (top 10): {_univs_ctx}
- % Ad honorem: {_kpis_ch.get('ad_honorem_pct', 57.1)}%
- Concentración centros HHI: {_cap.get('hhi_centros', 0.17)} — Top 3 (P2MC, PEC, CTNEV) = {_cap.get('top3_centros_share_pct', 63.4)}% de la formación

### Convocatorias curadas y matching (fuente: {getattr(_conv_path_assistant, 'name', 'sin archivo')} | modo: {_conv_mode_assistant})
- Convocatorias curadas: {len(_conv_calls)} | Abiertas: {len(_conv_open)} | Próximas: {len(_conv_next)}
- Matching institucional formal: {len(_matching_formal)} evaluaciones | última evaluación: {_matching_updated}
- Portales estratégicos internacionales monitoreados: {len(PORTALES_CIENTIFICOS)}
{_conv_ctx}

### Matching con perfiles CCHEN
{_matching_ctx}

### Top oportunidades priorizadas (matching formal)
{_matching_top_ctx}

### Transferencia y portafolio tecnológico
- Activos semilla en portafolio: {len(_portfolio_df)}
- Fondos complementarios registrados: {len(funding_plus)}
- Registros IAEA TC: {len(iaea_tc)}
- {_patents_ctx}
{_portfolio_ctx}

### Outputs DataCite asociados a CCHEN
- Outputs DataCite: {len(_datacite_df)} | Con creador CCHEN explícito: {_datacite_direct}
- Tipos observados: {_datacite_types_ctx}
{_datacite_titles_ctx}

### Outputs OpenAIRE asociados a investigadores CCHEN
- Outputs OpenAIRE agregados: {len(_openaire_df)} | Con señal institucional CCHEN: {_openaire_org_linked}
- Tipos observados: {_openaire_types_ctx}
- Calidad del vínculo: {_openaire_scope_ctx}
{_openaire_titles_ctx}

### Convenios, acuerdos y perfiles de investigadores
- Convenios nacionales: {len(convenios)} | Contrapartes frecuentes: {_convenios_ctx}
- Acuerdos internacionales: {len(acuerdos)} | Países/regiones frecuentes: {_agreements_ctx}
- Perfiles ORCID cargados: {len(orcid)} | Top perfiles por works: {_orcid_ctx}

### Registro institucional ROR
- Institución ancla CCHEN: {_ror_anchor_ctx}
- Instituciones normalizadas con ROR: {_ror_total_linked}
- Pendientes de revisión manual sin ROR: {_ror_pending_count}
- Distribución de prioridad en cola ROR: {_ror_pending_priority_ctx}
- Top colaboradoras con ROR: {_ror_top_ctx}
- Pendientes priorizados destacados: {_ror_pending_top_ctx}

### Financiamiento complementario y cooperación técnica
{_funding_ctx}
{_iaea_ctx}

### Modelo unificado y gobernanza
- Entidades modeladas: {len(_entity_df)} | Relaciones definidas: {len(_rel_df)}
- Registros observados por entidad: {_entity_ctx}
- Registros operativos: {_entity_operational_ctx}
- Relaciones operativas más frecuentes: {_entity_relation_ctx}

## Instrucciones
- Responde en español, con tono técnico-profesional para informes internos CCHEN.
- Cuando generes informes usa secciones, bullets y cifras concretas de los datos de arriba.
- Los investigadores listados tienen afiliación CCHEN verificada por OpenAlex — úsalos cuando pregunten por investigadores de la institución.
- Cuando hables de instituciones o colaboraciones, prioriza nombres canónicos y ROR si está disponible.
- Si preguntan por convocatorias u oportunidades, prioriza el matching institucional formal y cita perfil, score_total, eligibility_status, readiness_status, owner_unit, evidence_summary y last_evaluated_at.
- Si preguntan por financiamiento, usa la tabla curada de funding complementario y cita fuente, instrumento, elegibilidad_base, source_confidence y last_verified_at.
- Si preguntan por transferencia o portafolio tecnológico, aclara que el portafolio actual es una semilla analítica y que requiere validación técnica antes de tratarlo como inventario formal.
- Si usas OpenAIRE, diferencia claramente entre vínculo fuerte (`cchen_ror_org` o `cchen_name_org`) y vínculo débil (`author_orcid_only`).
- Si preguntan por gobernanza o integración de datos, usa los registros canónicos de personas, proyectos, convocatorias e institution_registry como marco operativo; aclara que no existe aún un grafo persistente separado.
- Si una capa no está suficientemente poblada (por ejemplo, patentes o IAEA TC), dilo explícitamente y no extrapoles más allá de la evidencia.
- Para comparaciones internacionales usa tu conocimiento general aclarando que es referencial.
- No inventes cifras que no estén arriba. Si algo no está en los datos, dilo explícitamente.
"""

    _context_trace = {
        "pub": len(pub),
        "pub_enr": len(pub_enr),
        "anid": len(anid),
        "ch": len(ch),
        "orcid": len(orcid),
        "conv_calls": len(_conv_calls),
        "conv_open": len(_conv_open),
        "matching_formal": len(_matching_formal),
        "portfolio": len(_portfolio_df),
        "patents": len(patents),
        "funding_plus": len(funding_plus),
        "iaea_tc": len(iaea_tc),
        "entity_personas": len(entity_personas),
        "convenios": len(convenios),
        "acuerdos": len(acuerdos),
        "datacite": len(datacite),
        "openaire": len(openaire),
    }

    return _system_prompt, _context_trace


def render(ctx: dict) -> None:
    """Render the Asistente I+D section."""
    pub              = ctx["pub"]
    pub_enr          = ctx["pub_enr"]
    auth             = ctx["auth"]
    anid             = ctx["anid"]
    ch               = ctx["ch"]
    ch_ej            = ctx["ch_ej"]
    ch_adv           = ctx["ch_adv"]
    orcid            = ctx["orcid"]
    ror_registry     = ctx["ror_registry"]
    ror_pending_review = ctx["ror_pending_review"]
    funding_plus     = ctx["funding_plus"]
    iaea_tc          = ctx["iaea_tc"]
    matching_inst    = ctx["matching_inst"]
    entity_personas  = ctx["entity_personas"]
    entity_projects  = ctx["entity_projects"]
    entity_convocatorias = ctx["entity_convocatorias"]
    entity_links     = ctx["entity_links"]
    acuerdos         = ctx["acuerdos"]
    convenios        = ctx["convenios"]
    patents          = ctx["patents"]
    datacite         = ctx["datacite"]
    openaire         = ctx["openaire"]

    assistant_access = _access_context()
    st.title("Asistente I+D — CCHEN")
    st.caption("Analiza las capas integradas del observatorio y genera informes técnicos con IA")
    st.divider()

    if assistant_access["auth_enabled"] and not assistant_access["can_view_sensitive"]:
        st.warning(
            "El asistente queda restringido mientras no exista una sesión autorizada, "
            "porque el prompt incorpora contexto de capital humano y otros datos internos."
        )
        if assistant_access.get("auth_mode") == "internal":
            st.info("Tu usuario beta no tiene habilitado el acceso sensible requerido para esta sección.")
        elif assistant_access["auth_supported"] and not assistant_access["is_logged_in"]:
            if st.button("Iniciar sesión para habilitar el asistente", key="assistant_login"):
                st.login()
        st.stop()

    _patents_key = os.environ.get("PATENTSVIEW_API_KEY") or st.secrets.get("PATENTSVIEW_API_KEY", "")
    _system_prompt, _ctx_trace = _build_assistant_system_prompt(ctx, patents_key=_patents_key)

    # ── API Key (Groq) ──
    api_key = os.environ.get("GROQ_API_KEY") or st.secrets.get("GROQ_API_KEY", "")
    if not api_key:
        st.warning("⚠️ Configura tu `GROQ_API_KEY` en los secrets de Streamlit Cloud para activar el asistente.")
        st.code('GROQ_API_KEY = "gsk_..."', language="toml")
        st.stop()

    # ── Prompts rápidos ──
    _pr_col, _cl_col = st.columns([4, 1])
    with _pr_col:
        st.markdown(
            "<p style='font-size:0.78rem;font-weight:500;color:#64748B;"
            "letter-spacing:0.4px;text-transform:uppercase;margin:0'>Consultas frecuentes</p>",
            unsafe_allow_html=True
        )
    with _cl_col:
        if st.button("Limpiar chat", width="stretch"):
            st.session_state.messages = []
            st.rerun()
    q1, q2, q3, q4 = st.columns(4)
    prompt_rapido = ""
    if q1.button("Producción científica", width="stretch"):
        prompt_rapido = "Genera un informe técnico ejecutivo sobre la producción científica de CCHEN. Incluye: evolución temporal, calidad (cuartiles), áreas temáticas, colaboración internacional y comparación con el promedio latinoamericano en nuclear."
    if q2.button("Financiamiento ANID", width="stretch"):
        prompt_rapido = "Analiza el portafolio de financiamiento ANID de CCHEN. ¿Cuál es la estrategia de captación de fondos? ¿Qué oportunidades de mejora identificas para diversificar las fuentes?"
    if q3.button("Capital humano I+D", width="stretch"):
        prompt_rapido = "Elabora un diagnóstico del capital humano I+D de CCHEN (2022–2025). Incluye composición por modalidad, concentración operativa (HHI), riesgos identificados y recomendaciones para fortalecer la formación."
    if q4.button("Resumen ejecutivo", width="stretch"):
        prompt_rapido = "Redacta un resumen ejecutivo de 1 página del Observatorio Tecnológico Virtual de CCHEN para presentar a directivos. Incluye indicadores clave, estado actual y principales hallazgos."
    q5, q6, q7, q8 = st.columns(4)
    if q5.button("Perfil de investigadores", width="stretch"):
        prompt_rapido = "Describe el perfil de los investigadores más productivos de CCHEN según los datos del observatorio. ¿Quiénes son los líderes en producción científica? ¿En qué áreas temáticas se concentran? ¿Qué instituciones colaboran más frecuentemente?"
    if q6.button("Colaboración internacional", width="stretch"):
        prompt_rapido = "Analiza la red de colaboración internacional de CCHEN. ¿Con qué instituciones y países colabora más? ¿Qué oportunidades estratégicas de colaboración identifica para fortalecer la posición internacional de CCHEN en energía nuclear?"
    if q7.button("Convocatorias + matching", width="stretch"):
        prompt_rapido = "Usando el matching institucional formal, identifica las oportunidades abiertas y próximas más relevantes para CCHEN. Organízalas por perfil, incluye score_total, eligibility_status, readiness_status, owner_unit y recommended_action, y explica por qué cada una calza o no con la evidencia interna."
    if q8.button("Transferencia / portafolio", width="stretch"):
        prompt_rapido = "Con base en el portafolio tecnológico semilla, los proyectos ANID, publicaciones, convenios y financiamiento complementario, elabora un diagnóstico de transferencia para CCHEN. Distingue claramente entre capacidades observables, activos por validar y vacíos críticos como patentes o TRL."

    # ── Historial de chat ──
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # ── Input ──
    if _SEM_AVAILABLE:
        st.caption("🔍 Búsqueda semántica activa — el asistente recupera papers relevantes por consulta.")
    else:
        st.caption("💡 Para activar búsqueda semántica ejecuta: `python3 Scripts/build_embeddings.py`")
    user_input = st.chat_input("Escribe tu consulta o solicita un informe técnico...") or prompt_rapido
    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        _rag_context = ""
        if _SEM_AVAILABLE and user_input:
            try:
                _rag_df = _ss.search(user_input, top_k=5)
                if not _rag_df.empty:
                    _rag_lines = []
                    for _, _r in _rag_df.iterrows():
                        _title = str(_r.get("title", ""))[:100]
                        _year = _r.get("year", "")
                        _score = _r.get("score", 0)
                        _doi = _r.get("doi", "")
                        _abstract = str(_r.get("abstract", ""))[:200]
                        _rag_lines.append(f"  - [{_score:.2f}] {_title} ({_year}){' | doi:'+_doi if _doi else ''}{chr(10)+'    '+_abstract if _abstract and _abstract != 'nan' else ''}")
                    _rag_context = "\n\n### Publicaciones CCHEN más relevantes para esta consulta (búsqueda semántica):\n" + "\n".join(_rag_lines)
            except Exception:
                pass

        with st.chat_message("assistant"):
            reply = None
            client = None
            try:
                from groq import Groq as _Groq
                client = _Groq(api_key=api_key)
                _stream = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    max_tokens=2048,
                    stream=True,
                    messages=[{"role": "system", "content": _system_prompt + _rag_context}] +
                             [{"role": m["role"], "content": m["content"]}
                              for m in st.session_state.messages],
                )
                reply = st.write_stream(
                    (chunk.choices[0].delta.content or "")
                    for chunk in _stream
                    if chunk.choices
                )
            except Exception as e:
                # Fallback: respuesta basada en el contexto sin LLM
                _q = user_input.lower()
                if any(w in _q for w in ["publicacion", "paper", "artículo", "articulo"]):
                    reply = (
                        f"**Producción científica CCHEN** (fuente: OpenAlex)\n\n"
                        f"- Total publicaciones indexadas: **{len(pub):,}**\n"
                        f"- Rango: {int(pub['year'].min())}–{int(pub['year'].max())}\n"
                        f"- Con cuartil SJR: {len(pub_enr):,}\n\n"
                        f"_(Respuesta simplificada — servicio LLM no disponible: {e})_"
                    )
                elif any(w in _q for w in ["investigador", "autor", "orcid"]):
                    reply = (
                        f"**Investigadores CCHEN** (fuente: ORCID + OpenAlex)\n\n"
                        f"- Perfiles ORCID activos: **{len(orcid):,}**\n"
                        f"- Autorías registradas: **{len(auth):,}**\n\n"
                        f"_(Respuesta simplificada — servicio LLM no disponible: {e})_"
                    )
                elif any(w in _q for w in ["anid", "financiamiento", "fondo", "proyecto"]):
                    reply = (
                        f"**Financiamiento I+D CCHEN** (fuente: ANID)\n\n"
                        f"- Proyectos ANID adjudicados: **{len(anid):,}**\n\n"
                        f"_(Respuesta simplificada — servicio LLM no disponible: {e})_"
                    )
                else:
                    reply = (
                        f"⚠️ El servicio LLM (Groq) no está disponible en este momento: `{e}`\n\n"
                        f"Puedes explorar los datos directamente en las secciones del panel lateral."
                    )
                st.markdown(reply)
            st.session_state.messages.append({"role": "assistant", "content": reply})

            # ── Decisión dinámica de gráfico vía LLM ─────────────────────────
            _chart_decision = {}
            if client is not None:
                try:
                    _decision_prompt = (
                        "Analiza esta consulta y respuesta del Observatorio CCHEN y decide qué visualización "
                        "incluir en el informe PDF. Responde SOLO con un JSON válido, sin texto adicional.\n\n"
                        f"CONSULTA: {user_input}\n\nRESPUESTA: {reply[:800]}\n\n"
                        "Devuelve un JSON con esta estructura exacta:\n"
                        '{"chart": "<tipo>", "researchers": ["nombre1","nombre2"], '
                        '"keyword": "<tema_filtro>", "start_year": <año_inicio>, "end_year": <año_fin>}\n\n'
                        "Valores válidos para 'chart': investigators, funding, quality, collaboration, "
                        "production, human_capital\n"
                        "- investigators: si se pregunta por personas, investigadores o líneas de investigación\n"
                        "- funding: si se pregunta por proyectos, fondos ANID, financiamiento, convocatorias o transferencia\n"
                        "- quality: si se pregunta por calidad de publicaciones, cuartiles, acceso abierto\n"
                        "- collaboration: si se pregunta por colaboraciones, redes, alianzas internacionales, convenios o acuerdos\n"
                        "- production: si se pregunta por producción científica general, evolución, tendencias\n"
                        "- human_capital: si se pregunta por capital humano, formación, becas, tesistas\n"
                        "Para 'researchers': lista los nombres exactos de investigadores mencionados en la respuesta "
                        "(máximo 8). Usa [] si no hay nombres específicos.\n"
                        "Para 'keyword': palabra clave del tema (ej: 'plasma', 'nuclear', 'dosimetría'). Usa null si es general.\n"
                        "Para 'start_year' y 'end_year': rango temporal mencionado o null si no aplica."
                    )
                    _dec_resp = client.chat.completions.create(
                        model="llama-3.1-8b-instant",
                        max_tokens=200,
                        temperature=0,
                        messages=[{"role": "user", "content": _decision_prompt}],
                    )
                    _dec_text = _dec_resp.choices[0].message.content.strip()
                    _chart_decision = {}
                    try:
                        _chart_decision = _json.loads(_dec_text)
                    except _json.JSONDecodeError:
                        # Buscar primer { ... } balanceado
                        _depth, _start = 0, -1
                        for _ci, _ch in enumerate(_dec_text):
                            if _ch == "{":
                                if _depth == 0:
                                    _start = _ci
                                _depth += 1
                            elif _ch == "}":
                                _depth -= 1
                                if _depth == 0 and _start != -1:
                                    try:
                                        _chart_decision = _json.loads(_dec_text[_start:_ci + 1])
                                    except _json.JSONDecodeError:
                                        pass
                                    break
                except Exception:
                    pass  # Si falla, generate_pdf_report usa detección por keywords

            # ── Botón exportar informe PDF ────────────────────────────────────
            _fecha = _dt.datetime.now().strftime("%Y%m%d_%H%M")
            _pdf_bytes = generate_pdf_report(
                user_input, reply,
                pub_data=pub, pub_enr_data=pub_enr,
                auth_data=auth, anid_data=anid, ch_data=ch,
                chart_decision=_chart_decision,
            )
            if _pdf_bytes:
                st.download_button(
                    "Exportar informe PDF",
                    data=_pdf_bytes,
                    file_name=f"informe_cchen_{_fecha}.pdf",
                    mime="application/pdf",
                    width="content",
                )
            else:
                st.caption("⚠️ No se pudo generar el PDF (reportlab no disponible).")

        if prompt_rapido:
            st.rerun()
