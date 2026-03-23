"""
data_quality.py — Observatorio CCHEN 360°
==========================================
Verifica la calidad e integridad de todos los archivos de datos locales.
Genera un reporte en consola y (opcionalmente) en CSV.

USO:
    cd /Users/bastianayalainostroza/Dropbox/CCHEN
    python Database/data_quality.py
    python Database/data_quality.py --output Docs/reports/calidad_datos.csv

CHECKS POR TABLA:
    - Existencia del archivo CSV
    - Filas totales y sin duplicados
    - Columnas clave presentes (no nulas por encima del umbral)
    - Rangos válidos (años, montos)
    - Consistencia entre tablas (ej. autorías → publicaciones)
"""

import argparse
import csv
import datetime
import os
import warnings
from pathlib import Path

import pandas as pd

warnings.filterwarnings("ignore")

# ─── Catálogos de valores permitidos ──────────────────────────────────────────
# Valores válidos para ror_pending_review.recommended_resolution.
# Agregar aquí si se incorpora un nuevo tipo sin modificar la lógica de checks.
ALLOWED_ROR_RESOLUTIONS: frozenset[str] = frozenset({
    "manual_selectivo",
    "api_candidate_future",
    "confirmed_cchen",
    "confirmed_external",
    "discard",
})

# ─── Rutas ────────────────────────────────────────────────────────────────────

ROOT     = Path(__file__).parent.parent
DATA     = ROOT / "Data"
PUB      = DATA / "Publications"
ANID_DIR = DATA / "ANID"
INST_DIR = DATA / "Institutional"
RES_DIR  = DATA / "Researchers"
FUND_DIR = DATA / "Funding"
CH_DIR   = DATA / "Capital humano CCHEN" / "salida_dataset_maestro"
GOV_DIR  = DATA / "Gobernanza"

# ─── Frescura de datos ────────────────────────────────────────────────────────
# Días máximos permitidos sin actualizar (umbral de alerta)

VIG_DIR = DATA / "Vigilancia"

STALENESS_BUDGET: dict[Path, int] = {
    PUB / "cchen_openalex_works.csv":                     90,   # trimestral
    PUB / "cchen_authorships_enriched.csv":               90,
    PUB / "cchen_crossref_enriched.csv":                  90,
    PUB / "cchen_openalex_concepts.csv":                  90,
    RES_DIR / "cchen_researchers_orcid.csv":             180,   # semestral
    VIG_DIR / "arxiv_monitor.csv":                         8,   # semanal (+1 día margen)
    VIG_DIR / "news_monitor.csv":                          8,
    VIG_DIR / "convocatorias_curadas.csv":                 8,
    VIG_DIR / "convocatorias_matching_institucional.csv":  8,
    INST_DIR / "clean_Convenios_suscritos_por_la_Com.csv": 180,
    INST_DIR / "clean_Acuerdos_e_instrumentos_intern.csv": 180,
    INST_DIR / "cchen_institution_registry.csv":          180,
    INST_DIR / "ror_pending_review.csv":                  180,
    FUND_DIR / "cchen_funding_complementario.csv":        180,
    GOV_DIR / "entity_registry_personas.csv":              14,
    GOV_DIR / "entity_registry_proyectos.csv":             14,
    GOV_DIR / "entity_registry_convocatorias.csv":         14,
    GOV_DIR / "entity_links.csv":                          14,
}

# ─── Resultados ───────────────────────────────────────────────────────────────

RESULTS: list[dict] = []


