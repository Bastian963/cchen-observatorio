#!/usr/bin/env python3
"""
Estandariza el financiamiento complementario del observatorio.

Une semillas curadas de CORFO e IAEA TC en un único dataset reproducible
con columnas operativas para gobernanza, matching y asistente.

Uso:
    cd /Users/bastianayalainostroza/Dropbox/CCHEN
    python3 Scripts/fetch_funding_plus.py
"""

from __future__ import annotations

import hashlib
from datetime import date
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "Data"
FUND = DATA / "Funding"

CORFO_SEED = FUND / "corfo_funding_seed.csv"
IAEA_SEED = FUND / "cchen_iaea_tc.csv"
LEGACY_FILE = FUND / "cchen_funding_complementario.csv"
OUT_FILE = FUND / "cchen_funding_complementario.csv"

OUTPUT_COLUMNS = [
    "funding_id",
    "fuente",
    "instrumento",
    "titulo",
    "anio",
    "investigador_principal",
    "institucion",
    "monto",
    "moneda",
    "estado",
    "programa",
    "url",
    "area_cchen",
    "elegibilidad_base",
    "source_confidence",
    "last_verified_at",
    "observaciones",
]


def _text(value: object) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return str(value).strip()


def _number(value: object):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip().replace("$", "").replace(".", "").replace(",", ".")
    if not text:
        return None
    try:
        number = float(text)
    except ValueError:
        return None
    if number.is_integer():
        return int(number)
    return number


def _build_id(parts: list[str]) -> str:
    base = " | ".join(_text(p).lower() for p in parts if _text(p))
    return "fund_" + hashlib.md5(base.encode("utf-8")).hexdigest()[:12]


def _infer_area(row: dict) -> str:
    # Une TODAS las columnas texto para mayor cobertura de keywords
    joined = " ".join(_text(v) for v in row.values() if isinstance(v, (str, float, int))).lower()
    if any(k in joined for k in ("security", "seguridad", "cooperaci", "tc project", "iaea tc")):
        return "Seguridad nuclear y cooperación técnica"
    if any(k in joined for k in ("observatorio", "vigilancia", "inteligencia", "bibliometr")):
        return "Inteligencia científica y tecnológica"
    if any(k in joined for k in ("litio", "material", "aleaci", "cerami", "polimer")):
        return "Materiales y procesos para aplicaciones nucleares"
    if any(k in joined for k in ("medicina nuclear", "radiofármac", "radioterapia", "diagnóstic", "imag")):
        return "Medicina nuclear y aplicaciones clínicas"
    if any(k in joined for k in ("reactor", "neutron", "fisi", "combustible nuclear")):
        return "Física de reactores y tecnología nuclear"
    return "Aplicaciones nucleares e innovación institucional"


def _coalesce(*values: object) -> str:
    for value in values:
        text = _text(value)
        if text:
            return text
    return ""


def _load_corfo_seed() -> pd.DataFrame:
    if not CORFO_SEED.exists():
        return pd.DataFrame(columns=OUTPUT_COLUMNS)
    df = pd.read_csv(CORFO_SEED).fillna("")
    rows = []
    for _, row in df.iterrows():
        rec = {col: _text(row.get(col)) for col in OUTPUT_COLUMNS if col != "monto"}
        rec["monto"] = _number(row.get("monto"))
        rec["funding_id"] = _build_id([row.get("fuente"), row.get("instrumento"), row.get("titulo"), row.get("anio")])
        rec["area_cchen"] = _coalesce(rec.get("area_cchen"), _infer_area(rec))
        rec["last_verified_at"] = _coalesce(rec.get("last_verified_at"), date.today().isoformat())
        rec["source_confidence"] = _coalesce(rec.get("source_confidence"), "manual_curated")
        rows.append(rec)
    return pd.DataFrame(rows, columns=OUTPUT_COLUMNS)


