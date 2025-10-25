# Supabase Setup Guide for ReasoningBank

This guide will help you migrate from ChromaDB (local file storage) to Supabase (cloud database) for your ReasoningBank MCP server.

## Why Migrate to Supabase?

**Benefits:**
- ☁️ **Cloud-based**: No local storage required, access from anywhere
- 📈 **Scalable**: PostgreSQL scales better than local file storage
- 🔐 **Secure**: Built-in authentication and Row Level Security (RLS)
- 🔍 **Powerful queries**: Full SQL support with pgvector for semantic search
- 🌐 **Multi-instance**: Share memory bank across multiple deployments
- 💾 **Automatic backups**: Point-in-time recovery included
- 🚀 **Fast**: Optimized vector search with HNSW indexes

## Prerequisites

1. A Supabase account (free tier available at [supabase.com](https://supabase.com))
2. Python 3.8+ with pip
3. Existing ReasoningBank installation

## Step 1: Create Supabase Project

1. **Sign up/Login** to [Supabase](https://supabase.com)
2. **Create a new project**:
   - Click "New Project"
   - Choose organization
   - Enter project name (e.g., "reasoning-bank")
   - Choose database password (save this!)
   - Select region (choose closest to your location)
   - Click "Create new project"
3. **Wait for setup** (~2 minutes)

## Step 2: Get Your Credentials

Once your project is ready:

1. Go to **Settings** → **API**
2. Copy these values:
   - **Project URL** (looks like `https://xxxxx.supabase.co`)
   - **anon/public key** (starts with `eyJ...`)

## Step 3: Set Up Database Schema

### Option A: Using Supabase Dashboard (Recommended)

1. In your Supabase project, go to **SQL Editor**
2. Click **New query**
3. Copy the contents of `supabase_schema.sql` from this repository
4. Paste into the SQL editor
5. Click **Run** (or press Ctrl+Enter)
6. Wait for confirmation message

### Option B: Using Command Line

```bash
# Install Supabase CLI
npm install -g supabase

# Login
supabase login

# Link to your project
supabase link --project-ref your-project-ref

# Run migration
supabase db push --schema supabase_schema.sql
```

### Verify Schema Setup

After running the schema, verify it was created successfully:

```sql
-- Run this in SQL Editor to check tables exist
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN ('reasoning_traces', 'memory_items');

-- Check pgvector extension
SELECT * FROM pg_extension WHERE extname = 'vector';
```

You should see both tables listed and the vector extension enabled.

## Step 4: Configure Environment Variables

Create or update your `.env` file:

```bash
# Storage Backend Selection
STORAGE_BACKEND=supabase

# Supabase Configuration
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=eyJhbGc...your-key-here

# Optional: Custom table names (use defaults if not specified)
SUPABASE_TRACES_TABLE=reasoning_traces
SUPABASE_MEMORIES_TABLE=memory_items

# OpenRouter API (still required for LLM calls)
OPENROUTER_API_KEY=your-openrouter-key

# Other settings remain the same...
REASONING_MODEL=google/gemini-2.5-pro
REASONING_EFFORT=medium
```

## Step 5: Install Dependencies

Update your Python environment:

```bash
# Install/update dependencies
pip install -r requirements.txt

# This installs supabase>=2.0.0 among other dependencies
```

## Step 6: Migrate Existing Data (Optional)

If you have existing traces in ChromaDB, migrate them:

### Dry Run (Verify Data)

```bash
python migrate_to_supabase.py \
  --chromadb-dir ./chroma_data \
  --dry-run
```

### Actual Migration

```bash
python migrate_to_supabase.py \
  --chromadb-dir ./chroma_data \
  --supabase-url "https://xxxxx.supabase.co" \
  --supabase-key "eyJhbGc..."
```

Or using environment variables:

```bash
export SUPABASE_URL="https://xxxxx.supabase.co"
export SUPABASE_KEY="eyJhbGc..."
python migrate_to_supabase.py
```

**Migration Options:**
- `--chromadb-dir`: ChromaDB data directory (default: ./chroma_data)
- `--traces-file`: Specific traces.json file
- `--supabase-url`: Supabase project URL
- `--supabase-key`: Supabase API key
- `--dry-run`: Validate without uploading

## Step 7: Test the Connection

Create a test script `test_supabase.py`:

```python
from supabase_storage import SupabaseStorage
import uuid

# Initialize storage
storage = SupabaseStorage()

# Test adding a trace
trace_id = str(uuid.uuid4())
memory_item = {
    "id": str(uuid.uuid4()),
    "title": "Test Memory",
    "description": "Testing Supabase connection",
    "content": "This is a test memory to verify Supabase setup",
    "pattern_tags": ["test"]
}

storage.add_trace(
    trace_id=trace_id,
    task="Test task for Supabase",
    trajectory=[{"iteration": 1, "thought": "Testing", "action": "test", "output": "ok"}],
    outcome="success",
    memory_items=[memory_item],
    metadata={"test": True}
)

print("✓ Successfully added test trace to Supabase!")

# Test retrieval
stats = storage.get_statistics()
print(f"Total traces in Supabase: {stats['total_traces']}")
print(f"Total memories in Supabase: {stats['total_memories']}")
```

Run the test:

```bash
python test_supabase.py
```

## Step 8: Start Using Supabase

Now you can use your ReasoningBank MCP server with Supabase:

```bash
# Start the server
python reasoning_bank_server.py
```

The server will automatically use Supabase if `STORAGE_BACKEND=supabase` is set.

## Monitoring and Management

### View Your Data in Supabase

1. Go to **Table Editor** in Supabase dashboard
2. Select `reasoning_traces` or `memory_items`
3. Browse, filter, and query your data

### Check Statistics

```sql
-- Get overall statistics
SELECT * FROM get_reasoning_bank_stats();

-- View recent traces
SELECT id, task, outcome, timestamp 
FROM reasoning_traces 
ORDER BY timestamp DESC 
LIMIT 10;

-- Search memories by domain
SELECT title, domain_category, difficulty_level
FROM memory_items
WHERE domain_category = 'algorithms';
```

### Semantic Search Examples

```sql
-- Find similar traces (requires embedding vector)
-- This is handled by the SupabaseStorage class automatically
SELECT * FROM search_similar_traces(
    query_embedding := '[0.1, 0.2, ...]'::vector(384),
    match_count := 5
);
```

## Backup and Recovery

### Automatic Backups

Supabase provides automatic backups:
- **Free tier**: Daily backups, 7-day retention
- **Pro tier**: Point-in-time recovery

### Manual Backup

```bash
# Using Supabase CLI
supabase db dump -f backup.sql

# Restore
supabase db reset
psql -h your-db-host -U postgres -d postgres < backup.sql
```

## Performance Optimization

### Enable Realtime (Optional)

If you want real-time updates:

1. Go to **Database** → **Replication**
2. Enable replication for `reasoning_traces` and `memory_items`
3. Subscribe to changes in your application

### Index Optimization

The schema includes optimized indexes:
- **HNSW indexes** for vector similarity (faster than IVFFlat)
- **B-tree indexes** for common queries
- **GIN indexes** for array operations (pattern_tags)

Monitor index usage:

```sql
SELECT 
    schemaname, tablename, indexname, idx_scan 
FROM pg_stat_user_indexes 
WHERE schemaname = 'public'
ORDER BY idx_scan DESC;
```

## Troubleshooting

### Connection Issues

**Error: "Failed to connect to Supabase"**

1. Verify your URL and key are correct
2. Check if your IP is allowed (Supabase dashboard → Settings → Database → Connection pooling)
3. Ensure you're using the `anon` key, not the `service_role` key (unless intentional)

### Schema Issues

**Error: "Table does not exist"**

Run the schema setup again (Step 3)

### Migration Issues

**Error: "Vector dimension mismatch"**

The embedding model must produce 384-dimensional vectors (MiniLM-L6-v2). If you changed the model, update the schema:

```sql
-- Update vector dimensions (e.g., for 768-dim model)
ALTER TABLE reasoning_traces 
ALTER COLUMN task_embedding TYPE vector(768);

ALTER TABLE memory_items 
ALTER COLUMN content_embedding TYPE vector(768);
```

### Performance Issues

**Slow vector searches**

1. Ensure HNSW indexes are created (check schema)
2. Increase `m` and `ef_construction` parameters for HNSW:

```sql
DROP INDEX IF EXISTS idx_traces_embedding;
CREATE INDEX idx_traces_embedding ON reasoning_traces 
USING hnsw (task_embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

## Cost Considerations

### Free Tier Limits

- 500 MB database space
- 2 GB bandwidth per month
- 50,000 monthly active users
- Daily backups (7-day retention)

**Estimate**: The free tier can store ~50,000-100,000 memory items depending on content size.

### Upgrading

If you exceed free tier:
- **Pro tier**: $25/month (8 GB database, 250 GB bandwidth)
- **Pay-as-you-go**: Scale beyond Pro tier limits

## Switching Back to ChromaDB

If you need to switch back:

1. Update `.env`:
   ```bash
   STORAGE_BACKEND=chromadb
   ```

2. Export data from Supabase (if needed):
   ```bash
   # Create export script or use SQL dump
   supabase db dump -f supabase_backup.sql
   ```

3. Restart the server

## Advanced: Row Level Security (RLS)

For multi-user setups, configure RLS policies:

```sql
-- Example: Only allow users to see their own traces
ALTER TABLE reasoning_traces ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own traces"
    ON reasoning_traces FOR SELECT
    USING (auth.uid() = user_id);

-- Add user_id column first
ALTER TABLE reasoning_traces ADD COLUMN user_id UUID REFERENCES auth.users(id);
```

## Support

- **Supabase Docs**: https://supabase.com/docs
- **pgvector Docs**: https://github.com/pgvector/pgvector
- **ReasoningBank Issues**: Open an issue in this repository

## Summary Checklist

- [ ] Created Supabase project
- [ ] Copied Project URL and API key
- [ ] Ran database schema setup
- [ ] Updated `.env` with Supabase credentials
- [ ] Installed dependencies (`pip install -r requirements.txt`)
- [ ] Migrated existing data (if applicable)
- [ ] Tested connection
- [ ] Started server with `STORAGE_BACKEND=supabase`
- [ ] Verified data is being stored in Supabase

**Congratulations!** Your ReasoningBank is now running on Supabase cloud storage. 🎉
