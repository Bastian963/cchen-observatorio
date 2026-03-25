# Dashboard CCHEN - Notas operativas

## Mejoras integradas

- `DuckDB` como backend opcional para lectura rápida de CSVs en `data_loader.py`.
- Lectura opcional de tablas públicas desde `Supabase` con fallback local.
- `st.dialog` para inspección de datasets desde la interfaz.
- `st.fragment` para el bloque operativo del panel principal.
- Autenticación OIDC opcional con `st.login()` / `st.logout()` para proteger vistas sensibles.
- **Asistente I+D (2026-03-24):** spinner mientras espera Groq, expander "📚 Fuentes consultadas" con papers RAG, guard `reply or ""` para evitar crash en stream vacío.

## Instalación / actualización de dependencias

Desde la carpeta raíz del repositorio:

```bash
cd Dashboard
pip install -r requirements.txt
```

Si `duckdb` no está instalado, el dashboard sigue funcionando y hace fallback automático a `pandas`.

## Estándar de tests E2E (recomendado)

Para reproducir el comportamiento de CI sin tocar el Python global del sistema, ejecutar siempre el E2E con `uv` y Python 3.11:

```bash
cd ..
uv run --python 3.11 --with-requirements requirements.txt python Scripts/check_dashboard_e2e.py
```

Notas:

- Evitar `python Scripts/check_dashboard_e2e.py` directo si tu entorno activo no está en 3.11.
- Este flujo no reemplaza ni rompe tu `.venv` local.

## Ejecución tipo producción (contenedor)

Desde la raíz del repositorio:

```bash
docker build -f Dashboard/Dockerfile -t cchen-dashboard:latest .
docker run --rm -p 8501:8501 \
  --name cchen-dashboard \
  -e CCHEN_DATA_ROOT=/app/Data \
  cchen-dashboard:latest
```

Healthcheck local del contenedor:

```bash
curl http://localhost:8501/_stcore/health
```

Notas operativas:

- El contenedor expone `8501` y corre `streamlit run app.py` en modo headless.
- La imagen copia `Dashboard/`, `Scripts/`, `Data/` y `Database/` para permitir operación local completa.
- Si prefieres datos remotos (Supabase), configura `Dashboard/.streamlit/secrets.toml` con bloque `[supabase]`.

### Cobertura CI de Docker

- El pipeline [Dashboard Smoke Test](../.github/workflows/dashboard_smoke.yml) incluye un job `docker-smoke`.
- Este job construye la imagen con `Dashboard/Dockerfile`, levanta el contenedor y valida `/_stcore/health` con reintentos.
- Si el healthcheck falla, CI publica logs del contenedor para diagnóstico rápido.

## Ejecución producción local (sin Docker)

Si aún no tienes Docker, puedes ejecutar el dashboard en modo headless con el script:

```bash
bash Scripts/run_dashboard_prod_local.sh
```

Opcionalmente puedes cambiar host/puerto:

```bash
HOST=127.0.0.1 PORT=8502 bash Scripts/run_dashboard_prod_local.sh
```

Healthcheck:

```bash
curl http://127.0.0.1:8502/_stcore/health
```

## Configurar secretos

Copiar el ejemplo:

```bash
cp Dashboard/.streamlit/secrets.example.toml Dashboard/.streamlit/secrets.toml
```

Luego completar:

- `GROQ_API_KEY` para el asistente.
- `[supabase]` si quieres que el dashboard lea tablas públicas desde Supabase.
- `[auth]` con tu proveedor OIDC si quieres activar login.
- `[observatorio].sensitive_access_emails` con las cuentas autorizadas para vistas sensibles.

## Activar lectura pública desde Supabase

### Paso 1. Instalar dependencias

```bash
cd Dashboard
pip install -r requirements.txt
```

Esto instala `duckdb` y `supabase-py`.

### Paso 2. Configurar bloque `[supabase]` en `secrets.toml`

Ejemplo:

```toml
[supabase]
url = "https://xxxxxxxxxxxxxxxxxx.supabase.co"
anon_key = "eyJ..."
data_source = "auto"
```

Valores admitidos para `data_source`:

- `auto`: intenta Supabase para tablas públicas; si falla, usa archivos locales.
- `local`: fuerza CSV/Excel local.
- `supabase_public`: usa Supabase pública para las tablas soportadas.

### Paso 3. Crear el esquema y migrar datos

Desde `Database/`:

1. Ejecutar `Database/schema.sql` en el SQL Editor de Supabase.
2. Crear `Database/.env` a partir de `.env.example`.
3. Ejecutar:

```bash
python Database/migrate_to_supabase.py
```

### Paso 4. Verificar en la UI

Al abrir el dashboard:

- En el panel principal aparecerá `Backend datos`.
- También aparecerá `Fuente preferida`.
- El `Inspector de datasets` permite revisar muestras y confirmar que los esquemas cargan bien.

### Tablas públicas soportadas en esta fase

- `publications`
- `publications_enriched`
- `authorships`
- `crossref_data`
- `concepts`
- `patents`
- `datacite_outputs`
- `openaire_outputs`
- `anid_projects`
- `researchers_orcid`
- `institution_registry`
- `institution_registry_pending_review`
- `perfiles_institucionales`
- `convocatorias`
- `convocatorias_matching_rules`
- `convenios_nacionales`
- `acuerdos_internacionales`
- `entity_registry_proyectos`
- `entity_registry_convocatorias`
- `convocatorias_matching_institucional`
- `iaea_inis_monitor`
- `arxiv_monitor`
- `news_monitor`
- `citation_graph`
- `europmc_works`
- `bertopic_topics`
- `bertopic_topic_info`
- `citing_papers`
- `data_sources`

### Tablas que siguen locales en esta fase

- `capital_humano`
- `funding_complementario`
- `entity_registry_personas`
- `entity_links`
- `dian_publications`
- `grants_openalex`
- `publications_with_concepts`

Estas siguen locales para no mezclar OIDC de Streamlit con autorización real de Supabase/RLS, y porque son sensibles o internas.

## Activar autenticación OIDC

El ejemplo incluido usa Google como referencia por su `server_metadata_url`.

Campos mínimos:

- `redirect_uri`
- `cookie_secret`
- `client_id`
- `client_secret`
- `server_metadata_url`

Cuando `[auth]` está presente:

- `Formación de Capacidades` muestra solo agregados si no hay sesión autorizada.
- `Asistente I+D` se bloquea para usuarios no autenticados/autorizados.

## Convocatorias abiertas y portales estratégicos

La sección de `Financiamiento I+D` ahora distingue entre:

- convocatorias oficiales abiertas o próximas, con foco en académicos, postdocs y equipos científicos;
- y portales estratégicos internacionales que conviene monitorear, pero que no deben mezclarse como si fueran concursos abiertos.

### Fuente principal

- `Data/Vigilancia/convocatorias_curadas.csv`

### Regenerar la base curada

```bash
python3 Scripts/convocatorias_monitor.py
```

El script:

1. consulta el calendario oficial 2026 de `ANID`,
2. normaliza campos como `estado`, `perfil_objetivo` y `relevancia_cchen`,
3. y genera una salida apta para el dashboard.

### Criterio de diseño

- `Abierto` y `Próximo` se muestran como oportunidades postulables.
- Los portales internacionales serios (`IAEA`, `MSCA`, `ERC`, `Funding & Tenders`) se muestran aparte como radar estratégico.
- El dashboard prioriza perfiles `Académicos / PI`, `Postdoctorado`, `Doctorado`, `Innovación / transferencia` e `Infraestructura / consorcios`.
- Si solo existe el archivo legado `convocatorias.csv`, la interfaz carga ese dataset como fallback y advierte que requiere curaduría.

## Nuevas capas operativas del observatorio

Además de los paneles analíticos originales, el dashboard incorpora tres capas nuevas:

### 1. Convocatorias y matching