def check(
    name: str,
    path: Path,
    pk: str = None,
    required_cols: list[str] = None,
    year_col: str = None,
    year_min: int = 1980,
    year_max: int = 2026,
    completeness_threshold: float = 0.50,   # mínimo 50% no-nulo en columnas clave
    read_kwargs: dict = None,
):
    """
    Ejecuta una batería de checks sobre un archivo CSV.
    Agrega los resultados a RESULTS.
    """
    row = {
        "fuente": name,
        "archivo": str(path.relative_to(ROOT)),
        "existe": False,
        "filas": 0,
        "duplicados": 0,
        "cols_faltantes": "",
        "completeness_min": "",
        "year_fuera_rango": 0,
        "alertas": [],
        "estado": "OK",
    }

    if not path.exists():
        row["alertas"].append("ARCHIVO NO ENCONTRADO")
        row["estado"] = "CRITICO"
        RESULTS.append(row)
        _print_row(row)
        return

    row["existe"] = True
    rk = read_kwargs or {}
    try:
        df = pd.read_csv(path, **rk)
    except Exception as e:
        if isinstance(e, pd.errors.EmptyDataError):
            row["alertas"].append("Archivo CSV vacío")
            row["estado"] = "ADVERTENCIA"
            RESULTS.append(row)
            _print_row(row)
            return
        row["alertas"].append(f"Error de lectura: {e}")
        row["estado"] = "CRITICO"
        RESULTS.append(row)
        _print_row(row)
        return

    row["filas"] = len(df)

    # Duplicados en PK
    if pk and pk in df.columns:
        dups = df[pk].dropna().duplicated().sum()
        row["duplicados"] = int(dups)
        if dups > 0:
            row["alertas"].append(f"{dups} duplicados en '{pk}'")

    # Columnas requeridas presentes
    required_cols = required_cols or []
    missing = [c for c in required_cols if c not in df.columns]
    row["cols_faltantes"] = ", ".join(missing)
    if missing:
        row["alertas"].append(f"Columnas faltantes: {missing}")

    # Completeness de columnas clave
    present = [c for c in required_cols if c in df.columns]
    if present and len(df) > 0:
        rates = {c: df[c].notna().mean() for c in present}
        min_rate = min(rates.values())
        min_col  = min(rates, key=rates.get)
        row["completeness_min"] = f"{min_col}: {min_rate:.0%}"
        if min_rate < completeness_threshold:
            row["alertas"].append(
                f"Baja completeness en '{min_col}': {min_rate:.0%} "
                f"(umbral: {completeness_threshold:.0%})"
            )

    # Rango de años
    if year_col and year_col in df.columns:
        years = pd.to_numeric(df[year_col], errors="coerce").dropna()
        fuera = ((years < year_min) | (years > year_max)).sum()
        row["year_fuera_rango"] = int(fuera)
        if fuera > 0:
            row["alertas"].append(
                f"{fuera} filas con año fuera de [{year_min}, {year_max}]"
            )

    # Estado final
    if any("CRITICO" in a or "ARCHIVO" in a or "Baja completeness" in a for a in row["alertas"]):
        row["estado"] = "ADVERTENCIA"
    if row["filas"] == 0:
        row["estado"] = "ADVERTENCIA"
        row["alertas"].append("Archivo vacío (0 filas)")

    RESULTS.append(row)
    _print_row(row)


def _print_row(row: dict):
    estado_icon = {"OK": "✓", "ADVERTENCIA": "⚠", "CRITICO": "✗"}.get(row["estado"], "?")
    alertas_str = "; ".join(row["alertas"]) if row["alertas"] else "—"
    print(
        f"  [{estado_icon}] {row['fuente']:<35} "
        f"filas={row['filas']:>6}  "
        f"dups={row['duplicados']:>4}  "
        f"estado={row['estado']:<11} "
        f"alertas: {alertas_str}"
    )


def check_cross_integrity():
    """Verifica que work_ids en authorships y concepts existan en publications."""
    pub_path = PUB / "cchen_openalex_works.csv"
    aut_path = PUB / "cchen_authorships_enriched.csv"
    con_path = PUB / "cchen_openalex_concepts.csv"

    if not all(p.exists() for p in [pub_path, aut_path]):
        return

    pub_ids = set(pd.read_csv(pub_path)["openalex_id"].dropna())
    aut     = pd.read_csv(aut_path)
    aut_orphans = aut["work_id"].dropna()[~aut["work_id"].isin(pub_ids)].nunique()
    row = {
        "fuente": "INTEGRIDAD: authorships → publications",
        "archivo": "Publications/*",
        "existe": True, "filas": len(aut), "duplicados": 0,
        "cols_faltantes": "", "completeness_min": "",
        "year_fuera_rango": 0,
        "alertas": [],
        "estado": "OK",
    }
    if aut_orphans:
        row["alertas"].append(f"{aut_orphans} work_ids huérfanos en authorships")
        row["estado"] = "ADVERTENCIA"
    RESULTS.append(row)
    _print_row(row)

    if con_path.exists():
        con = pd.read_csv(con_path)
        con_orphans = con["work_id"].dropna()[~con["work_id"].isin(pub_ids)].nunique()
        row2 = {
            "fuente": "INTEGRIDAD: concepts → publications",
            "archivo": "Publications/*",
            "existe": True, "filas": len(con), "duplicados": 0,
            "cols_faltantes": "", "completeness_min": "",
            "year_fuera_rango": 0,
            "alertas": [],
            "estado": "OK",
        }
        if con_orphans:
            row2["alertas"].append(f"{con_orphans} work_ids huérfanos en concepts")
            row2["estado"] = "ADVERTENCIA"
        RESULTS.append(row2)
        _print_row(row2)


