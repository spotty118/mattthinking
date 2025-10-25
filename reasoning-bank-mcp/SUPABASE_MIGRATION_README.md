# Supabase Migration Utilities

This directory contains utilities for migrating ReasoningBank data from ChromaDB (local vector database) to Supabase (cloud PostgreSQL with pgvector).

## Files

### Core Migration Files

1. **`supabase_storage.py`** - SupabaseAdapter implementation
   - Implements `StorageBackendInterface` for compatibility
   - Provides semantic search using pgvector
   - Supports workspace isolation
   - Handles embedding generation and storage

2. **`migrate_to_supabase.py`** - Migration script
   - Reads data from ChromaDB
   - Uploads to Supabase
   - Validates migration success
   - Supports dry-run mode

3. **`supabase_schema.sql`** - Database schema
   - Creates tables with pgvector support
   - Defines similarity search functions
   - Sets up indexes for performance
   - Configures Row Level Security

4. **`MIGRATION_GUIDE.md`** - Comprehensive migration guide
   - Step-by-step instructions
   - Troubleshooting tips
   - Rollback procedures
   - Performance optimization

## Quick Start

### 1. Set Up Supabase

```bash
# Create Supabase project at https://supabase.com
# Run the schema in SQL Editor
cat supabase_schema.sql | pbcopy  # Copy to clipboard
# Paste in Supabase Dashboard → SQL Editor → Run
```

### 2. Configure Environment

```bash
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_KEY="your-service-role-key"
```

### 3. Test Migration (Dry Run)

```bash
python migrate_to_supabase.py --dry-run
```

### 4. Run Migration

```bash
python migrate_to_supabase.py
```

### 5. Update Configuration

```bash
# In .env file
STORAGE_BACKEND=supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-service-role-key
```

## Architecture

### Storage Backend Interface

Both ChromaDB and Supabase implement the same interface:

```python
class StorageBackendInterface(ABC):
    @abstractmethod
    def add_trace(trace_id, task, trajectory, outcome, memory_items, metadata, workspace_id):
        """Store reasoning trace with memory items"""
        
    @abstractmethod
    def query_similar_memories(query_text, n_results, include_errors, domain_filter, workspace_id):
        """Semantic search for memories"""
        
    @abstractmethod
    def get_statistics(workspace_id):
        """Get storage statistics"""
```

### Supabase Schema

```
reasoning_traces
├── id (UUID, PK)
├── task (TEXT)
├── task_embedding (vector(384))
├── trajectory (JSONB)
├── outcome (TEXT)
├── metadata (JSONB)
├── workspace_id (TEXT)
└── timestamps

memory_items
├── id (UUID, PK)
├── trace_id (UUID, FK)
├── title (TEXT)
├── description (TEXT)
├── content (TEXT)
├── content_embedding (vector(384))
├── error_context (JSONB)
├── pattern_tags (TEXT[])
├── domain_category (TEXT)
├── workspace_id (TEXT)
└── timestamps
```

### Vector Search

Supabase uses pgvector for semantic similarity:

```sql
-- Cosine similarity search
SELECT * FROM memory_items
ORDER BY content_embedding <=> query_embedding
LIMIT 10;
```

Indexes:
- HNSW index for fast approximate nearest neighbor search
- B-tree indexes for filtering (workspace, domain, etc.)

## Usage Examples

### Initialize Supabase Adapter

```python
from storage_adapter import create_storage_backend

# Create Supabase backend
backend = create_storage_backend(
    backend_type="supabase",
    supabase_url="https://your-project.supabase.co",
    supabase_key="your-key"
)
```

### Store Trace

```python
import uuid

trace_id = str(uuid.uuid4())
backend.add_trace(
    trace_id=trace_id,
    task="Implement binary search",
    trajectory=[{"iteration": 1, "action": "generate", "output": "..."}],
    outcome="success",
    memory_items=[
        {
            "id": str(uuid.uuid4()),
            "title": "Binary Search Pattern",
            "description": "Divide and conquer approach",
            "content": "Binary search works by...",
            "pattern_tags": ["algorithms", "binary_search"],
            "domain_category": "algorithms"
        }
    ],
    workspace_id="project-123"
)
```

### Query Memories

```python
memories = backend.query_similar_memories(
    query_text="How to search in sorted arrays?",
    n_results=5,
    include_errors=True,
    domain_filter="algorithms",
    workspace_id="project-123"
)

for memory in memories:
    print(f"{memory.title}: {memory.description}")
```

