"""
CCHEN Observatorio Tecnológico — Plataforma 3 en 1
Vigilancia e Inteligencia I+D+i+Tt · Comisión Chilena de Energía Nuclear
"""
import json
import os
import hashlib
import ast
import re
import datetime as dt
from html import unescape as html_unescape
from pathlib import Path
import matplotlib
matplotlib.use("Agg")  # forzar backend sin pantalla antes de cualquier import de pyplot
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import math
import data_loader as _data_loader
from sections.shared import (
    _available_sections,
    _get_secret_block,
    _streamlit_auth_supported,
    _auth_enabled,
    _access_context,
    _internal_auth_config,
    _internal_auth_login,
    _internal_auth_logout,
    _observatorio_app_mode,
    _section_visibility,
)


_DEFAULT_DATA_ROOT = Path(os.getenv("CCHEN_DATA_ROOT", str(Path(__file__).resolve().parent.parent / "Data")))
BASE = getattr(_data_loader, "BASE", _DEFAULT_DATA_ROOT)


def _compat_read_csv(*parts: str) -> pd.DataFrame:
    path = BASE.joinpath(*parts)
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path, encoding="utf-8-sig")
    except Exception:
        return pd.read_csv(path)


def _compat_read_json(*parts: str):
    path = BASE.joinpath(*parts)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _empty_loader():
    return pd.DataFrame()


def _csv_loader(*parts: str):
    def _loader():
        return _compat_read_csv(*parts)
    return _loader


def _json_loader(*parts: str):
    def _loader():
        return _compat_read_json(*parts)
    return _loader


def _resolve_loader(name: str, fallback=None):
    value = getattr(_data_loader, name, None)
    if value is not None:
        return value
    if fallback is not None:
        return fallback
    raise ImportError(f"data_loader no expone `{name}` y no existe fallback de compatibilidad")


load_publications = _resolve_loader("load_publications")
load_publications_enriched = _resolve_loader("load_publications_enriched")
load_authorships = _resolve_loader("load_authorships")
load_anid = _resolve_loader("load_anid")
load_capital_humano = _resolve_loader("load_capital_humano")
load_ch_resumen_ejecutivo = _resolve_loader(
    "load_ch_resumen_ejecutivo",
    _json_loader("Capital humano CCHEN", "salida_dataset_maestro", "resumen_ejecutivo.json"),
)
load_ch_analisis_avanzado = _resolve_loader(
    "load_ch_analisis_avanzado",
    _json_loader("Capital humano CCHEN", "salida_dataset_maestro", "analisis_avanzado", "resumen_analisis_avanzado.json"),
)
load_ch_cumplimiento_centros = _resolve_loader("load_ch_cumplimiento_centros", _empty_loader)
load_ch_transiciones = _resolve_loader("load_ch_transiciones", _empty_loader)
load_ch_participacion_tipo_anio = _resolve_loader("load_ch_participacion_tipo_anio", _empty_loader)
load_patents = _resolve_loader("load_patents", _csv_loader("Patents", "cchen_patents_uspto.csv"))
get_source_timestamps = _resolve_loader("get_source_timestamps", lambda: {})
load_dian_publications = _resolve_loader("load_dian_publications", _empty_loader)
load_crossref_enriched = _resolve_loader("load_crossref_enriched")
load_concepts = _resolve_loader("load_concepts")
load_datacite_outputs = _resolve_loader("load_datacite_outputs", _csv_loader("ResearchOutputs", "cchen_datacite_outputs.csv"))
load_openaire_outputs = _resolve_loader("load_openaire_outputs", _csv_loader("ResearchOutputs", "cchen_openaire_outputs.csv"))
load_grants_openalex = _resolve_loader("load_grants_openalex", _empty_loader)
load_orcid_researchers = _resolve_loader("load_orcid_researchers", _csv_loader("Researchers", "cchen_researchers_orcid.csv"))
load_padron_academicos_provisional = _resolve_loader(
    "load_padron_academicos_provisional",
    _csv_loader("Researchers", "cchen_planta_estado_orcid_actual.csv"),
)
load_ror_registry = _resolve_loader("load_ror_registry", _csv_loader("Institutional", "cchen_institution_registry.csv"))
load_ror_pending_review = _resolve_loader("load_ror_pending_review", _csv_loader("Institutional", "ror_pending_review.csv"))
load_funding_complementario = _resolve_loader("load_funding_complementario", _csv_loader("Funding", "cchen_funding_complementario.csv"))
load_iaea_tc = _resolve_loader("load_iaea_tc", _csv_loader("Funding", "cchen_iaea_tc.csv"))
load_perfiles_institucionales = _resolve_loader("load_perfiles_institucionales", _csv_loader("Vigilancia", "perfiles_institucionales_cchen.csv"))
load_matching_institucional = _resolve_loader("load_matching_institucional", _csv_loader("Vigilancia", "convocatorias_matching_institucional.csv"))
load_asset_catalog = _resolve_loader("load_asset_catalog", _empty_loader)
load_data_sources_runtime = _resolve_loader("load_data_sources_runtime", _empty_loader)
load_data_source_runs = _resolve_loader("load_data_source_runs", _empty_loader)
load_entity_registry_personas = _resolve_loader("load_entity_registry_personas", _csv_loader("Gobernanza", "entity_registry_personas.csv"))
load_entity_registry_proyectos = _resolve_loader("load_entity_registry_proyectos", _csv_loader("Gobernanza", "entity_registry_proyectos.csv"))
load_entity_registry_convocatorias = _resolve_loader("load_entity_registry_convocatorias", _csv_loader("Gobernanza", "entity_registry_convocatorias.csv"))
load_entity_links = _resolve_loader("load_entity_links", _csv_loader("Gobernanza", "entity_links.csv"))
load_publications_with_concepts = _resolve_loader("load_publications_with_concepts", _csv_loader("Publications", "cchen_publications_with_concepts.csv"))
load_convenios_nacionales = _resolve_loader("load_convenios_nacionales", _empty_loader)
load_acuerdos_internacionales = _resolve_loader("load_acuerdos_internacionales", _empty_loader)
load_unpaywall_oa = _resolve_loader("load_unpaywall_oa", _empty_loader)
load_iaea_inis = _resolve_loader("load_iaea_inis", _csv_loader("Vigilancia", "iaea_inis_monitor.csv"))
load_citation_graph = _resolve_loader("load_citation_graph", _csv_loader("Publications", "cchen_citation_graph.csv"))
load_citing_papers = _resolve_loader("load_citing_papers", _csv_loader("Publications", "cchen_citing_papers.csv"))
load_altmetric = _resolve_loader("load_altmetric", _empty_loader)
load_europmc = _resolve_loader("load_europmc", _csv_loader("Publications", "cchen_europmc_works.csv"))
load_arxiv_monitor = _resolve_loader("load_arxiv_monitor", _csv_loader("Vigilancia", "arxiv_monitor.csv"))
load_news_monitor = _resolve_loader("load_news_monitor", _csv_loader("Vigilancia", "news_monitor.csv"))
load_bertopic_topics = _resolve_loader("load_bertopic_topics", _csv_loader("Publications", "cchen_bertopic_topics.csv"))
load_bertopic_topic_info = _resolve_loader("load_bertopic_topic_info", _csv_loader("Publications", "cchen_bertopic_topic_info.csv"))
load_convocatorias = _resolve_loader("load_convocatorias", _csv_loader("Vigilancia", "convocatorias_curadas.csv"))
load_convocatorias_matching_rules = _resolve_loader(
    "load_convocatorias_matching_rules",
    _csv_loader("Vigilancia", "convocatorias_matching_rules.csv"),
)
get_data_backend_info = _resolve_loader(
    "get_data_backend_info",
    lambda: {
        "engine": "pandas",
        "detail": "compat mode local CSV fallback",
        "source_mode": "local",
    },
)
get_table_load_status = _resolve_loader("get_table_load_status", lambda: {})
_PUBLIC_TABLE_CONFIG = getattr(_data_loader, "PUBLIC_TABLE_CONFIG", {})

# ─── Config ───────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="CCHEN Observatorio",
    page_icon="⚛️",
    layout="wide",
    initial_sidebar_state="expanded",
)

BLUE   = "#003B6F"
RED    = "#C8102E"
GREEN  = "#00A896"
AMBER  = "#F4A60D"
PURPLE = "#7B2D8B"
PALETTE = [BLUE, RED, GREEN, AMBER, PURPLE, "#E76F51", "#52B788", "#264653"]

PORTALES_CIENTIFICOS = [
    {
        "nombre": "IAEA Coordinated Research Projects",
        "organismo": "IAEA",
        "perfil_objetivo": "Académicos / PI",
        "descripcion": "Portal oficial para proyectos coordinados de investigación en áreas nucleares, médicas, ambientales y tecnológicas.",
        "url": "https://www.iaea.org/projects/coordinated-research-projects",
    },
    {
        "nombre": "IAEA Technical Cooperation",
        "organismo": "IAEA",
        "perfil_objetivo": "Institucional / cooperación internacional",
        "descripcion": "Puerta de entrada a cooperación técnica, fortalecimiento de capacidades y proyectos nacionales o regionales.",
        "url": "https://www.iaea.org/about/organizational-structure/department-of-technical-cooperation",
    },
    {
        "nombre": "EU Funding & Tenders Portal",
        "organismo": "Comisión Europea",
        "perfil_objetivo": "Académicos / PI / consorcios",
        "descripcion": "Portal oficial de convocatorias europeas, incluyendo Horizon Europe y líneas relevantes para infraestructura y colaboración científica.",
        "url": "https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/home",
    },
    {
        "nombre": "MSCA Postdoctoral Fellowships",
        "organismo": "Comisión Europea",
        "perfil_objetivo": "Postdoctorado",
        "descripcion": "Programa oficial de fellowship postdoctoral de Marie Sklodowska-Curie Actions.",
        "url": "https://marie-sklodowska-curie-actions.ec.europa.eu/actions/postdoctoral-fellowships",
    },
    {
        "nombre": "ERC Apply for a Grant",
        "organismo": "European Research Council",
        "perfil_objetivo": "Académicos / PI",
        "descripcion": "Ruta oficial para convocatorias ERC Starting, Consolidator, Advanced, Synergy y otras líneas frontier.",
        "url": "https://erc.europa.eu/apply-grant",
    },
]

# ── ISO 2→3 para mapa choropleth ──────────────────────────────────────────────
_ISO2_ISO3 = {
    'AF':'AFG','AL':'ALB','DZ':'DZA','AR':'ARG','AM':'ARM','AU':'AUS','AT':'AUT',
    'AZ':'AZE','BD':'BGD','BY':'BLR','BE':'BEL','BO':'BOL','BA':'BIH','BR':'BRA',
    'BG':'BGR','CA':'CAN','CL':'CHL','CN':'CHN','CO':'COL','CR':'CRI','HR':'HRV',
    'CU':'CUB','CY':'CYP','CZ':'CZE','DK':'DNK','DO':'DOM','EC':'ECU','EG':'EGY',
    'EE':'EST','ET':'ETH','FI':'FIN','FR':'FRA','GE':'GEO','DE':'DEU','GH':'GHA',
    'GR':'GRC','GT':'GTM','HN':'HND','HU':'HUN','IS':'ISL','IN':'IND','ID':'IDN',
    'IR':'IRN','IQ':'IRQ','IE':'IRL','IL':'ISR','IT':'ITA','JP':'JPN','JO':'JOR',
    'KZ':'KAZ','KE':'KEN','KR':'KOR','KW':'KWT','KG':'KGZ','LV':'LVA','LB':'LBN',
    'LT':'LTU','LU':'LUX','MY':'MYS','MX':'MEX','MD':'MDA','MN':'MNG','ME':'MNE',
    'MA':'MAR','MZ':'MOZ','MM':'MMR','NA':'NAM','NP':'NPL','NL':'NLD','NZ':'NZL',
    'NI':'NIC','NE':'NER','NG':'NGA','MK':'MKD','NO':'NOR','OM':'OMN','PK':'PAK',
    'PA':'PAN','PY':'PRY','PE':'PER','PH':'PHL','PL':'POL','PT':'PRT','QA':'QAT',
    'RO':'ROU','RU':'RUS','SA':'SAU','SN':'SEN','RS':'SRB','ZA':'ZAF','ES':'ESP',
    'LK':'LKA','SD':'SDN','SE':'SWE','CH':'CHE','SY':'SYR','TW':'TWN','TJ':'TJK',
    'TZ':'TZA','TH':'THA','TN':'TUN','TR':'TUR','TM':'TKM','UG':'UGA','UA':'UKR',
    'AE':'ARE','GB':'GBR','US':'USA','UY':'URY','UZ':'UZB','VE':'VEN','VN':'VNM',
    'YE':'YEM','ZM':'ZMB','ZW':'ZWE','SK':'SVK','SI':'SVN','SG':'SGP','HK':'HKG',
    'KP':'PRK','MK':'MKD','LY':'LBY','SL':'SLE','CG':'COG','CD':'COD','TT':'TTO',
}

