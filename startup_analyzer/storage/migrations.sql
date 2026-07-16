-- Startup Analyzer schema for Supabase Postgres

CREATE TABLE IF NOT EXISTS analysis_runs (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(64) NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ,
    max_depth INT NOT NULL DEFAULT 4,
    status VARCHAR(32) NOT NULL DEFAULT 'running',
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS search_queries (
    id SERIAL PRIMARY KEY,
    run_id INT NOT NULL REFERENCES analysis_runs(id) ON DELETE CASCADE,
    session_id VARCHAR(64) NOT NULL,
    query TEXT NOT NULL,
    source VARCHAR(32) NOT NULL,
    depth INT NOT NULL DEFAULT 0,
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    rationale TEXT DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (run_id, source, query, depth)
);

CREATE TABLE IF NOT EXISTS raw_documents (
    id SERIAL PRIMARY KEY,
    run_id INT NOT NULL REFERENCES analysis_runs(id) ON DELETE CASCADE,
    session_id VARCHAR(64) NOT NULL,
    source VARCHAR(32) NOT NULL,
    external_id VARCHAR(512) NOT NULL,
    query TEXT DEFAULT '',
    depth INT NOT NULL DEFAULT 0,
    title TEXT DEFAULT '',
    content TEXT DEFAULT '',
    url TEXT DEFAULT '',
    metadata JSONB DEFAULT '{}'::jsonb,
    extracted BOOLEAN NOT NULL DEFAULT FALSE,
    collected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (session_id, source, external_id)
);

CREATE TABLE IF NOT EXISTS knowledge_entities (
    id SERIAL PRIMARY KEY,
    run_id INT NOT NULL REFERENCES analysis_runs(id) ON DELETE CASCADE,
    session_id VARCHAR(64) NOT NULL,
    entity_type VARCHAR(64) NOT NULL,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    confidence FLOAT NOT NULL DEFAULT 0.5,
    mention_count INT NOT NULL DEFAULT 1,
    platforms_seen JSONB DEFAULT '[]'::jsonb,
    evidence_doc_ids JSONB DEFAULT '[]'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb,
    UNIQUE (run_id, entity_type, name)
);

CREATE TABLE IF NOT EXISTS knowledge_relations (
    id SERIAL PRIMARY KEY,
    run_id INT NOT NULL REFERENCES analysis_runs(id) ON DELETE CASCADE,
    session_id VARCHAR(64) NOT NULL,
    source_entity_id INT REFERENCES knowledge_entities(id) ON DELETE CASCADE,
    target_entity_id INT REFERENCES knowledge_entities(id) ON DELETE CASCADE,
    relation_type VARCHAR(64) NOT NULL,
    confidence FLOAT NOT NULL DEFAULT 0.5,
    evidence_doc_ids JSONB DEFAULT '[]'::jsonb,
    UNIQUE (run_id, source_entity_id, target_entity_id, relation_type)
);

CREATE INDEX IF NOT EXISTS idx_raw_documents_run ON raw_documents(run_id);
CREATE INDEX IF NOT EXISTS idx_raw_documents_unextracted ON raw_documents(run_id, extracted) WHERE extracted = FALSE;
CREATE INDEX IF NOT EXISTS idx_search_queries_pending ON search_queries(run_id, status) WHERE status = 'pending';
CREATE INDEX IF NOT EXISTS idx_knowledge_entities_run ON knowledge_entities(run_id);
