# Arquitectura Técnica — Observatorio Tecnológico CCHEN 360°

**Versión:** 2.0 · **Fecha:** Marzo 2026
**Autor:** Bastián Ayala Inostroza
**Documentos base:** Memoria Metodológica - Observatorio CCHEN 360 (Sept. 2025); Propuesta de Implementación CORFO

---

## 1. Visión general del sistema

El Observatorio Tecnológico CCHEN es un sistema de inteligencia de datos con **arquitectura de tres capas** que transforma datos científicos dispersos en indicadores estratégicos accionables.

```
┌─────────────────────────────────────────────────────────────────┐
│  CAPA 3 — PRESENTACIÓN                                          │
│  Streamlit Dashboard (11 secciones modulares)                   │
│  Asistente I+D (RAG + Groq LLM)                                 │
│  Reportes PDF (reportlab + matplotlib)                          │
│  Grafo de citas interactivo (pyvis)                             │
├─────────────────────────────────────────────────────────────────┤
│  CAPA 2 — LÓGICA Y ANÁLISIS                                     │
│  data_loader.py — carga unificada Supabase ↔ CSV local          │
│  DuckDB — queries analíticas sobre CSV                          │
│  semantic_search.py — búsqueda vectorial (RAG backend)          │
│  Scripts/ — pipelines ETL y monitores de vigilancia             │
├─────────────────────────────────────────────────────────────────┤
│  CAPA 1 — DATOS                                                 │
│  CSVs locales en Data/ (Data Lake raw)                          │
│  Supabase / PostgreSQL 15 (Data Warehouse curado)               │
│  GitHub — versionado y trazabilidad                             │
└─────────────────────────────────────────────────────────────────┘
```

### Stack tecnológico actual (TRL 5)

| Componente | Tecnología | Versión | Notas |
|-----------|-----------|---------|-------|
| Dashboard | Streamlit | 1.50.0 | 11 secciones modulares en sections/ |
| Dataframes | pandas | 2.3.3 | Carga principal de datos |
| Visualización | plotly | 6.6.0 | Gráficos interactivos |
| Álgebra lineal | numpy | 2.0.2 | Embeddings semánticos |
| Base de datos | Supabase (PostgreSQL) | supabase-py 2.28.3 | 33 tablas operativas, RLS habilitado |
| Query local | DuckDB | — | Fallback y consultas analíticas |
| LLM principal | Groq (llama-3.3-70b-versatile) | groq>=0.11.0 | Asistente I+D |
| LLM auxiliar | Groq (llama-3.1-8b-instant) | groq>=0.11.0 | Decisión de gráficos PDF |
| Embeddings | sentence-transformers | 5.1.2 | paraphrase-multilingual-MiniLM-L12-v2 |
| Grafo visual | pyvis | 0.3.2 | Red de citas interactiva HTML |
| Reportes | reportlab + matplotlib | — | PDF con gráficos contextuales |
| Patrones sklearn | scikit-learn | 1.6.1 | Auxiliar en análisis |

### Stack objetivo (TRL 6–7, con presupuesto MM$42+)

- **Frontend:** Angular + TypeScript
- **Backend:** Django REST Framework (Python)
- **Base de datos:** PostgreSQL en Huawei Cloud
- **Data Lake:** Object Storage S3-compatible
- **BI:** Power BI o Metabase open source
- **Orquestación:** Apache Airflow o GitHub Actions avanzado
- **Autenticación:** OAuth2 institucional CCHEN

---

## 2. Diagrama de flujo de datos