# ── H-index ───────────────────────────────────────────────────────────────────
def calc_hindex(citation_series) -> int:
    cites = sorted(citation_series.dropna().astype(int).tolist(), reverse=True)
    return sum(1 for i, c in enumerate(cites, 1) if c >= i)

st.markdown(f"""
<style>
/* ── Tipografía base ─────────────────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"], .stApp {{
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
    color: #0F172A !important;
    background-color: #F8FAFC !important;
}}
.stApp, [data-testid="stAppViewContainer"],
[data-testid="stMain"], [data-testid="stMainBlockContainer"] {{
    background: #F8FAFC !important;
}}

/* ── Sidebar ─────────────────────────────────────────────────────────────── */
[data-testid="stSidebar"] {{
    background: linear-gradient(180deg, #001832 0%, {BLUE} 55%, #005BAA 100%) !important;
    border-right: none !important;
}}
[data-testid="stSidebar"] * {{ color: rgba(255,255,255,0.88) !important; }}
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3, [data-testid="stSidebar"] strong {{
    color: #FFFFFF !important;
}}
[data-testid="stSidebar"] [data-testid="stRadio"] label {{
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 0.82rem;
    font-weight: 400;
    letter-spacing: 0.1px;
    transition: background 0.15s;
}}
[data-testid="stSidebar"] [data-testid="stRadio"] label:hover {{
    background: rgba(255,255,255,0.1) !important;
}}
[data-testid="stSidebar"] hr {{ border-color: rgba(255,255,255,0.12) !important; }}
[data-testid="stSidebar"] .stCaption,
[data-testid="stSidebar"] small {{ color: rgba(255,255,255,0.48) !important; }}

/* ── Tipografía principal ────────────────────────────────────────────────── */
h1 {{ font-size: 1.45rem !important; font-weight: 700 !important;
      color: #0F172A !important; letter-spacing: -0.3px !important;
      line-height: 1.3 !important; }}
h2 {{ font-size: 1.05rem !important; font-weight: 600 !important; color: #1E293B !important; }}
h3 {{ font-size: 0.93rem !important; font-weight: 600 !important; color: #334155 !important; }}
p, li {{ color: #334155; line-height: 1.6; }}

/* ── Cards métricas ──────────────────────────────────────────────────────── */
.kpi-card {{
    flex: 1; background: white; border-radius: 12px; padding: 20px 18px;
    border: 1px solid #E2E8F0;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04), 0 4px 12px rgba(0,0,0,0.02);
}}

/* ── Expanders (área principal) ──────────────────────────────────────────── */
[data-testid="stExpander"] {{
    border: 1px solid #E2E8F0 !important;
    border-radius: 10px !important;
    background: white !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.03) !important;
}}
[data-testid="stExpander"] summary {{
    font-size: 0.83rem !important;
    font-weight: 500 !important;
    color: #334155 !important;
    padding: 10px 14px !important;
}}

/* ── Expanders dentro del sidebar ────────────────────────────────────────── */
[data-testid="stSidebar"] [data-testid="stExpander"] {{
    background: rgba(255,255,255,0.07) !important;
    border: 1px solid rgba(255,255,255,0.18) !important;
    box-shadow: none !important;
}}
[data-testid="stSidebar"] [data-testid="stExpander"] summary {{
    color: rgba(255,255,255,0.88) !important;
}}
[data-testid="stSidebar"] [data-testid="stExpander"] summary svg {{
    fill: rgba(255,255,255,0.70) !important;
    stroke: rgba(255,255,255,0.70) !important;
}}
[data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stExpanderDetails"] {{
    background: rgba(0,0,0,0.12) !important;
    border-top: 1px solid rgba(255,255,255,0.10) !important;
}}

/* ── Dataframes ──────────────────────────────────────────────────────────── */
[data-testid="stDataFrame"] {{
    border-radius: 10px; overflow: hidden; border: 1px solid #E2E8F0;
}}

/* ── Botones de descarga ─────────────────────────────────────────────────── */
.stDownloadButton > button {{
    border-radius: 6px !important;
    font-size: 0.79rem !important;
    font-weight: 500 !important;
    border: 1px solid #CBD5E1 !important;
    color: #334155 !important;
    background: white !important;
    padding: 6px 14px !important;
    transition: all 0.15s ease !important;
    box-shadow: 0 1px 2px rgba(0,0,0,0.04) !important;
}}
.stDownloadButton > button:hover {{
    background: {BLUE} !important;
    color: white !important;
    border-color: {BLUE} !important;
}}

/* ── Botones normales ────────────────────────────────────────────────────── */
.stButton > button {{
    border-radius: 6px !important;
    font-size: 0.79rem !important;
    font-weight: 500 !important;
    border: 1px solid #E2E8F0 !important;
    color: #334155 !important;
    background: white !important;
    padding: 7px 14px !important;
    transition: all 0.15s ease !important;
    box-shadow: 0 1px 2px rgba(0,0,0,0.04) !important;
    letter-spacing: 0.1px;
}}
.stButton > button:hover {{
    border-color: {BLUE} !important;
    color: {BLUE} !important;
    background: #F0F6FF !important;
}}

/* ── Botones dentro del sidebar (fondo oscuro → texto blanco, borde blanco) ── */
[data-testid="stSidebar"] .stButton > button {{
    background: rgba(255,255,255,0.07) !important;
    color: rgba(255,255,255,0.88) !important;
    border: 1px solid rgba(255,255,255,0.22) !important;
    box-shadow: none !important;
}}
[data-testid="stSidebar"] .stButton > button:hover {{
    background: rgba(255,255,255,0.17) !important;
    color: #FFFFFF !important;
    border-color: rgba(255,255,255,0.45) !important;
}}
[data-testid="stSidebar"] .stDownloadButton > button {{
    background: rgba(255,255,255,0.07) !important;
    color: rgba(255,255,255,0.88) !important;
    border: 1px solid rgba(255,255,255,0.22) !important;
    box-shadow: none !important;
}}
[data-testid="stSidebar"] .stDownloadButton > button:hover {{
    background: rgba(255,255,255,0.17) !important;
    color: #FFFFFF !important;
    border-color: rgba(255,255,255,0.45) !important;
}}

/* ── Selectbox, multiselect, text_input, slider — texto visible ─────────── */
[data-testid="stSelectbox"] label,
[data-testid="stMultiSelect"] label,
[data-testid="stTextInput"] label,
[data-testid="stSlider"] label,
[data-testid="stNumberInput"] label,
[data-testid="stRadio"] label,
[data-testid="stCheckbox"] label {{
    color: #334155 !important;
    font-size: 0.82rem !important;
    font-weight: 500 !important;
}}
[data-testid="stSelectbox"] div[data-baseweb="select"] > div,
[data-testid="stMultiSelect"] div[data-baseweb="select"] > div {{
    background: white !important;
    border-color: #CBD5E1 !important;
    color: #0F172A !important;
}}
[data-testid="stTextInput"] input {{
    background: white !important;
    color: #0F172A !important;
    border-color: #CBD5E1 !important;
}}
[data-testid="stTextInput"] input::placeholder {{
    color: #94A3B8 !important;
}}
/* slider valor y rango */
[data-testid="stSlider"] [data-testid="stTickBar"],
[data-testid="stSlider"] span {{
    color: #475569 !important;
}}

/* ── st.info / st.warning / st.success / st.error — texto siempre oscuro ── */
[data-testid="stAlert"] {{
    color: #1E293B !important;
}}
[data-testid="stAlert"] p,
[data-testid="stAlert"] span {{
    color: #1E293B !important;
}}

/* ── st.caption en área principal ────────────────────────────────────────── */
.stCaption, [data-testid="stCaptionContainer"] {{
    color: #64748B !important;
}}

/* ── Sidebar caption: subir opacidad para mayor legibilidad ─────────────── */
[data-testid="stSidebar"] .stCaption,
[data-testid="stSidebar"] small,
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {{
    color: rgba(255,255,255,0.65) !important;
}}

/* ── Expander — título y contenido ──────────────────────────────────────── */
[data-testid="stExpander"] summary span {{
    color: #334155 !important;
}}
[data-testid="stExpander"] [data-testid="stExpanderDetails"] {{
    color: #334155 !important;
}}

/* ── Métricas ─────────────────────────────────────────────────────────────── */
[data-testid="stMetric"] label {{
    color: #64748B !important;
    font-size: 0.78rem !important;
}}
[data-testid="stMetric"] [data-testid="stMetricValue"] {{
    color: #0F172A !important;
    font-weight: 700 !important;
}}
[data-testid="stMetric"] [data-testid="stMetricDelta"] {{
    font-size: 0.75rem !important;
}}

/* ── Tabs ─────────────────────────────────────────────────────────────────── */
[data-testid="stTabs"] [data-baseweb="tab"] {{
    color: #64748B !important;
    font-size: 0.83rem !important;
}}
[data-testid="stTabs"] [aria-selected="true"] {{
    color: {BLUE} !important;
    font-weight: 600 !important;
    border-bottom: 2px solid {BLUE} !important;
}}

/* ── Chat ────────────────────────────────────────────────────────────────── */
[data-testid="stChatMessage"] {{
    background: white !important;
    border: 1px solid #E2E8F0 !important;
    border-radius: 10px !important;
}}
[data-testid="stChatInputContainer"],
[data-testid="stChatInput"] {{
    background: white !important;
    color: #0F172A !important;
    border-color: #CBD5E1 !important;
}}

/* ── Alerts ──────────────────────────────────────────────────────────────── */
.alert-rojo     {{ background:#FEF2F2; border-left:3px solid {RED};   padding:10px 14px; border-radius:8px; }}
.alert-amarillo {{ background:#FFFBEB; border-left:3px solid {AMBER}; padding:10px 14px; border-radius:8px; }}
.alert-verde    {{ background:#F0FDF4; border-left:3px solid {GREEN}; padding:10px 14px; border-radius:8px; }}
.alert-azul     {{ background:#EEF4FF; border-left:3px solid {BLUE};  padding:10px 14px; border-radius:8px; }}

/* ── Scrollbar ───────────────────────────────────────────────────────────── */
::-webkit-scrollbar {{ width: 5px; height: 5px; }}
::-webkit-scrollbar-track {{ background: transparent; }}
::-webkit-scrollbar-thumb {{ background: #CBD5E1; border-radius: 10px; }}
::-webkit-scrollbar-thumb:hover {{ background: #94A3B8; }}

/* ── Dividers ────────────────────────────────────────────────────────────── */
hr {{ border-color: #E2E8F0 !important; margin: 0.4rem 0 !important; }}
</style>
""", unsafe_allow_html=True)


# ─── Carga cacheada ───────────────────────────────────────────────────────────

def _bootstrap_dashboard_env():
    try:
        supabase_cfg = st.secrets.get("supabase", {})
    except Exception:
        supabase_cfg = {}

    mappings = {
        "SUPABASE_URL": ("url", "SUPABASE_URL"),
        "SUPABASE_ANON_KEY": ("anon_key", "SUPABASE_ANON_KEY"),
        "SUPABASE_SERVICE_ROLE_KEY": ("service_role_key", "SUPABASE_SERVICE_ROLE_KEY"),
        "OBSERVATORIO_DATA_SOURCE": ("data_source", "OBSERVATORIO_DATA_SOURCE"),
        "CCHEN_DATA_ROOT": ("data_root", "CCHEN_DATA_ROOT"),
    }
    for env_name, keys in mappings.items():
        if os.environ.get(env_name):
            continue
        for key in keys:
            value = supabase_cfg.get(key)
            if value:
                os.environ[env_name] = str(value)
                break


_bootstrap_dashboard_env()


_LOGO_PATH = Path(__file__).parent / "assets" / "logo_cchen360.png"


