# Arquitectura Técnica — Observatorio Tecnológico CCHEN 360°

**Versión:** 1.0 · **Fecha:** Marzo 2026
**Autor:** Bastián Ayala Inostroza
**Documento base:** Memoria Metodológica - Observatorio CCHEN 360 (Sept. 2025)

---

## 1. Visión general

El observatorio es un sistema de inteligencia de datos con **arquitectura de tres capas**:

```
┌──────────────────────────────────────────────────────┐
│  CAPA 3 — PRESENTACIÓN                               │
│  Streamlit Dashboard · Asistente IA · PDF Reports    │
├──────────────────────────────────────────────────────┤
│  CAPA 2 — LÓGICA / ANÁLISIS                          │
│  data_loader.py · DuckDB · Supabase API              │
├──────────────────────────────────────────────────────┤
│  CAPA 1 — DATOS                                      │
│  CSVs locales → Supabase (PostgreSQL) → Data Lake    │
└──────────────────────────────────────────────────────┘
```

### Stack tecnológico actual (TRL 5)
- **Frontend:** Streamlit (Python) — modularizado en `Dashboard/sections/`
- **Backend/Lógica:** Python 3.9, pandas, plotly
- **Base de datos analítica:** DuckDB (en desarrollo)
- **Base de datos producción:** Supabase / PostgreSQL (en migración)
- **IA / LLM:** Groq API (llama-3.3-70b-versatile + llama-3.1-8b-instant) + fallback por keywords
- **Almacenamiento:** Dropbox → GitHub + Supabase Storage
- **Reportes:** reportlab (PDF), matplotlib
- **Citas científicas:** OpenAlex citation graph (script listo)
- **Patentes nacionales:** INAPI Chile (script listo)
- **Métricas alternativas:** Semantic Scholar (877 papers procesados)

### Stack objetivo (TRL 6–7, con presupuesto MM$42+)
- **Frontend:** Angular (JavaScript)
- **Backend:** Django REST Framework (Python)
- **Base de datos:** PostgreSQL en Huawei Cloud
- **Data Lake:** Object Storage S3-compatible
- **BI:** Power BI o Metabase open source
- **Orquestación:** Apache Airflow o GitHub Actions

---

## 2. Arquitectura de datos

### Modelo híbrido Data Lake + Data Warehouse

```
FUENTES EXTERNAS                   FUENTES INTERNAS
──────────────                     ────────────────
OpenAlex API                       Registro DIAN (Excel)
CrossRef API                       Capital Humano (Excel)
ORCID API                          ANID Repositorio
Lens.org API                       datos.gob.cl CSVs
arXiv RSS
SJR/Scimago CSV

        ↓ Notebooks/ (ETL)

┌─────────────────────────────────────────┐
│  DATA LAKE (raw)                        │
│  /Data/**/*.csv — archivos originales   │
│  GitHub → versionados y trazables       │
└─────────────────────────────────────────┘
        ↓ data_loader.py (transformación)

┌─────────────────────────────────────────┐
│  DATA WAREHOUSE (curado)                │
│  Supabase (PostgreSQL)                  │
│  Tablas normalizadas y relacionadas     │
│  API REST autogenerada                  │
└─────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────┐
│  CAPA ANALÍTICA                         │
│  DuckDB (queries sobre Supabase/CSVs)   │
│  data_loader.py (carga en Streamlit)    │
└─────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────┐
│  PUBLICACIÓN                            │
│  Zenodo (DOI por dataset)               │
│  Dashboard público (futuro)             │
└─────────────────────────────────────────┘
```

---

## 3. Esquema de tablas (Supabase / PostgreSQL)

Ver `Database/schema.sql` para el DDL completo.

### Tablas principales

