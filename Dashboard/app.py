"""
CCHEN Observatorio Tecnológico — Beta interna v0.2
Vigilancia e Inteligencia I+D+i+Tt · Comisión Chilena de Energía Nuclear
"""
import json
import os
import hashlib
import ast
import re
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
load_ror_registry = _resolve_loader("load_ror_registry", _csv_loader("Institutional", "cchen_institution_registry.csv"))
load_ror_pending_review = _resolve_loader("load_ror_pending_review", _csv_loader("Institutional", "ror_pending_review.csv"))
load_funding_complementario = _resolve_loader("load_funding_complementario", _csv_loader("Funding", "cchen_funding_complementario.csv"))
load_iaea_tc = _resolve_loader("load_iaea_tc", _csv_loader("Funding", "cchen_iaea_tc.csv"))
load_perfiles_institucionales = _resolve_loader("load_perfiles_institucionales", _csv_loader("Vigilancia", "perfiles_institucionales_cchen.csv"))
load_matching_institucional = _resolve_loader("load_matching_institucional", _csv_loader("Vigilancia", "convocatorias_matching_institucional.csv"))
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

@st.cache_data
def get_data():
    return dict(
        pub       = load_publications(),
        pub_enr   = load_publications_enriched(),
        auth      = load_authorships(),
        anid      = load_anid(),
        ch        = load_capital_humano(),
        ch_ej     = load_ch_resumen_ejecutivo(),
        ch_adv    = load_ch_analisis_avanzado(),
        ch_cumpl  = load_ch_cumplimiento_centros(),
        ch_trans  = load_ch_transiciones(),
        ch_tipo_a = load_ch_participacion_tipo_anio(),
        dian      = load_dian_publications(),
        crossref    = load_crossref_enriched(),
        concepts    = load_concepts(),
        datacite    = load_datacite_outputs(),
        openaire    = load_openaire_outputs(),
        grants_oa   = load_grants_openalex(),
        orcid       = load_orcid_researchers(),
        ror_registry = load_ror_registry(),
        ror_pending_review = load_ror_pending_review(),
        funding_plus = load_funding_complementario(),
        iaea_tc     = load_iaea_tc(),
        perfiles_inst = load_perfiles_institucionales(),
        matching_inst = load_matching_institucional(),
        entity_personas = load_entity_registry_personas(),
        entity_projects = load_entity_registry_proyectos(),
        entity_convocatorias = load_entity_registry_convocatorias(),
        entity_links = load_entity_links(),
        pub_full    = load_publications_with_concepts(),
        convenios   = load_convenios_nacionales(),
        acuerdos    = load_acuerdos_internacionales(),
        unpaywall   = load_unpaywall_oa(),
        citation_graph = load_citation_graph(),
        citing_papers  = load_citing_papers(),
        altmetric      = load_altmetric(),
        europmc        = load_europmc(),
        arxiv_monitor       = load_arxiv_monitor(),
        news_monitor        = load_news_monitor(),
        iaea_inis           = load_iaea_inis(),
        bertopic_topics     = load_bertopic_topics(),
        bertopic_topic_info = load_bertopic_topic_info(),
    )

D = get_data()
pub, pub_enr, auth = D["pub"], D["pub_enr"], D["auth"]
anid = D["anid"]
ch, ch_ej, ch_adv = D["ch"], D["ch_ej"], D["ch_adv"]
ch_cumpl, ch_trans, ch_tipo_a = D["ch_cumpl"], D["ch_trans"], D["ch_tipo_a"]
dian = D["dian"]
crossref     = D["crossref"]
concepts     = D["concepts"]
datacite     = D["datacite"]
openaire     = D["openaire"]
grants_oa    = D["grants_oa"]
orcid        = D["orcid"]
ror_registry = D["ror_registry"]
ror_pending_review = D["ror_pending_review"]
funding_plus = D["funding_plus"]
iaea_tc      = D["iaea_tc"]
perfiles_inst = D["perfiles_inst"]
matching_inst = D["matching_inst"]
entity_personas = D["entity_personas"]
entity_projects = D["entity_projects"]
entity_convocatorias = D["entity_convocatorias"]
entity_links = D["entity_links"]
pub_full     = D.get("pub_full", pub)
convenios    = D["convenios"]
acuerdos     = D["acuerdos"]
unpaywall    = D["unpaywall"]
citation_graph = D["citation_graph"]
citing_papers  = D["citing_papers"]
altmetric      = D["altmetric"]
europmc        = D["europmc"]
arxiv_monitor       = D["arxiv_monitor"]
news_monitor        = D["news_monitor"]
iaea_inis           = D["iaea_inis"]
bertopic_topics     = D["bertopic_topics"]
bertopic_topic_info = D["bertopic_topic_info"]

@st.cache_data
def get_patents():
    return load_patents()

patents = get_patents()
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


def _get_secret_block(name: str) -> dict:
    try:
        block = st.secrets.get(name, {})
        return dict(block) if block else {}
    except Exception:
        return {}


def _streamlit_auth_supported() -> bool:
    return all(hasattr(st, attr) for attr in ("login", "logout", "user"))


def _auth_enabled() -> bool:
    return _streamlit_auth_supported() and bool(_get_secret_block("auth"))


def _access_context() -> dict:
    user = getattr(st, "user", None) if _streamlit_auth_supported() else None
    is_logged_in = bool(getattr(user, "is_logged_in", False)) if user is not None else False
    email = (getattr(user, "email", "") or "").strip().lower() if user is not None else ""
    name = (getattr(user, "name", "") or email or "usuario") if user is not None else "usuario"

    observatorio_cfg = _get_secret_block("observatorio")
    allowlist = [
        str(item).strip().lower()
        for item in observatorio_cfg.get("sensitive_access_emails", [])
        if str(item).strip()
    ]
    is_allowlisted = (not allowlist) or (email in allowlist)
    can_view_sensitive = (not _auth_enabled()) or (is_logged_in and is_allowlisted)

    return {
        "auth_enabled": _auth_enabled(),
        "auth_supported": _streamlit_auth_supported(),
        "is_logged_in": is_logged_in,
        "email": email,
        "name": name,
        "allowlist": allowlist,
        "is_allowlisted": is_allowlisted,
        "can_view_sensitive": can_view_sensitive,
    }


def _dataset_catalog() -> dict:
    return {
        "Publicaciones OpenAlex": {
            "df": pub,
            "source": "Data/Publications/cchen_openalex_works.csv",
            "table_name": "publications",
            "sensitive": False,
        },
        "Publicaciones enriquecidas + SJR": {
            "df": pub_enr,
            "source": "Data/Publications/cchen_publications_with_quartile_sjr.csv",
            "table_name": "publications_enriched",
            "sensitive": False,
        },
        "Autorías OpenAlex": {
            "df": auth,
            "source": "Data/Publications/cchen_authorships_enriched.csv",
            "table_name": "authorships",
            "sensitive": False,
        },
        "ANID": {
            "df": anid,
            "source": "Data/ANID/RepositorioAnid_con_monto.csv",
            "table_name": "anid_projects",
            "sensitive": False,
        },
        "Capital Humano": {
            "df": ch,
            "source": "Data/Capital humano CCHEN/salida_dataset_maestro/dataset_maestro_limpio.csv",
            "table_name": "capital_humano",
            "sensitive": True,
        },
        "CrossRef": {
            "df": crossref,
            "source": "Data/Publications/cchen_crossref_enriched.csv",
            "table_name": "crossref_data",
            "sensitive": False,
        },
        "Conceptos OpenAlex": {
            "df": concepts,
            "source": "Data/Publications/cchen_openalex_concepts.csv",
            "table_name": "concepts",
            "sensitive": False,
        },
        "DataCite outputs": {
            "df": datacite,
            "source": "Data/ResearchOutputs/cchen_datacite_outputs.csv",
            "table_name": "datacite_outputs",
            "sensitive": False,
        },
        "OpenAIRE outputs": {
            "df": openaire,
            "source": "Data/ResearchOutputs/cchen_openaire_outputs.csv",
            "table_name": "openaire_outputs",
            "sensitive": False,
        },
        "Investigadores ORCID": {
            "df": orcid,
            "source": "Data/Researchers/cchen_researchers_orcid.csv",
            "table_name": "researchers_orcid",
            "sensitive": False,
        },
        "Registro institucional ROR": {
            "df": ror_registry,
            "source": "Data/Institutional/cchen_institution_registry.csv",
            "table_name": "institution_registry",
            "sensitive": False,
        },
        "Cola revisión ROR": {
            "df": ror_pending_review,
            "source": "Data/Institutional/ror_pending_review.csv",
            "table_name": "institution_registry_pending_review",
            "sensitive": False,
        },
        "Financiamiento complementario": {
            "df": funding_plus,
            "source": "Data/Funding/cchen_funding_complementario.csv",
            "table_name": "funding_complementario",
            "sensitive": True,
        },
        "Perfiles institucionales": {
            "df": perfiles_inst,
            "source": "Data/Vigilancia/perfiles_institucionales_cchen.csv",
            "table_name": "perfiles_institucionales",
            "sensitive": False,
        },
        "Matching institucional": {
            "df": matching_inst,
            "source": "Data/Vigilancia/convocatorias_matching_institucional.csv",
            "table_name": "convocatorias_matching_institucional",
            "sensitive": False,
        },
        "Entidades persona": {
            "df": entity_personas,
            "source": "Data/Gobernanza/entity_registry_personas.csv",
            "table_name": "entity_registry_personas",
            "sensitive": True,
        },
        "Entidades proyecto": {
            "df": entity_projects,
            "source": "Data/Gobernanza/entity_registry_proyectos.csv",
            "table_name": "entity_registry_proyectos",
            "sensitive": False,
        },
        "Entidades convocatoria": {
            "df": entity_convocatorias,
            "source": "Data/Gobernanza/entity_registry_convocatorias.csv",
            "table_name": "entity_registry_convocatorias",
            "sensitive": False,
        },
        "Enlaces entre entidades": {
            "df": entity_links,
            "source": "Data/Gobernanza/entity_links.csv",
            "table_name": "entity_links",
            "sensitive": True,
        },
        "Convenios nacionales": {
            "df": convenios,
            "source": "Data/Institutional/clean_Convenios_suscritos_por_la_Com.csv",
            "table_name": "convenios_nacionales",
            "sensitive": False,
        },
        "Acuerdos internacionales": {
            "df": acuerdos,
            "source": "Data/Institutional/clean_Acuerdos_e_instrumentos_intern.csv",
            "table_name": "acuerdos_internacionales",
            "sensitive": False,
        },
        "Unpaywall OA enrichment": {
            "df": unpaywall,
            "source": "Data/Publications/cchen_unpaywall_oa.csv",
            "table_name": "unpaywall_oa",
            "sensitive": False,
        },
        "Monitor IAEA INIS": {
            "df": load_iaea_inis(),
            "source": "Data/Vigilancia/iaea_inis_monitor.csv",
            "table_name": "iaea_inis_monitor",
            "sensitive": False,
        },
    }


