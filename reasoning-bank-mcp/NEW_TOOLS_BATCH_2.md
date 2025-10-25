# NEW MCP TOOLS - BATCH 2

This document describes the 5 additional MCP tools built to expose previously missing functionality.

**Total tools now: 13 MCP tools**

---

## Tool 9: `cleanup_old_data` - Data Retention Management

**Purpose**: Delete old traces/memories and manage workspace deletion with safety controls.

**Exposes functionality from**:
- `storage_adapter.py`: `delete_old_traces()`, `delete_workspace()`
- `workspace_manager.py`: `delete_workspace()` with safety confirmation

**Key features**:
- Delete traces older than specified retention period
- Free storage space automatically
- Delete entire workspaces (requires explicit confirmation)
- Workspace-specific or global cleanup
- Estimated freed space calculation

**Parameters**:
```python
retention_days: int          # Number of days to retain data (older deleted)
workspace_id: Optional[str]  # Filter by workspace (None = all workspaces)
delete_workspace: bool       # If True, delete entire workspace
confirm_workspace_delete: bool  # Safety confirmation for workspace deletion
```

**Returns**:
```python
{
    "operation": "delete_old_traces" | "delete_workspace",
    "deleted_traces_count": int,
    "deleted_memories_count": int,
    "freed_space_mb": float,           # If delete_old_traces
    "retention_cutoff": str,           # ISO timestamp
    "workspace_id": str,               # If workspace-specific
    "deletion_timestamp": str          # If delete_workspace
}
```

**Usage examples**:
```python
# Delete data older than 90 days
result = cleanup_old_data(retention_days=90)

# Delete old data from specific workspace
result = cleanup_old_data(retention_days=60, workspace_id="abc123")

# Delete entire workspace (requires confirmation)
result = cleanup_old_data(
    retention_days=0,
    workspace_id="abc123",
    delete_workspace=True,
    confirm_workspace_delete=True
)
```

**Safety features**:
- Workspace deletion requires `confirm_workspace_delete=True`
- Warning messages if confirmation not provided
- Automatic workspace context clearing if current workspace deleted

---

## Tool 10: `get_performance_metrics` - Performance Monitoring

**Purpose**: Get comprehensive system performance metrics including API latencies, cache stats, and token usage.

**Exposes functionality from**:
- `performance_optimizer.py`: `PerformanceMonitor.get_statistics()`
- `storage_adapter.py`: `get_statistics()` for storage metrics

**Key features**:
- API call latency tracking (min/max/avg)
- Cache hit rates
- Token consumption statistics
- Embeddings generation counts
- System uptime tracking
- Storage backend statistics integration
- Optional metrics reset after reading

**Parameters**:
```python
reset_after_read: bool = False  # Reset metrics after reading
```

**Returns**:
```python
{
    "uptime_seconds": float,
    "api_calls": int,
    "avg_api_latency": float,      # Seconds
    "min_api_latency": float,
    "max_api_latency": float,
    "cache_hit_rate": float,       # Percentage
    "total_tokens_used": int,
    "embeddings_generated": int,
    "memories_cached": int,
    "storage_stats": {
        "total_traces": int,
        "total_memories": int,
        "success_rate": float,
        ...
    }
}
```

**Usage examples**:
```python
# Get current performance metrics
metrics = get_performance_metrics()
print(f"Cache hit rate: {metrics['cache_hit_rate']}%")
print(f"Avg API latency: {metrics['avg_api_latency']}s")

# Get metrics and reset counters
metrics = get_performance_metrics(reset_after_read=True)
```

**Auto-initialization**:
- Performance monitor created automatically if not exists
- Integrates with existing storage statistics

---

## Tool 11: `manage_cache` - Cache Management

**Purpose**: Manage the in-memory cache for frequently accessed memories.

**Exposes functionality from**:
- `performance_optimizer.py`: `MemoryCache` methods
- `storage_adapter.py`: `memory_cache` attribute

