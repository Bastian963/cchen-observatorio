# CCHEN — Observatorio Tecnológico I+D+i+Tt

[![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)](https://www.python.org)
[![Supabase](https://img.shields.io/badge/Supabase-PostgreSQL-3ECF8E?logo=supabase)](https://supabase.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Comisión Chilena de Energía Nuclear — Proyecto CORFO CCHEN 360**
**Responsable:** Bastián Ayala Inostroza · Analista de Datos I+D
**Inicio:** 2024 · **Estado:** Plataforma 3 en 1 en consolidación (interno + portal público por fases)

---

## Overview

El **Observatorio Tecnológico CCHEN** ya no se presenta sólo como un dashboard, sino como una **plataforma institucional de conocimiento 3 en 1**:

- `Observatorio Analítico`: inteligencia, vigilancia y apoyo a decisiones.
- `Repositorio Institucional DSpace`: publicaciones, informes y memoria técnica.
- `Portal de Datos CKAN`: datasets, series y recursos descargables.

Regla operativa del sistema:

- `DSpace` conserva documentos y publicaciones.
- `CKAN` conserva datos publicables.
- el `dashboard` consume, relaciona y explica; no reemplaza a ninguno de los dos.

---

## Plataforma Institucional 3 en 1

| Superficie | Rol | Estado actual | URL pública |
| --- | --- | --- | --- |
| `Observatorio Analítico` | Indicadores, vigilancia, asistente y narrativa ejecutiva | Beta pública en preparación | `https://observatorio.cchen.cl` |
| `Repositorio Institucional DSpace` | Publicaciones, informes, policy briefs y documentos | Publicación documental canónica | `https://repo.cchen.cl` |
| `Portal de Datos CKAN` | Datasets, series, recursos y metadatos descargables | Publicación de datos canónica | `https://datos.cchen.cl` |

Documentación base:

- [ARCHITECTURE.md](ARCHITECTURE.md)
- [INTEGRACION_OBSERVATORIO.md](INTEGRACION_OBSERVATORIO.md)
- [Docs/PLAN_TRABAJO_2026.md](Docs/PLAN_TRABAJO_2026.md)
- [Docs/matriz_publicacion_3_en_1.md](Docs/matriz_publicacion_3_en_1.md)
- [Docs/operations/runbook_plataforma_3_en_1.md](Docs/operations/runbook_plataforma_3_en_1.md)
- [Docs/operations/runbook_publicacion_vm_observatorio_3en1.md](Docs/operations/runbook_publicacion_vm_observatorio_3en1.md)
- [Docs/operations/runbook_backup_restore_observatorio_3en_1.md](Docs/operations/runbook_backup_restore_observatorio_3en_1.md)
- [Docs/operations/acceso_interno_observatorio_3en1.md](Docs/operations/acceso_interno_observatorio_3en1.md)
- [Docs/operations/estado_beta_publica_3en1.md](Docs/operations/estado_beta_publica_3en1.md)
- [Docs/operations/runbook_oracle_piloto_publico_3en1.md](Docs/operations/runbook_oracle_piloto_publico_3en1.md)

Para desarrollo local y operación sobre `localhost`, usa el runbook:

- [Docs/operations/runbook_plataforma_3_en_1.md](Docs/operations/runbook_plataforma_3_en_1.md)

---

## Superficies de publicación

La estrategia de despliegue queda separada en dos superficies:

- **Portal público 3 en 1**
  - `https://observatorio.cchen.cl` → dashboard público
  - `https://repo.cchen.cl` → DSpace público
  - `https://datos.cchen.cl` → CKAN público
- **Superficie interna**
  - `https://obs-int.cchen.cl` → dashboard interno completo

Regla operativa:

- el portal público sólo muestra vistas y activos publicables;
- la superficie interna mantiene `internal_auth`, diagnóstico operativo y capas sensibles;
- `DSpace` y `CKAN` siguen siendo las fuentes de verdad públicas.

Documentos recomendados para esta separación:

- [Docs/matriz_visibilidad_publico_interno_3en1.md](Docs/matriz_visibilidad_publico_interno_3en1.md)
- [Docs/operations/runbook_publicacion_portal_publico_3en1.md](Docs/operations/runbook_publicacion_portal_publico_3en1.md)
- [Docs/operations/estado_beta_publica_3en1.md](Docs/operations/estado_beta_publica_3en1.md)
- [Docs/operations/runbook_oracle_piloto_publico_3en1.md](Docs/operations/runbook_oracle_piloto_publico_3en1.md)

Baseline operativo actual:

- rama fuente de verdad: `feat/observatorio-3en1-public-portal`
- tag técnico de referencia: `observatorio-3en1-public-beta-ready-2026-03-29`
- gate de repo previo a la VM pública:

```bash
bash Scripts/check_public_beta_release.sh
```

- `docker-compose.yml` legado queda fuera del baseline institucional y no debe mezclarse con esta ruta.

## Publicación interna por URL

La vía canónica para compartir el Observatorio 3 en 1 dentro de CCHEN es una VM Linux con Docker Compose, `Nginx` reverse proxy, TLS institucional y subdominios separados:

- `https://obs-int.cchen.cl` → dashboard
- `https://repo-int.cchen.cl` → DSpace UI y `/server`
- `https://datos-int.cchen.cl` → CKAN

Piezas versionadas para este despliegue:

- `docker-compose.observatorio.prod.yml`
- `.env.prod.example`
- `deploy/nginx/templates/observatorio-public.conf.template`
- `Scripts/check_observatorio_prod_overlay.sh`
- `Scripts/check_observatorio_public_url.sh`
- `Scripts/wait_and_check_observatorio_public_url.sh`
- `Scripts/backup_observatorio_prod.sh`
- `Scripts/prepare_local_public_demo.sh`

Runbooks asociados:

- `Docs/operations/runbook_publicacion_vm_observatorio_3en1.md`
- `Docs/operations/runbook_publicacion_portal_publico_3en1.md`
- `Docs/operations/runbook_backup_restore_observatorio_3en_1.md`
- `Docs/operations/acceso_interno_observatorio_3en1.md`

---

## Arquitectura de producto

La arquitectura funcional se ordena así:

- `Dashboard`: lectura ejecutiva, trazabilidad analítica y descubrimiento contextual.
- `DSpace`: publicación y preservación documental.
- `CKAN`: publicación y distribución de datos.
- `Supabase`, `DuckDB`, `Scripts/` y `Data/`: capa de preparación, curación y análisis, no la capa pública final por sí sola.

El stack local canónico queda en `docker-compose.observatorio.yml`.

### Stack tecnológico

| Capa | Tecnología | Rol |
|------|-----------|-----|
| Analítica | Streamlit 1.50 | Dashboard interactivo modular |
| Lógica | Python 3.10+, pandas 2.3, plotly 6.6 | Procesamiento y visualización |
| Base analítica | Supabase (PostgreSQL 15) | Almacenamiento persistente, 35 tablas con RLS |
| Query local | DuckDB | Consultas analíticas rápidas sobre CSV |
| Repositorio documental | DSpace 7.x | Publicaciones, informes y documentos |
| Portal de datos | CKAN 2.10 | Datasets, recursos y Action API |
| Índices búsqueda | Solr | Descubrimiento en DSpace y CKAN |
| LLM principal | Groq API — llama-3.3-70b-versatile | Asistente I+D conversacional |
| Embeddings | sentence-transformers | Búsqueda semántica RAG |
| Reportes | reportlab + matplotlib | Generación de PDF con gráficos |

---

## Runbook de actualización y monitoreo

Consulta el flujo detallado de actualización, registro de logs y monitoreo en:
- [Docs/operations/runbook_actualizacion_monitoreo.md](Docs/operations/runbook_actualizacion_monitoreo.md)

Y para la operación del stack 3 en 1:
- [Docs/operations/runbook_plataforma_3_en_1.md](Docs/operations/runbook_plataforma_3_en_1.md)
- [Docs/operations/runbook_publicacion_vm_observatorio_3en1.md](Docs/operations/runbook_publicacion_vm_observatorio_3en1.md)

---

## Actualización automática de datos institucionales

El observatorio cuenta con un workflow de GitHub Actions que ejecuta semanalmente (lunes 08:00 UTC) los scripts principales de descarga y actualización de outputs institucionales (Zenodo, Europe PMC, OpenAIRE, etc.).

- El workflow está en `.github/workflows/actualizacion_datos.yml`.
- Instala dependencias, ejecuta los scripts y hace commit/push automático de los datos nuevos si hay cambios.
- Permite agregar más scripts o pasos según evolucione el observatorio.
- La notificación por email ante fallos queda documentada como mejora futura.

**¿Cómo funciona?**
1. Corre los scripts de descarga y actualización de datos institucionales.
2. Si hay cambios en los datos, los commitea y pushea automáticamente.
3. Permite ejecución manual desde la interfaz de GitHub Actions.
4. El log de cada corrida queda registrado en la pestaña Actions del repositorio.

Consulta el workflow y sus pasos en:
- [.github/workflows/actualizacion_datos.yml](.github/workflows/actualizacion_datos.yml)

---

## Validación de afiliación institucional vía ORCID

El observatorio implementa un flujo automatizado para validar y actualizar la afiliación institucional de sus investigadores usando datos de ORCID y padrón interno. Este proceso combina extracción automática, cruce de datos y revisión manual para asegurar la máxima calidad y confiabilidad.

- El script principal (`Scripts/build_planta_orcid_exports.py`) cruza padrón y ORCID, generando reportes de estado y brechas.
- El proceso de auditoría (`Scripts/_tmp_audit_orcid.py`) identifica casos dudosos, duplicados y empleadores no reconocidos.
- **Siempre se requiere una revisión humana** para validar casos ambiguos o con información incompleta.

Consulta el detalle del flujo y recomendaciones en:

- [Docs/plan_validacion_orcid.md](Docs/plan_validacion_orcid.md)

---

## Dashboard Sections

El dashboard está organizado en 12 secciones, accesibles desde la barra lateral:

### 1. Plataforma Institucional
Portada institucional del modelo 3 en 1. Explica la separación funcional entre dashboard, DSpace y CKAN, muestra enlaces profundos a cada superficie y entrega una lectura rápida del estado operativo del stack local.

### 2. Panel de Indicadores
Vista ejecutiva consolidada con KPIs principales: total de publicaciones, citas acumuladas, porcentaje en Q1/Q2, financiamiento ANID total, personas formadas. Incluye franja operativa con estado de sesión: datasets remotos, fallbacks locales activos, datasets no disponibles y snapshot local más reciente.

### 3. Producción Científica
Análisis bibliométrico completo: evolución temporal, distribución por cuartil SJR, revistas de publicación, acceso abierto, conceptos temáticos OpenAlex, publicaciones DIAN internas y comparación con registros EuroPMC. Soporta filtros por año, tipo, cuartil y área temática.

### 4. Redes y Colaboración
Mapa choropleth de co-autorías internacionales, tabla de instituciones colaboradoras con ancla ROR, análisis de perfiles ORCID de investigadores CCHEN, y visualización de convenios nacionales (84) y acuerdos internacionales (91).

### 5. Vigilancia Tecnológica
Monitor de tendencias en áreas nucleares clave (dosimetría, medicina nuclear, reactores, radiofarmacia): arXiv RSS, noticias Google, documentos IAEA INIS, análisis de tópicos BERTopic y Semantic Scholar. Incluye perfiles institucionales para matching.

### 6. Financiamiento I+D
Repositorio ANID completo: 24 proyectos adjudicados, $1.337 MM CLP en financiamiento, distribución por instrumento (Fondecyt Regular, Iniciación, Postdoctorado, Anillos). Complementado con fuentes CORFO, IAEA TC y funding detectado por OpenAlex/CrossRef.

### 7. Convocatorias y Matching
Calendario de convocatorias abiertas y próximas (ANID, IAEA, Horizonte Europa, ERC, MSCA). Sistema de matching institucional formal con score de adecuación, elegibilidad, readiness y acción recomendada por perfil CCHEN.

### 8. Transferencia y Portafolio
Portafolio tecnológico semilla con clasificación TRL, unidad responsable y potencial de transferencia. Outputs DataCite y OpenAIRE asociados a CCHEN vía ROR institucional.

### 9. Modelo y Gobernanza
Registro canónico de entidades: 604 personas, 24 proyectos, 26 convocatorias y 657 enlaces operativos. Modelo de gobernanza con fuentes, timestamps de actualización y calidad de datos.

### 10. Formación de Capacidades
Panel de capital humano I+D: 97 personas formadas (2022–2025), distribución por modalidad (tesista, memorista, becario, profesional), centro, universidad tutora y evolución anual.

### 11. Asistente I+D
Asistente conversacional basado en RAG + Groq LLM (llama-3.3-70b-versatile). Inyecta contexto de los 5 papers más relevantes (búsqueda semántica), indicadores clave y datos de convocatorias activas. Genera informes PDF descargables con gráficos contextuales automáticos.

### 12. Grafo de Citas
Visualización interactiva con plotly + networkx del grafo de citas OpenAlex: 714 papers CCHEN con 9.840 citas totales y 8.499 papers externos citantes. Análisis de instituciones y países que citan a CCHEN, impacto por área temática.

---

## Database Schema

La base de datos Supabase contiene **35 tablas operativas**: **31 públicas** y **4 sensibles**. El DDL completo está en `Database/schema.sql`.

| Módulo | Tablas principales | Acceso |
|-------|--------------------|--------|
| Producción científica | `publications`, `publications_enriched`, `authorships`, `crossref_data`, `concepts` | Público |
| Producción interna | `dian_publications` | Público |
| Propiedad intelectual | `patents` | Público |
| Financiamiento | `anid_projects`, `funding_complementario` | `funding_complementario` sensible |
| Capital humano e investigadores | `capital_humano`, `researchers_orcid` | `capital_humano` sensible |
| Ecosistema institucional | `convenios_nacionales`, `acuerdos_internacionales`, `institution_registry`, `institution_registry_pending_review` | Público |
| Outputs de investigación | `datacite_outputs`, `openaire_outputs` | Público |
| Núcleo institucional | `entity_registry_personas`, `entity_registry_proyectos`, `entity_registry_convocatorias`, `entity_links` | `entity_registry_personas` y `entity_links` sensibles |
| Convocatorias y matching | `perfiles_institucionales`, `convocatorias`, `convocatorias_matching_rules`, `convocatorias_matching_institucional` | Público |
| Vigilancia y analítica | `iaea_inis_monitor`, `arxiv_monitor`, `news_monitor`, `citation_graph`, `europmc_works`, `bertopic_topics`, `bertopic_topic_info`, `citing_papers` | Público |
| Búsqueda semántica | `paper_embeddings` | Público |
| Gobernanza de datos | `data_sources` | Público |

---

## Semantic Search / RAG

El Asistente I+D implementa un pipeline de Retrieval-Augmented Generation (RAG):

### Pipeline completo

```
1. PRE-CÓMPUTO (offline, ejecutar manualmente)
   Scripts/build_embeddings.py
   → Lee cchen_openalex_works.csv
   → Concatena título + abstract por paper
   → Modelo: paraphrase-multilingual-MiniLM-L12-v2 (384 dims, multilingüe)
   → Salida: Data/Publications/cchen_embeddings.npy  (matriz N×384 float32)
             Data/Publications/cchen_embeddings_meta.csv

2. BÚSQUEDA (runtime, en cada consulta al asistente)
   Scripts/semantic_search.py
   → Codifica la consulta del usuario con el mismo modelo
   → Calcula similitud coseno: emb @ q_vec  (dot product, vectores normalizados)
   → Retorna top-5 papers más similares con score

3. INYECCIÓN EN PROMPT (Dashboard/sections/asistente_id.py)
   → Los top-5 papers se formatean como contexto
   → Se insertan en el system prompt antes de la consulta al LLM
   → Groq llama-3.3-70b-versatile genera la respuesta con ese contexto

4. FALLBACK
   → Si los embeddings no están pre-calculados, el asistente sigue funcionando
   → Solo se pierde la recuperación semántica de papers específicos
```

### Ejecutar por primera vez

```bash
# Instalar dependencias
pip install sentence-transformers

# Calcular embeddings (requiere ~5 minutos en CPU)
python3 Scripts/build_embeddings.py

# Verificar búsqueda
python3 Scripts/semantic_search.py "dosimetría radiación reactores nucleares"
```

### Evaluación rápida de retrieval (sin Groq)

```bash
# sanity run publication_rag (filtra automáticamente prompts publication_rag)
bash Scripts/run_publication_rag_sanity.sh

# con comparación contra corrida previa
bash Scripts/run_publication_rag_sanity.sh \
  --compare-with Docs/reports/assistant_eval_run_publication_rag_topk5.csv

# modo salida mínima (CI)
bash Scripts/run_publication_rag_sanity.sh --quiet

# modo JSON estructurado (CI)
bash Scripts/run_publication_rag_sanity.sh --json
```

Salida esperada:

- CSV de corrida en `Docs/reports/assistant_eval_run_<run_label>.csv`
- Si usas `--compare-with`, CSV comparativo en `Docs/reports/assistant_eval_compare_<run_label>.csv`

---

## Data Update Pipeline

### Paso a paso para actualizar datos

```bash
# 1. Descargar/actualizar publicaciones desde OpenAlex
jupyter nbconvert --to notebook --execute Notebooks/01_Download_publications.ipynb

# 2. Enriquecer con CrossRef (financiadores, abstracts)
jupyter nbconvert --to notebook --execute Notebooks/02_CrossRef_enrichment.ipynb

# 3. Descargar citas y grafo de citación
python3 Scripts/fetch_openalex_citations.py          # ~15 min para 877 papers

# 4. Actualizar EuroPMC (literatura biomédica)
python3 Scripts/fetch_europmc.py

# 5. Actualizar DataCite outputs (datasets CCHEN)
python3 Scripts/fetch_datacite_outputs.py

# 6. Actualizar OpenAIRE (outputs vía ORCID)
python3 Scripts/fetch_openaire_outputs.py

# 7. Recalcular embeddings semánticos
python3 Scripts/build_embeddings.py

# 8. Validar calidad de datos
python3 Database/data_quality.py

# 9. Migrar publicaciones principales a Supabase
python3 Database/migrate_to_supabase.py

# 10. Migrar grafo de citas a Supabase (8.499 filas)
python3 Database/migrate_citing_papers.py

# 11. Migrar EuroPMC (74 papers con PMID/PMCID)
python3 Database/migrate_europmc.py

# 12. Migrar vigilancia tecnológica (citation_graph + arxiv + iaea + noticias)
python3 Database/migrate_vigilancia.py

# 13. Migrar BERTopic (358 papers + 23 topics)
python3 Database/migrate_bertopic.py

# 14. Migrar convocatorias y reglas de matching
python3 Database/migrate_convocatorias.py

# 15. Migrar embeddings semánticos a pgvector (877 × 384 dims)
python3 Database/migrate_embeddings.py
```

### Scripts de vigilancia (automatizados vía GitHub Actions)

Estos scripts corren cada lunes a las 08:00 UTC:

| Script | Salida | Descripción |
|--------|--------|-------------|
| `Scripts/arxiv_monitor.py` | `Data/Vigilancia/arxiv_monitor.csv` | Papers nuevos en arXiv relevantes a CCHEN |
| `Scripts/news_monitor.py` | `Data/Vigilancia/news_monitor.csv` | Noticias Google sobre CCHEN y energía nuclear |
| `Scripts/convocatorias_monitor.py` | `Data/Vigilancia/convocatorias_curadas.csv` | Convocatorias abiertas ANID y fondos internacionales |
| `Scripts/iaea_inis_monitor.py` | `Data/Vigilancia/iaea_inis_monitor.csv` | Vigilancia de literatura nuclear en IAEA INIS |

Comportamiento operativo del workflow `arxiv_monitor.yml`:

- `arXiv` y `news` son rutas principales y se esperan en cada corrida.
- `convocatorias` e `IAEA INIS` corren en modo `best-effort` con `continue-on-error: true` por dependencia externa (scraping/estabilidad API).
- La migración `Database/migrate_vigilancia.py` también corre con `continue-on-error: true` y puede registrar `SKIP` por fuente cuando no existe el CSV esperado.
- El paso de commit agrega solo archivos existentes para evitar errores de `pathspec` cuando una fuente opcional no generó salida.
- El log incluye un resumen operativo por fuente con estado `OK` o `SKIP`, más conteo de filas cuando aplica.

---

## Setup & Deployment

### Gate de beta pública del portal

Antes de preparar una VM pública o congelar un SHA de publicación, deja el repo en verde con:

```bash
bash Scripts/check_public_beta_release.sh
```

Ese gate valida:

- smoke local del dashboard,
- contrato del overlay público,
- modo público real del dashboard sin muralla beta ni secciones internas.

### Instalación local

```bash
# 1. Clonar repositorio
git clone --recurse-submodules https://github.com/Bastian963/cchen-observatorio.git
cd cchen-observatorio

# Si ya clonaste antes sin submódulos:
git submodule update --init --recursive

# 2. Instalar dependencias
cd Dashboard
pip install -r requirements.txt

# 3. Configurar secrets
mkdir -p .streamlit
cp .streamlit/secrets.toml.example .streamlit/secrets.toml

# Editar .streamlit/secrets.toml con una configuración mínima:
cat > .streamlit/secrets.toml << EOF
GROQ_API_KEY = "gsk_..."        # Obtener gratis en https://console.groq.com

[supabase]
url         = "https://xxxx.supabase.co"
anon_key    = "eyJ..."
service_role_key = "sb_service_role_..."   # requerido para datasets sensibles en beta privada
data_source = "auto"             # auto | local | supabase_public

[internal_auth]
enabled = true
beta_badge = "Beta interna"
beta_title = "Observatorio Tecnológico CCHEN"
beta_message = "Acceso privado para revisión funcional, validación de datos sensibles y migración progresiva del observatorio."

[[internal_auth.users]]
username = "tu.usuario"
password = "cambiar-por-una-clave-segura"
role = "admin"
can_view_sensitive = true
EOF

# 4. (Opcional) Configurar ruta de datos si Data/ no está junto a Dashboard/
export CCHEN_DATA_ROOT="/ruta/absoluta/a/Data"

# 5. Lanzar dashboard
streamlit run app.py
```

Notas de clonado:

- `ckan-src` se mantiene como submódulo limpio apuntando a CKAN upstream.
- La customización operativa local de CKAN vive en `ckan/`.
- El frontend DSpace versionado para Docker vive en `dspace-frontend/` como snapshot estático mínimo; el repo Angular completo no se publica en esta pasada.

### Modos de fuente de datos

El dashboard soporta tres modos configurables via `data_source` en secrets.toml:

| Modo | Comportamiento |
|------|---------------|
| `auto` (recomendado) | Intenta leer tablas públicas desde Supabase; si falla, usa CSVs locales. Las tablas sensibles usan `service_role_key` si está disponible |
| `local` | Solo usa archivos locales en `Data/` (sin Supabase) |
| `supabase_public` | Fuerza lectura remota de tablas públicas; falla si Supabase no está disponible. Las tablas sensibles siguen requiriendo `service_role_key` |

### Franja operativa y frescura

- La franja superior del dashboard resume el estado de carga de la sesión actual usando el registro runtime `TABLE_LOAD_STATUS`.
- Expone, por dataset instrumentado, si la lectura efectiva fue `Supabase pública`, `Supabase privada`, `Fallback local`, `Local` o `No disponible`.
- Muestra además el snapshot local más reciente detectado en `Data/`, útil para distinguir entre conectividad remota y respaldo disponible en el host.
- Cuando `data_source != local`, la fecha mostrada corresponde al respaldo local conocido, no necesariamente al último sync remoto de Supabase.

### Carga lazy por sección

- El dashboard ya no precarga todas las capas al iniciar.
- `Dashboard/app.py` mantiene un registro de loaders cacheados por dataset y arma el `ctx` solo con los datasets requeridos por la sección activa.
- La navegación entre secciones reutiliza `st.cache_data`, de modo que los datasets ya consultados se reaprovechan sin volver a leerlos en cada cambio.
- La franja operativa y el inspector reflejan el estado de la sección actual, no un preload global de todo el observatorio.

### Contingencia en Streamlit Cloud

Streamlit Cloud queda como vía secundaria o de contingencia para mostrar sólo el dashboard. Ya no es la ruta principal para compartir la plataforma 3 en 1 completa.

1. Fork o push del repositorio a GitHub
2. Ir a [share.streamlit.io](https://share.streamlit.io) → New app
3. Seleccionar repo, rama `main`, archivo `Dashboard/app.py`
4. Streamlit Cloud instalará automáticamente el `requirements.txt` de la raíz del repo
5. En **Secrets**, agregar una configuración de beta privada:

```toml
GROQ_API_KEY = "gsk_..."

[supabase]
url         = "https://xxxx.supabase.co"
anon_key    = "eyJ..."
service_role_key = "sb_service_role_..."
data_source = "auto"

[internal_auth]
enabled = true
beta_badge = "Beta interna"
beta_title = "Observatorio Tecnológico CCHEN"
beta_message = "Acceso privado para revisión funcional, validación de datos sensibles y migración progresiva del observatorio."

[[internal_auth.users]]
username = "tu.usuario"
password = "cambiar-por-una-clave-segura"
role = "admin"
can_view_sensitive = true
```

### Notas de despliegue

- El archivo canónico para Streamlit Cloud es `requirements.txt` en la raíz del repositorio.
- Se fija `python-3.11` en `runtime.txt` para evitar problemas de compatibilidad con el stack científico (`sentence-transformers`, `matplotlib`, `plotly`, `networkx`, `duckdb`).
- Si el deploy muestra un error del tipo `cannot import name 'load_convocatorias' from 'data_loader'`, la app está corriendo una revisión antigua del repo. En ese caso:
  1. confirma que Streamlit Cloud apunte a la rama `main`,
  2. fuerza un `Redeploy` o `Reboot app`,
  3. verifica que el deploy use el commit más reciente del repositorio.

### Smoke test de CI

- El workflow [dashboard_smoke.yml](/Users/bastianayalainostroza/Dropbox/CCHEN/.github/workflows/dashboard_smoke.yml) corre en `push`, `pull_request` y manualmente.
- Compila `Dashboard/app.py`, `Dashboard/data_loader.py` y `Dashboard/sections/*.py`.
- Ejecuta [check_dashboard_smoke.py](/Users/bastianayalainostroza/Dropbox/CCHEN/Scripts/check_dashboard_smoke.py), que valida:
  - contrato de imports `app/sections -> data_loader`,
  - carga local de convocatorias, matching, funding y núcleo institucional,
  - y columnas mínimas de los datasets críticos del observatorio.
- Ejecuta además [check_dashboard_e2e.py](/Users/bastianayalainostroza/Dropbox/CCHEN/Scripts/check_dashboard_e2e.py), un E2E mínimo con `streamlit.testing.v1.AppTest` que verifica:
  - la muralla beta de acceso,
  - el login interno con secrets inyectados de prueba,
  - y la navegación de secciones clave (`Panel de Indicadores`, `Convocatorias y Matching`, `Grafo de Citas`) para cubrir la carga lazy por sección.
- Este E2E debe correrse con **Python 3.11**, igual que el runtime del dashboard.
- **Estándar operativo recomendado:** ejecutar el E2E local con `uv` para no depender de la versión de Python del sistema ni del `.venv` activo.

```bash
uv run --python 3.11 --with-requirements requirements.txt python Scripts/check_dashboard_e2e.py
```

- Este comando crea/usa un entorno efímero aislado y no modifica tu Python global.

### Contrato de base de datos en CI

- El workflow [database_contract.yml](/Users/bastianayalainostroza/Dropbox/CCHEN/.github/workflows/database_contract.yml) corre en `push`, `pull_request` y manualmente cuando cambian `Database/**`.
- Compila los scripts de base de datos y ejecuta [check_database_contract.py](/Users/bastianayalainostroza/Dropbox/CCHEN/Scripts/check_database_contract.py).
- El chequeo falla si:
  - `migrate_to_supabase.py` usa tablas no creadas en `schema.sql`,
  - `schema.sql` define tablas nuevas sin ruta de migración declarada,
  - una tabla no tiene `RLS` habilitado,
  - o no tiene ninguna `policy` asociada.

### Secrets requeridos

| Variable | Descripción | Obligatoria | Obtener en |
|----------|-------------|-------------|-----------|
| `GROQ_API_KEY` | API key de Groq (LLM) | Sí | [console.groq.com](https://console.groq.com) |
| `supabase.url` | URL del proyecto Supabase | Para modo remoto | Dashboard Supabase |
| `supabase.anon_key` | Anon key pública de Supabase | Para lectura pública remota | Dashboard Supabase → API |
| `supabase.service_role_key` | Service role key para datasets sensibles en el dashboard beta | Solo si quieres capital humano y vistas sensibles en cloud | Dashboard Supabase → API |
| `internal_auth.*` | Usuarios, claves y roles de ingreso beta | Recomendada en el dashboard desplegado | Secrets del dashboard |
| `SUPABASE_KEY` | Service role key para scripts de migración Database/ | Solo scripts Database/ | Dashboard Supabase → API |

### Activación final de Supabase

1. En tu proyecto Supabase, abrir **SQL Editor** y ejecutar [schema.sql](/Users/bastianayalainostroza/Dropbox/CCHEN/Database/schema.sql).
2. Crear `Database/.env` con:

```bash
SUPABASE_URL=https://uhoeftavcvuzcqhukshi.supabase.co
SUPABASE_KEY=tu_service_role_key
SUPABASE_ANON_KEY=tu_anon_key_publica
```

3. Migrar datos:

```bash
python3 Database/migrate_to_supabase.py
```

4. Verificar contrato local:

```bash
python3 Scripts/check_database_contract.py
OBSERVATORIO_DATA_SOURCE=local python3 Scripts/check_dashboard_smoke.py
uv run --python 3.11 --with-requirements requirements.txt python Scripts/check_dashboard_e2e.py
```

5. Verificar conectividad real contra tu instancia:

```bash
python3 Scripts/check_supabase_runtime.py
```

6. En `Dashboard/.streamlit/secrets.toml` o en los secrets del dashboard desplegado, configurar:

```toml
GROQ_API_KEY = "gsk_..."

[supabase]
url = "https://uhoeftavcvuzcqhukshi.supabase.co"
anon_key = "tu_anon_key_publica"
service_role_key = "tu_service_role_key"
data_source = "auto"

[internal_auth]
enabled = true
beta_badge = "Beta interna"
beta_title = "Observatorio Tecnológico CCHEN"
beta_message = "Acceso privado para revisión funcional, validación de datos sensibles y migración progresiva del observatorio."

[[internal_auth.users]]
username = "tu.usuario"
password = "cambiar-por-una-clave-segura"
role = "admin"
can_view_sensitive = true
```

7. Levantar localmente, desplegar el dashboard en la VM 3 en 1 o usar Streamlit Cloud sólo como contingencia.

### Preparación de beta pública en VM

Para la ruta pública real del portal 3 en 1 usa:

- `.env.public.example`
- `Dashboard/.streamlit/secrets.public.toml.example`
- `Docs/operations/runbook_publicacion_portal_publico_3en1.md`
- `Docs/operations/estado_beta_publica_3en1.md`
- `Docs/operations/runbook_oracle_piloto_publico_3en1.md`
- `Scripts/deploy_observatorio_public.sh`
- `Scripts/sync_observatorio_letsencrypt_certs.sh`
- `Scripts/wait_and_check_observatorio_public_portal.sh`

La política objetivo de acceso es:

- `https://observatorio.cchen.cl` público
- `https://repo.cchen.cl` público
- `https://datos.cchen.cl` público
- `https://obs-int.cchen.cl` protegido con `Basic Auth` + `internal_auth`

Recomendación operativa para el primer piloto Oracle:

- si todavía hay `trial credits`, usar una VM `x86` pequeña o mediana para reducir riesgo de compatibilidad con imágenes externas;
- si el objetivo es `Always Free` estricto, usar `VM.Standard.A1.Flex` y validar explícitamente `dashboard`, `DSpace`, `CKAN` y `reverse-proxy`.

### Cómo verificar desde la app

- Abre `Inspector de datasets`.
- Cada dataset ahora muestra `Lectura efectiva`.
- Los valores esperados son:
  - `Supabase pública`: está saliendo desde tu instancia remota.
  - `Fallback local`: intentó Supabase pero cayó al CSV local.
  - `Solo local / autenticado`: el dataset es sensible o no se expone por la ruta pública; puede venir de la capa privada del dashboard o de un CSV local.

---

## File Structure

```
CCHEN/
├── README.md                         ← Este archivo
├── ARCHITECTURE.md                   ← Diseño técnico completo
├── requirements.txt                  ← Dependencias raíz del dashboard y contingencia Streamlit Cloud
├── runtime.txt                       ← Versión de Python usada en deploy
│
├── Dashboard/                        ← Aplicación web Streamlit
│   ├── app.py                        ← Punto de entrada; arma contexto lazy y enruta secciones
│   ├── data_loader.py                ← Carga y preprocesa todos los datasets
│   ├── requirements.txt              ← Dependencias del dashboard (pip install aquí)
│   └── sections/                     ← Módulos del dashboard (uno por sección)
│       ├── __init__.py
│       ├── shared.py                 ← Constantes, helpers, generate_pdf_report()
│       ├── panel_indicadores.py      ← KPIs ejecutivos y franja operativa
│       ├── produccion_cientifica.py  ← Bibliometría completa
│       ├── redes_colaboracion.py     ← Mapas y redes institucionales
│       ├── vigilancia_tecnologica.py ← Monitor de tendencias y arXiv
│       ├── financiamiento_id.py      ← ANID, CORFO, fuentes complementarias
│       ├── convocatorias_matching.py ← Convocatorias abiertas y scoring
│       ├── transferencia_portafolio.py ← Portafolio TRL, DataCite, OpenAIRE
│       ├── modelo_gobernanza.py      ← Entidades canónicas y gobernanza
│       ├── formacion_capacidades.py  ← Capital humano I+D
│       ├── asistente_id.py           ← Asistente RAG + Groq LLM
│       └── grafo_citas.py            ← Grafo interactivo plotly + networkx
│
├── Scripts/                          ← Scripts de recolección y análisis
│   ├── fetch_openalex_citations.py   ← Grafo de citas OpenAlex
│   ├── fetch_europmc.py              ← Literatura biomédica EuroPMC
│   ├── fetch_datacite_outputs.py     ← Datasets DOI vía DataCite
│   ├── fetch_openaire_outputs.py     ← Outputs OpenAIRE vía ORCID
│   ├── fetch_inapi_patents.py        ← Patentes INAPI Chile
│   ├── fetch_patentsview_patents.py  ← Patentes PatentsView/USPTO
│   ├── fetch_altmetric.py            ← Métricas alternativas Altmetric
│   ├── fetch_funding_plus.py         ← Financiamiento complementario
│   ├── fetch_semantic_scholar.py     ← Métricas Semantic Scholar
│   ├── build_embeddings.py           ← Pre-cómputo de embeddings semánticos
│   ├── semantic_search.py            ← Búsqueda semántica (RAG backend)
│   ├── build_ror_registry.py         ← Registro institucional ROR
│   ├── build_operational_core.py     ← Entidades canónicas y matching
│   ├── arxiv_monitor.py              ← Monitor arXiv (GitHub Actions)
│   ├── news_monitor.py               ← Monitor noticias (GitHub Actions)
│   ├── convocatorias_monitor.py      ← Monitor convocatorias ANID
│   ├── generar_boletin.py            ← Boletín HTML semanal
│   ├── iaea_inis_monitor.py          ← Vigilancia IAEA INIS
│   ├── run_bertopic.py               ← Modelado de tópicos BERTopic
│   └── enrich_unpaywall.py           ← Acceso abierto Unpaywall
│
├── Database/                         ← Esquema y migración a Supabase
│   ├── schema.sql                    ← DDL completo PostgreSQL (35 tablas)
│   ├── migrate_to_supabase.py        ← Migración idempotente de tablas principales
│   ├── migrate_citing_papers.py      ← citing_papers (8.499 filas)
│   ├── migrate_europmc.py            ← europmc_works (74 filas)
│   ├── migrate_vigilancia.py         ← citation_graph + arxiv + iaea + news
│   ├── migrate_bertopic.py           ← bertopic_topics + bertopic_topic_info
│   ├── migrate_convocatorias.py      ← convocatorias + matching_rules
│   ├── migrate_embeddings.py         ← paper_embeddings (877 × 384 dims, pgvector)
│   └── data_quality.py               ← Validación y reporte de calidad
│
├── Notebooks/                        ← Pipelines ETL Jupyter (ejecutar en orden)
│   ├── 01_Download_publications.ipynb
│   ├── 02_CrossRef_enrichment.ipynb
│   ├── 03_OpenAlex_concepts.ipynb
│   ├── 04_ORCID_researchers.ipynb
│   ├── 05_Download_patents.ipynb
│   ├── 06_ANID_repository.ipynb
│   ├── 07_MinCiencia_funding.ipynb
│   └── analysis/
│
├── Data/                             ← Datos locales (gitignoreados — demasiado grandes)
│   ├── Publications/                 ← CSVs OpenAlex, CrossRef, SJR, citas
│   ├── Capital humano CCHEN/         ← Dataset maestro de capital humano
│   ├── ANID/                         ← Repositorio ANID con montos
│   ├── Funding/                      ← Financiamiento complementario, IAEA TC
│   ├── Institutional/                ← Registro ROR, convenios, acuerdos
│   ├── Researchers/                  ← Perfiles ORCID
│   ├── Patents/                      ← Patentes Lens.org / INAPI
│   ├── ResearchOutputs/              ← DataCite + OpenAIRE outputs
│   ├── Gobernanza/                   ← Entidades canónicas y enlaces
│   ├── Vigilancia/                   ← arXiv, noticias, convocatorias
│   └── Publicaciones DIAN CCHEN/     ← Registro interno DIAN (Excel)
│
├── Docs/                             ← Documentación técnica y reportes
│   ├── design/                       ← Propuesta de implementación, memoria metodológica
│   ├── reports/                      ← Bitácora y reportes generados
│   └── methodology/                  ← Notas metodológicas
│
└── Tests/                            ← Tests unitarios del dashboard
```

---

## Data Sources Table

| Fuente | Tabla Supabase | Registros | Frecuencia actualización | Requiere token |
|--------|---------------|-----------|--------------------------|---------------|
| OpenAlex API | `publications`, `authorships`, `concepts` | 877 / 7.971 / 21.348 | Trimestral | No |
| CrossRef API | `crossref_data` | 764 | Trimestral | No (email recomendado) |
| Scimago SJR | `publications_enriched` | 616 con cuartil | Anual | No |
| ORCID API | `researchers_orcid` | 48 | Semestral | No |
| ANID Repositorio | `anid_projects` | 24 | Manual | No |
| datos.gob.cl | `convenios_nacionales`, `acuerdos_internacionales` | 84 / 91 | Semestral | No |
| EuroPMC REST API | `europmc_works` | 74 | Trimestral | No |
| DataCite API | `datacite_outputs` | Variable | Trimestral | No |
| OpenAIRE Graph API | `openaire_outputs` | Variable | Trimestral | No |
| ROR API | `institution_registry` | 697 | Anual | No |
| OpenAlex Citations | `citing_papers` | 8.499 | Trimestral | No |
| OpenAlex citation graph | `citation_graph` | 877 | Trimestral | No |
| arXiv RSS | `arxiv_monitor` | ~225 | Semanal (auto) | No |
| IAEA INIS | `iaea_inis_monitor` | ~109 | Semanal (auto, best-effort) | No |
| Google News | `news_monitor` | ~65 | Semanal (auto) | No |
| BERTopic (NLP local) | `bertopic_topics`, `bertopic_topic_info` | 358 / 23 | Manual | No |
| Convocatorias curadas | `convocatorias`, `convocatorias_matching_rules` | 26 / 6 | Semanal (best-effort por scraping) | No |
| pgvector embeddings | `paper_embeddings` | 877 × 384 dims | Manual | No |
| Altmetric API | (CSV local) | Variable | Trimestral | Sí (free tier) |
| PatentsView / USPTO | `patents` | Pendiente | Manual | Sí (registro gratuito) |
| INAPI Chile | `patents` | Pendiente | Manual | No |
| Groq API | — | — | Runtime | Sí (gratis) |
| sentence-transformers | — | — | Pre-cómputo manual | No |

---

## License & Author

**Autor:** Bastián Ayala Inostroza
**Institución:** Comisión Chilena de Energía Nuclear (CCHEN)
**Proyecto:** CORFO CCHEN 360 — Plan de Fortalecimiento de Aplicaciones Nucleares
**Gestor Tecnológico:** Rodrigo Núñez G.

Este repositorio contiene código fuente bajo licencia MIT. Los datos en `Data/` son propiedad de CCHEN y no se publican en este repositorio (están excluidos por `.gitignore`).

Para contacto técnico o académico: observatory@cchen.cl

---

*Observatorio Tecnológico Virtual CCHEN · Beta v0.2 · Marzo 2026*
