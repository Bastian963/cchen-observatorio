#!/usr/bin/env python3
"""Genera exportables de planta con estado ORCID y brechas para dashboard/QA.

Entradas:
- Padron base (provisional o formal) con al menos nombre_completo y grupo_investigacion.
- CSV ORCID consolidado de investigadores.

Salidas:
- Data/Researchers/cchen_planta_estado_orcid_actual.csv
- Data/Researchers/cchen_planta_orcid_brechas_actual.csv
- (opcional) copias versionadas con fecha.
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import unicodedata
from pathlib import Path

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "Data" / "Researchers"


def _norm(text: object) -> str:
    value = "" if pd.isna(text) else str(text)
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = re.sub(r"[^a-zA-Z0-9]+", " ", value.lower())
    return " ".join(value.split())


def _valid_orcid(orcid_id: object) -> bool:
    if pd.isna(orcid_id):
        return False
    value = str(orcid_id).strip().upper()
    if not re.fullmatch(r"[0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{3}[0-9X]", value):
        return False
    digits = value.replace("-", "")
    total = 0
    for char in digits[:-1]:
        total = (total + int(char)) * 2
    remainder = total % 11
    result = (12 - remainder) % 11
    check = "X" if result == 10 else str(result)
    return check == digits[-1]


def _is_cchen_employer(text: object) -> bool:
    value = _norm(text)
    keys = ["cchen", "comision chilena", "chilean nuclear", "nuclear energy commission"]
    return any(key in value for key in keys)


def _infer_match_row(
    row: pd.Series,
    orcid_by_id: pd.DataFrame,
    orcid_by_name: pd.DataFrame,
) -> tuple[str, pd.Series | None]:
    mapped_id = row.get("orcid_id")
    if pd.notna(mapped_id) and mapped_id in orcid_by_id.index:
        return "match_por_id", orcid_by_id.loc[mapped_id]

    target = row["nombre_norm"]
    exact = orcid_by_name[orcid_by_name["name_norm"] == target]
    if len(exact) == 1:
        return "match_exacto", exact.iloc[0]

    target_tokens = set(target.split())
    if not target_tokens:
        return "sin_match", None

    def _score(name_norm: str) -> tuple[float, int]:
        tokens = set(str(name_norm).split())
        overlap = len(tokens & target_tokens)
        ratio = overlap / max(1, len(target_tokens))
        return ratio, overlap

    scored = orcid_by_name["name_norm"].map(_score)
    ratios = scored.map(lambda x: x[0])
    overlaps = scored.map(lambda x: x[1])
    # Evita falsos positivos por un solo apellido compartido.
    approx_mask = (ratios >= 0.67) & (overlaps >= 2)
    approx = orcid_by_name[approx_mask].copy()
    approx["_score"] = ratios[approx_mask]
    approx["_works_sort"] = pd.to_numeric(approx.get("orcid_works_count", 0), errors="coerce").fillna(-1)
    approx_cols = list(approx.columns)
    idx_score = approx_cols.index("_score")
    idx_works = approx_cols.index("_works_sort")
    approx_rows = list(approx.itertuples(index=False, name=None))
    approx_rows = sorted(
        approx_rows,
        key=lambda r: (
            float(r[idx_score]) if pd.notna(r[idx_score]) else 0.0,
            float(r[idx_works]) if pd.notna(r[idx_works]) else -1.0,
        ),
        reverse=True,
    )
    approx = pd.DataFrame(approx_rows, columns=approx_cols)
    if len(approx) == 1:
        return "match_aproximado", approx.iloc[0]
    return "sin_match", None


def _build_exports(padron: pd.DataFrame, orcid: pd.DataFrame) -> pd.DataFrame:
    padron = padron.copy()
    orcid = orcid.copy()

    if "nombre_completo" not in padron.columns:
        raise ValueError("El padron base debe incluir columna nombre_completo")
    if "grupo_investigacion" not in padron.columns:
        padron["grupo_investigacion"] = "No informado"
    if "vigente" not in padron.columns:
        padron["vigente"] = True
    if "padron_estado" not in padron.columns:
        padron["padron_estado"] = "provisional"
    if "fuente_validacion" not in padron.columns:
        padron["fuente_validacion"] = "padron_base"
    if "fecha_fuente" not in padron.columns:
        padron["fecha_fuente"] = dt.date.today().isoformat()
    if "observaciones" not in padron.columns:
        padron["observaciones"] = ""

    padron["nombre_norm"] = padron["nombre_completo"].map(_norm)

    orcid["orcid_id"] = orcid["orcid_id"].astype(str).str.strip()
    orcid["name_norm"] = orcid["full_name"].map(_norm)
    orcid["orcid_id_valido"] = orcid["orcid_id"].map(_valid_orcid)
    orcid["orcid_profile_url_valida"] = orcid.apply(
        lambda r: str(r.get("orcid_profile_url", "")).strip() == f"https://orcid.org/{r['orcid_id']}",
        axis=1,
    )
    if "employers" in orcid.columns:
        employer_series = orcid["employers"]
    else:
        employer_series = pd.Series([""] * len(orcid), index=orcid.index)
    orcid["employer_cchen_verificado"] = employer_series.map(_is_cchen_employer)

    by_id = orcid.set_index("orcid_id", drop=False)

    rows: list[dict] = []
    for _, row in padron.iterrows():
        match_status, match_row = _infer_match_row(row, by_id, orcid)
        out = row.to_dict()

        if match_row is None:
            out.update(
                {
                    "orcid_match_status": "sin_match",
                    "orcid_correspondencia_nombre": "sin_orcid",
                    "orcid_id": "",
                    "orcid_full_name": "",
                    "orcid_id_valido": False,
                    "orcid_profile_url_valida": False,
                    "employer_cchen_verificado": False,
                    "orcid_works_count": None,
                    "orcid_employers_csv": "",
                    "estado_orcid": "sin_orcid_csv",
                    "estado_revision_manual": "pendiente_busqueda_orcid",
                    "revision_recomendada": "sin_orcid",
                }
            )
        else:
            original_tokens = set(str(row["nombre_norm"]).split())
            matched_tokens = set(str(match_row["name_norm"]).split())
            ratio = len(original_tokens & matched_tokens) / max(1, len(original_tokens))
            if ratio >= 0.95:
                correspondencia = "alta"
            elif ratio >= 0.5:
                correspondencia = "media"
            else:
                correspondencia = "baja"

            id_valido = bool(match_row["orcid_id_valido"])
            url_valida = bool(match_row["orcid_profile_url_valida"])
            employer_ok = bool(match_row["employer_cchen_verificado"])

            if id_valido and employer_ok and correspondencia == "alta" and match_status in {"match_exacto", "match_por_id"}:
                estado_orcid = "orcid_confirmado_cchen"
                estado_revision = "confirmado"
                revision = "ok"
            elif id_valido and employer_ok and match_status in {"match_aproximado", "match_por_id"}:
                estado_orcid = "orcid_match_aproximado_cchen"
                estado_revision = "revisar_nombre_grupo"
                revision = "revisar_match_aproximado"
            elif id_valido and not employer_ok:
                estado_orcid = "orcid_valido_sin_employer_cchen"
                estado_revision = "revisar_employer_en_orcid"
                revision = "revisar_employer"
            elif not id_valido:
                estado_orcid = "orcid_requiere_revision"
                estado_revision = "revisar_id_orcid"
                revision = "revisar_id"
            elif not url_valida:
                estado_orcid = "orcid_requiere_revision"
                estado_revision = "revisar_url_orcid"
                revision = "revisar_url"
            else:
                estado_orcid = "orcid_requiere_revision"
                estado_revision = "pendiente_revision"
                revision = "revisar_general"

            out.update(
                {
                    "orcid_match_status": match_status,
                    "orcid_correspondencia_nombre": correspondencia,
                    "orcid_id": match_row["orcid_id"],
                    "orcid_full_name": match_row.get("full_name", ""),
                    "orcid_id_valido": id_valido,
                    "orcid_profile_url_valida": url_valida,
                    "employer_cchen_verificado": employer_ok,
                    "orcid_works_count": match_row.get("orcid_works_count"),
                    "orcid_employers_csv": match_row.get("employers", ""),
                    "estado_orcid": estado_orcid,
                    "estado_revision_manual": estado_revision,
                    "revision_recomendada": revision,
                }
            )

        rows.append(out)

    export = pd.DataFrame(rows)
    ordered_cols = [
        "nombre_completo",
        "grupo_investigacion",
        "vigente",
        "padron_estado",
        "estado_orcid",
        "estado_revision_manual",
        "orcid_match_status",
        "orcid_correspondencia_nombre",
        "orcid_id",
        "orcid_id_valido",
        "orcid_profile_url_valida",
        "employer_cchen_verificado",
        "orcid_works_count",
        "orcid_full_name",
        "orcid_employers_csv",
        "fuente_validacion",
        "fecha_fuente",
        "revision_recomendada",
        "observaciones",
    ]
    for col in ordered_cols:
        if col not in export.columns:
            export[col] = ""
    export = export[ordered_cols]
    idx_group = ordered_cols.index("grupo_investigacion")
    idx_name = ordered_cols.index("nombre_completo")
    export_rows = list(export.itertuples(index=False, name=None))
    export_rows = sorted(
        export_rows,
        key=lambda r: (str(r[idx_group]), str(r[idx_name])),
    )
    export = pd.DataFrame(export_rows, columns=ordered_cols)
    return export.reset_index(drop=True)


def _write_exports(export: pd.DataFrame, output_dir: Path, stamp: str) -> tuple[Path, Path, Path, Path, pd.DataFrame]:
    output_dir.mkdir(parents=True, exist_ok=True)

    actual_path = output_dir / "cchen_planta_estado_orcid_actual.csv"
    dated_path = output_dir / f"cchen_planta_estado_orcid_{stamp}.csv"

    brechas_mask = export["estado_revision_manual"].isin(
        ["pendiente_busqueda_orcid", "revisar_employer_en_orcid", "revisar_nombre_grupo"]
    )
    brechas: pd.DataFrame = export.loc[brechas_mask, :].copy()
    if not brechas.empty:
        brechas["categoria_brecha"] = brechas["estado_revision_manual"].map(
            {
                "pendiente_busqueda_orcid": "sin_orcid",
                "revisar_employer_en_orcid": "revisar_employer",
                "revisar_nombre_grupo": "revisar_nombre_grupo",
            }
        )
    else:
        brechas.loc[:, "categoria_brecha"] = pd.Series(dtype="object")

    brechas_actual_path = output_dir / "cchen_planta_orcid_brechas_actual.csv"
    brechas_dated_path = output_dir / f"cchen_planta_orcid_brechas_{stamp}.csv"

    export.to_csv(actual_path, index=False)
    export.to_csv(dated_path, index=False)
    brechas.to_csv(brechas_actual_path, index=False)
    brechas.to_csv(brechas_dated_path, index=False)
    return actual_path, dated_path, brechas_actual_path, brechas_dated_path, brechas


def main() -> int:
    parser = argparse.ArgumentParser(description="Genera exportables de planta con estado ORCID")
    parser.add_argument(
        "--padron-base",
        default=str(DATA_DIR / "cchen_padron_academicos_provisional_2026-02-18.csv"),
        help="CSV base de padron de investigadores/académicos",
    )
    parser.add_argument(
        "--orcid-csv",
        default=str(DATA_DIR / "cchen_researchers_orcid.csv"),
        help="CSV consolidado ORCID",
    )
    parser.add_argument(
        "--stamp",
        default=dt.date.today().isoformat(),
        help="Fecha para salidas versionadas (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DATA_DIR),
        help="Directorio de salida para exportables (default: Data/Researchers)",
    )
    args = parser.parse_args()

    padron_path = Path(args.padron_base)
    orcid_path = Path(args.orcid_csv)
    output_dir = Path(args.output_dir)

    if not padron_path.exists():
        print(f"[planta-orcid] FAIL - no existe padron base: {padron_path}")
        return 1
    if not orcid_path.exists():
        print(f"[planta-orcid] FAIL - no existe csv ORCID: {orcid_path}")
        return 1

    padron = pd.read_csv(padron_path)
    orcid = pd.read_csv(orcid_path)

    export = _build_exports(padron, orcid)
    actual_path, dated_path, brechas_actual_path, brechas_dated_path, brechas = _write_exports(
        export,
        output_dir,
        args.stamp,
    )

    print("[planta-orcid] OK")
    def _show(path: Path) -> str:
        try:
            return str(path.relative_to(REPO_ROOT))
        except Exception:
            return str(path)

    print(f"  - actual:  {_show(actual_path)} ({len(export)} filas)")
    print(f"  - dated:   {_show(dated_path)} ({len(export)} filas)")
    print(f"  - brechas: {_show(brechas_actual_path)} ({len(brechas)} filas)")
    print(f"  - brechas versionada: {_show(brechas_dated_path)} ({len(brechas)} filas)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
