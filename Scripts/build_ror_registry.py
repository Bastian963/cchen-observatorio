#!/usr/bin/env python3
"""
Construye un registro institucional ROR para el Observatorio CCHEN
combinando evidencia local de OpenAlex authorships, ORCID y convenios.

Uso:
    cd /Users/bastianayalainostroza/Dropbox/CCHEN
    python3 Scripts/build_ror_registry.py
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "Data"
PUB = DATA / "Publications"
RES = DATA / "Researchers"
INST = DATA / "Institutional"

AUTH_FILE = PUB / "cchen_authorships_enriched.csv"
ORCID_FILE = RES / "cchen_researchers_orcid.csv"
CONVENIOS_FILE = INST / "clean_Convenios_suscritos_por_la_Com.csv"
SEED_FILE = INST / "ror_seed_institutions.csv"
ALIASES_FILE = INST / "ror_manual_aliases.csv"
OUTPUT_FILE = INST / "cchen_institution_registry.csv"
PENDING_REVIEW_FILE = INST / "ror_pending_review.csv"


def _normalize_name(value: object) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = str(value).strip()
    if not text:
        return ""
    text = (
        unicodedata.normalize("NFKD", text)
        .encode("ascii", "ignore")
        .decode("ascii")
        .lower()
    )
    text = re.sub(r"[^a-z0-9]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _split_multi(value: object) -> list[str]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return []
    return [chunk.strip() for chunk in str(value).split(";") if chunk.strip()]


def _empty_record(key: str, canonical_name: str) -> dict:
    return {
        "canonical_name": canonical_name,
        "normalized_key": key,
        "ror_id": None,
        "openalex_institution_id": None,
        "organization_type": None,
        "city": None,
        "country_name": None,
        "country_code": None,
        "website": None,
        "grid_id": None,
        "isni": None,
        "aliases_observed": set(),
        "authorships_count": 0,
        "orcid_profiles_count": 0,
        "convenios_count": 0,
        "is_cchen_anchor": False,
        "match_status": "observed_without_ror",
        "source_evidence": set(),
        "ror_record_last_modified": None,
    }


def _load_seed() -> pd.DataFrame:
    if not SEED_FILE.exists():
        return pd.DataFrame()
    df = pd.read_csv(SEED_FILE)
    if "normalized_key" not in df.columns:
        df["normalized_key"] = df["canonical_name"].map(_normalize_name)
    return df


def _load_aliases() -> pd.DataFrame:
    if not ALIASES_FILE.exists():
        return pd.DataFrame()
    df = pd.read_csv(ALIASES_FILE)
    required = {"observed_name", "target_canonical_name"}
    if not required.issubset(set(df.columns)):
        raise ValueError(
            f"El archivo de aliases manuales debe incluir {sorted(required)}: {ALIASES_FILE}"
        )
    return df.fillna("")


def _resolve_key(name: str, alias_to_key: dict[str, str], records: dict[str, dict], ror_id: str | None = None) -> str:
    norm = _normalize_name(name)
    if not norm:
        return ""
    if norm in alias_to_key:
        return alias_to_key[norm]
    if ror_id:
        for key, record in records.items():
            if record.get("ror_id") == ror_id:
                return key
    return norm


def build_registry() -> pd.DataFrame:
    seed_df = _load_seed()
    aliases_df = _load_aliases()
    records: dict[str, dict] = {}
    alias_to_key: dict[str, str] = {}

    for _, row in seed_df.iterrows():
        key = row["normalized_key"]
        record = _empty_record(key, row["canonical_name"])
        for field in [
            "ror_id", "organization_type", "city", "country_name", "country_code",
            "website", "grid_id", "isni", "ror_record_last_modified"
        ]:
            if field in row.index:
                record[field] = row[field]
        record["is_cchen_anchor"] = bool(row.get("is_cchen_anchor", False))
        record["match_status"] = "seed_verified"
        record["source_evidence"].add("seed")
        record["aliases_observed"].add(row["canonical_name"])
        for alias in _split_multi(row.get("aliases_seed")):
            record["aliases_observed"].add(alias)
            alias_to_key[_normalize_name(alias)] = key
        alias_to_key[key] = key
        records[key] = record

    for _, row in aliases_df.iterrows():
        observed = str(row["observed_name"]).strip()
        target_name = str(row["target_canonical_name"]).strip()
        if not observed or not target_name:
            continue
        observed_norm = _normalize_name(observed)
        target_norm = _normalize_name(target_name)
        if not observed_norm or not target_norm:
            continue
        alias_to_key[observed_norm] = target_norm
        if target_norm not in records:
            record = _empty_record(target_norm, target_name)
            if row.get("target_ror_id"):
                record["ror_id"] = row["target_ror_id"]
                record["match_status"] = "manual_alias_with_ror"
            if row.get("target_country_code"):
                record["country_code"] = row["target_country_code"]
            record["source_evidence"].add("manual_alias")
            record["aliases_observed"].add(target_name)
            records[target_norm] = record
        else:
            record = records[target_norm]
            if not record["canonical_name"]:
                record["canonical_name"] = target_name
            if row.get("target_ror_id") and not record.get("ror_id"):
                record["ror_id"] = row["target_ror_id"]
                record["match_status"] = "manual_alias_with_ror"
            if row.get("target_country_code") and not record.get("country_code"):
                record["country_code"] = row["target_country_code"]
            record["source_evidence"].add("manual_alias")
        records[target_norm]["aliases_observed"].add(observed)
        records[target_norm]["aliases_observed"].add(target_name)
        alias_to_key[target_norm] = target_norm

    if AUTH_FILE.exists():
        auth = pd.read_csv(
            AUTH_FILE,
            usecols=[
                "institution_name", "institution_country_code",
                "institution_ror", "institution_id",
            ],
        )
        auth_summary = (
            auth.dropna(subset=["institution_name"])
            .groupby(
                ["institution_name", "institution_country_code", "institution_ror", "institution_id"],
                dropna=False,
            )
            .size()
            .reset_index(name="n_authorships")
            .sort_values("n_authorships", ascending=False)
        )
        for _, row in auth_summary.iterrows():
            key = _resolve_key(row["institution_name"], alias_to_key, records, row["institution_ror"])
            if not key:
                continue
            record = records.get(key)
            if record is None:
                record = _empty_record(key, row["institution_name"])
                records[key] = record
            if not record["canonical_name"] or record["authorships_count"] == 0:
                record["canonical_name"] = row["institution_name"]
            record["aliases_observed"].add(row["institution_name"])
            alias_to_key[_normalize_name(row["institution_name"])] = key
            record["authorships_count"] += int(row["n_authorships"])
            record["source_evidence"].add("authorships")
            if pd.notna(row["institution_country_code"]) and not record["country_code"]:
                record["country_code"] = row["institution_country_code"]
            if pd.notna(row["institution_ror"]) and row["institution_ror"]:
                record["ror_id"] = row["institution_ror"]
                record["match_status"] = "observed_with_ror" if record["match_status"] != "seed_verified" else record["match_status"]
            if pd.notna(row["institution_id"]) and row["institution_id"] and not record["openalex_institution_id"]:
                record["openalex_institution_id"] = row["institution_id"]

    if ORCID_FILE.exists():
        orcid = pd.read_csv(ORCID_FILE, usecols=["employers"])
        employer_counter = Counter()
        for employers in orcid["employers"].dropna():
            for employer in _split_multi(employers):
                employer_counter[employer] += 1
        for employer, count in employer_counter.items():
            key = _resolve_key(employer, alias_to_key, records)
            if not key:
                continue
            record = records.get(key)
            if record is None:
                record = _empty_record(key, employer)
                records[key] = record
            record["aliases_observed"].add(employer)
            alias_to_key[_normalize_name(employer)] = key
            record["orcid_profiles_count"] += int(count)
            record["source_evidence"].add("orcid")

    if CONVENIOS_FILE.exists():
        convenios = pd.read_csv(CONVENIOS_FILE, encoding="utf-8", on_bad_lines="skip")
        convenios.columns = [str(c).strip() for c in convenios.columns]
        if "CONTRAPARTE DEL CONVENIO" in convenios.columns:
            counterpart_counter = (
                convenios["CONTRAPARTE DEL CONVENIO"].dropna().astype(str).str.strip().value_counts()
            )
            for counterpart, count in counterpart_counter.items():
                key = _resolve_key(counterpart, alias_to_key, records)
                if not key:
                    continue
                record = records.get(key)
                if record is None:
                    record = _empty_record(key, counterpart)
                    records[key] = record
                record["aliases_observed"].add(counterpart)
                alias_to_key[_normalize_name(counterpart)] = key
                record["convenios_count"] += int(count)
                record["source_evidence"].add("convenios")

    out_rows = []
    for key, record in records.items():
        if not record["canonical_name"]:
            continue
        if record["match_status"] == "observed_without_ror" and record["ror_id"]:
            record["match_status"] = "observed_with_ror"
        out_rows.append({
            "canonical_name": record["canonical_name"],
            "normalized_key": key,
            "ror_id": record["ror_id"],
            "openalex_institution_id": record["openalex_institution_id"],
            "organization_type": record["organization_type"],
            "city": record["city"],
            "country_name": record["country_name"],
            "country_code": record["country_code"],
            "website": record["website"],
            "grid_id": record["grid_id"],
            "isni": record["isni"],
            "aliases_observed": "; ".join(sorted(record["aliases_observed"])),
            "authorships_count": int(record["authorships_count"]),
            "orcid_profiles_count": int(record["orcid_profiles_count"]),
            "convenios_count": int(record["convenios_count"]),
            "is_cchen_anchor": bool(record["is_cchen_anchor"]),
            "match_status": record["match_status"],
            "source_evidence": "; ".join(sorted(record["source_evidence"])),
            "ror_record_last_modified": record["ror_record_last_modified"],
        })

    df = pd.DataFrame(out_rows)
    if df.empty:
        return df
    df = df.sort_values(
        ["is_cchen_anchor", "authorships_count", "orcid_profiles_count", "convenios_count", "canonical_name"],
        ascending=[False, False, False, False, True],
    ).reset_index(drop=True)
    return df


def _looks_chilean_or_public(name: str) -> bool:
    text = str(name).upper()
    keywords = [
        "CHILE", "COMISION", "COMISIÓN", "SERVICIO", "MINISTERIO", "MUNICIPALIDAD",
        "INTENDENCIA", "CARABINEROS", "POLIC", "BOMBEROS", "EJÉRCITO", "EJERCITO",
        "INSTITUTO", "HOSPITAL", "UNIVERSIDAD", "ACADEMIA", "EMPRESA NACIONAL",
        "SOCIEDAD NACIONAL", "DIRECCIÓN", "DIRECCION",
    ]
    return any(keyword in text for keyword in keywords)


def _classify_pending(row: pd.Series) -> tuple[str, str, bool, str]:
    name = str(row.get("canonical_name", ""))
    authorships = int(row.get("authorships_count", 0) or 0)
    orcid_profiles = int(row.get("orcid_profiles_count", 0) or 0)
    convenios = int(row.get("convenios_count", 0) or 0)
    signal = authorships + orcid_profiles + convenios
    is_local = _looks_chilean_or_public(name)

    if convenios >= 1 or is_local:
        return (
            "Media",
            "manual_selectivo",
            False,
            "Institución revisada manualmente y mantenida en cola selectiva de curaduría local.",
        )
    if authorships > 0 and not is_local:
        return (
            "Media",
            "api_candidate_future",
            True,
            "Institución observada en authorships sin ROR; conviene resolverla más adelante con búsqueda API focalizada.",
        )
    if orcid_profiles >= 2 and not is_local:
        return (
            "Media",
            "api_candidate_future",
            True,
            "Institución extranjera repetida en ORCID; se mantiene como candidato a automatización futura.",
        )
    if signal >= 1 and is_local:
        return (
            "Baja",
            "manual_selectivo",
            False,
            "Institución local o pública con señal limitada; queda en curaduría manual selectiva.",
        )
    return (
        "Baja",
        "api_candidate_future" if not is_local else "manual_selectivo",
        not is_local,
        "Caso de baja señal; se conserva en cola operativa para revisión futura sin elevarlo a prioridad alta.",
    )


def build_pending_review(registry_df: pd.DataFrame) -> pd.DataFrame:
    if registry_df is None or registry_df.empty:
        return pd.DataFrame()

    pending = registry_df[
        registry_df["ror_id"].isna() &
        (
            (registry_df["authorships_count"] > 0) |
            (registry_df["orcid_profiles_count"] > 0) |
            (registry_df["convenios_count"] > 0)
        )
    ].copy()
    if pending.empty:
        return pending

    pending["signal_total"] = (
        pending["authorships_count"].fillna(0).astype(int) +
        pending["orcid_profiles_count"].fillna(0).astype(int) +
        pending["convenios_count"].fillna(0).astype(int)
    )
    classes = pending.apply(_classify_pending, axis=1, result_type="expand")
    classes.columns = ["priority_level", "recommended_resolution", "api_candidate", "rationale"]
    pending = pd.concat([pending.reset_index(drop=True), classes.reset_index(drop=True)], axis=1)
    priority_order = {"Alta": 3, "Media": 2, "Baja": 1}
    pending["priority_rank"] = pending["priority_level"].map(priority_order).fillna(0).astype(int)
    pending = pending.sort_values(
        ["priority_rank", "signal_total", "authorships_count", "convenios_count", "orcid_profiles_count", "canonical_name"],
        ascending=[False, False, False, False, False, True],
    ).reset_index(drop=True)
    return pending[[
        "canonical_name", "authorships_count", "orcid_profiles_count", "convenios_count",
        "signal_total", "source_evidence", "priority_level", "recommended_resolution",
        "api_candidate", "rationale", "aliases_observed",
    ]]


def main() -> None:
    df = build_registry()
    pending_df = build_pending_review(df)
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_FILE, index=False)
    pending_df.to_csv(PENDING_REVIEW_FILE, index=False)
    print(f"[OK] Registro ROR generado: {OUTPUT_FILE}")
    print(f"     Filas: {len(df)}")
    if not df.empty:
        with_ror = int(df["ror_id"].notna().sum())
        print(f"     Instituciones con ROR: {with_ror}")
        print(f"     CCHEN ancla: {int(df['is_cchen_anchor'].sum())}")
    print(f"[OK] Cola de revisión ROR: {PENDING_REVIEW_FILE}")
    print(f"     Pendientes priorizados: {len(pending_df)}")


if __name__ == "__main__":
    main()
