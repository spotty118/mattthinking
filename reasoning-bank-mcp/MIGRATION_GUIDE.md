# ReasoningBank Migration Guide: ChromaDB to Supabase

This guide provides step-by-step instructions for migrating your ReasoningBank data from ChromaDB (local storage) to Supabase (cloud storage).

## Overview

The migration process transfers:
- All reasoning traces with task embeddings
- All memory items with content embeddings
- Genealogy relationships (parent-child memory links)
- Workspace isolation metadata
- Error context and pattern tags

## Prerequisites

### 1. Supabase Account Setup

1. Create a Supabase account at https://supabase.com
2. Create a new project
3. Note your project URL and API key (service_role key for full access)

### 2. Install Dependencies

```bash
pip install supabase>=2.0.0
```

### 3. Set Up Supabase Schema

Run the SQL schema file in your Supabase SQL editor:

```bash
# Copy the contents of supabase_schema.sql
cat reasoning-bank-mcp/supabase_schema.sql
```

Then paste and execute in Supabase Dashboard → SQL Editor

This creates:
- `reasoning_traces` table with pgvector support
- `memory_items` table with pgvector support
- Vector similarity search functions
- Indexes for performance
- Row Level Security policies

## Migration Process

### Step 1: Backup Your Data

Before migrating, create a backup of your ChromaDB data:

```bash
# Backup ChromaDB data
tar -czf chroma_backup_$(date +%Y%m%d).tar.gz chroma_data/

# Backup traces (if stored separately)
tar -czf traces_backup_$(date +%Y%m%d).tar.gz traces/
```

### Step 2: Set Environment Variables

```bash
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_KEY="your-service-role-key"
```

### Step 3: Dry Run (Recommended)

Test the migration without uploading data:

```bash
python migrate_to_supabase.py --dry-run
```

This validates:
- ChromaDB data can be read
- Trace structure is correct
- Memory items are valid

### Step 4: Run Migration

Execute the full migration:

```bash
python migrate_to_supabase.py
```

Options:
- `--chromadb-dir PATH`: ChromaDB data directory (default: ./chroma_data)
- `--traces-file PATH`: Path to traces.json file
- `--supabase-url URL`: Supabase project URL
- `--supabase-key KEY`: Supabase API key
- `--dry-run`: Validate without uploading

### Step 5: Verify Migration

Check the migration results:

```python
from supabase_storage import SupabaseAdapter

# Initialize adapter
adapter = SupabaseAdapter()

# Get statistics
stats = adapter.get_statistics()
print(f"Total traces: {stats['total_traces']}")
print(f"Total memories: {stats['total_memories']}")
print(f"Success rate: {stats['success_rate']}%")
```

### Step 6: Update Configuration

Update your `.env` file to use Supabase:

```bash
# Change storage backend
STORAGE_BACKEND=supabase

# Add Supabase credentials
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-service-role-key

# Optional: Keep ChromaDB settings for rollback
# STORAGE_BACKEND=chromadb
# REASONING_BANK_DATA=./chroma_data
```

### Step 7: Test the System

Test that the system works with Supabase:

```bash
# Run a test query
python -c "
from storage_adapter import create_storage_backend
backend = create_storage_backend('supabase')
memories = backend.query_similar_memories('test query', n_results=5)
print(f'Found {len(memories)} memories')
"
```

## Rollback Procedure

If you need to rollback to ChromaDB:

### 1. Restore Configuration

```bash
# Update .env
STORAGE_BACKEND=chromadb
REASONING_BANK_DATA=./chroma_data
```

### 2. Restore Backup (if needed)

```bash
# Restore ChromaDB data
tar -xzf chroma_backup_YYYYMMDD.tar.gz

# Restore traces
tar -xzf traces_backup_YYYYMMDD.tar.gz
```

### 3. Restart Services

```bash
# If using Docker
docker-compose down
docker-compose up -d

# If running locally
# Restart your application
```

## Troubleshooting

### Migration Fails with "Connection Error"

**Problem**: Cannot connect to Supabase

**Solutions**:
1. Verify SUPABASE_URL and SUPABASE_KEY are correct
2. Check network connectivity
3. Ensure service_role key is used (not anon key)
4. Check Supabase project status

### Migration Fails with "Schema Not Found"

**Problem**: Required tables don't exist

**Solution**:
1. Run `supabase_schema.sql` in Supabase SQL Editor
2. Verify pgvector extension is enabled
3. Check table creation succeeded

### "Embedding Dimension Mismatch"

**Problem**: Vector dimensions don't match

**Solution**:
1. Ensure using same embedding model (all-MiniLM-L6-v2 = 384 dims)
2. Update schema if using different model
3. Regenerate embeddings if needed

### Slow Migration Performance

**Problem**: Migration takes too long

**Solutions**:
1. Migrate in batches (modify script to process N traces at a time)
2. Disable indexes temporarily during migration
3. Use Supabase connection pooling
4. Increase batch size in migration script

### Memory Items Missing After Migration

**Problem**: Some memories not migrated

**Solutions**:
1. Check migration logs for errors
2. Verify memory items have required fields (id, title, description, content)
3. Re-run migration for failed traces
4. Check Supabase storage limits

## Performance Optimization

### After Migration

1. **Analyze Tables**:
```sql
ANALYZE reasoning_traces;
ANALYZE memory_items;
```

2. **Verify Indexes**:
```sql
SELECT * FROM pg_indexes 
WHERE tablename IN ('reasoning_traces', 'memory_items');
```

3. **Check Vector Index Performance**:
```sql
EXPLAIN ANALYZE
SELECT * FROM memory_items
ORDER BY content_embedding <=> '[0.1, 0.2, ...]'::vector
LIMIT 10;
```

## Workspace Isolation

The migration preserves workspace isolation:

- Each trace and memory includes `workspace_id`
- Queries automatically filter by workspace
- Use WorkspaceManager for multi-tenant setups

Example:
```python
from workspace_manager import WorkspaceManager
from storage_adapter import create_storage_backend

# Set workspace
manager = WorkspaceManager()
manager.set_workspace("/path/to/project")

# Queries will be filtered by workspace
backend = create_storage_backend('supabase')
memories = backend.query_similar_memories(
    "query",
    workspace_id=manager.get_workspace_id()
)
```

## Cost Considerations

### Supabase Pricing

- **Free Tier**: 500MB database, 1GB file storage, 2GB bandwidth
- **Pro Tier**: $25/month for 8GB database, 100GB storage
- **Pay-as-you-go**: Additional storage and bandwidth

### Cost Optimization

1. **Use appropriate indexes**: HNSW for vectors, B-tree for filters
2. **Implement caching**: Use CachedLLMClient to reduce API calls
3. **Archive old traces**: Move inactive data to cold storage
4. **Monitor usage**: Track database size and query performance

## Support

For issues or questions:

1. Check logs: `docker-compose logs -f reasoning-bank`
2. Review Supabase dashboard for errors
3. Consult ReasoningBank documentation
4. Open an issue on GitHub

## Next Steps

After successful migration:

1. ✅ Monitor system performance
2. ✅ Set up automated backups
3. ✅ Configure Row Level Security (RLS) policies
4. ✅ Implement data retention policies
5. ✅ Optimize query performance
6. ✅ Set up monitoring and alerts

## Additional Resources

- [Supabase Documentation](https://supabase.com/docs)
- [pgvector Documentation](https://github.com/pgvector/pgvector)
- [ReasoningBank Design Document](design.md)
- [Storage Adapter Interface](storage_adapter.py)
