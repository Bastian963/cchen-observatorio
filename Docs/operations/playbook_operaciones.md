# Playbook de Operaciones — Observatorio CCHEN 360° 3 en 1

**Versión:** 1.0  
**Fecha:** 2026-03-28  
**Propietario:** Bastián Ayala I.  
**Repositorio:** https://github.com/Bastian963/cchen-observatorio  
**Portal público dashboard:** https://observatorio.cchen.cl  
**Dashboard interno:** https://obs-int.cchen.cl  
**DSpace público:** https://repo.cchen.cl  
**CKAN público:** https://datos.cchen.cl  

---

## Índice

1. [SLA Matrix v1](#1-sla-matrix-v1)
2. [Inventario de componentes](#2-inventario-de-componentes)
3. [Clasificación de incidentes](#3-clasificación-de-incidentes)
4. [Playbooks por escenario](#4-playbooks-por-escenario)
5. [Mantenimiento preventivo](#5-mantenimiento-preventivo)
6. [Comandos de diagnóstico rápido](#6-comandos-de-diagnóstico-rápido)

---

## 1. SLA Matrix v1

### 1.1 Fuentes de datos (pipeline `arxiv_monitor.yml`)

| Fuente | Criticidad | Frecuencia | Propietario dato | Disponibilidad objetivo | Frescura máxima | En caso de fallo |
|--------|-----------|------------|-----------------|------------------------|-----------------|-----------------|
| **arXiv** | 🔴 Crítica | Semanal (lunes 08:00 UTC) | arXiv.org API (pública) | ≥95% de corridas | 8 días | Incidente P1 — escalar inmediatamente |
| **News** | 🔴 Crítica | Semanal (lunes 08:00 UTC) | RSS / NewsAPI | ≥95% de corridas | 8 días | Incidente P1 — escalar inmediatamente |
| **IAEA INIS** | 🟡 Best-effort | Semanal (lunes 08:00 UTC) | IAEA API (pública, TLS inestable) | ≥50% de corridas (best-effort) | 30 días | Alerta si SKIP ≥2 semanas consecutivas → P2 |
| **Convocatorias ANID** | 🟡 Best-effort | Semanal (lunes 08:00 UTC) | Web scraping anid.cl | ≥60% de corridas (best-effort) | 14 días | Alerta si SKIP ≥2 semanas → P2; ejecutar manualmente |
| **Citation graph** | ⚪ Manual | A demanda | CSV local (`Data/Vigilancia/`) | N/A (no corre en CI) | 60 días | Manual: regenerar con `fetch_openalex_citations.py` |
| **Boletín semanal** | 🟡 Importante | Semanal (tras pipeline) | Generado internamente | ≥95% de corridas | 8 días | Revisar log de `generar_boletin.py` |

### 1.2 Servicios de infraestructura

| Servicio | Criticidad | SLA externo | Verificación | Fallback |
|----------|-----------|-------------|--------------|---------|
| **Supabase (PostgreSQL 15)** | 🔴 Crítica | 99.9% uptime (Supabase SLA) | `python3 Scripts/check_supabase_runtime.py` | CSV local vía `data_loader.py` |
| **Reverse proxy 3 en 1** | 🔴 Crítica | VM pública / interna | `bash Scripts/check_observatorio_public_portal.sh` | Sandbox local o staging |
| **Dashboard Streamlit** | 🔴 Crítica | Público + interno | `bash Scripts/check_observatorio_stack.sh` / `bash Scripts/check_observatorio_public_portal.sh` | Streamlit Cloud sólo como contingencia temporal |
| **DSpace UI + REST** | 🔴 Crítica | Público | `bash Scripts/check_observatorio_public_portal.sh` | N/A |
| **CKAN UI + Action API** | 🔴 Crítica | Público | `bash Scripts/check_observatorio_public_portal.sh` | N/A |
| **GitHub Actions** | 🟡 Importante | 99.9% uptime (GitHub SLA) | `gh run list --workflow arxiv_monitor.yml` | Trigger manual |
| **Groq LLM API** | 🟡 Importante | Best-effort (free tier) | Log del dashboard en runtime | Asistente responde con mensaje de error controlado |

### 1.3 Workflows CI/CD

| Workflow | Disparador | Timeout | SLA objetivo | Alerta si |
|----------|-----------|---------|--------------|-----------|
| `arxiv_monitor.yml` | Lunes 08:00 UTC + manual | 15 min | ≤4 min duración | >4 min o conclusion ≠ success |
| `dashboard_smoke.yml` | Push a `main` | 5 min | ≤2 min | Falla en imports o section load |
| `database_contract.yml` | Push a `main` | 5 min | ≤2 min | Falla en schema o row counts |

---

## 2. Inventario de componentes

### Scripts de ingesta (ejecutables manualmente o vía CI)

| Script | Función | Datos entrada | Datos salida |
|--------|---------|---------------|--------------|
| `Scripts/arxiv_monitor.py` | Fetch semanal arXiv | arXiv API | `Data/Vigilancia/arxiv_monitor_YYYY-MM-DD.csv` |
| `Scripts/news_monitor.py` | Fetch semanal noticias | RSS/NewsAPI | `Data/Vigilancia/news_monitor_YYYY-MM-DD.csv` |
| `Scripts/iaea_inis_monitor.py` | Fetch INIS nuclear | IAEA API | `Data/Vigilancia/iaea_inis_YYYY-MM-DD.csv` |
| `Scripts/convocatorias_monitor.py` | Scraping ANID | anid.cl HTML | `Data/Vigilancia/convocatorias_YYYY-MM-DD.csv` |
| `Scripts/generar_boletin.py` | Boletín HTML semanal | CSVs Vigilancia | `Data/Boletines/boletin_YYYY-SXX.html` |
| `Scripts/fetch_openalex_citations.py` | Citation graph | OpenAlex API | `Data/Vigilancia/citation_graph_YYYY-MM-DD.csv` |

### Scripts de migración a Supabase

| Script | Tablas destino | Notas |
|--------|---------------|-------|
| `Database/migrate_vigilancia.py` | `vigilancia_arxiv`, `vigilancia_news`, `iaea_inis`, `convocatorias` | Best-effort: SKIP si CSV ausente |
| `Database/migrate_dian.py` | `dian_publications` | 133 registros base (2026-03-23) |
| `Database/migrate_citing_papers.py` | `citing_papers` | Requiere `citation_graph_*.csv` local |
| `Database/migrate_embeddings.py` | `paper_embeddings` | 877 embeddings 384-dim |
| `Database/migrate_bertopic.py` | `bertopic_topics`, `bertopic_assignments` | Requiere modelo BERTopic generado |

### Scripts de verificación

| Script | Qué verifica | Cuándo usar |
|--------|-------------|------------|
| `Scripts/check_supabase_runtime.py` | Conectividad + lectura 35 tablas | Tras deploy o ante dudas de conexión |
| `Scripts/check_dashboard_smoke.py` | Imports, secciones, data_loader | Tras cambios en Dashboard/ |
| `Scripts/check_database_contract.py` | Schema + row counts vs. esperados | Tras migración o cambios de schema |
| `Scripts/check_observatorio_stack.sh` | Salud local end-to-end del stack 3 en 1 | Tras reinicios o reconstrucción local |
| `Scripts/check_observatorio_prod_overlay.sh` | Contrato del overlay productivo por URL | Antes de merge o despliegue |
| `Scripts/check_observatorio_public_url.sh` | Salud por dominios publicados | Tras deploy en VM |
| `Database/data_quality.py` | Calidad e integridad CSVs locales | Mensual o antes de migración masiva |

---

## 3. Clasificación de incidentes

| Prioridad | Definición | Tiempo de respuesta | Tiempo de resolución |
|-----------|-----------|--------------------|--------------------|
| **P1 — Crítico** | arXiv=0 o News=0, `obs-int`/`repo-int`/`datos-int` caídos, Supabase inaccesible, migración falla total | Inmediata (mismo día) | ≤24 horas |
| **P2 — Alto** | IAEA SKIP ≥2 semanas, convocatorias SKIP ≥2 semanas, smoke del observatorio falla, database contract falla | ≤2 días hábiles | ≤5 días hábiles |
| **P3 — Medio** | una superficie responde degradada, arXiv 1-9 filas, News 1-19 filas, duración job >4 min o boletín sin generar | ≤1 semana | Próxima corrida |
| **P4 — Bajo** | Warnings en log, campos vacíos < umbral, documentación desactualizada | ≤1 mes | Backlog |

---

## 4. Playbooks por escenario

---

### PB-01: arXiv o News retornan 0 filas (P1)

**Síntoma:** Punto 3 o 4 del checklist = ❌ (0 filas o SKIP)

```bash
# 1. Diagnóstico: ver log completo del run fallido
RUN_ID=$(gh run list --workflow arxiv_monitor.yml --limit 1 --json databaseId -q '.[0].databaseId')
gh run view "$RUN_ID" --log | grep -A5 -B5 "arXiv\|news_monitor"

# 2. Ejecutar script localmente para aislar el problema
cd /Users/bastianayalainostroza/Dropbox/CCHEN
python3 Scripts/arxiv_monitor.py     # o news_monitor.py
ls -lh Data/Vigilancia/              # verificar si CSV fue creado

# 3. Si hay datos locales, subir a Supabase manualmente
python3 Database/migrate_vigilancia.py

# 4. Si el script falla, revisar API keys / rate limits
# arXiv: sin key requerida; verificar conectividad a export.arxiv.org
# News: revisar variable NEWS_API_KEY en .env

# 5. Trigger manual del workflow tras fix
gh workflow run arxiv_monitor.yml
```

**Escalar si:** el problema persiste >24h o si la API fuente está caída.

---

### PB-02: IAEA INIS con TLS/SSL error (P2/P3)

**Síntoma:** Punto 7 del checklist = ⚠️ TLS error, SKIP en log

```bash
# 1. Verificar si es problema temporal (reintentar directo)
python3 Scripts/iaea_inis_monitor.py

# 2. Si persiste, probar con proxy/sin SSL verify (solo diagnóstico local)
# NO implementar en producción sin autorización

# 3. Verificar estado de la API
# URL: https://inis.iaea.org/search/
# Contacto técnico INIS: inis-secretariat@iaea.org

# 4. Si SKIP ≥2 semanas consecutivas: registrar en sla_semanal.md y crear issue
gh issue create \
  --title "IAEA INIS: SKIP ≥2 semanas (TLS error persistente)" \
  --body "Fecha inicio: YYYY-MM-DD. Ver log run ID: $RUN_ID. Acción: contactar soporte IAEA o ajustar queries." \
  --label "data-pipeline,alerta"
```

---

### PB-03: Convocatorias ANID sin archivo (P2/P3)

**Síntoma:** Punto 8 del checklist = ⚠️ "Sin archivo de convocatorias aún"

```bash
# 1. Ejecutar scraper manualmente (fuera del runner CI)
python3 Scripts/convocatorias_monitor.py
ls -lh Data/Vigilancia/convocatorias_*

# 2. Si el scraper falla: revisar cambios en el HTML de anid.cl
# Inspeccionar: https://www.anid.cl/concursos/
# Los selectores CSS pueden cambiar tras rediseño del sitio

# 3. Alternativa: curar manualmente el CSV
# Estructura esperada: ver Data/Vigilancia/convocatorias_*.csv existentes
# Copiar última versión y actualizar manualmente las fechas

# 4. Si SKIP ≥2 semanas: crear issue + actualizar scraper
gh issue create \
  --title "Convocatorias ANID: SKIP ≥2 semanas (scraper desactualizado)" \
  --body "Fecha inicio: YYYY-MM-DD. Revisar selectores CSS en convocatorias_monitor.py." \
  --label "data-pipeline,alerta"
```

---

### PB-04: Migración Supabase falla parcialmente (P1/P2)

**Síntoma:** Punto 5 o 6 del checklist: filas migradas ≠ filas leídas (diferencia >10%)

```bash
# 1. Verificar conectividad Supabase
python3 Scripts/check_supabase_runtime.py

# 2. Verificar contrato de schema
python3 Scripts/check_database_contract.py

# 3. Ejecutar migración aislada
python3 Database/migrate_vigilancia.py 2>&1 | tee /tmp/migrate_vigilancia.log
grep -E "ERROR|error|failed|SKIP" /tmp/migrate_vigilancia.log

# 4. Si hay error de schema (columna ausente o tipo incorrecto)
# Revisar Database/schema.sql y comparar con tabla en Supabase Dashboard
# URL: https://supabase.com/dashboard/project/{project_id}/editor

# 5. Si el error es de unicidad (duplicados): verificar lógica de upsert
# migrate_vigilancia.py usa ON CONFLICT DO UPDATE — revisar constraint definida
```

---

### PB-05: Una superficie 3 en 1 cae o responde degradada (P1)

**Síntoma:** `obs-int`, `repo-int` o `datos-int` no responden, o una sección del dashboard falla por dependencias del stack

```bash
# 1. Estado general local del stack
bash Scripts/check_observatorio_stack.sh
bash Scripts/wait_and_check_observatorio_stack.sh

# 2. Smoke del dashboard
python3 Scripts/check_dashboard_smoke.py

# 3. E2E check completo
python3 Scripts/check_dashboard_e2e.py

# 4. Verificar que data_loader funciona
cd Dashboard
python3 -c "import data_loader; print(data_loader.TABLE_LOAD_STATUS)"

# 5. Si falla import de sección específica
python3 -c "import sections.{nombre_seccion}"

# 6. Verificar Supabase accesible (el dashboard usa fallback a CSV si falla)
python3 Scripts/check_supabase_runtime.py

# 7. Si el problema parece del overlay productivo
bash Scripts/check_observatorio_prod_overlay.sh

# 8. Si el problema aparece sólo en la VM publicada
bash Scripts/check_observatorio_public_url.sh
```

Escalamiento:

- si falla sólo `obs-int`, revisar `dashboard` + `reverse-proxy`
- si falla `repo-int`, revisar `dspace-backend`, `dspace-frontend` y la ruta `/server`
- si falla `datos-int`, revisar `ckan`, `ckan-solr` y `ckan-db`
- usar Streamlit Cloud sólo como contingencia temporal para demo del dashboard, no como resolución principal

---

### PB-06: `database_contract.yml` o `dashboard_smoke.yml` fallan en push (P2)

**Síntoma:** Push a `main` → CI rojo

```bash
# 1. Ver log del workflow fallido
gh run list --workflow database_contract.yml --limit 3
RUN_ID=<id>
gh run view "$RUN_ID" --log

# 2. Reproducir localmente antes de hacer push
python3 Scripts/check_database_contract.py
python3 Scripts/check_dashboard_smoke.py

# 3. Si es schema mismatch: revisar última migración aplicada
# 4. Si es import error: revisar requirements.txt y dependencias instaladas
pip install -r requirements.txt
pip install -r Dashboard/requirements.txt
```

---

### PB-07: Job `arxiv_monitor.yml` dura >8 min (P2)

**Síntoma:** Punto 2 del checklist = ⚠️ o ❌ en duración

```bash
# 1. Ver qué step tardó más
gh run view "$RUN_ID" --json jobs -q '.jobs[].steps[] | "\(.number) \(.name) \(.completedAt)"'

# 2. Candidatos habituales:
#    - iaea_inis_monitor.py: timeouts por TLS (9 queries × 30s = 270s máx)
#    - migrate_vigilancia.py: batch inserts lentos
#    - generar_boletin.py: si procesa mucho texto

# 3. Mitigación inmediata: reducir timeout por query en iaea_inis_monitor.py
# timeout=10 → timeout=5 en el script

# 4. Si el workflow supera 15 min → GitHub lo cancela automáticamente
# Revisar si hay pasos que se pueden paralelizar o mover a schedule separado
```

---

## 5. Mantenimiento preventivo

### Semanal (cada lunes, tras corrida automática)
- [ ] Completar checklist en [sla_semanal.md](sla_semanal.md)
- [ ] Actualizar KPIs de comité en [comite_kpis.md](comite_kpis.md)
- [ ] Ejecutar batería QA del asistente en [qa_asistente_id.md](qa_asistente_id.md)
- [ ] Ejecutar `bash Scripts/check_observatorio_stack.sh`
- [ ] Actualizar historial IAEA/Convocatorias si hay SKIP
- [ ] Si nivel = 🔴: abrir issue antes del martes

### Mensual (primer lunes de cada mes)
- [ ] Ejecutar `Database/data_quality.py --output Docs/reports/calidad_YYYY-MM.csv`
- [ ] Revisar top 5 brechas de calidad y crear tareas
- [ ] Verificar que `requirements.txt` esté actualizado (`pip list --outdated`)
- [ ] Revisar logs de Groq API: latencia y errores del asistente
- [ ] Confirmar que `paper_embeddings` tiene cobertura ≥80% de publications

### Trimestral
- [ ] Actualizar `ARCHITECTURE.md` con cambios de TRL y hitos
- [ ] Revisar y actualizar este playbook
- [ ] Ejecutar `build_operational_core.py` si hay nuevas publicaciones masivas
- [ ] Probar `bash Scripts/check_observatorio_prod_overlay.sh`
- [ ] Validar backup + restore mínimo del stack 3 en 1

---

## 6. Comandos de diagnóstico rápido

```bash
# ── Estado general del observatorio ──────────────────────────────────────────

# Último run del pipeline semanal
gh run list --workflow arxiv_monitor.yml --limit 5 \
  --json databaseId,conclusion,createdAt,displayTitle \
  -q '.[] | "\(.databaseId) | \(.conclusion) | \(.createdAt)"'

# Log resumido del último run (checklist 10 puntos)
RUN_ID=$(gh run list --workflow arxiv_monitor.yml --limit 1 --json databaseId -q '.[0].databaseId')
gh run view "$RUN_ID" --log | grep -E \
  "Estado operativo|arXiv|News.*fila|IAEA|SKIP|convocatorias|Boletín guardado|filas migradas|Leídas:|TLS"

# ── Supabase ──────────────────────────────────────────────────────────────────

# Verificar conexión y lectura de todas las tablas
python3 Scripts/check_supabase_runtime.py

# Contrato de schema
python3 Scripts/check_database_contract.py

# ── Dashboard ─────────────────────────────────────────────────────────────────

# Smoke test (imports, secciones, data_loader)
python3 Scripts/check_dashboard_smoke.py

# Estado local end-to-end
bash Scripts/check_observatorio_stack.sh

# Contrato del overlay productivo
bash Scripts/check_observatorio_prod_overlay.sh

# Sandbox local de publicación por URL
bash Scripts/prepare_local_public_demo.sh

# ── Data quality ──────────────────────────────────────────────────────────────

# Reporte calidad CSVs locales (consola)
python3 Database/data_quality.py

# Reporte con CSV de salida
python3 Database/data_quality.py --output Docs/reports/calidad_$(date +%Y-%m).csv

# ── Pipeline manual (ejecutar fuera de CI) ────────────────────────────────────

cd /Users/bastianayalainostroza/Dropbox/CCHEN

# Ingesta individual
python3 Scripts/arxiv_monitor.py
python3 Scripts/news_monitor.py
python3 Scripts/iaea_inis_monitor.py
python3 Scripts/convocatorias_monitor.py

# Migración a Supabase
python3 Database/migrate_vigilancia.py

# Boletín semanal
python3 Scripts/generar_boletin.py

# Trigger manual del workflow completo
gh workflow run arxiv_monitor.yml
```

---

*Última actualización: 2026-03-23 | Próxima revisión: 2026-06-23*
