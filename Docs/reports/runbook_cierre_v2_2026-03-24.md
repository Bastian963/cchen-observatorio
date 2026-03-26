# Runbook de cierre v2 (2026-03-24)

Objetivo: cerrar la evaluación `structured_responses_v2` en una sola pasada cuando haya cuota disponible en Groq.

## Preflight (recomendado antes de correr)

```bash
bash Scripts/preflight_cierre_v2.sh
```

Valida insumos, scripts y template pendiente sin gastar tokens Groq.
Deja evidencia en `Docs/reports/preflight_cierre_v2_<timestamp>.json`.

## Opción rápida (comando único)

```bash
GROQ_API_KEY="<key>" Scripts/cerrar_v2_structured.sh
```

Este comando ejecuta automáticamente: extracción Q01-Q02, rerun Q03-Q10, merge final, comparación v1 vs v2 y generación de resumen ejecutivo.

## Opción programada con registro de estado

```bash
export GROQ_API_KEY="<key>"
bash Scripts/programar_cierre_v2.sh
```

Artefactos que deja:

- `Docs/reports/cierre_v2_scheduler_<run_id>.out`
- `Docs/reports/cierre_v2_scheduler_<run_id>.pid`
- `Docs/reports/cierre_v2_job_<run_id>.log`
- `Docs/reports/cierre_v2_job_status_<run_id>.json`

Estados posibles en el JSON de status:

- `success`
- `rate_limited` (detecta `rate_limit_exceeded`, `Rate limit reached` o `429`)
- `missing_api_key`
- `failed`

## Estado al cierre del día

- `Q01` y `Q02` ya exitosas en corrida parcial.
- `Q03` a `Q10` pendientes por rate limit.
- Input parcial ya preparado: `Docs/reports/assistant_eval_template_pending_q03_q10.csv`.

## Paso 0 — Generar archivo head Q01-Q02 (si no existe)

```bash
awk -F, 'NR==1 || $1=="Q01" || $1=="Q02"' \
  Docs/reports/assistant_eval_structured_responses_v2.csv \
  > Docs/reports/assistant_eval_structured_responses_v2_q01_q02.csv
```

Resultado esperado:

- CSV con 3 líneas (header + 2 filas).

## Paso 1 — Ejecutar pendientes Q03-Q10

```bash
GROQ_API_KEY="<key>" .venv/bin/python Scripts/assistant_eval_structured_responses.py \
  --input Docs/reports/assistant_eval_template_pending_q03_q10.csv \
  --run-label structured_responses_v2_pending \
  --output Docs/reports/assistant_eval_structured_responses_v2_pending.csv
```

Resultado esperado:

- CSV de salida con 8 filas (`Q03,Q04,Q05,Q06,Q07,Q08,Q09,Q10`).

## Paso 2 — Consolidar en un v2 final único

```bash
.venv/bin/python Scripts/merge_structured_eval_runs.py \
  --head Docs/reports/assistant_eval_structured_responses_v2_q01_q02.csv \
  --tail Docs/reports/assistant_eval_structured_responses_v2_pending.csv \
  --template Docs/reports/assistant_eval_structured_responses_v1.csv \
  --run-label structured_responses_v2_final \
  --output Docs/reports/assistant_eval_structured_responses_v2_final.csv \
  --strict-complete
```

Resultado esperado:

- `merged rows (unique query_id): 8`
- `missing query_id: 0`
- archivo final generado en `Docs/reports/assistant_eval_structured_responses_v2_final.csv`.

Nota:

- El `--template` debe ser `assistant_eval_structured_responses_v1.csv` (8 queries structured).
- No usar `assistant_eval_template.csv` para este merge, porque incluye queries de `publication_rag`.

## Paso 3 — Comparar v1 vs v2 final

```bash
.venv/bin/python Scripts/compare_eval_runs.py \
  --v1 Docs/reports/assistant_eval_structured_responses_v1.csv \
  --v2 Docs/reports/assistant_eval_structured_responses_v2_final.csv \
  --output Docs/reports/assistant_eval_compare_structured_v2_final_vs_v1.csv
```

Resultado esperado:

- Resumen agregado con `heuristic_citation_tags` > 0 en v2.
- CSV de comparación listo para reporte.

## Paso 4 — Cierre documental

Actualizar:

- `ARCHITECTURE.md` sección 17.2 con resultados finales v1 vs v2.
- Si corresponde, anexar hallazgo en bitácora de reportes.
- Completar resumen ejecutivo usando `Docs/reports/resumen_cierre_v2_template.md`.

## Paso 5 — Generar resumen ejecutivo automático

```bash
.venv/bin/python Scripts/generar_resumen_cierre_v2.py \
  --compare Docs/reports/assistant_eval_compare_structured_v2_final_vs_v1.csv \
  --output Docs/reports/resumen_cierre_v2.md \
  --responsable "Bastián Ayala"
```

Resultado esperado:

- Archivo `Docs/reports/resumen_cierre_v2.md` con placeholders completos.

## Troubleshooting rápido

1. Si vuelve a aparecer rate limit:

- reintentar en ventana siguiente sin cambiar input.

1. Si falla merge por faltantes:

- revisar que el archivo `--head` contenga `Q01,Q02` y `--tail` contenga `Q03..Q10`.
- ejecutar de nuevo con `--strict-complete` para validar cobertura exacta.

1. Si comparación muestra métricas vacías:

- validar que se esté comparando structured vs structured (`assistant_eval_structured_responses_*.csv`).