```
FUENTES EXTERNAS                         FUENTES INTERNAS
────────────────                         ────────────────
OpenAlex API (REST)                      Registro DIAN Excel
  → publicaciones, autorías, citas,      Capital Humano Excel (maestro limpio)
    conceptos, grants, citas             ANID Repositorio CSV
CrossRef API (REST)                      datos.gob.cl (convenios, acuerdos)
  → financiadores, abstracts, refs
ORCID API (REST)
  → perfiles investigadores
EuroPMC REST API
  → literatura biomédica, PMID/PMCID
DataCite API (REST)
  → datasets y outputs DOI vía ROR
OpenAIRE Graph API (REST)
  → outputs adicionales vía ORCID
ANID Repositorio (web scraping)
  → proyectos con montos
arXiv RSS
  → papers nuevos relevantes
IAEA INIS
  → documentos nucleares (vigilancia)
Semantic Scholar API
  → métricas adicionales de impacto
Altmetric API
  → impacto en redes y medios
PatentsView / INAPI Chile
  → patentes y PI
Scimago SJR (CSV anual)
  → cuartiles de revistas 1999–2024

        │
        ▼ Notebooks/ + Scripts/ (ETL, extracción, limpieza)
        │
┌───────────────────────────────────────────────────────┐
│  DATA LAKE local  Data/**/*.csv                       │
│  ─ cchen_openalex_works.csv           (877 papers)    │
│  ─ cchen_authorships_enriched.csv     (7.971 filas)   │
│  ─ cchen_openalex_concepts.csv        (21.348 filas)  │
│  ─ cchen_crossref_enriched.csv        (764 filas)     │
│  ─ cchen_publications_with_quartile_sjr.csv           │
│  ─ cchen_citing_papers.csv            (8.499 filas)   │
│  ─ cchen_europmc_works.csv            (74 filas)      │
│  ─ cchen_datacite_outputs.csv                         │
│  ─ cchen_openaire_outputs.csv                         │
│  ─ cchen_institution_registry.csv     (697 filas)     │
│  ─ RepositorioAnid_con_monto.csv      (24 proyectos)  │
│  ─ dataset_maestro_limpio.csv         (capital humano)│
│  ─ entity_registry_*.csv + links.csv                 │
│  ─ cchen_embeddings.npy + _meta.csv   (RAG)          │
└───────────────────────────────┬───────────────────────┘
                                │ Database/migrate_to_supabase.py
                                │ (upsert idempotente, chunks de 500 filas)
                                ▼
┌───────────────────────────────────────────────────────┐
│  SUPABASE (PostgreSQL 15)                             │
│  33 tablas operativas, relaciones FK y vistas         │
│  API REST autogenerada con autenticación JWT          │
│  RLS habilitado: políticas públicas y autenticadas    │
│  Lectura: anon key para público; service_role para    │
│  beta privada y migración                             │
│  Paginación: 1.000 filas por página (SUPABASE_PAGE_SIZE) │
└───────────────────────────────┬───────────────────────┘
                                │ data_loader.py
                                │ (_load_public_table → _fetch_supabase_table)
                                ▼
┌───────────────────────────────────────────────────────┐
│  DASHBOARD STREAMLIT                                  │
│  app.py → resuelve loaders cacheados y arma ctx lazy │
│  sections/*.py → render() recibe ctx dict            │
│  shared.py → helpers, estilos, generate_pdf_report() │
└───────────────────────────────────────────────────────┘
```

---

## 3. Módulo data_loader.py

`Dashboard/data_loader.py` es el núcleo de carga de datos del sistema. Implementa un patrón de **fallback automático** Supabase → CSV local.

### PUBLIC_TABLE_CONFIG

Diccionario que declara todas las tablas con soporte de lectura remota desde Supabase:

```python
PUBLIC_TABLE_CONFIG = {
    "publications":              {"order_by": "openalex_id"},
    "publications_enriched":     {"order_by": "work_id"},
    "authorships":               {"order_by": "id"},
    "crossref_data":             {"order_by": "doi"},
    "concepts":                  {"order_by": "id"},
    "patents":                   {"order_by": "patent_uid"},
    "datacite_outputs":          {"order_by": "doi"},
    "openaire_outputs":          {"order_by": "openaire_id"},
    "anid_projects":             {"order_by": "proyecto"},
    "researchers_orcid":         {"order_by": "orcid_id"},
    "institution_registry":      {"order_by": "normalized_key"},
    "institution_registry_pending_review": {"order_by": "canonical_name"},
    "perfiles_institucionales":  {"order_by": "perfil_id"},
    "convocatorias":             {"order_by": "conv_id"},
    "convocatorias_matching_rules": {"order_by": "rule_id"},
    "convenios_nacionales":      {"order_by": "id"},
    "acuerdos_internacionales":  {"order_by": "id"},
    "entity_registry_proyectos": {"order_by": "project_id"},
    "entity_registry_convocatorias": {"order_by": "convocatoria_id"},
    "convocatorias_matching_institucional": {"order_by": "conv_id"},
    "iaea_inis_monitor":         {"order_by": "inis_id"},
    "arxiv_monitor":             {"order_by": "arxiv_id"},
    "news_monitor":              {"order_by": "news_id"},
    "citation_graph":            {"order_by": "openalex_id"},
    "europmc_works":             {"order_by": "source_id"},
    "bertopic_topics":           {"order_by": "openalex_id"},
    "bertopic_topic_info":       {"order_by": "topic"},
    "citing_papers":             {"order_by": "citing_id"},
    "data_sources":              {"order_by": "source_name"},
}
```

### SENSITIVE_TABLE_CONFIG

Tablas que no se exponen por la ruta pública y se cargan mediante `service_role` desde el backend del dashboard:

```python
SENSITIVE_TABLE_CONFIG = {
    "capital_humano": {"order_by": "id"},
    "funding_complementario": {"order_by": "funding_id"},
    "entity_registry_personas": {"order_by": "persona_id"},
    "entity_links": {"order_by": "origin_type"},
}
```

### _load_public_table(table_name, local_path)

Función central de carga de tablas públicas con tres modos:

```
modo "local"          → _read_csv_fast(local_path)
modo "supabase_public" → _fetch_supabase_table(table_name)  [falla si Supabase no disponible]
modo "auto" (default) → intenta Supabase; si falla → _read_csv_fast(local_path)
```

### _load_sensitive_table(table_name, local_path)

Ruta de carga para tablas sensibles:

```
modo "local"           → _read_csv_fast(local_path)
modo "auto"            → intenta service_role; si falla y existe CSV → fallback local
modo "supabase_public" → intenta service_role; si falla y no hay CSV → error
```

### TABLE_LOAD_STATUS y observabilidad operativa

Cada carga instrumentada registra su resultado en `TABLE_LOAD_STATUS`, con un snapshot por tabla en la sesión actual:

- `supabase_public` → lectura pública remota exitosa
- `supabase_private` → lectura sensible remota con `service_role`
- `local_fallback` → caída controlada a CSV local
- `local_only` → modo local explícito
- `unavailable` → no hubo lectura remota ni respaldo local utilizable

`Dashboard/app.py` consume este registro para construir la franja operativa superior y el inspector de datasets. Así, el usuario ve en tiempo real si la sesión está trabajando contra Supabase, contra respaldos locales o con datasets ausentes.

### Lazy loading por sección en app.py

El dashboard ya no usa un `get_data()` global para precargar todo el observatorio al inicio. En su lugar:

- `_DATASET_LOADERS` declara loaders cacheados por dataset.
- `_SECTION_DATASETS` define qué claves necesita cada sección del sidebar.
- `_build_section_ctx(section_name, can_view_sensitive)` arma el `ctx` solo con la porción requerida por la sección activa.
- `sections/*.py` mantienen la misma interfaz `render(ctx)`; el cambio ocurre en el ensamblaje del contexto, no en la API de cada módulo.

Este patrón reduce el costo de arranque del dashboard y evita leer tablas o CSVs que no son necesarios para la vista actual.

### _fetch_supabase_table(table_name, use_service_role=False)

Implementa **paginación completa** de Supabase:
- Primera página: `range(0, 999)` con `count="exact"` para obtener total
- Páginas siguientes: bucle `while start < total`, chunks de 1.000 filas
- Garantiza que nunca se pierden filas por el límite de 1.000 por request de Supabase

### _read_csv_fast(path)

Lee CSVs usando DuckDB si está disponible (mucho más rápido para archivos grandes), con fallback a pandas:

```python
con.execute(f"SELECT * FROM read_csv_auto('{path}', HEADER=TRUE, SAMPLE_SIZE=-1)")
```

---