| Tabla | Filas actuales | Fuente | Clave primaria |
|-------|----------------|--------|----------------|
| `publications` | 877 | OpenAlex API | `openalex_id` |
| `authorships` | 7.971 | OpenAlex API | `(work_id, author_id)` |
| `publications_enriched` | 616 | OpenAlex + SJR | `work_id` |
| `crossref_data` | 764 | CrossRef API | `doi` |
| `concepts` | 21.348 | OpenAlex API | `(work_id, concept_name)` |
| `patents` | 0+ | PatentsView / USPTO | `patent_uid` |
| `anid_projects` | 30 | ANID Repositorio | `proyecto` |
| `capital_humano` | 112 | Registro interno | `id` (serial) |
| `researchers_orcid` | 48 | ORCID API | `orcid_id` |
| `funding_complementario` | 2+ | Dataset curado | `funding_id` |
| `institution_registry` | 697 | ROR + OpenAlex + ORCID + convenios | `normalized_key` |
| `institution_registry_pending_review` | 48 | Curaduría ROR | `canonical_name` |
| `entity_registry_personas` | 604 | Núcleo institucional fase 1 | `persona_id` |
| `entity_registry_proyectos` | 24 | Núcleo institucional fase 1 | `project_id` |
| `entity_registry_convocatorias` | 26 | Núcleo institucional fase 1 | `convocatoria_id` |
| `entity_links` | 657 | Núcleo institucional fase 1 | `(origin_type, origin_id, relation, target_type, target_id)` |
| `convocatorias_matching_institucional` | 26 | Mesa institucional fase 1 | `(conv_id, perfil_id)` |
| `convenios_nacionales` | 84 | datos.gob.cl | `id` (serial) |
| `acuerdos_internacionales` | 91 | datos.gob.cl | `id` (serial) |
| `data_sources` | — | Gobernanza | `source_name` |

### Relaciones clave

```
publications (openalex_id)
    ├── authorships (work_id → openalex_id)
    ├── publications_enriched (work_id → openalex_id)
    ├── crossref_data (doi → doi)
    └── concepts (work_id → openalex_id)

anid_projects
    └── (relacionable con publications por autor)

capital_humano
    └── (relacionable con researchers_orcid por nombre)
```

---

## 4. Pipeline de actualización de datos

```
Paso 1 — Recolección (Notebooks/ en orden numérico)
  01_Download_publications      → Data/Publications/cchen_openalex_works.csv
  02_CrossRef_enrichment        → Data/Publications/cchen_crossref_enriched.csv
  03_OpenAlex_concepts          → Data/Publications/cchen_openalex_concepts.csv
  04_ORCID_researchers          → Data/Researchers/cchen_researchers_orcid.csv
  05_Download_patents / Scripts/fetch_patentsview_patents.py
                                 → Data/Patents/cchen_patents.csv o Data/Patents/cchen_patents_uspto.csv
  06_ANID_repository            → Data/ANID/RepositorioAnid_con_monto.csv
  07_MinCiencia_funding / Scripts/fetch_funding_plus.py
                                 → Data/Funding/cchen_funding_complementario.csv
  Scripts/build_ror_registry.py  → Data/Institutional/cchen_institution_registry.csv
                                 → Data/Institutional/ror_pending_review.csv
  Scripts/build_operational_core.py
                                 → Data/Gobernanza/entity_registry_*.csv
                                 → Data/Gobernanza/entity_links.csv
                                 → Data/Vigilancia/convocatorias_matching_institucional.csv
  Scripts/fetch_openalex_citations.py
                                 → Data/Publications/cchen_citation_graph.csv
                                 → Data/Publications/cchen_citing_papers.csv
  Scripts/fetch_inapi_patents.py → Data/Patents/cchen_inapi_patents.csv
  Scripts/fetch_semantic_scholar.py
                                 → Data/Publications/cchen_semantic_scholar.csv

Paso 2 — Validación de calidad
  python Database/data_quality.py
  → Genera reporte de calidad + alertas

Paso 3 — Migración a Supabase
  python Database/migrate_to_supabase.py
  → Upsert en todas las tablas

Paso 4 — Verificación
  Dashboard → Panel de Indicadores → Fuentes y actualización
```

