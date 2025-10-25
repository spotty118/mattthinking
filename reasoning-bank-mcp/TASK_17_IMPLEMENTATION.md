# Task 17: get_memory_genealogy MCP Tool Implementation

## Overview
Implemented the `get_memory_genealogy` MCP tool that traces memory evolution trees, showing how knowledge evolved through refinement and derivation.

## Implementation Details

### 1. Enhanced `get_genealogy()` Method in ReasoningBank Core

**Location:** `reasoning_bank_core.py`

**Key Features:**
- Retrieves all memories from storage to build genealogy tree
- Finds parent memories using `parent_memory_id` field
- Finds additional parent memories from `derived_from` list
- Identifies children (memories that reference this memory as parent)
- Builds complete ancestry chain from root to current memory
- Handles circular references with visited set
- Provides rich metadata about relationships

**Return Structure:**
```python
{
    "memory_id": str,              # The queried memory ID
    "memory_title": str,           # Title of the memory
    "evolution_stage": int,        # Current evolution stage
    "parents": [                   # List of parent memories
        {
            "id": str,
            "title": str,
            "evolution_stage": int,
            "relationship": str    # "parent" or "derived_from"
        }
    ],
    "children": [                  # List of derived memories
        {
            "id": str,
            "title": str,
            "evolution_stage": int,
            "relationship": str    # "child" or "derived"
        }
    ],
    "derived_from": [str],         # List of memory IDs
    "ancestry_chain": [str],       # Complete chain from root to current
    "total_ancestors": int,        # Count of ancestors
    "total_descendants": int,      # Count of descendants
    "is_root": bool,              # True if no parents
    "is_leaf": bool               # True if no children
}
```

### 2. MCP Tool Implementation

**Location:** `reasoning_bank_server.py`

The `get_memory_genealogy` MCP tool was already defined in the server file. It:
- Accepts a `memory_id` parameter
- Calls `reasoning_bank.get_genealogy(memory_id)`
- Returns the genealogy data
- Handles errors gracefully

**Tool Signature:**
```python
@server.call_tool()
async def get_memory_genealogy(memory_id: str) -> Dict[str, Any]:
    """
    Trace memory evolution tree
    
    Returns the complete ancestry and descendant tree for a memory,
    showing how knowledge evolved through refinement and derivation.
    """
```

### 3. Test Coverage

**Location:** `test_genealogy.py`

Created comprehensive test that verifies:
1. Creating memories with parent-child relationships
2. Creating multi-generation ancestry chains (root → child → grandchild)
3. Creating sibling memories (alternative evolution branches)
4. Creating memories derived from multiple parents
5. Retrieving genealogy for root memories
6. Retrieving genealogy for child memories
7. Retrieving genealogy for leaf memories
8. Tracing complete ancestry chains
9. Finding all descendants

**Test Scenarios:**
- Root memory (generation 0) with 2 children
- Child memory (generation 1) with parent and children
- Grandchild memory (generation 2) with full ancestry chain
- Sibling memory (alternative branch from root)
- Merged memory (derived from multiple parents)

## Requirements Addressed

### ✅ Requirement 5.3: MCP Tool Interface
- Implemented `get_memory_genealogy` tool that accepts memory UUID
- Returns complete evolution tree with parent-child relationships

### ✅ Requirement 8.1: Parent Memory Recording
- System records parent memory UUID in `parent_memory_id` field
- Genealogy method retrieves and displays parent information

### ✅ Requirement 8.2: Evolution Stage Tracking
- System tracks evolution stage numbers (0 = original, 1+ = refined)
- Genealogy includes evolution stage for all memories in tree

### ✅ Requirement 8.3: Complete Ancestry Tree
- Returns complete ancestry tree including all parents and derived memories
- Builds ancestry chain from root to current memory
- Handles multi-generation chains correctly

### ✅ Requirement 8.4: Query Derived Memories
- Supports querying all memories derived from a specific parent
- Returns children list with all descendants
- Distinguishes between direct children and derived memories

### ✅ Requirement 8.5: Genealogy Metadata
- Includes genealogy metadata in retrieval results
- Provides `is_root`, `is_leaf`, `total_ancestors`, `total_descendants`
- Shows relationship types (parent, child, derived_from, derived)

## Usage Example

```python
# Via MCP tool
result = await get_memory_genealogy(memory_id="550e8400-e29b-41d4-a716-446655440000")

# Direct API
genealogy = reasoning_bank.get_genealogy("550e8400-e29b-41d4-a716-446655440000")

# Example output
{
    "memory_id": "550e8400-e29b-41d4-a716-446655440000",
    "memory_title": "Binary Search with Error Handling",
    "evolution_stage": 1,
    "parents": [
        {
            "id": "parent-uuid",
            "title": "Binary Search Algorithm",
            "evolution_stage": 0
        }
    ],
    "children": [
        {
            "id": "child-uuid",
            "title": "Optimized Binary Search",
            "evolution_stage": 2,
            "relationship": "child"
        }
    ],
    "ancestry_chain": ["parent-uuid", "550e8400-e29b-41d4-a716-446655440000"],
    "total_ancestors": 1,
    "total_descendants": 1,
    "is_root": false,
    "is_leaf": false
}
```

## Implementation Notes

### Performance Considerations
- Current implementation loads all memories to build genealogy tree
- For large datasets (>10,000 memories), consider:
  - Adding direct relationship queries to storage backend
  - Caching genealogy results
  - Implementing pagination for large trees

### Storage Backend Support
- Works with ChromaDB adapter (current implementation)
- Accesses `storage.collection.get()` directly
- Future: Add genealogy-specific methods to StorageBackendInterface

### Error Handling
- Raises `MemoryRetrievalError` if memory not found
- Handles circular references with visited set
- Gracefully handles missing parent references

## Testing

To run the genealogy tests:

```bash
cd reasoning-bank-mcp
python3 test_genealogy.py
```

The test creates a multi-generation memory tree and verifies:
- Parent-child relationships are correctly tracked
- Evolution stages increment properly
- Ancestry chains are complete
- Descendants are found correctly
- Multiple parent derivation works

## Files Modified

1. **reasoning_bank_core.py**
   - Enhanced `get_genealogy()` method with full implementation
   - Added parent/child relationship traversal
   - Added ancestry chain building
   - Added comprehensive error handling

2. **reasoning_bank_server.py**
   - MCP tool already existed, no changes needed
   - Tool properly calls `reasoning_bank.get_genealogy()`

3. **test_genealogy.py** (new file)
   - Comprehensive test suite for genealogy functionality
   - Tests all requirements (8.1-8.5)
   - Creates complex multi-generation memory trees

## Verification

The implementation satisfies all task requirements:

✅ Create `get_memory_genealogy()` tool function accepting memory_id parameter
✅ Call `ReasoningBank.get_genealogy()` to trace evolution tree
✅ Format genealogy data with parent-child relationships
✅ Return complete ancestry tree
✅ Address requirements 5.3, 8.1, 8.2, 8.3, 8.4, 8.5

## Next Steps

The genealogy functionality is complete and ready for use. Future enhancements could include:
- Visualization of genealogy trees (e.g., Mermaid diagrams)
- Genealogy-based memory filtering
- Evolution metrics (average generations, branching factor)
- Genealogy-aware memory pruning
