# Modo Comité — KPIs Semanales (v1)

**Versión:** 1.0  
**Fecha:** 2026-03-23  
**Objetivo:** Seguimiento ejecutivo semanal del estado operativo y calidad de datos del Observatorio CCHEN 360°.

---

## 1) KPIs de comité (8)

| KPI | Definición | Fórmula | Meta (verde) | Umbral amarillo | Umbral rojo | Fuente |
|-----|------------|---------|---------------|------------------|-------------|--------|
| K1. Éxito del pipeline semanal | Estado del workflow `arxiv_monitor.yml` | `success_runs / total_runs_semana * 100` | 100% | 1 run en fallo parcial | `conclusion != success` | GitHub Actions logs |
| K2. Volumen crítico de ingesta | Cobertura de fuentes críticas (arXiv + News) | `arxiv_filas + news_filas` | `>= 30` y ambos >0 | 1 fuente entre 1 y umbral | 1 fuente en 0 o SKIP | Estado operativo en log |
| K3. Paridad de migración | Consistencia entre filas leídas y migradas | `migradas / leidas * 100` por fuente | 100% ambas fuentes | 90%-99% | <90% o error de migración | Log de `migrate_vigilancia.py` |
| K4. Estabilidad best-effort | Comportamiento de IAEA + Convocatorias | `semanas_consecutivas_skip` por fuente | 0 semanas | 1 semana | >=2 semanas | `sla_semanal.md` historial |
| K5. Puntualidad del boletín | Generación del boletín semanal | `boletin_generado (sí/no)` | Sí | N/A | No | `Data/Boletines/` + log |
| K6. Advertencias de calidad | # de fuentes en ADVERTENCIA en data quality | `count(estado == ADVERTENCIA)` | 0-1 | 2-3 | >=4 | `calidad_YYYY-MM.csv` |
| K7. Cobertura de funding enriquecido | Calidad de metadatos de financiamiento | `%crossref_funders` y `filas_openalex_grants` | `crossref_funders >= 30%` y grants >0 | 25%-29% o grants=0 aislado | <25% sostenido o grants=0 >=2 cortes | `calidad_YYYY-MM.csv` |
| K8. Consistencia temporal | Registros con año fuera de rango | `filas_fuera_rango / filas_totales_publicaciones * 100` | <=2% | >2% y <=5% | >5% | `calidad_YYYY-MM.csv` |

---

## 2) Conexión directa con brechas actuales

Brechas detectadas en marzo 2026 y KPI que las monitorea:

| Brecha detectada | Evidencia actual | KPI asociado | Estado actual |
|------------------|------------------|--------------|---------------|
| OpenAlex grants vacío | 0 filas (ADVERTENCIA) | K7 | Amarillo |
| CrossRef funders bajo umbral | 25% (<30%) | K7 | Amarillo |
| OpenAlex works con años fuera de rango | 50 filas fuera de [1990, 2026] | K8 | Amarillo |
| Publications enriched con años fuera de rango | 36 filas fuera de [1990, 2026] | K8 | Amarillo |
| Duplicados en ANID proyectos | 6 duplicados en `proyecto` | K6 | Verde con observación |

---

## 3) Tablero semanal de comité

Completar una fila por semana.

| Semana | K1 Pipeline | K2 Ingesta crítica | K3 Paridad migración | K4 Best-effort | K5 Boletín | K6 Calidad | K7 Funding | K8 Temporal | Nivel global | Acción |
|--------|-------------|--------------------|----------------------|----------------|------------|------------|------------|-------------|-------------|--------|
| S13-2026 | 🟢 100% | 🟢 98 filas (33+65) | 🟢 100% / 100% | 🟡 IAEA+Conv semana 1 | 🟢 Sí | 🟡 2 advertencias | 🟡 25% + grants=0 | 🟡 86/1493 = 5.8% | 🟡 Alerta | Mantener seguimiento; escalar si best-effort repite semana 2 |

Notas de cálculo S13-2026:
- K2 = 33 (arXiv) + 65 (News) = 98.
- K8 = (50 + 36) / (877 + 616) = 86 / 1493 = 5.8%.

---

## 4) Regla de nivel global para comité

- **🟢 Verde:** 0 KPIs en rojo y máximo 2 en amarillo.
- **🟡 Amarillo:** 1 KPI en rojo o 3-4 en amarillo.
- **🔴 Rojo:** 2 o más KPIs en rojo, o falla en K1/K2/K3/K5.

---

## 5) Guion comité (15 minutos)

### Min 0-3: Estado general
- K1, K2, K3 y K5 (operación mínima viable semanal).
- Decisión rápida: ¿la semana está en verde, amarillo o rojo?

### Min 3-8: Riesgos best-effort y continuidad
- K4: IAEA/Convocatorias (¿semana consecutiva 1 o >=2?).
- Definir si corresponde abrir issue o solo observación.

### Min 8-12: Calidad de datos
- K6, K7, K8 con foco en tendencia (sube/baja respecto a semana/corte previo).
- Priorizar una corrección concreta para la semana siguiente.

### Min 12-15: Cierre ejecutivo
- 3 decisiones: mantener, corregir, escalar.
- Asignar responsable y fecha para cada acción.

---

## 6) Acciones gatilladas por KPI (playbook corto)

| KPI | Si está en amarillo | Si está en rojo |
|-----|---------------------|-----------------|
| K1 | Revisar run logs y documentar causa | Trigger manual + issue inmediata |
| K2 | Revisar filtros/queries en `arxiv_monitor.py` y `news_monitor.py` | Escalar P1, fix y rerun el mismo día |
| K3 | Reintentar `migrate_vigilancia.py`, verificar schema | Incidente de datos: bloquear reporte semanal hasta corregir |
| K4 | Marcar semana consecutiva en SLA | Abrir issue de fuente externa + plan alternativo manual |
| K5 | Reintentar `generar_boletin.py` local | Publicar versión manual mínima el mismo día |
| K6 | Priorizar 1-2 advertencias para cierre semanal | Ejecutar plan de remediación de calidad (top 3) |
| K7 | Revisar enriquecimiento CrossRef/OpenAlex grants | Escalar a corrección de pipeline y revisión de cobertura |
| K8 | Aplicar limpieza de años y validaciones previas | Bloquear métricas temporales hasta saneamiento |

---

## 7) Comando base para actualización semanal

```bash
# 1) Estado operativo del último run
RUN_ID=$(gh run list --workflow arxiv_monitor.yml --limit 1 --json databaseId -q '.[0].databaseId')
gh run view "$RUN_ID" --log | grep -E \
"Estado operativo|arXiv|News.*fila|IAEA|SKIP|convocatorias|Boletín guardado|filas migradas|Leídas:|TLS"

# 2) Calidad mensual (o semanal si se requiere)
python3 Database/data_quality.py --output Docs/reports/calidad_$(date +%Y-%m).csv
```

---

*Próxima revisión de KPIs: 2026-03-30 (Semana 14).*