### Frecuencia recomendada

| Fuente | Frecuencia | Automatización | Razón |
|--------|-----------|---------------|-------|
| arXiv RSS (vigilancia) | Semanal | GitHub Actions (lunes 08:00 UTC) | Papers nuevos cada semana |
| Google News CCHEN | Semanal | GitHub Actions (lunes 08:00 UTC) | Noticias de alta rotación |
| Convocatorias ANID | Semanal | GitHub Actions (lunes 08:00 UTC) | Estados cambian durante el año |
| OpenAlex publicaciones | Trimestral | Manual (Notebook 01) | Nuevos papers se indexan con ~3 meses de delay |
| CrossRef | Trimestral | Manual (Notebook 02) | Junto con OpenAlex |
| ORCID | Semestral | Manual (Notebook 04) | Perfiles cambian poco |
| SJR/Scimago | Anual | Manual (Notebook 09) | Publican en enero del año siguiente |
| datos.gob.cl | Semestral | Manual | Convenios/acuerdos cambian poco |

### Workflow automatizado

`.github/workflows/arxiv_monitor.yml` ejecuta cada lunes los tres monitores de vigilancia:

```
arXiv RSS       → Data/Vigilancia/arxiv_monitor.csv  + arxiv_state.json
Google News     → Data/Vigilancia/news_monitor.csv   + news_state.json
Convocatorias   → Data/Vigilancia/convocatorias_curadas.csv
```

El script de convocatorias corre con `continue-on-error: true` porque depende de scraping HTML del sitio de ANID.

---

## 5. Módulos del observatorio

Según la Memoria Metodológica (Documento de Trabajo N°2, Sept. 2025), el observatorio tiene 7 módulos:

### Mapa de recopilación por módulo

La siguiente tabla resume en qué módulo conviene recopilar datos, tecnologías y herramientas según su función dentro del observatorio:

| Módulo | Qué datos / activos recopila o gestiona | Tecnologías / herramientas asociadas | Estado actual |
|--------|------------------------------------------|--------------------------------------|---------------|
| Vigilancia y Prospección Tecnológica | Publicaciones, patentes, tendencias, actores, señales emergentes, normativa, taxonomías temáticas y fuentes externas de vigilancia | OpenAlex, CrossRef, Lens.org, arXiv RSS, IAEA INIS, Semantic Scholar, spaCy, BERTopic, GitHub Actions | Parcial |
| Inteligencia Aplicada | Indicadores, rankings, benchmarking, análisis bibliométrico, mapas de actores, dashboards, reportes y productos analíticos | Python, pandas, Plotly, Streamlit, DuckDB, Groq/LLM, reportlab, Power BI o Metabase (objetivo) | Activo (TRL 4) |
| Difusión y Divulgación | Boletines, newsletters, micrositios, data stories, contenidos audiovisuales, métricas de alcance e impacto comunicacional | Mailchimp, Brevo, GitHub Pages, Altmetric API, plantillas LLM | Pendiente |
| Repositorio de Datos | Datasets raw y curados, CSVs, tablas, metadatos, scripts, fichas metodológicas, evidencias, snapshots y documentación técnica | Supabase/PostgreSQL, DuckDB, GitHub, Zenodo, Supabase Storage, Data Lake local en `Data/` | En desarrollo |
| Transferencia y Codiseño | Inventario de tecnologías CCHEN, activos con TRL 6-9, acuerdos de colaboración, propiedad intelectual, bitácoras y carpetas compartidas por proyecto | Plataformas colaborativas con trazabilidad, control de versiones, gestión documental legal, DMDA/MTA digitales | Pendiente |
| Colaboración Ecosistémica | Convenios, acuerdos institucionales, perfiles ORCID, conectores con ANID/CORFO/universidades, indicadores exportables y datos interoperables | API REST, FastAPI o Django REST, CERIF, CASRAI, EuroCRIS, conectores institucionales | Inicial |
| Gobernanza de Datos | Catálogo de fuentes, frecuencia de actualización, reglas de calidad, responsables, permisos, trazabilidad, auditoría, metadatos y políticas de resguardo | `Database/data_quality.py`, validaciones automáticas, logging, backups, Dublin Core, DCAT, ORCID | Inicial |

