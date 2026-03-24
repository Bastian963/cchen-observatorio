# Plan 30-60-90 — Maduración TRL 5 → 6 del Observatorio CCHEN 360°

**Versión:** 2.0 (revisado tras lectura de `observatorio_cchen_documentacion.tex`)  
**Fecha de emisión:** 2026-03-23 (Semana 13)  
**Responsable técnico:** Bastián Ayala I.  
**TRL actual:** 5 · **TRL objetivo H1:** 5 consolidado · **TRL objetivo H3:** 6 demo operacional  
**Fin de fase:** 2026-06-20 (Semana 25) → transición a TRL 6

---

## Estado de partida (Sem 13-2026)

**Sistema actual:** Beta v0.2 · TRL 5 · 34 tablas Supabase · 11 secciones · GitHub Actions semanal activo

| Módulo | Estado actual | Pendiente para TRL 6 |
|--------|--------------|----------------------|
| A. Vigilancia/Prospección | Activo (TRL 5) | BERTopic integrado en dashboard |
| B. Inteligencia Aplicada | Activo (TRL 5) | Demo institucional; QA Asistente |
| C. Difusión y Divulgación | Parcial (TRL 3) | Envío automático boletín (Brevo) |
| D. Repositorio de Datos | Activo (TRL 5) | Zenodo DOI; patentes activas |
| E. Transferencia y Codiseño | Pendiente (TRL 1-2) | Inventario TRL 6-9 de activos |
| F. Colaboración Ecosistémica | Parcial (TRL 2-3) | ROR registry pendientes |
| G. Gobernanza de Datos | Parcial (TRL 3) | Alertas de calidad en verde |

---

## Horizonte 1 — Días 1-30: Completar TRL 5 (Sem 13→17, hasta 2026-04-18)

**Meta:** Todos los módulos activos ≥ TRL 5. Deuda técnica de datos resuelta. Pipeline autónomo sin intervención.

### Ítems de desarrollo pendientes (del roadmap oficial)

| # | Ítem | Módulo | Acción concreta | Plazo |
|---|------|--------|-----------------|-------|
| D1 | Lens.org API token | E (Transferencia) | Registrar en `lens.org/lens/user/subscriptions#patents` (gratuito, uso académico) → pegar token en `05_Download_patents.ipynb` → ejecutar notebook → migrar a `patents` table. **Nota:** PatentsView migró a USPTO ODP (data.uspto.gov) con API interrumpida; Lens.org es la fuente primaria del diseño original (cubre USPTO + EPO + WIPO + INAPI Chile) | Sem 14 |
| D2 | BERTopic en Vigilancia | A (Vigilancia) | `run_bertopic.py` ya existe y tiene 23 tópicos; integrar visualización en sección "Vigilancia Tecnológica" del dashboard | Sem 15 |
| D3 | GitHub Pages para boletines | C (Difusión) | Crear `gh-pages` branch; publicar `Data/Boletines/*.html` como sitio estático semanal | Sem 16 |
| D4 | Envío boletín por Brevo | C (Difusión) | Configurar Brevo API (300 emails/día gratis, mejor free tier que Mailchimp); agregar paso en `generar_boletin.py` | Sem 16 |

### Deuda técnica de datos detectada (alertas amarillas S13)

| # | Brecha | Acción | Plazo |
|---|--------|--------|-------|
| Q1 | OpenAlex grants vacío (0 filas) | Reejecutar `03_OpenAlex_concepts.ipynb` con parámetro `grants=true` | Sem 14 |
| Q2 | CrossRef funders 25% (< 30% meta) | Ampliar lote en `02_CrossRef_enrichment.ipynb`; evaluar si umbral es realista | Sem 14 |
| Q3 | 86 registros con año fuera de rango | Filtrar en `data_quality.py`; validar upstream en `01_Download_publications.ipynb` | Sem 15 |
| Q4 | 6 duplicados en ANID proyectos | Deduplicar en `migrate_convocatorias.py`; agregar assert post-migración | Sem 15 |

### Checklist semanal — H1 (cada lunes)

- [ ] Completar fila en `sla_semanal.md` y `comite_kpis.md` (K1–K8)
- [ ] Si K4 (IAEA/Convocatorias) ≥ 2 semanas SKIP → abrir issue técnico en GitHub
- [ ] Revisar `arxiv_monitor.yml`: éxito 100% sin intervención manual (K1)

**Greenlight H1 (Sem 17):**
- [ ] D1–D4 completados o justificados
- [ ] Q1–Q4 resueltos o umbrales ajustados
- [ ] K6, K7, K8 en verde 2 semanas consecutivas
- [ ] `patents` table poblada (aunque sea con 0 filas — PatentsView registrado)