def _load_iaea_seed() -> pd.DataFrame:
    rows: list[dict] = []
    if IAEA_SEED.exists():
        iaea = pd.read_csv(IAEA_SEED).fillna("")
        for _, row in iaea.iterrows():
            title = _coalesce(row.get("titulo"), row.get("proyecto_tc"))
            if not title:
                continue
            rec = {
                "funding_id": _build_id(["IAEA", row.get("proyecto_tc"), title, row.get("anio")]),
                "fuente": _coalesce(row.get("fuente"), "IAEA TC"),
                "instrumento": "Technical Cooperation",
                "titulo": title,
                "anio": row.get("anio") or "",
                "investigador_principal": "",
                "institucion": "Comisión Chilena de Energía Nuclear",
                "monto": None,
                "moneda": "USD",
                "estado": _coalesce(row.get("estado"), "Activo"),
                "programa": "IAEA Technical Cooperation",
                "url": _coalesce(row.get("url"), "https://www.iaea.org"),
                "area_cchen": "Seguridad nuclear y cooperación técnica",
                "elegibilidad_base": "Cooperación técnica internacional con contraparte institucional y capacidades nucleares aplicadas.",
                "source_confidence": "manual_placeholder",
                "last_verified_at": date.today().isoformat(),
                "observaciones": _coalesce(row.get("observaciones"), "Completar código oficial, contraparte y monto."),
            }
            rows.append(rec)

    if not rows and LEGACY_FILE.exists():
        legacy = pd.read_csv(LEGACY_FILE).fillna("")
        legacy = legacy[legacy["fuente"].astype(str).str.contains("IAEA", case=False, na=False)]
        for _, row in legacy.iterrows():
            title = _coalesce(row.get("titulo"), row.get("programa"))
            if not title:
                continue
            rows.append({
                "funding_id": _build_id(["IAEA", title, row.get("anio")]),
                "fuente": _coalesce(row.get("fuente"), "IAEA TC"),
                "instrumento": "Technical Cooperation",
                "titulo": title,
                "anio": row.get("anio") or "",
                "investigador_principal": _text(row.get("investigador_principal")),
                "institucion": _coalesce(row.get("institucion"), "Comisión Chilena de Energía Nuclear"),
                "monto": _number(row.get("monto")),
                "moneda": _coalesce(row.get("moneda"), "USD"),
                "estado": _coalesce(row.get("estado"), "Activo"),
                "programa": _coalesce(row.get("programa"), "IAEA Technical Cooperation"),
                "url": _coalesce(row.get("url"), "https://www.iaea.org"),
                "area_cchen": "Seguridad nuclear y cooperación técnica",
                "elegibilidad_base": "Cooperación técnica internacional con contraparte institucional y capacidades nucleares aplicadas.",
                "source_confidence": "legacy_placeholder",
                "last_verified_at": date.today().isoformat(),
                "observaciones": _coalesce(row.get("observaciones"), "Migrado desde dataset legado."),
            })

    return pd.DataFrame(rows, columns=OUTPUT_COLUMNS)


def main() -> None:
    corfo = _load_corfo_seed()
    iaea = _load_iaea_seed()
    out = pd.concat([corfo, iaea], ignore_index=True)
    if out.empty:
        out = pd.DataFrame(columns=OUTPUT_COLUMNS)
    else:
        out["anio"] = pd.to_numeric(out["anio"], errors="coerce").astype("Int64")
        out["monto"] = pd.to_numeric(out["monto"], errors="coerce")
        out = out.drop_duplicates(subset=["funding_id"]).sort_values(["fuente", "anio", "titulo"], na_position="last")

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT_FILE, index=False, encoding="utf-8-sig")
    print(f"[OK] Financiamiento complementario curado: {OUT_FILE}")
    print(f"     Filas: {len(out)}")
    if not out.empty:
        print(f"     Fuentes: {', '.join(sorted(out['fuente'].dropna().astype(str).unique().tolist()))}")


if __name__ == "__main__":
    main()
