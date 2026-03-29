-- Incremental migration: source refresh runtime governance
-- Apply on existing Supabase projects that already have data_sources.

ALTER TABLE data_sources ADD COLUMN IF NOT EXISTS source_key TEXT;
ALTER TABLE data_sources ADD COLUMN IF NOT EXISTS enabled BOOLEAN DEFAULT FALSE;
ALTER TABLE data_sources ADD COLUMN IF NOT EXISTS runner_command TEXT;
ALTER TABLE data_sources ADD COLUMN IF NOT EXISTS output_targets JSONB DEFAULT '[]'::jsonb;
ALTER TABLE data_sources ADD COLUMN IF NOT EXISTS owner TEXT;
ALTER TABLE data_sources ADD COLUMN IF NOT EXISTS visibility TEXT DEFAULT 'publico';
ALTER TABLE data_sources ADD COLUMN IF NOT EXISTS blocking BOOLEAN DEFAULT FALSE;
ALTER TABLE data_sources ADD COLUMN IF NOT EXISTS freshness_sla_days INTEGER;
ALTER TABLE data_sources ADD COLUMN IF NOT EXISTS last_run_status TEXT;
ALTER TABLE data_sources ADD COLUMN IF NOT EXISTS last_run_id TEXT;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'data_sources_source_key_key'
    ) THEN
        ALTER TABLE data_sources
        ADD CONSTRAINT data_sources_source_key_key UNIQUE (source_key);
    END IF;
END $$;

INSERT INTO data_sources (
    source_name,
    description,
    url,
    table_name,
    notebook_path,
    update_frequency,
    requires_token
)
SELECT
    'Zenodo outputs',
    'Outputs institucionales CCHEN publicados en Zenodo',
    'https://zenodo.org/api',
    NULL,
    'Scripts/download_zenodo_cchen_combined.py',
    'semestral',
    FALSE
WHERE NOT EXISTS (
    SELECT 1 FROM data_sources WHERE source_name = 'Zenodo outputs'
);

UPDATE data_sources
SET source_key = 'openalex_publicaciones',
    enabled = FALSE,
    runner_command = NULL,
    output_targets = '["Data/Publications/cchen_openalex_works.csv"]'::jsonb,
    owner = 'observatorio-cchen',
    visibility = 'publico',
    blocking = FALSE,
    freshness_sla_days = 90
WHERE source_name = 'OpenAlex publicaciones';

UPDATE data_sources
SET source_key = 'crossref',
    enabled = FALSE,
    runner_command = NULL,
    output_targets = '["Data/Publications/cchen_crossref_enriched.csv"]'::jsonb,
    owner = 'observatorio-cchen',
    visibility = 'publico',
    blocking = FALSE,
    freshness_sla_days = 90
WHERE source_name = 'CrossRef';

UPDATE data_sources
SET source_key = 'openalex_conceptos',
    enabled = FALSE,
    runner_command = NULL,
    output_targets = '["Data/Publications/cchen_openalex_concepts.csv"]'::jsonb,
    owner = 'observatorio-cchen',
    visibility = 'publico',
    blocking = FALSE,
    freshness_sla_days = 90
WHERE source_name = 'OpenAlex conceptos';

UPDATE data_sources
SET source_key = 'orcid',
    enabled = FALSE,
    runner_command = NULL,
    output_targets = '["Data/Researchers/cchen_researchers_orcid.csv"]'::jsonb,
    owner = 'observatorio-cchen',
    visibility = 'operador',
    blocking = FALSE,
    freshness_sla_days = 180
WHERE source_name = 'ORCID';

UPDATE data_sources
SET source_key = 'patentsview_uspto',
    enabled = FALSE,
    runner_command = NULL,
    output_targets = '["Data/Patents/cchen_patents_uspto.csv"]'::jsonb,
    owner = 'observatorio-cchen',
    visibility = 'publico',
    blocking = FALSE,
    freshness_sla_days = 180
WHERE source_name = 'PatentsView/USPTO';

UPDATE data_sources
SET source_key = 'anid_repositorio',
    enabled = FALSE,
    runner_command = NULL,
    output_targets = '["Data/ANID/RepositorioAnid_con_monto.csv"]'::jsonb,
    owner = 'observatorio-cchen',
    visibility = 'publico',
    blocking = FALSE,
    freshness_sla_days = 365