---

## Horizonte 2 — Días 31-60: Demo operacional TRL 6 (Sem 17→22, hasta 2026-05-23)

**Meta:** El sistema puede ser demostrado ante comité directivo y contraparte CORFO sin soporte técnico en sala. Boletín llegando a destinatarios reales.

### Actividades de maduración

| # | Actividad | Descripción | Entregable | Plazo |
|---|-----------|-------------|-----------|-------|
| V1 | QA Asistente I+D completo | Aplicar batería de 20 preguntas formales (`qa_asistente_id.md`); documentar puntuación 0-160 | Informe QA con observaciones y comparativa respecto a referencia | Sem 18 |
| V2 | Demo institucional | Sesión guiada 45 min con ≥2 usuarios finales CCHEN (dirección, DIAN, vinculación); recorrer las 11 secciones | Registro structured de retroalimentación | Sem 19 |
| V3 | Zenodo archival — primer DOI | Archivar corpus CCHEN en Zenodo (gratuito, GitHub integración) → genera DOI citable para el corpus de 877 papers | DOI público de Zenodo + badge en README | Sem 20 |
| V4 | Validación Transferencia y Portafolio | Inventario TRL 6-9 de activos tecnológicos CCHEN con contraparte vinculación | Lista de activos con TRL asignado en `portafolio_tecnologico_semilla.csv` | Sem 21 |
| V5 | Smoke test post-cambios | Ejecutar `check_dashboard_smoke.py` + `check_dashboard_e2e.py`; documentar resultado | Log E2E sin errores críticos | Sem 21 |

### Checklist semanal — H2

- [ ] Completar fila semanal en `sla_semanal.md` y `comite_kpis.md`
- [ ] Verificar que boletín HTML llega a lista de distribución Brevo (primer envío real)
- [ ] Si hay cambios en `app.py` → `check_dashboard_smoke.py` antes de push

**Greenlight H2 (Sem 22):**
- [ ] QA Asistente completado con puntuación documentada (V1)
- [ ] Demo realizada con ≥2 usuarios (V2)
- [ ] Zenodo DOI publicado (V3)
- [ ] Boletín llegando automáticamente a destinatarios reales (D4 de H1 operativo)

---

## Horizonte 3 — Días 61-90: Cierre y preparación TRL 7 (Sem 22→25, hasta 2026-06-20)

**Meta:** Tag `v1.0` publicado. Activos documentados para traspaso. Decisión técnica tomada sobre stack TRL 7-8 con presupuesto real.

### Actividades de cierre

| # | Actividad | Descripción | Entregable | Plazo |
|---|-----------|-------------|-----------|-------|
| C1 | E2E completo + tag v1.0 | `check_dashboard_e2e.py` sin errores → tag `v1.0` en GitHub | Tag publicado; log E2E adjunto | Sem 23 |
| C2 | Informe calidad Q1-2026 | Consolidar `calidad_YYYY-MM.csv` Ene-Jun; tabla resumen de alertas y resoluciones | `Docs/reports/informe_calidad_2026-Q1.md` | Sem 23 |
| C3 | Informe de performance | Consolidar benchmarks (baseline vs post-quickwins, section proxy times) | `Docs/reports/informe_performance_2026-Q1.md` | Sem 24 |
| C4 | Decisión stack TRL 7-8 | Evaluar opciones de orquestación y frontend (ver sección abajo) | `Docs/design/decision_stack_trl7.md` | Sem 24 |
| C5 | Entrega formal | Enviar a contraparte: repo, credenciales Supabase, `playbook_operaciones.md`, Zenodo DOI | Correo formal con adjuntos | Sem 25 |
| C6 | Retrospectiva de fase | Lecciones aprendidas, brechas abiertas, KPIs al cierre | `Docs/operations/retrospectiva_fase1.md` | Sem 25 |

### Checklist semanal — H3

- [ ] Completar fila semanal en `sla_semanal.md` y `comite_kpis.md`
- [ ] Avanzar ítems C1–C6 según plazo

**Greenlight H3 (Sem 25 = cierre de fase):**
- [ ] E2E limpio + tag v1.0 (C1)
- [ ] Informe calidad Q1 entregado (C2)
- [ ] Informe performance entregado (C3)
- [ ] Decisión stack TRL 7 documentada (C4)
- [ ] Entrega formal realizada (C5)
- [ ] Retrospectiva escrita (C6)

---

## Decisión de herramientas — Stack robusto por componente