### Lectura práctica

- Si el objetivo es **capturar información externa** sobre publicaciones, patentes, tendencias o actores, el módulo principal es **Vigilancia y Prospección Tecnológica**.
- Si el objetivo es **almacenar y organizar datasets, tablas, metadatos y scripts**, corresponde al **Repositorio de Datos**.
- Si el objetivo es **convertir datos en indicadores, visualizaciones o reportes**, corresponde a **Inteligencia Aplicada**.
- Si el objetivo es **intercambiar datos con otras instituciones o exponer APIs**, corresponde a **Colaboración Ecosistémica**.
- Si el objetivo es **asegurar calidad, trazabilidad y estándares**, corresponde a **Gobernanza de Datos**.
- Si el objetivo es **ordenar tecnologías transferibles, PI y codiseño con terceros**, corresponde a **Transferencia y Codiseño**.
- Si el objetivo es **publicar hallazgos para públicos internos o externos**, corresponde a **Difusión y Divulgación**.

### Matriz operativa por módulo

La siguiente matriz traduce cada módulo a una lógica operativa de entradas, procesos, salidas y herramientas:

| Módulo | Entradas principales | Procesos clave | Salidas esperadas | Herramientas / stack |
|--------|----------------------|----------------|-------------------|----------------------|
| Vigilancia y Prospección Tecnológica | APIs científicas, portales de patentes, repositorios abiertos, RSS, taxonomías temáticas | Extracción vía API, limpieza, desduplicación, clasificación temática con BERTopic, monitoreo periódico | Alertas, bases de vigilancia, mapeos de tendencias, señales emergentes, datasets fuente | OpenAlex, CrossRef, Lens.org, arXiv RSS, IAEA INIS, Semantic Scholar, BERTopic, GitHub Actions |
| Inteligencia Aplicada | Datos curados desde vigilancia, repositorio y fuentes internas CCHEN | Integración analítica, modelamiento descriptivo, cálculo de KPIs, benchmarking, visualización y redacción de reportes | Dashboards, reportes PDF, rankings, mapas de actores, análisis bibliométricos, indicadores estratégicos | Python, pandas, DuckDB, Plotly, Streamlit, Groq/LLM, reportlab, Power BI o Metabase |
| Difusión y Divulgación | Insights, figuras, reportes, dashboards, documentos del observatorio | Curaduría editorial, adaptación de lenguaje, generación LLM, publicación multicanal, distribución | Boletines HTML/PDF semanales, newsletter, GitHub Pages, métricas de difusión | Mailchimp, Brevo, GitHub Pages, Altmetric API, plantillas LLM |
| Repositorio de Datos | CSVs raw, tablas curadas, scripts, reportes, metadatos, snapshots, documentación técnica | Versionado, almacenamiento, catalogación, normalización, preservación, consulta y publicación controlada | Data lake local, warehouse curado, tablas analíticas, datasets reproducibles, evidencia documental | Supabase/PostgreSQL, DuckDB, GitHub, Zenodo, Supabase Storage, carpeta `Data/` |
| Transferencia y Codiseño | Inventario de tecnologías, resultados transferibles, acuerdos, necesidades de socios, documentos de PI | Clasificación por TRL, gestión documental, trazabilidad de colaboración, resguardo legal, codiseño con actores externos | Catálogo de tecnologías, carpetas de proyecto, acuerdos digitales, bitácoras de transferencia | Plataformas colaborativas, control de versiones, gestores documentales, DMDA/MTA digitales |
| Colaboración Ecosistémica | Convenios, acuerdos, perfiles ORCID, fuentes externas interoperables, indicadores exportables | Integración interinstitucional, exposición de datos, conexión mediante estándares, intercambio de indicadores | API pública/privada, exportaciones, paneles interoperables, conectores con ecosistemas I+D+i | FastAPI o Django REST, CERIF, CASRAI, EuroCRIS, conectores institucionales |
| Gobernanza de Datos | Catálogo de fuentes, reglas de negocio, políticas de acceso, logs, metadatos, responsables de datos | Validación de calidad, auditoría, control de permisos, trazabilidad, respaldo, estandarización y monitoreo | Reportes de calidad, catálogos de datos, trazabilidad de actualizaciones, políticas de resguardo | `Database/data_quality.py`, logging, backups, Dublin Core, DCAT, ORCID |