## 4. Esquema de tablas Supabase

El DDL completo está en `Database/schema.sql`. La base actual contiene **33 tablas operativas**, distribuidas en **29 tablas públicas** y **4 tablas sensibles**.

### Distribución por módulos

```text
Publicaciones científicas
  publications, publications_enriched, authorships, crossref_data, concepts

Propiedad intelectual
  patents

Financiamiento
  anid_projects, funding_complementario

Capital humano e investigadores
  capital_humano, researchers_orcid

Institucional y territorial
  convenios_nacionales, acuerdos_internacionales,
  institution_registry, institution_registry_pending_review

Outputs de investigación
  datacite_outputs, openaire_outputs

Núcleo institucional
  entity_registry_personas, entity_registry_proyectos,
  entity_registry_convocatorias, entity_links

Convocatorias y matching
  perfiles_institucionales, convocatorias,
  convocatorias_matching_rules, convocatorias_matching_institucional

Vigilancia y analítica científica
  iaea_inis_monitor, arxiv_monitor, news_monitor,
  citation_graph, europmc_works, bertopic_topics,
  bertopic_topic_info, citing_papers

Gobernanza
  data_sources
```

### Tablas sensibles

```text
capital_humano
funding_complementario
entity_registry_personas
entity_links
```

Estas tablas tienen políticas `authenticated` en Supabase y, en la beta privada actual, el dashboard decide si cargarlas según el login interno y el flag `can_view_sensitive`.

### Relaciones FK principales

```
publications (openalex_id)
    ├── authorships.work_id
    ├── publications_enriched.work_id
    ├── crossref_data.doi → publications.doi
    └── concepts.work_id

citing_papers.cited_cchen_id → publications.openalex_id
```

---

## 5. Pipeline RAG / Búsqueda Semántica

### Arquitectura del sistema RAG

```
                    OFFLINE (pre-cómputo)
                    ─────────────────────
cchen_openalex_works.csv
        │
        │ Scripts/build_embeddings.py
        │ Modelo: paraphrase-multilingual-MiniLM-L12-v2
        │ Dimensión: 384 (float32)
        │ Normalización: L2 (para cosine similarity = dot product)
        ▼
cchen_embeddings.npy          ← matriz (N × 384) float32
cchen_embeddings_meta.csv     ← openalex_id | doi | title | year


                    RUNTIME (por cada consulta)
                    ───────────────────────────
Usuario escribe pregunta
        │
        │ Scripts/semantic_search.py :: search(query, top_k=5)
        │ 1. Carga embeddings.npy en memoria (una vez, cached)
        │ 2. Codifica query con SentenceTransformer (misma instancia)
        │ 3. scores = embeddings @ query_vec  (dot product vectorizado)
        │ 4. top_idx = argsort(scores)[::-1][:top_k]
        ▼
DataFrame: openalex_id | doi | title | year | score
        │
        │ Dashboard/sections/asistente_id.py
        │ Formatea top-5 como contexto:
        │   "Papers más relevantes a tu consulta:
        │    - (2023) Título del paper | score=0.87 | doi:..."
        ▼
Groq API  (llama-3.3-70b-versatile)
        │ System prompt: contexto institucional + top-5 papers
        │ User message: pregunta del usuario
        ▼
Respuesta con contexto científico específico de CCHEN
```

### Modelo de embeddings

| Atributo | Valor |
|---------|-------|
| Nombre | `paraphrase-multilingual-MiniLM-L12-v2` |
| Dimensiones | 384 |
| Idiomas soportados | 50+ (incluye español e inglés) |
| Tamaño del modelo | ~480 MB |
| Normalización | L2 (normalizado, cosine = dot product) |
| Batch size | 64 (configurable) |
| Fallback | Si no hay embeddings pre-calculados, el asistente funciona sin RAG |

### Comando para recalcular embeddings

```bash
# Modelo por defecto (multilingual, recomendado)
python3 Scripts/build_embeddings.py

# Modelo alternativo (inglés, más rápido)
python3 Scripts/build_embeddings.py --model all-MiniLM-L6-v2

# Forzar recálculo completo
python3 Scripts/build_embeddings.py --reset
```