- Sección dedicada: `Convocatorias y Matching`
- Fuentes base:
  - `Data/Vigilancia/convocatorias_curadas.csv`
  - `Data/Vigilancia/perfiles_institucionales_cchen.csv`
  - `Data/Vigilancia/convocatorias_matching_rules.csv`
  - `Data/Vigilancia/convocatorias_matching_institucional.csv`
- Cruza convocatorias abiertas o próximas con perfiles observables de CCHEN:
  - `Académicos / PI`
  - `Postdoctorado`
  - `Doctorado`
  - `Innovación / transferencia`
  - `Infraestructura / consorcios`
  - `Colaboración / movilidad`
- El matching usa señales ya cargadas en el observatorio: proyectos ANID, capital humano, publicaciones, convenios y acuerdos.
- El producto operativo ya no se calcula “al vuelo”: consume el CSV formal con `score_total`, `eligibility_status`, `readiness_status`, `owner_unit` y `recommended_action`.

### 2. Portafolio tecnológico / transferencia

- Sección dedicada: `Transferencia y Portafolio`
- Archivo semilla: `Data/Transferencia/portafolio_tecnologico_semilla.csv`
- El portafolio actual debe entenderse como `semilla analítica`, no como inventario tecnológico validado.
- Su objetivo es ordenar capacidades observables y preparar validación posterior de:
  - `TRL`
  - unidad responsable
  - potencial de transferencia
  - propiedad intelectual asociada

### 3. Modelo unificado y gobernanza

- Sección dedicada: `Modelo y Gobernanza`
- Archivos base:
  - `Data/Gobernanza/entity_registry_personas.csv`
  - `Data/Gobernanza/entity_registry_proyectos.csv`
  - `Data/Gobernanza/entity_registry_convocatorias.csv`
  - `Data/Gobernanza/entity_links.csv`
- Define el núcleo institucional operativo del observatorio con IDs estables y relaciones versionables.

## Asistente I+D actualizado

El asistente ahora incorpora, además de publicaciones, ANID y capital humano:

- convocatorias curadas abiertas y próximas,
- matching institucional formal con score, elegibilidad, readiness y unidad responsable,
- portafolio tecnológico semilla,
- convenios nacionales y acuerdos internacionales,
- perfiles ORCID,
- financiamiento complementario e IAEA TC,
- el registro institucional ROR,
- y los registros canónicos de personas, proyectos, convocatorias y enlaces.

Notas importantes:

- Si una capa está incompleta, el asistente debe explicitarlo.
- El portafolio tecnológico se presenta como semilla por validar.
- Si no hay patentes integradas, el asistente no debe inferir un portafolio de PI formal.

## Registro institucional ROR

Se agregó una primera integración formal con `ROR` para normalización institucional.

### Archivos base

- semilla manual: `Data/Institutional/ror_seed_institutions.csv`
- aliases manuales: `Data/Institutional/ror_manual_aliases.csv`
- registro derivado: `Data/Institutional/cchen_institution_registry.csv`
- cola priorizada de revisión: `Data/Institutional/ror_pending_review.csv`
- script regenerable: `Scripts/build_ror_registry.py`
- estado operativo fase 1: `0` filas `Alta`; solo se conservan `manual_selectivo` y `api_candidate_future`

### Regenerar el registro

```bash
python3 Scripts/build_ror_registry.py
```

### Qué hace esta integración

- fija a `CCHEN` como institución ancla con `ROR ID = https://ror.org/03hv95d67`;
- aplica una capa de aliases manuales para variantes en español/inglés, errores ortográficos y subunidades institucionales obvias;
- consolida instituciones observadas desde `OpenAlex authorships`;
- suma evidencia desde `ORCID` y `convenios nacionales`;
- separa instituciones ya normalizadas de aquellas que aún requieren revisión manual;
- y genera una cola priorizada para curaduría local antes de decidir si conviene usar la API viva de `ROR`.

### Limitaciones actuales

