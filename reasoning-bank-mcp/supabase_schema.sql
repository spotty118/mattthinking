-- ReasoningBank Supabase Schema
-- This schema supports the migration from ChromaDB to Supabase with pgvector

-- Enable pgvector extension for vector similarity search
CREATE EXTENSION IF NOT EXISTS vector;

-- Create reasoning_traces table
CREATE TABLE IF NOT EXISTS reasoning_traces (
    id UUID PRIMARY KEY,
    task TEXT NOT NULL,
    task_embedding vector(384), -- MiniLM-L6-v2 produces 384-dim vectors
    trajectory JSONB NOT NULL,
    outcome TEXT NOT NULL CHECK (outcome IN ('success', 'failure', 'partial')),
    metadata JSONB DEFAULT '{}'::jsonb,
    parent_trace_id UUID REFERENCES reasoning_traces(id) ON DELETE SET NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    num_memories INTEGER DEFAULT 0,
    workspace_id TEXT, -- Workspace isolation support
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create memory_items table
CREATE TABLE IF NOT EXISTS memory_items (
    id UUID PRIMARY KEY,
    trace_id UUID NOT NULL REFERENCES reasoning_traces(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT,
    content TEXT NOT NULL,
    content_embedding vector(384), -- MiniLM-L6-v2 produces 384-dim vectors
    error_context JSONB,
    pattern_tags TEXT[] DEFAULT ARRAY[]::TEXT[],
    difficulty_level TEXT CHECK (difficulty_level IN ('simple', 'moderate', 'complex', 'expert')),
    domain_category TEXT,
    parent_memory_id UUID REFERENCES memory_items(id) ON DELETE SET NULL,
    evolution_stage INTEGER DEFAULT 0,
    workspace_id TEXT, -- Workspace isolation support
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_traces_outcome ON reasoning_traces(outcome);
CREATE INDEX IF NOT EXISTS idx_traces_timestamp ON reasoning_traces(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_traces_parent ON reasoning_traces(parent_trace_id) WHERE parent_trace_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_traces_workspace ON reasoning_traces(workspace_id) WHERE workspace_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_memories_trace ON memory_items(trace_id);
CREATE INDEX IF NOT EXISTS idx_memories_domain ON memory_items(domain_category) WHERE domain_category IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_memories_difficulty ON memory_items(difficulty_level) WHERE difficulty_level IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_memories_tags ON memory_items USING GIN(pattern_tags);
CREATE INDEX IF NOT EXISTS idx_memories_error ON memory_items((error_context IS NOT NULL)) WHERE error_context IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_memories_workspace ON memory_items(workspace_id) WHERE workspace_id IS NOT NULL;

-- Create vector similarity search indexes using HNSW (Hierarchical Navigable Small World)
-- HNSW is faster than IVFFlat for most use cases
CREATE INDEX IF NOT EXISTS idx_traces_embedding ON reasoning_traces 
USING hnsw (task_embedding vector_cosine_ops);

CREATE INDEX IF NOT EXISTS idx_memories_embedding ON memory_items 
USING hnsw (content_embedding vector_cosine_ops);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers for automatic timestamp updates
CREATE TRIGGER update_traces_updated_at 
    BEFORE UPDATE ON reasoning_traces
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_memories_updated_at 
    BEFORE UPDATE ON memory_items
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to check if pgvector extension is enabled
CREATE OR REPLACE FUNCTION check_pgvector_enabled()
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM pg_extension WHERE extname = 'vector'
    );
END;
$$ LANGUAGE plpgsql;

-- Function for semantic similarity search on traces
CREATE OR REPLACE FUNCTION search_similar_traces(
    query_embedding vector(384),
    match_count INTEGER DEFAULT 5,
    outcome_filter TEXT DEFAULT NULL,
    domain_filter TEXT DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    task TEXT,
    outcome TEXT,
    timestamp TIMESTAMPTZ,
    distance FLOAT,
    similarity FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        t.id,
        t.task,
        t.outcome,
        t.timestamp,
        (t.task_embedding <=> query_embedding) AS distance,
        1 - (t.task_embedding <=> query_embedding) AS similarity
    FROM reasoning_traces t
    WHERE
        (outcome_filter IS NULL OR t.outcome = outcome_filter)
        AND t.task_embedding IS NOT NULL
    ORDER BY t.task_embedding <=> query_embedding
    LIMIT match_count;
END;
$$ LANGUAGE plpgsql;

-- Function for semantic similarity search on memory items
CREATE OR REPLACE FUNCTION search_similar_memories(
    query_embedding vector(384),
    match_count INTEGER DEFAULT 5,
    domain_filter TEXT DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    trace_id UUID,
    title TEXT,
    description TEXT,
    content TEXT,
    error_context JSONB,
    pattern_tags TEXT[],
    difficulty_level TEXT,
    domain_category TEXT,
    distance FLOAT,
    similarity FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        m.id,
        m.trace_id,
        m.title,
        m.description,
        m.content,
        m.error_context,
        m.pattern_tags,
        m.difficulty_level,
        m.domain_category,
        (m.content_embedding <=> query_embedding) AS distance,
        1 - (m.content_embedding <=> query_embedding) AS similarity
    FROM memory_items m
    WHERE
        (domain_filter IS NULL OR m.domain_category = domain_filter)
        AND m.content_embedding IS NOT NULL
    ORDER BY m.content_embedding <=> query_embedding
    LIMIT match_count;
END;
$$ LANGUAGE plpgsql;

-- Function to get statistics
CREATE OR REPLACE FUNCTION get_reasoning_bank_stats()
RETURNS TABLE (
    total_traces BIGINT,
    success_traces BIGINT,
    failure_traces BIGINT,
    total_memories BIGINT,
    memories_with_errors BIGINT,
    success_rate FLOAT
) AS $$
DECLARE
    v_total_traces BIGINT;
    v_success_traces BIGINT;
    v_failure_traces BIGINT;
    v_total_memories BIGINT;
    v_memories_with_errors BIGINT;
    v_success_rate FLOAT;
BEGIN
    SELECT COUNT(*) INTO v_total_traces FROM reasoning_traces;
    SELECT COUNT(*) INTO v_success_traces FROM reasoning_traces WHERE outcome = 'success';
    SELECT COUNT(*) INTO v_failure_traces FROM reasoning_traces WHERE outcome = 'failure';
    SELECT COUNT(*) INTO v_total_memories FROM memory_items;
    SELECT COUNT(*) INTO v_memories_with_errors FROM memory_items WHERE error_context IS NOT NULL;
    
    IF v_total_traces > 0 THEN
        v_success_rate := (v_success_traces::FLOAT / v_total_traces::FLOAT) * 100;
    ELSE
        v_success_rate := 0.0;
    END IF;
    
    RETURN QUERY SELECT 
        v_total_traces,
        v_success_traces,
        v_failure_traces,
        v_total_memories,
        v_memories_with_errors,
        v_success_rate;
END;
$$ LANGUAGE plpgsql;

-- Row Level Security (RLS) Policies
-- Enable RLS on tables
ALTER TABLE reasoning_traces ENABLE ROW LEVEL SECURITY;
ALTER TABLE memory_items ENABLE ROW LEVEL SECURITY;

-- Create policies for authenticated users (adjust based on your auth setup)
CREATE POLICY "Allow all operations for authenticated users" 
    ON reasoning_traces 
    FOR ALL 
    TO authenticated 
    USING (true);

CREATE POLICY "Allow all operations for authenticated users" 
    ON memory_items 
    FOR ALL 
    TO authenticated 
    USING (true);

-- For service role (bypass RLS)
CREATE POLICY "Service role has full access to traces" 
    ON reasoning_traces 
    FOR ALL 
    TO service_role 
    USING (true);

CREATE POLICY "Service role has full access to memories" 
    ON memory_items 
    FOR ALL 
    TO service_role 
    USING (true);

-- Comments for documentation
COMMENT ON TABLE reasoning_traces IS 'Stores complete reasoning trajectories with task embeddings for semantic search';
COMMENT ON TABLE memory_items IS 'Stores extracted memory items with content embeddings, linked to parent traces';
COMMENT ON COLUMN reasoning_traces.task_embedding IS 'Vector embedding of task description for semantic similarity search';
COMMENT ON COLUMN memory_items.content_embedding IS 'Vector embedding of memory content for semantic similarity search';
COMMENT ON FUNCTION search_similar_traces IS 'Semantic similarity search for traces using cosine distance';
COMMENT ON FUNCTION search_similar_memories IS 'Semantic similarity search for memory items using cosine distance';


-- Updated function for semantic similarity search with workspace support
DROP FUNCTION IF EXISTS search_similar_memories(vector, INTEGER, TEXT);

CREATE OR REPLACE FUNCTION search_similar_memories(
    query_embedding vector(384),
    match_count INTEGER DEFAULT 5,
    domain_filter TEXT DEFAULT NULL,
    workspace_filter TEXT DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    trace_id UUID,
    title TEXT,
    description TEXT,
    content TEXT,
    error_context JSONB,
    pattern_tags TEXT[],
    difficulty_level TEXT,
    domain_category TEXT,
    parent_memory_id UUID,
    evolution_stage INTEGER,
    distance FLOAT,
    similarity FLOAT,
    trace_outcome TEXT,
    trace_timestamp TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        m.id,
        m.trace_id,
        m.title,
        m.description,
        m.content,
        m.error_context,
        m.pattern_tags,
        m.difficulty_level,
        m.domain_category,
        m.parent_memory_id,
        m.evolution_stage,
        (m.content_embedding <=> query_embedding) AS distance,
        1 - (m.content_embedding <=> query_embedding) AS similarity,
        t.outcome AS trace_outcome,
        t.timestamp AS trace_timestamp
    FROM memory_items m
    LEFT JOIN reasoning_traces t ON m.trace_id = t.id
    WHERE
        (domain_filter IS NULL OR m.domain_category = domain_filter)
        AND (workspace_filter IS NULL OR m.workspace_id = workspace_filter)
        AND m.content_embedding IS NOT NULL
    ORDER BY m.content_embedding <=> query_embedding
    LIMIT match_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION search_similar_memories IS 'Semantic similarity search for memory items with workspace isolation support';