### Convocatorias Abiertas

Las convocatorias abiertas deben tratarse como un subproducto específico del módulo de **Vigilancia y Prospección Tecnológica**, pero su visualización útil para usuarios finales corresponde a **Inteligencia Aplicada**.

- **Captura:** calendario oficial de ANID, fichas concursales oficiales y portales institucionales serios de cooperación o grants internacionales.
- **Curaduría:** clasificación por `estado`, `perfil objetivo`, `relevancia para CCHEN` y separación explícita entre `convocatoria abierta/próxima` versus `portal estratégico`.
- **Salida recomendada:** una sección dentro de `Financiamiento I+D` que priorice académicos, postdocs, doctorados, consorcios científicos e innovación/transferencia.
- **No recomendado:** mezclar noticias RSS o notas de prensa con convocatorias postulables.

### Prioridades implementadas sobre el dashboard

Tomando la lectura modular del observatorio, las prioridades más útiles para la fase actual quedaron implementadas de esta forma:

| Prioridad | Producto implementado | Fuente o archivo base | Propósito |
|-----------|-----------------------|------------------------|-----------|
| Convocatorias + matching con perfiles CCHEN | Sección `Convocatorias y Matching` | `Data/Vigilancia/convocatorias_curadas.csv`, `Data/Vigilancia/convocatorias_matching_rules.csv`, `Data/Vigilancia/convocatorias_matching_institucional.csv` | Convierte el radar de oportunidades en una mesa institucional con scoring formal, elegibilidad explícita, unidad responsable y acción recomendada. |
| Portafolio tecnológico / transferencia | Sección `Transferencia y Portafolio` | `Data/Transferencia/portafolio_tecnologico_semilla.csv` | Ordena capacidades observables y deja una base inicial para validación de `TRL`, unidad responsable y potencial de transferencia. |
| Modelo unificado de entidades + gobernanza | Sección `Modelo y Gobernanza` | `Data/Gobernanza/entity_registry_personas.csv`, `entity_registry_proyectos.csv`, `entity_registry_convocatorias.csv` y `entity_links.csv` | Estabiliza entidades críticas, relaciones y prioridades de gobierno para futuras integraciones, RLS y recuperación contextual del asistente. |

### Asistente del observatorio

El `Asistente I+D` debe entenderse como una capa de **Inteligencia Aplicada** alimentada por el repositorio y por productos derivados de vigilancia y gobernanza. En su estado actual, además de publicaciones, ANID y capital humano, ya debe consumir:

- convocatorias curadas abiertas y próximas,
- matching institucional formal con `score_total`, `eligibility_status`, `readiness_status` y `owner_unit`,
- portafolio tecnológico semilla,
- convenios nacionales y acuerdos internacionales,
- perfiles ORCID,
- financiamiento complementario e `IAEA TC`,
- el registro institucional `ROR`,
- y los registros canónicos de personas, proyectos, convocatorias y enlaces.

Restricción metodológica:

- cuando una capa esté incompleta, el asistente debe declararlo explícitamente;
- el portafolio tecnológico actual debe presentarse como **semilla analítica por validar**;
- y la ausencia de patentes integradas no debe interpretarse como inexistencia institucional, sino como una brecha del repositorio actual.

### Integración institucional con ROR

Se incorporó una primera capa de normalización institucional basada en `ROR` para fortalecer el módulo de **Colaboración Ecosistémica** y la gobernanza de entidades.

- `CCHEN` queda fijada como institución ancla con `ROR ID https://ror.org/03hv95d67`.
- El registro derivado se genera desde:
  - `OpenAlex authorships` para instituciones colaboradoras con `institution_ror`,
  - `ORCID` para empleadores observados,
  - `convenios nacionales` para contrapartes institucionales,
  - una semilla manual en `Data/Institutional/ror_seed_institutions.csv`,
  - y aliases curados en `Data/Institutional/ror_manual_aliases.csv`.
- Producto generado: `Data/Institutional/cchen_institution_registry.csv`.
- Cola de curaduría generada: `Data/Institutional/ror_pending_review.csv`.
- Script de regeneración: `Scripts/build_ror_registry.py`.
- Estado operativo fase 1: `0` filas con prioridad `Alta`; la cola restante se reclasifica solo como `manual_selectivo` o `api_candidate_future`.

Utilidad práctica:

- mejora la trazabilidad de colaboraciones institucionales,
- reduce ambigüedad en nombres de instituciones dentro del asistente,
- deja una cola priorizada para revisión manual antes de automatizar búsquedas externas,
- y prepara al observatorio para una futura conexión directa con la API de `ROR` y luego con `DataCite`.

### Outputs de investigación vía DataCite

Se incorporó una primera capa de outputs no-paper asociados a `CCHEN`, útil para fortalecer **Transferencia y Codiseño**, **Repositorio de Datos** e **Inteligencia Aplicada**.

- Fuente: `DataCite API`, filtrada por `ROR https://ror.org/03hv95d67`.
- Productos generados:
  - `Data/ResearchOutputs/cchen_datacite_outputs.csv`
  - `Data/ResearchOutputs/datacite_state.json`
- Script de regeneración: `Scripts/fetch_datacite_outputs.py`.

Utilidad práctica:

- incorpora `datasets` y otros outputs DOI que no siempre aparecen bien representados como papers;
- permite conectar producción científica con activos de datos y repositorios;
- y alimenta tanto el dashboard como el asistente con evidencia adicional para transferencia y portafolio.

### Outputs complementarios vía OpenAIRE Graph

Se añadió una capa inicial basada en `OpenAIRE Graph` para complementar publicaciones y datasets con una visión centrada en investigadores `CCHEN` que ya tienen `ORCID` cargado.

- Fuente: `OpenAIRE Graph API`, consultada por `authorOrcid`.
- Productos generados:
  - `Data/ResearchOutputs/cchen_openaire_outputs.csv`
  - `Data/ResearchOutputs/openaire_state.json`
- Script de regeneración: `Scripts/fetch_openaire_outputs.py`.

Utilidad práctica:

- ayuda a identificar outputs que no siempre quedan bien consolidados solo con `OpenAlex`;
- diferencia si el vínculo con `CCHEN` aparece por organización o solo por autor;
- y mejora el módulo de **Transferencia y Codiseño** al relacionar outputs, autores, repositorios y potenciales proyectos asociados.

### a. Vigilancia y Prospección Tecnológica
**Función:** Monitoreo automatizado de tendencias globales en áreas estratégicas de CCHEN
**Estado:** Parcial — recolección implementada; clasificación temática con BERTopic e IAEA INIS pendientes
**Tecnologías implementadas:**
- APIs directas: OpenAlex, CrossRef, arXiv RSS, Semantic Scholar, IAEA INIS (pendiente)
- NLP/Tópicos: BERTopic (cruzar papers arXiv con tópicos institucionales)
- Automatización: GitHub Actions (lunes 08:00 UTC)
**Próximo paso:** integrar IAEA INIS como fuente de vigilancia nuclear especializada