def _render_beta_access_gate() -> None:
    if _observatorio_app_mode() != "internal":
        return

    auth_cfg = _internal_auth_config()
    if not auth_cfg.get("enabled"):
        return

    access = _access_context()
    if access.get("is_logged_in"):
        return

    if _LOGO_PATH.exists():
        col_l, col_logo, col_r = st.columns([1, 1, 1])
        with col_logo:
            st.image(str(_LOGO_PATH), width=220)

    st.markdown(
        f"""
        <div style="padding:0.5rem 0 1.25rem 0">
            <div style="font-size:0.72rem;font-weight:700;letter-spacing:0.16em;text-transform:uppercase;color:{BLUE};margin-bottom:0.5rem">
                {access.get("beta_badge", "Beta interna")}
            </div>
            <div style="font-size:2.1rem;font-weight:800;color:#0F172A;line-height:1.1;margin-bottom:0.65rem">
                {access.get("beta_title", "Observatorio Tecnológico CCHEN")}
            </div>
            <div style="font-size:1rem;color:#475569;max-width:52rem;line-height:1.6">
                {access.get("beta_message", "")}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    hero_col, login_col = st.columns([1.35, 0.9], gap="large")

    with hero_col:
        st.markdown(
            """
            ### Acceso privado del observatorio
            Esta versión está pensada para revisión interna, validación funcional y migración progresiva
            desde los datasets locales hacia la arquitectura del observatorio.
            """
        )
        st.info(
            "El ingreso permite revisar módulos en beta, fuentes aún en consolidación y tablas internas "
            "que no deben quedar expuestas en una URL pública abierta."
        )
        st.caption(
            "Los usuarios se definen en `Dashboard/.streamlit/secrets.toml` o en los secrets del "
            "dashboard desplegado. Las credenciales no quedan hardcodeadas en el repositorio."
        )

    with login_col:
        st.markdown("### Ingreso beta")
        st.caption("Usa tu usuario interno para continuar.")
        with st.form("observatorio_internal_login", clear_on_submit=False):
            username = st.text_input("Usuario", placeholder="tu.usuario")
            password = st.text_input("Clave", type="password")
            submit = st.form_submit_button("Ingresar al observatorio", width="stretch")
        if submit:
            ok, message = _internal_auth_login(username, password)
            if ok:
                st.success("Acceso concedido. Redirigiendo…")
                st.rerun()
            else:
                st.error(message)

    st.stop()


_render_beta_access_gate()


_APP_ACCESS = _access_context()
_APP_MODE = _APP_ACCESS.get("app_mode", "internal")
_CAPITAL_HUMANO_COLUMNS = getattr(_data_loader, "CAPITAL_HUMANO_COLUMNS", [
    "id", "anio_hoja", "nombre", "inicio", "termino", "duracion_dias", "tutor",
    "centro_norm", "tipo_norm", "universidad", "carrera", "monto_contrato_num",
    "ad_honorem", "objeto_contrato", "observaciones_texto", "informe_url_principal",
    "flag_fechas_inconsistentes", "flag_tipo_fuera_catalogo", "created_at",
])


def _empty_capital_humano_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=_CAPITAL_HUMANO_COLUMNS)


def _maybe_sensitive(loader, enabled: bool, empty_factory=pd.DataFrame):
    return loader() if enabled else empty_factory()


_DATASET_LOADERS = {
    "pub": lambda can_view_sensitive: load_publications(),
    "pub_enr": lambda can_view_sensitive: load_publications_enriched(),
    "auth": lambda can_view_sensitive: load_authorships(),
    "anid": lambda can_view_sensitive: load_anid(),
    "ch": lambda can_view_sensitive: _maybe_sensitive(
        load_capital_humano,
        can_view_sensitive,
        _empty_capital_humano_frame,
    ),
    "ch_ej": lambda can_view_sensitive: load_ch_resumen_ejecutivo(),
    "ch_adv": lambda can_view_sensitive: load_ch_analisis_avanzado(),
    "ch_cumpl": lambda can_view_sensitive: load_ch_cumplimiento_centros(),
    "ch_trans": lambda can_view_sensitive: load_ch_transiciones(),
    "ch_tipo_a": lambda can_view_sensitive: load_ch_participacion_tipo_anio(),
    "dian": lambda can_view_sensitive: load_dian_publications(),
    "crossref": lambda can_view_sensitive: load_crossref_enriched(),
    "concepts": lambda can_view_sensitive: load_concepts(),
    "datacite": lambda can_view_sensitive: load_datacite_outputs(),
    "openaire": lambda can_view_sensitive: load_openaire_outputs(),
    "grants_oa": lambda can_view_sensitive: load_grants_openalex(),
    "orcid": lambda can_view_sensitive: load_orcid_researchers(),
    "padron_acad": lambda can_view_sensitive: load_padron_academicos_provisional(),
    "ror_registry": lambda can_view_sensitive: load_ror_registry(),
    "ror_pending_review": lambda can_view_sensitive: load_ror_pending_review(),
    "funding_plus": lambda can_view_sensitive: _maybe_sensitive(
        load_funding_complementario,
        can_view_sensitive,
    ),
    "iaea_tc": lambda can_view_sensitive: load_iaea_tc(),
    "perfiles_inst": lambda can_view_sensitive: load_perfiles_institucionales(),
    "matching_inst": lambda can_view_sensitive: load_matching_institucional(),
    "asset_catalog": lambda can_view_sensitive: load_asset_catalog(),
    "entity_personas": lambda can_view_sensitive: _maybe_sensitive(
        load_entity_registry_personas,
        can_view_sensitive,
    ),
    "entity_projects": lambda can_view_sensitive: load_entity_registry_proyectos(),
    "entity_convocatorias": lambda can_view_sensitive: load_entity_registry_convocatorias(),
    "entity_links": lambda can_view_sensitive: _maybe_sensitive(
        load_entity_links,
        can_view_sensitive,
    ),
    "pub_full": lambda can_view_sensitive: load_publications_with_concepts(),
    "convenios": lambda can_view_sensitive: load_convenios_nacionales(),
    "acuerdos": lambda can_view_sensitive: load_acuerdos_internacionales(),
    "unpaywall": lambda can_view_sensitive: load_unpaywall_oa(),
    "citation_graph": lambda can_view_sensitive: load_citation_graph(),
    "citing_papers": lambda can_view_sensitive: load_citing_papers(),
    "altmetric": lambda can_view_sensitive: load_altmetric(),
    "europmc": lambda can_view_sensitive: load_europmc(),
    "arxiv_monitor": lambda can_view_sensitive: load_arxiv_monitor(),
    "news_monitor": lambda can_view_sensitive: load_news_monitor(),
    "iaea_inis": lambda can_view_sensitive: load_iaea_inis(),
    "bertopic_topics": lambda can_view_sensitive: load_bertopic_topics(),
    "bertopic_topic_info": lambda can_view_sensitive: load_bertopic_topic_info(),
    "patents": lambda can_view_sensitive: load_patents(),
}

_SECTION_DATASETS = {
    "Plataforma Institucional": (
        "pub", "anid", "datacite", "openaire", "patents", "asset_catalog",
    ),
    "Panel de Indicadores": (
        "pub", "pub_enr", "anid", "ch", "ch_ej", "ch_adv",
        "ror_pending_review", "patents", "orcid", "padron_acad", "asset_catalog",
    ),
    "Producción Científica": (
        "pub", "pub_enr", "auth", "dian", "concepts", "orcid", "unpaywall", "europmc",
    ),
    "Redes y Colaboración": (
        "auth", "pub", "ror_pending_review", "ror_registry",
    ),
    "Vigilancia Tecnológica": (
        "arxiv_monitor", "news_monitor", "iaea_inis",
        "pub", "pub_enr", "bertopic_topics", "bertopic_topic_info",
    ),
    "Financiamiento I+D": (
        "anid", "crossref", "funding_plus", "iaea_tc", "acuerdos", "convenios",
    ),
    "Convocatorias y Matching": (
        "matching_inst", "perfiles_inst", "asset_catalog",
    ),
    "Transferencia y Portafolio": (
        "datacite", "openaire", "orcid", "patents", "pub_enr",
        "anid", "funding_plus", "acuerdos", "convenios",
    ),
    "Modelo y Gobernanza": (
        "pub", "auth", "ch", "orcid", "patents", "convenios", "acuerdos",
        "matching_inst", "entity_personas", "entity_projects",
        "entity_convocatorias", "entity_links",
    ),
    "Formación de Capacidades": (
        "ch", "ch_ej", "ch_adv", "ch_cumpl", "ch_trans", "padron_acad",
    ),
    "Asistente I+D": (
        "pub", "pub_enr", "auth", "anid", "ch", "ch_ej", "ch_adv", "orcid",
        "ror_registry", "ror_pending_review", "funding_plus", "iaea_tc",
        "matching_inst", "entity_personas", "entity_projects",
        "entity_convocatorias", "entity_links", "acuerdos", "convenios",
        "patents", "datacite", "openaire", "asset_catalog",
    ),
    "Grafo de Citas": (
        "pub", "pub_enr", "citation_graph", "citing_papers",
    ),
}

_DATASET_METADATA = {
    "pub": {
        "label": "Publicaciones OpenAlex",
        "source": "Data/Publications/cchen_openalex_works.csv",
        "table_name": "publications",
        "sensitive": False,
    },
    "pub_enr": {
        "label": "Publicaciones enriquecidas + SJR",
        "source": "Data/Publications/cchen_publications_with_quartile_sjr.csv",
        "table_name": "publications_enriched",
        "sensitive": False,
    },
    "auth": {
        "label": "Autorías OpenAlex",
        "source": "Data/Publications/cchen_authorships_enriched.csv",
        "table_name": "authorships",
        "sensitive": False,
    },
    "anid": {
        "label": "ANID",
        "source": "Data/ANID/RepositorioAnid_con_monto.csv",
        "table_name": "anid_projects",
        "sensitive": False,
    },
    "ch": {
        "label": "Capital Humano",
        "source": "Data/Capital humano CCHEN/salida_dataset_maestro/dataset_maestro_limpio.csv",
        "table_name": "capital_humano",
        "sensitive": True,
    },
    "patents": {
        "label": "Patentes",
        "source": "Data/Patents/cchen_patents_uspto.csv",
        "table_name": "patents",
        "sensitive": False,
    },
    "crossref": {
        "label": "CrossRef",
        "source": "Data/Publications/cchen_crossref_enriched.csv",
        "table_name": "crossref_data",
        "sensitive": False,
    },
    "concepts": {
        "label": "Conceptos OpenAlex",
        "source": "Data/Publications/cchen_openalex_concepts.csv",
        "table_name": "concepts",
        "sensitive": False,
    },
    "datacite": {
        "label": "DataCite outputs",
        "source": "Data/ResearchOutputs/cchen_datacite_outputs.csv",
        "table_name": "datacite_outputs",
        "sensitive": False,
    },
    "openaire": {
        "label": "OpenAIRE outputs",
        "source": "Data/ResearchOutputs/cchen_openaire_outputs.csv",
        "table_name": "openaire_outputs",
        "sensitive": False,
    },
    "orcid": {
        "label": "Investigadores ORCID",
        "source": "Data/Researchers/cchen_researchers_orcid.csv",
        "table_name": "researchers_orcid",
        "sensitive": False,
    },
    "ror_registry": {
        "label": "Registro institucional ROR",
        "source": "Data/Institutional/cchen_institution_registry.csv",
        "table_name": "institution_registry",
        "sensitive": False,
    },
    "ror_pending_review": {
        "label": "Cola revisión ROR",
        "source": "Data/Institutional/ror_pending_review.csv",
        "table_name": "institution_registry_pending_review",
        "sensitive": False,
    },
    "funding_plus": {
        "label": "Financiamiento complementario",
        "source": "Data/Funding/cchen_funding_complementario.csv",
        "table_name": "funding_complementario",
        "sensitive": True,
    },
    "iaea_tc": {
        "label": "IAEA Technical Cooperation",
        "source": "Data/Funding/cchen_iaea_tc.csv",
        "table_name": "iaea_tc_projects",
        "sensitive": False,
    },
    "perfiles_inst": {
        "label": "Perfiles institucionales",
        "source": "Data/Vigilancia/perfiles_institucionales_cchen.csv",
        "table_name": "perfiles_institucionales",
        "sensitive": False,
    },
    "matching_inst": {
        "label": "Matching institucional",
        "source": "Data/Vigilancia/convocatorias_matching_institucional.csv",
        "table_name": "convocatorias_matching_institucional",
        "sensitive": False,
    },
    "asset_catalog": {
        "label": "Catálogo activos 3 en 1",
        "source": "Data/Gobernanza/catalogo_activos_3_en_1.csv",
        "table_name": "catalogo_activos_3_en_1",
        "sensitive": False,
    },
    "entity_personas": {
        "label": "Entidades persona",
        "source": "Data/Gobernanza/entity_registry_personas.csv",
        "table_name": "entity_registry_personas",
        "sensitive": True,
    },
    "entity_projects": {
        "label": "Entidades proyecto",
        "source": "Data/Gobernanza/entity_registry_proyectos.csv",
        "table_name": "entity_registry_proyectos",
        "sensitive": False,
    },
    "entity_convocatorias": {
        "label": "Entidades convocatoria",
        "source": "Data/Gobernanza/entity_registry_convocatorias.csv",
        "table_name": "entity_registry_convocatorias",
        "sensitive": False,
    },
    "entity_links": {
        "label": "Enlaces entre entidades",
        "source": "Data/Gobernanza/entity_links.csv",
        "table_name": "entity_links",
        "sensitive": True,
    },
    "convenios": {
        "label": "Convenios nacionales",
        "source": "Data/Institutional/clean_Convenios_suscritos_por_la_Com.csv",
        "table_name": "convenios_nacionales",
        "sensitive": False,
    },
    "acuerdos": {
        "label": "Acuerdos internacionales",
        "source": "Data/Institutional/clean_Acuerdos_e_instrumentos_intern.csv",
        "table_name": "acuerdos_internacionales",
        "sensitive": False,
    },
    "unpaywall": {
        "label": "Unpaywall OA enrichment",
        "source": "Data/Publications/cchen_unpaywall_oa.csv",
        "table_name": "unpaywall_oa",
        "sensitive": False,
    },
    "citation_graph": {
        "label": "Citation graph",
        "source": "Data/Publications/cchen_citation_graph.csv",
        "table_name": "citation_graph",
        "sensitive": False,
    },
    "citing_papers": {
        "label": "Papers citantes",
        "source": "Data/Publications/cchen_citing_papers.csv",
        "table_name": "citing_papers",
        "sensitive": False,
    },
    "europmc": {
        "label": "EuroPMC",
        "source": "Data/Publications/cchen_europmc_works.csv",
        "table_name": "europmc_works",
        "sensitive": False,
    },
    "arxiv_monitor": {
        "label": "Monitor arXiv",
        "source": "Data/Vigilancia/arxiv_monitor.csv",
        "table_name": "arxiv_monitor",
        "sensitive": False,
    },
    "news_monitor": {
        "label": "Monitor noticias",
        "source": "Data/Vigilancia/news_monitor.csv",
        "table_name": "news_monitor",
        "sensitive": False,
    },
    "iaea_inis": {
        "label": "Monitor IAEA INIS",
        "source": "Data/Vigilancia/iaea_inis_monitor.csv",
        "table_name": "iaea_inis_monitor",
        "sensitive": False,
    },
    "bertopic_topics": {
        "label": "BERTopic topics",
        "source": "Data/Publications/cchen_bertopic_topics.csv",
        "table_name": "bertopic_topics",
        "sensitive": False,
    },
    "bertopic_topic_info": {
        "label": "BERTopic topic info",
        "source": "Data/Publications/cchen_bertopic_topic_info.csv",
        "table_name": "bertopic_topic_info",
        "sensitive": False,
    },
    "dian": {
        "label": "Publicaciones DIAN",
        "source": "Data/Publicaciones DIAN CCHEN/Publicaciones DIAN.xlsx",
        "table_name": "dian_publications",
        "sensitive": False,
    },
}

_ACTIVE_SECTION_CTX = None


def _dataset_keys_for_section(section_name: str, *, app_mode: str, can_view_sensitive: bool) -> tuple[str, ...]:
    dataset_keys = list(_SECTION_DATASETS.get(section_name, ()))
    if app_mode == "public" or not can_view_sensitive:
        dataset_keys = [
            key for key in dataset_keys
            if not _DATASET_METADATA.get(key, {}).get("sensitive", False)
        ]
    return tuple(dataset_keys)


@st.cache_data(show_spinner=False, ttl=900, max_entries=256)
def _load_dataset_cached(dataset_key: str, can_view_sensitive: bool):
    loader = _DATASET_LOADERS.get(dataset_key)
    if loader is None:
        raise KeyError(f"Dataset no registrado para lazy loading: {dataset_key}")
    return loader(can_view_sensitive)


@st.cache_data(show_spinner=False, ttl=900, max_entries=64)
def _load_section_datasets_cached(section_name: str, can_view_sensitive: bool, app_mode: str) -> dict:
    dataset_keys = _dataset_keys_for_section(
        section_name,
        app_mode=app_mode,
        can_view_sensitive=can_view_sensitive,
    )
    return {
        key: _load_dataset_cached(key, can_view_sensitive)
        for key in dataset_keys
    }


def _current_section_name() -> str:
    return str(globals().get("seccion") or "Plataforma Institucional")


def _build_section_ctx(section_name: str, can_view_sensitive: bool) -> dict:
    app_mode = _access_context().get("app_mode", "internal")
    ctx = dict(_load_section_datasets_cached(section_name, can_view_sensitive, app_mode))
    ctx["render_operational_strip"] = render_operational_strip
    ctx["open_dataset_inspector"] = open_dataset_inspector
    ctx["app_mode"] = app_mode
    ctx["is_public_app"] = app_mode == "public"
    ctx["section_visibility"] = _section_visibility(section_name)
    return ctx


def _active_section_ctx() -> dict:
    current_name = _current_section_name()
    current_ctx = globals().get("_ACTIVE_SECTION_CTX")
    if isinstance(current_ctx, dict) and current_ctx.get("_section_name") == current_name:
        return current_ctx
    ctx = _build_section_ctx(current_name, _access_context()["can_view_sensitive"])
    ctx["_section_name"] = current_name
    return ctx

_timestamps = get_source_timestamps()
_backend = get_data_backend_info()


# ─── Section imports ──────────────────────────────────────────────────────────

from sections.shared import (
    BLUE, RED, GREEN, AMBER, PURPLE, PALETTE,
    PORTALES_CIENTIFICOS, _ISO2_ISO3,
    _dialog, _fragment,
    calc_hindex, kpi, kpi_row, sec, make_csv,
    semaforo_badge,
    _bool_from_any, _text_or_empty,
    _clean_html_text, _clean_news_title, _clean_news_snippet,
    _pretty_topic_term, _build_topic_label, _topic_terms_preview,
    _normalize_convocatorias_df, _load_convocatorias_data,
    _load_portafolio_seed, _load_entity_model_tables,
    _extract_agreement_country_counts, _build_matching_profiles_summary,
    _build_entity_observed_counts,
    _get_secret_block, _streamlit_auth_supported, _auth_enabled, _access_context,
    generate_pdf_report,
)

from sections import (
    plataforma_institucional,
    panel_indicadores,
    produccion_cientifica,
    redes_colaboracion,
    vigilancia_tecnologica,
    financiamiento_id,
    convocatorias_matching,
    transferencia_portafolio,
    modelo_gobernanza,
    formacion_capacidades,
    asistente_id,
    grafo_citas,
)

if hasattr(st, "dialog"):
    _dialog = st.dialog
else:
    def _dialog(title, **_kwargs):
        def decorator(func):
            def wrapped(*args, **kwargs):
                with st.expander(title, expanded=True):
                    return func(*args, **kwargs)
            return wrapped
        return decorator


if hasattr(st, "fragment"):
    _fragment = st.fragment
else:
    def _fragment(func=None, **_kwargs):
        if func is None:
            def decorator(inner):
                return inner
            return decorator
        return func


def _dataset_catalog(ctx: dict | None = None) -> dict:
    active_ctx = ctx or _active_section_ctx()
    catalog = {}
    for dataset_key, meta in _DATASET_METADATA.items():
        if dataset_key not in active_ctx:
            continue
        catalog[meta["label"]] = {
            "key": dataset_key,
            "df": active_ctx[dataset_key],
            "source": meta["source"],
            "table_name": meta["table_name"],
            "sensitive": meta["sensitive"],
        }
    return catalog


def _describe_dataset_read_source(meta: dict) -> tuple[str, str]:
    table_name = str(meta.get("table_name") or "").strip()
    status = get_table_load_status().get(table_name, {}) if table_name else {}
    source = status.get("source", "")
    detail = status.get("detail", "")
    source_path = str(meta.get("source") or "").strip()
    has_local_backup = False
    if source_path.startswith("Data/"):
        parts = Path(source_path).parts
        rel_parts = parts[1:] if parts and parts[0] == "Data" else parts
        has_local_backup = bool(rel_parts) and BASE.joinpath(*rel_parts).exists()

    if source == "supabase_public":
        return "Supabase pública", table_name
    if source == "supabase_private":
        return "Supabase privada", table_name
    if source == "local_fallback":
        return "Fallback local", detail or meta.get("source", "CSV local")
    if source == "local_only":
        if table_name and table_name in _PUBLIC_TABLE_CONFIG:
            return "Local", detail or meta.get("source", "CSV local")
        return "Solo local / autenticado", detail or meta.get("source", "CSV local")
    if source == "unavailable":
        return "No disponible", detail or "sin respaldo local disponible"
    if has_local_backup:
        return "Local", detail or meta.get("source", "CSV local")
    if table_name and table_name in _PUBLIC_TABLE_CONFIG:
        return "Remoto habilitado", table_name
    return "Solo local / autenticado", meta.get("source", "CSV local")


def _catalog_local_path(meta: dict) -> Path | None:
    source = str(meta.get("source") or "").strip()
    if not source.startswith("Data/"):
        return None
    parts = Path(source).parts
    rel_parts = parts[1:] if parts and parts[0] == "Data" else parts
    if not rel_parts:
        return None
    return BASE.joinpath(*rel_parts)


def _dataset_snapshot_info(meta: dict) -> tuple[str, int | None]:
    path = _catalog_local_path(meta)
    if path is None or not path.exists():
        return "—", None
    try:
        modified = dt.datetime.fromtimestamp(path.stat().st_mtime)
    except OSError:
        return "—", None
    age_days = max((dt.datetime.now() - modified).days, 0)
    return modified.strftime("%d/%m/%Y"), age_days


def _format_dataset_names(names: list[str], limit: int = 4) -> str:
    if not names:
        return "—"
    visible = names[:limit]
    hidden = len(names) - len(visible)
    if hidden > 0:
        return f"{', '.join(visible)} y {hidden} más"
    return ", ".join(visible)


def _build_runtime_dataset_status() -> pd.DataFrame:
    access = _access_context()
    status_map = get_table_load_status()
    rows = []
    section_name = _current_section_name()
    catalog = _dataset_catalog()

    for dataset_name, meta in catalog.items():
        table_name = str(meta.get("table_name") or "").strip()
        status = status_map.get(table_name, {}) if table_name else {}
        read_source, read_detail = _describe_dataset_read_source(meta)
        snapshot_label, snapshot_age_days = _dataset_snapshot_info(meta)
        is_sensitive = bool(meta.get("sensitive"))
        if is_sensitive and not access["can_view_sensitive"]:
            row_count = "Restringido"
        else:
            df = meta.get("df", pd.DataFrame())
            row_count = f"{len(df):,}" if hasattr(df, "__len__") else "—"

        rows.append(
            {
                "dataset": dataset_name,
                "table_name": table_name or "—",
                "sensitive": "Sí" if is_sensitive else "No",
                "source_code": status.get("source") or ("local_only" if snapshot_age_days is not None else "unknown"),
                "read_source": read_source,
                "read_detail": read_detail,
                "rows": row_count,
                "snapshot": snapshot_label,
                "snapshot_age_days": snapshot_age_days,
                "section_name": section_name,
            }
        )

    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values(["read_source", "dataset"]).reset_index(drop=True)


def _summarize_runtime_dataset_status(status_df: pd.DataFrame) -> dict:
    if status_df.empty:
        return {
            "dataset_count": 0,
            "remote_count": 0,
            "fallback_count": 0,
            "local_only_count": 0,
            "unavailable_count": 0,
            "fallback_names": [],
            "unavailable_names": [],
            "freshest_snapshot": "—",
            "freshest_snapshot_age_days": None,
        }

    source_counts = status_df["source_code"].value_counts()
    snapshot_df = status_df[status_df["snapshot_age_days"].notna()].sort_values(
        ["snapshot_age_days", "dataset"]
    )
    freshest_snapshot = "—"
    freshest_snapshot_age_days = None
    if not snapshot_df.empty:
        freshest_snapshot = str(snapshot_df.iloc[0]["snapshot"])
        freshest_snapshot_age_days = int(snapshot_df.iloc[0]["snapshot_age_days"])

    return {
        "dataset_count": int(len(status_df)),
        "remote_count": int(source_counts.get("supabase_public", 0) + source_counts.get("supabase_private", 0)),
        "fallback_count": int(source_counts.get("local_fallback", 0)),
        "local_only_count": int(source_counts.get("local_only", 0)),
        "unavailable_count": int(source_counts.get("unavailable", 0) + source_counts.get("unknown", 0)),
        "fallback_names": status_df.loc[status_df["source_code"] == "local_fallback", "dataset"].tolist(),
        "unavailable_names": status_df.loc[
            status_df["source_code"].isin(["unavailable", "unknown"]), "dataset"
        ].tolist(),
        "freshest_snapshot": freshest_snapshot,
        "freshest_snapshot_age_days": freshest_snapshot_age_days,
    }


def _build_source_refresh_status() -> tuple[pd.DataFrame, pd.DataFrame]:
    registry_df = load_data_sources_runtime()
    runs_df = load_data_source_runs()
    if registry_df.empty:
        return pd.DataFrame(), pd.DataFrame()

    status_df = registry_df.copy()
    for column in ("last_updated", "next_update_due"):
        if column in status_df.columns:
            status_df[column] = pd.to_datetime(status_df[column], errors="coerce")
    status_df["enabled"] = status_df.get("enabled", False).fillna(False).astype(bool)
    status_df["blocking"] = status_df.get("blocking", False).fillna(False).astype(bool)
    today_ts = pd.Timestamp(dt.date.today())
    status_df["is_overdue"] = status_df["enabled"] & status_df["next_update_due"].notna() & (
        status_df["next_update_due"].dt.normalize() <= today_ts
    )
    status_df["last_updated_label"] = status_df["last_updated"].dt.strftime("%d/%m/%Y").fillna("—")
    status_df["next_update_due_label"] = status_df["next_update_due"].dt.strftime("%d/%m/%Y").fillna("—")
    status_df["last_run_status"] = status_df.get("last_run_status", "").fillna("").replace("", "sin registro")
    status_df["freshness_sla_days"] = pd.to_numeric(
        status_df.get("freshness_sla_days"), errors="coerce"
    ).astype("Int64")

    if not runs_df.empty:
        runs_df = runs_df.copy()
        for column in ("started_at", "finished_at"):
            if column in runs_df.columns:
                runs_df[column] = pd.to_datetime(runs_df[column], errors="coerce")
        runs_df["finished_at_label"] = runs_df["finished_at"].dt.strftime("%d/%m/%Y %H:%M").fillna("—")
        runs_df["records_written"] = pd.to_numeric(runs_df.get("records_written"), errors="coerce").fillna(0).astype(int)
        runs_df = runs_df.sort_values(["finished_at", "source_key"], ascending=[False, True]).reset_index(drop=True)

    status_df = status_df.sort_values(
        ["is_overdue", "blocking", "enabled", "source_name"],
        ascending=[False, False, False, True],
    ).reset_index(drop=True)
    return status_df, runs_df


@_dialog("Inspector de datasets", width="large")
def open_dataset_inspector():
    access = _access_context()
    section_name = _current_section_name()
    catalog = _dataset_catalog()
    runtime_df = _build_runtime_dataset_status()
    runtime_summary = _summarize_runtime_dataset_status(runtime_df)
    dataset_name = st.selectbox("Dataset", list(catalog.keys()), index=0)
    meta = catalog[dataset_name]
    df = meta["df"]
    read_source, read_detail = _describe_dataset_read_source(meta)
    snapshot_label, snapshot_age_days = _dataset_snapshot_info(meta)

    with st.expander("Estado operativo de la sesión", expanded=False):
        st.caption(f"Sección actual: `{section_name}`")
        st.caption(
            f"Datasets instrumentados: {runtime_summary['dataset_count']} · "
            f"remotos: {runtime_summary['remote_count']} · "
            f"fallback: {runtime_summary['fallback_count']} · "
            f"solo local: {runtime_summary['local_only_count']} · "
            f"no disponibles: {runtime_summary['unavailable_count']}"
        )
        st.dataframe(
            runtime_df[["dataset", "read_source", "rows", "snapshot", "sensitive"]],
            width="stretch",
            height=320,
            hide_index=True,
        )

    st.caption(f"Fuente: `{meta['source']}`")
    st.caption(f"Lectura efectiva: `{read_source}` · `{read_detail}`")
    row_metric = "Restringido" if meta["sensitive"] and not access["can_view_sensitive"] else f"{len(df):,}"
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Filas", row_metric)
    c2.metric("Columnas", f"{len(df.columns):,}" if hasattr(df, "columns") else "—")
    c3.metric("Sensibilidad", "Restringido" if meta["sensitive"] else "Público")
    c4.metric("Origen", read_source)
    c5.metric("Snapshot local", snapshot_label)
    if snapshot_age_days is not None:
        st.caption(f"Respaldo local disponible de `{dataset_name}`: {snapshot_label} ({snapshot_age_days} días).")

    if meta["sensitive"] and not access["can_view_sensitive"]:
        st.warning(
            "Este dataset está marcado como sensible. Inicia sesión con un usuario autorizado "
            "para ver muestras o columnas detalladas."
        )
        return

    sample_size = st.slider("Filas de muestra", min_value=5, max_value=100, value=20, step=5)
    preview = df.head(sample_size).copy()
    st.dataframe(preview, width="stretch", height=420)
    st.download_button(
        "Exportar muestra CSV",
        make_csv(preview),
        file_name=f"preview_{dataset_name.lower().replace(' ', '_')}.csv",
        mime="text/csv",
    )


@_fragment
def render_operational_strip():
    access = _access_context()
    section_name = _current_section_name()
    engine_label = _backend["engine"].upper()
    engine_short = engine_label[:6] if len(engine_label) > 6 else engine_label
    acceso_short = "Sí" if access["can_view_sensitive"] else "No"
    runtime_df = _build_runtime_dataset_status()
    runtime_summary = _summarize_runtime_dataset_status(runtime_df)
    c1, c2, c3, c4, c5, c6 = st.columns([1.0, 0.9, 0.9, 0.9, 1.1, 0.9])
    c1.metric("Motor datos", engine_short)
    c2.metric("Modo", _backend.get("source_mode", "auto"))
    c3.metric("Remoto", f"{runtime_summary['remote_count']}")
    c4.metric("Fallback", f"{runtime_summary['fallback_count']}")
    c5.metric("Snapshot", runtime_summary["freshest_snapshot"])
    c6.metric("Acceso sens.", acceso_short)

    st.caption(_backend["detail"])
    st.caption(
        f"Sección actual `{section_name}`: {runtime_summary['dataset_count']} datasets instrumentados · "
        f"{runtime_summary['local_only_count']} solo local · "
        f"{runtime_summary['unavailable_count']} no disponibles."
    )
    if runtime_summary["freshest_snapshot_age_days"] is not None:
        st.caption(
            "Respaldo local más reciente: "
            f"{runtime_summary['freshest_snapshot']} ({runtime_summary['freshest_snapshot_age_days']} días)."
        )
    if _backend.get("source_mode") != "local":
        st.caption(
            "La frescura mostrada corresponde al respaldo local disponible en este host; "
            "no necesariamente al último sync remoto en Supabase."
        )

    if runtime_summary["fallback_count"] > 0:
        st.warning(
            "Fallback local activo en: "
            f"{_format_dataset_names(runtime_summary['fallback_names'])}."
        )
    elif runtime_summary["unavailable_count"] > 0:
        st.info(
            "Datasets no disponibles en esta sesión: "
            f"{_format_dataset_names(runtime_summary['unavailable_names'])}."
        )
    else:
        st.caption("Sin fallbacks activos en la sesión actual.")

    b1, b2 = st.columns(2)
    with b1:
        if st.button("🔍 Datasets", key="btn_open_dataset_inspector", width="stretch"):
            open_dataset_inspector()
    with b2:
        if st.button("♻ Limpiar caché", key="btn_clear_dashboard_cache", width="stretch"):
            st.cache_data.clear()
            st.rerun()


# ─── Helpers ──────────────────────────────────────────────────────────────────

def kpi(label, value, sub="", color=BLUE):
    sub_html = (f'<div style="font-size:0.71rem;color:#94A3B8;margin-top:3px;'
                f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{sub}</div>') if sub else ''
    return (
        f"<div style='flex:1;min-width:0;background:white;border-radius:14px;padding:18px 16px 16px;"
        f"border:1px solid rgba(0,59,111,0.07);border-top:3px solid {color};"
        f"box-shadow:0 2px 12px rgba(0,30,66,0.06),0 1px 3px rgba(0,0,0,0.03)'>"
        f"<div style='font-size:1.85rem;font-weight:700;color:{color};line-height:1.1;"
        f"letter-spacing:-0.5px'>{value}</div>"
        f"<div style='font-size:0.7rem;color:#64748B;margin-top:7px;font-weight:500;"
        f"text-transform:uppercase;letter-spacing:0.6px'>{label}</div>"
        f"{sub_html}</div>"
    )

def kpi_row(*cards):
    html = '<div style="display:flex;gap:10px;margin-bottom:10px">' + ''.join(cards) + '</div>'
    st.markdown(html, unsafe_allow_html=True)

def sec(title):
    st.markdown(
        f"<div style='display:flex;align-items:center;gap:9px;margin-bottom:14px;margin-top:4px'>"
        f"<div style='width:3px;height:18px;background:linear-gradient(180deg,{BLUE},{RED});"
        f"border-radius:2px;flex-shrink:0'></div>"
        f"<span style='color:#0F172A;font-size:0.9rem;font-weight:600;letter-spacing:-0.1px'>"
        f"{title}</span></div>",
        unsafe_allow_html=True
    )

def make_csv(df) -> bytes:
    """CSV con BOM UTF-8 para compatibilidad con Excel en Windows/Mac."""
    return df.to_csv(index=False).encode("utf-8-sig")


def _bool_from_any(value) -> bool:
    if isinstance(value, bool):
        return value
    if pd.isna(value):
        return False
    return str(value).strip().lower() in {"1", "true", "t", "yes", "y", "si", "sí"}


def _text_or_empty(value) -> str:
    return "" if pd.isna(value) else str(value).strip()


_HTML_TAG_RE = re.compile(r"<[^>]+>")
_HTML_ATTR_RE = re.compile(r"(href|target)\s*=\s*\"[^\"]*\"?", re.IGNORECASE)
_URL_RE = re.compile(r"https?://\S+")


def _clean_html_text(value) -> str:
    text = html_unescape(_text_or_empty(value))
    text = text.replace("\xa0", " ")
    text = re.sub(r"<a\b[^>]*", " ", text, flags=re.IGNORECASE)
    text = _HTML_ATTR_RE.sub(" ", text)
    text = _URL_RE.sub(" ", text)
    text = text.replace("<a", " ").replace("</a", " ").replace(">", " ")
    text = _HTML_TAG_RE.sub(" ", text)
    text = re.sub(r"\s+", " ", text).strip(" -\n\t")
    return text


def _clean_news_title(title, source_name="") -> str:
    clean_title = _clean_html_text(title)
    clean_source = _clean_html_text(source_name)
    if clean_source:
        for sep in [" - ", " | ", " — ", " – "]:
            suffix = f"{sep}{clean_source}"
            if clean_title.lower().endswith(suffix.lower()):
                clean_title = clean_title[:-len(suffix)].strip()
                break
    return clean_title


def _clean_news_snippet(snippet, title="") -> str:
    clean_snippet = _clean_html_text(snippet)
    clean_title = _clean_html_text(title)
    if clean_title and clean_snippet.lower().startswith(clean_title.lower()):
        clean_snippet = clean_snippet[len(clean_title):].lstrip(" .:-")
    if clean_snippet.lower().startswith("leer noticia completa"):
        return ""
    return clean_snippet


def _pretty_topic_term(term: str) -> str:
    text = _clean_html_text(term).replace("_", " ")
    text = re.sub(r"\s+", " ", text).strip(" -")
    if not text:
        return ""
    replacements = {
        "ph": "pH",
        "iii": "III",
        "ii": "II",
        "iv": "IV",
        "vi": "VI",
        "vii": "VII",
        "viii": "VIII",
        "ix": "IX",
        "x": "X",
    }
    words = []
    for token in text.split():
        lower = token.lower()
        words.append(replacements.get(lower, token.capitalize()))
    return " ".join(words)


def _build_topic_label(topic_id, name="", representation="", max_terms: int = 3) -> str:
    candidates = []
    if representation:
        try:
            parsed = ast.literal_eval(representation) if isinstance(representation, str) else representation
            if isinstance(parsed, (list, tuple)):
                candidates.extend([_pretty_topic_term(str(item)) for item in parsed if _pretty_topic_term(str(item))])
        except Exception:
            pass
    if not candidates and name:
        raw_name = re.sub(r"^-?\\d+_", "", _clean_html_text(str(name)))
        candidates.extend([_pretty_topic_term(part) for part in raw_name.split("_") if _pretty_topic_term(part)])

    ranked = sorted(
        [(idx, cand, len(cand.split())) for idx, cand in enumerate(candidates)],
        key=lambda item: (-item[2], item[0]),
    )
    selected = []
    selected_norm = []
    for _, cand, _ in ranked:
        norm = cand.lower()
        tokens = set(norm.split())
        if not norm:
            continue
        if norm in selected_norm:
            continue
        if any(norm in prev or tokens.issubset(set(prev.split())) for prev in selected_norm):
            continue
        selected.append(cand)
        selected_norm.append(norm)
        if len(selected) >= max_terms:
            break

    if not selected and name:
        fallback = _pretty_topic_term(re.sub(r"^-?\\d+_", "", _clean_html_text(str(name))))
        if fallback:
            selected = [fallback]

    prefix = f"Tema {int(topic_id)}" if pd.notna(topic_id) and int(topic_id) >= 0 else "Outliers"
    return prefix + (f" · {' · '.join(selected)}" if selected else "")


def _topic_terms_preview(representation, max_terms: int = 6) -> str:
    if pd.isna(representation):
        return ""
    try:
        parsed = ast.literal_eval(representation) if isinstance(representation, str) else representation
        if isinstance(parsed, (list, tuple)):
            return ", ".join(
                [_pretty_topic_term(str(item)) for item in parsed[:max_terms] if _pretty_topic_term(str(item))]
            )
    except Exception:
        return _pretty_topic_term(str(representation))
    return _pretty_topic_term(str(representation))


def _normalize_convocatorias_df(df: pd.DataFrame, mode: str) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    if {"title", "link", "published"}.issubset(df.columns):
        out = pd.DataFrame({
            "conv_id": df.get("conv_id", pd.Series(range(len(df)))).astype(str),
            "tipo_registro": "legacy_monitor",
            "titulo": df.get("title", ""),
            "organismo": df.get("source_name", df.get("fuente", "Monitor externo")),
            "categoria": "Monitor legado",
            "estado": "Revisar",
            "apertura_texto": "",
            "cierre_texto": "",
            "fallo_texto": "",
            "apertura_iso": "",
            "cierre_iso": "",
            "perfil_objetivo": "Revisión manual",
            "relevancia_cchen": "Revisar",
            "fuente": df.get("fuente", "Monitor legado"),
            "es_oficial": False,
            "postulable": False,
            "url": df.get("link", ""),
            "notas": df.get("snippet", ""),
        })
        published_dt = pd.to_datetime(df.get("published", pd.Series(dtype=str)), errors="coerce", utc=True)
        out["apertura_dt"] = published_dt.dt.tz_convert(None)
        out["cierre_dt"] = pd.NaT
        out["orden"] = range(len(out))
        out["modo_carga"] = mode
        return out

    rename_map = {
        "title": "titulo",
        "link": "url",
        "source_name": "organismo",
    }
    out = df.rename(columns=rename_map).copy()
    expected = [
        "conv_id", "tipo_registro", "titulo", "organismo", "categoria", "estado",
        "apertura_texto", "cierre_texto", "fallo_texto", "apertura_iso", "cierre_iso",
        "perfil_objetivo", "relevancia_cchen", "fuente", "es_oficial",
        "postulable", "url", "notas",
    ]
    for col in expected:
        if col not in out.columns:
            out[col] = ""

    out["titulo"] = out["titulo"].map(_text_or_empty)
    if out["conv_id"].map(_text_or_empty).eq("").any():
        out.loc[out["conv_id"].map(_text_or_empty).eq(""), "conv_id"] = out.loc[
            out["conv_id"].map(_text_or_empty).eq(""), "titulo"
        ].map(lambda x: hashlib.md5(x.encode("utf-8")).hexdigest()[:12])
    out["tipo_registro"] = out["tipo_registro"].map(_text_or_empty).replace("", "convocatoria")
    out["organismo"] = out["organismo"].map(_text_or_empty).replace("", "ANID")
    out["categoria"] = out["categoria"].map(_text_or_empty).replace("", "Convocatorias")
    out["estado"] = out["estado"].map(_text_or_empty).replace("", "Revisar")
    out["apertura_texto"] = out["apertura_texto"].map(_text_or_empty)
    out["cierre_texto"] = out["cierre_texto"].map(_text_or_empty)
    out["fallo_texto"] = out["fallo_texto"].map(_text_or_empty)
    out["perfil_objetivo"] = out["perfil_objetivo"].map(_text_or_empty).replace("", "General")
    out["relevancia_cchen"] = out["relevancia_cchen"].map(_text_or_empty).replace("", "Media")
    out["fuente"] = out["fuente"].map(_text_or_empty).replace("", "Curado")
    out["url"] = out["url"].map(_text_or_empty)
    out["notas"] = out["notas"].map(_text_or_empty)
    out["es_oficial"] = out["es_oficial"].map(_bool_from_any)
    out["postulable"] = out["postulable"].map(_bool_from_any)
    out["apertura_dt"] = pd.to_datetime(out["apertura_iso"], errors="coerce")
    out["cierre_dt"] = pd.to_datetime(out["cierre_iso"], errors="coerce")
    out["orden"] = range(len(out))
    out["modo_carga"] = mode
    return out


def _load_convocatorias_data():
    base = BASE / "Vigilancia"
    curated = base / "convocatorias_curadas.csv"
    legacy = base / "convocatorias.csv"

    if curated.exists():
        return _normalize_convocatorias_df(pd.read_csv(curated), mode="curated"), "curated", curated
    if legacy.exists():
        return _normalize_convocatorias_df(pd.read_csv(legacy), mode="legacy"), "legacy", legacy
    return pd.DataFrame(), "missing", curated


@st.cache_data
def _load_portafolio_seed() -> pd.DataFrame:
    p = BASE / "Transferencia" / "portafolio_tecnologico_semilla.csv"
    if not p.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(p)
    except Exception:
        return pd.DataFrame()


@st.cache_data
def _load_entity_model_tables() -> tuple[pd.DataFrame, pd.DataFrame]:
    base = BASE / "Gobernanza"
    ent = base / "modelo_entidades_observatorio.csv"
    rel = base / "relaciones_entidades_observatorio.csv"
    ent_df = pd.read_csv(ent) if ent.exists() else pd.DataFrame()
    rel_df = pd.read_csv(rel) if rel.exists() else pd.DataFrame()
    return ent_df, rel_df


def _extract_agreement_country_counts(df: pd.DataFrame) -> pd.Series:
    if df is None or df.empty:
        return pd.Series(dtype="int64")

    for col in df.columns:
        low = str(col).lower()
        if "pais" in low or "país" in low or "region" in low or "región" in low:
            s = df[col].dropna().astype(str).str.strip()
            if not s.empty:
                return s.value_counts()

    # Fallback para archivos planos donde la primera fila útil define encabezados
    try:
        raw = df.astype(str).fillna("")
        for idx in range(min(len(raw), 8)):
            row = [str(v).strip().upper() for v in raw.iloc[idx].tolist()]
            if "PAIS" in row or "PAÍS" in row:
                col_idx = row.index("PAIS") if "PAIS" in row else row.index("PAÍS")
                values = raw.iloc[idx + 1 :, col_idx].astype(str).str.strip()
                values = values[(values != "") & (~values.str.startswith("TABLA")) & (values != "nan")]
                if not values.empty:
                    return values.value_counts()
    except Exception:
        pass
    return pd.Series(dtype="int64")


def _build_matching_profiles_summary(matching_df: pd.DataFrame) -> pd.DataFrame:
    if matching_df is None or matching_df.empty:
        return pd.DataFrame()
    rows = []
    for perfil, subset in matching_df.groupby("perfil_nombre", dropna=False):
        subset = subset.sort_values(["score_total", "estado", "cierre_iso", "apertura_iso"], ascending=[False, True, True, True], na_position="last")
        abiertos = int((subset["estado"] == "Abierto").sum())
        proximos = int((subset["estado"] == "Próximo").sum())
        destacados = subset["convocatoria_titulo"].head(3).tolist()
        max_score = int(pd.to_numeric(subset["score_total"], errors="coerce").fillna(0).max())
        fuerza = "Alta" if max_score >= 75 else "Media" if max_score >= 55 else "Inicial"
        evidencia = _text_or_empty(subset["evidence_summary"].dropna().iloc[0]) if "evidence_summary" in subset.columns and subset["evidence_summary"].notna().any() else "Sin evidencia sintetizada."
        owners = ", ".join(sorted({_text_or_empty(v) for v in subset["owner_unit"].dropna().tolist() if _text_or_empty(v)}))
        elegibles = int((subset["eligibility_status"] == "Cumple base observada").sum()) if "eligibility_status" in subset.columns else 0
        rows.append({
            "perfil": _text_or_empty(perfil),
            "fuerza_interna": fuerza,
            "evidencia": evidencia,
            "senal": f"{elegibles} oportunidades con elegibilidad base observada.",
            "abiertas": abiertos,
            "proximas": proximos,
            "oportunidades_destacadas": " | ".join(destacados) if destacados else "Sin oportunidades asociadas",
            "unidad_responsable": owners or "Sin unidad asignada",
        })
    return pd.DataFrame(rows)


def _build_entity_observed_counts() -> dict:
    conv_df = entity_convocatorias if entity_convocatorias is not None and not entity_convocatorias.empty else pd.DataFrame()
    portafolio_df = _load_portafolio_seed()
    return {
        "publicacion": len(pub),
        "persona": len(entity_personas) if entity_personas is not None and not entity_personas.empty else (ch["nombre"].nunique() if "nombre" in ch.columns else len(ch)),
        "investigador_cchen": int(entity_personas["is_cchen_investigator"].astype(str).str.lower().isin(["true", "1"]).sum()) if entity_personas is not None and not entity_personas.empty and "is_cchen_investigator" in entity_personas.columns else (auth[auth["is_cchen_affiliation"] == True]["author_name"].nunique() if "author_name" in auth.columns else 0),
        "proyecto": len(entity_projects) if entity_projects is not None and not entity_projects.empty else len(anid),
        "convocatoria": len(conv_df) if not conv_df.empty else 0,
        "activo_tecnologico": len(portafolio_df),
        "institucion": auth["institution_name"].dropna().nunique() if "institution_name" in auth.columns else 0,
        "acuerdo": len(acuerdos),
        "convenio": len(convenios),
        "orcid": len(orcid),
        "patente": len(patents),
    }


def generate_pdf_report(question: str, answer: str,
                        pub_data=None, pub_enr_data=None,
                        auth_data=None, anid_data=None, ch_data=None,
                        chart_decision=None):
    """Genera un PDF con gráficos contextuales según el tema de la consulta."""
    try:
        import re, datetime as _dtt
        from io import BytesIO
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Image as RLImage

        BLUE_RL = colors.HexColor("#003B6F")
        RED_RL  = colors.HexColor("#C8102E")
        GREY_RL = colors.HexColor("#666666")
        BG_RL   = colors.HexColor("#EEF4FF")
        PAGE_W  = 16 * cm

        buf = BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4,
                                rightMargin=2.5*cm, leftMargin=2.5*cm,
                                topMargin=2*cm, bottomMargin=2*cm)
        styles = getSampleStyleSheet()
        s_title  = ParagraphStyle("ct",  parent=styles["Title"],    textColor=BLUE_RL, fontSize=16, spaceAfter=4)
        s_meta   = ParagraphStyle("cm",  parent=styles["Normal"],   textColor=GREY_RL, fontSize=9,  spaceAfter=10)
        s_h2     = ParagraphStyle("ch",  parent=styles["Heading2"], textColor=BLUE_RL, fontSize=11, spaceAfter=4)
        s_ctx    = ParagraphStyle("cc",  parent=styles["Heading3"], textColor=GREY_RL, fontSize=9,
                                  spaceAfter=6, spaceBefore=8)
        s_q      = ParagraphStyle("cq",  parent=styles["Normal"],   textColor=BLUE_RL, fontSize=10,
                                  leftIndent=8, backColor=BG_RL, borderPad=6, leading=15, spaceAfter=10)
        s_body   = ParagraphStyle("cb",  parent=styles["Normal"],   fontSize=10, leading=15, spaceAfter=4)
        s_bullet = ParagraphStyle("cbu", parent=styles["Normal"],   fontSize=10, leading=13,
                                  leftIndent=14, spaceAfter=2)
        s_footer = ParagraphStyle("cf",  parent=styles["Normal"],   textColor=GREY_RL, fontSize=8)

        def _esc(t):
            t = t.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
            t = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', t)
            t = re.sub(r'__(.+?)__',     r'<b>\1</b>', t)
            t = re.sub(r'\*(.+?)\*',     r'<i>\1</i>', t)
            return t

        def _png(fig):
            ib = BytesIO(); fig.savefig(ib, format="png", dpi=150, bbox_inches="tight")
            plt.close(fig); ib.seek(0); return ib

        def _apply_style(ax):
            ax.spines[["top","right"]].set_visible(False)
            ax.tick_params(labelsize=7, colors="#334155")
            ax.set_facecolor("white")
            ax.figure.patch.set_facecolor("white")

        # ── Tema: desde decisión LLM o fallback por keywords ──────────────────
        _cd = chart_decision or {}
        _researchers = _cd.get("researchers") or []
        _keyword     = _cd.get("keyword") or None
        _yr_start    = _cd.get("start_year") or None
        _yr_end      = _cd.get("end_year") or None

        if _cd.get("chart") in ("investigators","funding","quality","collaboration",
                                "production","human_capital"):
            topic = _cd["chart"]
        else:
            _text = (question + " " + answer).lower()
            def _has(*words): return any(w in _text for w in words)
            if _has("investigador","plasma","autor","quién trabaja","quien trabaja","perfil"):
                topic = "investigators"
            elif _has("financiamiento","anid","fondecyt","fondo","proyecto","monto"):
                topic = "funding"
            elif _has("capital humano","formación","modalidad","tesista","becario"):
                topic = "human_capital"
            elif _has("colaboración","internacional","país","extranjero","coautoría"):
                topic = "collaboration"
            elif _has("cuartil","calidad","sjr","q1","q2","acceso abierto"):
                topic = "quality"
            else:
                topic = "production"

        # ── Generadores de gráficos por tema ──────────────────────────────────

        def chart_investigators():
            """Investigadores CCHEN: muestra los mencionados o top 15."""
            if auth_data is None or auth_data.empty: return []
            _a = auth_data[auth_data["is_cchen_affiliation"] == True]

            # Filtrar por investigadores mencionados en la respuesta
            if _researchers:
                _norm = [r.lower().strip() for r in _researchers]
                _mask = _a["author_name"].str.lower().apply(
                    lambda n: any(r in n or n in r for r in _norm))
                _af = _a[_mask]
                top = _af.groupby("author_name")["work_id"].nunique().sort_values(ascending=False)
                _title = f"Investigadores CCHEN mencionados — producción"
            else:
                top = _a.groupby("author_name")["work_id"].nunique().sort_values(ascending=False).head(15)
                _title = "Top investigadores CCHEN — producción total"

            if top.empty:
                top = _a.groupby("author_name")["work_id"].nunique().sort_values(ascending=False).head(15)

            # Si hay keyword, también mostrar evolución temporal de esos investigadores
            imgs = []
            _h = max(3, min(5, 0.4 * len(top) + 1.5))
            fig, ax = plt.subplots(figsize=(7, _h))
            _apply_style(ax)
            ax.barh(top.index[::-1], top.values[::-1], color="#003B6F", alpha=0.82)
            for i, v in enumerate(top.values[::-1]):
                ax.text(v + 0.2, i, str(int(v)), va="center", fontsize=7, color="#334155")
            ax.set_xlabel("N° publicaciones", fontsize=8)
            ax.set_title(_title, fontsize=9, fontweight="bold", color="#003B6F")
            fig.tight_layout(pad=0.5)
            imgs.append((_png(fig), PAGE_W, PAGE_W * _h / 7))

            # Gráfico de citas por investigador si hay datos de pub
            if pub_data is not None and not top.empty:
                try:
                    _cites = (auth_data[auth_data["author_name"].isin(top.index[:8])]
                              .merge(pub_data[["openalex_id","cited_by_count"]],
                                     left_on="work_id", right_on="openalex_id", how="left")
                              .groupby("author_name")["cited_by_count"].sum()
                              .sort_values(ascending=False))
                    if not _cites.empty:
                        fig2, ax2 = plt.subplots(figsize=(7, 3))
                        _apply_style(ax2)
                        ax2.barh(_cites.index[::-1], _cites.values[::-1], color="#C8102E", alpha=0.75)
                        for i, v in enumerate(_cites.values[::-1]):
                            ax2.text(v + 1, i, str(int(v)), va="center", fontsize=7)
                        ax2.set_xlabel("Citas totales", fontsize=8)
                        ax2.set_title("Citas por investigador", fontsize=9,
                                      fontweight="bold", color="#003B6F")
                        fig2.tight_layout(pad=0.5)
                        imgs.append((_png(fig2), PAGE_W, PAGE_W * 3 / 7))
                except Exception:
                    pass
            return imgs

        def chart_funding():
            """Fondos ANID por programa y evolución temporal."""
            if anid_data is None or anid_data.empty: return []
            imgs = []
            # Chart 1: por instrumento
            inst = anid_data["instrumento_norm"].value_counts().head(8)
            fig1, ax1 = plt.subplots(figsize=(6, 3))
            _apply_style(ax1)
            cs = ["#003B6F","#00A896","#F4A60D","#C8102E","#7B2D8B","#E76F51","#52B788","#264653"]
            bars = ax1.barh(inst.index[::-1], inst.values[::-1],
                            color=cs[:len(inst)], alpha=0.85)
            for bar, v in zip(bars, inst.values[::-1]):
                ax1.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height()/2,
                         str(int(v)), va="center", fontsize=7)
            ax1.set_xlabel("N° proyectos", fontsize=8)
            ax1.set_title("Proyectos ANID por instrumento", fontsize=9,
                          fontweight="bold", color="#003B6F")
            fig1.tight_layout(pad=0.5)
            imgs.append((_png(fig1), PAGE_W * 0.9, PAGE_W * 0.9 * 3 / 6))
            # Chart 2: evolución temporal
            yr = anid_data.dropna(subset=["anio_concurso"])
            yr = yr[yr["anio_concurso"].between(2010, 2025)]
            by_yr = yr.groupby("anio_concurso").size().reset_index(name="N")
            if len(by_yr) > 2:
                fig2, ax2 = plt.subplots(figsize=(7, 2.5))
                _apply_style(ax2)
                ax2.bar(by_yr["anio_concurso"].astype(int),
                        by_yr["N"], color="#003B6F", alpha=0.82)
                ax2.set_xlabel("Año concurso", fontsize=8)
                ax2.set_ylabel("N° proyectos", fontsize=8)
                ax2.set_title("Proyectos adjudicados por año", fontsize=9,
                              fontweight="bold", color="#003B6F")
                fig2.tight_layout(pad=0.5)
                imgs.append((_png(fig2), PAGE_W, PAGE_W * 2.5 / 7))
            return imgs

        def chart_human_capital():
            """Capital humano por modalidad y evolución."""
            if ch_data is None or ch_data.empty: return []
            imgs = []
            # Chart 1: composición por tipo
            tipo = ch_data["tipo_norm"].value_counts() if "tipo_norm" in ch_data.columns else pd.Series()
            if not tipo.empty:
                fig1, ax1 = plt.subplots(figsize=(5, 3.5))
                cs = ["#003B6F","#00A896","#F4A60D","#C8102E","#7B2D8B","#E76F51"]
                wedges, texts, autotexts = ax1.pie(tipo.values, labels=tipo.index,
                    colors=cs[:len(tipo)], autopct="%1.0f%%",
                    pctdistance=0.82, startangle=140)
                for t in texts: t.set_fontsize(7)
                for a in autotexts: a.set_fontsize(7); a.set_color("white")
                ax1.set_title("Composición por modalidad", fontsize=9,
                              fontweight="bold", color="#003B6F")
                fig1.patch.set_facecolor("white")
                fig1.tight_layout(pad=0.3)
                imgs.append((_png(fig1), PAGE_W * 0.6, PAGE_W * 0.6 * 3.5 / 5))
            # Chart 2: evolución anual
            if "anio_hoja" in ch_data.columns:
                yr2 = ch_data.dropna(subset=["anio_hoja"])
                by_yr2 = yr2.groupby("anio_hoja").size().reset_index(name="N")
                if len(by_yr2) > 1:
                    fig2, ax2 = plt.subplots(figsize=(6, 2.5))
                    _apply_style(ax2)
                    ax2.bar(by_yr2["anio_hoja"].astype(int), by_yr2["N"],
                            color="#00A896", alpha=0.82)
                    ax2.set_xlabel("Año", fontsize=8)
                    ax2.set_ylabel("N° personas", fontsize=8)
                    ax2.set_title("Capital humano I+D por año", fontsize=9,
                                  fontweight="bold", color="#003B6F")
                    fig2.tight_layout(pad=0.5)
                    imgs.append((_png(fig2), PAGE_W, PAGE_W * 2.5 / 6))
            return imgs

        def chart_collaboration():
            """Top instituciones y países colaboradores."""
            if auth_data is None or auth_data.empty: return []
            imgs = []
            _ext = auth_data[auth_data["is_cchen_affiliation"] == False]
            # Chart 1: top instituciones
            inst = _ext["institution_name"].value_counts().head(12).dropna()
            if not inst.empty:
                fig1, ax1 = plt.subplots(figsize=(7, 4))
                _apply_style(ax1)
                ax1.barh(inst.index[::-1], inst.values[::-1], color="#003B6F", alpha=0.82)
                for i, v in enumerate(inst.values[::-1]):
                    ax1.text(v + 0.1, i, str(int(v)), va="center", fontsize=7)
                ax1.set_xlabel("N° co-autorías", fontsize=8)
                ax1.set_title("Principales instituciones colaboradoras", fontsize=9,
                              fontweight="bold", color="#003B6F")
                fig1.tight_layout(pad=0.5)
                imgs.append((_png(fig1), PAGE_W, PAGE_W * 4 / 7))
            # Chart 2: top países
            if "country_code" in _ext.columns:
                pais = _ext["country_code"].value_counts().head(10).dropna()
                if not pais.empty:
                    fig2, ax2 = plt.subplots(figsize=(5, 2.8))
                    _apply_style(ax2)
                    cs2 = ["#003B6F","#00A896","#F4A60D","#C8102E","#7B2D8B",
                           "#E76F51","#52B788","#264653","#A8DADC","#457B9D"]
                    ax2.bar(pais.index, pais.values, color=cs2[:len(pais)], alpha=0.85)
                    ax2.set_xlabel("País (ISO-2)", fontsize=8)
                    ax2.set_ylabel("N° co-autorías", fontsize=8)
                    ax2.set_title("Colaboración por país", fontsize=9,
                                  fontweight="bold", color="#003B6F")
                    fig2.tight_layout(pad=0.5)
                    imgs.append((_png(fig2), PAGE_W * 0.7, PAGE_W * 0.7 * 2.8 / 5))
            return imgs

        def chart_quality():
            """Cuartiles SJR + acceso abierto."""
            if pub_enr_data is None or pub_enr_data.empty: return []
            imgs = []
            if "quartile" in pub_enr_data.columns:
                qc = pub_enr_data["quartile"].value_counts().reindex(["Q1","Q2","Q3","Q4"]).fillna(0)
                fig1, ax1 = plt.subplots(figsize=(5, 3))
                _apply_style(ax1)
                cs = ["#003B6F","#00A896","#F4A60D","#C8102E"]
                bars = ax1.bar(qc.index, qc.values, color=cs, alpha=0.88)
                for bar, v in zip(bars, qc.values):
                    if v > 0:
                        ax1.text(bar.get_x() + bar.get_width()/2,
                                 bar.get_height() + 0.5, str(int(v)),
                                 ha="center", va="bottom", fontsize=8, fontweight="bold")
                ax1.set_xlabel("Cuartil SJR", fontsize=8)
                ax1.set_ylabel("N° papers", fontsize=8)
                ax1.set_title("Distribución por cuartil SJR", fontsize=9,
                              fontweight="bold", color="#003B6F")
                fig1.tight_layout(pad=0.5)
                imgs.append((_png(fig1), PAGE_W * 0.6, PAGE_W * 0.6 * 3 / 5))
            if pub_data is not None and "is_oa" in pub_data.columns:
                oa_c = pub_data["is_oa"].value_counts()
                fig2, ax2 = plt.subplots(figsize=(3.5, 3))
                ax2.pie([oa_c.get(True,0), oa_c.get(False,0)],
                        labels=["Acceso abierto","Cerrado"],
                        colors=["#00A896","#CBD5E1"], autopct="%1.0f%%",
                        pctdistance=0.8, startangle=90)
                ax2.set_title("Acceso abierto", fontsize=9,
                              fontweight="bold", color="#003B6F")
                fig2.patch.set_facecolor("white")
                fig2.tight_layout(pad=0.3)
                imgs.append((_png(fig2), PAGE_W * 0.45, PAGE_W * 0.45))
            return imgs

        def chart_production():
            """Producción por año + áreas temáticas, con filtro de rango si aplica."""
            if pub_data is None or pub_data.empty: return []
            imgs = []
            _y0 = int(_yr_start) if _yr_start else 2000
            _y1 = int(_yr_end)   if _yr_end   else 2025
            by_yr = (pub_data[pub_data["year"].between(_y0, _y1)]
                     .groupby("year")
                     .agg(Papers=("openalex_id","count"), Citas=("cited_by_count","sum"))
                     .reset_index())
            fig1, ax1 = plt.subplots(figsize=(7.5, 3))
            _apply_style(ax1)
            ax2 = ax1.twinx()
            ax1.bar(by_yr["year"], by_yr["Papers"], color="#003B6F", alpha=0.82)
            ax2.plot(by_yr["year"], by_yr["Citas"], color="#C8102E",
                     linewidth=1.8, marker="o", markersize=3)
            ax1.set_xlabel("Año", fontsize=8)
            ax1.set_ylabel("N° Papers", fontsize=8, color="#003B6F")
            ax2.set_ylabel("Citas", fontsize=8, color="#C8102E")
            ax2.tick_params(labelsize=7, colors="#C8102E")
            p1 = mpatches.Patch(color="#003B6F", label="Papers")
            p2 = mpatches.Patch(color="#C8102E", label="Citas")
            ax1.legend(handles=[p1, p2], fontsize=7, loc="upper left")
            ax1.set_title(f"Evolución de producción científica CCHEN ({_y0}–{_y1})",
                          fontsize=9, fontweight="bold", color="#003B6F")
            fig1.tight_layout(pad=0.5)
            imgs.append((_png(fig1), PAGE_W, PAGE_W * 3 / 7.5))
            # Top journals
            if "source" in pub_data.columns:
                jrnl = pub_data["source"].value_counts().head(8).dropna()
                fig2, ax3 = plt.subplots(figsize=(7, 3))
                _apply_style(ax3)
                ax3.barh(jrnl.index[::-1], jrnl.values[::-1], color="#003B6F", alpha=0.75)
                for i, v in enumerate(jrnl.values[::-1]):
                    ax3.text(v + 0.1, i, str(int(v)), va="center", fontsize=7)
                ax3.set_xlabel("N° publicaciones", fontsize=8)
                ax3.set_title("Principales revistas de publicación", fontsize=9,
                              fontweight="bold", color="#003B6F")
                fig2.tight_layout(pad=0.5)
                imgs.append((_png(fig2), PAGE_W, PAGE_W * 3 / 7))
            return imgs

        # ── Seleccionar gráficos según tema ───────────────────────────────────
        _chart_fns = {
            "investigators": chart_investigators,
            "funding":        chart_funding,
            "human_capital":  chart_human_capital,
            "collaboration":  chart_collaboration,
            "quality":        chart_quality,
            "production":     chart_production,
        }
        _topic_labels = {
            "investigators": "Investigadores CCHEN",
            "funding":        "Financiamiento I+D (ANID)",
            "human_capital":  "Capital Humano I+D",
            "collaboration":  "Colaboración Internacional",
            "quality":        "Calidad y Acceso Abierto",
            "production":     "Producción Científica",
        }
        chart_imgs = []
        try:
            chart_imgs = _chart_fns[topic]()
        except Exception:
            pass

        # ── Construir story ────────────────────────────────────────────────────
        story = []
        story.append(Paragraph("CCHEN \u2014 Observatorio Tecnol\u00f3gico I+D+i+Tt", s_title))
        story.append(Paragraph(
            f"Informe generado: {_dtt.datetime.now().strftime('%d/%m/%Y %H:%M')} "
            f"\u00b7 Asistente IA (Groq / llama-3.3-70b-versatile)", s_meta))
        story.append(HRFlowable(width="100%", thickness=2, color=RED_RL, spaceAfter=10))

        if chart_imgs:
            story.append(Paragraph(f"Datos de contexto \u2014 {_topic_labels[topic]}:", s_h2))
            story.append(Spacer(1, 0.15*cm))
            for (ib, w, h) in chart_imgs:
                story.append(RLImage(ib, width=w, height=h))
                story.append(Spacer(1, 0.2*cm))
            story.append(HRFlowable(width="100%", thickness=1,
                                    color=colors.HexColor("#CCCCCC"), spaceAfter=8))

        story.append(Paragraph("<b>Consulta:</b>", s_h2))
        story.append(Paragraph(_esc(question), s_q))
        story.append(Spacer(1, 0.3*cm))
        story.append(Paragraph("<b>Respuesta del Asistente:</b>", s_h2))
        story.append(Spacer(1, 0.15*cm))

        for line in answer.split("\n"):
            line = line.rstrip()
            if not line:
                story.append(Spacer(1, 0.18*cm)); continue
            esc = _esc(line)
            if   line.startswith("### "):                 story.append(Paragraph(esc[4:], s_h2))
            elif line.startswith("## "):                  story.append(Paragraph(esc[3:], s_h2))
            elif line.startswith("# "):                   story.append(Paragraph(esc[2:], s_h2))
            elif line.startswith(("- ","* ","\u2022 ")):  story.append(Paragraph("\u2022 " + esc[2:], s_bullet))
            elif line.startswith(("  - ","  * ")):        story.append(Paragraph("  \u25e6 " + esc[4:], s_bullet))
            else:                                         story.append(Paragraph(esc, s_body))

        story.append(Spacer(1, 0.5*cm))
        story.append(HRFlowable(width="100%", thickness=1,
                                color=colors.HexColor("#CCCCCC"), spaceAfter=5))
        story.append(Paragraph(
            "Observatorio Tecnol\u00f3gico Virtual CCHEN \u00b7 "
            "Proyecto CORFO CCHEN 360 \u00b7 Beta v0.2", s_footer))

        doc.build(story)
        return buf.getvalue()
    except Exception:
        return None


def semaforo_badge(valor):
    colores = {"VERDE": ("#E8F5E9", GREEN, "🟢"), "AMARILLO": ("#FFF8E1", AMBER, "🟡"), "ROJO": ("#FDECEA", RED, "🔴")}
    bg, border, icon = colores.get(valor, ("#F5F5F5", "#999", "⚪"))
    return f"<span style='background:{bg};border:1px solid {border};border-radius:4px;padding:2px 8px;font-size:0.85rem'>{icon} {valor}</span>"


# ─── Sidebar ──────────────────────────────────────────────────────────────────

with st.sidebar:
    access = _access_context()
    available_sections = access.get("visible_sections") or _available_sections(access.get("app_mode"))
    if _LOGO_PATH.exists():
        st.image(str(_LOGO_PATH), width=160)
    else:
        st.markdown(
            "<div style='padding:8px 4px 4px'>"
            f"<div style='font-size:0.65rem;font-weight:600;letter-spacing:1.8px;"
            f"text-transform:uppercase;color:rgba(255,255,255,0.45);margin-bottom:2px'>CCHEN</div>"
            f"<div style='font-size:1.1rem;font-weight:700;color:#FFFFFF;line-height:1.3'>"
            f"Observatorio<br>Tecnológico</div>"
            f"</div>",
            unsafe_allow_html=True
        )
    st.markdown("---")
    seccion = st.radio(
        "Sección del observatorio",
        available_sections,
        label_visibility="collapsed",
    )
    st.markdown("---")
    with st.expander("Fuentes y actualización", expanded=False):
        if access.get("app_mode") != "public":
            source_status_df, source_runs_df = _build_source_refresh_status()
            if not source_status_df.empty:
                enabled_df = source_status_df[source_status_df["enabled"]]
                overdue_count = int(enabled_df["is_overdue"].sum()) if not enabled_df.empty else 0
                failed_count = int(enabled_df["last_run_status"].astype(str).str.lower().eq("failed").sum()) if not enabled_df.empty else 0
                c_status_1, c_status_2, c_status_3 = st.columns(3)
                c_status_1.metric("Fuentes habilitadas", f"{len(enabled_df):,}")
                c_status_2.metric("Vencidas", f"{overdue_count:,}")
                c_status_3.metric("Últ. fallo", f"{failed_count:,}")
                st.caption(
                    "Estado operativo del runner canónico de refresh. "
                    "Las fuentes manuales siguen registradas pero fuera del scheduler."
                )
                st.dataframe(
                    source_status_df[
                        [
                            "source_name",
                            "update_frequency",
                            "last_updated_label",
                            "next_update_due_label",
                            "last_run_status",
                        ]
                    ].rename(
                        columns={
                            "source_name": "Fuente",
                            "update_frequency": "Frecuencia",
                            "last_updated_label": "Última actualización",
                            "next_update_due_label": "Próxima esperada",
                            "last_run_status": "Estado",
                        }
                    ),
                    width="stretch",
                    height=260,
                    hide_index=True,
                )
                if not source_runs_df.empty:
                    st.caption("Últimas corridas registradas")
                    st.dataframe(
                        source_runs_df[
                            ["source_key", "status", "records_written", "finished_at_label", "trigger_kind"]
                        ]
                        .head(6)
                        .rename(
                            columns={
                                "source_key": "Source key",
                                "status": "Estado",
                                "records_written": "Registros",
                                "finished_at_label": "Finalizó",
                                "trigger_kind": "Trigger",
                            }
                        ),
                        width="stretch",
                        height=220,
                        hide_index=True,
                    )
                st.divider()
        if _backend.get("source_mode") != "local":
            st.caption(
                "Modo de datos no-local activo: estas fechas corresponden a snapshots/archivos locales "
                "de respaldo, no necesariamente al último sync en Supabase."
            )
        for fuente, fecha in _timestamps.items():
            _icon = "·" if fecha != "—" else "—"
            st.caption(f"{_icon} **{fuente}**: {fecha}")
        st.caption("Fecha de última modificación del archivo.")
        if st.button("Inspector datasets", key="sidebar_open_dataset_inspector", width="stretch"):
            open_dataset_inspector()
    with st.expander("Acceso y permisos", expanded=False):
        if access.get("app_mode") == "public":
            st.caption("Portal público del observatorio 3 en 1.")
            st.caption("Esta superficie no carga datasets sensibles ni requiere autenticación para navegar.")
            st.caption("Las vistas internas y operativas permanecen en la superficie `obs-int`.")
        elif access.get("auth_mode") == "internal":
            if access["is_logged_in"]:
                st.success(f"Sesión activa: {access['name']}")
                if access.get("username"):
                    st.caption(f"Usuario: {access['username']}")
                if access.get("role"):
                    st.caption(f"Rol: {access['role']}")
                if access["can_view_sensitive"]:
                    st.caption("Acceso a datasets internos habilitado.")
                else:
                    st.warning("Tu usuario no tiene acceso a vistas sensibles.")
                if st.button("Cerrar sesión", key="sidebar_logout_internal", width="stretch"):
                    _internal_auth_logout()
                    st.rerun()
            else:
                st.caption("El observatorio beta requiere autenticación interna.")
        elif not access["auth_supported"]:
            st.caption("Tu versión de Streamlit no expone `st.login()` / `st.user`.")
        elif not access["auth_enabled"]:
            st.caption("OIDC no configurado. El dashboard opera en modo local abierto.")
            st.caption("Configura `Dashboard/.streamlit/secrets.toml` para activar login.")
        else:
            if access["is_logged_in"]:
                st.success(f"Sesión activa: {access['name']}")
                if access["email"]:
                    st.caption(access["email"])
                if access["allowlist"] and not access["is_allowlisted"]:
                    st.warning("Tu cuenta está autenticada, pero no está autorizada para vistas sensibles.")
                elif access["can_view_sensitive"]:
                    st.caption("Acceso sensible habilitado.")
                if st.button("Cerrar sesión", key="sidebar_logout", width="stretch"):
                    st.logout()
            else:
                st.caption("Inicia sesión para habilitar vistas sensibles y alinear el acceso con RLS.")
                if st.button("Iniciar sesión", key="sidebar_login", width="stretch"):
                    st.login()
    st.markdown("---")
    if access.get("app_mode") == "public":
        st.caption("Portal público v0.3  ·  Observatorio CCHEN 3 en 1")
    else:
        st.caption("Beta interna v0.2  ·  CORFO CCHEN 360")


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION ROUTING
# ══════════════════════════════════════════════════════════════════════════════

_ctx = dict(
    _build_section_ctx(seccion, _APP_ACCESS["can_view_sensitive"])
)
_ctx["_section_name"] = seccion
_ACTIVE_SECTION_CTX = _ctx

_SECTION_MAP = {
    "Plataforma Institucional":  plataforma_institucional.render,
    "Panel de Indicadores":       panel_indicadores.render,
    "Producción Científica":      produccion_cientifica.render,
    "Redes y Colaboración":       redes_colaboracion.render,
    "Vigilancia Tecnológica":     vigilancia_tecnologica.render,
    "Financiamiento I+D":         financiamiento_id.render,
    "Convocatorias y Matching":   convocatorias_matching.render,
    "Transferencia y Portafolio": transferencia_portafolio.render,
    "Modelo y Gobernanza":        modelo_gobernanza.render,
    "Formación de Capacidades":   formacion_capacidades.render,
    "Asistente I+D":              asistente_id.render,
    "Grafo de Citas":             grafo_citas.render,
}

_render_fn = _SECTION_MAP.get(seccion)
if _render_fn is not None:
    _render_fn(_ctx)
else:
    st.error(f"Sección desconocida: {seccion!r}")