WHERE source_name = 'ANID Repositorio';

UPDATE data_sources
SET source_key = 'datos_gob_convenios',
    enabled = FALSE,
    runner_command = NULL,
    output_targets = '["Data/Institutional/clean_Convenios_suscritos_por_la_Com.csv"]'::jsonb,
    owner = 'observatorio-cchen',
    visibility = 'publico',
    blocking = FALSE,
    freshness_sla_days = 180
WHERE source_name = 'datos.gob.cl convenios';

UPDATE data_sources
SET source_key = 'datos_gob_acuerdos',
    enabled = FALSE,
    runner_command = NULL,
    output_targets = '["Data/Institutional/clean_Acuerdos_e_instrumentos_intern.csv"]'::jsonb,
    owner = 'observatorio-cchen',
    visibility = 'publico',
    blocking = FALSE,
    freshness_sla_days = 180
WHERE source_name = 'datos.gob.cl acuerdos';

UPDATE data_sources
SET source_key = 'ror_registry',
    enabled = TRUE,
    runner_command = 'python Scripts/build_ror_registry.py',
    output_targets = '["Data/Institutional/cchen_institution_registry.csv"]'::jsonb,
    owner = 'observatorio-cchen',
    visibility = 'publico',
    blocking = TRUE,
    freshness_sla_days = 180
WHERE source_name = 'ROR registry';

UPDATE data_sources
SET source_key = 'ror_pending_review',
    enabled = TRUE,
    runner_command = 'python Scripts/build_ror_registry.py',
    output_targets = '["Data/Institutional/ror_pending_review.csv"]'::jsonb,
    owner = 'observatorio-cchen',
    visibility = 'operador',
    blocking = FALSE,
    freshness_sla_days = 180
WHERE source_name = 'ROR pending review';

UPDATE data_sources
SET source_key = 'datacite_outputs',
    enabled = TRUE,
    runner_command = 'python Scripts/fetch_datacite_outputs.py',
    output_targets = '["Data/ResearchOutputs/cchen_datacite_outputs.csv","Data/ResearchOutputs/datacite_state.json"]'::jsonb,
    owner = 'observatorio-cchen',
    visibility = 'publico',
    blocking = FALSE,
    freshness_sla_days = 180
WHERE source_name = 'DataCite outputs';

UPDATE data_sources
SET source_key = 'openaire_outputs',
    enabled = TRUE,
    runner_command = 'python Scripts/fetch_openaire_outputs.py',
    output_targets = '["Data/ResearchOutputs/cchen_openaire_outputs.csv","Data/ResearchOutputs/openaire_state.json"]'::jsonb,
    owner = 'observatorio-cchen',
    visibility = 'publico',
    blocking = FALSE,
    freshness_sla_days = 180
WHERE source_name = 'OpenAIRE outputs';

UPDATE data_sources
SET source_key = 'zenodo_outputs',
    enabled = FALSE,
    runner_command = NULL,
    output_targets = '["zenodo_cchen_combined_downloads"]'::jsonb,
    owner = 'observatorio-cchen',
    visibility = 'publico',
    blocking = FALSE,
    freshness_sla_days = 180
WHERE source_name = 'Zenodo outputs';

UPDATE data_sources
SET source_key = 'sjr_scimago',
    enabled = FALSE,
    runner_command = NULL,
    output_targets = '["Data/Publications/cchen_publications_with_quartile_sjr.csv"]'::jsonb,
    owner = 'observatorio-cchen',
    visibility = 'publico',
    blocking = FALSE,
    freshness_sla_days = 365
WHERE source_name = 'SJR/Scimago';

UPDATE data_sources
SET source_key = 'perfiles_institucionales',
    enabled = FALSE,
    runner_command = NULL,
    output_targets = '["Data/Vigilancia/perfiles_institucionales_cchen.csv"]'::jsonb,
    owner = 'observatorio-cchen',
    visibility = 'operador',
    blocking = FALSE,
    freshness_sla_days = 8
WHERE source_name = 'Perfiles institucionales';

