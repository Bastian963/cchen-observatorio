#!/usr/bin/env python3
"""Build the canonical capital humano dataset from the internal Excel file."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import unicodedata
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "Data" / "Capital humano CCHEN" / "Alumnos, honorarios y investigador visitante.xlsx"
DEFAULT_OUTPUT_DIR = ROOT / "Data" / "Capital humano CCHEN" / "salida_dataset_maestro"

OUTPUT_COLUMNS = [
    "anio_hoja",
    "excel_row_number",
    "nombre",
    "inicio",
    "termino",
    "duracion_dias",
    "tutor",
    "centro_raw",
    "centro_norm",
    "tipo_raw",
    "tipo_norm",
    "ticchen_raw",
    "ticchen_norm",
    "observaciones_raw",
    "observaciones_texto",
    "observaciones_urls",
    "observaciones_url_principal",
    "objeto_contrato",
    "carrera",
    "universidad",
    "monto_contrato_raw",
    "monto_contrato_num",
    "ad_honorem",
    "monto_parseable",
    "informe_raw",
    "informe_texto",
    "informe_urls",
    "informe_url_principal",
    "flag_fechas_inconsistentes",
    "flag_obs_tiene_url",
    "flag_informe_tiene_url",
    "flag_tipo_fuera_catalogo",
    "flag_centro_fuera_catalogo",
    "flag_ticchen_fuera_catalogo",
    "flag_monto_no_parseable",
]

CENTRO_ALIASES = {
    "cefnem": "CEFNEN",
    "cefnen": "CEFNEN",
    "cinas": "CINAS",
    "cinasb": "CINASB",
    "ctnev": "CTNEV",
    "dgin": "DGIN",
    "dgin.": "DGIN",
    "dricn": "DRICN",
    "drtec": "DRTeC",
    "mets": "METS",
    "p2mc": "P2MC",
    "pec": "PEC",
    "rech": "RECH",
}

TIPO_ALIASES = {
    "acuerdo de estadia": "Acuerdo de estadia",
    "acuerdo de estadía": "Acuerdo de estadia",
    "honorarios": "Honorarios",
    "memorista": "Memorista",
    "practica profesional": "Practica profesional",
    "práctica profesional": "Practica profesional",
    "tesista": "Tesista",
}

TICCHEN_ALIASES = {
    "extension": "Extension",
    "extensión": "Extension",
    "lista": "Lista",
    "no solicitada": "No solicitada",
    "solicitada": "Solicitada",
    "virtual": "Virtual",
}

VALID_CENTROS = set(CENTRO_ALIASES.values())
VALID_TIPOS = set(TIPO_ALIASES.values())
VALID_TICCHEN = set(TICCHEN_ALIASES.values())
URL_RE = re.compile(r"https?://[^\s)>\"]+")


def _strip_accents(value: str) -> str:
    return "".join(
        char
        for char in unicodedata.normalize("NFKD", value)
        if not unicodedata.combining(char)
    )


def _norm_key(value: object) -> str:
    text = "" if pd.isna(value) else str(value)
    text = " ".join(text.replace("\xa0", " ").split()).strip().lower()
    return _strip_accents(text)


def _clean_text(value: object) -> str:
    if pd.isna(value):
        return ""
    return " ".join(str(value).replace("\xa0", " ").split()).strip()


def _optional_text(value: object) -> str | None:
    text = _clean_text(value)
    return text or None


def _normalize_centro(value: object) -> str | None:
    text = _clean_text(value)
    if not text:
        return None
    return CENTRO_ALIASES.get(_norm_key(text), text)


def _normalize_tipo(value: object) -> str | None:
    text = _clean_text(value)
    if not text:
        return None
    return TIPO_ALIASES.get(_norm_key(text), text)


def _normalize_ticchen(value: object) -> str | None:
    text = _clean_text(value)
    if not text:
        return None
    return TICCHEN_ALIASES.get(_norm_key(text), text)


def _date_iso(value: object) -> str | None:
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return None
    return parsed.date().isoformat()


def _duration_days(start: object, end: object) -> int | None:
    start_dt = pd.to_datetime(start, errors="coerce")
    end_dt = pd.to_datetime(end, errors="coerce")
    if pd.isna(start_dt) or pd.isna(end_dt):
        return None
    return int((end_dt.date() - start_dt.date()).days + 1)


def _extract_urls(value: object) -> list[str]:
    text = _clean_text(value)
    return [url.rstrip(".,;") for url in URL_RE.findall(text)]


def _remove_urls(value: object) -> str | None:
    text = _clean_text(value)
    if not text:
        return None
    text = URL_RE.sub("", text)
    text = " ".join(text.split()).strip()
    return text or None


def _parse_amount(value: object) -> tuple[float | None, bool, bool]:
    text = _clean_text(value)
    if not text:
        return None, False, True
    if "honorem" in _norm_key(text):
        return None, True, True
    digits = re.sub(r"[^\d]", "", text)
    if not digits:
        return None, False, False
    return float(int(digits)), False, True


def read_capital_humano_excel(path: Path) -> pd.DataFrame:
    xls = pd.ExcelFile(path)
    frames: list[pd.DataFrame] = []
    for sheet_name in xls.sheet_names:
        if not str(sheet_name).isdigit():
            continue
        frame = pd.read_excel(path, sheet_name=sheet_name, header=1, engine="openpyxl")
        frame = frame.dropna(how="all").dropna(axis=1, how="all").copy()
        frame["anio_hoja"] = int(sheet_name)
        # Header is row 2 in the workbook; pandas index 0 corresponds to Excel row 3.
        frame["excel_row_number"] = frame.index + 3
        frames.append(frame)
    if not frames:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)
    raw = pd.concat(frames, ignore_index=True)
    raw = raw[raw["Nombre"].notna() & raw["Nombre"].astype(str).str.strip().ne("")].copy()

    records: list[dict[str, object]] = []
    for _, row in raw.iterrows():
        observaciones_urls = _extract_urls(row.get("Observaciones"))
        informe_urls = _extract_urls(row.get("Informe"))
        amount_num, ad_honorem, amount_parseable = _parse_amount(row.get("Monto contrato"))
        start_iso = _date_iso(row.get("Inicio"))
        end_iso = _date_iso(row.get("Término"))
        duration = _duration_days(row.get("Inicio"), row.get("Término"))
        centro_norm = _normalize_centro(row.get("Centro"))
        tipo_norm = _normalize_tipo(row.get("Tipo"))
        ticchen_norm = _normalize_ticchen(row.get("Ticchen"))

        record = {
            "anio_hoja": int(row["anio_hoja"]),
            "excel_row_number": int(row["excel_row_number"]),
            "nombre": _clean_text(row.get("Nombre")),
            "inicio": start_iso,
            "termino": end_iso,
            "duracion_dias": duration,
            "tutor": _optional_text(row.get("Tutor")),
            "centro_raw": _optional_text(row.get("Centro")),
            "centro_norm": centro_norm,
            "tipo_raw": _optional_text(row.get("Tipo")),
            "tipo_norm": tipo_norm,
            "ticchen_raw": _optional_text(row.get("Ticchen")),
            "ticchen_norm": ticchen_norm,
            "observaciones_raw": _optional_text(row.get("Observaciones")),
            "observaciones_texto": _remove_urls(row.get("Observaciones")),
            "observaciones_urls": "; ".join(observaciones_urls) or None,
            "observaciones_url_principal": observaciones_urls[0] if observaciones_urls else None,
            "objeto_contrato": _optional_text(row.get("Objeto del contrato")),
            "carrera": _optional_text(row.get("Carrera")),
            "universidad": _optional_text(row.get("Universidad")),
            "monto_contrato_raw": _optional_text(row.get("Monto contrato")),
            "monto_contrato_num": amount_num,
            "ad_honorem": int(ad_honorem),
            "monto_parseable": int(amount_parseable),
            "informe_raw": _optional_text(row.get("Informe")),
            "informe_texto": _remove_urls(row.get("Informe")),
            "informe_urls": "; ".join(informe_urls) or None,
            "informe_url_principal": informe_urls[0] if informe_urls else None,
            "flag_fechas_inconsistentes": int(duration is not None and duration <= 0),
            "flag_obs_tiene_url": int(bool(observaciones_urls)),
            "flag_informe_tiene_url": int(bool(informe_urls)),
            "flag_tipo_fuera_catalogo": int(tipo_norm is not None and tipo_norm not in VALID_TIPOS),
            "flag_centro_fuera_catalogo": int(centro_norm is not None and centro_norm not in VALID_CENTROS),
            "flag_ticchen_fuera_catalogo": int(ticchen_norm is not None and ticchen_norm not in VALID_TICCHEN),
            "flag_monto_no_parseable": int(bool(_clean_text(row.get("Monto contrato"))) and not amount_parseable),
        }
        records.append(record)

    out = pd.DataFrame.from_records(records, columns=OUTPUT_COLUMNS)
    return out.sort_values(["anio_hoja", "excel_row_number"]).reset_index(drop=True)


def _pct(numerator: int | float, denominator: int | float) -> float:
    if not denominator:
        return 0.0
    return round(100 * float(numerator) / float(denominator), 2)


def _hhi(series: pd.Series) -> float:
    counts = series.dropna().astype(str).str.strip().replace("", pd.NA).dropna().value_counts()
    if counts.empty:
        return 0.0
    shares = counts / counts.sum()
    return round(float((shares**2).sum()), 4)


def _build_transitions(df: pd.DataFrame) -> pd.DataFrame:
    rows: list[tuple[str, str]] = []
    sortable = df.copy()
    sortable["_name_key"] = sortable["nombre"].map(_norm_key)
    sortable["_inicio"] = pd.to_datetime(sortable["inicio"], errors="coerce")
    for _, group in sortable.dropna(subset=["tipo_norm"]).sort_values("_inicio").groupby("_name_key"):
        types = [str(item) for item in group["tipo_norm"].tolist() if str(item).strip()]
        for current, next_type in zip(types, types[1:]):
            if current != next_type:
                rows.append((current, next_type))
    if not rows:
        return pd.DataFrame(columns=["tipo_origen", "tipo_destino", "transiciones", "porcentaje_total", "porcentaje_desde_origen"])
    trans = pd.DataFrame(rows, columns=["tipo_origen", "tipo_destino"])
    out = trans.value_counts(["tipo_origen", "tipo_destino"]).reset_index(name="transiciones")
    total = int(out["transiciones"].sum())
    origin_total = out.groupby("tipo_origen")["transiciones"].transform("sum")
    out["porcentaje_total"] = out["transiciones"].map(lambda value: _pct(value, total))
    out["porcentaje_desde_origen"] = [
        _pct(value, origin) for value, origin in zip(out["transiciones"], origin_total)
    ]
    return out.sort_values("transiciones", ascending=False).reset_index(drop=True)


def _semaforo(score: float) -> str:
    if score >= 70:
        return "VERDE"
    if score >= 45:
        return "AMARILLO"
    return "ROJO"


def _build_cumplimiento_centros(df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for centro, group in df.dropna(subset=["centro_norm"]).groupby("centro_norm"):
        registros = len(group)
        obs_pct = _pct(int(group["flag_obs_tiene_url"].sum()), registros)
        inf_pct = _pct(int(group["flag_informe_tiene_url"].sum()), registros)
        both_pct = _pct(int(((group["flag_obs_tiene_url"] == 1) & (group["flag_informe_tiene_url"] == 1)).sum()), registros)
        score = round(0.5 * obs_pct + 0.4 * inf_pct + 0.1 * both_pct, 2)
        rows.append(
            {
                "entidad": centro,
                "registros": registros,
                "personas_unicas": group["nombre"].nunique(),
                "obs_url_pct": obs_pct,
                "informe_url_pct": inf_pct,
                "ambas_url_pct": both_pct,
                "score_documental": score,
                "semaforo_documental": _semaforo(score),
            }
        )
    return pd.DataFrame(rows).sort_values(["score_documental", "registros"], ascending=[False, False])


def _build_summary(df: pd.DataFrame, transitions: pd.DataFrame, cumplimiento: pd.DataFrame) -> dict:
    starts = pd.to_datetime(df["inicio"], errors="coerce")
    ends = pd.to_datetime(df["termino"], errors="coerce")
    remunerated = df["monto_contrato_num"].notna()
    tipo_counts = df["tipo_norm"].value_counts()
    practica_names = set(df.loc[df["tipo_norm"].eq("Practica profesional"), "nombre"].map(_norm_key))
    memorista_names = set(df.loc[df["tipo_norm"].eq("Memorista"), "nombre"].map(_norm_key))
    tesista_names = set(df.loc[df["tipo_norm"].eq("Tesista"), "nombre"].map(_norm_key))
    honorarios_names = set(df.loc[df["tipo_norm"].eq("Honorarios"), "nombre"].map(_norm_key))
    top_transition = transitions.iloc[0].to_dict() if not transitions.empty else {}

    kpis = {
        "registros_totales": int(len(df)),
        "personas_unicas": int(df["nombre"].nunique()),
        "periodo": {
            "inicio": starts.min().date().isoformat() if starts.notna().any() else "",
            "fin": ends.max().date().isoformat() if ends.notna().any() else "",
        },
        "registros_por_anio": {str(k): int(v) for k, v in df["anio_hoja"].value_counts().sort_index().items()},
        "ad_honorem_pct": _pct(int(df["ad_honorem"].sum()), len(df)),
        "remunerado_pct": _pct(int(remunerated.sum()), len(df)),
        "sin_info_monto_pct": _pct(int(df["monto_contrato_raw"].isna().sum()), len(df)),
        "continuidad_2mas_anios_pct": _pct(
            int((df.groupby(df["nombre"].map(_norm_key))["anio_hoja"].nunique() >= 2).sum()),
            int(df["nombre"].map(_norm_key).nunique()),
        ),
        "trayectorias": {
            "personas_con_progresion": int(df["nombre"].map(_norm_key).duplicated(keep=False).sum()),
            "personas_total": int(df["nombre"].nunique()),
            "personas_con_progresion_pct": _pct(
                int((df.groupby(df["nombre"].map(_norm_key))["tipo_norm"].nunique() >= 2).sum()),
                int(df["nombre"].map(_norm_key).nunique()),
            ),
            "transicion_mas_frecuente": (
                f"{top_transition.get('tipo_origen')} -> {top_transition.get('tipo_destino')}"
                if top_transition else ""
            ),
            "transicion_mas_frecuente_n": int(top_transition.get("transiciones", 0) or 0),
            "funnel_practica_base": len(practica_names),
            "funnel_practica_to_memorista": len(practica_names & memorista_names),
            "funnel_practica_to_tesista": len(practica_names & tesista_names),
            "funnel_practica_to_honorarios": len(practica_names & honorarios_names),
            "funnel_practica_to_memorista_pct": _pct(len(practica_names & memorista_names), len(practica_names)),
            "funnel_practica_to_tesista_pct": _pct(len(practica_names & tesista_names), len(practica_names)),
            "funnel_practica_to_honorarios_pct": _pct(len(practica_names & honorarios_names), len(practica_names)),
        },
        "capacidad": {
            "top3_tutores_share_pct": _pct(int(df["tutor"].value_counts().head(3).sum()), len(df)),
            "top3_centros_share_pct": _pct(int(df["centro_norm"].value_counts().head(3).sum()), len(df)),
            "hhi_tutores": _hhi(df["tutor"]),
            "hhi_centros": _hhi(df["centro_norm"]),
        },
        "eficiencia": {
            "registros_remunerados": int(remunerated.sum()),
            "registros_totales": int(len(df)),
            "remunerados_pct": _pct(int(remunerated.sum()), len(df)),
            "monto_total": int(df["monto_contrato_num"].sum(skipna=True)),
            "monto_promedio": round(float(df["monto_contrato_num"].mean(skipna=True) or 0), 2),
            "monto_mediana": round(float(df["monto_contrato_num"].median(skipna=True) or 0), 2),
            "monto_min": int(df["monto_contrato_num"].min(skipna=True) or 0),
            "monto_max": int(df["monto_contrato_num"].max(skipna=True) or 0),
        },
        "cumplimiento": {
            "centros_total": int(cumplimiento["entidad"].nunique()) if not cumplimiento.empty else 0,
            "centros_rojo": int(cumplimiento["semaforo_documental"].eq("ROJO").sum()) if not cumplimiento.empty else 0,
            "tutores_total": int(df["tutor"].nunique()),
            "tutores_rojo": 0,
        },
        "calidad": {
            "missing_counts": {
                col: int(df[col].isna().sum())
                for col in ["inicio", "termino", "tipo_norm", "centro_norm", "tutor", "universidad", "carrera"]
            },
            "duration_invalid": int(df["flag_fechas_inconsistentes"].sum()),
            "duration_outlier_365": int((pd.to_numeric(df["duracion_dias"], errors="coerce") > 365).sum()),
            "potential_duplicate_name_pairs": int(df["nombre"].map(_norm_key).duplicated().sum()),
            "normalization_groups_universidad": int(df["universidad"].dropna().nunique()),
            "normalization_groups_carrera": int(df["carrera"].dropna().nunique()),
        },
    }
    return {"generated_at": dt.datetime.now().isoformat(timespec="seconds"), "kpis": kpis}


def write_outputs(df: pd.DataFrame, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    avanzado_dir = output_dir / "analisis_avanzado"
    avanzado_dir.mkdir(parents=True, exist_ok=True)
    basico_dir = output_dir / "analisis_capital_humano"
    basico_dir.mkdir(parents=True, exist_ok=True)

    dataset_path = output_dir / "dataset_maestro_limpio.csv"
    df.to_csv(dataset_path, index=False, encoding="utf-8-sig")

    transitions = _build_transitions(df)
    cumplimiento = _build_cumplimiento_centros(df)
    transitions.to_csv(avanzado_dir / "transiciones_modalidad.csv", index=False, encoding="utf-8-sig")
    cumplimiento.to_csv(avanzado_dir / "cumplimiento_documental_centros.csv", index=False, encoding="utf-8-sig")

    tipo_anio = (
        df.groupby(["anio_hoja", "tipo_norm"], dropna=False)
        .size()
        .reset_index(name="registros")
        .sort_values(["anio_hoja", "tipo_norm"])
    )
    tipo_anio.to_csv(basico_dir / "participacion_tipo_anio.csv", index=False, encoding="utf-8-sig")

    summary = _build_summary(df, transitions, cumplimiento)
    (output_dir / "resumen_ejecutivo.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    advanced = {
        "generated_at": summary["generated_at"],
        "input_csv": str(dataset_path),
        "general": {
            "registros_totales": summary["kpis"]["registros_totales"],
            "personas_unicas": summary["kpis"]["personas_unicas"],
            "periodo_min_inicio": summary["kpis"]["periodo"]["inicio"],
            "periodo_max_termino": summary["kpis"]["periodo"]["fin"],
        },
        **{key: summary["kpis"][key] for key in ["trayectorias", "capacidad", "eficiencia", "cumplimiento", "calidad"]},
    }
    (avanzado_dir / "resumen_analisis_avanzado.json").write_text(
        json.dumps(advanced, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / "resumen_dataset_maestro.json").write_text(
        json.dumps(
            {
                "generated_at": summary["generated_at"],
                "input_excel": str(DEFAULT_INPUT),
                "records": int(len(df)),
                "valid_people": int(df["nombre"].nunique()),
                "years": sorted(int(year) for year in df["anio_hoja"].dropna().unique()),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build capital humano canonical CSV from Excel.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.input.exists():
        raise SystemExit(f"[capital-humano] Excel no encontrado: {args.input}")
    df = read_capital_humano_excel(args.input)
    if df.empty:
        raise SystemExit("[capital-humano] No se encontraron registros validos.")
    write_outputs(df, args.output_dir)
    print(f"[capital-humano] OK: {len(df)} registros -> {args.output_dir / 'dataset_maestro_limpio.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
