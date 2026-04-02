"""Shared constants and helper functions — CCHEN Observatorio"""
import os
import ast
import re
import hmac
import hashlib
import math
from html import unescape as html_unescape
from pathlib import Path
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ── Colours ───────────────────────────────────────────────────────────────────
BLUE   = "#003B6F"
RED    = "#C8102E"
GREEN  = "#00A896"
AMBER  = "#F4A60D"
PURPLE = "#7B2D8B"
PALETTE = [BLUE, RED, GREEN, AMBER, PURPLE, "#E76F51", "#52B788", "#264653"]

# ── Portal list ───────────────────────────────────────────────────────────────
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
    'KP':'PRK','LY':'LBY','SL':'SLE','CG':'COG','CD':'COD','TT':'TTO',
}

# ── Streamlit compat shims ─────────────────────────────────────────────────────
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


# ── H-index ───────────────────────────────────────────────────────────────────
def calc_hindex(citation_series) -> int:
    cites = sorted(citation_series.dropna().astype(int).tolist(), reverse=True)
    return sum(1 for i, c in enumerate(cites, 1) if c >= i)


# ── KPI helpers ───────────────────────────────────────────────────────────────
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


# ── Catálogo institucional 3 en 1 ────────────────────────────────────────────
ASSET_SURFACES = {"dspace", "ckan", "dashboard"}
ASSET_PUBLICATION_STATUS = {"draft", "ready_for_publish", "published"}
ASSET_CATALOG_COLUMNS = [
    "asset_id",
    "surface",
    "title",
    "local_path",
    "area_unidad",
    "tema",
    "anio",
    "responsables",
    "palabras_clave",
    "visibilidad",
    "identificador",
    "public_url",
    "vinculo_cruzado",
    "dashboard_section",
    "publication_status",
]

OBSERVATORIO_APP_MODES = {"internal", "public"}
SECTION_VISIBILITY = {
    "Plataforma Institucional": "publica",
    "Panel de Indicadores": "interna",
    "Producción Científica": "publica",
    "Redes y Colaboración": "publica",
    "Vigilancia Tecnológica": "publica",
    "Financiamiento I+D": "publica",
    "Convocatorias y Matching": "publica",
    "Transferencia y Portafolio": "publica",
    "Modelo y Gobernanza": "interna",
    "Formación de Capacidades": "interna",
    "Asistente I+D": "mixta",
    "Grafo de Citas": "publica",
}
DEFAULT_PUBLIC_SECTIONS = tuple(
    section for section, visibility in SECTION_VISIBILITY.items()
    if visibility in {"publica", "mixta"}
)
DEFAULT_INTERNAL_SECTIONS = tuple(SECTION_VISIBILITY.keys())

_PLATFORM_URL_KEYS = {
    "dashboard_url": "http://localhost:8501",
    "dspace_ui_url": "http://localhost:4000",
    "dspace_api_url": "http://localhost:8080/server/api",
    "ckan_url": "http://localhost:5001",
    "ckan_api_url": "http://localhost:5001/api/3/action/status_show",
}


def _split_catalog_values(value) -> list[str]:
    if pd.isna(value):
        return []
    text = str(value).strip()
    if not text:
        return []
    parts = re.split(r"[;,]\s*", text)
    return [part.strip() for part in parts if part and part.strip()]


def _normalize_url_with_platform(value: str, platform_links: dict[str, str]) -> str:
    text = str(value or "").strip()
    if not text:
        return ""

    replacements = {
        "http://localhost:8501": platform_links.get("dashboard_url", ""),
        "https://localhost:8501": platform_links.get("dashboard_url", ""),
        "http://localhost:4000": platform_links.get("dspace_ui_url", ""),
        "https://localhost:4000": platform_links.get("dspace_ui_url", ""),
        "http://localhost:8080/server/api": platform_links.get("dspace_api_url", ""),
        "https://localhost:8080/server/api": platform_links.get("dspace_api_url", ""),
        "http://localhost:8080/server": platform_links.get("dspace_api_url", "").removesuffix("/api"),
        "https://localhost:8080/server": platform_links.get("dspace_api_url", "").removesuffix("/api"),
        "http://localhost:5001/api/3/action/status_show": platform_links.get("ckan_api_url", ""),
        "https://localhost:5001/api/3/action/status_show": platform_links.get("ckan_api_url", ""),
        "http://localhost:5001": platform_links.get("ckan_url", ""),
        "https://localhost:5001": platform_links.get("ckan_url", ""),
    }

    for source, target in replacements.items():
        if source and target and text.startswith(source):
            return text.replace(source, target, 1)
    return text