UPDATE data_sources
SET source_key = 'convocatorias_curadas',
    enabled = TRUE,
    runner_command = 'python Scripts/convocatorias_monitor.py && python Database/migrate_convocatorias.py',
    output_targets = '["Data/Vigilancia/convocatorias_curadas.csv"]'::jsonb,
    owner = 'observatorio-cchen',
    visibility = 'publico',
    blocking = FALSE,
    freshness_sla_days = 14
WHERE source_name = 'Convocatorias curadas';

UPDATE data_sources
SET source_key = 'matching_rules',
    enabled = FALSE,
    runner_command = NULL,
    output_targets = '["Data/Vigilancia/convocatorias_matching_rules.csv"]'::jsonb,
    owner = 'observatorio-cchen',
    visibility = 'operador',
    blocking = FALSE,
    freshness_sla_days = 14
WHERE source_name = 'Matching rules';

UPDATE data_sources
SET source_key = 'matching_institucional',
    enabled = TRUE,
    runner_command = 'python Scripts/build_operational_core.py',
    output_targets = '["Data/Vigilancia/convocatorias_matching_institucional.csv"]'::jsonb,
    owner = 'observatorio-cchen',
    visibility = 'operador',
    blocking = FALSE,
    freshness_sla_days = 8
WHERE source_name = 'Matching institucional';

UPDATE data_sources
SET source_key = 'iaea_inis_monitor',
    enabled = TRUE,
    runner_command = 'python Scripts/iaea_inis_monitor.py && python Database/migrate_vigilancia.py',
    output_targets = '["Data/Vigilancia/iaea_inis_monitor.csv"]'::jsonb,
    owner = 'observatorio-cchen',
    visibility = 'publico',
    blocking = FALSE,
    freshness_sla_days = 30
WHERE source_name = 'IAEA INIS monitor';

UPDATE data_sources
SET source_key = 'arxiv_monitor',
    enabled = TRUE,
    runner_command = 'python Scripts/arxiv_monitor.py && python Database/migrate_vigilancia.py',
    output_targets = '["Data/Vigilancia/arxiv_monitor.csv"]'::jsonb,
    owner = 'observatorio-cchen',
    visibility = 'publico',
    blocking = TRUE,
    freshness_sla_days = 8
WHERE source_name = 'arXiv monitor';

UPDATE data_sources
SET source_key = 'news_monitor',
    enabled = TRUE,
    runner_command = 'python Scripts/news_monitor.py && python Database/migrate_vigilancia.py',
    output_targets = '["Data/Vigilancia/news_monitor.csv"]'::jsonb,
    owner = 'observatorio-cchen',
    visibility = 'publico',
    blocking = TRUE,
    freshness_sla_days = 8
WHERE source_name = 'News monitor';

UPDATE data_sources
SET source_key = 'citation_graph',
    enabled = TRUE,
    runner_command = 'python Scripts/fetch_openalex_citations.py && python Database/migrate_vigilancia.py && python Database/migrate_citing_papers.py',
    output_targets = '["Data/Publications/cchen_citation_graph.csv"]'::jsonb,
    owner = 'observatorio-cchen',
    visibility = 'publico',
    blocking = FALSE,
    freshness_sla_days = 90
WHERE source_name = 'Citation graph';

UPDATE data_sources
SET source_key = 'europmc_works',
    enabled = TRUE,
    runner_command = 'python Scripts/fetch_europmc.py && python Database/migrate_europmc.py',
    output_targets = '["Data/Publications/cchen_europmc_works.csv","Data/Publications/europmc_state.json"]'::jsonb,
    owner = 'observatorio-cchen',
    visibility = 'publico',
    blocking = FALSE,
    freshness_sla_days = 180
WHERE source_name = 'EuropePMC';

UPDATE data_sources
SET source_key = 'bertopic_topics',
    enabled = FALSE,
    runner_command = NULL,
    output_targets = '["Data/Publications/cchen_bertopic_topics.csv"]'::jsonb,
    owner = 'observatorio-cchen',
    visibility = 'operador',
    blocking = FALSE,
    freshness_sla_days = 90
WHERE source_name = 'BERTopic topics';

UPDATE data_sources
SET source_key = 'bertopic_topic_info',
    enabled = FALSE,
    runner_command = NULL,
    output_targets = '["Data/Publications/cchen_bertopic_topic_info.csv"]'::jsonb,
    owner = 'observatorio-cchen',
    visibility = 'operador',
    blocking = FALSE,
    freshness_sla_days = 90