### b. Inteligencia Aplicada
**Función:** Transformar datos en indicadores, reportes y dashboards interactivos
**Estado:** Activo (TRL 4) — Dashboard Streamlit + Asistente IA
**Tecnologías:** Python, Streamlit, Plotly, Groq/LLM, reportlab
**Próximos pasos:** Migrar a Angular+Django, integrar Power BI/Metabase

### c. Difusión y Divulgación
**Función:** Comunicar hallazgos del observatorio a públicos diversos
**Estado:** Parcial — boletín HTML generado por `Scripts/generar_boletin.py`, distribución pendiente
**Tecnologías implementadas / planificadas:**
- Boletín semanal: `Scripts/generar_boletin.py` → HTML en `Data/Boletines/` (GitHub Actions)
- Newsletter: Mailchimp API (gratis hasta 500 contactos) o Brevo
- Publicación estática: GitHub Pages (sin servidor adicional requerido)
- Altmetric API (por DOI) para medir impacto de divulgación
**Próximo paso:** configurar envío automático vía Mailchimp al finalizar el GitHub Action semanal

### d. Repositorio de Datos
**Función:** Almacenar, clasificar, preservar y disponibilizar datos y evidencia
**Estado:** En desarrollo (este documento)
**Stack implementado:** Supabase (PostgreSQL) + DuckDB + GitHub + Zenodo
**Ver:** `Database/schema.sql` y `Database/migrate_to_supabase.py`

### e. Transferencia y Codiseño
**Función:** Espacios colaborativos para transferencia tecnológica e IP
**Estado:** Pendiente — requiere inventario de tecnologías CCHEN (TRL 6-9) previo
**Tecnologías requeridas:** Plataforma colaborativa con trazabilidad, gestión de PI, DMDA/MTA digitales
**Prerequisito institucional:** Catálogo de tecnologías clasificadas por TRL

### f. Colaboración Ecosistémica
**Función:** Conectar CCHEN con el ecosistema científico-tecnológico nacional e internacional
**Estado:** Inicial — convenios y acuerdos institucionales cargados
**Tecnologías requeridas:** API REST pública (FastAPI o Django REST), estándares CERIF/CASRAI
**Datos disponibles:** 84 convenios nacionales, 41 acuerdos internacionales, 48 perfiles ORCID

### g. Gobernanza de Datos (vertical transversal)
**Función:** Asegurar calidad, trazabilidad y seguridad de todos los datos
**Estado:** Inicial
**Ver:** `Database/data_quality.py`
**Estándares a adoptar:** Dublin Core (metadatos), DCAT (catálogo), ORCID (identidad)

---

## 6. Roadmap TRL

```
TRL 3 ──→ TRL 4 ──→ TRL 5 ──→ TRL 6 ──→ TRL 7
  ↑           ↑          ↑
(datos)    (dash)     AHORA
                     (modular
                      + citas
                      + patentes)

TRL 3: Prototipos funcionales validados en entorno controlado
TRL 4: Tecnología operando en entorno relevante (✓ alcanzado)
TRL 5: Integración parcial + productos para decisiones estratégicas (actual)
TRL 6: Integración completa + operación regular
TRL 7: Sistema en entorno real con conectividad estable
```

### Hitos alcanzados en TRL 5 (marzo 2026)

- Dashboard modularizado en `Dashboard/sections/` (10 módulos independientes)
- Script `fetch_openalex_citations.py` — grafo de citas para 877 papers
- Script `fetch_inapi_patents.py` — búsqueda en INAPI Chile
- Semantic Scholar: 877/877 papers procesados con métricas de impacto
- 6 correcciones de calidad de código (vectorización, JSON robusto, logging, fallback LLM)

---