def check_staleness() -> list[str]:
    """Verifica la frescura de archivos críticos según su frecuencia de actualización esperada."""
    now = datetime.datetime.now()
    stale: list[str] = []
    for path, max_days in STALENESS_BUDGET.items():
        if not path.exists():
            continue
        age_days = (now - datetime.datetime.fromtimestamp(path.stat().st_mtime)).days
        label = str(path.relative_to(ROOT))
        if age_days > max_days:
            stale.append(label)
            print(f"  [⚠] DESACTUALIZADO  {label:<55} {age_days:>4} días (máx {max_days})")
        else:
            print(f"  [✓] Vigente         {label:<55} {age_days:>4} días (máx {max_days})")

    if stale:
        RESULTS.append({
            "fuente": f"FRESCURA: {len(stale)} archivo(s) desactualizado(s)",
            "archivo": "; ".join(stale),
            "existe": True, "filas": 0, "duplicados": 0,
            "cols_faltantes": "", "completeness_min": "",
            "year_fuera_rango": 0,
            "alertas": [f"Desactualizado: {f}" for f in stale],
            "estado": "ADVERTENCIA",
        })
    return stale


def _append_custom_result(name: str, path: Path, rows: int, alerts: list[str], state: str = "OK"):
    row = {
        "fuente": name,
        "archivo": str(path.relative_to(ROOT)) if path.exists() else str(path),
        "existe": path.exists(),
        "filas": rows,
        "duplicados": 0,
        "cols_faltantes": "",
        "completeness_min": "",
        "year_fuera_rango": 0,
        "alertas": alerts,
        "estado": state if alerts else "OK",
    }
    RESULTS.append(row)
    _print_row(row)


def check_ror_operational_state():
    """Verifica que la cola ROR operativa no mantenga prioridades obsoletas."""
    path = INST_DIR / "ror_pending_review.csv"
    if not path.exists():
        return
    df = pd.read_csv(path)
    alerts: list[str] = []
    alta = int(df["priority_level"].fillna("").eq("Alta").sum()) if "priority_level" in df.columns else 0
    if alta > 0:
        alerts.append(f"{alta} filas siguen con priority_level='Alta'")
    if "recommended_resolution" in df.columns:
        invalid = sorted(set(df["recommended_resolution"].dropna()) - ALLOWED_ROR_RESOLUTIONS)
        if invalid:
            alerts.append(f"recommended_resolution fuera de catálogo: {invalid}")
    _append_custom_result(
        "ROR pending review operativo",
        path,
        len(df),
        alerts,
        "ADVERTENCIA" if alerts else "OK",
    )


def check_funding_operational_coverage():
    """Verifica presencia mínima de CORFO e IAEA en funding curado."""
    path = FUND_DIR / "cchen_funding_complementario.csv"
    if not path.exists():
        return
    df = pd.read_csv(path)
    alerts: list[str] = []
    fuentes = {str(v).upper() for v in df.get("fuente", pd.Series(dtype=str)).dropna()}
    if not any("CORFO" in f for f in fuentes):
        alerts.append("No hay registros CORFO en funding complementario")
    if not any("IAEA" in f for f in fuentes):
        alerts.append("No hay registros IAEA en funding complementario")
    if "source_confidence" in df.columns and df["source_confidence"].isna().any():
        alerts.append("Hay filas sin source_confidence")
    if "last_verified_at" in df.columns and df["last_verified_at"].isna().any():
        alerts.append("Hay filas sin last_verified_at")
    _append_custom_result(
        "Funding complementario operativo",
        path,
        len(df),
        alerts,
        "ADVERTENCIA" if alerts else "OK",
    )