def asset_catalog_frame(ctx: dict) -> pd.DataFrame:
    asset_catalog = ctx.get("asset_catalog", pd.DataFrame())
    if not isinstance(asset_catalog, pd.DataFrame) or asset_catalog.empty:
        return pd.DataFrame(columns=ASSET_CATALOG_COLUMNS)

    frame = asset_catalog.copy()
    for col in ASSET_CATALOG_COLUMNS:
        if col not in frame.columns:
            frame[col] = pd.Series(dtype="object")
    for col in ASSET_CATALOG_COLUMNS:
        if col == "anio":
            continue
        frame[col] = frame[col].fillna("").astype(str).str.strip()
    frame["surface"] = frame["surface"].str.lower()
    frame["publication_status"] = frame["publication_status"].str.lower()
    frame["anio"] = pd.to_numeric(frame["anio"], errors="coerce").astype("Int64")
    platform_links = _platform_links()
    for col in ("public_url", "vinculo_cruzado"):
        frame[col] = frame[col].apply(lambda value: _normalize_url_with_platform(value, platform_links))
    return frame[ASSET_CATALOG_COLUMNS].copy()


def filter_asset_catalog(
    asset_catalog: pd.DataFrame,
    *,
    section_name: str | None = None,
    surface: str | None = None,
    publication_status: str | None = None,
    require_public_url: bool = False,
    limit: int | None = None,
) -> pd.DataFrame:
    if not isinstance(asset_catalog, pd.DataFrame) or asset_catalog.empty:
        return pd.DataFrame(columns=ASSET_CATALOG_COLUMNS)

    frame = asset_catalog.copy()
    frame = frame.reindex(columns=ASSET_CATALOG_COLUMNS, fill_value="")
    for col in ASSET_CATALOG_COLUMNS:
        if col == "anio":
            continue
        frame[col] = frame[col].fillna("").astype(str).str.strip()
    frame["surface"] = frame.get("surface", pd.Series(index=frame.index, dtype="object")).fillna("").astype(str).str.lower()
    frame["publication_status"] = frame.get(
        "publication_status",
        pd.Series(index=frame.index, dtype="object"),
    ).fillna("").astype(str).str.lower()

    if surface:
        frame = frame[frame["surface"] == str(surface).strip().lower()]
    if publication_status:
        frame = frame[
            frame["publication_status"] == str(publication_status).strip().lower()
        ]
    if section_name:
        expected = str(section_name).strip().lower()
        frame = frame[
            frame.get("dashboard_section", pd.Series(index=frame.index, dtype="object")).fillna("").astype(str).apply(
                lambda value: expected in {item.lower() for item in _split_catalog_values(value)}
            )
        ]
    if require_public_url:
        frame = frame[
            frame.get("public_url", pd.Series(index=frame.index, dtype="object")).fillna("").astype(str).str.strip() != ""
        ]

    status_order = {"published": 0, "ready_for_publish": 1, "draft": 2}
    surface_order = {"dspace": 0, "ckan": 1, "dashboard": 2}
    status_series = frame.get("publication_status", pd.Series(index=frame.index, dtype="object")).fillna("").astype(str)
    surface_series = frame.get("surface", pd.Series(index=frame.index, dtype="object")).fillna("").astype(str)
    title_series = frame.get("title", pd.Series(index=frame.index, dtype="object")).fillna("").astype(str)
    frame = frame.assign(
        _status_rank=status_series.map(status_order).fillna(9),
        _surface_rank=surface_series.map(surface_order).fillna(9),
        _title_sort=title_series.str.lower(),
    ).sort_values(
        ["_status_rank", "_surface_rank", "_title_sort"],
        ascending=[True, True, True],
        na_position="last",
    )
    frame = frame.drop(columns=["_status_rank", "_surface_rank", "_title_sort"], errors="ignore")
    if limit is not None:
        frame = frame.head(limit)
    return frame.reset_index(drop=True)


def match_assets_to_query(asset_catalog: pd.DataFrame, query: str, limit: int = 5) -> pd.DataFrame:
    if not isinstance(asset_catalog, pd.DataFrame) or asset_catalog.empty:
        return pd.DataFrame(columns=ASSET_CATALOG_COLUMNS)

    terms = [term for term in re.findall(r"\w+", str(query).lower()) if len(term) >= 3]
    if not terms:
        return filter_asset_catalog(asset_catalog, require_public_url=True, limit=limit)

    frame = asset_catalog.copy()
    frame = frame.reindex(columns=ASSET_CATALOG_COLUMNS, fill_value="")
    for col in ASSET_CATALOG_COLUMNS:
        if col == "anio":
            continue
        frame[col] = frame[col].fillna("").astype(str).str.strip()
    frame["surface"] = frame.get("surface", pd.Series(index=frame.index, dtype="object")).fillna("").astype(str).str.lower()
    frame["publication_status"] = frame.get(
        "publication_status",
        pd.Series(index=frame.index, dtype="object"),
    ).fillna("").astype(str).str.lower()

    def _score_row(row: pd.Series) -> int:
        score = 0
        title = str(row.get("title", "")).lower()
        tema = str(row.get("tema", "")).lower()
        keywords = str(row.get("palabras_clave", "")).lower()
        section = str(row.get("dashboard_section", "")).lower()
        area = str(row.get("area_unidad", "")).lower()
        publication_status = str(row.get("publication_status", "")).lower()

        for term in terms:
            if term in title:
                score += 4
            if term in tema:
                score += 3
            if term in keywords:
                score += 3
            if term in section:
                score += 2
            if term in area:
                score += 2
        if publication_status == "published":
            score += 3
        if str(row.get("public_url", "")).strip():
            score += 2
        return score

    frame = frame.assign(_score=frame.apply(_score_row, axis=1))
    frame = frame[frame["_score"] > 0].sort_values(
        ["_score", "publication_status", "title"],
        ascending=[False, True, True],
        na_position="last",
    )
    frame = frame.drop(columns=["_score"], errors="ignore")
    if limit is not None:
        frame = frame.head(limit)
    return frame.reset_index(drop=True)


