#!/usr/bin/env python3
"""Generate concise evidence briefs by strategic topic."""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "Scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import evidence_search

TOPICS = [
    {
        "key": "radiofarmacia",
        "title": "Radiofarmacia y medicina nuclear",
        "query": "radiofarmacia medicina nuclear CCHEN compuestos transferencia",
        "decision": "Mantener como caso demostrativo, con validacion tecnica antes de hablar de transferencia.",
    },
    {
        "key": "outputs_repositorios",
        "title": "Outputs, datasets y repositorios abiertos",
        "query": "outputs datasets repositorios Zenodo DataCite OpenAIRE CCHEN",
        "decision": "Usar como evidencia de trazabilidad y productos reutilizables; clasificar utilidad por output.",
    },
    {
        "key": "patentes_pi",
        "title": "Patentes y propiedad intelectual",
        "query": "patentes propiedad intelectual INAPI CCHEN transferencia",
        "decision": "Mantener como capa de antecedentes; requiere revision legal, vigencia y relacion con activos actuales.",
    },
    {
        "key": "materiales_procesos",
        "title": "Materiales y procesos para aplicaciones nucleares",
        "query": "materiales procesos aplicaciones nucleares CCHEN patentes proyectos publicaciones",
        "decision": "Priorizar como linea tecnica con publicaciones, proyectos y patentes por revisar.",
    },
    {
        "key": "convocatorias_oportunidades",
        "title": "Convocatorias y oportunidades",
        "query": "convocatorias oportunidades financiamiento matching institucional investigacion CCHEN",
        "decision": "Usar para priorizar postulaciones y rutas de maduracion institucional.",
    },
    {
        "key": "colaboracion_convenios",
        "title": "Convenios y colaboracion institucional",
        "query": "convenios acuerdos colaboracion institucional nuclear CCHEN",
        "decision": "Usar como mapa de contrapartes; validar vigencia y alcance operativo antes de tomar decisiones.",
    },
]


def _slug(value: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower())
    return re.sub(r"_+", "_", text).strip("_")


def _safe(value: object) -> str:
    return str(value or "").replace("|", "/").replace("\n", " ").strip()


def _type_counts(results: pd.DataFrame) -> str:
    if results.empty:
        return "Sin resultados."
    rows = results["tipo_evidencia"].value_counts().reset_index()
    rows.columns = ["Tipo", "Registros"]
    return "\n".join(f"- {row.Tipo}: {int(row.Registros)}" for _, row in rows.iterrows())


def _source_counts(results: pd.DataFrame) -> str:
    if results.empty:
        return "Sin resultados."
    rows = results["fuente"].value_counts().head(8).reset_index()
    rows.columns = ["Fuente", "Registros"]
    return "\n".join(f"- {row.Fuente}: {int(row.Registros)}" for _, row in rows.iterrows())


def _brief_markdown(topic: dict, results: pd.DataFrame, top_k: int) -> str:
    today = dt.date.today().isoformat()
    lines = [
        f"# Ficha de evidencia: {topic['title']}",
        "",
        f"Fecha: {today}",
        "",
        "## Pregunta de busqueda",
        "",
        f"`{topic['query']}`",
        "",
        "## Lectura ejecutiva",
        "",
        f"Esta ficha resume los primeros {min(top_k, len(results))} registros recuperados desde el indice interno de evidencia CCHEN. No constituye evaluacion legal, comercial ni validacion de transferencia tecnologica.",
        "",
        "## Tipos de evidencia recuperada",
        "",
        _type_counts(results),
        "",
        "## Fuentes principales",
        "",
        _source_counts(results),
        "",
        "## Evidencia destacada",
        "",
        "| Score | Tipo | Fuente | Titulo | Uso para gestion | Brecha |",
        "|---:|---|---|---|---|---|",
    ]
    for _, row in results.head(top_k).iterrows():
        lines.append(
            f"| {float(row.get('score', 0) or 0):.3f} | {_safe(row.get('tipo_evidencia'))} | "
            f"{_safe(row.get('fuente'))} | {_safe(row.get('titulo'))[:140]} | "
            f"{_safe(row.get('uso_observatorio'))[:180]} | {_safe(row.get('brecha'))[:180]} |"
        )
    lines.extend(
        [
            "",
            "## Decision sugerida",
            "",
            topic["decision"],
            "",
            "## Prompt para sintesis con LLM",
            "",
            "```text",
            "Actua como asistente de evidencia para gestion de investigacion e innovacion CCHEN.",
            f"Pregunta: {topic['query']}",
            "Usa solo la evidencia recuperada desde la base interna.",
            "Para cada hallazgo indica fuente, tipo de evidencia, relacion con CCHEN, posible uso, brecha y nivel de confianza.",
            "No afirmes que una tecnologia esta lista para transferirse. No inventes evidencia.",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def generate(out_dir: Path, top_k: int) -> pd.DataFrame:
    out_dir.mkdir(parents=True, exist_ok=True)
    index_rows: list[dict] = []
    for topic in TOPICS:
        results = evidence_search.search(topic["query"], top_k=top_k)
        file_name = f"ficha_evidencia_{_slug(topic['key'])}.md"
        path = out_dir / file_name
        path.write_text(_brief_markdown(topic, results, top_k), encoding="utf-8")
        index_rows.append(
            {
                "topic_key": topic["key"],
                "topic_title": topic["title"],
                "query": topic["query"],
                "records": int(len(results)),
                "top_type": str(results.iloc[0].get("tipo_evidencia", "")) if not results.empty else "",
                "top_source": str(results.iloc[0].get("fuente", "")) if not results.empty else "",
                "brief_path": str(path.relative_to(ROOT)),
            }
        )
    index_df = pd.DataFrame(index_rows)
    index_df.to_csv(out_dir / "indice_fichas_evidencia.csv", index=False, encoding="utf-8-sig")
    (out_dir / "indice_fichas_evidencia.md").write_text(
        "# Indice de fichas de evidencia\n\n"
        + "| Tema | Registros | Fuente top | Ficha |\n"
        + "|---|---:|---|---|\n"
        + "\n".join(
            f"| {row.topic_title} | {int(row.records)} | {row.top_source} | [{Path(row.brief_path).name}]({Path(row.brief_path).name}) |"
            for _, row in index_df.iterrows()
        )
        + "\n",
        encoding="utf-8",
    )
    return index_df


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--top-k", type=int, default=12)
    parser.add_argument("--out-dir", default="Docs/reports/evidence_topics")
    args = parser.parse_args()
    index_df = generate(ROOT / args.out_dir, args.top_k)
    print(index_df[["topic_key", "records", "top_type", "top_source"]].to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
