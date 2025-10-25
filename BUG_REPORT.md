# Bug Report - ReasoningBank MCP System

## Date: October 25, 2025

### Summary
This document details critical and medium-severity bugs found during codebase review of the ReasoningBank MCP system.

---

## 🔴 CRITICAL BUGS (Must Fix Immediately)

### Bug #1: Missing MCP Dependency in requirements.txt
**File:** `reasoning-bank-mcp/requirements.txt`  
**Severity:** CRITICAL  
**Impact:** System cannot start - ImportError on server startup

**Description:**
The `reasoning_bank_server.py` imports from `mcp` package (lines 28-30):
```python
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types
```

However, `requirements.txt` does not include the `mcp` or `fastmcp` package.

**Fix:**
Add to `requirements.txt`:
```
mcp>=1.0.0
# OR if using FastMCP
fastmcp>=1.0.0
```

---

### Bug #2: Incomplete SupabaseAdapter - Missing Required Methods
**File:** `reasoning-bank-mcp/supabase_storage.py`  
**Lines:** 554 (file ends prematurely)  
**Severity:** CRITICAL  
**Impact:** Runtime errors when using Supabase backend

**Description:**
The `SupabaseAdapter` class implements `StorageBackendInterface` but is missing two required abstract methods:
- `delete_old_traces()`
- `delete_workspace()`

The file appears to be truncated at line 554, cutting off mid-class definition.

**Fix:**
Complete the implementation of `SupabaseAdapter` by adding the missing methods:
```python
def delete_old_traces(
    self,
    retention_days: int,
    workspace_id: Optional[str] = None
) -> Dict[str, Any]:
    # Implementation needed
    pass

def delete_workspace(self, workspace_id: str) -> Dict[str, Any]:
    # Implementation needed
    pass
```

---

### Bug #3: Backend-Specific Code Breaks Abstraction
**File:** `reasoning-bank-mcp/reasoning_bank_core.py`  
**Line:** 488  
**Severity:** CRITICAL  
**Impact:** get_genealogy() fails with Supabase backend

**Description:**
The `get_genealogy()` method directly accesses ChromaDB-specific API:
```python
all_results = self.storage.collection.get(
    where={"workspace_id": workspace_id} if workspace_id else None,
    include=["metadatas"]
)
```

This assumes `self.storage` is a ChromaDBAdapter and has a `.collection` attribute, violating the `StorageBackendInterface` abstraction.

**Fix:**
Add a new abstract method to `StorageBackendInterface`:
```python
@abstractmethod
def get_all_memories_metadata(
    self,
    workspace_id: Optional[str] = None
) -> Dict[str, Any]:
    """Get all memories with metadata for genealogy queries"""
    pass
```

Then implement this in both ChromaDBAdapter and SupabaseAdapter.

---

### Bug #4: Logger Attribute Error in SupabaseAdapter
**File:** `reasoning-bank-mcp/supabase_storage.py`  
**Lines:** 449, 475  
**Severity:** HIGH  
**Impact:** AttributeError when logging errors

**Description:**
Code uses `self.logger.error()` but logger is module-level, not instance-level:
```python
# Line 449
self.logger.error(f"Failed to count traces: {str(e)}")

# Line 475
self.logger.error(f"Failed to count memories: {str(e)}")
```

**Fix:**
Change to use module-level logger:
```python
logger.error(f"Failed to count traces: {str(e)}")
logger.error(f"Failed to count memories: {str(e)}")
```

---

## 🟡 MEDIUM SEVERITY BUGS

### Bug #5: Similarity Score Metadata Not Returned
**File:** `reasoning-bank-mcp/storage_adapter.py`  
**Lines:** 463-468  
**Severity:** MEDIUM  
**Impact:** Similarity scores and other metadata lost during retrieval

**Description:**
The code adds metadata with `_` prefix but then filters it out:
```python
memory_dict["_similarity_score"] = similarity_score
memory_dict["_trace_outcome"] = metadata.get("outcome")
memory_dict["_trace_timestamp"] = metadata.get("timestamp")

# Then filters out underscore-prefixed keys
memories.append(MemoryItemSchema(**{k: v for k, v in memory_dict.items() if not k.startswith("_")}))
```

This means similarity_score, trace_outcome, and trace_timestamp are never passed to the MemoryItem.

**Fix:**
Store these values in proper MemoryItem fields or include them without underscore prefix.

---

### Bug #6: Timezone-Naive DateTime Comparison
**File:** `reasoning-bank-mcp/reasoning_bank_core.py`  
**Line:** 424  
**Severity:** MEDIUM  
**Impact:** TypeError when comparing timezone-aware and naive datetimes

**Description:**
In `compute_composite_score()`, uses `datetime.now()` (timezone-naive) but `memory.trace_timestamp` might be timezone-aware:
```python
trace_time = datetime.fromisoformat(memory.trace_timestamp.replace('Z', '+00:00'))
# ^^ This is timezone-aware

age_seconds = (current_time - trace_time).total_seconds()
# ^^ current_time from datetime.now() is timezone-naive
```

