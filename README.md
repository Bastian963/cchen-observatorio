# CCHEN — Observatorio Tecnológico I+D+i+Tt

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://cchen-observatorio.streamlit.app)
[![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)](https://www.python.org)
[![Supabase](https://img.shields.io/badge/Supabase-PostgreSQL-3ECF8E?logo=supabase)](https://supabase.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Comisión Chilena de Energía Nuclear — Proyecto CORFO CCHEN 360**
**Responsable:** Bastián Ayala Inostroza · Analista de Datos I+D
**Inicio:** 2024 · **Estado:** Beta interna v0.2 (TRL 5)

---

## Overview

El **Observatorio Tecnológico CCHEN** es una plataforma de inteligencia científica y tecnológica para la Comisión Chilena de Energía Nuclear (CCHEN). Integra datos de múltiples fuentes abiertas y sistemas internos para transformarlos en indicadores estratégicos, vigilancia tecnológica y soporte a la toma de decisiones en materias de I+D+i.

El observatorio cubre cinco grandes dimensiones institucionales:

- **Producción científica** — publicaciones indexadas en OpenAlex, CrossRef, EuroPMC y Scimago SJR
- **Financiamiento I+D** — proyectos ANID (FONDECYT, Anillos, CORFO) y fuentes complementarias
- **Capital humano** — formación de tesistas, becarios, memoristas y postdocs (2022–2025)
- **Colaboración internacional** — co-autorías con 40+ países, 697 instituciones colaboradoras registradas con ancla ROR
- **Transferencia tecnológica** — portafolio de activos, convenios nacionales y acuerdos internacionales

---

## Live Demo

El dashboard está desplegado en Streamlit Cloud con acceso beta privado:

**https://cchen-observatorio.streamlit.app**

---

## Architecture

### Diagrama de alto nivel

```
┌──────────────────────────────────────────────────────────────┐
│  FUENTES EXTERNAS                  FUENTES INTERNAS          │
│  OpenAlex · CrossRef · ORCID       Registro DIAN (Excel)     │
│  EuroPMC · DataCite · OpenAIRE     Capital Humano (Excel)    │
│  ANID Repositorio · Scimago SJR    ANID / CORFO datasets     │
│  arXiv RSS · IAEA INIS             datos.gob.cl              │
└──────────────────────────┬───────────────────────────────────┘
                           │ Scripts/ + Notebooks/ (ETL)
                           ▼
┌──────────────────────────────────────────────────────────────┐
│  DATA LAKE   Data/**/*.csv — archivos originales             │
│              GitHub — versionados y trazables                │
└──────────────────────────┬───────────────────────────────────┘
                           │ Database/migrate_to_supabase.py
                           ▼
┌──────────────────────────────────────────────────────────────┐
│  SUPABASE (PostgreSQL)   33 tablas operativas                │
│                          API REST autogenerada               │
│                          RLS habilitado + policies públicas  │
│                          y autenticadas                      │
└──────────────────────────┬───────────────────────────────────┘
                           │ Dashboard/data_loader.py
                           ▼
┌──────────────────────────────────────────────────────────────┐
│  DASHBOARD STREAMLIT     Dashboard/app.py                    │
│  11 secciones modulares  Dashboard/sections/*.py             │
│  Login beta · Groq · RAG · pyvis  Scripts/semantic_search.py │
└──────────────────────────────────────────────────────────────┘
```

### Stack tecnológico

| Capa | Tecnología | Rol |
|------|-----------|-----|
| Frontend | Streamlit 1.50 | Dashboard interactivo modular |
| Lógica | Python 3.10+, pandas 2.3, plotly 6.6 | Procesamiento y visualización |
| Base de datos | Supabase (PostgreSQL 15) | Almacenamiento persistente, 33 tablas con RLS |
| Lector local | DuckDB | Consultas analíticas rápidas sobre CSV |
| LLM principal | Groq API — llama-3.3-70b-versatile | Asistente I+D conversacional |
| LLM auxiliar | Groq API — llama-3.1-8b-instant | Decisiones de gráficos en PDF |
| Embeddings | sentence-transformers (paraphrase-multilingual-MiniLM-L12-v2) | Búsqueda semántica RAG |
| Grafo de citas | pyvis 0.3.2 | Red interactiva de citas OpenAlex |
| Reportes | reportlab + matplotlib | Generación de PDF con gráficos |
| Fuente ciencias vida | EuroPMC REST API | 74 papers CCHEN con PMID/PMCID |
| Fuente patentes | INAPI Chile + PatentsView | Vigilancia de propiedad intelectual |

---

## Dashboard Sections

El dashboard está organizado en 11 secciones, accesibles desde la barra lateral:

### 1. Panel de Indicadores
Vista ejecutiva consolidada con KPIs principales: total de publicaciones, citas acumuladas, porcentaje en Q1/Q2, financiamiento ANID total, personas formadas. Incluye franja operativa con estado de sesión: datasets remotos, fallbacks locales activos, datasets no disponibles y snapshot local más reciente.

### 2. Producción Científica
Análisis bibliométrico completo: evolución temporal, distribución por cuartil SJR, revistas de publicación, acceso abierto, conceptos temáticos OpenAlex, publicaciones DIAN internas y comparación con registros EuroPMC. Soporta filtros por año, tipo, cuartil y área temática.

### 3. Redes y Colaboración
Mapa choropleth de co-autorías internacionales, tabla de instituciones colaboradoras con ancla ROR, análisis de perfiles ORCID de investigadores CCHEN, y visualización de convenios nacionales (84) y acuerdos internacionales (91).

### 4. Vigilancia Tecnológica
Monitor de tendencias en áreas nucleares clave (dosimetría, medicina nuclear, reactores, radiofarmacia): arXiv RSS, noticias Google, documentos IAEA INIS, análisis de tópicos BERTopic y Semantic Scholar. Incluye perfiles institucionales para matching.

### 5. Financiamiento I+D
Repositorio ANID completo: 24 proyectos adjudicados, $1.337 MM CLP en financiamiento, distribución por instrumento (Fondecyt Regular, Iniciación, Postdoctorado, Anillos). Complementado con fuentes CORFO, IAEA TC y funding detectado por OpenAlex/CrossRef.

### 6. Convocatorias y Matching
Calendario de convocatorias abiertas y próximas (ANID, IAEA, Horizonte Europa, ERC, MSCA). Sistema de matching institucional formal con score de adecuación, elegibilidad, readiness y acción recomendada por perfil CCHEN.

### 7. Transferencia y Portafolio
Portafolio tecnológico semilla con clasificación TRL, unidad responsable y potencial de transferencia. Outputs DataCite y OpenAIRE asociados a CCHEN vía ROR institucional.

### 8. Modelo y Gobernanza
Registro canónico de entidades: 604 personas, 24 proyectos, 26 convocatorias y 657 enlaces operativos. Modelo de gobernanza con fuentes, timestamps de actualización y calidad de datos.

### 9. Formación de Capacidades
Panel de capital humano I+D: 97 personas formadas (2022–2025), distribución por modalidad (tesista, memorista, becario, profesional), centro, universidad tutora y evolución anual.

### 10. Asistente I+D
Asistente conversacional basado en RAG + Groq LLM (llama-3.3-70b-versatile). Inyecta contexto de los 5 papers más relevantes (búsqueda semántica), indicadores clave y datos de convocatorias activas. Genera informes PDF descargables con gráficos contextuales automáticos.

### 11. Grafo de Citas
Visualización interactiva con pyvis del grafo de citas OpenAlex: 714 papers CCHEN con 9.840 citas totales y 8.499 papers externos citantes. Análisis de instituciones y países que citan a CCHEN, impacto por área temática.

---

## Database Schema

La base de datos Supabase contiene **33 tablas operativas**: **29 públicas** y **4 sensibles**. El DDL completo está en `Database/schema.sql`.

| Módulo | Tablas principales | Acceso |
|-------|--------------------|--------|
| Producción científica | `publications`, `publications_enriched`, `authorships`, `crossref_data`, `concepts` | Público |
| Propiedad intelectual | `patents` | Público |
| Financiamiento | `anid_projects`, `funding_complementario` | `funding_complementario` sensible |
| Capital humano e investigadores | `capital_humano`, `researchers_orcid` | `capital_humano` sensible |
| Ecosistema institucional | `convenios_nacionales`, `acuerdos_internacionales`, `institution_registry`, `institution_registry_pending_review` | Público |
| Outputs de investigación | `datacite_outputs`, `openaire_outputs` | Público |
| Núcleo institucional | `entity_registry_personas`, `entity_registry_proyectos`, `entity_registry_convocatorias`, `entity_links` | `entity_registry_personas` y `entity_links` sensibles |
| Convocatorias y matching | `perfiles_institucionales`, `convocatorias`, `convocatorias_matching_rules`, `convocatorias_matching_institucional` | Público |
| Vigilancia y analítica | `iaea_inis_monitor`, `arxiv_monitor`, `news_monitor`, `citation_graph`, `europmc_works`, `bertopic_topics`, `bertopic_topic_info`, `citing_papers` | Público |
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

# 9. Migrar todo a Supabase
python3 Database/migrate_to_supabase.py

# 10. Migrar grafo de citas a Supabase
python3 Database/migrate_citing_papers.py
```

### Scripts de vigilancia (automatizados vía GitHub Actions)

Estos scripts corren cada lunes a las 08:00 UTC:

| Script | Salida | Descripción |
|--------|--------|-------------|
| `Scripts/arxiv_monitor.py` | `Data/Vigilancia/arxiv_monitor.csv` | Papers nuevos en arXiv relevantes a CCHEN |
| `Scripts/news_monitor.py` | `Data/Vigilancia/news_monitor.csv` | Noticias Google sobre CCHEN y energía nuclear |
| `Scripts/convocatorias_monitor.py` | `Data/Vigilancia/convocatorias_curadas.csv` | Convocatorias abiertas ANID y fondos internacionales |

---

## Setup & Deployment

### Instalación local

```bash
# 1. Clonar repositorio
git clone https://github.com/Bastian963/cchen-observatorio.git
cd cchen-observatorio

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

### Despliegue en Streamlit Cloud

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
- Se fija `python-3.11` en `runtime.txt` para evitar problemas de compatibilidad con el stack científico (`sentence-transformers`, `matplotlib`, `pyvis`, `duckdb`).
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
| `internal_auth.*` | Usuarios, claves y roles de ingreso beta | Recomendada en Streamlit Cloud | Secrets del dashboard |
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
```

5. Verificar conectividad real contra tu instancia:

```bash
python3 Scripts/check_supabase_runtime.py
```

6. En `Dashboard/.streamlit/secrets.toml` o en Streamlit Cloud → **Secrets**, configurar:

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

7. Levantar localmente o redeployar Streamlit Cloud.

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
├── requirements.txt                  ← Dependencias raíz para Streamlit Cloud
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
│       └── grafo_citas.py            ← Grafo interactivo pyvis
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
│   ├── schema.sql                    ← DDL completo PostgreSQL
│   ├── migrate_to_supabase.py        ← Migración idempotente de 21 tablas
│   ├── migrate_citing_papers.py      ← Migración de citing_papers (8.499 filas)
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
| EuroPMC REST API | (CSV local) | 74 | Trimestral | No |
| DataCite API | `datacite_outputs` | Variable | Trimestral | No |
| OpenAIRE Graph API | `openaire_outputs` | Variable | Trimestral | No |
| ROR API | `institution_registry` | 697 | Anual | No |
| OpenAlex Citations | `citing_papers` | 8.499 | Trimestral | No |
| arXiv RSS | (CSV vigilancia) | Variable | Semanal (auto) | No |
| Google News | (CSV vigilancia) | Variable | Semanal (auto) | No |
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
