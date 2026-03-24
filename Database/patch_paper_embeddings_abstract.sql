ALTER TABLE paper_embeddings
    ADD COLUMN IF NOT EXISTS abstract TEXT;

CREATE OR REPLACE FUNCTION match_papers(
    query_embedding vector(384),
    match_count     int DEFAULT 5
)
RETURNS TABLE(
    openalex_id text,
    doi text,
    title text,
    year numeric,
    abstract text,
    similarity float
)
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