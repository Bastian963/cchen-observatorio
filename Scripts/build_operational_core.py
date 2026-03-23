#!/usr/bin/env python3
"""
Construye la capa operativa de Fase 1 para el observatorio:
- entidades canónicas
- enlaces entre entidades
- matching institucional formal para convocatorias

Uso:
    cd /Users/bastianayalainostroza/Dropbox/CCHEN
    python3 Scripts/build_operational_core.py
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from datetime import date, datetime
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "Data"
PUB = DATA / "Publications"
ANID_DIR = DATA / "ANID"
RES_DIR = DATA / "Researchers"
INST_DIR = DATA / "Institutional"
FUND_DIR = DATA / "Funding"
TRANS_DIR = DATA / "Transferencia"
VIG_DIR = DATA / "Vigilancia"
GOV_DIR = DATA / "Gobernanza"
CH_DIR = DATA / "Capital humano CCHEN" / "salida_dataset_maestro"

FILES = {
    "orcid": RES_DIR / "cchen_researchers_orcid.csv",
    "auth": PUB / "cchen_authorships_enriched.csv",
    "anid": ANID_DIR / "RepositorioAnid_con_monto.csv",
    "conv": VIG_DIR / "convocatorias_curadas.csv",
    "ror": INST_DIR / "cchen_institution_registry.csv",
    "funding": FUND_DIR / "cchen_funding_complementario.csv",
    "portfolio": TRANS_DIR / "portafolio_tecnologico_semilla.csv",
    "capital": CH_DIR / "dataset_maestro_limpio.csv",
    "convenios": INST_DIR / "clean_Convenios_suscritos_por_la_Com.csv",
    "acuerdos": INST_DIR / "clean_Acuerdos_e_instrumentos_intern.csv",
    "profiles": VIG_DIR / "perfiles_institucionales_cchen.csv",
    "rules": VIG_DIR / "convocatorias_matching_rules.csv",
}

OUT_PERSONAS = GOV_DIR / "entity_registry_personas.csv"
OUT_PROYECTOS = GOV_DIR / "entity_registry_proyectos.csv"
OUT_CONVOCATORIAS = GOV_DIR / "entity_registry_convocatorias.csv"
OUT_LINKS = GOV_DIR / "entity_links.csv"
OUT_MATCHING = VIG_DIR / "convocatorias_matching_institucional.csv"


def _text(value: object) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return str(value).strip()


def _norm(value: object) -> str:
    text = _text(value)
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii").lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _hash_id(prefix: str, *parts: object) -> str:
    base = " | ".join(_norm(p) for p in parts if _norm(p))
    return f"{prefix}_{hashlib.md5(base.encode('utf-8')).hexdigest()[:12]}"


def _split_multi(value: object) -> list[str]:
    return [chunk.strip() for chunk in _text(value).split(";") if chunk.strip()]


def _bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return _text(value).lower() in {"1", "true", "t", "yes", "y", "si", "sí"}


def _name_variants(value: object) -> list[str]:
    text = _text(value)
    if not text:
        return []
    variants = {_norm(text)}
    if "," in text:
        parts = [chunk.strip() for chunk in text.split(",", 1)]
        if len(parts) == 2 and parts[0] and parts[1]:
            variants.add(_norm(f"{parts[1]} {parts[0]}"))
    return [v for v in variants if v]


def _load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path, encoding="utf-8-sig", on_bad_lines="skip").fillna("")
    except Exception:
        return pd.read_csv(path, on_bad_lines="skip").fillna("")


def load_inputs() -> dict[str, pd.DataFrame]:
    return {name: _load_csv(path) for name, path in FILES.items()}


def build_institution_lookup(ror_df: pd.DataFrame) -> tuple[dict[str, tuple[str, str]], str]:
    lookup: dict[str, tuple[str, str]] = {}
    anchor_id = ""
    if ror_df.empty:
        return lookup, anchor_id
    for _, row in ror_df.iterrows():
        canonical = _text(row.get("canonical_name"))
        norm_key = _text(row.get("normalized_key")) or _norm(canonical)
        inst_id = _text(row.get("ror_id")) or norm_key
        if canonical:
            lookup[_norm(canonical)] = (inst_id, canonical)
        if norm_key:
            lookup[_norm(norm_key)] = (inst_id, canonical or norm_key)
        for alias in _split_multi(row.get("aliases_observed")):
            lookup[_norm(alias)] = (inst_id, canonical or alias)
        if _bool(row.get("is_cchen_anchor")):
            anchor_id = inst_id
            lookup[_norm("CCHEN")] = (inst_id, canonical)
    return lookup, anchor_id


def resolve_institution(name: object, lookup: dict[str, tuple[str, str]], anchor_id: str) -> tuple[str, str]:
    text = _text(name)
    if not text:
        return anchor_id or "", "Comisión Chilena de Energía Nuclear" if anchor_id else ""
    key = _norm(text)
    if key in lookup:
        return lookup[key]
    if key in {_norm("Comision Chilena de Energia Nuclear"), _norm("Comisión Chilena de Energía Nuclear"), _norm("CCHEN"), _norm("Chilean Nuclear Energy Commission")}:
        return anchor_id or key, "Comisión Chilena de Energía Nuclear"
    return key, text


def _authorships_summary(auth_df: pd.DataFrame) -> pd.DataFrame:
    if auth_df.empty:
        return pd.DataFrame(columns=["author_id", "author_name", "normalized_name", "cchen_publications_count"])
    cchen = auth_df[auth_df["is_cchen_affiliation"].map(_bool)].copy()
    if cchen.empty:
        return pd.DataFrame(columns=["author_id", "author_name", "normalized_name", "cchen_publications_count"])
    out = (
        cchen.groupby(["author_id", "author_name"], dropna=False)["work_id"]
        .nunique()
        .reset_index(name="cchen_publications_count")
    )
    out["normalized_name"] = out["author_name"].map(_norm)
    return out.sort_values("cchen_publications_count", ascending=False)


def build_personas(inputs: dict[str, pd.DataFrame], lookup: dict[str, tuple[str, str]], anchor_id: str) -> pd.DataFrame:
    orcid = inputs["orcid"].copy()
    auth = _authorships_summary(inputs["auth"])
    capital = inputs["capital"].copy()

    auth_by_name = {
        row["normalized_name"]: row
        for _, row in auth.iterrows()
        if _text(row.get("normalized_name"))
    }

    rows: list[dict] = []
    used_author_ids: set[str] = set()
    used_names: set[str] = set()

    for _, row in orcid.iterrows():
        full_name = _text(row.get("full_name"))
        if not full_name:
            continue
        norm_name = _norm(full_name)
        auth_row = auth_by_name.get(norm_name)
        institution_id, institution_name = anchor_id, "Comisión Chilena de Energía Nuclear"
        for employer in _split_multi(row.get("employers")):
            institution_id, institution_name = resolve_institution(employer, lookup, anchor_id)
            if institution_name:
                break
        persona = {
            "persona_id": _text(row.get("orcid_id")) or (auth_row.get("author_id") if auth_row is not None else _hash_id("pers", full_name)),
            "canonical_name": full_name,
            "normalized_name": norm_name,
            "orcid_id": _text(row.get("orcid_id")),
            "author_id": _text(auth_row.get("author_id")) if auth_row is not None else "",
            "source_anchor": "orcid",
            "source_coverage": "; ".join(sorted({"orcid", "authorships"} if auth_row is not None else {"orcid"})),
            "is_cchen_investigator": bool(anchor_id and institution_id == anchor_id),
            "appears_in_capital_humano": bool(not capital.empty and capital["nombre"].map(_norm).eq(norm_name).any()),
            "appears_in_orcid": True,
            "appears_in_authorships": auth_row is not None,
            "institution_id": institution_id,
            "institution_name": institution_name,
            "cchen_publications_count": int(auth_row.get("cchen_publications_count", 0)) if auth_row is not None else 0,
            "orcid_works_count": int(pd.to_numeric(row.get("orcid_works_count"), errors="coerce") or 0),
            "capital_humano_records": int(capital["nombre"].map(_norm).eq(norm_name).sum()) if not capital.empty else 0,
            "employers": _text(row.get("employers")),
            "education": _text(row.get("education")),
            "sensitivity_level": "Media" if capital is not None and (not capital.empty and capital["nombre"].map(_norm).eq(norm_name).any()) else "Baja",
        }
        rows.append(persona)
        used_names.add(norm_name)
        if persona["author_id"]:
            used_author_ids.add(persona["author_id"])

    for _, row in auth.iterrows():
        author_id = _text(row.get("author_id"))
        author_name = _text(row.get("author_name"))
        norm_name = _text(row.get("normalized_name"))
        if not author_name or author_id in used_author_ids or norm_name in used_names:
            continue
        rows.append({
            "persona_id": author_id or _hash_id("pers", author_name),
            "canonical_name": author_name,
            "normalized_name": norm_name,
            "orcid_id": "",
            "author_id": author_id,
            "source_anchor": "authorships",
            "source_coverage": "authorships",
            "is_cchen_investigator": True,
            "appears_in_capital_humano": bool(not capital.empty and capital["nombre"].map(_norm).eq(norm_name).any()),
            "appears_in_orcid": False,
            "appears_in_authorships": True,
            "institution_id": anchor_id,
            "institution_name": "Comisión Chilena de Energía Nuclear",
            "cchen_publications_count": int(row.get("cchen_publications_count", 0)),
            "orcid_works_count": 0,
            "capital_humano_records": int(capital["nombre"].map(_norm).eq(norm_name).sum()) if not capital.empty else 0,
            "employers": "Comisión Chilena de Energía Nuclear",
            "education": "",
            "sensitivity_level": "Media" if not capital.empty and capital["nombre"].map(_norm).eq(norm_name).any() else "Baja",
        })
        used_names.add(norm_name)
        if author_id:
            used_author_ids.add(author_id)

    if not capital.empty:
        for _, row in capital.iterrows():
            person_name = _text(row.get("nombre"))
            norm_name = _norm(person_name)
            if not person_name or norm_name in used_names:
                continue
            rows.append({
                "persona_id": _hash_id("pers", person_name),
                "canonical_name": person_name,
                "normalized_name": norm_name,
                "orcid_id": "",
                "author_id": "",
                "source_anchor": "capital_humano",
                "source_coverage": "capital_humano",
                "is_cchen_investigator": False,
                "appears_in_capital_humano": True,
                "appears_in_orcid": False,
                "appears_in_authorships": False,
                "institution_id": anchor_id,
                "institution_name": "Comisión Chilena de Energía Nuclear",
                "cchen_publications_count": 0,
                "orcid_works_count": 0,
                "capital_humano_records": int(capital["nombre"].map(_norm).eq(norm_name).sum()),
                "employers": "",
                "education": "",
                "sensitivity_level": "Media",
            })
            used_names.add(norm_name)

    out = pd.DataFrame(rows)
    if out.empty:
        return out
    out = out.sort_values(
        ["is_cchen_investigator", "cchen_publications_count", "orcid_works_count", "capital_humano_records", "canonical_name"],
        ascending=[False, False, False, False, True],
    ).drop_duplicates(subset=["persona_id"])
    return out


def map_project_profile(row: pd.Series) -> str:
    joined = " ".join(
        _text(row.get(col))
        for col in ("instrumento", "instrumento_full", "instrumento_norm", "programa", "programa_full", "titulo")
    ).lower()
    if "postdoctor" in joined or "posdoctor" in joined:
        return "postdoctorado"
    if "doctorado" in joined or "tesis" in joined:
        return "doctorado_formacion"
    if any(token in joined for token in ["anillo", "milenio", "equipamiento", "centro", "consor"]):
        return "infraestructura_consorcios"
    if any(token in joined for token in ["ecos", "gemini", "alma", "movilidad", "vinculacion", "cooperacion"]):
        return "cooperacion_movilidad"
    if any(token in joined for token in ["idea", "tecnolog", "viu", "innov", "transfer", "fonis"]):
        return "innovacion_transferencia"
    return "pi_ciencia"


def build_projects(inputs: dict[str, pd.DataFrame], persons: pd.DataFrame, lookup: dict[str, tuple[str, str]], anchor_id: str) -> pd.DataFrame:
    anid = inputs["anid"].copy()
    if anid.empty:
        return pd.DataFrame()
    person_lookup: dict[str, str] = {}
    for _, prow in persons.iterrows():
        for variant in _name_variants(prow.get("canonical_name")):
            person_lookup.setdefault(variant, prow["persona_id"])
    rows = []
    for _, row in anid.iterrows():
        title = _text(row.get("titulo"))
        code = _text(row.get("proyecto"))
        author = _text(row.get("autor"))
        author_persona_id = ""
        for variant in _name_variants(author):
            if variant in person_lookup:
                author_persona_id = person_lookup[variant]
                break
        inst_id, inst_name = resolve_institution(_text(row.get("institucion_full")) or _text(row.get("institucion")), lookup, anchor_id)
        rows.append({
            "project_id": code or _hash_id("proj", title, row.get("anio_concurso")),
            "proyecto_codigo": code,
            "titulo": title,
            "anio_concurso": pd.to_numeric(row.get("anio_concurso"), errors="coerce"),
            "autor": author,
            "autor_persona_id": author_persona_id,
            "institucion_id": inst_id,
            "institucion_name": inst_name,
            "programa": _text(row.get("programa_full")) or _text(row.get("programa")),
            "instrumento": _text(row.get("instrumento_full")) or _text(row.get("instrumento")),
            "estado": _text(row.get("estado_full")) or _text(row.get("estado")),
            "monto_programa_num": pd.to_numeric(row.get("monto_programa_num"), errors="coerce"),
            "strategic_profile_id": map_project_profile(row),
            "data_source": "ANID Repositorio",
        })
    out = pd.DataFrame(rows).drop_duplicates(subset=["project_id"])
    return out.sort_values(["anio_concurso", "titulo"], ascending=[False, True], na_position="last")


def load_profiles(inputs: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, pd.DataFrame]:
    profiles = inputs["profiles"].copy()
    rules = inputs["rules"].copy()
    for df in (profiles, rules):
        if df.empty:
            continue
        for col in df.columns:
            if df[col].dtype == object:
                df[col] = df[col].fillna("")
    return profiles, rules


def parse_aliases(text: object) -> list[str]:
    return [_text(x) for x in _text(text).split(";") if _text(x)]


def build_profile_evidence(inputs: dict[str, pd.DataFrame], persons: pd.DataFrame) -> dict[str, dict]:
    anid = inputs["anid"]
    auth = inputs["auth"]
    capital = inputs["capital"]
    funding = inputs["funding"]
    portfolio = inputs["portfolio"]
    acuerdos = inputs["acuerdos"]
    convenios = inputs["convenios"]

    innovation_projects = int(
        anid.apply(lambda r: map_project_profile(r) == "innovacion_transferencia", axis=1).sum()
    ) if not anid.empty else 0
    infra_projects = int(
        anid.apply(lambda r: map_project_profile(r) == "infraestructura_consorcios", axis=1).sum()
    ) if not anid.empty else 0
    postdoc_projects = int(
        anid.apply(lambda r: map_project_profile(r) == "postdoctorado", axis=1).sum()
    ) if not anid.empty else 0
    pi_projects = int(
        anid.apply(lambda r: map_project_profile(r) == "pi_ciencia", axis=1).sum()
    ) if not anid.empty else 0
    doctoral_pipeline = int(capital["tipo_norm"].astype(str).str.contains("tesista|memorista", case=False, na=False).sum()) if not capital.empty and "tipo_norm" in capital.columns else 0
    intl_inst = int(auth[~auth["is_cchen_affiliation"].map(_bool)]["institution_name"].astype(str).replace("", pd.NA).dropna().nunique()) if not auth.empty else 0
    acuerdos_n = len(acuerdos)
    convenios_n = len(convenios)
    funding_n = len(funding)
    portfolio_n = len(portfolio)
    instrument_assets = int(portfolio["dominio_tecnologico"].astype(str).str.contains("instrument", case=False, na=False).sum()) if not portfolio.empty and "dominio_tecnologico" in portfolio.columns else 0
    top_areas = "sin áreas sintetizadas en esta capa"

    def strength_points(label: str) -> int:
        return {"Alta": 15, "Media": 10, "Inicial": 5}.get(label, 5)

    evidence = {
        "pi_ciencia": {
            "strength": "Alta" if pi_projects >= 10 else "Media" if pi_projects >= 4 else "Inicial",
            "evidence_specific": 5 if pi_projects >= 10 else 3 if pi_projects >= 4 else 1,
            "summary": f"{pi_projects} proyectos ANID de perfil científico y {persons['is_cchen_investigator'].sum()} investigadores CCHEN canónicos.",
            "booleans": {"doctorado": True, "institucion": True, "transferencia": innovation_projects > 0, "red_internacional": intl_inst > 0, "capacidad_instrumental": instrument_assets > 0},
        },
        "postdoctorado": {
            "strength": "Alta" if postdoc_projects >= 2 or doctoral_pipeline >= 15 else "Media" if postdoc_projects >= 1 or doctoral_pipeline >= 8 else "Inicial",
            "evidence_specific": 5 if postdoc_projects >= 2 or doctoral_pipeline >= 15 else 3 if postdoc_projects >= 1 or doctoral_pipeline >= 8 else 1,
            "summary": f"{postdoc_projects} proyectos posdoctorales detectados y pipeline de {doctoral_pipeline} tesistas/memoristas.",
            "booleans": {"doctorado": doctoral_pipeline > 0, "institucion": True, "transferencia": innovation_projects > 0, "red_internacional": acuerdos_n > 0, "capacidad_instrumental": instrument_assets > 0},
        },
        "doctorado_formacion": {
            "strength": "Alta" if doctoral_pipeline >= 20 else "Media" if doctoral_pipeline >= 8 else "Inicial",
            "evidence_specific": 5 if doctoral_pipeline >= 20 else 3 if doctoral_pipeline >= 8 else 1,
            "summary": f"{doctoral_pipeline} registros de formación avanzada en capital humano.",
            "booleans": {"doctorado": doctoral_pipeline > 0, "institucion": True, "transferencia": innovation_projects > 0, "red_internacional": acuerdos_n > 0, "capacidad_instrumental": instrument_assets > 0},
        },
        "innovacion_transferencia": {
            "strength": "Alta" if innovation_projects + funding_n + portfolio_n >= 6 else "Media" if innovation_projects + funding_n + portfolio_n >= 3 else "Inicial",
            "evidence_specific": 5 if innovation_projects + funding_n + portfolio_n >= 6 else 3 if innovation_projects + funding_n + portfolio_n >= 3 else 1,
            "summary": f"{innovation_projects} proyectos ANID aplicados, {funding_n} fondos complementarios y {portfolio_n} activos semilla.",
            "booleans": {"doctorado": doctoral_pipeline > 0, "institucion": True, "transferencia": innovation_projects + funding_n + portfolio_n > 0, "red_internacional": acuerdos_n > 0, "capacidad_instrumental": instrument_assets > 0},
        },
        "infraestructura_consorcios": {
            "strength": "Alta" if infra_projects + instrument_assets + acuerdos_n >= 6 else "Media" if infra_projects + instrument_assets + acuerdos_n >= 3 else "Inicial",
            "evidence_specific": 5 if infra_projects + instrument_assets + acuerdos_n >= 6 else 3 if infra_projects + instrument_assets + acuerdos_n >= 3 else 1,
            "summary": f"{infra_projects} proyectos asociativos/equipamiento, {instrument_assets} activos instrumentales y {acuerdos_n} acuerdos internacionales.",
            "booleans": {"doctorado": doctoral_pipeline > 0, "institucion": True, "transferencia": portfolio_n > 0, "red_internacional": acuerdos_n > 0, "capacidad_instrumental": infra_projects > 0 or instrument_assets > 0},
        },
        "cooperacion_movilidad": {
            "strength": "Alta" if intl_inst >= 20 or acuerdos_n >= 10 else "Media" if intl_inst >= 8 or acuerdos_n >= 3 or convenios_n >= 10 else "Inicial",
            "evidence_specific": 5 if intl_inst >= 20 or acuerdos_n >= 10 else 3 if intl_inst >= 8 or acuerdos_n >= 3 or convenios_n >= 10 else 1,
            "summary": f"{intl_inst} instituciones colaboradoras externas, {acuerdos_n} acuerdos internacionales y {convenios_n} convenios nacionales.",
            "booleans": {"doctorado": doctoral_pipeline > 0, "institucion": True, "transferencia": funding_n > 0, "red_internacional": intl_inst > 0 or acuerdos_n > 0, "capacidad_instrumental": instrument_assets > 0},
        },
    }

    for payload in evidence.values():
        payload["strength_points"] = strength_points(payload["strength"])
    return evidence


def deadline_metrics(row: pd.Series) -> tuple[str, int]:
    today = date.today()
    state = _text(row.get("estado"))
    target_text = row.get("cierre_iso") if state == "Abierto" else row.get("apertura_iso")
    target = pd.to_datetime(target_text, errors="coerce")
    if pd.isna(target):
        return "Sin fecha crítica", 0
    days = (target.date() - today).days
    if days <= 30:
        return "Ventana <= 30 días", 10
    if days <= 60:
        return "Ventana 31-60 días", 5
    return "Ventana > 60 días", 0


def evaluate_eligibility(rule: pd.Series, evidence: dict) -> tuple[str, int, list[str]]:
    checks = {
        "requiere_doctorado": ("doctorado", "base doctoral"),
        "requiere_institucion": ("institucion", "respaldo institucional"),
        "requiere_transferencia": ("transferencia", "señales de transferencia"),
        "requiere_red_internacional": ("red_internacional", "red internacional"),
        "requiere_capacidad_instrumental": ("capacidad_instrumental", "capacidad instrumental"),
    }
    penalties = 0
    missing: list[str] = []
    for rule_col, (ev_key, label) in checks.items():
        if not _bool(rule.get(rule_col)):
            continue
        value = evidence["booleans"].get(ev_key)
        if value is False:
            penalties -= 30
            missing.append(label)
        elif value is None:
            penalties -= 10
            missing.append(f"{label} (por validar)")
    if penalties <= -30:
        return "No cumple base observada", penalties, missing
    if penalties < 0:
        return "Requiere validación", penalties, missing
    return "Cumple base observada", penalties, missing


def readiness_label(score_total: int, eligibility_status: str) -> str:
    if eligibility_status == "No cumple base observada":
        return "No listo"
    if score_total >= 75:
        return "Listo para activar"
    if score_total >= 55:
        return "Requiere preparación"
    return "Exploratorio"


def recommended_action(score_total: int, state: str, owner_unit: str, eligibility_status: str) -> str:
    if eligibility_status == "No cumple base observada":
        return f"Revisar elegibilidad antes de asignar a {owner_unit}."
    if state == "Abierto" and score_total >= 75:
        return f"Activar pre-postulación inmediata con {owner_unit} y contraparte técnica."
    if state == "Abierto" and score_total >= 55:
        return f"Abrir evaluación rápida de capacidad con {owner_unit}."
    if state == "Próximo" and score_total >= 75:
        return f"Preparar pipeline y designar formulador en {owner_unit} antes de apertura."
    return f"Mantener en radar institucional y reunir evidencia mínima con {owner_unit}."


def build_matching(
    inputs: dict[str, pd.DataFrame],
    persons: pd.DataFrame,
    projects: pd.DataFrame,
    profiles: pd.DataFrame,
    rules: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    conv = inputs["conv"].copy()
    if conv.empty or profiles.empty or rules.empty:
        return pd.DataFrame(), pd.DataFrame()

    calls = conv[conv["tipo_registro"].astype(str) == "convocatoria"].copy()
    calls = calls[calls["estado"].astype(str).isin(["Abierto", "Próximo"])].copy()
    if calls.empty:
        return pd.DataFrame(), pd.DataFrame()

    evidence_by_profile = build_profile_evidence(inputs, persons)
    profile_map = {row["perfil_id"]: row for _, row in profiles.iterrows()}

    registry_rows: list[dict] = []
    match_rows: list[dict] = []
    for _, call in calls.iterrows():
        call_profile = _text(call.get("perfil_objetivo"))
        matched_any = False
        for _, rule in rules.iterrows():
            exact_aliases = parse_aliases(rule.get("exact_aliases"))
            secondary_aliases = parse_aliases(rule.get("secondary_aliases"))
            match_type = ""
            if call_profile in exact_aliases:
                match_type = "exacto"
                profile_points = 20
            elif call_profile in secondary_aliases:
                match_type = "secundario"
                profile_points = 10
            else:
                continue

            matched_any = True
            profile = profile_map.get(rule["perfil_id"], {})
            evidence = evidence_by_profile.get(rule["perfil_id"], {
                "strength": "Inicial",
                "strength_points": 5,
                "evidence_specific": 1,
                "summary": "Sin señales suficientes",
                "booleans": {},
            })
            state_points = {"Abierto": 25, "Próximo": 15}.get(_text(call.get("estado")), 0)
            rel_points = {"Alta": 25, "Media": 15, "Baja": 5}.get(_text(call.get("relevancia_cchen")), 5)
            deadline_class, deadline_points = deadline_metrics(call)
            eligibility_status, eligibility_penalty, missing = evaluate_eligibility(rule, evidence)
            score_total = (
                state_points
                + rel_points
                + profile_points
                + evidence["strength_points"]
                + deadline_points
                + evidence["evidence_specific"]
                + eligibility_penalty
            )
            score_total = max(0, min(100, int(score_total)))
            readiness = readiness_label(score_total, eligibility_status)
            owner_unit = _text(profile.get("owner_unit")) or "Observatorio"
            recommended = recommended_action(score_total, _text(call.get("estado")), owner_unit, eligibility_status)
            breakdown = {
                "estado": state_points,
                "relevancia_cchen": rel_points,
                "ajuste_perfil": profile_points,
                "fuerza_interna": evidence["strength_points"],
                "urgencia_ventana": deadline_points,
                "evidencia_especifica": evidence["evidence_specific"],
                "penalizacion_elegibilidad": eligibility_penalty,
                "match_type": match_type,
                "missing_requirements": missing,
            }
            registry_rows.append({
                "convocatoria_id": _text(call.get("conv_id")),
                "titulo": _text(call.get("titulo")),
                "organismo": _text(call.get("organismo")),
                "categoria": _text(call.get("categoria")),
                "estado": _text(call.get("estado")),
                "perfil_objetivo": call_profile,
                "perfil_id": _text(rule.get("perfil_id")),
                "owner_unit": owner_unit,
                "relevancia_cchen": _text(call.get("relevancia_cchen")),
                "es_oficial": _bool(call.get("es_oficial")),
                "postulable": _bool(call.get("postulable")),
                "apertura_iso": _text(call.get("apertura_iso")),
                "cierre_iso": _text(call.get("cierre_iso")),
                "url": _text(call.get("url")),
                "last_evaluated_at": date.today().isoformat(),
            })
            match_rows.append({
                "conv_id": _text(call.get("conv_id")),
                "convocatoria_titulo": _text(call.get("titulo")),
                "estado": _text(call.get("estado")),
                "categoria": _text(call.get("categoria")),
                "organismo": _text(call.get("organismo")),
                "perfil_objetivo": call_profile,
                "perfil_id": _text(rule.get("perfil_id")),
                "perfil_nombre": _text(profile.get("perfil_nombre")),
                "owner_unit": owner_unit,
                "score_total": score_total,
                "score_breakdown": json.dumps(breakdown, ensure_ascii=False),
                "eligibility_status": eligibility_status,
                "readiness_status": readiness,
                "recommended_action": recommended,
                "deadline_class": deadline_class,
                "evidence_summary": evidence["summary"],
                "url": _text(call.get("url")),
                "relevancia_cchen": _text(call.get("relevancia_cchen")),
                "apertura_iso": _text(call.get("apertura_iso")),
                "cierre_iso": _text(call.get("cierre_iso")),
                "match_type": match_type,
                "last_evaluated_at": date.today().isoformat(),
            })

        if not matched_any:
            registry_rows.append({
                "convocatoria_id": _text(call.get("conv_id")),
                "titulo": _text(call.get("titulo")),
                "organismo": _text(call.get("organismo")),
                "categoria": _text(call.get("categoria")),
                "estado": _text(call.get("estado")),
                "perfil_objetivo": call_profile,
                "perfil_id": "",
                "owner_unit": "Observatorio",
                "relevancia_cchen": _text(call.get("relevancia_cchen")),
                "es_oficial": _bool(call.get("es_oficial")),
                "postulable": _bool(call.get("postulable")),
                "apertura_iso": _text(call.get("apertura_iso")),
                "cierre_iso": _text(call.get("cierre_iso")),
                "url": _text(call.get("url")),
                "last_evaluated_at": date.today().isoformat(),
            })

    registry_df = pd.DataFrame(registry_rows).drop_duplicates(subset=["convocatoria_id", "perfil_id"])
    match_df = pd.DataFrame(match_rows).sort_values(["score_total", "estado", "cierre_iso", "apertura_iso"], ascending=[False, True, True, True], na_position="last")
    return registry_df, match_df


def build_entity_links(persons: pd.DataFrame, projects: pd.DataFrame, conv_registry: pd.DataFrame, anchor_id: str) -> pd.DataFrame:
    rows: list[dict] = []
    for _, row in persons.iterrows():
        if _text(row.get("institution_id")):
            rows.append({
                "origin_type": "persona",
                "origin_id": row["persona_id"],
                "relation": "afiliada_a",
                "target_type": "institucion",
                "target_id": row["institution_id"],
                "source_evidence": row["source_coverage"],
                "confidence": "alta" if row["is_cchen_investigator"] else "media",
            })
    for _, row in projects.iterrows():
        if _text(row.get("autor_persona_id")):
            rows.append({
                "origin_type": "proyecto",
                "origin_id": row["project_id"],
                "relation": "liderado_por",
                "target_type": "persona",
                "target_id": row["autor_persona_id"],
                "source_evidence": "ANID",
                "confidence": "media",
            })
        if _text(row.get("institucion_id")):
            rows.append({
                "origin_type": "proyecto",
                "origin_id": row["project_id"],
                "relation": "alojado_en",
                "target_type": "institucion",
                "target_id": row["institucion_id"],
                "source_evidence": "ANID",
                "confidence": "alta",
            })
    for _, row in conv_registry.iterrows():
        if anchor_id:
            rows.append({
                "origin_type": "convocatoria",
                "origin_id": row["convocatoria_id"],
                "relation": "relevante_para",
                "target_type": "institucion",
                "target_id": anchor_id,
                "source_evidence": "matching_institucional",
                "confidence": "media",
            })
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    return out.drop_duplicates()


def main() -> None:
    inputs = load_inputs()
    lookup, anchor_id = build_institution_lookup(inputs["ror"])
    persons = build_personas(inputs, lookup, anchor_id)
    projects = build_projects(inputs, persons, lookup, anchor_id)
    profiles, rules = load_profiles(inputs)
    conv_registry, matching = build_matching(inputs, persons, projects, profiles, rules)
    links = build_entity_links(persons, projects, conv_registry, anchor_id)

    for path in [OUT_PERSONAS, OUT_PROYECTOS, OUT_CONVOCATORIAS, OUT_LINKS, OUT_MATCHING]:
        path.parent.mkdir(parents=True, exist_ok=True)

    persons.to_csv(OUT_PERSONAS, index=False, encoding="utf-8-sig")
    projects.to_csv(OUT_PROYECTOS, index=False, encoding="utf-8-sig")
    conv_registry.to_csv(OUT_CONVOCATORIAS, index=False, encoding="utf-8-sig")
    links.to_csv(OUT_LINKS, index=False, encoding="utf-8-sig")
    matching.to_csv(OUT_MATCHING, index=False, encoding="utf-8-sig")

    print(f"[OK] Personas canónicas: {OUT_PERSONAS} ({len(persons)} filas)")
    print(f"[OK] Proyectos canónicos: {OUT_PROYECTOS} ({len(projects)} filas)")
    print(f"[OK] Convocatorias canónicas: {OUT_CONVOCATORIAS} ({len(conv_registry)} filas)")
    print(f"[OK] Enlaces entre entidades: {OUT_LINKS} ({len(links)} filas)")
    print(f"[OK] Matching institucional: {OUT_MATCHING} ({len(matching)} filas)")


if __name__ == "__main__":
    main()
