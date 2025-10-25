# Workspace Isolation Guide

## Overview

**Workspace Isolation** ensures that each codebase directory has its own isolated memory bank in ReasoningBank. This prevents knowledge from different projects from mixing together.

## How It Works

### Automatic Workspace Detection

When you open a directory, ReasoningBank automatically:
1. Detects the directory path
2. Generates a unique `workspace_id` (hash of the absolute path)
3. Filters all queries and storage by that workspace_id

### Key Features

✅ **Separate Memory Banks**: Each workspace has isolated traces and memories  
✅ **Automatic Isolation**: No cross-contamination between projects  
✅ **Deterministic IDs**: Same directory always gets the same workspace_id  
✅ **Passive Learning**: Works with both active and passive learning modes  

## Usage

### Set Workspace (Automatic)

The workspace is auto-detected from your current directory when the MCP server starts.

```bash
# The server auto-detects from your current working directory
cd /path/to/project-a
docker-compose up -d  # workspace_id = hash of /path/to/project-a
```

### Set Workspace (Manual)

Use the `set_workspace` tool to explicitly set a workspace:

```python
# Via MCP tool
set_workspace(directory_path="/Users/justin/my-project")
```

### Check Current Workspace

```python
# Get workspace info
get_workspace_info()

# Returns:
{
  "workspace_id": "a1b2c3d4e5f6g7h8",
  "workspace_path": "/Users/justin/my-project",
  "workspace_name": "my-project",
  "status": "active"
}
```

## Examples

### Example: Two Separate Projects

**Project A** (`/Users/justin/frontend-app`):
```bash
cd /Users/justin/frontend-app
docker-compose restart

# workspace_id = hash("/Users/justin/frontend-app")
# All learnings stored with this workspace_id
```

Ask questions about React → stored to Project A's memory bank

**Project B** (`/Users/justin/backend-api`):
```bash
cd /Users/justin/backend-api  
docker-compose restart

# workspace_id = hash("/Users/justin/backend-api")
# Completely separate from Project A
```

Ask questions about Node.js → stored to Project B's memory bank

### Data Isolation

**Project A queries** only see Project A memories:
```sql
SELECT * FROM memory_items 
WHERE workspace_id = 'a1b2c3d4e5f6g7h8';  -- Only Project A
```

**Project B queries** only see Project B memories:
```sql
SELECT * FROM memory_items 
WHERE workspace_id = 'x9y8z7w6v5u4t3s2';  -- Only Project B
```

## Environment Variable

You can also set workspace via environment variable:

```bash
# In .env or docker-compose.yml
WORKSPACE_PATH=/Users/justin/my-project
```

The workspace manager will use this if available.

## Database Schema

### Tables with Workspace Isolation

Both tables now include `workspace_id`:

**reasoning_traces**:
- `workspace_id` TEXT - Isolates traces by workspace
- Indexed for fast filtering

**memory_items**:
- `workspace_id` TEXT - Isolates memories by workspace
- Indexed for fast filtering

### Query Functions

All search functions now support workspace filtering:

```sql
-- Search traces in current workspace only
search_similar_traces(
  query_embedding := ...,
  match_count := 5,
  workspace_filter := 'current_workspace_id'
);

-- Search memories in current workspace only
search_similar_memories(
  query_embedding := ...,
  match_count := 5,
  workspace_filter := 'current_workspace_id'
);
```

## Benefits

### 1. **Clean Separation**
Different projects don't pollute each other's memory banks.

### 2. **Contextual Learning**
Memories are relevant to the specific codebase you're working on.

### 3. **No Manual Management**
Automatic detection means zero configuration for most use cases.

### 4. **Flexible Switching**
Easy to switch between projects - just change directory and restart.

## Advanced Usage

### Share Learnings Across Workspaces

If you want to share knowledge between projects, you can:

1. **Query specific workspace**:
```python
# Manually query another workspace's memories
# (requires modifying the search to accept workspace_id parameter)
```

2. **Export/Import**:
```sql
-- Export memories from one workspace
SELECT * FROM memory_items WHERE workspace_id = 'source_id';

-- Import to another (update workspace_id)
UPDATE memory_items 
SET workspace_id = 'target_id' 
WHERE id IN (...);
```

### Global Memories (All Workspaces)

Set `workspace_id = NULL` for global memories:

```sql
-- Store a global memory (visible to all workspaces)
INSERT INTO memory_items (...) VALUES (..., NULL);
```

The search functions treat `NULL` workspace_id as "match all workspaces".

## Workspace ID Generation

Workspace IDs are generated deterministically:

```python
import hashlib

def generate_workspace_id(path: str) -> str:
    abs_path = os.path.abspath(path)
    hash_obj = hashlib.sha256(abs_path.encode('utf-8'))
    return hash_obj.hexdigest()[:16]
```

**Properties**:
- Same path → same ID (deterministic)
- Different paths → different IDs
- 16-character hex string
- Based on absolute path (not affected by symlinks)

## Troubleshooting

### Memories Not Appearing

**Problem**: You stored memories but can't retrieve them.

**Solution**: Check workspace ID:
```python
get_workspace_info()
# Make sure workspace_id matches where memories were stored
```

### Wrong Workspace Active

**Problem**: Getting memories from a different project.

**Solution**: Set workspace explicitly:
```python
set_workspace(directory_path="/correct/path/to/project")
```

### Workspace Not Auto-Detected

**Problem**: Workspace shows as "not_set".

**Solution**: Set via environment variable or manual tool call:
```bash
export WORKSPACE_PATH=/path/to/your/project
docker-compose restart
```

## Summary

✅ **Each directory = isolated memory bank**  
✅ **Automatic detection from current directory**  
✅ **Manual override available**  
✅ **Zero cross-contamination**  
✅ **Works with passive and active learning**  

Your ReasoningBank now keeps different projects completely separate! 🎯
