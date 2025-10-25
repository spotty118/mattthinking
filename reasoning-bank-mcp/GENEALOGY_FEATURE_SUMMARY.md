# Memory Genealogy Feature Summary

## What Was Implemented

The `get_memory_genealogy` MCP tool enables tracing the complete evolution history of memories, showing how knowledge evolved through refinement and derivation.

## Key Capabilities

### 1. Parent-Child Tracking
- Each memory can have a `parent_memory_id` indicating direct lineage
- Memories can be `derived_from` multiple parent memories
- Evolution stages track generation depth (0 = root, 1+ = evolved)

### 2. Ancestry Chain
- Traces complete path from root ancestor to current memory
- Example: `root_id → child_id → grandchild_id`
- Prevents circular references with visited tracking

### 3. Descendant Discovery
- Finds all memories that evolved from a given memory
- Distinguishes between direct children and derived memories
- Supports branching evolution (multiple children from one parent)

### 4. Rich Metadata
- `is_root`: Memory has no parents
- `is_leaf`: Memory has no children
- `total_ancestors`: Count of generations above
- `total_descendants`: Count of memories evolved from this one

## Example Use Cases

### Use Case 1: Trace Algorithm Evolution
```
Root: "Binary Search Algorithm" (stage 0)
  ├─ Child: "Binary Search with Error Handling" (stage 1)
  │   └─ Grandchild: "Optimized Binary Search with Logging" (stage 2)
  └─ Child: "Binary Search for Strings" (stage 1)
```

### Use Case 2: Merge Multiple Approaches
```
Parent A: "Error Handling Pattern" (stage 1)
Parent B: "String Comparison Pattern" (stage 1)
  └─ Merged: "Universal Search with Error Handling" (stage 2)
      [derived_from: [Parent A, Parent B]]
```

### Use Case 3: Find All Variations
Query genealogy for root memory to see all evolved versions:
- Direct children (immediate refinements)
- Grandchildren (further refinements)
- Derived memories (alternative approaches)

## API Reference

### MCP Tool
```python
# Call via MCP
result = await get_memory_genealogy(
    memory_id="550e8400-e29b-41d4-a716-446655440000"
)
```

### Direct API
```python
# Call directly
genealogy = reasoning_bank.get_genealogy(
    memory_id="550e8400-e29b-41d4-a716-446655440000"
)
```

### Response Format
```json
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
  "derived_from": ["parent-uuid"],
  "ancestry_chain": ["parent-uuid", "550e8400-e29b-41d4-a716-446655440000"],
  "total_ancestors": 1,
  "total_descendants": 1,
  "is_root": false,
  "is_leaf": false
}
```

## Benefits

1. **Knowledge Lineage**: Understand how solutions evolved over time
2. **Pattern Discovery**: Identify successful evolution paths
3. **Context Awareness**: See what approaches were tried before
4. **Quality Tracking**: Monitor how refinements improve solutions
5. **Branching Analysis**: Discover alternative solution approaches

## Integration Points

### With Memory Retrieval
- Genealogy metadata can inform memory ranking
- Prefer memories from successful evolution chains
- Avoid patterns from failed branches

### With Iterative Refinement
- Store parent_memory_id when refining solutions
- Increment evolution_stage for each refinement
- Track which memories led to improvements

### With MaTTS (Parallel Solutions)
- When merging best solutions, record derived_from
- Create new memories that combine multiple approaches
- Track which parallel attempts contributed to final solution

## Performance Notes

- Current implementation loads all memories to build tree
- Efficient for datasets up to ~10,000 memories
- For larger datasets, consider:
  - Caching genealogy results
  - Adding direct relationship queries to storage
  - Implementing lazy loading for large trees

## Future Enhancements

1. **Visualization**: Generate Mermaid diagrams of evolution trees
2. **Metrics**: Calculate branching factor, average depth, success rates by generation
3. **Pruning**: Remove unsuccessful evolution branches
4. **Search**: Find memories by genealogy criteria (e.g., "all stage 2+ memories")
5. **Export**: Export genealogy trees for analysis

## Testing

Comprehensive test suite in `test_genealogy.py` covers:
- Multi-generation chains (3+ levels)
- Sibling memories (branching)
- Multiple parent derivation
- Ancestry chain building
- Descendant discovery
- All requirements (8.1-8.5)

Run tests:
```bash
cd reasoning-bank-mcp
python3 test_genealogy.py
```

## Requirements Satisfied

✅ **5.3**: MCP tool interface for genealogy queries
✅ **8.1**: Parent memory UUID recording
✅ **8.2**: Evolution stage tracking
✅ **8.3**: Complete ancestry tree retrieval
✅ **8.4**: Query all derived memories
✅ **8.5**: Genealogy metadata in results
