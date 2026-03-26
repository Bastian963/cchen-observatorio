#!/usr/bin/env python3
"""
Genera auto_stats.tex con \newcommand que reflejan el estado actual de los datos.

Lee los CSVs locales de Data/ y escribe Docs/reports/auto_stats.tex.
El .tex principal hace \input{auto_stats.tex} para usar estas macros.

Uso:
    cd /Users/bastianayalainostroza/Dropbox/CCHEN
    python3 Scripts/generar_stats_latex.py
"""

from __future__ import annotations

import re
import sys
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "Data"
PUB  = DATA / "Publications"
RES  = DATA / "Researchers"
ANID = DATA / "ANID"
INST = DATA / "Institutional"
VIG  = DATA / "Vigilancia"
OUT  = ROOT / "Docs" / "reports" / "auto_stats.tex"

MESES_ES = {
    1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
    5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
    9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre",
}


def _fmt(n: int) -> str:
    """Formatea número con separador de miles LaTeX: 8499 → 8{,}499."""
    s = f"{n:,}"
    return s.replace(",", "{,}")


def _load(path: Path, **read_kw) -> pd.DataFrame | None:
    if not path.exists():
        print(f"  [WARN] no encontrado: {path.relative_to(ROOT)}", file=sys.stderr)
        return None
    return pd.read_csv(path, **read_kw)


def compute_stats() -> dict[str, str]:
    stats: dict[str, str] = {}

    # -- Publicaciones OpenAlex --
    df = _load(PUB / "cchen_openalex_works.csv")
    stats["publications"] = _fmt(len(df)) if df is not None else "?"

    # -- Autorías --
    df = _load(PUB / "cchen_authorships_enriched.csv")
    stats["authorships"] = _fmt(len(df)) if df is not None else "?"

    # -- Papers citantes --
    df = _load(PUB / "cchen_citing_papers.csv")
    stats["citing"] = _fmt(len(df)) if df is not None else "?"

    # -- EuroPMC --
    df = _load(PUB / "cchen_europmc_works.csv")
    stats["europmc"] = _fmt(len(df)) if df is not None else "?"

    # -- Perfiles ORCID --
    df = _load(RES / "cchen_researchers_orcid.csv")
    stats["orcid"] = _fmt(len(df)) if df is not None else "?"

    # -- Proyectos ANID (solo tipo "Proyecto", excluye Informes Finales) --
    df = _load(ANID / "RepositorioAnid_con_monto.csv")
    if df is not None:
        n = int((df["tipo"] == "Proyecto").sum()) if "tipo" in df.columns else len(df)
        stats["anid"] = _fmt(n)
    else:
        stats["anid"] = "?"

    # -- Convenios nacionales --
    df = _load(INST / "clean_Convenios_suscritos_por_la_Com.csv")
    stats["convenios"] = _fmt(len(df)) if df is not None else "?"

    # -- Acuerdos internacionales (fila 2 = header real, filtrar por número) --
    df = _load(INST / "clean_Acuerdos_e_instrumentos_intern.csv", header=2)
    if df is not None:
        col0 = df.columns[0]
        mask = df[col0].notna() & df[col0].astype(str).str.strip().str.match(r"^\d+$")
        stats["acuerdos"] = _fmt(int(mask.sum()))
    else:
        stats["acuerdos"] = "?"

    # -- DOIs Unpaywall verificados --
    df = _load(PUB / "cchen_unpaywall_oa.csv")
    if df is not None:
        stats["unpaywall"] = _fmt(len(df))
        if "is_oa" in df.columns:
            pct = round(df["is_oa"].mean() * 100)
            stats["oa_pct"] = str(pct)
        else:
            stats["oa_pct"] = "?"
    else:
        stats["unpaywall"] = "?"
        stats["oa_pct"] = "?"

    # -- Embeddings pgvector --
    df = _load(PUB / "cchen_embeddings_meta.csv")
    stats["embeddings"] = _fmt(len(df)) if df is not None else "?"

    # -- Convocatorias curadas --
    df = _load(VIG / "convocatorias_curadas.csv")
    stats["convocatorias"] = _fmt(len(df)) if df is not None else "?"

    # -- Tópicos BERTopic --
    df = _load(PUB / "cchen_bertopic_topic_info.csv")
    stats["bertopic"] = _fmt(len(df)) if df is not None else "?"

    # -- Fecha de generación --
    hoy = date.today()
    stats["fecha"] = f"{MESES_ES[hoy.month].capitalize()} {hoy.year}"
    stats["fecha_iso"] = hoy.isoformat()

    return stats


def write_tex(stats: dict[str, str]) -> None:
    lines = [
        "%% ============================================================",
        "%%  auto_stats.tex — GENERADO AUTOMÁTICAMENTE por generar_stats_latex.py",
        f"%%  Última actualización: {stats['fecha_iso']}",
        "%%  NO editar manualmente — se sobreescribe en cada ejecución.",
        "%% ============================================================",
        "",
        "%% --- Publicaciones y corpus ---",
        f"\\newcommand{{\\StatPublications}}{{{stats['publications']}}}",
        f"\\newcommand{{\\StatAuthorias}}{{{stats['authorships']}}}",
        f"\\newcommand{{\\StatCiting}}{{{stats['citing']}}}",
        f"\\newcommand{{\\StatEuropmc}}{{{stats['europmc']}}}",
        f"\\newcommand{{\\StatEmbeddings}}{{{stats['embeddings']}}}",
        "",
        "%% --- Capital humano e institucional ---",
        f"\\newcommand{{\\StatOrcid}}{{{stats['orcid']}}}",
        f"\\newcommand{{\\StatAnid}}{{{stats['anid']}}}",
        f"\\newcommand{{\\StatConvenios}}{{{stats['convenios']}}}",
        f"\\newcommand{{\\StatAcuerdos}}{{{stats['acuerdos']}}}",
        "",
        "%% --- Acceso abierto ---",
        f"\\newcommand{{\\StatUnpaywall}}{{{stats['unpaywall']}}}",
        f"\\newcommand{{\\StatOApct}}{{{stats['oa_pct']}}}",
        "",
        "%% --- Vigilancia tecnológica ---",
        f"\\newcommand{{\\StatConvocatorias}}{{{stats['convocatorias']}}}",
        f"\\newcommand{{\\StatBertopic}}{{{stats['bertopic']}}}",
        "",
        "%% --- Fecha del documento ---",
        f"\\newcommand{{\\StatFecha}}{{{stats['fecha']}}}",
        "",
    ]
    OUT.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    print("Calculando estadísticas desde CSVs locales...")
    stats = compute_stats()

    print("\nResumen:")
    for k, v in stats.items():
        print(f"  {k:20s} = {v}")

    write_tex(stats)
    print(f"\n✓ Generado: {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