def render_asset_links_table(df: pd.DataFrame, title: str, empty_message: str) -> None:
    sec(title)
    if not isinstance(df, pd.DataFrame) or df.empty:
        st.info(empty_message)
        return

    display = df.copy()
    display["anio"] = display["anio"].astype("Int64").astype(str).replace("<NA>", "")
    st.dataframe(
        display[[
            "title",
            "surface",
            "tema",
            "anio",
            "publication_status",
            "public_url",
            "vinculo_cruzado",
        ]].rename(columns={
            "title": "Activo",
            "surface": "Superficie",
            "tema": "Tema",
            "anio": "Año",
            "publication_status": "Estado",
            "public_url": "URL pública",
            "vinculo_cruzado": "Vínculo cruzado",
        }),
        width="stretch",
        hide_index=True,
        column_config={
            "URL pública": st.column_config.LinkColumn("URL pública"),
            "Vínculo cruzado": st.column_config.LinkColumn("Vínculo cruzado"),
        },
    )


# ── Bool / text helpers ───────────────────────────────────────────────────────
def _bool_from_any(value) -> bool:
    if isinstance(value, bool):
        return value
    if pd.isna(value):
        return False
    return str(value).strip().lower() in {"1", "true", "t", "yes", "y", "si", "sí"}


def _text_or_empty(value) -> str:
    return "" if pd.isna(value) else str(value).strip()


_HTML_TAG_RE = re.compile(r"<[^<>]*>?")  # handles malformed tags without closing >
_HTML_ATTR_RE = re.compile(r"(href|target)\s*=\s*\"[^\"]*\"?", re.IGNORECASE)
_URL_RE = re.compile(r"https?://\S+")


def _clean_html_text(value) -> str:
    text = html_unescape(_text_or_empty(value))
    text = text.replace("\xa0", " ")
    text = re.sub(r"<a\b[^>]*", " ", text, flags=re.IGNORECASE)
    text = _HTML_ATTR_RE.sub(" ", text)
    text = _URL_RE.sub(" ", text)
    text = text.replace("<a", " ").replace("</a", " ")
    text = _HTML_TAG_RE.sub(" ", text)
    text = text.replace("<", " ").replace(">", " ")  # catch any remaining angle brackets
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
        "ph": "pH", "iii": "III", "ii": "II", "iv": "IV",
        "vi": "VI", "vii": "VII", "viii": "VIII", "ix": "IX", "x": "X",
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


# ── Convocatorias helpers ──────────────────────────────────────────────────────
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
    import data_loader as _data_loader

    base = getattr(_data_loader, "BASE", Path(__file__).resolve().parents[2] / "Data")
    curated = base / "Vigilancia" / "convocatorias_curadas.csv"
    load_convocatorias = getattr(_data_loader, "load_convocatorias", None)

    # Intentar Supabase primero (o CSV local si existe)
    if callable(load_convocatorias):
        df = load_convocatorias()
    else:
        df = pd.read_csv(curated, encoding="utf-8-sig") if curated.exists() else pd.DataFrame()
    if not df.empty:
        return _normalize_convocatorias_df(df, mode="curated"), "curated", curated

    return pd.DataFrame(), "missing", curated


@st.cache_data
def _load_portafolio_seed() -> pd.DataFrame:
    from data_loader import BASE
    p = BASE / "Transferencia" / "portafolio_tecnologico_semilla.csv"
    if not p.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(p)
    except Exception:
        return pd.DataFrame()


@st.cache_data
def _load_entity_model_tables() -> tuple:
    from data_loader import BASE
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