Los documentos de diseño (Memoria Metodológica, Propuesta de Implementación) proponen herramientas de terceros (incluyendo n8n y otras). Esta sección evalúa cada caso con criterio técnico, priorizando lo que ya funciona.

### Automatización ETL (actual: GitHub Actions)

| Herramienta | Veredicto | Razón |
|-------------|-----------|-------|
| **GitHub Actions** ✅ mantener | Óptimo para TRL 5-6 | Ya funciona, gratis, versionado junto al código, `workflow_dispatch` para ejecución manual. No reemplazar. |
| **n8n** ❌ no adoptar ahora | Overhead sin beneficio | Requiere servidor propio o n8n.cloud (costo). Los workflows no son Python nativo. No integra con pytest/CI. Diseñado para usar con GUI, no para un stack 100% Python. Reconsiderar solo si entra un equipo no-técnico que deba operar los pipelines. |
| **Prefect** 🟡 evaluar en TRL 7 | Python-nativo y ligero | Si la complejidad de los DAGs crece (dependencias cruzadas entre notebooks), Prefect es el mejor paso intermedio antes de Airflow. Instala como paquete Python, sin servidor adicional. |
| **Apache Airflow** 🟡 TRL 7-8 | Objetivo ya documentado | Correcto para el stack de producción (Angular + Django + Huawei Cloud). Requiere infraestructura dedicada. Mantenerse en el roadmap como target de 2027. |

**Recomendación para este plan (90 días):** no cambiar nada en automatización. GitHub Actions cubre todos los casos de TRL 5-6.

### Entrega del boletín (actual: HTML sin envío)

| Herramienta | Veredicto | Razón |
|-------------|-----------|-------|
| **Brevo (Sendinblue)** ✅ adoptar | Mejor free tier | 300 emails/día gratis, API REST limpia, templates HTML, listas de distribución. Superior a Mailchimp en el free tier. |
| **Mailchimp** 🟡 alternativa | Conocido, pero más restrictivo | 500 contactos / 1.000 emails/mes gratis. Suficiente para CCHEN pero con más fricción en la API. |
| **GitHub Pages** ✅ adoptar | Complementario | Para publicar el HTML del boletín como página pública o intranet. Gratis, sin dependencias adicionales. |

### Archival de datos (pendiente)

| Herramienta | Veredicto | Razón |
|-------------|-----------|-------|
| **Zenodo** ✅ adoptar en H2 | Estándar de facto | DOIs gratuitos, integración directa con GitHub, aceptado por ANID/CORFO como evidencia de outputs. El corpus CCHEN de 877 papers es citable. |
| **Figshare / OSF** 🟡 alternativa | Similares a Zenodo | Solo si Zenodo tiene limitaciones inesperadas. Mantener Zenodo como primera opción. |

### Frontend (objetivo TRL 7-8)

| Herramienta | Veredicto | Razón |
|-------------|-----------|-------|
| **Streamlit** ✅ mantener para TRL 5-6 | Funciona y está desplegado | No migrar hasta tener presupuesto real y equipo. Complejidad de Angular no justificada con 1 desarrollador. |
| **Angular + TypeScript** 🟡 TRL 7-8 | Objetivo correcto | Correcto para el stack de producción empresarial. Requiere desarrollador frontend dedicado o presupuesto MM$42+. |
| **Metabase OSS** 🟡 alternativa BI | Para usuarios no-técnicos | Si la dirección necesita dashboards propios sin pasar por el developer, Metabase conecta directamente a Supabase. Gratuito y self-hosted. |

### Observabilidad (TRL 7-8)

| Herramienta | Veredicto | Razón |
|-------------|-----------|-------|
| **Prometheus + Grafana** 🟡 TRL 7-8 | Objetivo correcto | Requiere infraestructura dedicada. No justificado en TRL 5-6. |
| **GitHub Actions summaries** ✅ ahora | Suficiente para TRL 5-6 | Los job summaries ya proveen observabilidad del pipeline semanal. |
| **Sentry (free tier)** 🟡 opcional en TRL 6 | Error tracking para el dashboard | Si el dashboard llega a usuarios externos reales, Sentry captura excepciones de Streamlit. Gratis para proyectos pequeños. |

### Autenticación (TRL 7-8)

