# Database/ — Repositorio de Datos CCHEN

Este directorio contiene el esquema de base de datos, scripts de migración y gobernanza de datos del Observatorio CCHEN 360°.

## Archivos

| Archivo | Descripción |
|---------|-------------|
| `schema.sql` | DDL completo para Supabase/PostgreSQL — ejecutar una vez para crear todas las tablas |
| `migrate_to_supabase.py` | Script de migración CSV → Supabase (upsert idempotente) |
| `data_quality.py` | Verificación de calidad e integridad de los CSVs locales |
| `.env.example` | Plantilla de credenciales (copiar como `.env`) |
| `.env` | Credenciales reales — **NO subir a GitHub** |

## Primer uso

### 1. Crear la base de datos en Supabase

```bash
# 1. Crear proyecto en https://supabase.com (gratis)
# 2. Ir a SQL Editor → New Query
# 3. Pegar el contenido de schema.sql y ejecutar
```

### 2. Configurar credenciales

```bash
cp Database/.env.example Database/.env
# Editar Database/.env con tu SUPABASE_URL y SUPABASE_KEY
```

### 3. Instalar dependencias

```bash
pip install supabase pandas openpyxl python-dotenv
```

### 4. Verificar calidad de datos locales

```bash
python Database/data_quality.py
# Opcional: guardar reporte
python Database/data_quality.py --output Docs/reports/calidad_datos.csv
```

### 5. Migrar datos a Supabase

```bash
python Database/migrate_to_supabase.py
```

El script migra en orden correcto (respetando foreign keys):
1. `publications` → 2. `publications_enriched` → 3. `authorships` → 4. `crossref_data` → 5. `concepts`
6. `patents` → 7. `anid_projects` → 8. `funding_complementario` → 9. `capital_humano` → 10. `researchers_orcid`
11. `institution_registry` → 12. `institution_registry_pending_review` → 13. `datacite_outputs`
14. `openaire_outputs` → 15. `convenios_nacionales` → 16. `acuerdos_internacionales`

## Frecuencia de actualización

| Tabla | Fuente | Frecuencia |
|-------|--------|-----------|
| publications, authorships, concepts | OpenAlex API | Trimestral |
| publications_enriched | OpenAlex + SJR | Trimestral |
| crossref_data | CrossRef API | Trimestral |
| patents | Lens.org o PatentsView/USPTO | Semestral |
| researchers_orcid | ORCID API | Semestral |
| institution_registry | ROR seed + OpenAlex + ORCID + convenios | Semestral |
| institution_registry_pending_review | Derivado de ROR para curaduría manual | Semestral |
| datacite_outputs | DataCite API filtrada por ROR CCHEN | Semestral |
| openaire_outputs | OpenAIRE Graph API vía ORCID CCHEN | Semestral |
| anid_projects | ANID Repositorio | Anual |
| funding_complementario | Registro curado manual | Semestral |
| capital_humano | Registro interno | Semestral |
| convenios_nacionales, acuerdos_internacionales | datos.gob.cl | Semestral |

## Arquitectura de datos

Ver `ARCHITECTURE.md` en la raíz del proyecto para el diseño completo:
- Diagrama de flujo Data Lake → Data Warehouse → Publicación
- Modelo de tablas y relaciones
- Decisiones técnicas justificadas
- Roadmap TRL