WHERE source_name = 'BERTopic topic info';

UPDATE data_sources
SET source_key = 'openalex_citations',
    enabled = TRUE,
    runner_command = 'python Scripts/fetch_openalex_citations.py && python Database/migrate_vigilancia.py && python Database/migrate_citing_papers.py',
    output_targets = '["Data/Publications/cchen_citing_papers.csv"]'::jsonb,
    owner = 'observatorio-cchen',
    visibility = 'publico',
    blocking = FALSE,
    freshness_sla_days = 90
WHERE source_name = 'OpenAlex Citations';

UPDATE data_sources
SET source_key = 'funding_complementario',
    enabled = TRUE,
    runner_command = 'python Scripts/fetch_funding_plus.py',
    output_targets = '["Data/Funding/cchen_funding_complementario.csv"]'::jsonb,
    owner = 'observatorio-cchen',
    visibility = 'operador',
    blocking = FALSE,
    freshness_sla_days = 180
WHERE source_name = 'Funding complementario';

UPDATE data_sources
SET source_key = 'entity_registry_personas',
    enabled = TRUE,
    runner_command = 'python Scripts/build_operational_core.py',
    output_targets = '["Data/Gobernanza/entity_registry_personas.csv"]'::jsonb,
    owner = 'observatorio-cchen',
    visibility = 'operador',
    blocking = FALSE,
    freshness_sla_days = 14
WHERE source_name = 'Entity registry personas';

UPDATE data_sources
SET source_key = 'entity_registry_proyectos',
    enabled = TRUE,
    runner_command = 'python Scripts/build_operational_core.py',
    output_targets = '["Data/Gobernanza/entity_registry_proyectos.csv"]'::jsonb,
    owner = 'observatorio-cchen',
    visibility = 'operador',
    blocking = FALSE,
    freshness_sla_days = 14
WHERE source_name = 'Entity registry proyectos';

UPDATE data_sources
SET source_key = 'entity_registry_convocatorias',
    enabled = TRUE,
    runner_command = 'python Scripts/build_operational_core.py',
    output_targets = '["Data/Gobernanza/entity_registry_convocatorias.csv"]'::jsonb,
    owner = 'observatorio-cchen',
    visibility = 'operador',
    blocking = FALSE,
    freshness_sla_days = 14
WHERE source_name = 'Entity registry convocatorias';

UPDATE data_sources
SET source_key = 'entity_links',
    enabled = TRUE,
    runner_command = 'python Scripts/build_operational_core.py',
    output_targets = '["Data/Gobernanza/entity_links.csv"]'::jsonb,
    owner = 'observatorio-cchen',
    visibility = 'operador',
    blocking = FALSE,
    freshness_sla_days = 14
WHERE source_name = 'Entity links';

UPDATE data_sources
SET source_key = 'capital_humano',
    enabled = FALSE,
    runner_command = NULL,
    output_targets = '["Data/Capital humano CCHEN/salida_dataset_maestro/dataset_maestro_limpio.csv"]'::jsonb,
    owner = 'observatorio-cchen',
    visibility = 'operador',
    blocking = FALSE,
    freshness_sla_days = 180
WHERE source_name = 'Capital humano';

CREATE TABLE IF NOT EXISTS data_source_runs (
    run_id            TEXT NOT NULL,
    source_key        TEXT NOT NULL REFERENCES data_sources(source_key),
    trigger_kind      TEXT,
    started_at        TIMESTAMP NOT NULL,
    finished_at       TIMESTAMP NOT NULL,
    status            TEXT NOT NULL,
    records_written   INTEGER DEFAULT 0,
    artifacts_json    JSONB DEFAULT '[]'::jsonb,
    error_summary     TEXT,
    created_at        TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (run_id, source_key)
);

COMMENT ON TABLE data_source_runs IS
    'Historial operativo de corridas del runner canónico de refresh de fuentes.';

ALTER TABLE data_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE data_source_runs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "public_read_data_sources" ON data_sources;
CREATE POLICY "public_read_data_sources" ON data_sources FOR SELECT USING (TRUE);

DROP POLICY IF EXISTS "public_read_data_source_runs" ON data_source_runs;
CREATE POLICY "public_read_data_source_runs" ON data_source_runs FOR SELECT USING (TRUE);
