-- Observatorio CCHEN 360° — Paso 1: tablas de fuentes existentes
-- Ejecutar en: Supabase Dashboard → SQL Editor → New query
-- Creado: 2026-05-11
-- ─────────────────────────────────────────────────────────────────────────────

-- openalex_publicaciones
CREATE TABLE IF NOT EXISTS openalex_publicaciones (
  openalex_id      TEXT PRIMARY KEY,
  doi              TEXT,
  title            TEXT,
  year             INTEGER,
  type             TEXT,
  source           TEXT,
  cited_by_count   INTEGER DEFAULT 0,
  is_oa            BOOLEAN,
  oa_status        TEXT,
  oa_url           TEXT,
  pmid             TEXT,
  pmcid            TEXT,
  europmc_url      TEXT
);

-- crossref_enrichment (JOIN con openalex_publicaciones por doi)
CREATE TABLE IF NOT EXISTS crossref_enrichment (
  doi                 TEXT PRIMARY KEY,
  crossref_funders    TEXT,
  crossref_funder_doi TEXT,
  references_count    INTEGER,
  cited_by_crossref   INTEGER,
  abstract            TEXT,
  license_url         TEXT,
  publisher           TEXT,
  subject             TEXT
);

-- openalex_conceptos (clave compuesta work_id + concept_name)
CREATE TABLE IF NOT EXISTS openalex_conceptos (
  work_id         TEXT NOT NULL,
  concept_name    TEXT NOT NULL,
  concept_level   INTEGER,
  concept_score   REAL,
  source          TEXT,
  PRIMARY KEY (work_id, concept_name)
);

-- researchers_orcid
CREATE TABLE IF NOT EXISTS researchers_orcid (
  orcid_id           TEXT PRIMARY KEY,
  orcid_profile_url  TEXT,
  given_name         TEXT,
  family_name        TEXT,
  full_name          TEXT,
  employers          TEXT,
  education          TEXT,
  orcid_works_count  INTEGER DEFAULT 0
);

-- convenios_nacionales
CREATE TABLE IF NOT EXISTS convenios_nacionales (
  numero              TEXT PRIMARY KEY,
  contraparte         TEXT,
  nro_resolucion      TEXT,
  fecha_resolucion    TEXT,
  nro_convenio        TEXT,
  descripcion         TEXT,
  duracion            TEXT,
  otros_antecedentes  TEXT
);

-- acuerdos_internacionales
CREATE TABLE IF NOT EXISTS acuerdos_internacionales (
  id               TEXT PRIMARY KEY,
  seccion          TEXT,
  numero           TEXT,
  pais_organismo   TEXT,
  instrumento      TEXT,
  firma            TEXT,
  vigencia         TEXT,
  estado           TEXT
);

-- anid_projects
CREATE TABLE IF NOT EXISTS anid_projects (
  proyecto          INTEGER PRIMARY KEY,
  titulo            TEXT,
  resumen           TEXT,
  autor             TEXT,
  institucion       TEXT,
  programa          TEXT,
  tipo              TEXT,
  link              TEXT,
  anio_concurso     INTEGER,
  instrumento       TEXT,
  estado            TEXT,
  full_url          TEXT,
  monto_programa    TEXT,
  monto_num         BIGINT,
  instrumento_full  TEXT,
  concurso_full     TEXT,
  estado_full       TEXT,
  rolinvest         TEXT,
  area_oecd         TEXT,
  area_fondecyt     TEXT,
  fecha_inicio      TEXT,
  fecha_fin         TEXT
);

-- Verificación
SELECT table_name,
  (SELECT count(*) FROM information_schema.columns c
   WHERE c.table_name = t.table_name AND c.table_schema = 'public') AS cols
FROM information_schema.tables t
WHERE table_schema = 'public'
  AND table_name IN (
    'openalex_publicaciones','crossref_enrichment','openalex_conceptos',
    'researchers_orcid','convenios_nacionales','acuerdos_internacionales','anid_projects'
  )
ORDER BY table_name;