---

## 6. Integración Groq API

### Modelos utilizados

| Modelo | Uso | Temperatura | Max tokens |
|--------|-----|------------|-----------|
| `llama-3.3-70b-versatile` | Asistente I+D principal | 0.4 | ~4096 |
| `llama-3.1-8b-instant` | Decisión de chart type para PDF | 0.1 | ~256 |

### Estructura del system prompt

El prompt del asistente inyecta, en orden:

1. **Identidad y rol** — quién es el asistente y para qué sirve
2. **Contexto de producción científica** — total papers, citas, h-index, top 10 papers más citados
3. **Áreas temáticas** — top-8 áreas por frecuencia en publicaciones
4. **Top investigadores** — top-25 investigadores CCHEN con N° papers
5. **Financiamiento ANID** — todos los proyectos con monto e instrumento
6. **Capital humano** — composición por modalidad, centros, universidades
7. **Convocatorias abiertas y próximas** — hasta 6 de cada tipo
8. **Matching institucional** — tabla de oportunidades priorizadas con score
9. **Portafolio tecnológico** — activos TRL con potencial de transferencia
10. **Entidades canónicas** — personas, proyectos, convocatorias y enlaces
11. **Convenios y acuerdos** — contrapartes principales
12. **Financiamiento complementario** — fuentes no-ANID
13. **Papers relevantes (RAG)** — top-5 por búsqueda semántica sobre la consulta actual

### Decisión de gráficos (modelo auxiliar)

Antes de generar el PDF, se llama a `llama-3.1-8b-instant` con un prompt estructurado para decidir:
- Tipo de gráfico apropiado (`production`, `investigators`, `funding`, `collaboration`, `quality`, `human_capital`)
- Investigadores específicos a destacar (si aplica)
- Rango de años relevante
- Keyword clave de la consulta

---

## 7. Generación de PDF — generate_pdf_report()

La función `generate_pdf_report()` en `Dashboard/sections/shared.py` genera un PDF con:

### Estructura del documento

```
CCHEN — Observatorio Tecnológico I+D+i+Tt    ← Título azul institucional
Fecha generación · Modelo Groq              ← Metadatos
────────────────────────────────────         ← Línea roja
[GRÁFICOS CONTEXTUALES]                      ← 1–2 charts matplotlib según topic
────────────────────────────────────
Consulta:
  [Texto de la pregunta del usuario]         ← Fondo azul claro

Respuesta del Asistente:
  [Respuesta del LLM, parseada línea a línea]
  - # → Heading2 (azul, 11pt)
  - "- " / "* " → Bullet (•, sangría 14pt)
  - "  - " → Sub-bullet (◦, sangría doble)
  - Resto → Body (10pt, leading 15pt)
────────────────────────────────────
Observatorio CCHEN · CORFO CCHEN 360       ← Footer gris 8pt
```

### Topics y gráficos asociados

| Topic detectado | Gráficos generados |
|----------------|-------------------|
| `production` | Barras papers/año + línea citas; Top 8 revistas |
| `investigators` | Barras horizontales top-15 investigadores; Citas por investigador |
| `funding` | Barras proyectos por instrumento; Proyectos adjudicados por año |
| `human_capital` | Pie por modalidad; Barras personas/año |
| `collaboration` | Top-12 instituciones colaboradoras; Colaboración por país |
| `quality` | Distribución cuartiles SJR; Pie acceso abierto/cerrado |

### Márgenes y tipografía