- esta primera capa no consulta la API viva de `ROR`; usa una semilla local más la evidencia ya presente en el observatorio;
- algunas instituciones en español/inglés todavía quedan separadas si no existe alias explícito;
- y los acuerdos internacionales aún aportan mejor país que institución canónica.

## Fase 1 operativa: núcleo institucional + matching

La fase 1 deja tres productos formales que ya no dependen de heurísticas del dashboard:

- `Data/Funding/cchen_funding_complementario.csv`
- `Data/Gobernanza/entity_registry_personas.csv`, `entity_registry_proyectos.csv`, `entity_registry_convocatorias.csv`, `entity_links.csv`
- `Data/Vigilancia/convocatorias_matching_institucional.csv`

### Regenerar la fase

```bash
python3 Scripts/build_ror_registry.py
python3 Scripts/fetch_funding_plus.py
python3 Scripts/build_operational_core.py
python3 Database/data_quality.py
```

### Qué valida esta fase

- `ROR`: la cola pendiente no debe contener `priority_level = Alta`
- `Funding`: debe existir al menos una fila `CORFO` y una `IAEA`
- `Matching`: toda convocatoria `Abierta` o `Próxima` debe tener evaluación formal
- `Gobernanza`: los enlaces deben apuntar a entidades canónicas conocidas

## Outputs DataCite

Se agregó una primera integración formal con `DataCite` para capturar `datasets` y otros outputs con DOI asociados a `CCHEN` mediante el `ROR` institucional.

### Archivos base

- script regenerable: `Scripts/fetch_datacite_outputs.py`
- salida principal: `Data/ResearchOutputs/cchen_datacite_outputs.csv`
- estado de última captura: `Data/ResearchOutputs/datacite_state.json`

### Regenerar outputs

Con acceso a red:

```bash
python3 Scripts/fetch_datacite_outputs.py
```

Si trabajas desde una descarga local de la API:

```bash
python3 Scripts/fetch_datacite_outputs.py --raw-json Data/ResearchOutputs/datacite_raw_cchen.json
```

### Qué hace esta integración

- consulta `DataCite API` filtrando por `https://ror.org/03hv95d67`;
- aplana DOI, tipo de output, publisher/repositorio, creators, ORCID y afiliaciones;
- detecta cuántos creators muestran explícitamente la afiliación `CCHEN`;
- y alimenta el módulo de `Transferencia y Portafolio` y el contexto del asistente.

### Limitaciones actuales

- esta primera capa depende de que `DataCite` declare correctamente la afiliación `ROR` en los `creators`;
- no reemplaza publicaciones OpenAlex/Crossref: sirve para outputs de datos, software y otros registros DOI;
- y en entornos con red restringida conviene trabajar con `--raw-json` como fallback reproducible.

## Outputs OpenAIRE

Se agregó una capa inicial con `OpenAIRE Graph` para seguir outputs asociados a investigadores `CCHEN` con `ORCID`.

### Archivos base

- script regenerable: `Scripts/fetch_openaire_outputs.py`
- salida principal: `Data/ResearchOutputs/cchen_openaire_outputs.csv`
- estado de última captura: `Data/ResearchOutputs/openaire_state.json`

### Regenerar outputs

```bash
python3 Scripts/fetch_openaire_outputs.py
```

Opcional para pruebas rápidas:

```bash
python3 Scripts/fetch_openaire_outputs.py --limit-authors 10
```

### Qué hace esta integración

- consulta `OpenAIRE Graph API` por `authorOrcid` usando los perfiles CCHEN ya cargados;
- agrega los resultados por `output`, no por consulta individual;
- marca si el vínculo con `CCHEN` aparece por `ROR`, por nombre institucional o solo por autor;
- y alimenta el dashboard y el asistente con una capa complementaria a `OpenAlex` y `DataCite`.

## Patentes USPTO vía PatentsView

Se extrajo la parte de `PatentsView` del notebook a un script operativo para que la capa de patentes no dependa del notebook.

### Archivos base

- script regenerable: `Scripts/fetch_patentsview_patents.py`
- salida principal: `Data/Patents/cchen_patents_uspto.csv`
- estado de última captura: `Data/Patents/patentsview_state.json`

