#!/usr/bin/env python3
"""Evaluate the unified evidence search with fixed management questions."""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "Scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import evidence_search

DEFAULT_QUERIES = [
    {
        "query_id": "Q01",
        "query": "radiofarmacia con potencial de transferencia",
        "expected_types": {"senal tematica", "compuesto", "publicacion", "patente"},
        "expected_terms": {"radiofarm", "fdg", "lu-177", "ga-68", "tc-99m", "i-131", "medicina nuclear"},
    },
    {
        "query_id": "Q02",
        "query": "capacidades CCHEN en medicina nuclear",
        "expected_types": {"senal tematica", "publicacion", "compuesto"},
        "expected_terms": {"medicina nuclear", "nuclear medicine", "dosimetr", "pet", "spect"},
    },
    {
        "query_id": "Q03",
        "query": "outputs o datasets asociados a CCHEN",
        "expected_types": {"dataset/output"},
        "expected_terms": {"dataset", "output", "zenodo", "datacite", "openaire", "repositorio"},
    },
    {
        "query_id": "Q04",
        "query": "patentes y propiedad intelectual CCHEN",
        "expected_types": {"patente"},
        "expected_terms": {"patente", "inapi", "propiedad intelectual", "titular", "clasificacion"},
    },
    {
        "query_id": "Q05",
        "query": "convenios o colaboraciones institucionales nucleares",
        "expected_types": {"convenio"},
        "expected_terms": {"convenio", "acuerdo", "cooperacion", "universidad", "organismo"},
    },
    {
        "query_id": "Q06",
        "query": "convocatorias y oportunidades para investigacion CCHEN",
        "expected_types": {"oportunidad", "proyecto"},
        "expected_terms": {"convocatoria", "anid", "fondo", "matching", "proyecto"},
    },
]


def _contains_expected_term(row: pd.Series, expected_terms: set[str]) -> bool:
    text = " ".join(
        str(row.get(col, "") or "").lower()
        for col in ["titulo", "resumen", "tema", "relacion_cchen", "uso_observatorio", "brecha", "fuente"]
    )
    return any(term in text for term in expected_terms)


def evaluate(top_k: int) -> pd.DataFrame:
    rows: list[dict] = []
    for item in DEFAULT_QUERIES:
        results = evidence_search.search(item["query"], top_k=top_k)
        if results.empty:
            rows.append(
                {
                    "query_id": item["query_id"],
                    "query": item["query"],
                    "top_k": top_k,
                    "results": 0,
                    "expected_type_hits": 0,
                    "expected_term_hits": 0,
                    "top_type": "",
                    "top_source": "",
                    "top_title": "",
                    "top_score": 0.0,
                    "status": "fail",
                    "notes": "Sin resultados.",
                }
            )
            continue

        type_hits = results["tipo_evidencia"].astype(str).isin(item["expected_types"])
        term_hits = results.apply(lambda row: _contains_expected_term(row, item["expected_terms"]), axis=1)
        top = results.iloc[0]
        status = "ok" if bool(type_hits.iloc[0]) and int(type_hits.sum()) >= max(1, top_k // 3) else "warning"
        if int(term_hits.sum()) == 0:
            status = "warning"
        rows.append(
            {
                "query_id": item["query_id"],
                "query": item["query"],
                "top_k": top_k,
                "results": int(len(results)),
                "expected_type_hits": int(type_hits.sum()),
                "expected_term_hits": int(term_hits.sum()),
                "top_type": str(top.get("tipo_evidencia", "")),
                "top_source": str(top.get("fuente", "")),
                "top_title": str(top.get("titulo", ""))[:180],
                "top_score": float(top.get("score", 0) or 0),
                "status": status,
                "notes": "Top result type and evidence terms are aligned." if status == "ok" else "Revisar ranking o cobertura de esta consulta.",
            }
        )
    return pd.DataFrame(rows)


def write_report(df: pd.DataFrame, out_csv: Path, out_md: Path) -> None:
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_csv, index=False, encoding="utf-8-sig")
    status_counts = df["status"].value_counts().to_dict()
    lines = [
        "# Evaluacion de busqueda de evidencia semantica",
        "",
        f"Fecha: {dt.date.today().isoformat()}",
        "",
        "## Resumen",
        "",
        f"- Consultas evaluadas: {len(df)}",
        f"- OK: {status_counts.get('ok', 0)}",
        f"- Advertencias: {status_counts.get('warning', 0)}",
        f"- Fallos: {status_counts.get('fail', 0)}",
        "",
        "## Resultados",
        "",
        "| Query | Estado | Top tipo | Top fuente | Top titulo | Hits tipo | Hits termino |",
        "|---|---|---|---|---|---:|---:|",
    ]
    for _, row in df.iterrows():
        title = str(row["top_title"]).replace("|", "/")
        lines.append(
            f"| {row['query_id']} | {row['status']} | {row['top_type']} | {row['top_source']} | "
            f"{title} | {row['expected_type_hits']} | {row['expected_term_hits']} |"
        )
    lines.extend(
        [
            "",
            "## Criterio",
            "",
            "La evaluacion no mide verdad semantica completa. Verifica que el primer resultado y una fraccion relevante del top-k pertenezcan al tipo de evidencia esperado, y que aparezcan terminos tematicos coherentes.",
        ]
    )
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--top-k", type=int, default=8)
    parser.add_argument("--date", default=dt.date.today().isoformat())
    args = parser.parse_args()

    df = evaluate(args.top_k)
    reports_dir = ROOT / "Docs" / "reports"
    out_csv = reports_dir / f"evidence_search_eval_{args.date}.csv"
    out_md = reports_dir / f"evidence_search_eval_{args.date}.md"
    write_report(df, out_csv, out_md)
    print(df[["query_id", "status", "top_type", "top_source", "expected_type_hits", "expected_term_hits"]].to_string(index=False))
    print(f"[OK] CSV: {out_csv}")
    print(f"[OK] MD:  {out_md}")
    return 0 if not df["status"].eq("fail").any() else 1


if __name__ == "__main__":
    raise SystemExit(main())
