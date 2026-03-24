-- ============================================================
-- OBSERVATORIO TECNOLÓGICO CCHEN 360° — Esquema Supabase
-- ============================================================
-- Base de datos: PostgreSQL 15+ (Supabase)
-- Autor: Bastián Ayala Inostroza
-- Fecha: Marzo 2026
-- Fuente de datos: ver ARCHITECTURE.md → Sección 3
--
-- INSTRUCCIONES:
--   1. Crear proyecto en https://supabase.com (gratis)
--   2. Ir a SQL Editor → New Query
--   3. Pegar este archivo completo y ejecutar
--   4. Luego ejecutar: python Database/migrate_to_supabase.py
-- ============================================================

-- Extensiones útiles
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "unaccent";
CREATE EXTENSION IF NOT EXISTS vector;     -- pgvector: búsqueda semántica

-- ============================================================
-- MÓDULO: PUBLICACIONES CIENTÍFICAS
-- Fuente: OpenAlex API (Notebooks/01_Download_publications.ipynb)
-- ============================================================

CREATE TABLE IF NOT EXISTS publications (
    openalex_id         TEXT PRIMARY KEY,           -- ej: "https://openalex.org/W123456"
    doi                 TEXT UNIQUE,                -- ej: "10.1234/journal.xxx"
    title               TEXT NOT NULL,
    year                INTEGER,
    type                TEXT,                       -- "article", "book-chapter", etc.
    source              TEXT,                       -- nombre de la revista
    cited_by_count      INTEGER DEFAULT 0,
    is_oa               BOOLEAN DEFAULT FALSE,
    oa_status           TEXT,                       -- "gold", "green", "bronze", "closed"
    oa_url              TEXT,
    created_at          TIMESTAMP DEFAULT NOW(),
    updated_at          TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_publications_year ON publications(year);
CREATE INDEX IF NOT EXISTS idx_publications_doi  ON publications(doi);

COMMENT ON TABLE publications IS
    'Publicaciones científicas CCHEN. Fuente: OpenAlex API. 877 registros (2025).';

-- ============================================================

CREATE TABLE IF NOT EXISTS publications_enriched (
    work_id             TEXT PRIMARY KEY REFERENCES publications(openalex_id),
    doi                 TEXT,
    year_num            INTEGER,
    type_norm           TEXT,
    source_norm         TEXT,
    n_authorships       INTEGER,
    n_unique_institutions INTEGER,
    has_outside_cchen_collab  BOOLEAN,
    has_international_collab  BOOLEAN,
    cchen_has_first_author    BOOLEAN,
    cchen_has_last_author     BOOLEAN,
    n_cchen_authors     INTEGER,
    quartile            TEXT CHECK (quartile IN ('Q1','Q2','Q3','Q4')),
    sjr_num             NUMERIC,
    categories          TEXT,
    areas               TEXT,                       -- separado por ";"
    match_status        TEXT,
    is_retracted        BOOLEAN DEFAULT FALSE,
    oa_status           TEXT,
    created_at          TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pub_enr_quartile ON publications_enriched(quartile);
CREATE INDEX IF NOT EXISTS idx_pub_enr_year     ON publications_enriched(year_num);

COMMENT ON TABLE publications_enriched IS
    'Publicaciones con cuartil SJR, colaboración y metadatos adicionales. '
    'Fuente: OpenAlex + Scimago SJR. 616 registros con cuartil disponible.';

-- ============================================================

CREATE TABLE IF NOT EXISTS authorships (
    id                      SERIAL PRIMARY KEY,
    work_id                 TEXT REFERENCES publications(openalex_id),
    author_id               TEXT,
    author_name             TEXT NOT NULL,
    author_order            INTEGER,
    author_position         TEXT,                   -- "first", "middle", "last"
    is_first_author         BOOLEAN,
    is_last_author          BOOLEAN,
    institution_id          TEXT,
    institution_name        TEXT,
    institution_country_code TEXT,                  -- ISO-2: "CL", "US", etc.
    institution_ror         TEXT,
    is_cchen_affiliation    BOOLEAN DEFAULT FALSE,
    created_at              TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_auth_work_id     ON authorships(work_id);
CREATE INDEX IF NOT EXISTS idx_auth_author_name ON authorships(author_name);
CREATE INDEX IF NOT EXISTS idx_auth_cchen       ON authorships(is_cchen_affiliation);
CREATE INDEX IF NOT EXISTS idx_auth_country     ON authorships(institution_country_code);

COMMENT ON TABLE authorships IS
    'Autorías por paper con afiliación institucional. '
    'Fuente: OpenAlex API. 7.971 registros.';

-- ============================================================

CREATE TABLE IF NOT EXISTS crossref_data (
    doi                 TEXT PRIMARY KEY REFERENCES publications(doi),
    crossref_funders    TEXT,                       -- separado por "; "
    crossref_funder_doi TEXT,
    references_count    INTEGER,
    cited_by_crossref   INTEGER,
    abstract            TEXT,
    license_url         TEXT,
    publisher           TEXT,
    subject             TEXT,
    created_at          TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE crossref_data IS
    'Datos CrossRef: financiadores externos, abstracts, referencias. '
    'Fuente: CrossRef Polite Pool API. 764 registros.';

-- ============================================================

CREATE TABLE IF NOT EXISTS concepts (
    id                  SERIAL PRIMARY KEY,
    work_id             TEXT REFERENCES publications(openalex_id),
    concept_name        TEXT NOT NULL,
    concept_level       INTEGER,                    -- 0=dominio, 1=área, 2=sub-área, etc.
    concept_score       NUMERIC,                    -- 0.0 a 1.0
    source              TEXT DEFAULT 'openalex',
    created_at          TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_concepts_work_id ON concepts(work_id);
CREATE INDEX IF NOT EXISTS idx_concepts_name    ON concepts(concept_name);
CREATE INDEX IF NOT EXISTS idx_concepts_level   ON concepts(concept_level);

COMMENT ON TABLE concepts IS
    'Conceptos/áreas temáticas por paper. '
    'Fuente: OpenAlex Concepts API. 21.348 registros (872/877 papers cubiertos).';

-- ============================================================
-- MÓDULO: VIGILANCIA / PATENTES
-- Fuente: Lens.org o PatentsView (USPTO)
-- ============================================================

CREATE TABLE IF NOT EXISTS patents (
    patent_uid          TEXT PRIMARY KEY,
    lens_id             TEXT,
    patent_id           TEXT,
    doc_number          TEXT,
    doc_key             TEXT,
    title               TEXT,
    abstract            TEXT,
    jurisdiction        TEXT,
    publication_date    DATE,
    filing_date         DATE,
    publication_year    INTEGER,
    grant_year          INTEGER,
    publication_type    TEXT,
    assignees           TEXT,
    assignee_countries  TEXT,
    inventors           TEXT,
    inventor_countries  TEXT,
    n_inventors_cl      INTEGER DEFAULT 0,
    ipc_symbols         TEXT,
    cited_by_count      INTEGER DEFAULT 0,
    source              TEXT,
    query_org           TEXT,
    patent_url          TEXT,
    created_at          TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_patents_source ON patents(source);
CREATE INDEX IF NOT EXISTS idx_patents_year ON patents(grant_year);
CREATE INDEX IF NOT EXISTS idx_patents_jurisdiction ON patents(jurisdiction);

COMMENT ON TABLE patents IS
    'Patentes y registros USPTO/Lens asociados a CCHEN. '
    'Fuente: Lens.org o PatentsView, según disponibilidad de credenciales.';

-- ============================================================
-- MÓDULO: FINANCIAMIENTO I+D
-- Fuente: ANID Repositorio (Notebooks/06_ANID_repository.ipynb)
-- ============================================================

CREATE TABLE IF NOT EXISTS anid_projects (
    proyecto            TEXT PRIMARY KEY,           -- código ANID
    titulo              TEXT,
    resumen             TEXT,
    autor               TEXT,
    institucion         TEXT,
    programa            TEXT,
    programa_norm       TEXT,                       -- normalizado: "FONDECYT", etc.
    instrumento         TEXT,
    instrumento_norm    TEXT,                       -- normalizado: "Fondecyt Regular", etc.
    estado              TEXT,
    estado_full         TEXT,
    anio_concurso       INTEGER,
    monto_programa_num  NUMERIC,                    -- CLP
    link                TEXT,
    oecd_area           TEXT,
    created_at          TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_anid_anio        ON anid_projects(anio_concurso);
CREATE INDEX IF NOT EXISTS idx_anid_instrumento ON anid_projects(instrumento_norm);

COMMENT ON TABLE anid_projects IS
    'Proyectos ANID adjudicados por investigadores CCHEN. '
    'Fuente: Repositorio ANID. 30 proyectos.';

-- ============================================================

CREATE TABLE IF NOT EXISTS funding_complementario (
    funding_id          TEXT PRIMARY KEY,
    fuente              TEXT NOT NULL,              -- "CORFO", "IAEA TC", "FIC-R", etc.
    instrumento         TEXT,
    titulo              TEXT,
    anio                INTEGER,
    investigador_principal TEXT,
    institucion         TEXT,
    monto               NUMERIC,
    moneda              TEXT DEFAULT 'CLP',
    estado              TEXT,
    programa            TEXT,
    url                 TEXT,
    area_cchen          TEXT,
    elegibilidad_base   TEXT,
    source_confidence   TEXT,
    last_verified_at    DATE,
    observaciones       TEXT,
    created_at          TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_funding_plus_fuente ON funding_complementario(fuente);
CREATE INDEX IF NOT EXISTS idx_funding_plus_anio ON funding_complementario(anio);

COMMENT ON TABLE funding_complementario IS
    'Financiamiento complementario más allá de ANID (CORFO, IAEA TC y afines) '
    'con identificador estable, elegibilidad base, confianza de fuente y fecha de verificación. '
    'Fuente: dataset curado por Scripts/fetch_funding_plus.py.';

-- ============================================================
-- MÓDULO: CAPITAL HUMANO
-- Fuente: Registro interno CCHEN (Excel → dataset_maestro_limpio.csv)
-- ============================================================

CREATE TABLE IF NOT EXISTS capital_humano (
    id                  SERIAL PRIMARY KEY,
    anio_hoja           INTEGER,
    nombre              TEXT NOT NULL,
    inicio              DATE,
    termino             DATE,
    duracion_dias       INTEGER,
    tutor               TEXT,
    centro_norm         TEXT,
    tipo_norm           TEXT,                       -- "Tesista", "Memorista", "Práctica", etc.
    universidad         TEXT,
    carrera             TEXT,
    monto_contrato_num  NUMERIC,
    ad_honorem          BOOLEAN DEFAULT FALSE,
    objeto_contrato     TEXT,
    observaciones_texto TEXT,
    informe_url_principal TEXT,
    flag_fechas_inconsistentes BOOLEAN,
    flag_tipo_fuera_catalogo   BOOLEAN,
    created_at          TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ch_anio   ON capital_humano(anio_hoja);
CREATE INDEX IF NOT EXISTS idx_ch_centro ON capital_humano(centro_norm);
CREATE INDEX IF NOT EXISTS idx_ch_tipo   ON capital_humano(tipo_norm);

COMMENT ON TABLE capital_humano IS
    'Registro de personas en formación I+D en CCHEN (tesistas, memoristas, prácticas, etc.). '
    'Fuente: Registro interno DIAN. 112 registros (2022–2025).';

-- ============================================================
-- MÓDULO: INVESTIGADORES
-- Fuente: ORCID API (Notebooks/04_ORCID_researchers.ipynb)
-- ============================================================

CREATE TABLE IF NOT EXISTS researchers_orcid (
    orcid_id            TEXT PRIMARY KEY,           -- ej: "0000-0002-1234-5678"
    orcid_profile_url   TEXT,
    given_name          TEXT,
    family_name         TEXT,
    full_name           TEXT,
    employers           TEXT,
    education           TEXT,
    orcid_works_count   INTEGER,
    created_at          TIMESTAMP DEFAULT NOW(),
    updated_at          TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE researchers_orcid IS
    'Perfiles ORCID de investigadores CCHEN. '
    'Fuente: ORCID Public API. 48 perfiles.';

-- ============================================================
-- MÓDULO: COLABORACIÓN ECOSISTÉMICA (INSTITUCIONAL)
-- Fuente: datos.gob.cl (CSVs descargados)
-- ============================================================

CREATE TABLE IF NOT EXISTS convenios_nacionales (
    id                  SERIAL PRIMARY KEY,
    contraparte         TEXT,
    n_resolucion        TEXT,
    fecha_resolucion    DATE,
    n_convenio          TEXT,
    descripcion         TEXT,
    duracion            TEXT,
    otros_antecedentes  TEXT,
    created_at          TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE convenios_nacionales IS
    'Convenios nacionales suscritos por CCHEN. '
    'Fuente: datos.gob.cl. 84 convenios.';

-- ============================================================

CREATE TABLE IF NOT EXISTS acuerdos_internacionales (
    id                  SERIAL PRIMARY KEY,
    seccion             TEXT,                       -- "TABLA 1. Latinoamérica", etc.
    pais                TEXT,
    instrumento         TEXT,
    firma               TEXT,
    vigencia            TEXT,
    created_at          TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_acuerdos_pais ON acuerdos_internacionales(pais);

COMMENT ON TABLE acuerdos_internacionales IS
    'Acuerdos e instrumentos internacionales CCHEN. '
    'Fuente: datos.gob.cl. 41 acuerdos (Latinoamérica, organismos internacionales, otros países).';

-- ============================================================
-- REGISTRO INSTITUCIONAL NORMALIZADO (ROR)
-- Fuente: semilla ROR + OpenAlex authorships + ORCID + convenios
-- ============================================================

CREATE TABLE IF NOT EXISTS institution_registry (
    id                       SERIAL PRIMARY KEY,
    canonical_name           TEXT NOT NULL,
    normalized_key           TEXT UNIQUE NOT NULL,
    ror_id                   TEXT,
    openalex_institution_id  TEXT,
    organization_type        TEXT,
    city                     TEXT,
    country_name             TEXT,
    country_code             TEXT,
    website                  TEXT,
    grid_id                  TEXT,
    isni                     TEXT,
    aliases_observed         TEXT,
    authorships_count        INTEGER DEFAULT 0,
    orcid_profiles_count     INTEGER DEFAULT 0,
    convenios_count          INTEGER DEFAULT 0,
    is_cchen_anchor          BOOLEAN DEFAULT FALSE,
    match_status             TEXT,
    source_evidence          TEXT,
    ror_record_last_modified DATE,
    created_at               TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_institution_registry_ror ON institution_registry(ror_id);
CREATE INDEX IF NOT EXISTS idx_institution_registry_country ON institution_registry(country_code);

COMMENT ON TABLE institution_registry IS
    'Registro institucional normalizado del observatorio con ROR como identificador canónico. '
    'Fuente: semilla ROR + OpenAlex authorships + ORCID + convenios.';

-- ============================================================
-- COLA DE REVISIÓN ROR
-- Fuente: derivados del registro institucional para curaduría
-- ============================================================

CREATE TABLE IF NOT EXISTS institution_registry_pending_review (
    id                       SERIAL PRIMARY KEY,
    canonical_name           TEXT UNIQUE NOT NULL,
    authorships_count        INTEGER DEFAULT 0,
    orcid_profiles_count     INTEGER DEFAULT 0,
    convenios_count          INTEGER DEFAULT 0,
    signal_total             INTEGER DEFAULT 0,
    source_evidence          TEXT,
    priority_level           TEXT,
    recommended_resolution   TEXT,
    api_candidate            BOOLEAN DEFAULT FALSE,
    rationale                TEXT,
    aliases_observed         TEXT,
    created_at               TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ror_pending_priority ON institution_registry_pending_review(priority_level);
CREATE INDEX IF NOT EXISTS idx_ror_pending_resolution ON institution_registry_pending_review(recommended_resolution);

COMMENT ON TABLE institution_registry_pending_review IS
    'Cola priorizada para revisar instituciones sin ROR aún resuelto. '
    'Fuente: Script build_ror_registry.py sobre evidencias de OpenAlex, ORCID y convenios.';

-- ============================================================
-- OUTPUTS DATACITE
-- Fuente: DataCite API filtrada por ROR institucional de CCHEN
-- ============================================================

CREATE TABLE IF NOT EXISTS datacite_outputs (
    doi                       TEXT PRIMARY KEY,
    title                     TEXT,
    publisher                 TEXT,
    publication_year          INTEGER,
    resource_type_general     TEXT,
    resource_type             TEXT,
    client_id                 TEXT,
    url                       TEXT,
    created                   TIMESTAMP,
    updated                   TIMESTAMP,
    state                     TEXT,
    version                   TEXT,
    rights                    TEXT,
    subjects                  TEXT,
    creators                  TEXT,
    creator_orcids            TEXT,
    creator_affiliations      TEXT,
    cchen_affiliated_creators INTEGER DEFAULT 0,
    has_cchen_ror_affiliation BOOLEAN DEFAULT FALSE,
    related_identifiers       TEXT,
    citation_count            INTEGER,
    view_count                INTEGER,
    download_count            INTEGER,
    description               TEXT,
    source                    TEXT,
    source_filter_ror         TEXT,
    created_at                TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_datacite_outputs_year ON datacite_outputs(publication_year);
CREATE INDEX IF NOT EXISTS idx_datacite_outputs_type ON datacite_outputs(resource_type_general);
CREATE INDEX IF NOT EXISTS idx_datacite_outputs_publisher ON datacite_outputs(publisher);

COMMENT ON TABLE datacite_outputs IS
    'Datasets y otros outputs con DOI asociados a CCHEN vía DataCite, filtrados por el ROR institucional. '
    'Fuente: DataCite API + ROR CCHEN.';

-- ============================================================
-- OUTPUTS OPENAIRE
-- Fuente: OpenAIRE Graph API vía ORCID de investigadores CCHEN
-- ============================================================

CREATE TABLE IF NOT EXISTS openaire_outputs (
    openaire_id                    TEXT PRIMARY KEY,
    main_title                     TEXT,
    type                           TEXT,
    publication_date               DATE,
    publisher                      TEXT,
    best_access_right_label        TEXT,
    open_access_color              TEXT,
    publicly_funded                BOOLEAN DEFAULT FALSE,
    is_green                       BOOLEAN DEFAULT FALSE,
    is_in_diamond_journal          BOOLEAN DEFAULT FALSE,
    language_code                  TEXT,
    language_label                 TEXT,
    sources                        TEXT,
    collected_from                 TEXT,
    authors                        TEXT,
    organization_names             TEXT,
    organization_rors              TEXT,
    has_cchen_ror_org              BOOLEAN DEFAULT FALSE,
    has_cchen_name_org             BOOLEAN DEFAULT FALSE,
    match_scope                    TEXT,
    project_codes                  TEXT,
    project_acronyms               TEXT,
    project_funders                TEXT,
    instance_urls                  TEXT,
    instance_types                 TEXT,
    hosted_by                      TEXT,
    pids                           TEXT,
    matched_orcids                 TEXT,
    matched_researchers            TEXT,
    matched_cchen_researchers_count INTEGER DEFAULT 0,
    query_hits                     INTEGER DEFAULT 0,
    source                         TEXT,
    created_at                     TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_openaire_outputs_type ON openaire_outputs(type);
CREATE INDEX IF NOT EXISTS idx_openaire_outputs_date ON openaire_outputs(publication_date);
CREATE INDEX IF NOT EXISTS idx_openaire_outputs_scope ON openaire_outputs(match_scope);

COMMENT ON TABLE openaire_outputs IS
    'Outputs agregados desde OpenAIRE Graph asociados a ORCID de investigadores CCHEN. '
    'La columna match_scope distingue vínculo por organización CCHEN o solo por autor.';

-- ============================================================
-- NÚCLEO INSTITUCIONAL OPERATIVO
-- Fuente: Scripts/build_operational_core.py
-- ============================================================

CREATE TABLE IF NOT EXISTS entity_registry_personas (
    persona_id               TEXT PRIMARY KEY,
    canonical_name           TEXT NOT NULL,
    normalized_name          TEXT,
    orcid_id                 TEXT,
    author_id                TEXT,
    source_anchor            TEXT,
    source_coverage          TEXT,
    is_cchen_investigator    BOOLEAN DEFAULT FALSE,
    appears_in_capital_humano BOOLEAN DEFAULT FALSE,
    appears_in_orcid         BOOLEAN DEFAULT FALSE,
    appears_in_authorships   BOOLEAN DEFAULT FALSE,
    institution_id           TEXT,
    institution_name         TEXT,
    cchen_publications_count INTEGER DEFAULT 0,
    orcid_works_count        INTEGER DEFAULT 0,
    capital_humano_records   INTEGER DEFAULT 0,
    employers                TEXT,
    education                TEXT,
    sensitivity_level        TEXT,
    created_at               TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_entity_personas_institution ON entity_registry_personas(institution_id);
CREATE INDEX IF NOT EXISTS idx_entity_personas_orcid ON entity_registry_personas(orcid_id);

COMMENT ON TABLE entity_registry_personas IS
    'Registro canónico de personas del observatorio. Integra ORCID, OpenAlex y señales internas '
    'para consolidar investigadores y trayectorias observadas.';

CREATE TABLE IF NOT EXISTS entity_registry_proyectos (
    project_id            TEXT PRIMARY KEY,
    proyecto_codigo       TEXT,
    titulo                TEXT NOT NULL,
    anio_concurso         INTEGER,
    autor                 TEXT,
    autor_persona_id      TEXT,
    institucion_id        TEXT,
    institucion_name      TEXT,
    programa              TEXT,
    instrumento           TEXT,
    estado                TEXT,
    monto_programa_num    NUMERIC,
    strategic_profile_id  TEXT,
    data_source           TEXT,
    created_at            TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_entity_projects_author ON entity_registry_proyectos(autor_persona_id);
CREATE INDEX IF NOT EXISTS idx_entity_projects_profile ON entity_registry_proyectos(strategic_profile_id);

COMMENT ON TABLE entity_registry_proyectos IS
    'Registro canónico de proyectos adjudicados o relevantes para CCHEN. '
    'Fuente primaria: ANID Repositorio, normalizado por Scripts/build_operational_core.py.';

CREATE TABLE IF NOT EXISTS entity_registry_convocatorias (
    convocatoria_id      TEXT PRIMARY KEY,
    titulo               TEXT NOT NULL,
    organismo            TEXT,
    categoria            TEXT,
    estado               TEXT,
    perfil_objetivo      TEXT,
    perfil_id            TEXT,
    owner_unit           TEXT,
    relevancia_cchen     TEXT,
    es_oficial           BOOLEAN DEFAULT TRUE,
    postulable           BOOLEAN DEFAULT TRUE,
    apertura_iso         DATE,
    cierre_iso           DATE,
    url                  TEXT,
    last_evaluated_at    DATE,
    created_at           TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_entity_convocatorias_estado ON entity_registry_convocatorias(estado);
CREATE INDEX IF NOT EXISTS idx_entity_convocatorias_perfil ON entity_registry_convocatorias(perfil_id);

COMMENT ON TABLE entity_registry_convocatorias IS
    'Registro canónico de convocatorias curadas para la mesa institucional de oportunidades. '
    'Conserva perfil objetivo, unidad responsable y relevancia CCHEN.';

CREATE TABLE IF NOT EXISTS entity_links (
    origin_type          TEXT NOT NULL,
    origin_id            TEXT NOT NULL,
    relation             TEXT NOT NULL,
    target_type          TEXT NOT NULL,
    target_id            TEXT NOT NULL,
    source_evidence      TEXT,
    confidence           TEXT,
    created_at           TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (origin_type, origin_id, relation, target_type, target_id)
);

CREATE INDEX IF NOT EXISTS idx_entity_links_origin ON entity_links(origin_type, origin_id);
CREATE INDEX IF NOT EXISTS idx_entity_links_target ON entity_links(target_type, target_id);

COMMENT ON TABLE entity_links IS
    'Relaciones operativas entre entidades canónicas del observatorio. '
    'Permite navegar afiliaciones, autorías, asociaciones entre proyectos, personas e instituciones.';

CREATE TABLE IF NOT EXISTS convocatorias_matching_institucional (
    conv_id              TEXT NOT NULL,
    convocatoria_titulo  TEXT,
    estado               TEXT,
    categoria            TEXT,
    organismo            TEXT,
    perfil_objetivo      TEXT,
    perfil_id            TEXT NOT NULL,
    perfil_nombre        TEXT,
    owner_unit           TEXT,
    score_total          INTEGER,
    score_breakdown      TEXT,
    eligibility_status   TEXT,
    readiness_status     TEXT,
    recommended_action   TEXT,
    deadline_class       TEXT,
    evidence_summary     TEXT,
    url                  TEXT,
    relevancia_cchen     TEXT,
    apertura_iso         DATE,
    cierre_iso           DATE,
    match_type           TEXT,
    last_evaluated_at    DATE,
    created_at           TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (conv_id, perfil_id)
);

CREATE INDEX IF NOT EXISTS idx_matching_estado ON convocatorias_matching_institucional(estado);
CREATE INDEX IF NOT EXISTS idx_matching_owner ON convocatorias_matching_institucional(owner_unit);
CREATE INDEX IF NOT EXISTS idx_matching_score ON convocatorias_matching_institucional(score_total);

COMMENT ON TABLE convocatorias_matching_institucional IS
    'Producto operativo de matching entre convocatorias curadas y perfiles institucionales CCHEN. '
    'Incluye score formal, elegibilidad, readiness y acción recomendada.';

-- ============================================================
-- MÓDULO: VIGILANCIA Y MATCHING
-- Fuentes: Data/Vigilancia/*.csv + scripts semanales
-- ============================================================

CREATE TABLE IF NOT EXISTS perfiles_institucionales (
    perfil_id            TEXT PRIMARY KEY,
    perfil_nombre        TEXT NOT NULL,
    owner_unit           TEXT,
    profile_aliases      TEXT,
    secondary_aliases    TEXT,
    descripcion          TEXT,
    created_at           TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE perfiles_institucionales IS
    'Perfiles institucionales base para la mesa de convocatorias CCHEN. '
    'Define unidad responsable, alias y descripción operacional por perfil objetivo.';

CREATE TABLE IF NOT EXISTS convocatorias (
    conv_id              TEXT PRIMARY KEY,
    tipo_registro        TEXT,
    titulo               TEXT NOT NULL,
    organismo            TEXT,
    categoria            TEXT,
    estado               TEXT,
    apertura_texto       TEXT,
    cierre_texto         TEXT,
    fallo_texto          TEXT,
    apertura_iso         DATE,
    cierre_iso           DATE,
    perfil_objetivo      TEXT,
    relevancia_cchen     TEXT,
    fuente               TEXT,
    es_oficial           BOOLEAN DEFAULT TRUE,
    postulable           BOOLEAN DEFAULT TRUE,
    url                  TEXT,
    notas                TEXT,
    created_at           TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_convocatorias_estado ON convocatorias(estado);
CREATE INDEX IF NOT EXISTS idx_convocatorias_categoria ON convocatorias(categoria);
CREATE INDEX IF NOT EXISTS idx_convocatorias_cierre ON convocatorias(cierre_iso);

COMMENT ON TABLE convocatorias IS
    'Convocatorias curadas y priorizadas para CCHEN. '
    'Conserva calendario, relevancia, elegibilidad base y fuente oficial.';

CREATE TABLE IF NOT EXISTS convocatorias_matching_rules (
    rule_id                      TEXT PRIMARY KEY,
    perfil_id                    TEXT,
    exact_aliases                TEXT,
    secondary_aliases            TEXT,
    requiere_doctorado           BOOLEAN DEFAULT FALSE,
    requiere_institucion         BOOLEAN DEFAULT FALSE,
    requiere_transferencia       BOOLEAN DEFAULT FALSE,
    requiere_red_internacional   BOOLEAN DEFAULT FALSE,
    requiere_capacidad_instrumental BOOLEAN DEFAULT FALSE,
    notes                        TEXT,
    created_at                   TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE convocatorias_matching_rules IS
    'Reglas explícitas de matching para convocatorias CCHEN. '
    'Codifica perfiles, alias y banderas mínimas de elegibilidad institucional.';

CREATE TABLE IF NOT EXISTS iaea_inis_monitor (
    inis_id              TEXT PRIMARY KEY,
    title                TEXT NOT NULL,
    authors              TEXT,
    abstract_short       TEXT,
    link                 TEXT,
    published            TEXT,
    subject_area         TEXT,
    relevance_flag       TEXT,
    keywords_found       TEXT,
    source_type          TEXT,
    fetched_at           DATE,
    created_at           TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_inis_relevance ON iaea_inis_monitor(relevance_flag);
CREATE INDEX IF NOT EXISTS idx_inis_subject_area ON iaea_inis_monitor(subject_area);

COMMENT ON TABLE iaea_inis_monitor IS
    'Monitoreo de literatura IAEA INIS relevante a CCHEN. '
    'Fuente: Scripts/iaea_inis_monitor.py.';

CREATE TABLE IF NOT EXISTS arxiv_monitor (
    arxiv_id             TEXT PRIMARY KEY,
    title                TEXT NOT NULL,
    authors              TEXT,
    abstract_short       TEXT,
    link                 TEXT,
    published            TEXT,
    feed_area            TEXT,
    relevance_flag       TEXT,
    keywords_found       TEXT,
    fetched_at           DATE,
    created_at           TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_arxiv_relevance ON arxiv_monitor(relevance_flag);
CREATE INDEX IF NOT EXISTS idx_arxiv_feed_area ON arxiv_monitor(feed_area);

COMMENT ON TABLE arxiv_monitor IS
    'Monitoreo arXiv para áreas científicas relevantes al observatorio. '
    'Fuente: Scripts/arxiv_monitor.py.';

CREATE TABLE IF NOT EXISTS news_monitor (
    news_id              TEXT PRIMARY KEY,
    title                TEXT NOT NULL,
    source_name          TEXT,
    link                 TEXT,
    published            TEXT,
    snippet              TEXT,
    query_label          TEXT,
    topic_flag           TEXT,
    fetched_at           DATE,
    created_at           TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_news_topic_flag ON news_monitor(topic_flag);
CREATE INDEX IF NOT EXISTS idx_news_source_name ON news_monitor(source_name);

COMMENT ON TABLE news_monitor IS
    'Monitoreo de prensa sobre CCHEN, energía nuclear y ciencia relacionada. '
    'Fuente: Scripts/news_monitor.py.';

-- ============================================================
-- MÓDULO: ANALÍTICA CIENTÍFICA Y TEMÁTICA
-- Fuentes: OpenAlex, EuroPMC y BERTopic
-- ============================================================

CREATE TABLE IF NOT EXISTS citation_graph (
    openalex_id             TEXT PRIMARY KEY REFERENCES publications(openalex_id),
    doi                     TEXT,
    year                    INTEGER,
    cited_by_count          INTEGER DEFAULT 0,
    referenced_works_count  INTEGER DEFAULT 0,
    referenced_ids_sample   TEXT,
    fetched_at              DATE,
    created_at              TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_citation_graph_year ON citation_graph(year);
CREATE INDEX IF NOT EXISTS idx_citation_graph_cites ON citation_graph(cited_by_count);

COMMENT ON TABLE citation_graph IS
    'Resumen del grafo de citas por publicación CCHEN. '
    'Incluye conteos de citas recibidas y de referencias salientes desde OpenAlex.';

CREATE TABLE IF NOT EXISTS europmc_works (
    source_id            TEXT PRIMARY KEY,
    doi                  TEXT,
    pmid                 TEXT,
    pmcid                TEXT,
    title                TEXT NOT NULL,
    authors              TEXT,
    journal              TEXT,
    year                 INTEGER,
    pub_date             DATE,
    cited_by_count       INTEGER DEFAULT 0,
    is_open_access       TEXT,
    abstract_available   TEXT,
    source               TEXT,
    keywords             TEXT,
    affiliation_raw      TEXT,
    europmc_url          TEXT,
    fetched_at           DATE,
    created_at           TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_europmc_year ON europmc_works(year);
CREATE INDEX IF NOT EXISTS idx_europmc_doi ON europmc_works(doi);

COMMENT ON TABLE europmc_works IS
    'Outputs CCHEN detectados en EuroPMC. '
    'Complementa OpenAlex con literatura biomédica, PMC y preprints afines.';

CREATE TABLE IF NOT EXISTS bertopic_topics (
    openalex_id          TEXT NOT NULL REFERENCES publications(openalex_id),
    topic_id             INTEGER NOT NULL,
    title                TEXT,
    year                 INTEGER,
    abstract_best        TEXT,
    topic_prob           NUMERIC,
    created_at           TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (openalex_id, topic_id)
);

CREATE INDEX IF NOT EXISTS idx_bertopic_topics_topic ON bertopic_topics(topic_id);
CREATE INDEX IF NOT EXISTS idx_bertopic_topics_year ON bertopic_topics(year);

COMMENT ON TABLE bertopic_topics IS
    'Asignación de tema BERTopic por publicación CCHEN. '
    'Permite navegar distribución temática y series temporales.';

CREATE TABLE IF NOT EXISTS bertopic_topic_info (
    topic                INTEGER PRIMARY KEY,
    count                INTEGER,
    name                 TEXT,
    representation       TEXT,
    representative_docs  TEXT,
    created_at           TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE bertopic_topic_info IS
    'Metadatos de los temas BERTopic: nombre base, representación y documentos representativos.';

-- ============================================================
-- MÓDULO: BÚSQUEDA SEMÁNTICA (pgvector)
-- Fuente: Scripts/build_embeddings.py + Database/migrate_embeddings.py
-- Modelo: paraphrase-multilingual-MiniLM-L12-v2 (384 dims)
-- ============================================================

CREATE TABLE IF NOT EXISTS paper_embeddings (
    openalex_id  TEXT PRIMARY KEY REFERENCES publications(openalex_id),
    doi          TEXT,
    title        TEXT,
    year         NUMERIC,
    abstract     TEXT,
    embedding    vector(384)
);

ALTER TABLE paper_embeddings
    ADD COLUMN IF NOT EXISTS abstract TEXT;

CREATE INDEX IF NOT EXISTS idx_paper_embeddings_vec
    ON paper_embeddings USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 50);

COMMENT ON TABLE paper_embeddings IS
    'Embeddings semánticos de publicaciones CCHEN para búsqueda vectorial. '
    'Modelo: paraphrase-multilingual-MiniLM-L12-v2 (384 dims, normalizado L2). '
    '877 vectores. Fuente: Database/migrate_embeddings.py.';

-- Función RPC para búsqueda semántica por similitud coseno
CREATE OR REPLACE FUNCTION match_papers(
    query_embedding vector(384),
    match_count     int DEFAULT 5
)
RETURNS TABLE(openalex_id text, doi text, title text, year numeric, abstract text, similarity float)
LANGUAGE sql STABLE AS $$
    SELECT  pe.openalex_id,
            pe.doi,
            pe.title,
            pe.year,
            pe.abstract,
            1 - (pe.embedding <=> query_embedding) AS similarity
    FROM    paper_embeddings pe
    ORDER BY pe.embedding <=> query_embedding
    LIMIT   match_count;
$$;

ALTER TABLE paper_embeddings ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "public_read_paper_embeddings" ON paper_embeddings;
CREATE POLICY "public_read_paper_embeddings" ON paper_embeddings FOR SELECT USING (TRUE);

-- ============================================================
-- MÓDULO: GRAFO DE CITAS
-- Fuente: OpenAlex citation graph (papers citantes)
-- ============================================================

CREATE TABLE IF NOT EXISTS citing_papers (
    citing_id           TEXT NOT NULL,
    cited_cchen_id      TEXT NOT NULL REFERENCES publications(openalex_id),
    citing_doi          TEXT,
    citing_title        TEXT,
    citing_year         INTEGER,
    citing_institutions TEXT,
    created_at          TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (citing_id, cited_cchen_id)
);

CREATE INDEX IF NOT EXISTS idx_citing_papers_year ON citing_papers(citing_year);
CREATE INDEX IF NOT EXISTS idx_citing_papers_cited ON citing_papers(cited_cchen_id);

COMMENT ON TABLE citing_papers IS
    'Papers externos que citan publicaciones CCHEN. '
    'Fuente: grafo de citación OpenAlex. 8.499 registros esperados.';

-- ============================================================
-- MÓDULO: GOBERNANZA DE DATOS
-- Tabla de metadatos de fuentes (trazabilidad)
-- ============================================================

CREATE TABLE IF NOT EXISTS data_sources (
    source_name         TEXT PRIMARY KEY,
    description         TEXT,
    url                 TEXT,
    table_name          TEXT,                       -- tabla Supabase asociada
    notebook_path       TEXT,                       -- notebook que actualiza esta fuente
    last_updated        DATE,
    next_update_due     DATE,
    update_frequency    TEXT,                       -- "trimestral", "anual", etc.
    record_count        INTEGER,
    quality_score       NUMERIC,                    -- 0.0 a 1.0 (generado por data_quality.py)
    requires_token      BOOLEAN DEFAULT FALSE,
    token_source        TEXT,
    notes               TEXT,
    created_at          TIMESTAMP DEFAULT NOW(),
    updated_at          TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE data_sources IS
    'Catálogo de fuentes de datos del observatorio. '
    'Actualizado automáticamente por Database/data_quality.py.';

-- Poblar con las fuentes conocidas
INSERT INTO data_sources (source_name, description, url, table_name, notebook_path, update_frequency, requires_token) VALUES
    ('OpenAlex publicaciones',  'Publicaciones científicas CCHEN indexadas en OpenAlex',           'https://api.openalex.org', 'publications',            'Notebooks/01_Download_publications.ipynb',  'trimestral', FALSE),
    ('CrossRef',                'Financiadores externos, abstracts y referencias por DOI',          'https://api.crossref.org', 'crossref_data',           'Notebooks/02_CrossRef_enrichment.ipynb',     'trimestral', FALSE),
    ('OpenAlex Conceptos',      'Conceptos y áreas temáticas por paper',                            'https://api.openalex.org', 'concepts',                'Notebooks/03_OpenAlex_concepts.ipynb',       'trimestral', FALSE),
    ('ORCID',                   'Perfiles de investigadores CCHEN',                                 'https://pub.orcid.org',    'researchers_orcid',       'Notebooks/04_ORCID_researchers.ipynb',       'semestral',  FALSE),
    ('PatentsView / USPTO',     'Patentes USPTO asociadas a CCHEN vía PatentsView; requiere API key','https://search.patentsview.org/docs/', 'patents', 'Scripts/fetch_patentsview_patents.py', 'semestral', TRUE),
    ('ANID Repositorio',        'Proyectos FONDECYT y otros fondos adjudicados',                   'https://repositorio.anid.cl', 'anid_projects',         'Notebooks/06_ANID_repository.ipynb',         'anual',      FALSE),
    ('datos.gob.cl convenios',  'Convenios nacionales suscritos por CCHEN',                        'https://datos.gob.cl',     'convenios_nacionales',    NULL,                                         'semestral',  FALSE),
    ('datos.gob.cl acuerdos',   'Acuerdos internacionales CCHEN',                                  'https://datos.gob.cl',     'acuerdos_internacionales',NULL,                                         'semestral',  FALSE),
    ('ROR registry',            'Registro institucional normalizado con identificadores ROR',       'https://ror.org',          'institution_registry',    'Scripts/build_ror_registry.py',              'semestral',  FALSE),
    ('ROR pending review',      'Cola priorizada de instituciones sin ROR para curaduría manual',  'https://ror.org',          'institution_registry_pending_review', 'Scripts/build_ror_registry.py',       'semestral',  FALSE),
    ('DataCite outputs',        'Datasets y otros outputs con DOI asociados a CCHEN vía ROR',      'https://api.datacite.org', 'datacite_outputs',        'Scripts/fetch_datacite_outputs.py',          'semestral',  FALSE),
    ('OpenAIRE outputs',        'Outputs asociados a investigadores CCHEN vía ORCID en OpenAIRE', 'https://api.openaire.eu',  'openaire_outputs',        'Scripts/fetch_openaire_outputs.py',          'semestral',  FALSE),
    ('SJR Scimago',             'Rankings y cuartiles de revistas científicas',                    'https://www.scimagojr.com','publications_enriched',   NULL,                                         'anual',      FALSE),
    ('Perfiles institucionales', 'Perfiles institucionales base para matching y priorización',      NULL,                       'perfiles_institucionales', 'Data/Vigilancia/perfiles_institucionales_cchen.csv', 'semanal', FALSE),
    ('Convocatorias curadas',   'Calendario curado de convocatorias relevantes para CCHEN',         'https://anid.cl/calendario-concursos-2026/', 'convocatorias', 'Scripts/convocatorias_monitor.py', 'semanal', FALSE),
    ('Reglas de matching',      'Reglas explícitas de elegibilidad y alias para matching institucional', NULL,                 'convocatorias_matching_rules', 'Data/Vigilancia/convocatorias_matching_rules.csv', 'semanal', FALSE),
    ('Matching institucional',  'Scoring formal de convocatorias abiertas y próximas para CCHEN',   NULL,                       'convocatorias_matching_institucional', 'Scripts/build_operational_core.py', 'semanal', FALSE),
    ('IAEA INIS monitor',       'Monitoreo de literatura INIS relevante a CCHEN',                   'https://inis.iaea.org',    'iaea_inis_monitor',       'Scripts/iaea_inis_monitor.py',               'semanal', FALSE),
    ('arXiv monitor',           'Monitoreo de papers arXiv relevantes al observatorio',             'https://arxiv.org',        'arxiv_monitor',           'Scripts/arxiv_monitor.py',                    'semanal', FALSE),
    ('News monitor',            'Monitoreo de prensa y noticias sobre CCHEN y energía nuclear',     'https://news.google.com',  'news_monitor',            'Scripts/news_monitor.py',                     'semanal', FALSE),
    ('Citation graph',          'Resumen de citas y referencias de publicaciones CCHEN en OpenAlex', 'https://api.openalex.org', 'citation_graph',         'Scripts/fetch_openalex_citations.py',         'trimestral', FALSE),
    ('EuroPMC works',           'Outputs CCHEN identificados en EuroPMC',                           'https://europepmc.org',    'europmc_works',           'Scripts/fetch_europmc.py',                    'semestral', FALSE),
    ('BERTopic topics',         'Asignación temática BERTopic por publicación CCHEN',               NULL,                       'bertopic_topics',         'Scripts/run_bertopic.py',                     'trimestral', FALSE),
    ('BERTopic topic info',     'Metadatos y términos representativos de temas BERTopic',           NULL,                       'bertopic_topic_info',     'Scripts/run_bertopic.py',                     'trimestral', FALSE),
    ('OpenAlex Citations',      'Papers externos que citan publicaciones CCHEN',                  'https://api.openalex.org', 'citing_papers',           'Scripts/fetch_openalex_citations.py',        'trimestral', FALSE),
    ('Financiamiento complementario', 'CORFO, IAEA TC y otros fondos curados con elegibilidad y confianza', NULL, 'funding_complementario', 'Scripts/fetch_funding_plus.py', 'semestral', FALSE),
    ('Entity registry personas', 'Registro canónico de personas del observatorio',                  NULL,                       'entity_registry_personas', 'Scripts/build_operational_core.py',          'semanal',    FALSE),
    ('Entity registry proyectos','Registro canónico de proyectos adjudicados y asociados',          NULL,                       'entity_registry_proyectos','Scripts/build_operational_core.py',          'semanal',    FALSE),
    ('Entity registry convocatorias','Registro canónico de convocatorias curadas',                  NULL,                       'entity_registry_convocatorias','Scripts/build_operational_core.py',       'semanal',    FALSE),
    ('Entity links',            'Relaciones operativas entre entidades canónicas del observatorio', NULL,                       'entity_links',            'Scripts/build_operational_core.py',          'semanal',    FALSE),
    ('Capital humano',          'Registro interno consolidado de formación de capital humano CCHEN', NULL,                      'capital_humano',          'Data/Capital humano CCHEN/salida_dataset_maestro/dataset_maestro_limpio.csv', 'semestral', FALSE)
ON CONFLICT (source_name) DO NOTHING;

-- ============================================================
-- VISTAS ÚTILES
-- ============================================================

-- Vista: producción por año con KPIs básicos
CREATE OR REPLACE VIEW v_produccion_anual AS
SELECT
    p.year,
    COUNT(*)                        AS n_papers,
    SUM(p.cited_by_count)           AS citas_totales,
    ROUND(AVG(p.cited_by_count), 2) AS citas_promedio,
    SUM(CASE WHEN p.is_oa THEN 1 ELSE 0 END) AS n_oa,
    ROUND(100.0 * SUM(CASE WHEN p.is_oa THEN 1 ELSE 0 END) / COUNT(*), 1) AS pct_oa
FROM publications p
WHERE p.year IS NOT NULL AND p.year >= 1990
GROUP BY p.year
ORDER BY p.year;

-- Vista: top investigadores CCHEN
CREATE OR REPLACE VIEW v_top_investigadores AS
SELECT
    a.author_name,
    COUNT(DISTINCT a.work_id)       AS n_papers,
    SUM(p.cited_by_count)           AS citas_totales,
    MIN(p.year)                     AS primer_paper,
    MAX(p.year)                     AS ultimo_paper
FROM authorships a
JOIN publications p ON a.work_id = p.openalex_id
WHERE a.is_cchen_affiliation = TRUE
GROUP BY a.author_name
ORDER BY n_papers DESC;

-- Vista: colaboración internacional
CREATE OR REPLACE VIEW v_colaboracion_paises AS
SELECT
    a.institution_country_code      AS pais_iso2,
    COUNT(DISTINCT a.work_id)       AS papers_conjuntos,
    COUNT(DISTINCT a.institution_name) AS n_instituciones
FROM authorships a
WHERE a.is_cchen_affiliation = FALSE
  AND a.institution_country_code IS NOT NULL
GROUP BY a.institution_country_code
ORDER BY papers_conjuntos DESC;

-- Vista: distribución por cuartil SJR
CREATE OR REPLACE VIEW v_cuartiles AS
SELECT
    pe.quartile,
    pe.year_num                     AS year,
    COUNT(*)                        AS n_papers
FROM publications_enriched pe
WHERE pe.quartile IS NOT NULL
GROUP BY pe.quartile, pe.year_num
ORDER BY pe.year_num, pe.quartile;

-- Vista: financiadores externos (CrossRef)
CREATE OR REPLACE VIEW v_financiadores_externos AS
SELECT
    TRIM(funder)                    AS financiador,
    COUNT(*)                        AS n_papers
FROM crossref_data cd,
     LATERAL UNNEST(string_to_array(cd.crossref_funders, '; ')) AS funder
WHERE cd.crossref_funders IS NOT NULL
GROUP BY TRIM(funder)
ORDER BY n_papers DESC;

-- ============================================================
-- ROW LEVEL SECURITY (para Supabase)
-- Datos del observatorio son públicos de lectura
-- ============================================================

ALTER TABLE publications             ENABLE ROW LEVEL SECURITY;
ALTER TABLE publications_enriched    ENABLE ROW LEVEL SECURITY;
ALTER TABLE authorships              ENABLE ROW LEVEL SECURITY;
ALTER TABLE crossref_data            ENABLE ROW LEVEL SECURITY;
ALTER TABLE concepts                 ENABLE ROW LEVEL SECURITY;
ALTER TABLE patents                  ENABLE ROW LEVEL SECURITY;
ALTER TABLE anid_projects            ENABLE ROW LEVEL SECURITY;
ALTER TABLE capital_humano           ENABLE ROW LEVEL SECURITY;
ALTER TABLE researchers_orcid        ENABLE ROW LEVEL SECURITY;
ALTER TABLE convenios_nacionales     ENABLE ROW LEVEL SECURITY;
ALTER TABLE acuerdos_internacionales ENABLE ROW LEVEL SECURITY;
ALTER TABLE institution_registry     ENABLE ROW LEVEL SECURITY;
ALTER TABLE institution_registry_pending_review ENABLE ROW LEVEL SECURITY;
ALTER TABLE datacite_outputs         ENABLE ROW LEVEL SECURITY;
ALTER TABLE openaire_outputs         ENABLE ROW LEVEL SECURITY;
ALTER TABLE funding_complementario   ENABLE ROW LEVEL SECURITY;
ALTER TABLE entity_registry_personas ENABLE ROW LEVEL SECURITY;
ALTER TABLE entity_registry_proyectos ENABLE ROW LEVEL SECURITY;
ALTER TABLE entity_registry_convocatorias ENABLE ROW LEVEL SECURITY;
ALTER TABLE entity_links             ENABLE ROW LEVEL SECURITY;
ALTER TABLE perfiles_institucionales ENABLE ROW LEVEL SECURITY;
ALTER TABLE convocatorias            ENABLE ROW LEVEL SECURITY;
ALTER TABLE convocatorias_matching_rules ENABLE ROW LEVEL SECURITY;
ALTER TABLE convocatorias_matching_institucional ENABLE ROW LEVEL SECURITY;
ALTER TABLE iaea_inis_monitor        ENABLE ROW LEVEL SECURITY;
ALTER TABLE arxiv_monitor            ENABLE ROW LEVEL SECURITY;
ALTER TABLE news_monitor             ENABLE ROW LEVEL SECURITY;
ALTER TABLE citation_graph           ENABLE ROW LEVEL SECURITY;
ALTER TABLE europmc_works            ENABLE ROW LEVEL SECURITY;
ALTER TABLE bertopic_topics          ENABLE ROW LEVEL SECURITY;
ALTER TABLE bertopic_topic_info      ENABLE ROW LEVEL SECURITY;
ALTER TABLE citing_papers           ENABLE ROW LEVEL SECURITY;
ALTER TABLE data_sources             ENABLE ROW LEVEL SECURITY;

-- Lectura pública para tablas no sensibles
DROP POLICY IF EXISTS "public_read_publications" ON publications;
DROP POLICY IF EXISTS "public_read_pub_enriched" ON publications_enriched;
DROP POLICY IF EXISTS "public_read_authorships" ON authorships;
DROP POLICY IF EXISTS "public_read_crossref" ON crossref_data;
DROP POLICY IF EXISTS "public_read_concepts" ON concepts;
DROP POLICY IF EXISTS "public_read_patents" ON patents;
DROP POLICY IF EXISTS "public_read_anid" ON anid_projects;
DROP POLICY IF EXISTS "public_read_orcid" ON researchers_orcid;
DROP POLICY IF EXISTS "public_read_convenios" ON convenios_nacionales;
DROP POLICY IF EXISTS "public_read_acuerdos" ON acuerdos_internacionales;
DROP POLICY IF EXISTS "public_read_institution_registry" ON institution_registry;
DROP POLICY IF EXISTS "public_read_ror_pending" ON institution_registry_pending_review;
DROP POLICY IF EXISTS "public_read_datacite" ON datacite_outputs;
DROP POLICY IF EXISTS "public_read_openaire" ON openaire_outputs;
DROP POLICY IF EXISTS "public_read_entity_projects" ON entity_registry_proyectos;
DROP POLICY IF EXISTS "public_read_entity_convocatorias" ON entity_registry_convocatorias;
DROP POLICY IF EXISTS "public_read_profiles" ON perfiles_institucionales;
DROP POLICY IF EXISTS "public_read_convocatorias" ON convocatorias;
DROP POLICY IF EXISTS "public_read_matching_rules" ON convocatorias_matching_rules;
DROP POLICY IF EXISTS "public_read_matching" ON convocatorias_matching_institucional;
DROP POLICY IF EXISTS "public_read_inis_monitor" ON iaea_inis_monitor;
DROP POLICY IF EXISTS "public_read_arxiv_monitor" ON arxiv_monitor;
DROP POLICY IF EXISTS "public_read_news_monitor" ON news_monitor;
DROP POLICY IF EXISTS "public_read_citation_graph" ON citation_graph;
DROP POLICY IF EXISTS "public_read_europmc" ON europmc_works;
DROP POLICY IF EXISTS "public_read_bertopic_topics" ON bertopic_topics;
DROP POLICY IF EXISTS "public_read_bertopic_info" ON bertopic_topic_info;
DROP POLICY IF EXISTS "public_read_citing_papers" ON citing_papers;
DROP POLICY IF EXISTS "public_read_data_sources" ON data_sources;

CREATE POLICY "public_read_publications"    ON publications             FOR SELECT USING (TRUE);
CREATE POLICY "public_read_pub_enriched"    ON publications_enriched    FOR SELECT USING (TRUE);
CREATE POLICY "public_read_authorships"     ON authorships              FOR SELECT USING (TRUE);
CREATE POLICY "public_read_crossref"        ON crossref_data            FOR SELECT USING (TRUE);
CREATE POLICY "public_read_concepts"        ON concepts                 FOR SELECT USING (TRUE);
CREATE POLICY "public_read_patents"         ON patents                 FOR SELECT USING (TRUE);
CREATE POLICY "public_read_anid"            ON anid_projects            FOR SELECT USING (TRUE);
CREATE POLICY "public_read_orcid"           ON researchers_orcid        FOR SELECT USING (TRUE);
CREATE POLICY "public_read_convenios"       ON convenios_nacionales      FOR SELECT USING (TRUE);
CREATE POLICY "public_read_acuerdos"        ON acuerdos_internacionales FOR SELECT USING (TRUE);
CREATE POLICY "public_read_institution_registry" ON institution_registry FOR SELECT USING (TRUE);
CREATE POLICY "public_read_ror_pending"     ON institution_registry_pending_review FOR SELECT USING (TRUE);
CREATE POLICY "public_read_datacite"        ON datacite_outputs         FOR SELECT USING (TRUE);
CREATE POLICY "public_read_openaire"        ON openaire_outputs         FOR SELECT USING (TRUE);
CREATE POLICY "public_read_entity_projects" ON entity_registry_proyectos FOR SELECT USING (TRUE);
CREATE POLICY "public_read_entity_convocatorias" ON entity_registry_convocatorias FOR SELECT USING (TRUE);
CREATE POLICY "public_read_profiles"        ON perfiles_institucionales FOR SELECT USING (TRUE);
CREATE POLICY "public_read_convocatorias"   ON convocatorias            FOR SELECT USING (TRUE);
CREATE POLICY "public_read_matching_rules"  ON convocatorias_matching_rules FOR SELECT USING (TRUE);
CREATE POLICY "public_read_matching"        ON convocatorias_matching_institucional FOR SELECT USING (TRUE);
CREATE POLICY "public_read_inis_monitor"    ON iaea_inis_monitor        FOR SELECT USING (TRUE);
CREATE POLICY "public_read_arxiv_monitor"   ON arxiv_monitor            FOR SELECT USING (TRUE);
CREATE POLICY "public_read_news_monitor"    ON news_monitor             FOR SELECT USING (TRUE);
CREATE POLICY "public_read_citation_graph"  ON citation_graph           FOR SELECT USING (TRUE);
CREATE POLICY "public_read_europmc"         ON europmc_works            FOR SELECT USING (TRUE);
CREATE POLICY "public_read_bertopic_topics" ON bertopic_topics          FOR SELECT USING (TRUE);
CREATE POLICY "public_read_bertopic_info"   ON bertopic_topic_info      FOR SELECT USING (TRUE);
CREATE POLICY "public_read_citing_papers"   ON citing_papers            FOR SELECT USING (TRUE);
CREATE POLICY "public_read_data_sources"    ON data_sources             FOR SELECT USING (TRUE);

-- Capital humano: solo lectura autenticada (datos personales)
DROP POLICY IF EXISTS "auth_read_capital_humano" ON capital_humano;
DROP POLICY IF EXISTS "auth_read_funding_plus" ON funding_complementario;
DROP POLICY IF EXISTS "auth_read_entity_personas" ON entity_registry_personas;
DROP POLICY IF EXISTS "auth_read_entity_links" ON entity_links;

CREATE POLICY "auth_read_capital_humano"    ON capital_humano           FOR SELECT USING (auth.role() = 'authenticated');
CREATE POLICY "auth_read_funding_plus"      ON funding_complementario   FOR SELECT USING (auth.role() = 'authenticated');
CREATE POLICY "auth_read_entity_personas"   ON entity_registry_personas FOR SELECT USING (auth.role() = 'authenticated');
CREATE POLICY "auth_read_entity_links"      ON entity_links             FOR SELECT USING (auth.role() = 'authenticated');

-- Escritura solo para service_role (scripts de migración)
-- (las políticas de escritura usan service_role key, que bypasea RLS)

-- ============================================================
-- TABLA: dian_publications
-- Registro interno DIAN CCHEN de publicaciones científicas
-- ============================================================

CREATE TABLE IF NOT EXISTS dian_publications (
    dian_id             SERIAL PRIMARY KEY,
    numero              INTEGER,
    unidad              TEXT,
    titulo              TEXT NOT NULL,
    autores             TEXT,
    revista             TEXT,
    fecha_envio         DATE,
    fecha_aceptacion    DATE,
    fecha_publicacion   DATE,
    doi                 TEXT,
    cuartil             TEXT CHECK (cuartil IN ('Q1','Q2','Q3','Q4') OR cuartil IS NULL),
    participacion_drtec TEXT,
    anio                INTEGER
);

CREATE INDEX IF NOT EXISTS idx_dian_unidad  ON dian_publications(unidad);
CREATE INDEX IF NOT EXISTS idx_dian_anio    ON dian_publications(anio);
CREATE INDEX IF NOT EXISTS idx_dian_cuartil ON dian_publications(cuartil);

COMMENT ON TABLE dian_publications IS
    'Registro interno DIAN CCHEN de publicaciones científicas. '
    'Fuente: Publicaciones DIAN.xlsx (hoja Consolidado). 133 registros (2022–2025).';

-- RLS: lectura pública (datos bibliográficos, no sensibles)
ALTER TABLE dian_publications ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "public_read_dian" ON dian_publications;
CREATE POLICY "public_read_dian" ON dian_publications FOR SELECT USING (TRUE);