### Get Statistics

```python
stats = backend.get_statistics(workspace_id="project-123")
print(f"Total traces: {stats['total_traces']}")
print(f"Success rate: {stats['success_rate']}%")
```

## Migration Script Usage

### Basic Migration

```bash
python migrate_to_supabase.py
```

### Custom Paths

```bash
python migrate_to_supabase.py \
  --chromadb-dir /path/to/chroma_data \
  --traces-file /path/to/traces.json
```

### With Credentials

```bash
python migrate_to_supabase.py \
  --supabase-url https://your-project.supabase.co \
  --supabase-key your-key
```

### Dry Run

```bash
python migrate_to_supabase.py --dry-run
```

## Workspace Isolation

Both ChromaDB and Supabase support workspace isolation:

```python
from workspace_manager import WorkspaceManager

# Set workspace
manager = WorkspaceManager()
manager.set_workspace("/path/to/project")

# Queries are automatically filtered
backend = create_storage_backend("supabase")
memories = backend.query_similar_memories(
    "query",
    workspace_id=manager.get_workspace_id()
)
```

## Performance Considerations

### Embedding Generation

- Uses sentence-transformers (all-MiniLM-L6-v2)
- 384-dimensional vectors
- Batch processing for efficiency

### Vector Search

- HNSW index for fast approximate search
- Cosine similarity metric
- Typical query time: <100ms for 10k memories

### Scaling

- Supabase Free Tier: 500MB database
- Supabase Pro: 8GB+ database
- Horizontal scaling via read replicas

## Troubleshooting

### Connection Issues

```python
# Test connection
from supabase import create_client

client = create_client(
    "https://your-project.supabase.co",
    "your-key"
)

# Test query
result = client.table("reasoning_traces").select("*").limit(1).execute()
print(f"Connection successful: {len(result.data)} rows")
```

### Schema Issues

```sql
-- Check if pgvector is enabled
SELECT * FROM pg_extension WHERE extname = 'vector';

-- Check tables exist
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public';

-- Check indexes
SELECT * FROM pg_indexes 
WHERE tablename IN ('reasoning_traces', 'memory_items');
```

### Migration Errors

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
python migrate_to_supabase.py

# Check migration logs
tail -f migration.log
```

## Rollback

If migration fails or you need to rollback:

```bash
# 1. Update .env
STORAGE_BACKEND=chromadb

# 2. Restore backup
tar -xzf chroma_backup_YYYYMMDD.tar.gz

# 3. Restart services
docker-compose restart
```

## Testing

### Unit Tests

```bash
# Test Supabase adapter
python -m pytest test_supabase_storage.py

# Test migration
python -m pytest test_migration.py
```

### Integration Tests

```bash
# End-to-end migration test
python test_migration_integration.py
```

## Security

### API Keys

- Use service_role key for migration (full access)
- Use anon key for client applications (RLS enforced)
- Rotate keys regularly
- Never commit keys to version control

### Row Level Security

```sql
-- Enable RLS
ALTER TABLE reasoning_traces ENABLE ROW LEVEL SECURITY;
ALTER TABLE memory_items ENABLE ROW LEVEL SECURITY;

-- Create policies
CREATE POLICY "Users can only see their own data"
ON reasoning_traces
FOR SELECT
USING (auth.uid() = user_id);
```

## Monitoring

### Supabase Dashboard

- Database size and growth
- Query performance
- API usage
- Error rates

### Custom Monitoring

```python
# Track migration progress
stats = backend.get_statistics()
print(f"Migration progress: {stats['total_traces']} traces migrated")

# Monitor query performance
import time
start = time.time()
memories = backend.query_similar_memories("test")
print(f"Query time: {time.time() - start:.3f}s")
```

## Cost Optimization

1. **Use appropriate indexes**: HNSW for vectors, B-tree for filters
2. **Implement caching**: Cache frequently accessed memories
3. **Archive old data**: Move inactive traces to cold storage
4. **Optimize queries**: Use filters to reduce result set
5. **Monitor usage**: Track database size and API calls

## Support

For issues or questions:

1. Check [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md)
2. Review Supabase logs in dashboard
3. Check ReasoningBank documentation
4. Open an issue on GitHub

## Additional Resources

- [Supabase Documentation](https://supabase.com/docs)
- [pgvector Documentation](https://github.com/pgvector/pgvector)
- [ReasoningBank Design](design.md)
- [Storage Adapter Interface](storage_adapter.py)