| Herramienta | Veredicto | Razón |
|-------------|-----------|-------|
| **`internal_auth` actual** ✅ mantener para TRL 5-6 | Funciona para beta privada | El login interno con `secrets.toml` es suficiente para el ciclo de validación y la beta privada. No reemplazar hasta tener OAuth2 institucional. |
| **SAML 2.0 + OAuth2** 🟡 TRL 7-8 | Objetivo correcto | SSO institucional CCHEN. Requiere coordinación con TI de CCHEN. Mantenerse en el roadmap 2027. |
| **Supabase Auth** 🟡 TRL 6 intermedio | Puente hacia OAuth2 | Si se necesita gestión de usuarios más robusta antes de 2027, Supabase Auth (OAuth2, magic link, JWT real) es el paso intermedio natural, sin cambiar de plataforma. |

---

## Riesgos

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|-------------|---------|------------|
| OpenAlex cambia API de grants | Media | Alto (Q1 bloqueado) | Monitorear changelog; alternativa: ROR + Dimensions API |
| Contraparte no disponible para V2, V4 | Media | Medio | Demo grabada como fallback; buffer de 1 semana |
| Rotación de credenciales Supabase | Baja | Alto | Documentar rotación en `playbook_operaciones.md`; variables de entorno en todos los scripts |
| Lens.org token académico vence | Baja | Medio (patents) | USPTO ODP (data.uspto.gov) como fallback para patentes USPTO; EPO OPS para patentes EP |
| PatentsView API interrumpida (migración USPTO ODP) | **Alta (ya ocurrió)** | Bajo | `fetch_patentsview_patents.py` queda en standby; Lens.org es la fuente primaria diseñada en `05_Download_patents.ipynb` |
| Regresión en performance tras `pip install -U` | Baja | Medio | `perf_benchmark_loaders.py` como guardia CI obligatorio |
| IAEA INIS cambia API InvenioRDM | Baja | Bajo | Best-effort; fuente secundaria; no bloquea cierre |

---

## Vista de Gantt simplificada

```
Semana →    13  14  15  16  17  18  19  20  21  22  23  24  25
            |   |   |   |   |   |   |   |   |   |   |   |   |
H1 TRL 5 completo [████████████████████]
  D1 PatentsView             [████]
  D2 BERTopic en dashboard       [████]
  D3-D4 GitHub Pages + Brevo         [████]
  Q1-Q2 OpenAlex/CrossRef     [████]
  Q3-Q4 Calidad datos             [████]

H2 Demo TRL 6                       [████████████████████]
  V1 QA Asistente I+D                   [████]
  V2 Demo institucional                     [████]
  V3 Zenodo DOI                                 [████]
  V4 Portafolio TRL                                 [████]
  V5 E2E smoke                                       [████]

H3 Cierre + decisión TRL 7                      [████████████]
  C1 E2E + tag v1.0                                  [████]
  C2-C3 Informes calidad + perf                          [████]
  C4 Decisión stack TRL 7-8                                 [████]
  C5-C6 Entrega + Retrospectiva                                [██]
```

---

## Próximos pasos (2026 H2 → 2027, fuera del alcance de este plan)

Según el roadmap oficial (`observatorio_cchen_documentacion.tex`):

- **H2 2026 (TRL 6):** Mailchimp/Brevo automático completo, GitHub Pages estable, Zenodo con DOI canónico, Supabase en producción estable
- **2027 (TRL 7-8, budget MM$42+):** Angular + TypeScript SPA, Django REST Framework, PostgreSQL en Huawei Cloud, Apache Airflow DAGs, SAML 2.0 + OAuth2 institucional, Prometheus + Grafana, Object Storage S3-compatible

---

## Referencias a documentos operativos

| Documento | Uso en este plan |
|-----------|-----------------|
| [`Docs/operations/sla_semanal.md`](sla_semanal.md) | Registro semanal de estado por semana |
| [`Docs/operations/comite_kpis.md`](comite_kpis.md) | KPIs K1–K8 como criterio de greenlight por horizonte |
| [`Docs/operations/playbook_operaciones.md`](playbook_operaciones.md) | Runbook de incidentes; incluir en entrega C5 |
| [`Docs/operations/qa_asistente_id.md`](qa_asistente_id.md) | Batería QA para V1 |
| [`Docs/reports/observatorio_cchen_documentacion.tex`](../reports/observatorio_cchen_documentacion.tex) | Fuente de verdad técnica del sistema |
| [`Scripts/check_dashboard_e2e.py`](../../Scripts/check_dashboard_e2e.py) | Test E2E para C1 y V5 |
| [`Scripts/perf_benchmark_loaders.py`](../../Scripts/perf_benchmark_loaders.py) | Guardia de performance C3 |

---

*Versión 2.0 — Generado: 2026-03-23 · Basado en `observatorio_cchen_documentacion.tex` (roadmap TRL oficial) · Próxima revisión: 2026-04-18 (cierre H1)*