def check_matching_coverage():
    """Verifica que todas las convocatorias abiertas o próximas tengan matching formal."""
    conv_path = VIG_DIR / "convocatorias_curadas.csv"
    match_path = VIG_DIR / "convocatorias_matching_institucional.csv"
    if not conv_path.exists() or not match_path.exists():
        return
    conv = pd.read_csv(conv_path)
    match = pd.read_csv(match_path)
    if "tipo_registro" in conv.columns:
        conv = conv[conv["tipo_registro"].fillna("").eq("convocatoria")]
    if "estado" in conv.columns:
        conv = conv[conv["estado"].isin(["Abierto", "Próximo"])]
    conv_ids = set(conv["conv_id"].dropna()) if "conv_id" in conv.columns else set()
    matched = set(match["conv_id"].dropna()) if "conv_id" in match.columns else set()
    missing = sorted(conv_ids - matched)
    alerts = [f"Convocatorias abiertas/próximas sin matching: {missing[:8]}"] if missing else []
    _append_custom_result(
        "Cobertura matching convocatorias",
        match_path,
        len(match),
        alerts,
        "ADVERTENCIA" if alerts else "OK",
    )


def check_entity_links_integrity():
    """Verifica que los enlaces apunten a entidades conocidas cuando exista registro canónico."""
    links_path = GOV_DIR / "entity_links.csv"
    if not links_path.exists():
        return
    links = pd.read_csv(links_path)

    # Cargar todos los registros una sola vez (fuera del loop — evita re-lecturas)
    inst_registry_path = INST_DIR / "cchen_institution_registry.csv"
    institution_ids: set = set()
    if inst_registry_path.exists():
        inst_df = pd.read_csv(inst_registry_path)
        for col in ("ror_id", "normalized_key"):
            if col in inst_df.columns:
                institution_ids.update(inst_df[col].dropna())

    def _load_ids(fname: str, id_col: str) -> set:
        p = GOV_DIR / fname
        if not p.exists():
            return set()
        return set(pd.read_csv(p)[id_col].dropna())

    registries = {
        "persona":      _load_ids("entity_registry_personas.csv",      "persona_id"),
        "proyecto":     _load_ids("entity_registry_proyectos.csv",      "project_id"),
        "convocatoria": _load_ids("entity_registry_convocatorias.csv",  "convocatoria_id"),
        "institucion":  institution_ids,
    }

    # Validación vectorizada: una pasada por tipo en lugar de iterrows()
    alerts: list[str] = []
    orphan_origin_examples: list[str] = []
    orphan_target_examples: list[str] = []

    for side, id_col, examples_list in (
        ("origin", "origin_id", orphan_origin_examples),
        ("target", "target_id", orphan_target_examples),
    ):
        type_col = f"{side}_type"
        for etype, known_ids in registries.items():
            if not known_ids:
                continue
            mask = links[type_col].fillna("") == etype
            subset = links.loc[mask, id_col].dropna()
            orphans = subset[~subset.isin(known_ids)]
            examples_list.extend(orphans.astype(str).head(3).tolist())

    n_origin = len(orphan_origin_examples)
    n_target = len(orphan_target_examples)
    if n_origin:
        alerts.append(
            f"{n_origin} enlaces con origin_id sin registro canónico "
            f"(ej: {orphan_origin_examples[:3]})"
        )
    if n_target:
        alerts.append(
            f"{n_target} enlaces con target_id sin registro canónico "
            f"(ej: {orphan_target_examples[:3]})"
        )
    _append_custom_result(
        "Integridad entity_links",
        links_path,
        len(links),
        alerts,
        "ADVERTENCIA" if alerts else "OK",
    )