**Fix:**
```python
from datetime import datetime, timezone

def compute_composite_score(
    self,
    memory: MemoryItem,
    current_time: Optional[datetime] = None
) -> float:
    if current_time is None:
        current_time = datetime.now(timezone.utc)  # Make timezone-aware
    # ... rest of code
```

---

### Bug #7: Incorrect Token Count in Cached Client
**File:** `reasoning-bank-mcp/cached_llm_client.py`  
**Line:** 230  
**Severity:** LOW-MEDIUM  
**Impact:** Off-by-one error in statistics

**Description:**
Total requests calculation is incorrect:
```python
total_requests = self._cache_hits + self._cache_misses + self._cache_bypassed + 1
```

The `+1` should not be there. This calculates the count for the *next* request, not the current total.

**Fix:**
```python
total_requests = self._cache_hits + self._cache_misses + self._cache_bypassed
```

---

### Bug #8: Incorrect Model Name in Embedding Error
**File:** `reasoning-bank-mcp/storage_adapter.py`  
**Line:** 289  
**Severity:** LOW  
**Impact:** Misleading error messages

**Description:**
```python
raise EmbeddingError(
    "Failed to generate embedding",
    text=text[:100],
    model_name=self.embedder.get_sentence_embedding_dimension(),  # BUG: This returns int, not string
    context={"error": str(e)}
)
```

`get_sentence_embedding_dimension()` returns an integer (e.g., 384), not the model name.

**Fix:**
Store model name in `__init__` and use it:
```python
def __init__(self, ...):
    # ...
    self.embedding_model = embedding_model  # Store the model name
    self.embedder = SentenceTransformer(embedding_model)

def _generate_embedding(self, text: str) -> List[float]:
    try:
        embedding = self.embedder.encode(text, convert_to_numpy=True)
        return embedding.tolist()
    except Exception as e:
        raise EmbeddingError(
            "Failed to generate embedding",
            text=text[:100],
            model_name=self.embedding_model,  # Use stored model name
            context={"error": str(e)}
        )
```

---

## 🟢 LOW SEVERITY BUGS / CODE QUALITY ISSUES

### Bug #9: Confusing Async Logic in Parallel Solution Generation
**File:** `reasoning-bank-mcp/iterative_agent.py`  
**Lines:** 614-641  
**Severity:** LOW  
**Impact:** Code complexity, potential edge case failures

**Description:**
The `_generate_parallel_solutions()` method has complex async handling:
- Tries to detect existing event loop
- Falls back to ThreadPoolExecutor if loop exists
- Falls back to sequential if parallel fails

The logic is confusing and the ThreadPoolExecutor approach may not provide true parallelism for LLM calls (which are I/O bound and should use async).

**Recommendation:**
Simplify to either:
1. Always use async/await (preferred for I/O-bound operations)
2. Always use sequential (simpler, more predictable)

---

### Bug #10: Potential Distance Metric Confusion
**File:** `reasoning-bank-mcp/storage_adapter.py`  
**Line:** 456  
**Severity:** LOW  
**Impact:** Potentially incorrect similarity scores

**Description:**
Comment mentions "ChromaDB uses L2 distance" but the conversion formula `1.0 / (1.0 + distance)` is more appropriate for L2 distance than cosine distance. Need to verify which distance metric ChromaDB actually uses by default and ensure the conversion is correct.

**Recommendation:**
- Check ChromaDB documentation for default distance metric
- If using cosine similarity, scores should already be in [0, 1]
- If using L2 distance, current formula is acceptable
- Add clarifying comments

---

## Testing Recommendations

1. **Add integration tests** for Supabase backend to catch missing method implementations
2. **Add timezone tests** for datetime comparisons across timezones
3. **Add mock tests** for storage abstraction to ensure no backend-specific code leaks through
4. **Add statistics tests** to verify cache hit/miss counting accuracy

---

## Priority Fix Order

1. **CRITICAL**: Add MCP to requirements.txt (blocks system startup)
2. **CRITICAL**: Complete SupabaseAdapter implementation
3. **CRITICAL**: Fix get_genealogy() abstraction violation
4. **HIGH**: Fix logger attribute errors
5. **MEDIUM**: Fix similarity score metadata loss
6. **MEDIUM**: Fix timezone-naive datetime issues
7. **LOW**: Other cleanup and improvements

---

## Affected Components

- ✅ Core Server: `reasoning_bank_server.py`
- ✅ Storage Layer: `storage_adapter.py`, `supabase_storage.py`
- ✅ Core Logic: `reasoning_bank_core.py`
- ✅ Caching: `cached_llm_client.py`
- ✅ Agent: `iterative_agent.py`

---

## Notes

- All bugs have been verified by code inspection
- No runtime testing was performed for this report
- Some bugs may only manifest under specific conditions (e.g., Supabase backend, timezone differences)
- Code appears to be actively developed; some truncation may be from incomplete commits
