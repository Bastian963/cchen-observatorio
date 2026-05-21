-- Observatorio CCHEN 360° — Tablas de publicaciones
-- Ejecutar en: Supabase Dashboard → SQL Editor → New query
-- Creado: 2026-05-11
-- ─────────────────────────────────────────────────────────────────────────────

-- pubmed_works
CREATE TABLE IF NOT EXISTS pubmed_works (
  pmid              TEXT PRIMARY KEY,
  doi               TEXT,
  pmcid             TEXT,
  title             TEXT,
  authors           TEXT,
  journal           TEXT,
  year              INTEGER,
  pub_date          TEXT,
  abstract          TEXT,
  keywords          TEXT,
  is_open_access    TEXT,
  affiliation_raw   TEXT,
  pubmed_url        TEXT,
  fetched_at        TEXT
);

-- inspire_works
CREATE TABLE IF NOT EXISTS inspire_works (
  inspire_id          TEXT PRIMARY KEY,
  arxiv_id            TEXT,
  doi                 TEXT,
  title               TEXT,
  authors             TEXT,
  journal             TEXT,
  year                INTEGER,
  pub_date            TEXT,
  abstract            TEXT,
  keywords            TEXT,
  citation_count      INTEGER DEFAULT 0,
  document_type       TEXT,
  inspire_categories  TEXT,
  affiliation_raw     TEXT,
  inspire_url         TEXT,
  fetched_at          TEXT
);

-- arxiv_works
CREATE TABLE IF NOT EXISTS arxiv_works (
  arxiv_id          TEXT PRIMARY KEY,
  doi               TEXT,
  title             TEXT,
  authors           TEXT,
  categories        TEXT,
  year              INTEGER,
  pub_date          TEXT,
  updated_date      TEXT,
  abstract          TEXT,
  primary_category  TEXT,
  journal_ref       TEXT,
  comment           TEXT,
  arxiv_url         TEXT,
  fetched_at        TEXT
);

-- Verificación (ejecutar después para confirmar)
SELECT
  table_name,
  (SELECT count(*) FROM information_schema.columns c
   WHERE c.table_name = t.table_name AND c.table_schema = 'public') AS columnas
FROM information_schema.tables t
WHERE table_schema = 'public'
  AND table_name IN ('pubmed_works', 'inspire_works', 'arxiv_works')
ORDER BY table_name;