| Elemento | Valor |
|---------|-------|
| Márgenes izquierdo/derecho | 2.5 cm |
| Márgenes top/bottom | 2 cm |
| Ancho de contenido útil | 16 cm (PAGE_W) |
| Título | 16pt, azul CCHEN (#003B6F) |
| H2 / secciones | 11pt, azul CCHEN, spaceAfter=4pt |
| Body | 10pt, leading=16pt, spaceAfter=6pt |
| Bullets | 10pt, leading=14pt, leftIndent=14pt, spaceAfter=3pt |
| Sub-bullets | 10pt, leading=14pt, leftIndent=28pt |
| Metadata/footer | 8–9pt, gris (#666666) |

---

## 8. Grafo de citas (pyvis)

El grafo de citas visualiza la red de impacto científico de CCHEN usando pyvis para generar HTML interactivo embebido en Streamlit.

### Datos del grafo

| Métrica | Valor (marzo 2026) |
|--------|-------------------|
| Papers CCHEN con datos de citas | 714 |
| Citas totales acumuladas | 9.840 |
| Papers externos citantes | 8.499 |
| Instituciones citantes identificadas | >200 |

### Fuente de datos

```
Scripts/fetch_openalex_citations.py
    ↓ Para cada paper CCHEN:
    ↓ GET /works/{id}?select=cited_by_count,referenced_works,citing_works
    ↓ Sleep 0.15s entre requests (polite pool OpenAlex: 10 req/s)
    ↓ Guarda hasta 50 citing_works por paper CCHEN

→ Data/Publications/cchen_citation_graph.csv
    openalex_id | doi | year | cited_by_count | referenced_works_count | referenced_ids_sample

→ Data/Publications/cchen_citing_papers.csv
    citing_id | cited_cchen_id | citing_doi | citing_title | citing_year | citing_institutions

→ Database/migrate_citing_papers.py → Supabase: citing_papers (8.499 filas)
```

---

## 9. Integración EuroPMC

EuroPMC complementa OpenAlex para literatura biomédica (medicina nuclear, radiofarmacia, dosimetría médica).

### Queries de búsqueda

```
AFF:"Comision Chilena de Energia Nuclear"
AFF:"CCHEN" AND (COUNTRY:CL)
AFF:"Comisión Chilena de Energía Nuclear"
```

### Datos capturados

| Campo | Descripción |
|-------|-------------|
| `pmid` | PubMed ID |
| `pmcid` | PubMed Central ID |
| `source_id` | EuroPMC source identifier |
| `doi` | DOI del paper |
| `title`, `authors`, `journal` | Metadatos bibliográficos |
| `year`, `pub_date` | Fecha de publicación |
| `cited_by_count` | Citas en EuroPMC |
| `is_open_access` | Estado OA |
| `europmc_url` | URL directa al paper |

### Estado actual

- 74 papers CCHEN verificados con PMID o PMCID
- Cubre principalmente: medicina nuclear, radiofarmacia, dosimetría médica, biofísica
- No requiere API key (rate limit ~10 req/s respetado con sleep 0.5s)

---

## 10. Módulos del observatorio y estado

Según la Memoria Metodológica (Sept. 2025), el observatorio tiene 7 módulos funcionales:

| Módulo | Estado | Stack implementado |
|--------|--------|-------------------|
| a. Vigilancia y Prospección | Parcial | OpenAlex, CrossRef, arXiv, EuroPMC, Semantic Scholar, IAEA INIS |
| b. Inteligencia Aplicada | Activo (TRL 5) | Streamlit, Plotly, Groq LLM, reportlab |
| c. Difusión y Divulgación | Parcial | `generar_boletin.py`, GitHub Actions (pendiente envío) |
| d. Repositorio de Datos | En desarrollo | Supabase, DuckDB, GitHub, Zenodo (objetivo) |
| e. Transferencia y Codiseño | Inicial | Portafolio semilla, DataCite, OpenAIRE |
| f. Colaboración Ecosistémica | Inicial | ROR, convenios, acuerdos, ORCID |
| g. Gobernanza de Datos | Inicial | data_quality.py, entity_registry, timestamps |

---

## 11. Configuración de entornos

### Variables de entorno / secrets

```toml
# Dashboard/.streamlit/secrets.toml
GROQ_API_KEY = "gsk_..."          # Groq LLM — gratis en console.groq.com

[supabase]
url         = "https://xxxx.supabase.co"
anon_key    = "eyJ..."            # Anon key (lectura pública)
service_role_key = "sb_service_role_..."  # beta privada / tablas sensibles
data_source = "auto"              # auto | local | supabase_public
# data_root = "/ruta/absoluta/a/Data"  # solo si Data/ no está junto a Dashboard/

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

```bash
# Database/.env (solo para scripts de migración)
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_KEY=eyJ...               # service_role key (escribe datos, bypasses RLS)
```

### Modos de fuente de datos

```
OBSERVATORIO_DATA_SOURCE=auto          (default)
    → Tablas públicas: intenta Supabase y usa fallback local si falla
    → Tablas sensibles: usa service_role si está configurado

OBSERVATORIO_DATA_SOURCE=local
    → Solo CSVs locales, sin intentar Supabase

OBSERVATORIO_DATA_SOURCE=supabase_public
    → Tablas públicas: fuerza Supabase y falla si no está disponible
    → Tablas sensibles: siguen requiriendo service_role
    → Útil para validaciones estrictas de conectividad remota
```

### Modelo de acceso actual

- El observatorio opera en **beta privada** mediante `internal_auth` en Streamlit.
- El login interno controla la entrada a la app y el flag `can_view_sensitive`.
- Las tablas públicas se consultan con `anon_key`.
- Las tablas sensibles se consultan desde el backend del dashboard con `service_role_key`.
- Este login interno **no emite un JWT de Supabase por usuario**; la autorización fina ocurre en la capa de aplicación y Supabase conserva sus políticas RLS para la base.

### Tokens de APIs externas

| API | Token | Requerido para |
|-----|-------|---------------|
| Groq API | Sí (gratis) | Asistente I+D completo |
| Supabase | Anon key (gratis) | Lectura remota de tablas públicas |
| Supabase | Service role key (privado) | Migración de datos y vistas sensibles en beta privada |
| Altmetric | Sí (free tier) | `fetch_altmetric.py` |
| PatentsView | Sí (gratis con registro) | `fetch_patentsview_patents.py` |
| OpenAlex | No (polite email recomendado) | Todos los scripts OpenAlex |
| EuroPMC | No | `fetch_europmc.py` |
| CrossRef | No (email recomendado) | Notebooks CrossRef |
| ORCID | No (público read) | Notebook ORCID |

---

## 12. Pipeline de migración a Supabase

`Database/migrate_to_supabase.py` realiza migración **idempotente** (upsert):

### Orden de ejecución (por dependencias FK)

```
1.  publications                  (tabla base, sin dependencias)
2.  publications_enriched         (FK → publications.openalex_id)
3.  authorships                   (FK → publications.openalex_id)
4.  crossref_data                 (FK via publications.doi)
5.  concepts                      (FK → publications.openalex_id)
6.  patents                       (independiente)
7.  anid_projects                 (independiente)
8.  funding_complementario        (independiente)
9.  capital_humano                (independiente)
10. researchers_orcid             (independiente)
11. institution_registry          (independiente)
12. institution_registry_pending_review (independiente)
13. entity_registry_personas      (independiente)
14. entity_registry_proyectos     (independiente)
15. entity_registry_convocatorias (independiente)
16. entity_links                  (FK → entity_registry_*)
17. convocatorias_matching_institucional (FK → entity_registry_convocatorias)
18. datacite_outputs              (independiente)
19. openaire_outputs              (independiente)
20. convenios_nacionales          (independiente)
21. acuerdos_internacionales      (independiente)
```

Seguido de `Database/migrate_citing_papers.py` para la tabla `citing_papers` (8.499 filas, migración separada por tamaño).

### Parámetros de migración

- `CHUNK_SIZE = 500` filas por batch (recomendado Supabase ≤1000)
- Modo `upsert` con `on_conflict` por clave primaria
- Limpieza de NaN/NaT/inf → `None` (para Supabase NULL)
- Tipos numpy → Python nativo (`.item()` para compatibilidad JSON)

---

## 13. Automatización con GitHub Actions

`.github/workflows/arxiv_monitor.yml` ejecuta cada lunes 08:00 UTC:

```yaml
jobs:
  monitor:
    runs-on: ubuntu-latest
    steps:
      - python Scripts/arxiv_monitor.py       # arXiv RSS nuclear
      - python Scripts/news_monitor.py        # Google News CCHEN
      - python Scripts/convocatorias_monitor.py  # ANID + fondos (continue-on-error: true)
      - python Scripts/generar_boletin.py     # Boletín HTML semanal
```

Salidas:
- `Data/Vigilancia/arxiv_monitor.csv` + `arxiv_state.json`
- `Data/Vigilancia/news_monitor.csv` + `news_state.json`
- `Data/Vigilancia/convocatorias_curadas.csv`
- `Data/Boletines/boletin_YYYYMMDD.html`

---

## 14. Roadmap TRL

```
TRL 3 ──► TRL 4 ──► TRL 5 ──► TRL 6 ──► TRL 7
  ↑           ↑         ↑ actual
(datos)   (dash v0.1)  (modular + Supabase
                        + citas + patentes
                        + EuroPMC + RAG
                        + entidades canónicas)

TRL 3: Prototipos funcionales en entorno controlado
TRL 4: Dashboard operativo, datos integrados (alcanzado 2024)
TRL 5: Modularización completa, RAG, Supabase, EuroPMC, matching (actual)
TRL 6: Integración completa + operación regular + usuarios externos
TRL 7: Sistema en entorno real con conectividad estable institucional
```

### Hitos alcanzados en TRL 5 (marzo 2026)

- Dashboard modularizado en 11 secciones independientes
- Supabase con 33 tablas operativas, paginación completa y RLS aplicado
- Grafo de citas OpenAlex: 714 papers × 9.840 citas × 8.499 papers citantes
- EuroPMC: 74 papers con PMID/PMCID integrados
- RAG con sentence-transformers multilingüe
- Registro institucional ROR: 697 instituciones con ancla `https://ror.org/03hv95d67`
- Entidades canónicas: 604 personas, 24 proyectos, 26 convocatorias, 657 enlaces
- Matching institucional formal con scoring en 6 dimensiones
- DataCite + OpenAIRE outputs integrados

---

## 15. Decisiones de diseño y justificación

| Decisión | Alternativa descartada | Razón |
|----------|----------------------|-------|
| Streamlit | React, Angular, Flask | Prototipado rápido; 1 desarrollador; migrar cuando haya presupuesto |
| Supabase | MongoDB, Firebase, RDS | PostgreSQL compatible con Django futuro; gratis tier generoso; API REST autogenerada |
| DuckDB | Spark, dask | Sin servidor, integra nativo con pandas, excelente para escala actual (<1M filas) |
| Groq (Llama 3.3) | OpenAI GPT-4, Anthropic | Gratis en tier actual; llama-3.3-70b supera el rendimiento requerido |
| sentence-transformers | OpenAI embeddings, Cohere | Sin costo, ejecutable offline, multilingüe (español nativo) |
| GitHub | GitLab, Bitbucket | GitHub Actions para ETL automatizado; ecosistema familiar |
| Data/ gitignoreado | Subir datos al repo | Datos institucionales sensibles; tamaño excede límites GitHub |
| Gate interno + `service_role` para tablas sensibles | Exponer todo vía `anon` | Permite beta privada con datasets sensibles sin abrirlos públicamente en Streamlit Cloud |
| Paginación manual | Supabase SDK helper | Control explícito sobre el proceso; logging de progreso; gestión de errores |

---

## 16. Contactos y referencias

- **Gestor Tecnológico:** Rodrigo Núñez G. (autor de la propuesta de implementación)
- **Analista de Datos:** Bastián Ayala Inostroza (implementación del prototipo)
- **Proyecto CORFO:** CCHEN 360 — Plan de Fortalecimiento de Aplicaciones Nucleares
- **Institución:** Comisión Chilena de Energía Nuclear (https://www.cchen.cl)
- **ROR institucional:** https://ror.org/03hv95d67
- **Dashboard:** https://cchen-observatorio.streamlit.app
- **Repositorio:** https://github.com/Bastian963/cchen-observatorio
- **Propuesta técnica:** `Docs/design/Propuesta_implementacion.pdf`
- **Diseño metodológico:** `Docs/design/Memoria_metodologica.pdf`
- **Bitácora:** `Docs/reports/Bitacora_BA.pdf`