### Activar cuando tengas la API key

```bash
export PATENTSVIEW_API_KEY="..."
python3 Scripts/fetch_patentsview_patents.py
```

Opcional:

```bash
python3 Scripts/fetch_patentsview_patents.py --query-name "Chilean Nuclear Energy Commission"
python3 Scripts/fetch_patentsview_patents.py --size 1000
```

### Qué hace esta integración

- consulta `PatentsView PatentSearch API` en el endpoint de `patent`;
- usa variantes institucionales de `CCHEN` como `assignees.assignee_organization`;
- aplana inventores, assignees, países, IPC, año y citas;
- y deja el resultado en el formato que ya reconoce el dashboard.

### Nota importante

- `PatentsView` requiere `API key`;
- el script actual consulta hasta `1000` resultados por variante institucional en una sola pasada;
- y la propia documentación oficial advierte que, desde la actualización del `31 de marzo de 2025`, el índice de `assignees` puede ser poco confiable, por lo que conviene validar manualmente los resultados antes de tratarlos como inventario formal.

## Supabase y RLS

Las políticas RLS ya están definidas en `Database/schema.sql`.

Pasos:

1. Crear el proyecto en Supabase.
2. Ejecutar `Database/schema.sql` en el SQL Editor.
3. Migrar datos con `python Database/migrate_to_supabase.py`.
4. Verificar que `capital_humano` y `funding_complementario` queden bajo lectura autenticada.

## Documentación de cambios realizados

1. Se agregó backend opcional `DuckDB` para lectura rápida de CSVs.
2. Se agregó cliente Supabase opcional con selector de fuente `OBSERVATORIO_DATA_SOURCE`.
3. Se habilitó lectura remota solo para tablas públicas con fallback local.
4. Se dejó `capital_humano` y `funding_complementario` fuera de la ruta remota en esta fase.
5. Se agregó `Inspector de datasets` con `st.dialog`.
6. Se agregó bloque operativo con `st.fragment`.
7. Se integró autenticación OIDC opcional para restringir vistas sensibles.
8. Se agregó la sección `Convocatorias y Matching` con scoring por perfil CCHEN.
9. Se agregó la sección `Transferencia y Portafolio` basada en un portafolio tecnológico semilla.
10. Se agregó la sección `Modelo y Gobernanza` con catálogo de entidades y relaciones.
11. Se amplió el contexto del `Asistente I+D` para incorporar las nuevas capas del observatorio.
12. **(v0.3, marzo 2026)** Se modularizó `app.py` en `Dashboard/sections/` — 10 módulos independientes + `shared.py`.
13. **(v0.3)** Asistente LLM con fallback por keywords cuando Groq API no disponible.
14. **(v0.3)** JSON parsing robusto (extractor de llaves balanceadas) para respuestas LLM.
15. **(v0.3)** `news_monitor.py` con flag `--log` y clase `_Tee` para logging persistente.

## Arquitectura de secciones (v0.3)

El dashboard usa un patrón de despacho modular:

```
app.py
├── imports + config + CSS            (líneas 1–482)
├── from sections.shared import ...   (línea 485)
├── from sections import ...          (línea 502)
├── get_data() + sidebar              (líneas 411–1563)
└── _SECTION_MAP dispatch             (líneas 1601–1618)

Dashboard/sections/
├── shared.py              — constantes + helpers compartidos
├── panel_indicadores.py   — KPIs + alertas de gobernanza
├── produccion_cientifica.py
├── redes_colaboracion.py
├── vigilancia_tecnologica.py
├── financiamiento_id.py
├── convocatorias_matching.py
├── transferencia_portafolio.py
├── modelo_gobernanza.py
├── formacion_capacidades.py
└── asistente_id.py
```

Cada sección expone `render(ctx: dict) -> None`. El `ctx` contiene todos los dataframes y variables de contexto.

## Ejecutar

```bash
streamlit run Dashboard/app.py
```