def _describe_dataset_read_source(meta: dict) -> tuple[str, str]:
    table_name = str(meta.get("table_name") or "").strip()
    status = get_table_load_status().get(table_name, {}) if table_name else {}
    source = status.get("source", "")
    detail = status.get("detail", "")

    if source == "supabase_public":
        return "Supabase pública", table_name
    if source == "local_fallback":
        return "Fallback local", detail or meta.get("source", "CSV local")
    if source == "local_only":
        if table_name and table_name in _PUBLIC_TABLE_CONFIG:
            return "Local", detail or meta.get("source", "CSV local")
        return "Solo local / autenticado", detail or meta.get("source", "CSV local")
    if table_name and table_name in _PUBLIC_TABLE_CONFIG:
        return "Remoto habilitado", table_name
    return "Solo local / autenticado", meta.get("source", "CSV local")


@_dialog("Inspector de datasets", width="large")
def open_dataset_inspector():
    access = _access_context()
    catalog = _dataset_catalog()
    dataset_name = st.selectbox("Dataset", list(catalog.keys()), index=0)
    meta = catalog[dataset_name]
    df = meta["df"]
    read_source, read_detail = _describe_dataset_read_source(meta)

    st.caption(f"Fuente: `{meta['source']}`")
    st.caption(f"Lectura efectiva: `{read_source}` · `{read_detail}`")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Filas", f"{len(df):,}")
    c2.metric("Columnas", f"{len(df.columns):,}" if hasattr(df, "columns") else "—")
    c3.metric("Sensibilidad", "Restringido" if meta["sensitive"] else "Público")
    c4.metric("Origen", read_source)

    if meta["sensitive"] and not access["can_view_sensitive"]:
        st.warning(
            "Este dataset está marcado como sensible. Inicia sesión con un usuario autorizado "
            "para ver muestras o columnas detalladas."
        )
        return

    sample_size = st.slider("Filas de muestra", min_value=5, max_value=100, value=20, step=5)
    preview = df.head(sample_size).copy()
    st.dataframe(preview, use_container_width=True, height=420)
    st.download_button(
        "Exportar muestra CSV",
        make_csv(preview),
        file_name=f"preview_{dataset_name.lower().replace(' ', '_')}.csv",
        mime="text/csv",
    )


@_fragment
def render_operational_strip():
    access = _access_context()
    engine_label = _backend["engine"].upper()
    # Abreviar para que no se trunque en pantallas pequeñas
    engine_short = engine_label[:6] if len(engine_label) > 6 else engine_label
    acceso_short  = "Sí" if access["can_view_sensitive"] else "No"
    c1, c2, c3, c4, c5 = st.columns([1.1, 1.1, 1.0, 0.9, 2.2])
    c1.metric("Motor datos", engine_short)
    c2.metric("Fuente", _backend.get("source_mode", "auto"))
    c3.metric("Datasets", f"{len(_dataset_catalog())}")
    c4.metric("Acceso sens.", acceso_short)
    with c5:
        st.caption(_backend["detail"])
        b1, b2 = st.columns(2)
        with b1:
            if st.button("🔍 Datasets", key="btn_open_dataset_inspector", use_container_width=True):
                open_dataset_inspector()
        with b2:
            if st.button("♻ Limpiar caché", key="btn_clear_dashboard_cache", use_container_width=True):
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
    seccion = st.radio("Sección del observatorio", [
        "Panel de Indicadores",
        "Producción Científica",
        "Redes y Colaboración",
        "Vigilancia Tecnológica",
        "Financiamiento I+D",
        "Convocatorias y Matching",
        "Transferencia y Portafolio",
        "Modelo y Gobernanza",
        "Formación de Capacidades",
        "Asistente I+D",
        "Grafo de Citas",
    ], label_visibility="collapsed")
    st.markdown("---")
    with st.expander("Fuentes y actualización", expanded=False):
        if _backend.get("source_mode") != "local":
            st.caption(
                "Modo de datos no-local activo: estas fechas corresponden a snapshots/archivos locales "
                "de respaldo, no necesariamente al último sync en Supabase."
            )
        for fuente, fecha in _timestamps.items():
            _icon = "·" if fecha != "—" else "—"
            st.caption(f"{_icon} **{fuente}**: {fecha}")
        st.caption("Fecha de última modificación del archivo.")
        if st.button("Inspector datasets", key="sidebar_open_dataset_inspector", use_container_width=True):
            open_dataset_inspector()
    with st.expander("Acceso y permisos", expanded=False):
        if not access["auth_supported"]:
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
                if st.button("Cerrar sesión", key="sidebar_logout", use_container_width=True):
                    st.logout()
            else:
                st.caption("Inicia sesión para habilitar vistas sensibles y alinear el acceso con RLS.")
                if st.button("Iniciar sesión", key="sidebar_login", use_container_width=True):
                    st.login()
    st.markdown("---")
    st.caption("Beta v0.2  ·  CORFO CCHEN 360")


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION ROUTING
# ══════════════════════════════════════════════════════════════════════════════

_ctx = dict(
    pub=pub, pub_enr=pub_enr, auth=auth,
    anid=anid,
    ch=ch, ch_ej=ch_ej, ch_adv=ch_adv,
    ch_cumpl=ch_cumpl, ch_trans=ch_trans, ch_tipo_a=ch_tipo_a,
    dian=dian,
    crossref=crossref,
    concepts=concepts,
    datacite=datacite,
    openaire=openaire,
    grants_oa=grants_oa,
    orcid=orcid,
    ror_registry=ror_registry,
    ror_pending_review=ror_pending_review,
    funding_plus=funding_plus,
    iaea_tc=iaea_tc,
    perfiles_inst=perfiles_inst,
    matching_inst=matching_inst,
    entity_personas=entity_personas,
    entity_projects=entity_projects,
    entity_convocatorias=entity_convocatorias,
    entity_links=entity_links,
    pub_full=pub_full,
    convenios=convenios,
    acuerdos=acuerdos,
    unpaywall=unpaywall,
    citation_graph=citation_graph,
    citing_papers=citing_papers,
    altmetric=altmetric,
    europmc=europmc,
    arxiv_monitor=arxiv_monitor,
    news_monitor=news_monitor,
    iaea_inis=iaea_inis,
    bertopic_topics=bertopic_topics,
    bertopic_topic_info=bertopic_topic_info,
    patents=patents,
    render_operational_strip=render_operational_strip,
    open_dataset_inspector=open_dataset_inspector,
)

