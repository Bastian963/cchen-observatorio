-- =============================================================
-- Paso 3 — Tablas: SJR, Semantic Scholar, Altmetric, Patents
-- Pegar en Supabase → SQL Editor → Run
-- =============================================================

-- --------------------------------------------------------
-- 1. SJR Journal Rankings
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS sjr_journal_rankings (
    sourceid                TEXT        NOT NULL,
    year                    SMALLINT    NOT NULL,
    rank                    INTEGER,
    title                   TEXT,
    type                    TEXT,
    issn                    TEXT,
    publisher               TEXT,
    open_access             BOOLEAN,
    open_access_diamond     BOOLEAN,
    sjr                     NUMERIC(12,3),
    sjr_best_quartile       TEXT,
    h_index                 INTEGER,
    total_docs_year         INTEGER,
    total_docs_3years       INTEGER,
    total_refs              INTEGER,
    total_citations_3years  INTEGER,
    citable_docs_3years     INTEGER,
    citations_per_doc_2y    NUMERIC(10,3),
    ref_per_doc             NUMERIC(10,3),
    pct_female              NUMERIC(6,2),
    country                 TEXT,
    region                  TEXT,
    coverage                TEXT,
    categories              TEXT,
    areas                   TEXT,
    PRIMARY KEY (sourceid, year)
);

CREATE INDEX IF NOT EXISTS idx_sjr_year      ON sjr_journal_rankings (year);
CREATE INDEX IF NOT EXISTS idx_sjr_quartile  ON sjr_journal_rankings (sjr_best_quartile);
CREATE INDEX IF NOT EXISTS idx_sjr_country   ON sjr_journal_rankings (country);

-- --------------------------------------------------------
-- 2. Semantic Scholar Papers
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS semantic_scholar_papers (
    openalex_id     TEXT        PRIMARY KEY,
    doi             TEXT,
    ss_paper_id     TEXT,
    title           TEXT,
    year            SMALLINT,
    abstract        TEXT,
    tldr            TEXT,
    citation_count  INTEGER     DEFAULT 0,
    is_oa           BOOLEAN,
    fields_of_study TEXT,
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ss_doi  ON semantic_scholar_papers (doi);
CREATE INDEX IF NOT EXISTS idx_ss_year ON semantic_scholar_papers (year);

-- --------------------------------------------------------
-- 3. Altmetric Scores
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS altmetric_scores (
    doi                         TEXT    PRIMARY KEY,
    altmetric_id                TEXT,
    altmetric_score             NUMERIC(10,3),
    altmetric_score_1y          NUMERIC(10,3),
    altmetric_score_3m          NUMERIC(10,3),
    cited_by_posts_count        INTEGER DEFAULT 0,
    cited_by_tweeters_count     INTEGER DEFAULT 0,
    cited_by_newsoutlets_count  INTEGER DEFAULT 0,
    cited_by_policies_count     INTEGER DEFAULT 0,
    cited_by_wikipedia_count    INTEGER DEFAULT 0,
    cited_by_reddits_count      INTEGER DEFAULT 0,
    cited_by_feeds_count        INTEGER DEFAULT 0,
    mendeley_readers            INTEGER DEFAULT 0,
    is_oa                       TEXT,
    subjects                    TEXT,
    altmetric_url               TEXT,
    fetched_at                  DATE,
    updated_at                  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_altmetric_score ON altmetric_scores (altmetric_score DESC);

-- --------------------------------------------------------
-- 4. Patents (USPTO / PatentsView)
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS patents (
    patent_id           TEXT        PRIMARY KEY,
    title               TEXT,
    patent_date         DATE,
    grant_year          SMALLINT,
    cited_by_count      INTEGER     DEFAULT 0,
    assignees           TEXT,
    assignee_countries  TEXT,
    inventors           TEXT,
    inventor_countries  TEXT,
    n_inventors_cl      INTEGER     DEFAULT 0,
    ipc_symbols         TEXT,
    source              TEXT,
    query_org           TEXT,
    patent_url          TEXT,
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_patents_year ON patents (grant_year);
