# Flujo canónico de actualización y monitoreo de fuentes

## 1. Contrato operativo

- La fuente de verdad de gobernanza es `Database.data_sources`.
- El historial operativo vive en `Database.data_source_runs`.
- El runner canónico es `python Scripts/run_source_refresh.py`.
- El scheduler principal es `.github/workflows/actualizacion_datos.yml`.
- El workflow `.github/workflows/arxiv_monitor.yml` queda sólo para ejecución manual y boletín.

## 2. Modos de ejecución

### Corrida programada

- GitHub Actions ejecuta diariamente:

```bash
python Scripts/run_source_refresh.py --all-due
```

- El runner evalúa `enabled`, `update_frequency`, `freshness_sla_days`, `last_updated` y `next_update_due`.
- Cada fuente vencida ejecuta su `runner_command` declarado en `data_sources`.

### Corrida manual por fuente

```bash
python Scripts/run_source_refresh.py --source-key arxiv_monitor
python Scripts/run_source_refresh.py --source-key orcid --force
python Scripts/run_source_refresh.py --all-due --dry-run
```

## 3. Qué actualiza cada corrida

Por cada fuente ejecutada, el runner:

- registra `last_updated`
- recalcula `next_update_due`
- estima `record_count`
- calcula `quality_score` usando `Database/data_quality.py`
- actualiza `last_run_status`
- actualiza `last_run_id`
- agrega una fila en `data_source_runs`
- escribe un resumen JSON en `Docs/reports/source_runs/`

Snapshots locales auxiliares:

- `Data/Gobernanza/data_sources_runtime.csv`
- `Data/Gobernanza/data_source_runs.csv`

## 4. Observabilidad y trazabilidad

- Logs de scheduler: pestaña **Actions** del repositorio.
- Artefactos machine-readable por corrida:
  - `Docs/reports/source_runs/<timestamp>_<source_key>.json`
- Estado resumido en dashboard interno:
  - última actualización por fuente
  - próxima actualización esperada
  - overdue / al día
  - último estado de corrida

## 5. Agenda canónica

- `actualizacion_datos.yml` es el único cron operativo.
- `arxiv_monitor.yml` ya no debe usarse como agenda semanal principal.
- Si una fuente nueva se automatiza, primero debe quedar registrada en `data_sources` con:
  - `source_key`
  - `enabled`
  - `runner_command`
  - `output_targets`
  - `owner`
  - `visibility`
  - `blocking`
  - `freshness_sla_days`

## 6. Buenas prácticas

- No automatizar fuentes “por fuera” del contrato `data_sources`.
- Mantener `Zenodo`, `ORCID`, `OpenAIRE` y el resto de fuentes en el mismo registro operativo, aunque todavía sean manuales.
- Antes de cambiar una frecuencia, modificar primero `data_sources`; el scheduler debe obedecer al contrato, no a cron dispersos.
- Si una fuente falla y `blocking=false`, se registra el fallo pero no se detiene el resto de las fuentes.
- Si una fuente crítica falla y `blocking=true`, el runner devuelve error para que el scheduler quede rojo.

## 7. Comandos de revisión rápida

```bash
# Últimos runs del scheduler canónico
gh run list --workflow actualizacion_datos.yml --limit 5 \
  --json databaseId,conclusion,createdAt,displayTitle

# Ver log del último run
RUN_ID=$(gh run list --workflow actualizacion_datos.yml --limit 1 --json databaseId -q '.[0].databaseId')
gh run view "$RUN_ID" --log

# Dry-run local de fuentes vencidas
python Scripts/run_source_refresh.py --all-due --dry-run

# Verificar calidad y contrato
python Database/data_quality.py --output Docs/reports/calidad_datos.csv
python Scripts/check_database_contract.py
```

---

**Última actualización:** 2026-03-29