_SECTION_MAP = {
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

# ── LEGACY inline routing kept below for fallback reference ──────────────────
# The blocks below are unreachable when _SECTION_MAP dispatch succeeds above.
# They are preserved here to allow easy rollback if needed.

if False and seccion == "Panel de Indicadores":
    st.title("CCHEN — Observatorio Tecnológico I+D+i+Tt")
    st.markdown("**Panel consolidado de indicadores de Vigilancia Tecnológica** · Beta interna")
    st.divider()
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
        st.plotly_chart(fig, use_container_width=True)

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
        st.plotly_chart(fig2, use_container_width=True)

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
        st.plotly_chart(fig3, use_container_width=True)

    with col4:
        sec("Formación capital humano por tipo (2022–2025)")
        tc = ch["tipo_norm"].value_counts().reset_index()
        tc.columns = ["Tipo","N"]
        fig4 = px.bar(tc.sort_values("N"), x="N", y="Tipo", orientation="h",
                      color="Tipo", color_discrete_sequence=PALETTE, text="N", height=310)
        fig4.update_layout(showlegend=False, margin=dict(t=10,b=10))
        st.plotly_chart(fig4, use_container_width=True)

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


# ══════════════════════════════════════════════════════════════════════════════
#  PRODUCCIÓN CIENTÍFICA
# ══════════════════════════════════════════════════════════════════════════════

elif False and seccion == "Producción Científica":
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
            yr_range = st.slider("Período", 1990, 2026, (2000, 2025))
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
    kpi_row(
        kpi("% Q1+Q2", f"{pct_q}%", f"{n_q1q2} de {n_q_tot} con cuartil"),
        kpi("% Acceso Abierto", f"{100*df['is_oa'].mean():.0f}%"),
        kpi("% Collab. Intl.", f"{pct_collab}%", "papers enriquecidos"),
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
        collab_df = df_enr[["has_international_collab","has_outside_cchen_collab"]].copy()
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
        # Unir con citas de pub
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
        # Resaltar Chile
        fig_map.add_scattergeo(
            locations=["CHL"], locationmode="ISO-3",
            marker=dict(size=8, color=RED, symbol="star"),
            hoverinfo="text", text=["CCHEN (Chile)"], showlegend=False,
        )
        st.plotly_chart(fig_map, use_container_width=True)
        # Top 10 países como complemento
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
        # openalex_id ya es URL completa: "https://openalex.org/W..."
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

    # Unir con Unpaywall para agregar link directo al PDF
    if not unpaywall.empty and "doi" in unpaywall.columns and "oa_pdf_url" in unpaywall.columns:
        _uw_pdf = unpaywall[["doi","oa_pdf_url"]].copy()
        _uw_pdf = _uw_pdf[_uw_pdf["oa_pdf_url"].fillna("").str.startswith("http")]
        df_show = df_show.merge(_uw_pdf, on="doi", how="left")
        df_show["PDF"] = df_show["oa_pdf_url"].where(df_show["oa_pdf_url"].fillna("").ne(""), None)
        df_show = df_show.drop(columns=["oa_pdf_url"])
    else:
        df_show["PDF"] = None

    df_show = df_show.drop(columns=["doi"]).rename(columns={
        "year":"Año","title":"Título","type":"Tipo","source":"Journal",
        "cited_by_count":"Citas","is_oa":"OA",
    }).sort_values("Año", ascending=False)

    st.dataframe(df_show, use_container_width=True, height=400,
                 column_config={
                     "OA": st.column_config.CheckboxColumn("OA"),
                     "Enlace": st.column_config.LinkColumn("Enlace", display_text="🔗"),
                     "PDF": st.column_config.LinkColumn("PDF", display_text="📄"),
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

        # Layout circular
        _n = len(_top_nodes)
        _pos = {nd: (math.cos(2*math.pi*i/_n), math.sin(2*math.pi*i/_n))
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
            marker=dict(size=_sz, color=BLUE, line=dict(width=1.5, color="white"),
                        opacity=0.9),
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
            # Top-level concepts (level 0-1)
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

            # Level 2 breakdown
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

            # Tabla
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

        # Investigadores CCHEN únicos, ordenados por nº papers
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

        # H-index
        _cites_sorted = sorted(_inv_papers["cited_by_count"].dropna().astype(int).tolist(), reverse=True)
        _inv_h = sum(1 for i, c in enumerate(_cites_sorted, 1) if c >= i)
        _inv_total_cites = int(_inv_papers["cited_by_count"].sum())
        _inv_n = len(_inv_papers)
        _inv_yr_min = int(_inv_papers["year"].min()) if _inv_papers["year"].notna().any() else "?"
        _inv_yr_max = int(_inv_papers["year"].max()) if _inv_papers["year"].notna().any() else "?"
        _inv_oa_pct = 100 * _inv_papers["is_oa"].sum() / _inv_n if _inv_n > 0 else 0

        # KPIs
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

        # Top colaboradores
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


# ══════════════════════════════════════════════════════════════════════════════
#  REDES Y COLABORACIÓN
# ══════════════════════════════════════════════════════════════════════════════

elif False and seccion == "Redes y Colaboración":
    st.title("Redes de Colaboración Científica")
    st.caption("Fuente: OpenAlex authorships · 7.971 autorías · Análisis de redes e impacto bibliométrico")
    st.divider()

    with st.expander("Filtros", expanded=True):
        rc1, rc2 = st.columns(2)
        with rc1:
            yr_rc = st.slider("Período", 1990, 2026, (2005, 2025), key="rc_yr")
        with rc2:
            top_n_net = st.slider("Top N instituciones en la red", 10, 60, 30, key="rc_topn")

    # Enriquecer authorships con año del paper
    _auth_yr = auth.merge(
        pub[["openalex_id", "year"]].rename(columns={"openalex_id": "work_id"}),
        on="work_id", how="left"
    )
    _auth_rc = _auth_yr[_auth_yr["year"].between(*yr_rc)].copy()

    # ── KPIs ──────────────────────────────────────────────────────────────────
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

        # Aristas
        edge_x, edge_y = [], []
        for (u, v) in G_sub.edges():
            x0, y0 = pos[u]; x1, y1 = pos[v]
            edge_x += [x0, x1, None]; edge_y += [y0, y1, None]
        edge_trace = go.Scatter(
            x=edge_x, y=edge_y, mode="lines",
            line=dict(width=0.6, color="#CCCCCC"), hoverinfo="none",
        )

        # Nodos
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

        # Top 15 instituciones por conexiones
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

        # Construir pares de co-autores por paper
        _au_pairs = _auth_rc[["work_id", "author_id", "author_name", "is_cchen_affiliation"]].dropna(
            subset=["author_id", "author_name"]
        )
        # Índice cchen por author_id
        _cchen_ids = set(
            _au_pairs.loc[_au_pairs["is_cchen_affiliation"] == True, "author_id"]
        )

        _paper_authors = _au_pairs.groupby("work_id").apply(
            lambda df: list(zip(df["author_id"], df["author_name"]))
        ).reset_index(name="authors_list")

        _coauth_edges: dict[tuple, int] = {}
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
        _id_to_name: dict[str, str] = {}
        for (a_id, b_id), meta in _coauth_edges.items():
            G_au.add_edge(a_id, b_id, weight=meta["weight"])
            _id_to_name[a_id] = meta["name_a"]
            _id_to_name[b_id] = meta["name_b"]

        # Subgrafo con top N autores por grado
        _top_au_nodes = sorted(G_au.degree(), key=lambda x: -x[1])[:_top_n_authors]
        _top_au_ids   = [n for n, _ in _top_au_nodes]
        G_au_sub = G_au.subgraph(_top_au_ids)
        pos_au   = _nx.spring_layout(G_au_sub, seed=7, k=2.2 / (_top_n_authors ** 0.5))

        # Calcular número de papers por autor para tamaño del nodo
        _au_paper_count = _au_pairs.groupby("author_id")["work_id"].nunique().to_dict()

        # Aristas — grosor proporcional al peso (co-publicaciones)
        _ae_x, _ae_y, _ae_w = [], [], []
        for u, v, data in G_au_sub.edges(data=True):
            x0, y0 = pos_au[u]; x1, y1 = pos_au[v]
            _ae_x += [x0, x1, None]
            _ae_y += [y0, y1, None]
        _edge_au = go.Scatter(
            x=_ae_x, y=_ae_y, mode="lines",
            line=dict(width=0.8, color="rgba(150,150,150,0.4)"),
            hoverinfo="none",
        )

        # Nodos
        _an_x     = [pos_au[n][0] for n in G_au_sub.nodes()]
        _an_y     = [pos_au[n][1] for n in G_au_sub.nodes()]
        _an_deg   = [G_au_sub.degree(n) for n in G_au_sub.nodes()]
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

        # Tabla top 20 autores más conectados
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


# ══════════════════════════════════════════════════════════════════════════════
#  VIGILANCIA TECNOLÓGICA
# ══════════════════════════════════════════════════════════════════════════════

elif False and seccion == "Vigilancia Tecnológica":
    import datetime as _dtlib

    st.title("Vigilancia Tecnológica CCHEN")
    st.caption("Actividad publicadora institucional · Monitoreo de tendencias · Temas de investigación")
    st.divider()

    _VT_BASE = BASE / "Publications"
    _VT_VIG  = BASE / "Vigilancia"

    _vt_tabs = st.tabs(["📅 Publicaciones CCHEN", "📰 En la prensa", "📋 Boletín semanal", "📡 Monitor arXiv", "⚛️ Monitor IAEA INIS", "🔬 Temas de investigación"])

    # ── TAB 1: Publicaciones CCHEN ───────────────────────────────────────────
    with _vt_tabs[0]:
        _oa_path  = _VT_BASE / "cchen_openalex_works.csv"
        _we_path  = _VT_BASE / "cchen_works_enriched.csv"
        _abs_path = _VT_BASE / "cchen_abstracts_merged.csv"

        if not _oa_path.exists():
            st.info("No se encontró cchen_openalex_works.csv en Data/Publications.")
        else:
            _pub = pd.read_csv(_oa_path, low_memory=False)
            if _we_path.exists():
                _we = pd.read_csv(_we_path, low_memory=False)
                _pub = _pub.merge(
                    _we[["work_id", "publication_date"]].rename(columns={"work_id": "openalex_id"}),
                    on="openalex_id", how="left"
                )
            else:
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
        _news_path = _VT_VIG / "news_monitor.csv"
        if not _news_path.exists():
            st.info("Ejecuta `python3 Scripts/news_monitor.py` para obtener noticias.")
        else:
            _news = pd.read_csv(_news_path)
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
                                     plot_bgcolor="#F8FAFC", margin=dict(t=5,b=5,l=5,r=30))
                st.plotly_chart(fig_tc, use_container_width=True)

            with _gc2:
                sec("Principales medios")
                _sc = _news["source_name"].value_counts().head(8).reset_index()
                _sc.columns = ["Medio", "N"]
                fig_sc = px.bar(_sc.sort_values("N"), x="N", y="Medio", orientation="h",
                                color_discrete_sequence=[BLUE], text="N", height=220)
                fig_sc.update_traces(textposition="outside")
                fig_sc.update_layout(yaxis_title="", plot_bgcolor="#F8FAFC",
                                     margin=dict(t=5,b=5,l=5,r=30))
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
                fig_ts.update_layout(plot_bgcolor="#F8FAFC", margin=dict(t=5,b=5))
                st.plotly_chart(fig_ts, use_container_width=True)

            st.divider()

            # ── Lista de noticias ──────────────────────────────────────────
            sec(f"Noticias ({len(_nshow)})")
            _TOPIC_BADGE = {
                "CIENCIA": "🔬", "POLÍTICA": "🏛",
                "INSTITUCIONAL": "🏢", "GENERAL": "📰"
            }
            for _, _nrow in _nshow.head(50).iterrows():
                _badge  = _TOPIC_BADGE.get(_nrow.get("topic_flag",""), "📰")
                _nt     = _clean_news_title(_nrow.get("title_clean", ""), _nrow.get("source_name", ""))
                _nsrc   = _clean_html_text(_nrow.get("source_name",""))
                _ndate  = _nrow["published_dt"].strftime("%d %b %Y") \
                          if pd.notna(_nrow.get("published_dt")) else ""
                _nsnip  = _clean_news_snippet(_nrow.get("snippet_clean",""), _nt)
                _nlink  = str(_nrow.get("link",""))

                with st.expander(f"{_badge} **{_nsrc}** · {_nt[:96]}"):
                    st.caption(
                        f"📅 {_ndate}  ·  🏷 {_clean_html_text(_nrow.get('topic_flag',''))}  ·  "
                        f"🔍 {_clean_html_text(_nrow.get('query_label',''))}"
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
                                   help="Cuántas semanas hacia atrás cubrir")
        with _bc2:
            _bol_npub = st.slider("N° publicaciones CCHEN recientes", 3, 10, 5)

        if st.button("⚡ Generar boletín ahora", type="primary", use_container_width=True):
            with st.spinner("Generando boletín..."):
                import subprocess, sys
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
        _arxiv_path = _VT_VIG / "arxiv_monitor.csv"
        if not _arxiv_path.exists():
            st.info(
                "Aún no hay datos de monitoreo arXiv. "
                "Ejecuta `python3 Scripts/arxiv_monitor.py` para la primera captura."
            )
        else:
            _arxiv = pd.read_csv(_arxiv_path)
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
                _area_c.columns = ["Área","N"]
                fig_area = px.bar(_area_c, x="N", y="Área", orientation="h",
                                  color_discrete_sequence=[BLUE], text="N", height=280)
                fig_area.update_traces(textposition="outside")
                fig_area.update_layout(yaxis_title="", plot_bgcolor="#F8FAFC",
                                       margin=dict(t=5,b=5,l=5,r=30))
                st.plotly_chart(fig_area, use_container_width=True)

            with vc2:
                sec("Relevancia para CCHEN")
                _rel_c = _arxiv["relevance_flag"].value_counts().reset_index()
                _rel_c.columns = ["Relevancia","N"]
                _colors_rel = {"ALTA": RED, "MEDIA": AMBER, "BAJA": GREEN}
                fig_rel = px.pie(_rel_c, names="Relevancia", values="N",
                                 color="Relevancia",
                                 color_discrete_map=_colors_rel, height=280)
                fig_rel.update_traces(textposition="inside", textinfo="percent+label")
                fig_rel.update_layout(margin=dict(t=5,b=5))
                st.plotly_chart(fig_rel, use_container_width=True)

            st.divider()
            sec("Papers de alta relevancia")
            _high = _arxiv[_arxiv["relevance_flag"] == "ALTA"].sort_values("fetched_at", ascending=False)
            if _high.empty:
                st.info("No hay papers de alta relevancia en el registro actual.")
            else:
                for _, row in _high.head(20).iterrows():
                    with st.expander(f"[{row['feed_area']}] {row['title'][:90]}"):
                        st.markdown(f"**Área:** {row['feed_area']}  ·  **Fecha:** {row.get('fetched_at','')}")
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
        _inis_df = load_iaea_inis()
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
                kpi("Alta relevancia", f"{(_inis_df.get('relevance_flag','')=='ALTA').sum()}",
                    "match con keywords CCHEN"),
                kpi("Áreas cubiertas", f"{_inis_df['subject_area'].nunique() if 'subject_area' in _inis_df.columns else '—'}"),
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
                    with st.expander(f"[{_irow.get('subject_area','')}] {str(_irow.get('title',''))[:90]}"):
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
                    f"{(_bt_docs['topic_id']==-1).sum()}" if not _bt_docs.empty and 'topic_id' in _bt_docs.columns else "—",
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
                            text="Count", height=max(420, len(_bt_plot)*34))
            fig_bt.update_traces(textposition="outside")
            fig_bt.update_layout(yaxis_title="", plot_bgcolor="#F8FAFC",
                                 margin=dict(t=5,b=5,l=5,r=30))
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
                _tema_papers = _bt_docs[_bt_docs["topic_id"] == _tema_sel][["title","year","abstract_best"]].rename(
                    columns={"abstract_best":"abstract"}
                ) if "abstract_best" in _bt_docs.columns else _bt_docs[_bt_docs["topic_id"] == _tema_sel][["title","year"]]
                st.dataframe(_tema_papers, use_container_width=True, hide_index=True, height=300)



# ══════════════════════════════════════════════════════════════════════════════
#  FINANCIAMIENTO I+D (ANID)
# ══════════════════════════════════════════════════════════════════════════════

elif False and seccion == "Financiamiento I+D":
    st.title("Financiamiento I+D — Fondos ANID")
    st.caption("Fuente: Repositorio ANID · 30 proyectos adjudicados · 2000–2025")
    st.divider()

    with st.expander("Filtros", expanded=True):
        fc1,fc2,fc3 = st.columns(3)
        with fc1:
            yr_a = st.slider("Año concurso", 2000, 2025, (2000, 2025))
        with fc2:
            progs = ["Todos"] + sorted(anid["programa_norm"].dropna().unique())
            prog_sel = st.selectbox("Programa", progs)
        with fc3:
            busq_a = st.text_input("🔎 Buscar en título / resumen", placeholder="ej: plasma, fusión, reactor")

    df_a = anid[anid["anio_concurso"].between(*yr_a)].copy()
    if prog_sel != "Todos": df_a = df_a[df_a["programa_norm"] == prog_sel]
    if busq_a:
        mask = df_a["titulo"].str.contains(busq_a, case=False, na=False) | \
               df_a["resumen"].str.contains(busq_a, case=False, na=False)
        df_a = df_a[mask]

    monto_t  = df_a["monto_programa_num"].sum()
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
            Proyectos=("titulo","count"),
            Monto_MM=("monto_programa_num", lambda x: x.sum()/1e6)
        ).reset_index().dropna()
        fig = go.Figure()
        fig.add_bar(x=by_a["anio_concurso"], y=by_a["Proyectos"], name="N° Proyectos", marker_color=BLUE)
        fig.add_scatter(x=by_a["anio_concurso"], y=by_a["Monto_MM"], name="MM CLP",
                        mode="lines+markers", marker_color=RED, yaxis="y2")
        fig.update_layout(yaxis=dict(title="N° Proyectos"), yaxis2=dict(title="MM CLP", overlaying="y", side="right"),
                          legend=dict(orientation="h", y=1.1), margin=dict(t=10,b=30,l=40,r=60), height=320)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        sec("Distribución por programa")
        prog_c = df_a["programa_norm"].value_counts().reset_index()
        prog_c.columns = ["Programa","N"]
        fig2 = px.pie(prog_c, names="Programa", values="N",
                      color_discrete_sequence=PALETTE, height=320)
        fig2.update_traces(textposition="inside", textinfo="percent+label")
        fig2.update_layout(margin=dict(t=10,b=10))
        st.plotly_chart(fig2, use_container_width=True)

    col3, col4 = st.columns(2)

    with col3:
        sec("Monto por instrumento (MM CLP)")
        mi = df_a.groupby("instrumento_norm")["monto_programa_num"].sum().div(1e6).reset_index()
        mi.columns = ["Instrumento","Monto_MM"]
        mi = mi.sort_values("Monto_MM")
        fig3 = px.bar(mi, x="Monto_MM", y="Instrumento", orientation="h",
                      color_discrete_sequence=[BLUE], text=mi["Monto_MM"].round(1), height=280)
        fig3.update_layout(showlegend=False, margin=dict(t=10,b=10), xaxis_title="MM CLP")
        st.plotly_chart(fig3, use_container_width=True)

    with col4:
        sec("Proyectos por instrumento")
        pi = df_a["instrumento_norm"].value_counts().reset_index()
        pi.columns = ["Instrumento","N"]
        fig4 = px.bar(pi.sort_values("N"), x="N", y="Instrumento", orientation="h",
                      color_discrete_sequence=[RED], text="N", height=280)
        fig4.update_layout(showlegend=False, margin=dict(t=10,b=10))
        st.plotly_chart(fig4, use_container_width=True)

    sec(f"Tabla de proyectos — {len(df_a)} resultados")
    show_cols = ["anio_concurso","titulo","programa_norm","instrumento_norm","autor","estado_full","monto_programa_num"]
    df_a_s = df_a[show_cols].rename(columns={
        "anio_concurso":"Año","titulo":"Título","programa_norm":"Programa",
        "instrumento_norm":"Instrumento","autor":"Investigador",
        "estado_full":"Estado","monto_programa_num":"Monto CLP"
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
            kpi("Convenios nacionales",       str(len(convenios)) if _has_conv else "—",
                "suscritos con entidades nacionales"),
            kpi("Acuerdos internacionales",   str(len(acuerdos)) if _has_acue else "—",
                "instrumentos con organismos extranjeros"),
        )

        _cv1, _cv2 = st.columns(2)

        with _cv1:
            if _has_conv:
                sec(f"Convenios nacionales ({len(convenios)})")
                # Columnas disponibles: adaptar según los datos reales
                _conv_cols = [c for c in ["CONTRAPARTE DEL CONVENIO", "DESCRIPCIÓN",
                                           "DURACIÓN", "FECHA RESOLUCIÓN"] if c in convenios.columns]
                if not _conv_cols:
                    _conv_cols = convenios.columns.tolist()
                st.dataframe(convenios[_conv_cols], use_container_width=True, height=320)
                st.download_button(
                    "Exportar convenios CSV", make_csv(convenios[_conv_cols]),
                    "convenios_nacionales_cchen.csv", "text/csv",
                )

                # Gráfico si hay columna de fecha
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

                # Gráfico por país/región si existe la columna
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


# ══════════════════════════════════════════════════════════════════════════════
#  CONVOCATORIAS Y MATCHING
# ══════════════════════════════════════════════════════════════════════════════

elif False and seccion == "Convocatorias y Matching":
    st.title("Convocatorias y Matching CCHEN")
    st.caption(
        "Cruza el radar curado de oportunidades con perfiles institucionales, reglas explícitas "
        "de elegibilidad y un scoring formal para apoyar una mesa de pre-postulación seria."
    )
    st.divider()

    _conv, _conv_mode, _conv_path = _load_convocatorias_data()
    _matching = matching_inst.copy() if matching_inst is not None else pd.DataFrame()
    _profiles = perfiles_inst.copy() if perfiles_inst is not None else pd.DataFrame()
    _rules_path = BASE / "Vigilancia" / "convocatorias_matching_rules.csv"
    _rules = pd.read_csv(_rules_path) if _rules_path.exists() else pd.DataFrame()

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
                use_container_width=True,
                hide_index=True,
                height=320,
            )

        _mf1, _mf2, _mf3, _mf4 = st.columns([1.4, 1.3, 1.3, 1.8])
        with _mf1:
            _profile_options = _profiles["perfil_nombre"].dropna().tolist() if not _profiles.empty else sorted(_matching["perfil_nombre"].dropna().unique().tolist())
            _profile_selected = st.selectbox("Perfil a revisar", _profile_options, index=0, key="matching_profile_select")
        with _mf2:
            _state_selected = st.selectbox("Estado", ["Abierto y próximo", "Solo abiertas", "Solo próximas", "Todos"], key="matching_state_select")
        with _mf3:
            _readiness_selected = st.selectbox("Preparación", ["Todas", "Listo para activar", "Requiere preparación", "Exploratorio", "No listo"], key="matching_readiness_select")
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
        _match_show = _match_show.sort_values(["score_total", "estado", "cierre_iso", "apertura_iso"], ascending=[False, True, True, True], na_position="last")

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
                use_container_width=True,
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
                use_container_width=True,
                hide_index=True,
                height=250,
            )

        sec("Lectura operativa")
        _msg = _profile_summary[_profile_summary["perfil"] == _profile_selected] if not _profile_summary.empty else pd.DataFrame()
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


# ══════════════════════════════════════════════════════════════════════════════
#  TRANSFERENCIA Y PORTAFOLIO
# ══════════════════════════════════════════════════════════════════════════════

elif False and seccion == "Transferencia y Portafolio":
    st.title("Transferencia y Portafolio Tecnológico")
    st.caption(
        "Portafolio semilla construido desde señales observables del observatorio. "
        "No reemplaza la validación técnica, pero ordena dónde conviene profundizar primero."
    )
    st.divider()

    _portfolio = _load_portafolio_seed()
    _innovation_projects = (
        anid["instrumento_norm"].astype(str).str.contains("Idea|Tecnolog|VIU|Fonis", case=False, na=False).sum()
        if "instrumento_norm" in anid.columns else 0
    )
    _top_areas_transfer = []
    if "areas" in pub_enr.columns:
        _area_counts_transfer = {}
        for _value in pub_enr["areas"].dropna():
            for _area in str(_value).split(";"):
                _area = _area.strip()
                if _area:
                    _area_counts_transfer[_area] = _area_counts_transfer.get(_area, 0) + 1
        _top_areas_transfer = sorted(_area_counts_transfer.items(), key=lambda x: -x[1])[:6]

    kpi_row(
        kpi("Activos semilla", f"{len(_portfolio):,}", "capacidades a validar"),
        kpi("Proyectos de innovación", f"{int(_innovation_projects):,}", "ANID tipo IDeA, VIU, Fonis o afines"),
        kpi("Fondos complementarios", f"{len(funding_plus):,}", "CORFO, IAEA u otras fuentes"),
        kpi("Patentes cargadas", f"{len(patents):,}", "requiere fortalecimiento si sigue en cero"),
    )

    st.markdown(
        "<div class='alert-amarillo'><b>Estado del módulo:</b> el portafolio se deja como semilla analítica. "
        "Sirve para ordenar activos y conversaciones de transferencia, pero cada fila debe validarse con responsables técnicos, "
        "TRL y situación de propiedad intelectual.</div>",
        unsafe_allow_html=True,
    )

    sec("Portafolio tecnológico semilla")
    if _portfolio.empty:
        st.info("Aún no existe `Data/Transferencia/portafolio_tecnologico_semilla.csv`.")
    else:
        st.dataframe(
            _portfolio.rename(columns={
                "activo_id": "ID",
                "nombre_activo": "Activo",
                "tipo_activo": "Tipo",
                "dominio_tecnologico": "Dominio",
                "descripcion_base": "Descripción base",
                "evidencia_observatorio": "Evidencia",
                "estado_portafolio": "Estado",
                "trl_estimado": "TRL estimado",
                "estado_validacion": "Validación",
                "unidad_referente": "Unidad referente",
                "potencial_transferencia": "Potencial de transferencia",
                "proximo_paso": "Próximo paso",
            }),
            use_container_width=True,
            hide_index=True,
            height=360,
        )
        st.download_button(
            "Exportar portafolio semilla CSV",
            make_csv(_portfolio),
            "portafolio_tecnologico_semilla.csv",
            "text/csv",
        )

    _pt1, _pt2 = st.columns(2)
    with _pt1:
        sec("Señales observables para transferencia")
        _signals = pd.DataFrame([
            {"Señal": "Proyectos de innovación / tecnologías", "Valor": int(_innovation_projects)},
            {"Señal": "Fondos complementarios registrados", "Valor": int(len(funding_plus))},
            {"Señal": "Acuerdos internacionales", "Valor": int(len(acuerdos))},
            {"Señal": "Convenios nacionales", "Valor": int(len(convenios))},
            {"Señal": "Perfiles ORCID cargados", "Valor": int(len(orcid))},
            {"Señal": "Patentes integradas", "Valor": int(len(patents))},
        ])
        fig_sig = px.bar(
            _signals.sort_values("Valor"),
            x="Valor",
            y="Señal",
            orientation="h",
            color_discrete_sequence=[BLUE],
            text="Valor",
            height=340,
        )
        fig_sig.update_layout(showlegend=False, margin=dict(t=10, b=10))
        st.plotly_chart(fig_sig, use_container_width=True)

    with _pt2:
        sec("Áreas científicas que alimentan el portafolio")
        if _top_areas_transfer:
            _area_df = pd.DataFrame(_top_areas_transfer, columns=["Área", "Papers"])
            fig_area = px.bar(
                _area_df.sort_values("Papers"),
                x="Papers",
                y="Área",
                orientation="h",
                color_discrete_sequence=[GREEN],
                text="Papers",
                height=340,
            )
            fig_area.update_layout(showlegend=False, margin=dict(t=10, b=10))
            st.plotly_chart(fig_area, use_container_width=True)
        else:
            st.info("No hay áreas enriquecidas disponibles para este resumen.")

    sec("Outputs DataCite asociados a CCHEN")
    st.caption(
        "Esta capa captura datasets y otros outputs con DOI registrados en DataCite "
        "y asociados al ROR institucional de CCHEN."
    )
    if datacite.empty:
        st.info(
            "No hay outputs DataCite cargados. Ejecuta `python3 Scripts/fetch_datacite_outputs.py` "
            "o usa `--raw-json` si trabajas desde una descarga local."
        )
    else:
        _dc = datacite.copy()
        for _col in ["publication_year", "cchen_affiliated_creators", "citation_count", "download_count", "view_count"]:
            if _col in _dc.columns:
                _dc[_col] = pd.to_numeric(_dc[_col], errors="coerce")
        _dc_direct = _dc[_dc["cchen_affiliated_creators"].fillna(0) > 0] if "cchen_affiliated_creators" in _dc.columns else _dc
        _dc_types = _dc["resource_type_general"].fillna("Sin tipo").value_counts().reset_index()
        _dc_types.columns = ["Tipo", "N"]

        kpi_row(
            kpi("Outputs DataCite", f"{len(_dc):,}", "registros vinculados al ROR CCHEN"),
            kpi("Datasets", f"{int((_dc['resource_type_general'] == 'Dataset').sum()):,}" if "resource_type_general" in _dc.columns else "0", "outputs de datos"),
            kpi("Con creador CCHEN explícito", f"{len(_dc_direct):,}", "afiliación ROR visible en creators"),
            kpi("Repositorios/publishers", f"{_dc['publisher'].nunique():,}" if "publisher" in _dc.columns else "0", "ej. Zenodo, figshare"),
        )

        _dc1, _dc2 = st.columns([1, 1.3])
        with _dc1:
            fig_dc = px.bar(
                _dc_types.sort_values("N"),
                x="N",
                y="Tipo",
                orientation="h",
                color_discrete_sequence=[PURPLE],
                text="N",
                height=260,
            )
            fig_dc.update_layout(showlegend=False, margin=dict(t=10, b=10))
            st.plotly_chart(fig_dc, use_container_width=True)
        with _dc2:
            _dc_show = _dc[[
                "publication_year", "resource_type_general", "publisher",
                "title", "doi", "cchen_affiliated_creators",
            ]].rename(columns={
                "publication_year": "Año",
                "resource_type_general": "Tipo",
                "publisher": "Repositorio",
                "title": "Título",
                "doi": "DOI",
                "cchen_affiliated_creators": "Creadores CCHEN",
            }).sort_values(["Año", "Tipo"], ascending=[False, True])
            st.dataframe(
                _dc_show,
                use_container_width=True,
                hide_index=True,
                height=280,
                column_config={"DOI": st.column_config.LinkColumn("DOI", display_text="abrir")},
            )

        st.download_button(
            "Exportar outputs DataCite CSV",
            make_csv(_dc),
            "cchen_datacite_outputs.csv",
            "text/csv",
        )

    sec("OpenAIRE Graph asociado a investigadores CCHEN")
    st.caption(
        "Esta capa usa OpenAIRE Graph para observar outputs conectados a investigadores con ORCID "
        "registrado en CCHEN y distinguir si el vínculo con CCHEN aparece por organización o solo por autor."
    )
    if openaire.empty:
        st.info(
            "No hay outputs OpenAIRE cargados. Ejecuta `python3 Scripts/fetch_openaire_outputs.py` "
            "cuando quieras poblar esta capa."
        )
    else:
        _oa = openaire.copy()
        if "matched_cchen_researchers_count" in _oa.columns:
            _oa["matched_cchen_researchers_count"] = pd.to_numeric(
                _oa["matched_cchen_researchers_count"], errors="coerce"
            ).fillna(0).astype(int)
        _oa_types = _oa["type"].fillna("Sin tipo").value_counts().reset_index()
        _oa_types.columns = ["Tipo", "N"]
        _oa_scope = _oa["match_scope"].fillna("sin clasificar").value_counts().reset_index()
        _oa_scope.columns = ["Vínculo", "N"]
        _oa_org_linked = _oa[_oa["match_scope"].isin(["cchen_ror_org", "cchen_name_org"])] if "match_scope" in _oa.columns else _oa.iloc[0:0]

        kpi_row(
            kpi("Outputs OpenAIRE", f"{len(_oa):,}", "registros agregados por output"),
            kpi("Publicaciones", f"{int((_oa['type'] == 'publication').sum()):,}" if "type" in _oa.columns else "0", "según clasificación OpenAIRE"),
            kpi("Con señal institucional CCHEN", f"{len(_oa_org_linked):,}", "organización explícita o nombre de CCHEN"),
            kpi("Investigadores CCHEN vinculados", f"{int(_oa['matched_cchen_researchers_count'].sum()):,}" if "matched_cchen_researchers_count" in _oa.columns else "0", "hits acumulados por ORCID"),
        )

        _oa1, _oa2 = st.columns([1, 1])
        with _oa1:
            fig_oa_type = px.bar(
                _oa_types.sort_values("N"),
                x="N",
                y="Tipo",
                orientation="h",
                color_discrete_sequence=[BLUE],
                text="N",
                height=260,
            )
            fig_oa_type.update_layout(showlegend=False, margin=dict(t=10, b=10))
            st.plotly_chart(fig_oa_type, use_container_width=True)
        with _oa2:
            fig_oa_scope = px.bar(
                _oa_scope.sort_values("N"),
                x="N",
                y="Vínculo",
                orientation="h",
                color_discrete_sequence=[AMBER],
                text="N",
                height=260,
            )
            fig_oa_scope.update_layout(showlegend=False, margin=dict(t=10, b=10))
            st.plotly_chart(fig_oa_scope, use_container_width=True)

        _oa_show = _oa[[
            c for c in [
                "publication_date", "type", "match_scope", "main_title", "publisher",
                "matched_researchers", "matched_cchen_researchers_count",
            ] if c in _oa.columns
        ]].rename(columns={
            "publication_date": "Fecha",
            "type": "Tipo",
            "match_scope": "Vínculo",
            "main_title": "Título",
            "publisher": "Publisher",
            "matched_researchers": "Investigadores CCHEN",
            "matched_cchen_researchers_count": "N investigadores",
        }).sort_values(["Fecha", "N investigadores"], ascending=[False, False])
        st.dataframe(
            _oa_show.head(40),
            use_container_width=True,
            hide_index=True,
            height=300,
        )

        st.download_button(
            "Exportar outputs OpenAIRE CSV",
            make_csv(_oa),
            "cchen_openaire_outputs.csv",
            "text/csv",
        )

    sec("Siguientes pasos recomendados")
    st.markdown(
        "1. Validar cada activo con investigadores, laboratorios y responsables de PI.\n"
        "2. Agregar `TRL`, equipamiento asociado, estado de madurez y contraparte interna responsable.\n"
        "3. Vincular cada activo con publicaciones, proyectos ANID, estudiantes y convenios relevantes.\n"
        "4. Incorporar patentes, secretos industriales o resultados protegibles cuando exista inventario formal."
    )


# ══════════════════════════════════════════════════════════════════════════════
#  MODELO Y GOBERNANZA
# ══════════════════════════════════════════════════════════════════════════════

elif False and seccion == "Modelo y Gobernanza":
    st.title("Modelo Unificado y Gobernanza de Datos")
    st.caption(
        "Ordena las entidades críticas del observatorio, sus relaciones y la prioridad de gobierno "
        "para que la plataforma pueda crecer sin perder trazabilidad."
    )
    st.divider()

    _entity_df, _rel_df = _load_entity_model_tables()
    _observed_counts = _build_entity_observed_counts()

    kpi_row(
        kpi("Entidades modeladas", f"{len(_entity_df):,}", "catálogo base del observatorio"),
        kpi("Relaciones definidas", f"{len(_rel_df):,}", "enlaces críticos entre entidades"),
        kpi("Entidades con datos observados", f"{sum(1 for _v in _observed_counts.values() if _v > 0):,}", "capas con evidencia cargada"),
        kpi("Fuentes integradas", "11", "publicaciones, ANID, capital humano, convenios, ORCID y más"),
    )

    st.markdown(
        "<div class='alert-azul'><b>Objetivo:</b> pasar de datasets aislados a un modelo estable de entidades "
        "(`persona`, `investigador`, `proyecto`, `publicación`, `convocatoria`, `activo tecnológico`, `institución`) "
        "que permita matching, trazabilidad y mejores respuestas del asistente.</div>",
        unsafe_allow_html=True,
    )

    sec("Catálogo de entidades")
    if _entity_df.empty:
        st.info("Aún no existe el catálogo de entidades del observatorio.")
    else:
        _entity_show = _entity_df.copy()
        _entity_show["registros_observados"] = _entity_show["entidad"].map(_observed_counts).fillna(0).astype(int)
        st.dataframe(
            _entity_show.rename(columns={
                "entidad": "Entidad",
                "descripcion": "Descripción",
                "fuente_principal": "Fuente principal",
                "identificador_clave": "Identificador",
                "nivel_sensibilidad": "Sensibilidad",
                "prioridad_gobernanza": "Prioridad",
                "steward_sugerido": "Steward sugerido",
                "estado_modelado": "Estado modelado",
                "registros_observados": "Registros observados",
            }),
            use_container_width=True,
            hide_index=True,
            height=340,
        )

    sec("Registros operativos canónicos")
    _op1, _op2, _op3, _op4 = st.columns(4)
    with _op1:
        kpi("Personas canónicas", f"{len(entity_personas):,}", "registro operativo fase 1")
    with _op2:
        kpi("Proyectos canónicos", f"{len(entity_projects):,}", "registro operativo fase 1")
    with _op3:
        kpi("Convocatorias canónicas", f"{len(entity_convocatorias):,}", "registro operativo fase 1")
    with _op4:
        kpi("Enlaces entre entidades", f"{len(entity_links):,}", "relaciones operativas generadas")

    _tab_p, _tab_proj, _tab_conv, _tab_links = st.tabs([
        "Personas", "Proyectos", "Convocatorias", "Links"
    ])
    with _tab_p:
        if entity_personas.empty:
            st.info("No existe aún `entity_registry_personas.csv`.")
        else:
            st.dataframe(
                entity_personas[[
                    "persona_id", "canonical_name", "orcid_id", "author_id",
                    "is_cchen_investigator", "appears_in_capital_humano",
                    "institution_name", "cchen_publications_count",
                ]].rename(columns={
                    "persona_id": "Persona ID",
                    "canonical_name": "Nombre canónico",
                    "orcid_id": "ORCID",
                    "author_id": "Author ID",
                    "is_cchen_investigator": "Investigador CCHEN",
                    "appears_in_capital_humano": "En capital humano",
                    "institution_name": "Institución",
                    "cchen_publications_count": "Papers CCHEN",
                }),
                use_container_width=True,
                hide_index=True,
                height=280,
            )
    with _tab_proj:
        if entity_projects.empty:
            st.info("No existe aún `entity_registry_proyectos.csv`.")
        else:
            st.dataframe(
                entity_projects[[
                    "project_id", "titulo", "autor", "institucion_name",
                    "instrumento", "estado", "strategic_profile_id",
                ]].rename(columns={
                    "project_id": "Proyecto ID",
                    "titulo": "Título",
                    "autor": "IR / Responsable",
                    "institucion_name": "Institución",
                    "instrumento": "Instrumento",
                    "estado": "Estado",
                    "strategic_profile_id": "Perfil estratégico",
                }),
                use_container_width=True,
                hide_index=True,
                height=280,
            )
    with _tab_conv:
        if entity_convocatorias.empty:
            st.info("No existe aún `entity_registry_convocatorias.csv`.")
        else:
            st.dataframe(
                entity_convocatorias[[
                    "convocatoria_id", "titulo", "estado", "perfil_id", "owner_unit", "relevancia_cchen"
                ]].rename(columns={
                    "convocatoria_id": "Convocatoria ID",
                    "titulo": "Título",
                    "estado": "Estado",
                    "perfil_id": "Perfil",
                    "owner_unit": "Unidad responsable",
                    "relevancia_cchen": "Relevancia",
                }),
                use_container_width=True,
                hide_index=True,
                height=280,
            )
    with _tab_links:
        if entity_links.empty:
            st.info("No existe aún `entity_links.csv`.")
        else:
            st.dataframe(
                entity_links.rename(columns={
                    "origin_type": "Origen",
                    "origin_id": "ID origen",
                    "relation": "Relación",
                    "target_type": "Destino",
                    "target_id": "ID destino",
                    "source_evidence": "Evidencia",
                    "confidence": "Confianza",
                }),
                use_container_width=True,
                hide_index=True,
                height=280,
            )

    sec("Relaciones críticas entre entidades")
    if _rel_df.empty:
        st.info("Aún no existe el mapa de relaciones del observatorio.")
    else:
        st.dataframe(
            _rel_df.rename(columns={
                "origen": "Origen",
                "relacion": "Relación",
                "destino": "Destino",
                "descripcion": "Descripción",
                "fuente_evidencia": "Fuente de evidencia",
                "prioridad": "Prioridad",
            }),
            use_container_width=True,
            hide_index=True,
            height=320,
        )

    sec("Prioridades inmediatas de gobernanza")
    _gov = pd.DataFrame([
        {
            "Prioridad": "1. Resolver identificadores",
            "Acción": "Definir claves maestras para persona, proyecto, publicación, convocatoria e institución.",
            "Impacto": "Evita duplicados y habilita joins estables.",
        },
        {
            "Prioridad": "2. Marcar sensibilidad",
            "Acción": "Separar explícitamente capas públicas, internas y sensibles para aplicar RLS con criterio.",
            "Impacto": "Protege capital humano y datos institucionales.",
        },
        {
            "Prioridad": "3. Trazabilidad de actualización",
            "Acción": "Registrar fecha, fuente, script y responsable de cada tabla integrada.",
            "Impacto": "Mejora auditoría y confianza en el observatorio.",
        },
        {
            "Prioridad": "4. Enlace con asistencia IA",
            "Acción": "Usar este modelo como base del contexto y luego como recuperación temática.",
            "Impacto": "Hace que el asistente responda con más precisión y menos prompt manual.",
        },
    ])
    st.dataframe(_gov, use_container_width=True, hide_index=True, height=220)

    _g1, _g2, _g3, _g4 = st.columns(4)
    with _g1:
        st.download_button(
            "Exportar entidades CSV",
            make_csv(_entity_df if not _entity_df.empty else pd.DataFrame()),
            "modelo_entidades_observatorio.csv",
            "text/csv",
        )
    with _g2:
        st.download_button(
            "Exportar relaciones CSV",
            make_csv(_rel_df if not _rel_df.empty else pd.DataFrame()),
            "relaciones_entidades_observatorio.csv",
            "text/csv",
        )
    with _g3:
        st.download_button(
            "Exportar entidades operativas",
            make_csv(entity_personas if not entity_personas.empty else pd.DataFrame()),
            "entity_registry_personas.csv",
            "text/csv",
        )
    with _g4:
        st.download_button(
            "Exportar matching formal",
            make_csv(matching_inst if matching_inst is not None and not matching_inst.empty else pd.DataFrame()),
            "convocatorias_matching_institucional.csv",
            "text/csv",
        )


# ══════════════════════════════════════════════════════════════════════════════
#  FORMACIÓN DE CAPACIDADES (Capital Humano)
# ══════════════════════════════════════════════════════════════════════════════

elif False and seccion == "Formación de Capacidades":
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
    if anio_sel:      df_c = df_c[df_c["anio_hoja"].isin(anio_sel)]
    if tipo_ch != "Todos":    df_c = df_c[df_c["tipo_norm"] == tipo_ch]
    if centro_sel != "Todos": df_c = df_c[df_c["centro_norm"] == centro_sel]
    if busq_ch:
        df_c = df_c[df_c["nombre"].str.contains(busq_ch, case=False, na=False) |
                    df_c["universidad"].str.contains(busq_ch, case=False, na=False)]

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
        tc.columns = ["Tipo","N"]
        fig1 = px.bar(tc.sort_values("N"), x="N", y="Tipo", orientation="h",
                      color="Tipo", color_discrete_sequence=PALETTE, text="N", height=300)
        fig1.update_layout(showlegend=False, margin=dict(t=10,b=10))
        st.plotly_chart(fig1, use_container_width=True)

    with col2:
        sec("Evolución anual por modalidad")
        by_at = df_c.groupby(["anio_hoja","tipo_norm"]).size().reset_index(name="N")
        fig2 = px.bar(by_at, x="anio_hoja", y="N", color="tipo_norm",
                      color_discrete_sequence=PALETTE, barmode="stack", height=300,
                      labels={"anio_hoja":"Año","N":"Personas","tipo_norm":"Modalidad"})
        fig2.update_layout(margin=dict(t=10,b=30), legend=dict(orientation="h", y=1.1))
        st.plotly_chart(fig2, use_container_width=True)

    col3, col4 = st.columns(2)

    with col3:
        sec("Por centro CCHEN")
        cc = df_c["centro_norm"].value_counts().reset_index()
        cc.columns = ["Centro","N"]
        fig3 = px.bar(cc.sort_values("N"), x="N", y="Centro", orientation="h",
                      color_discrete_sequence=[BLUE], text="N", height=340)
        fig3.update_layout(showlegend=False, margin=dict(t=10,b=10))
        st.plotly_chart(fig3, use_container_width=True)

    with col4:
        sec("Top 10 universidades de origen")
        uc = df_c["universidad"].value_counts().head(10).reset_index()
        uc.columns = ["Universidad","N"]
        fig4 = px.bar(uc.sort_values("N"), x="N", y="Universidad", orientation="h",
                      color_discrete_sequence=[RED], text="N", height=340)
        fig4.update_layout(showlegend=False, margin=dict(t=10,b=10))
        st.plotly_chart(fig4, use_container_width=True)

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
                "→ Tesista":   traj.get("funnel_practica_to_tesista",   0),
                "→ Honorarios":traj.get("funnel_practica_to_honorarios", 0),
            }
            fig5 = go.Figure(go.Funnel(
                y=list(funnel_data.keys()),
                x=list(funnel_data.values()),
                textinfo="value+percent initial",
                marker=dict(color=[BLUE, GREEN, AMBER, RED]),
            ))
            fig5.update_layout(margin=dict(t=10,b=10), height=280)
            st.plotly_chart(fig5, use_container_width=True)

    with col6:
        sec("Transiciones observadas entre modalidades")
        if not ch_trans.empty:
            ch_trans["Transición"] = ch_trans["tipo_origen"] + " → " + ch_trans["tipo_destino"]
            fig6 = px.bar(ch_trans.sort_values("transiciones"), x="transiciones", y="Transición",
                          orientation="h", color_discrete_sequence=[PURPLE], text="transiciones",
                          height=280)
            fig6.update_layout(showlegend=False, margin=dict(t=10,b=10), xaxis_title="N° casos")
            st.plotly_chart(fig6, use_container_width=True)

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
            _av = "background:#E8F5E9;border-left:4px solid #00A896;padding:8px 12px;border-radius:4px"
            st.markdown(f"<div style='{_aa}'>📊 <b>Concentración centros:</b> HHI = {hhi_c} ({nivel})<br>"
                        f"Top 3 centros concentran el <b>{pct_c}%</b> de la formación (P2MC, PEC, CTNEV)</div>",
                        unsafe_allow_html=True)
        with hc2:
            hhi_t = cap.get("hhi_tutores", 0.055)
            pct_t = cap.get("top3_tutores_share_pct", 29.5)
            nivel_t = "Alta" if hhi_t > 0.15 else "Moderada" if hhi_t > 0.10 else "Baja"
            _av = "background:#E8F5E9;border-left:4px solid #00A896;padding:8px 12px;border-radius:4px"
            st.markdown(f"<div style='{_av}'>📊 <b>Concentración tutores:</b> HHI = {hhi_t} ({nivel_t})<br>"
                        f"Top 3 tutores concentran el <b>{pct_t}%</b> de los registros</div>",
                        unsafe_allow_html=True)
        st.markdown("")

    if cap_access["can_view_sensitive"]:
        sec(f"Tabla de personas — {len(df_c)} registros")
        df_cs = df_c[["anio_hoja","nombre","tipo_norm","centro_norm","universidad","duracion_dias","tutor","ad_honorem"]
                    ].rename(columns={
            "anio_hoja":"Año","nombre":"Nombre","tipo_norm":"Modalidad","centro_norm":"Centro",
            "universidad":"Universidad","duracion_dias":"Días","tutor":"Tutor/a","ad_honorem":"Ad honorem"
        }).sort_values("Año", ascending=False)
        st.dataframe(df_cs, use_container_width=True, height=420,
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
        st.dataframe(df_cs, use_container_width=True, height=420)
        st.download_button(
            "Exportar resumen CSV",
            make_csv(df_cs),
            "capital_humano_cchen_agregado.csv",
            "text/csv",
        )


# ══════════════════════════════════════════════════════════════════════════════
#  ASISTENTE I+D
# ══════════════════════════════════════════════════════════════════════════════

elif False and seccion == "Asistente I+D":
    assistant_access = _access_context()
    st.title("Asistente I+D — CCHEN")
    st.caption("Analiza las capas integradas del observatorio y genera informes técnicos con IA")
    st.divider()

    if assistant_access["auth_enabled"] and not assistant_access["can_view_sensitive"]:
        st.warning(
            "El asistente queda restringido mientras no exista una sesión autorizada, "
            "porque el prompt incorpora contexto de capital humano y otros datos internos."
        )
        if assistant_access["auth_supported"] and not assistant_access["is_logged_in"]:
            if st.button("Iniciar sesión para habilitar el asistente", key="assistant_login"):
                st.login()
        st.stop()

    # ── Contexto de datos para el sistema ──
    _kpis_ch  = ch_ej.get("kpis", {})
    _adv      = ch_adv
    _cap      = _adv.get("concentracion", {})
    _monto_mm = anid["monto_programa_num"].sum() / 1e6
    _top_areas_raw = {}
    for _row in pub_enr["areas"].dropna():
        for _a in str(_row).split(";"):
            _a = _a.strip()
            if _a: _top_areas_raw[_a] = _top_areas_raw.get(_a, 0) + 1
    _top_areas = sorted(_top_areas_raw.items(), key=lambda x: -x[1])[:8]
    _top_journals = pub_enr["source_title"].value_counts().head(5).to_dict() if "source_title" in pub_enr.columns else pub["source"].value_counts().head(5).to_dict()

    # Investigadores con afiliación CCHEN (desde authorships)
    _auth_cchen = auth[auth["is_cchen_affiliation"] == True]
    _top_inv = (_auth_cchen.groupby("author_name")["work_id"]
                .nunique().sort_values(ascending=False).head(25))
    _inv_lista = ", ".join(f"{n} ({p} papers)" for n, p in _top_inv.items())
    _n_inv_unicos = _auth_cchen["author_name"].nunique()

    # Datos adicionales para el contexto
    _top_papers = pub.nlargest(10, 'cited_by_count')[['title','year','source','cited_by_count']]
    _papers_ctx = "\n".join(f"  - ({r.year}) {str(r.title)[:90]} | {int(r.cited_by_count)} citas | {r.source}"
                            for _, r in _top_papers.iterrows())
    _anid_ctx = "\n".join(
        f"  - ({int(r.anio_concurso) if pd.notna(r.anio_concurso) else 'sin año'}) {str(r.titulo)[:80]} | {r.instrumento_norm} | {'$'+str(round(r.monto_programa_num/1e6,1))+'MM' if pd.notna(r.monto_programa_num) and r.monto_programa_num > 0 else 'sin monto'}"
        for _, r in anid.iterrows()
    )
    _collab_inst = auth[auth['is_cchen_affiliation'] == False]['institution_name'].value_counts().head(12)
    _collab_ctx = ", ".join(f"{i} ({n})" for i, n in _collab_inst.items())
    _tutores_ctx = ", ".join(f"{t} ({n} alumnos)" for t, n in ch['tutor'].value_counts().head(10).items())
    _centros_ctx = ", ".join(f"{c} ({n})" for c, n in ch['centro_norm'].value_counts().items())
    _univs_ctx   = ", ".join(f"{u} ({n})" for u, n in ch['universidad'].value_counts().head(10).items())
    _conv_df, _conv_mode_assistant, _conv_path_assistant = _load_convocatorias_data()
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

    _matching_formal = matching_inst.copy() if matching_inst is not None else pd.DataFrame()
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

    _portfolio_df = _load_portafolio_seed()
    _portfolio_ctx = "\n".join(
        f"  - {r.nombre_activo} | TRL estimado {r.trl_estimado} | {r.potencial_transferencia}"
        for _, r in _portfolio_df.head(6).iterrows()
    ) if not _portfolio_df.empty else "  - No hay portafolio tecnológico cargado."

    _entity_df, _rel_df = _load_entity_model_tables()
    _entity_counts = _build_entity_observed_counts()
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
        if not convenios.empty and "CONTRAPARTE DEL CONVENIO" in convenios.columns else pd.Series(dtype="int64")
    )
    _convenios_ctx = ", ".join(f"{i} ({n})" for i, n in _conv_counterparties.items()) if not _conv_counterparties.empty else "Sin contraparte resumida"

    _agreement_countries = _extract_agreement_country_counts(acuerdos)
    _agreements_ctx = ", ".join(f"{i} ({n})" for i, n in _agreement_countries.head(8).items()) if not _agreement_countries.empty else "Sin países resumidos"

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
    _patents_key = os.environ.get("PATENTSVIEW_API_KEY") or st.secrets.get("PATENTSVIEW_API_KEY", "")
    _patents_ctx = (
        f"Se detectaron {len(patents)} patentes o registros de PI cargados."
        if not patents.empty else
        (
            "No hay patentes integradas en la base actual; la ruta oficial existe en "
            "`Scripts/fetch_patentsview_patents.py`, pero sigue pendiente la credencial `PATENTSVIEW_API_KEY`."
            if not _patents_key else
            "No hay patentes integradas en la base actual; no se debe inferir un portafolio de PI todavía."
        )
    )
    _datacite_df = datacite.copy()
    if not _datacite_df.empty:
        if "publication_year" in _datacite_df.columns:
            _datacite_df["publication_year"] = pd.to_numeric(_datacite_df["publication_year"], errors="coerce")
        if "cchen_affiliated_creators" in _datacite_df.columns:
            _datacite_df["cchen_affiliated_creators"] = pd.to_numeric(_datacite_df["cchen_affiliated_creators"], errors="coerce").fillna(0).astype(int)
        _datacite_types_ctx = ", ".join(
            f"{k} ({v})" for k, v in _datacite_df["resource_type_general"].fillna("Sin tipo").value_counts().items()
        )
        _datacite_titles_ctx = "\n".join(
            f"  - ({int(r.publication_year) if pd.notna(r.publication_year) else 'sin año'}) {str(r.title)[:100]} | {r.resource_type_general} | {r.publisher}"
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
            _openaire_df["matched_cchen_researchers_count"] = pd.to_numeric(
                _openaire_df["matched_cchen_researchers_count"], errors="coerce"
            ).fillna(0).astype(int)
        _openaire_scope_ctx = ", ".join(
            f"{k} ({v})" for k, v in _openaire_df["match_scope"].fillna("sin clasificar").value_counts().items()
        ) if "match_scope" in _openaire_df.columns else "Sin clasificación de vínculo"
        _openaire_types_ctx = ", ".join(
            f"{k} ({v})" for k, v in _openaire_df["type"].fillna("Sin tipo").value_counts().items()
        ) if "type" in _openaire_df.columns else "Sin tipos OpenAIRE"
        _openaire_titles_ctx = "\n".join(
            f"  - ({str(r.publication_date)[:10] if pd.notna(r.publication_date) else 'sin fecha'}) {str(r.main_title)[:100]} | {r.type} | {r.match_scope}"
            for _, r in _openaire_df.head(8).iterrows()
        )
        _openaire_org_linked = int(_openaire_df["match_scope"].isin(["cchen_ror_org", "cchen_name_org"]).sum()) if "match_scope" in _openaire_df.columns else 0
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
        _ror_pending_priority_ctx = ", ".join(
            f"{k} ({v})"
            for k, v in _ror_pending_df["priority_level"].fillna("Sin prioridad").value_counts().items()
        ) if "priority_level" in _ror_pending_df.columns else "Sin prioridades clasificadas"
        _ror_pending_top_ctx = ", ".join(
            f"{r.canonical_name} [{r.priority_level}]"
            for _, r in _ror_pending_df.head(8).iterrows()
        ) if "priority_level" in _ror_pending_df.columns else ", ".join(
            str(name) for name in _ror_pending_df["canonical_name"].head(8).tolist()
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

    _system_prompt = f"""Eres el asistente del Observatorio Tecnológico de la Comisión Chilena de Energía Nuclear (CCHEN), Chile. Apoyas al equipo de I+D con análisis de datos, redacción de informes técnicos y vigilancia tecnológica.

## Datos actuales del observatorio (cifras reales, extraídas de OpenAlex + ANID + registros internos)

### Producción Científica
- Total publicaciones: {len(pub)} trabajos (1990–2025)
- Citas totales: {int(pub['cited_by_count'].sum()):,} | Promedio: {pub['cited_by_count'].mean():.1f} citas/paper
- Papers con cuartil SJR: {len(pub_enr)} → Q1: {len(pub_enr[pub_enr['quartile']=='Q1'])}, Q2: {len(pub_enr[pub_enr['quartile']=='Q2'])}, Q3: {len(pub_enr[pub_enr['quartile']=='Q3'])}, Q4: {len(pub_enr[pub_enr['quartile']=='Q4'])}
- % Q1+Q2: {round(100*len(pub_enr[pub_enr['quartile'].isin(['Q1','Q2'])])/max(1,len(pub_enr[pub_enr['quartile'].notna()])),1)}%
- Acceso Abierto: {round(100*pub['is_oa'].mean(),1)}%
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
- Registros: {len(ch)} | Personas únicas: {ch['nombre'].nunique()} | Universidades: {ch['universidad'].nunique()}
- Modalidades: {', '.join(f"{k} ({v})" for k,v in ch['tipo_norm'].value_counts().items())}
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

    # ── API Key (Groq) ──
    api_key = os.environ.get("GROQ_API_KEY") or st.secrets.get("GROQ_API_KEY", "")
    if not api_key:
        st.warning("⚠️ Configura tu `GROQ_API_KEY` en `.streamlit/secrets.toml` para activar el asistente. Obtén una clave gratis en console.groq.com")
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
        if st.button("Limpiar chat", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
    q1,q2,q3,q4 = st.columns(4)
    prompt_rapido = ""
    if q1.button("Producción científica", use_container_width=True):
        prompt_rapido = "Genera un informe técnico ejecutivo sobre la producción científica de CCHEN. Incluye: evolución temporal, calidad (cuartiles), áreas temáticas, colaboración internacional y comparación con el promedio latinoamericano en nuclear."
    if q2.button("Financiamiento ANID", use_container_width=True):
        prompt_rapido = "Analiza el portafolio de financiamiento ANID de CCHEN. ¿Cuál es la estrategia de captación de fondos? ¿Qué oportunidades de mejora identificas para diversificar las fuentes?"
    if q3.button("Capital humano I+D", use_container_width=True):
        prompt_rapido = "Elabora un diagnóstico del capital humano I+D de CCHEN (2022–2025). Incluye composición por modalidad, concentración operativa (HHI), riesgos identificados y recomendaciones para fortalecer la formación."
    if q4.button("Resumen ejecutivo", use_container_width=True):
        prompt_rapido = "Redacta un resumen ejecutivo de 1 página del Observatorio Tecnológico Virtual de CCHEN para presentar a directivos. Incluye indicadores clave, estado actual y principales hallazgos."
    q5, q6, q7, q8 = st.columns(4)
    if q5.button("Perfil de investigadores", use_container_width=True):
        prompt_rapido = "Describe el perfil de los investigadores más productivos de CCHEN según los datos del observatorio. ¿Quiénes son los líderes en producción científica? ¿En qué áreas temáticas se concentran? ¿Qué instituciones colaboran más frecuentemente?"
    if q6.button("Colaboración internacional", use_container_width=True):
        prompt_rapido = "Analiza la red de colaboración internacional de CCHEN. ¿Con qué instituciones y países colabora más? ¿Qué oportunidades estratégicas de colaboración identifica para fortalecer la posición internacional de CCHEN en energía nuclear?"
    if q7.button("Convocatorias + matching", use_container_width=True):
        prompt_rapido = "Usando el matching institucional formal, identifica las oportunidades abiertas y próximas más relevantes para CCHEN. Organízalas por perfil, incluye score_total, eligibility_status, readiness_status, owner_unit y recommended_action, y explica por qué cada una calza o no con la evidencia interna."
    if q8.button("Transferencia / portafolio", use_container_width=True):
        prompt_rapido = "Con base en el portafolio tecnológico semilla, los proyectos ANID, publicaciones, convenios y financiamiento complementario, elabora un diagnóstico de transferencia para CCHEN. Distingue claramente entre capacidades observables, activos por validar y vacíos críticos como patentes o TRL."

    # ── Historial de chat ──
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # ── Input ──
    user_input = st.chat_input("Escribe tu consulta o solicita un informe técnico...") or prompt_rapido
    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            reply = None
            try:
                from groq import Groq as _Groq
                client = _Groq(api_key=api_key)
                _stream = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    max_tokens=2048,
                    stream=True,
                    messages=[{"role": "system", "content": _system_prompt}] +
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
                        f"- Rango: {int(pub['publication_year'].min())}–{int(pub['publication_year'].max())}\n"
                        f"- Con cuartil SJR: {len(pub_enr):,}\n\n"
                        f"_(Respuesta simplificada — servicio LLM no disponible: {e})_"
                    )
                elif any(w in _q for w in ["investigador", "autor", "orcid"]):
                    reply = (
                        f"**Investigadores CCHEN** (fuente: ORCID + OpenAlex)\n\n"
                        f"- Perfiles ORCID activos: **{len(D.get('orcid', pd.DataFrame())):,}**\n"
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
            try:
                import json as _json
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
                # Extraer primer bloque JSON válido (no greedy, evita problemas con DOTALL)
                import re as _re
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
            import datetime as _dt
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
                    use_container_width=False,
                )
            else:
                st.caption("⚠️ No se pudo generar el PDF (reportlab no disponible).")

        if prompt_rapido:
            st.rerun()
