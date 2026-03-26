"""Tests for build_planta_orcid_exports script."""
from __future__ import annotations

import subprocess
from pathlib import Path

import pandas as pd


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "Scripts" / "build_planta_orcid_exports.py"


def test_build_planta_orcid_exports_generates_expected_files(tmp_path):
    padron_path = tmp_path / "padron.csv"
    orcid_path = tmp_path / "orcid.csv"
    out_dir = tmp_path / "out"

    padron = pd.DataFrame(
        [
            {
                "nombre_completo": "Ana Perez Soto",
                "grupo_investigacion": "METS",
                "vigente": True,
                "padron_estado": "formal",
                "fuente_validacion": "rrhh",
                "fecha_fuente": "2026-03-24",
                "observaciones": "",
            },
            {
                "nombre_completo": "Bruno Diaz",
                "grupo_investigacion": "P2MC",
                "vigente": True,
                "padron_estado": "formal",
                "fuente_validacion": "rrhh",
                "fecha_fuente": "2026-03-24",
                "observaciones": "",
            },
        ]
    )
    padron.to_csv(padron_path, index=False)

    orcid = pd.DataFrame(
        [
            {
                "orcid_id": "0000-0002-1825-0097",
                "orcid_profile_url": "https://orcid.org/0000-0002-1825-0097",
                "full_name": "Ana Perez Soto",
                "employers": "Comision Chilena de Energia Nuclear",
                "orcid_works_count": 3,
            }
        ]
    )
    orcid.to_csv(orcid_path, index=False)

    cmd = [
        "python",
        str(SCRIPT_PATH),
        "--padron-base",
        str(padron_path),
        "--orcid-csv",
        str(orcid_path),
        "--stamp",
        "2026-03-24",
        "--output-dir",
        str(out_dir),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stdout + "\n" + result.stderr

    actual = out_dir / "cchen_planta_estado_orcid_actual.csv"
    dated = out_dir / "cchen_planta_estado_orcid_2026-03-24.csv"
    gaps = out_dir / "cchen_planta_orcid_brechas_actual.csv"
    gaps_dated = out_dir / "cchen_planta_orcid_brechas_2026-03-24.csv"

    assert actual.exists()
    assert dated.exists()
    assert gaps.exists()
    assert gaps_dated.exists()

    df_actual = pd.read_csv(actual)
    df_gaps = pd.read_csv(gaps)

    assert len(df_actual) == 2
    assert {"estado_orcid", "estado_revision_manual", "orcid_id_valido"}.issubset(df_actual.columns)
    assert set(df_gaps["categoria_brecha"]).issubset({"sin_orcid", "revisar_employer", "revisar_nombre_grupo"})

    ana = df_actual[df_actual["nombre_completo"] == "Ana Perez Soto"].iloc[0]
    bruno = df_actual[df_actual["nombre_completo"] == "Bruno Diaz"].iloc[0]

    assert ana["estado_orcid"] in {"orcid_confirmado_cchen", "orcid_match_aproximado_cchen"}
    assert ana["orcid_id_valido"] is True or ana["orcid_id_valido"] == True
    assert bruno["estado_orcid"] == "sin_orcid_csv"