## 7. Decisiones técnicas y justificación

| Decisión | Alternativa descartada | Razón |
|----------|----------------------|-------|
| Supabase como BD | MongoDB, Firebase | PostgreSQL compatible con stack Django futuro; gratis tier generoso |
| DuckDB para análisis | Spark, BigQuery | Sin servidor, integra con Python/pandas nativo, excelente para el tamaño actual |
| Groq como LLM API | OpenAI, Anthropic | Gratis en tier actual; llama-3.3-70b supera rendimiento necesario |
| Streamlit (no Angular) | React, Vue | Prototipado rápido; el equipo es 1 persona; migrar a Angular cuando haya financiamiento |
| GitHub para versionado | GitLab, Bitbucket | Integración con GitHub Actions para ETL automatizado futuro |
| Zenodo para publicación | Figshare, OSF | Integrado con CERN, reconocido académicamente, DOI gratuito |

---

## 8. Configuración de entornos

### Variables de entorno requeridas

```toml
# Dashboard/.streamlit/secrets.toml
GROQ_API_KEY = "gsk_..."          # Groq (LLM) — gratis en console.groq.com

[supabase]
url        = "https://xxxx.supabase.co"
anon_key   = "eyJ..."
data_source = "auto"              # auto | local | supabase_public
data_root  = "/ruta/absoluta/a/Data"  # solo si Data/ no está junto a Dashboard/
```

`CCHEN_DATA_ROOT` también puede configurarse como variable de entorno del sistema:

```bash
export CCHEN_DATA_ROOT="/ruta/absoluta/a/Data"
```

Si no se define, el dashboard infiere automáticamente `../Data` relativo a `Dashboard/data_loader.py`.

```bash
# Database/.env (para scripts de migración)
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_KEY=eyJ...               # anon key (pública) o service_role key (privada)
```

### Configuración del dashboard: fuente de datos

El dashboard Streamlit puede operar en tres modos:

- `local`: usa únicamente CSVs/Excel locales en `Data/`.
- `auto`: intenta leer tablas públicas desde Supabase y, si falla, vuelve a archivos locales.
- `supabase_public`: fuerza lectura remota para las tablas públicas ya migradas.

Configuración sugerida en `Dashboard/.streamlit/secrets.toml`:

```toml
[supabase]
url = "https://xxxx.supabase.co"
anon_key = "eyJ..."
data_source = "auto"   # auto | local | supabase_public
```

En la implementación actual, las tablas públicas soportadas por lectura remota son:

- `publications`
- `publications_enriched`
- `authorships`
- `crossref_data`
- `concepts`
- `anid_projects`
- `researchers_orcid`
- `convenios_nacionales`
- `acuerdos_internacionales`

Las tablas sensibles o derivadas siguen locales en esta fase:

- `capital_humano`
- `funding_complementario`
- `dian_publications`
- `publications_with_concepts`
- `grants_openalex`
- `patents`

### Tokens de APIs externas (opcional, para actualizar datos)

```python
# Notebooks/01_Download_publications.ipynb
# No requiere token — OpenAlex es abierta

# Notebooks/05_Download_patents.ipynb
LENS_TOKEN = "..."                # lens.org — gratis académico
PATENTSVIEW_API_KEY = "..."       # PatentsView/USPTO — gratis con registro
```

---

## 9. Contactos y referencias

- **Gestor Tecnológico:** Rodrigo Núñez G. (autor de la propuesta de implementación)
- **Analista de Datos:** Bastián Ayala Inostroza (implementación del prototipo)
- **Proyecto CORFO:** CCHEN 360 — Plan de Fortalecimiento de Aplicaciones Nucleares
- **Propuesta técnica:** `Docs/design/Propuesta_implementacion.pdf`
- **Diseño metodológico:** `Docs/design/Memoria_metodologica.pdf`
- **Bitácora de trabajo:** `Docs/reports/Bitacora_BA.pdf`
