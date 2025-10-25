# ReasoningBank MCP Server - Quick Reference

Quick reference guide for using the ReasoningBank MCP Server tools and features.

## Table of Contents

- [MCP Tools](#mcp-tools)
- [Common Usage Patterns](#common-usage-patterns)
- [Configuration Examples](#configuration-examples)
- [Code Examples](#code-examples)
- [CLI Commands](#cli-commands)
- [Troubleshooting Quick Fixes](#troubleshooting-quick-fixes)

## MCP Tools

### solve_coding_task

Solve a coding task with memory-guided iterative reasoning.

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `task` | string | ✅ | - | The coding task description |
| `use_memory` | boolean | ❌ | `true` | Retrieve and use past memories |
| `enable_matts` | boolean | ❌ | `true` | Enable Memory-Aware Test-Time Scaling |
| `matts_k` | integer | ❌ | `5` | Number of parallel solutions (MaTTS) |
| `matts_mode` | string | ❌ | `"parallel"` | MaTTS mode: "parallel" or "sequential" |
| `store_result` | boolean | ❌ | `true` | Store result in memory bank |

**Example Request**:

```json
{
  "task": "Implement a binary search function in Python that handles duplicates",
  "use_memory": true,
  "enable_matts": true,
  "matts_k": 5,
  "matts_mode": "parallel",
  "store_result": true
}
```

**Example Response**:

```json
{
  "solution": "def binary_search(arr, target):\n    left, right = 0, len(arr) - 1\n    ...",
  "outcome": "success",
  "score": 0.92,
  "trajectory": [
    {
      "iteration": 1,
      "action": "think",
      "content": "Initial solution attempt...",
      "timestamp": "2025-10-23T10:30:00Z"
    },
    {
      "iteration": 1,
      "action": "evaluate",
      "score": 0.75,
      "feedback": "Good start, but needs edge case handling",
      "timestamp": "2025-10-23T10:30:15Z"
    },
    {
      "iteration": 2,
      "action": "refine",
      "content": "Improved solution with edge cases...",
      "timestamp": "2025-10-23T10:30:30Z"
    }
  ],
  "memories_used": [
    {
      "id": "uuid-123",
      "title": "Binary Search Implementation",
      "similarity_score": 0.89,
      "has_error_context": false
    }
  ],
  "metadata": {
    "total_iterations": 2,
    "total_tokens": 3500,
    "cache_hits": 2,
    "reasoning_tokens": 1200
  }
}
```

---

### retrieve_memories

Query past experiences semantically.

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `query` | string | ✅ | - | Search query text |
| `n_results` | integer | ❌ | `5` | Number of results to return |

**Example Request**:

```json
{
  "query": "binary search with edge cases",
  "n_results": 5
}
```

**Example Response**:

```json
{
  "memories": [
    {
      "id": "uuid-123",
      "title": "Binary Search with Duplicates",
      "description": "Implementation handling duplicate values",
      "content": "def binary_search_duplicates(arr, target):\n    ...",
      "similarity_score": 0.92,
      "recency_score": 0.85,
      "composite_score": 0.89,
      "error_context": null,
      "pattern_tags": ["binary-search", "edge-cases"],
      "domain_category": "algorithms",
      "trace_outcome": "success",
      "trace_timestamp": "2025-10-22T15:30:00Z"
    },
    {
      "id": "uuid-456",
      "title": "Binary Search Edge Case Bug",
      "description": "Common off-by-one error in binary search",
      "content": "Watch out for: while left <= right vs left < right",
      "similarity_score": 0.87,
      "recency_score": 0.90,
      "composite_score": 0.88,
      "error_context": {
        "error_type": "IndexError",
        "failure_pattern": "Off-by-one error in loop condition",
        "corrective_guidance": "Use left <= right for inclusive bounds"
      },
      "pattern_tags": ["binary-search", "off-by-one"],
      "domain_category": "algorithms",
      "trace_outcome": "failure",
      "trace_timestamp": "2025-10-21T10:15:00Z"
    }
  ],
  "total_results": 2,
  "query_time_ms": 45
}
```

---

### get_memory_genealogy

Trace the evolution tree of a memory.

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `memory_id` | string | ✅ | - | UUID of the memory |

**Example Request**:

```json
{
  "memory_id": "uuid-789"
}
```

**Example Response**:

```json
{
  "memory_id": "uuid-789",
  "genealogy": {
    "ancestors": [
      {
        "id": "uuid-123",
        "title": "Basic Binary Search",
        "evolution_stage": 0,
        "created_at": "2025-10-20T10:00:00Z"
      },
      {
        "id": "uuid-456",
        "title": "Binary Search with Bounds Check",
        "evolution_stage": 1,
        "parent_memory_id": "uuid-123",
        "created_at": "2025-10-21T14:30:00Z"
      }
    ],
    "current": {
      "id": "uuid-789",
      "title": "Binary Search with Duplicates",
      "evolution_stage": 2,
      "parent_memory_id": "uuid-456",
      "created_at": "2025-10-22T16:45:00Z"
    },
    "descendants": [
      {
        "id": "uuid-999",
        "title": "Optimized Binary Search",
        "evolution_stage": 3,
        "parent_memory_id": "uuid-789",
        "created_at": "2025-10-23T09:20:00Z"
      }
    ]
  },
  "total_generations": 4
}
```

---

### get_statistics

Get system performance metrics.

**Parameters**: None

**Example Request**:

```json
{}
```

**Example Response**:

```json
{
  "memory_statistics": {
    "total_traces": 127,
    "total_memories": 384,
    "success_rate": 0.87,
    "failure_rate": 0.13,
    "average_score": 0.82
  },
  "cache_statistics": {
    "total_calls": 1543,
    "cache_hits": 687,
    "cache_misses": 856,
    "cache_hit_rate": 0.445,
    "cache_size": 89,
    "cache_max_size": 100
  },
  "api_statistics": {
    "total_api_calls": 856,
    "failed_calls": 12,
    "retried_calls": 8,
    "error_rate": 0.014,
    "average_latency_ms": 1250
  },
  "workspace_statistics": {
    "current_workspace_id": "abc123def456",
    "workspace_memory_count": 42
  },
  "uptime_seconds": 86400
}
```

## Common Usage Patterns

### Pattern 1: Simple Task Solving

Solve a task with default settings (memory enabled, MaTTS enabled):

```json
{
  "task": "Write a function to reverse a linked list"
}
```

### Pattern 2: Fast Mode (No MaTTS)

Solve quickly without parallel attempts:

```json
{
  "task": "Write a function to reverse a linked list",
  "enable_matts": false
}
```

### Pattern 3: Cold Start (No Memory)

Solve without using past memories:

```json
{
  "task": "Write a function to reverse a linked list",
  "use_memory": false
}
```

### Pattern 4: Exploration Mode (Don't Store)

Try solutions without storing results:

```json
{
  "task": "Write a function to reverse a linked list",
  "store_result": false
}
```

### Pattern 5: High-Quality Mode

Generate more solutions for better quality:

```json
{
  "task": "Write a function to reverse a linked list",
  "enable_matts": true,
  "matts_k": 10,
  "matts_mode": "parallel"
}
```

### Pattern 6: Sequential MaTTS

Generate multiple solutions sequentially (lower memory usage):

```json
{
  "task": "Write a function to reverse a linked list",
  "enable_matts": true,
  "matts_k": 5,
  "matts_mode": "sequential"
}
```

### Pattern 7: Memory Research

Find relevant past experiences before solving:

```json
// First, retrieve memories
{
  "query": "linked list reversal",
  "n_results": 10
}

// Then solve with context
{
  "task": "Write a function to reverse a linked list",
  "use_memory": true
}
```

### Pattern 8: Error Analysis

Find past failures to avoid mistakes:

```json
{
  "query": "linked list null pointer error",
  "n_results": 5
}
```

### Pattern 9: Knowledge Evolution

Trace how knowledge improved over time:

```json
// Get a memory ID from retrieve_memories
{
  "memory_id": "uuid-from-previous-query"
}
```

## Configuration Examples

### Development Configuration

`.env` for local development:

```env
OPENROUTER_API_KEY=your_dev_api_key
REASONING_BANK_DATA=./chroma_data
REASONING_BANK_TRACES=./traces
DEFAULT_MODEL=google/gemini-2.5-pro
DEFAULT_REASONING_EFFORT=low
MAX_ITERATIONS=2
ENABLE_CACHE=true
CACHE_TTL=1800
STORAGE_BACKEND=chromadb
LOG_LEVEL=DEBUG
```

### Production Configuration

`.env` for production:

```env
OPENROUTER_API_KEY=your_prod_api_key
REASONING_BANK_DATA=/var/lib/reasoning-bank/chroma_data
REASONING_BANK_TRACES=/var/lib/reasoning-bank/traces
DEFAULT_MODEL=google/gemini-2.5-pro
DEFAULT_REASONING_EFFORT=medium
MAX_ITERATIONS=3
ENABLE_CACHE=true
CACHE_TTL=3600
CACHE_MAX_SIZE=1000
STORAGE_BACKEND=supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_key
LOG_LEVEL=INFO
```

### High-Performance Configuration

`.env` for maximum performance:

```env
OPENROUTER_API_KEY=your_api_key
DEFAULT_MODEL=google/gemini-2.0-flash-thinking-exp
DEFAULT_REASONING_EFFORT=low
MAX_ITERATIONS=2
ENABLE_CACHE=true
CACHE_TTL=7200
CACHE_MAX_SIZE=2000
STORAGE_BACKEND=chromadb
```

### High-Quality Configuration

`.env` for maximum quality:

```env
OPENROUTER_API_KEY=your_api_key
DEFAULT_MODEL=google/gemini-2.5-pro
DEFAULT_REASONING_EFFORT=high
MAX_ITERATIONS=5
ENABLE_CACHE=true
CACHE_TTL=3600
STORAGE_BACKEND=supabase
```

## Code Examples

### Python Client Example

```python
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def solve_task():
    server_params = StdioServerParameters(
        command="python",
        args=["reasoning_bank_server.py"]
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Solve a coding task
            result = await session.call_tool(
                "solve_coding_task",
                arguments={
                    "task": "Implement quicksort in Python",
                    "use_memory": True,
                    "enable_matts": True
                }
            )
            
            print(f"Solution: {result['solution']}")
            print(f"Score: {result['score']}")
            print(f"Memories used: {len(result['memories_used'])}")

asyncio.run(solve_task())
```

### Retrieve Memories Example

```python
async def search_memories():
    # ... (setup as above)
    
    result = await session.call_tool(
        "retrieve_memories",
        arguments={
            "query": "sorting algorithms",
            "n_results": 5
        }
    )
    
    for memory in result['memories']:
        print(f"Title: {memory['title']}")
        print(f"Score: {memory['composite_score']}")
        if memory['error_context']:
            print(f"⚠️  Error: {memory['error_context']['failure_pattern']}")
        print()

asyncio.run(search_memories())
```

### Batch Processing Example

```python
async def batch_solve():
    tasks = [
        "Implement binary search",
        "Implement merge sort",
        "Implement depth-first search"
    ]
    
    # ... (setup as above)
    
    results = []
    for task in tasks:
        result = await session.call_tool(
            "solve_coding_task",
            arguments={"task": task}
        )
        results.append(result)
    
    # Analyze results
    avg_score = sum(r['score'] for r in results) / len(results)
    print(f"Average score: {avg_score}")

asyncio.run(batch_solve())
```

## CLI Commands

### Start Server

```bash
# Local development
python reasoning_bank_server.py

# Docker
docker-compose up -d

# Docker with rebuild
docker-compose up -d --build
```

### View Logs

```bash
# Docker logs (real-time)
docker-compose logs -f reasoning-bank

# Docker logs (last 100 lines)
docker-compose logs --tail=100 reasoning-bank

# Search for errors
docker-compose logs reasoning-bank | grep ERROR
```

### Test Deployment

```bash
# Run verification script
python verify_deployment.py

# Run test suite
python test_phase1_phase2.py
python test_responses_api.py
python test_server.py
```

### Database Operations

```bash
# Backup ChromaDB
tar -czf chroma_backup_$(date +%Y%m%d).tar.gz chroma_data/

# Restore ChromaDB
tar -xzf chroma_backup_YYYYMMDD.tar.gz

# Migrate to Supabase
python migrate_to_supabase.py

# Validate migration
python validate_migration_setup.py
```

### Container Management

```bash
# Stop container
docker-compose down

# Restart container
docker-compose restart

# View container stats
docker stats reasoning-bank-mcp

# Execute command in container
docker-compose exec reasoning-bank python -c "print('Hello')"

# Access container shell
docker-compose exec reasoning-bank /bin/bash
```

## Troubleshooting Quick Fixes

### Issue: API Key Error

```bash
# Check if API key is set
grep OPENROUTER_API_KEY .env

# Set API key
echo "OPENROUTER_API_KEY=your_key_here" >> .env

# Restart
docker-compose restart
```

### Issue: Container Won't Start

```bash
# Check logs
docker-compose logs reasoning-bank

# Rebuild
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Issue: Slow Performance

```bash
# Enable caching
echo "ENABLE_CACHE=true" >> .env

# Reduce reasoning effort
echo "DEFAULT_REASONING_EFFORT=low" >> .env

# Restart
docker-compose restart
```

### Issue: Out of Memory

```bash
# Clear cache (restart container)
docker-compose restart

# Increase memory limit in docker-compose.yml
# Add under service:
#   mem_limit: 4g
```

### Issue: ChromaDB Errors

```bash
# Check permissions
ls -la chroma_data/

# Recreate directory
docker-compose down
rm -rf chroma_data/
mkdir chroma_data
docker-compose up -d
```

### Issue: No Memories Found

This is normal for cold start. Solve a few tasks first:

```json
{
  "task": "Implement bubble sort",
  "store_result": true
}
```

Then query:

```json
{
  "query": "sorting algorithm",
  "n_results": 5
}
```

## Performance Tips

1. **Enable Caching**: Set `ENABLE_CACHE=true` for 20-30% cost reduction
2. **Use Lower Reasoning Effort**: Set `DEFAULT_REASONING_EFFORT=low` for faster responses
3. **Reduce Iterations**: Set `MAX_ITERATIONS=2` for quicker results
4. **Disable MaTTS for Speed**: Set `enable_matts=false` in requests
5. **Use Sequential MaTTS**: Set `matts_mode=sequential` to reduce memory usage
6. **Increase Cache Size**: Set `CACHE_MAX_SIZE=1000` for better hit rates
7. **Use Faster Model**: Set `DEFAULT_MODEL=google/gemini-2.0-flash-thinking-exp`

## Best Practices

1. **Always Use Memory**: Keep `use_memory=true` to benefit from past experiences
2. **Store Results**: Keep `store_result=true` to build knowledge base
3. **Monitor Statistics**: Regularly check `get_statistics` for system health
4. **Review Error Memories**: Query error contexts to learn from failures
5. **Use Workspace Isolation**: Separate projects for better organization
6. **Regular Backups**: Backup ChromaDB data regularly
7. **Monitor Logs**: Check logs for errors and performance issues
8. **Update API Keys**: Rotate keys regularly for security

## Quick Reference Card

| Task | Command/Request |
|------|----------------|
| Solve task | `{"task": "..."}` |
| Fast solve | `{"task": "...", "enable_matts": false}` |
| Search memories | `{"query": "...", "n_results": 5}` |
| Get stats | `{}` (get_statistics) |
| View logs | `docker-compose logs -f` |
| Restart | `docker-compose restart` |
| Backup | `tar -czf backup.tar.gz chroma_data/` |
| Test | `python verify_deployment.py` |

## Additional Resources

- [README.md](README.md) - Full documentation
- [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) - Deployment instructions
- [Design Document](.kiro/specs/reasoningbank-mcp-system/design.md) - Architecture details
- [Requirements Document](.kiro/specs/reasoningbank-mcp-system/requirements.md) - System requirements