# ─── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Reporte de calidad de datos CCHEN")
    parser.add_argument("--output", help="Ruta CSV para guardar el reporte (opcional)")
    args = parser.parse_args()

    now = datetime.datetime.now()
    print("\n" + "=" * 100)
    print(f"  REPORTE DE CALIDAD DE DATOS — Observatorio CCHEN 360°")
    print(f"  {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 100 + "\n")

    # ── Publicaciones ──────────────────────────────────────────────────────────
    print("── PUBLICACIONES\n")
    check("OpenAlex works",          PUB / "cchen_openalex_works.csv",
          pk="openalex_id",
          required_cols=["openalex_id", "title", "year", "source", "cited_by_count"],
          year_col="year", year_min=1990, year_max=2026)

    check("Publications enriched",   PUB / "cchen_publications_with_quartile_sjr.csv",
          pk="work_id",
          required_cols=["work_id", "year_num", "quartile", "n_authorships"],
          year_col="year_num", year_min=1990, year_max=2026,
          completeness_threshold=0.40)  # quartile solo disponible para revistas indexadas

    check("Authorships enriched",    PUB / "cchen_authorships_enriched.csv",
          required_cols=["work_id", "author_name", "institution_country_code"],
          completeness_threshold=0.60)

    check("CrossRef enriched",       PUB / "cchen_crossref_enriched.csv",
          pk="doi",
          required_cols=["doi", "crossref_funders"],
          completeness_threshold=0.30)   # muchos papers sin funder declarado

    check("OpenAlex concepts",       PUB / "cchen_openalex_concepts.csv",
          required_cols=["work_id", "concept_name", "concept_score"])

    check("Publications with concepts", PUB / "cchen_publications_with_concepts.csv",
          pk="openalex_id",
          required_cols=["openalex_id", "title", "year"])

    check("Publications full",       PUB / "cchen_publications_full.csv",
          pk="openalex_id",
          required_cols=["openalex_id", "title", "year"])

    check("OpenAlex grants",         PUB / "cchen_openalex_grants.csv",
          required_cols=["work_id"])

    # ── ANID ──────────────────────────────────────────────────────────────────
    print("\n── ANID / FINANCIAMIENTO\n")
    check("ANID proyectos",          ANID_DIR / "RepositorioAnid_con_monto.csv",
          pk="proyecto",
          required_cols=["proyecto", "titulo", "autor", "anio_concurso", "monto_programa_num"],
          year_col="anio_concurso", year_min=2000, year_max=2026)

    check("Funding complementario",  FUND_DIR / "cchen_funding_complementario.csv",
          pk="funding_id",
          required_cols=["funding_id", "fuente", "instrumento", "titulo", "anio", "source_confidence", "last_verified_at"],
          year_col="anio", year_min=2000, year_max=2026,
          read_kwargs={"encoding": "utf-8-sig"})

    check("IAEA TC",                 FUND_DIR / "cchen_iaea_tc.csv",
          required_cols=["proyecto_tc", "titulo", "fuente", "anio"],
          year_col="anio", year_min=2000, year_max=2026,
          read_kwargs={"encoding": "utf-8-sig"})

    check_funding_operational_coverage()

    # ── Vigilancia y matching ──────────────────────────────────────────────────
    print("\n── VIGILANCIA Y MATCHING\n")
    check("Convocatorias curadas",   VIG_DIR / "convocatorias_curadas.csv",
          pk="conv_id",
          required_cols=["conv_id", "titulo", "estado"],
          read_kwargs={"encoding": "utf-8-sig"})

    check("Perfiles institucionales", VIG_DIR / "perfiles_institucionales_cchen.csv",
          pk="perfil_id",
          required_cols=["perfil_id", "perfil_nombre", "owner_unit"],
          read_kwargs={"encoding": "utf-8-sig"})

    check("Reglas de matching",      VIG_DIR / "convocatorias_matching_rules.csv",
          pk="rule_id",
          required_cols=["rule_id", "perfil_id", "exact_aliases"],
          read_kwargs={"encoding": "utf-8-sig"})

    check("Matching institucional",  VIG_DIR / "convocatorias_matching_institucional.csv",
          required_cols=["conv_id", "perfil_id", "owner_unit", "score_total", "eligibility_status", "recommended_action"],
          completeness_threshold=0.90,
          read_kwargs={"encoding": "utf-8-sig"})

    check_matching_coverage()

    # ── Capital Humano ─────────────────────────────────────────────────────────
    print("\n── CAPITAL HUMANO\n")
    check("Dataset maestro CH",      CH_DIR / "dataset_maestro_limpio.csv",
          required_cols=["nombre", "tipo_norm", "centro_norm", "anio_hoja"],
          year_col="anio_hoja", year_min=2020, year_max=2026,
          read_kwargs={"encoding": "utf-8-sig"})

    # ── Investigadores ─────────────────────────────────────────────────────────
    print("\n── INVESTIGADORES\n")
    check("ORCID researchers",       RES_DIR / "cchen_researchers_orcid.csv",
          pk="orcid_id",
          required_cols=["orcid_id", "full_name", "orcid_works_count"])

    # ── Institucional ──────────────────────────────────────────────────────────
    print("\n── INSTITUCIONAL\n")
    check("Convenios nacionales",    INST_DIR / "clean_Convenios_suscritos_por_la_Com.csv",
          required_cols=["CONTRAPARTE DEL CONVENIO", "FECHA RESOLUCIÓN"])

    check("Acuerdos internacionales", INST_DIR / "clean_Acuerdos_e_instrumentos_intern.csv",
          required_cols=[])

    check("Institution registry ROR", INST_DIR / "cchen_institution_registry.csv",
          pk="normalized_key",
          required_cols=["canonical_name", "normalized_key", "match_status"],
          read_kwargs={"encoding": "utf-8-sig"})

    check("ROR pending review",      INST_DIR / "ror_pending_review.csv",
          pk="canonical_name",
          required_cols=["canonical_name", "priority_level", "recommended_resolution"],
          read_kwargs={"encoding": "utf-8-sig"})

    check_ror_operational_state()

    # ── Gobernanza operativa ───────────────────────────────────────────────────
    print("\n── GOBERNANZA OPERATIVA\n")
    check("Entity registry personas", GOV_DIR / "entity_registry_personas.csv",
          pk="persona_id",
          required_cols=["persona_id", "canonical_name", "institution_id"],
          completeness_threshold=0.40,
          read_kwargs={"encoding": "utf-8-sig"})

    check("Entity registry proyectos", GOV_DIR / "entity_registry_proyectos.csv",
          pk="project_id",
          required_cols=["project_id", "titulo", "institucion_id"],
          year_col="anio_concurso", year_min=2000, year_max=2026,
          read_kwargs={"encoding": "utf-8-sig"})

    check("Entity registry convocatorias", GOV_DIR / "entity_registry_convocatorias.csv",
          pk="convocatoria_id",
          required_cols=["convocatoria_id", "titulo", "perfil_id", "owner_unit"],
          read_kwargs={"encoding": "utf-8-sig"})

    check("Entity links",            GOV_DIR / "entity_links.csv",
          required_cols=["origin_type", "origin_id", "relation", "target_type", "target_id"],
          completeness_threshold=1.0,
          read_kwargs={"encoding": "utf-8-sig"})

    # ── Integridad referencial ─────────────────────────────────────────────────
    print("\n── INTEGRIDAD REFERENCIAL\n")
    check_cross_integrity()
    check_entity_links_integrity()

    # ── Frescura de datos ──────────────────────────────────────────────────────
    print("\n── FRESCURA DE DATOS\n")
    stale_files = check_staleness()
    if not stale_files:
        print("  Todos los archivos monitoreados están dentro del período esperado.")

    # ── Resumen final ──────────────────────────────────────────────────────────
    total    = len(RESULTS)
    ok_count = sum(1 for r in RESULTS if r["estado"] == "OK")
    warn     = sum(1 for r in RESULTS if r["estado"] == "ADVERTENCIA")
    crit     = sum(1 for r in RESULTS if r["estado"] == "CRITICO")
    total_rows = sum(r.get("filas", 0) for r in RESULTS
                     if "INTEGRIDAD" not in r["fuente"])

    print("\n" + "=" * 100)
    print(f"  RESUMEN: {total} fuentes verificadas | "
          f"{ok_count} OK  {warn} advertencias  {crit} críticos | "
          f"{total_rows:,} filas totales")
    print("=" * 100 + "\n")

    # ── Exportar CSV ───────────────────────────────────────────────────────────
    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = ["fuente", "archivo", "existe", "filas", "duplicados",
                      "cols_faltantes", "completeness_min", "year_fuera_rango",
                      "alertas", "estado"]
        with open(out, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in RESULTS:
                r2 = dict(r)
                r2["alertas"] = "; ".join(r2.get("alertas", []))
                writer.writerow({k: r2.get(k, "") for k in fieldnames})
        print(f"  Reporte guardado en: {out}\n")


if __name__ == "__main__":
    main()