**Key features**:
- Get detailed cache statistics
- Clear entire cache
- Invalidate specific memory from cache
- LRU eviction tracking
- Cache hit/miss statistics

**Parameters**:
```python
action: str                  # "statistics" | "clear" | "invalidate"
memory_id: Optional[str]     # Required for "invalidate" action
```

**Returns**:

For `action="statistics"`:
```python
{
    "cache_size": int,          # Current items in cache
    "max_size": int,            # Maximum cache capacity
    "hits": int,
    "misses": int,
    "hit_rate": float,          # Percentage
    "evictions": int,
    "total_requests": int
}
```

For `action="clear"` or `action="invalidate"`:
```python
{
    "success": True,
    "action": str,
    "memory_id": str,          # For invalidate only
    "message": str
}
```

**Usage examples**:
```python
# Get cache statistics
stats = manage_cache(action="statistics")
print(f"Hit rate: {stats['hit_rate']}%")
print(f"Cache size: {stats['cache_size']}/{stats['max_size']}")

# Clear entire cache
manage_cache(action="clear")

# Invalidate specific memory
manage_cache(action="invalidate", memory_id="mem_12345")
```

**Error handling**:
- Returns error if cache not enabled in storage backend
- Validates memory_id for invalidate action

---

## Tool 12: `migrate_database` - Database Migration

**Purpose**: Migrate data from ChromaDB to Supabase with validation and dry-run support.

**Exposes functionality from**:
- `migrate_to_supabase.py`: `MigrationManager.run_migration()`
- `validate_migration_setup.py`: Validation functions

**Key features**:
- Full ChromaDB to Supabase migration
- Dry-run validation without data transfer
- Migration statistics and verification
- Automatic trace validation
- Post-migration verification

**Parameters**:
```python
target_backend: str          # "supabase" (only supported backend)
supabase_url: Optional[str]  # Or set SUPABASE_URL env var
supabase_key: Optional[str]  # Or set SUPABASE_KEY env var
chromadb_dir: Optional[str]  # Default: "./chroma_data"
dry_run: bool = False        # Validate without migrating
```

**Returns**:
```python
{
    "total_traces": int,
    "successful": int,
    "failed": int,
    "skipped": int,
    "verification": {           # If not dry_run
        "total_traces": int,
        "total_memories": int
    }
}
```

**Usage examples**:
```python
# Dry-run validation
result = migrate_database(
    target_backend="supabase",
    dry_run=True
)

# Actual migration
result = migrate_database(
    target_backend="supabase",
    supabase_url="https://xxx.supabase.co",
    supabase_key="your-api-key",
    chromadb_dir="./chroma_data"
)
print(f"Migrated {result['successful']}/{result['total_traces']} traces")
```

**Prerequisites**:
- Supabase project setup
- `supabase_schema.sql` executed in Supabase
- `SUPABASE_URL` and `SUPABASE_KEY` environment variables set

**Best practices**:
- Always test with `dry_run=True` first
- Verify environment variables are set
- Check migration statistics for failures

---

## Tool 13: `compress_prompt` - Prompt Compression

**Purpose**: Compress prompts to reduce token consumption while preserving meaning.

**Exposes functionality from**:
- `performance_optimizer.py`: `PromptCompressor.compress()`

**Key features**:
- Remove redundant whitespace
- Compress code blocks (remove comments, empty lines)
- Intelligent truncation preserving structure
- Token count estimation (4 chars/token heuristic)
- Compression statistics

**Parameters**:
```python
prompt: str                  # Original prompt text
max_tokens: int = 12000      # Maximum tokens allowed
compression_ratio: float = 0.7  # Target compression ratio (0.0-1.0)
```

**Returns**:
```python
{
    "compressed_prompt": str,
    "original_tokens": int,
    "compressed_tokens": int,
    "reduction_percentage": float,
    "compression_applied": bool,
    "original_length": int,      # Character count
    "compressed_length": int
}
```