def _build_entity_observed_counts(pub, ch, auth, entity_personas, entity_projects,
                                  entity_convocatorias, entity_links, acuerdos,
                                  convenios, orcid, patents) -> dict:
    conv_df = entity_convocatorias if entity_convocatorias is not None and not entity_convocatorias.empty else pd.DataFrame()
    portafolio_df = _load_portafolio_seed()
    return {
        "publicacion": len(pub),
        "persona": len(entity_personas) if entity_personas is not None and not entity_personas.empty else (ch["nombre"].nunique() if "nombre" in ch.columns else len(ch)),
        "investigador_cchen": int(entity_personas["is_cchen_investigator"].astype(str).str.lower().isin(["true", "1"]).sum()) if entity_personas is not None and not entity_personas.empty and "is_cchen_investigator" in entity_personas.columns else (auth[auth["is_cchen_affiliation"] == True]["author_name"].nunique() if "author_name" in auth.columns else 0),
        "proyecto": len(entity_projects) if entity_projects is not None and not entity_projects.empty else len(pub),
        "convocatoria": len(conv_df) if not conv_df.empty else 0,
        "activo_tecnologico": len(portafolio_df),
        "institucion": auth["institution_name"].dropna().nunique() if "institution_name" in auth.columns else 0,
        "acuerdo": len(acuerdos),
        "convenio": len(convenios),
        "orcid": len(orcid),
        "patente": len(patents),
    }


# ── Semáforo badge ─────────────────────────────────────────────────────────────
def semaforo_badge(valor):
    colores = {"VERDE": ("#E8F5E9", GREEN, "🟢"), "AMARILLO": ("#FFF8E1", AMBER, "🟡"), "ROJO": ("#FDECEA", RED, "🔴")}
    bg, border, icon = colores.get(valor, ("#F5F5F5", "#999", "⚪"))
    return f"<span style='background:{bg};border:1px solid {border};border-radius:4px;padding:2px 8px;font-size:0.85rem'>{icon} {valor}</span>"


# ── Auth / access helpers (for render_operational_strip) ──────────────────────
def _get_secret_block(name: str) -> dict:
    try:
        block = st.secrets.get(name, {})
        return dict(block) if block else {}
    except Exception:
        return {}


def _streamlit_auth_supported() -> bool:
    return all(hasattr(st, attr) for attr in ("login", "logout", "user"))


def _normalize_username(value: str) -> str:
    return str(value or "").strip().lower()