**Usage examples**:
```python
# Compress a long prompt
result = compress_prompt(
    prompt="Very long prompt with lots of whitespace and code...",
    max_tokens=8000
)
print(result['compressed_prompt'])
print(f"Reduced by {result['reduction_percentage']}%")

# Aggressive compression
result = compress_prompt(
    prompt=long_text,
    max_tokens=4000,
    compression_ratio=0.5
)
```

**Compression techniques**:
1. **Whitespace reduction**: Multiple spaces → single space, multiple newlines → double newline
2. **Code block compression**: Remove comments (# and //), remove empty lines
3. **Intelligent truncation**: Preserve first 60% and last 30% if needed

**Token estimation**:
- Uses 4 characters per token heuristic
- Approximate but fast estimation
- Good for real-time compression decisions

---

## Complete Tool Summary

**All 13 MCP Tools**:

1. `solve_coding_task` - Iterative reasoning with MaTTS parallel solutions
2. `retrieve_memories` - Semantic memory search with filtering
3. `get_memory_genealogy` - Memory evolution tracking
4. `get_statistics` - System statistics
5. `capture_knowledge` - Passive learning from conversations
6. `search_knowledge` - Advanced knowledge retrieval
7. `manage_workspace` - Workspace context management
8. `backup_memories` - Backup/restore/validate operations
9. `cleanup_old_data` - Data retention and workspace deletion (NEW)
10. `get_performance_metrics` - Performance monitoring (NEW)
11. `manage_cache` - Cache management (NEW)
12. `migrate_database` - Database migration (NEW)
13. `compress_prompt` - Prompt compression (NEW)

---

## Implementation Status

**All 13 tools compiled successfully** ✅

**Files modified**:
- `reasoning_bank_server.py` - Added tools 9-13 (lines 1101-1620)

**No syntax errors** - All Python files compile cleanly.

---

## Testing Recommendations

**Tool 9 - cleanup_old_data**:
```bash
# Test retention-based cleanup
curl -X POST http://localhost:8000/cleanup_old_data \
  -d '{"retention_days": 90}'

# Test workspace deletion (requires confirmation)
curl -X POST http://localhost:8000/cleanup_old_data \
  -d '{"workspace_id": "test123", "delete_workspace": true, "confirm_workspace_delete": true}'
```

**Tool 10 - get_performance_metrics**:
```bash
# Get current metrics
curl -X POST http://localhost:8000/get_performance_metrics

# Get metrics and reset
curl -X POST http://localhost:8000/get_performance_metrics \
  -d '{"reset_after_read": true}'
```

**Tool 11 - manage_cache**:
```bash
# Get cache statistics
curl -X POST http://localhost:8000/manage_cache \
  -d '{"action": "statistics"}'

# Clear cache
curl -X POST http://localhost:8000/manage_cache \
  -d '{"action": "clear"}'
```

**Tool 12 - migrate_database**:
```bash
# Dry-run validation
curl -X POST http://localhost:8000/migrate_database \
  -d '{"target_backend": "supabase", "dry_run": true}'

# Actual migration (set env vars first)
export SUPABASE_URL="https://xxx.supabase.co"
export SUPABASE_KEY="your-key"
curl -X POST http://localhost:8000/migrate_database \
  -d '{"target_backend": "supabase"}'
```

**Tool 13 - compress_prompt**:
```bash
# Compress a prompt
curl -X POST http://localhost:8000/compress_prompt \
  -d '{"prompt": "Long prompt text...", "max_tokens": 8000}'
```

---

## Cross-References

- See `COMPLETE_TOOL_LIST.md` for comprehensive documentation of all 13 tools
- See `FIXES_APPLIED.md` for critical bug fixes applied earlier
- See `NEW_MCP_TOOLS.md` for tools 5-6 documentation (previous batch)