def _coerce_bool(value, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "si", "sí", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    return default


def _platform_links() -> dict[str, str]:
    secrets = _get_secret_block("platform")
    resolved: dict[str, str] = {}
    for key, default in _PLATFORM_URL_KEYS.items():
        env_key = f"OBSERVATORIO_{key.upper()}"
        resolved[key] = str(os.getenv(env_key) or secrets.get(key) or default).strip()
    return resolved


def _observatorio_config() -> dict:
    block = _get_secret_block("observatorio")
    app_mode = str(os.getenv("OBSERVATORIO_APP_MODE") or block.get("app_mode") or "internal").strip().lower()
    if app_mode not in OBSERVATORIO_APP_MODES:
        app_mode = "internal"

    public_assistant_enabled = _coerce_bool(
        os.getenv("OBSERVATORIO_PUBLIC_ASSISTANT_ENABLED"),
        default=_coerce_bool(block.get("public_assistant_enabled", True), default=True),
    )

    if app_mode == "public":
        visible_sections = list(DEFAULT_PUBLIC_SECTIONS)
        portal_badge = "Portal público"
        portal_title = "Observatorio Tecnológico CCHEN"
        portal_message = (
            "Versión pública del observatorio 3 en 1. Expone sólo vistas, datasets y activos "
            "institucionales publicables."
        )
    else:
        visible_sections = list(DEFAULT_INTERNAL_SECTIONS)
        portal_badge = "Beta interna"
        portal_title = "Observatorio Tecnológico CCHEN"
        portal_message = (
            "Acceso privado para revisión funcional, validación de datos y despliegue progresivo del observatorio."
        )

    if app_mode == "public" and not public_assistant_enabled:
        visible_sections = [section for section in visible_sections if section != "Asistente I+D"]

    return {
        "app_mode": app_mode,
        "public_assistant_enabled": public_assistant_enabled,
        "visible_sections": visible_sections,
        "portal_badge": portal_badge,
        "portal_title": portal_title,
        "portal_message": portal_message,
    }


def _observatorio_app_mode() -> str:
    return str(_observatorio_config().get("app_mode", "internal"))


def _is_public_app() -> bool:
    return _observatorio_app_mode() == "public"


def _section_visibility(section_name: str) -> str:
    return str(SECTION_VISIBILITY.get(str(section_name), "interna"))


def _available_sections(app_mode: str | None = None) -> list[str]:
    mode = str(app_mode or _observatorio_app_mode()).strip().lower()
    return list(DEFAULT_PUBLIC_SECTIONS if mode == "public" else DEFAULT_INTERNAL_SECTIONS)


def _internal_auth_config() -> dict:
    block = _get_secret_block("internal_auth")
    raw_users = block.get("users", [])
    user_items: list[dict] = []

    if isinstance(raw_users, dict):
        for username, payload in raw_users.items():
            item = dict(payload) if isinstance(payload, dict) else {}
            item.setdefault("username", username)
            user_items.append(item)
    elif isinstance(raw_users, (list, tuple)):
        for payload in raw_users:
            if isinstance(payload, dict):
                user_items.append(dict(payload))

    users_by_username: dict[str, dict] = {}
    for item in user_items:
        username = _normalize_username(item.get("username"))
        if not username:
            continue
        users_by_username[username] = {
            "username": username,
            "password": str(item.get("password", "") or ""),
            "password_sha256": str(item.get("password_sha256", "") or "").strip().lower(),
            "name": str(item.get("name", "") or username),
            "email": str(item.get("email", "") or ""),
            "role": str(item.get("role", "") or ""),
            "can_view_sensitive": bool(item.get("can_view_sensitive", True)),
        }

    enabled = bool(block.get("enabled", True)) and bool(users_by_username)
    return {
        "enabled": enabled,
        "beta_badge": str(block.get("beta_badge", "Beta interna") or "Beta interna"),
        "beta_title": str(block.get("beta_title", "Observatorio Tecnológico CCHEN") or "Observatorio Tecnológico CCHEN"),
        "beta_message": str(
            block.get(
                "beta_message",
                "Acceso privado para revisión funcional, validación de datos y despliegue progresivo del observatorio.",
            ) or ""
        ),
        "users_by_username": users_by_username,
    }


def _internal_auth_enabled() -> bool:
    return bool(_internal_auth_config().get("enabled"))


def _verify_internal_password(raw_password: str, user_cfg: dict) -> bool:
    candidate = str(raw_password or "")
    if not candidate:
        return False

    stored_hash = str(user_cfg.get("password_sha256", "") or "").strip().lower()
    if stored_hash:
        digest = hashlib.sha256(candidate.encode("utf-8")).hexdigest()
        return hmac.compare_digest(digest, stored_hash)

    stored_password = str(user_cfg.get("password", "") or "")
    if not stored_password:
        return False
    return hmac.compare_digest(candidate, stored_password)


def _internal_auth_login(username: str, password: str) -> tuple[bool, str]:
    cfg = _internal_auth_config()
    if not cfg.get("enabled"):
        return False, "El login interno no está configurado en los secrets."

    normalized = _normalize_username(username)
    user_cfg = cfg["users_by_username"].get(normalized)
    if user_cfg is None or not _verify_internal_password(password, user_cfg):
        return False, "Usuario o clave incorrectos."

    st.session_state["observatorio_internal_auth_username"] = normalized
    return True, ""


def _internal_auth_logout() -> None:
    st.session_state.pop("observatorio_internal_auth_username", None)


def _auth_enabled() -> bool:
    return _internal_auth_enabled() or (
        _streamlit_auth_supported() and bool(_get_secret_block("auth"))
    )


def _access_context() -> dict:
    observatorio_cfg = _observatorio_config()
    app_mode = observatorio_cfg["app_mode"]
    if app_mode == "public":
        return {
            "app_mode": "public",
            "auth_enabled": False,
            "auth_supported": _streamlit_auth_supported(),
            "auth_mode": "public",
            "is_logged_in": False,
            "email": "",
            "name": "visitante",
            "username": "",
            "role": "public",
            "allowlist": [],
            "is_allowlisted": False,
            "can_view_sensitive": False,
            "beta_badge": observatorio_cfg["portal_badge"],
            "beta_title": observatorio_cfg["portal_title"],
            "beta_message": observatorio_cfg["portal_message"],
            "visible_sections": observatorio_cfg["visible_sections"],
            "public_assistant_enabled": observatorio_cfg["public_assistant_enabled"],
        }

    internal_cfg = _internal_auth_config()
    if internal_cfg.get("enabled"):
        username = _normalize_username(st.session_state.get("observatorio_internal_auth_username", ""))
        user_cfg = internal_cfg["users_by_username"].get(username)
        is_logged_in = user_cfg is not None
        name = user_cfg.get("name", username or "usuario") if user_cfg else "usuario"
        email = _normalize_username(user_cfg.get("email", "")) if user_cfg else ""
        can_view_sensitive = bool(user_cfg.get("can_view_sensitive", False)) if user_cfg else False
        return {
            "app_mode": "internal",
            "auth_enabled": True,
            "auth_supported": True,
            "auth_mode": "internal",
            "is_logged_in": is_logged_in,
            "email": email,
            "name": name,
            "username": username,
            "role": user_cfg.get("role", "") if user_cfg else "",
            "allowlist": [],
            "is_allowlisted": can_view_sensitive,
            "can_view_sensitive": can_view_sensitive,
            "beta_badge": internal_cfg.get("beta_badge", "Beta interna"),
            "beta_title": internal_cfg.get("beta_title", "Observatorio Tecnológico CCHEN"),
            "beta_message": internal_cfg.get("beta_message", ""),
            "visible_sections": observatorio_cfg["visible_sections"],
            "public_assistant_enabled": observatorio_cfg["public_assistant_enabled"],
        }

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
    auth_enabled = _streamlit_auth_supported() and bool(_get_secret_block("auth"))
    can_view_sensitive = (is_logged_in and is_allowlisted) if auth_enabled else True

    return {
        "app_mode": "internal",
        "auth_enabled": auth_enabled,
        "auth_supported": _streamlit_auth_supported(),
        "auth_mode": "oidc" if auth_enabled else "open",
        "is_logged_in": is_logged_in,
        "email": email,
        "name": name,
        "username": email,
        "role": "",
        "allowlist": allowlist,
        "is_allowlisted": is_allowlisted,
        "can_view_sensitive": can_view_sensitive,
        "beta_badge": "Beta interna",
        "beta_title": "Observatorio Tecnológico CCHEN",
        "beta_message": "",
        "visible_sections": _observatorio_config()["visible_sections"],
        "public_assistant_enabled": _observatorio_config()["public_assistant_enabled"],
    }


# ── open_dataset_inspector & render_operational_strip ─────────────────────────
# These depend on data variables; they are kept in app.py where the data lives.
# Stubs exported here for import compatibility in app.py.
# The real implementations remain in app.py and are available via __builtins__ trick.
# Actually: we expose them so sections can import the name; but app.py keeps the body.
# The simplest approach: sections don't call these directly, so no stub needed.

def generate_pdf_report(question: str, answer: str,
                        pub_data=None, pub_enr_data=None,
                        auth_data=None, anid_data=None, ch_data=None,
                        chart_decision=None):
    """Genera un PDF con gráficos contextuales según el tema de la consulta."""
    try:
        import re, datetime as _dtt
        from io import BytesIO
        import matplotlib
        matplotlib.use("Agg")
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
        s_title  = ParagraphStyle("ct",  parent=styles["Title"],    textColor=BLUE_RL, fontSize=16,
                                  spaceAfter=6, spaceBefore=0, leading=20)
        s_meta   = ParagraphStyle("cm",  parent=styles["Normal"],   textColor=GREY_RL, fontSize=9,
                                  spaceAfter=12, leading=13)
        s_h2     = ParagraphStyle("ch",  parent=styles["Heading2"], textColor=BLUE_RL, fontSize=11,
                                  spaceAfter=6, spaceBefore=10, leading=15)
        s_ctx    = ParagraphStyle("cc",  parent=styles["Heading3"], textColor=GREY_RL, fontSize=9,
                                  spaceAfter=6, spaceBefore=8, leading=12)
        s_q      = ParagraphStyle("cq",  parent=styles["Normal"],   textColor=BLUE_RL, fontSize=10,
                                  leftIndent=10, rightIndent=10, backColor=BG_RL,
                                  borderPad=8, leading=16, spaceAfter=12, spaceBefore=4)
        s_body   = ParagraphStyle("cb",  parent=styles["Normal"],   fontSize=10, leading=16,
                                  spaceAfter=6, spaceBefore=0, wordWrap="CJK")
        s_bullet = ParagraphStyle("cbu", parent=styles["Normal"],   fontSize=10, leading=15,
                                  leftIndent=18, firstLineIndent=0, spaceAfter=3, spaceBefore=1,
                                  wordWrap="CJK")
        s_sub_bullet = ParagraphStyle("csbu", parent=styles["Normal"], fontSize=10, leading=15,
                                  leftIndent=32, firstLineIndent=0, spaceAfter=2, spaceBefore=0,
                                  wordWrap="CJK")
        s_footer = ParagraphStyle("cf",  parent=styles["Normal"],   textColor=GREY_RL, fontSize=8,
                                  leading=11, spaceAfter=0)

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

        def chart_investigators():
            if auth_data is None or auth_data.empty: return []
            _a = auth_data[auth_data["is_cchen_affiliation"] == True]
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
                        ax2.set_title("Citas por investigador", fontsize=9, fontweight="bold", color="#003B6F")
                        fig2.tight_layout(pad=0.5)
                        imgs.append((_png(fig2), PAGE_W, PAGE_W * 3 / 7))
                except Exception:
                    pass
            return imgs

        def chart_funding():
            if anid_data is None or anid_data.empty: return []
            imgs = []
            inst = anid_data["instrumento_norm"].value_counts().head(8)
            fig1, ax1 = plt.subplots(figsize=(6, 3))
            _apply_style(ax1)
            cs = ["#003B6F","#00A896","#F4A60D","#C8102E","#7B2D8B","#E76F51","#52B788","#264653"]
            bars = ax1.barh(inst.index[::-1], inst.values[::-1], color=cs[:len(inst)], alpha=0.85)
            for bar, v in zip(bars, inst.values[::-1]):
                ax1.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height()/2,
                         str(int(v)), va="center", fontsize=7)
            ax1.set_xlabel("N° proyectos", fontsize=8)
            ax1.set_title("Proyectos ANID por instrumento", fontsize=9, fontweight="bold", color="#003B6F")
            fig1.tight_layout(pad=0.5)
            imgs.append((_png(fig1), PAGE_W * 0.9, PAGE_W * 0.9 * 3 / 6))
            yr = anid_data.dropna(subset=["anio_concurso"])
            yr = yr[yr["anio_concurso"].between(2010, 2025)]
            by_yr = yr.groupby("anio_concurso").size().reset_index(name="N")
            if len(by_yr) > 2:
                fig2, ax2 = plt.subplots(figsize=(7, 2.5))
                _apply_style(ax2)
                ax2.bar(by_yr["anio_concurso"].astype(int), by_yr["N"], color="#003B6F", alpha=0.82)
                ax2.set_xlabel("Año concurso", fontsize=8)
                ax2.set_ylabel("N° proyectos", fontsize=8)
                ax2.set_title("Proyectos adjudicados por año", fontsize=9, fontweight="bold", color="#003B6F")
                fig2.tight_layout(pad=0.5)
                imgs.append((_png(fig2), PAGE_W, PAGE_W * 2.5 / 7))
            return imgs

        def chart_human_capital():
            if ch_data is None or ch_data.empty: return []
            imgs = []
            tipo = ch_data["tipo_norm"].value_counts() if "tipo_norm" in ch_data.columns else pd.Series()
            if not tipo.empty:
                fig1, ax1 = plt.subplots(figsize=(5, 3.5))
                cs = ["#003B6F","#00A896","#F4A60D","#C8102E","#7B2D8B","#E76F51"]
                wedges, texts, autotexts = ax1.pie(tipo.values, labels=tipo.index,
                    colors=cs[:len(tipo)], autopct="%1.0f%%", pctdistance=0.82, startangle=140)
                for t in texts: t.set_fontsize(7)
                for a in autotexts: a.set_fontsize(7); a.set_color("white")
                ax1.set_title("Composición por modalidad", fontsize=9, fontweight="bold", color="#003B6F")
                fig1.patch.set_facecolor("white")
                fig1.tight_layout(pad=0.3)
                imgs.append((_png(fig1), PAGE_W * 0.6, PAGE_W * 0.6 * 3.5 / 5))
            if "anio_hoja" in ch_data.columns:
                yr2 = ch_data.dropna(subset=["anio_hoja"])
                by_yr2 = yr2.groupby("anio_hoja").size().reset_index(name="N")
                if len(by_yr2) > 1:
                    fig2, ax2 = plt.subplots(figsize=(6, 2.5))
                    _apply_style(ax2)
                    ax2.bar(by_yr2["anio_hoja"].astype(int), by_yr2["N"], color="#00A896", alpha=0.82)
                    ax2.set_xlabel("Año", fontsize=8)
                    ax2.set_ylabel("N° personas", fontsize=8)
                    ax2.set_title("Capital humano I+D por año", fontsize=9, fontweight="bold", color="#003B6F")
                    fig2.tight_layout(pad=0.5)
                    imgs.append((_png(fig2), PAGE_W, PAGE_W * 2.5 / 6))
            return imgs

        def chart_collaboration():
            if auth_data is None or auth_data.empty: return []
            imgs = []
            _ext = auth_data[auth_data["is_cchen_affiliation"] == False]
            inst = _ext["institution_name"].value_counts().head(12).dropna()
            if not inst.empty:
                fig1, ax1 = plt.subplots(figsize=(7, 4))
                _apply_style(ax1)
                ax1.barh(inst.index[::-1], inst.values[::-1], color="#003B6F", alpha=0.82)
                for i, v in enumerate(inst.values[::-1]):
                    ax1.text(v + 0.1, i, str(int(v)), va="center", fontsize=7)
                ax1.set_xlabel("N° co-autorías", fontsize=8)
                ax1.set_title("Principales instituciones colaboradoras", fontsize=9, fontweight="bold", color="#003B6F")
                fig1.tight_layout(pad=0.5)
                imgs.append((_png(fig1), PAGE_W, PAGE_W * 4 / 7))
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
                    ax2.set_title("Colaboración por país", fontsize=9, fontweight="bold", color="#003B6F")
                    fig2.tight_layout(pad=0.5)
                    imgs.append((_png(fig2), PAGE_W * 0.7, PAGE_W * 0.7 * 2.8 / 5))
            return imgs

        def chart_quality():
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
                ax1.set_title("Distribución por cuartil SJR", fontsize=9, fontweight="bold", color="#003B6F")
                fig1.tight_layout(pad=0.5)
                imgs.append((_png(fig1), PAGE_W * 0.6, PAGE_W * 0.6 * 3 / 5))
            if pub_data is not None and "is_oa" in pub_data.columns:
                oa_c = pub_data["is_oa"].value_counts()
                fig2, ax2 = plt.subplots(figsize=(3.5, 3))
                ax2.pie([oa_c.get(True,0), oa_c.get(False,0)],
                        labels=["Acceso abierto","Cerrado"],
                        colors=["#00A896","#CBD5E1"], autopct="%1.0f%%",
                        pctdistance=0.8, startangle=90)
                ax2.set_title("Acceso abierto", fontsize=9, fontweight="bold", color="#003B6F")
                fig2.patch.set_facecolor("white")
                fig2.tight_layout(pad=0.3)
                imgs.append((_png(fig2), PAGE_W * 0.45, PAGE_W * 0.45))
            return imgs

        def chart_production():
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
            ax2.plot(by_yr["year"], by_yr["Citas"], color="#C8102E", linewidth=1.8, marker="o", markersize=3)
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
            if "source" in pub_data.columns:
                jrnl = pub_data["source"].value_counts().head(8).dropna()
                fig2, ax3 = plt.subplots(figsize=(7, 3))
                _apply_style(ax3)
                ax3.barh(jrnl.index[::-1], jrnl.values[::-1], color="#003B6F", alpha=0.75)
                for i, v in enumerate(jrnl.values[::-1]):
                    ax3.text(v + 0.1, i, str(int(v)), va="center", fontsize=7)
                ax3.set_xlabel("N° publicaciones", fontsize=8)
                ax3.set_title("Principales revistas de publicación", fontsize=9, fontweight="bold", color="#003B6F")
                fig2.tight_layout(pad=0.5)
                imgs.append((_png(fig2), PAGE_W, PAGE_W * 3 / 7))
            return imgs

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

        story = []
        story.append(Paragraph("CCHEN \u2014 Observatorio Tecnol\u00f3gico I+D+i+Tt", s_title))
        story.append(Paragraph(
            f"Informe generado: {_dtt.datetime.now().strftime('%d/%m/%Y %H:%M')} "
            f"\u00b7 Asistente IA (Groq / llama-3.3-70b-versatile)", s_meta))
        story.append(HRFlowable(width="100%", thickness=2, color=RED_RL, spaceAfter=10))

        if chart_imgs:
            story.append(Paragraph(f"Datos de contexto \u2014 {_topic_labels[topic]}:", s_h2))
            story.append(Spacer(1, 0.20*cm))
            for (ib, w, h) in chart_imgs:
                # Clamp width to PAGE_W and keep aspect ratio to prevent overflow
                _max_w = PAGE_W
                if w > _max_w:
                    h = h * (_max_w / w)
                    w = _max_w
                story.append(RLImage(ib, width=w, height=h))
                story.append(Spacer(1, 0.30*cm))
            story.append(HRFlowable(width="100%", thickness=1,
                                    color=colors.HexColor("#CCCCCC"), spaceAfter=10))
            story.append(Spacer(1, 0.15*cm))

        story.append(Paragraph("<b>Consulta:</b>", s_h2))
        story.append(Spacer(1, 0.10*cm))
        story.append(Paragraph(_esc(question), s_q))
        story.append(Spacer(1, 0.35*cm))
        story.append(Paragraph("<b>Respuesta del Asistente:</b>", s_h2))
        story.append(Spacer(1, 0.20*cm))

        for line in answer.split("\n"):
            line = line.rstrip()
            if not line:
                story.append(Spacer(1, 0.20*cm)); continue
            esc = _esc(line)
            if   line.startswith("### "):                  story.append(Paragraph(esc[4:],       s_h2))
            elif line.startswith("## "):                   story.append(Paragraph(esc[3:],       s_h2))
            elif line.startswith("# "):                    story.append(Paragraph(esc[2:],       s_h2))
            elif line.startswith(("- ","* ","\u2022 ")):   story.append(Paragraph("\u2022 " + esc[2:],   s_bullet))
            elif line.startswith(("  - ","  * ","   - ")): story.append(Paragraph("\u25e6 " + esc.lstrip(" -* "), s_sub_bullet))
            elif line.startswith(("    - ","    * ")):     story.append(Paragraph("\u25e6 " + esc.lstrip(" -* "), s_sub_bullet))
            elif line.startswith(("**", "__")) and line.rstrip("* _:").endswith(("**", "__", ":")):
                story.append(Paragraph(esc, s_h2))
            else:                                          story.append(Paragraph(esc,            s_body))

        story.append(Spacer(1, 0.60*cm))
        story.append(HRFlowable(width="100%", thickness=1,
                                color=colors.HexColor("#CCCCCC"), spaceAfter=8))
        story.append(Spacer(1, 0.10*cm))
        story.append(Paragraph(
            "Observatorio Tecnol\u00f3gico Virtual CCHEN \u00b7 "
            "Proyecto CORFO CCHEN 360 \u00b7 Beta v0.2", s_footer))

        doc.build(story)
        return buf.getvalue()
    except Exception:
        return None
