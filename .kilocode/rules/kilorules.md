# ============================================================================
# FILE: .kilocode
# ReasoningBank Integration Rules for Kilocode
# ============================================================================

# ReasoningBank Memory System - Kilocode Integration

## System Overview
You are connected to ReasoningBank MCP server - a self-evolving memory system that learns from all coding sessions and prevents repeated bugs across all your AI assistants.

## Mandatory Three-Phase Workflow

### PHASE 1: MEMORY RETRIEVAL (ALWAYS FIRST)
Before writing ANY code, you MUST call:
```
retrieve_memories(
  query="description of current task",
  n_results=5
)
```

**What to look for in results:**
- ✓ **Success memories** (type: "success"): Proven approaches to apply
- ⚠️ **Failure memories** (type: "failure"): Past bugs to avoid
- 🚫 **Error context** (has_error_context: true): Critical bug warnings

**CRITICAL RULE**: If any memory has `has_error_context: true`, READ IT CAREFULLY. This is a specific bug you should NOT repeat. The error_context contains:
- What code was wrong
- The exact error that occurred
- How it was fixed
- Why it happened

### PHASE 2: IMPLEMENTATION (MEMORY-GUIDED)
While coding, you must:
1. **Apply** successful patterns from retrieved memories
2. **Avoid** specific errors mentioned in failure memories
3. **Skip** APIs/functions marked as hallucinations
4. **Never** use code patterns that failed before
5. **Reference** learned strategies in your approach

**Example**: 
If memory says: "⚠️ json.loads() fails on file objects - use json.load()"
Then write: `json.load(file)` NOT `json.loads(file)`

### PHASE 3: RESULT STORAGE (ALWAYS AFTER)

**For Successful Completions:**
```
solve_coding_task(
  task="clear description of what was accomplished",
  use_memory=true,
  store_result=true
)
```

**For Failures/Bugs (EXTREMELY CRITICAL):**
When ANY error, bug, or mistake occurs, you MUST immediately store it with complete error_context:

```
solve_coding_task(
  task="task description",
  use_memory=true,
  store_result=true,
  error_context={
    "error_type": "TypeError",
    "error_message": "full error message from traceback",
    "what_was_wrong": "specific code that was incorrect",
    "how_fixed": "exact change made to fix it",
    "why_happened": "root cause analysis - why did this happen?",
    "summary": "brief description for future semantic matching"
  }
)
```

## Error Context Standards (MANDATORY FORMAT)

Every bug MUST include all six fields:

### 1. error_type
The exception class or error category:
- Standard Python: "TypeError", "AttributeError", "SyntaxError", "ImportError", "ValueError", "KeyError", "IndexError"
- Custom: "hallucination", "logic_error", "performance_issue"

### 2. error_message
The exact error message from the traceback or your observation:
- Copy the full error text if available
- Be specific and complete

### 3. what_was_wrong
The specific incorrect code or approach:
- Show the actual bad code
- Be precise about what was used incorrectly
- Examples:
  - "Used `requests.get(url, max_wait=5)`"
  - "Tried to call `list.append_all(items)`"
  - "Used `json.loads(file_object)`"
  - "Imported non-existent `from json import parse_file`"

### 4. how_fixed
Your exact correction:
- Show the corrected code
- Explain what you changed
- Examples:
  - "Changed to `requests.get(url, timeout=5)`"
  - "Changed to `list.extend(items)`"
  - "Changed to `json.load(file_object)`"
  - "Changed to `import json` and used `json.load()`"

### 5. why_happened
Root cause analysis (this is the most important field):
- Explain WHY the error occurred, not just WHAT happened
- Identify the conceptual mistake
- Examples:
  - "Hallucinated 'max_wait' parameter - requests library only has 'timeout'"
  - "Mixed concepts from append() and extend() - created fake method"
  - "Confused json.loads (for strings) with json.load (for files)"
  - "Hallucinated a convenience function that doesn't exist in standard library"

### 6. summary
Brief description for semantic search matching (1-2 lines):
- Make it searchable for future similar situations
- Include key terms
- Examples:
  - "requests timeout parameter hallucination - max_wait doesn't exist"
  - "list.append_all is not a real method - use extend"
  - "json.loads vs json.load file object confusion"

## Real-World Examples

### Example 1: API Parameter Hallucination
```python
# You write:
response = requests.get(url, max_wait=5)

# Error occurs:
# TypeError: get() got an unexpected keyword argument 'max_wait'

# You must store with:
error_context = {
  "error_type": "TypeError",
  "error_message": "get() got an unexpected keyword argument 'max_wait'",
  "what_was_wrong": "Used requests.get(url, max_wait=5) with non-existent parameter",
  "how_fixed": "Changed to requests.get(url, timeout=5) using the correct parameter name",
  "why_happened": "Hallucinated 'max_wait' parameter by mixing timeout concepts from other libraries. The requests library uses 'timeout' parameter, not 'max_wait'.",
  "summary": "requests library max_wait parameter hallucination - correct parameter is timeout"
}
```

### Example 2: Wrong Function for Context
```python
# You write:
with open('data.json', 'r') as f:
    data = json.loads(f)

# Error occurs:
# TypeError: the JSON object must be str, bytes or bytearray, not TextIOWrapper

# You must store with:
error_context = {
  "error_type": "TypeError",
  "error_message": "the JSON object must be str, bytes or bytearray, not TextIOWrapper",
  "what_was_wrong": "Used json.loads(file_object) on a file handle instead of file contents",
  "how_fixed": "Changed to json.load(file_object) to read directly from file",
  "why_happened": "Confused json.loads() which parses a string with json.load() which reads from a file object. The 's' in 'loads' means string, while 'load' works with files.",
  "summary": "json.loads vs json.load - loads is for strings, load is for file objects"
}
```

### Example 3: Non-existent Method
```python
# You write:
my_list.append_all([1, 2, 3])

# Error occurs:
# AttributeError: 'list' object has no attribute 'append_all'

# You must store with:
error_context = {
  "error_type": "AttributeError",
  "error_message": "'list' object has no attribute 'append_all'",
  "what_was_wrong": "Called my_list.append_all([1,2,3]) which doesn't exist",
  "how_fixed": "Changed to my_list.extend([1,2,3]) to add multiple items",
  "why_happened": "Hallucinated a method by combining append() (adds one item) and extend() (adds multiple items) concepts into a fake 'append_all' method that doesn't exist in Python.",
  "summary": "list.append_all hallucination - use extend() for multiple items"
}
```

### Example 4: Import Hallucination
```python
# You write:
from datetime import datetime_now

# Error occurs:
# ImportError: cannot import name 'datetime_now' from 'datetime'

# You must store with:
error_context = {
  "error_type": "ImportError",
  "error_message": "cannot import name 'datetime_now' from 'datetime'",
  "what_was_wrong": "Tried to import non-existent datetime_now from datetime module",
  "how_fixed": "Changed to 'from datetime import datetime' then used 'datetime.now()'",
  "why_happened": "Hallucinated a convenience function by combining the class name and method name. The datetime module has a datetime class with a now() method, not a datetime_now function.",
  "summary": "datetime_now doesn't exist - use datetime.now() method instead"
}
```

### Example 5: Wrong API Method
```python
# You write:
df.sort(by='column_name')

# Error occurs:
# AttributeError: 'DataFrame' object has no attribute 'sort'

# You must store with:
error_context = {
  "error_type": "AttributeError",
  "error_message": "'DataFrame' object has no attribute 'sort'",
  "what_was_wrong": "Used df.sort(by='column') which was deprecated and removed",
  "how_fixed": "Changed to df.sort_values(by='column_name')",
  "why_happened": "Used outdated pandas API - sort() was replaced by sort_values() in pandas 0.17. This is a deprecated method that no longer exists in current versions.",
  "summary": "pandas DataFrame.sort() deprecated - use sort_values() instead"
}
```

## Critical Rules for Kilocode (ENFORCE STRICTLY)

### DO's:
✅ **ALWAYS** retrieve memories before writing any code
✅ **ALWAYS** store results after task completion (success OR failure)
✅ **ALWAYS** include complete 6-field error_context for bugs
✅ **ALWAYS** explain WHY the error happened in root cause
✅ **ALWAYS** apply successful strategies from retrieved memories
✅ **ALWAYS** avoid errors that are warned about in memories
✅ **ALWAYS** help the system learn by providing thorough context

### DON'Ts:
❌ **NEVER** skip memory retrieval before coding
❌ **NEVER** repeat errors that have warnings in memory
❌ **NEVER** use APIs/methods marked as hallucinations in memory
❌ **NEVER** store incomplete error_context (all 6 fields required)
❌ **NEVER** ignore error warnings from retrieved memories
❌ **NEVER** just say "there was an error" without documenting it
❌ **NEVER** write the same bug that's already in memory

## Advanced Feature: MaTTS Mode
For complex or ambiguous tasks where you're uncertain, use Memory-Aware Test-Time Scaling:

```
solve_coding_task(
  task="complex task description",
  use_memory=true,
  enable_matts=true,
  matts_k=3
)
```

This generates 3 different solution attempts in parallel and picks the best one using self-contrast. It provides richer learning signals and higher success rates on difficult tasks.

## Memory Priority System
When you retrieve memories, prioritize them as:

1. **HIGHEST PRIORITY**: Error warnings (has_error_context: true)
   - These are critical bugs to avoid
   - Never repeat these exact errors
   - Apply the fixes mentioned

2. **HIGH PRIORITY**: Failure patterns (type: "failure")
   - General approaches that didn't work
   - Anti-patterns to avoid

3. **MEDIUM PRIORITY**: Success patterns (type: "success")
   - Proven strategies that worked
   - Apply when relevant to current task

4. **LOW PRIORITY**: General strategies
   - Consider if applicable
   - Adapt to current context

## Benefits You Get From This System
- **30-40% reduction** in repeated bugs and errors
- **Continuous improvement** across all coding sessions
- **Prevention** of API hallucinations and fake methods
- **Faster debugging** - system remembers what worked
- **Institutional knowledge** that persists forever
- **Cross-session learning** - all AI assistants share this memory
- **Reduced hallucinations** through error tracking

## Complete Session Example

```
User: "Write a Python script to fetch data from an API with a 5-second timeout"

Step 1 - RETRIEVE:
retrieve_memories("fetch API data with timeout Python")

Retrieved memory shows:
{
  "title": "Avoid requests.get max_wait parameter",
  "type": "failure",
  "has_error_context": true,
  "error_summary": "requests.get() has no 'max_wait' parameter - use 'timeout'"
}

Step 2 - IMPLEMENT (applying memory):
You write:
```python
import requests

def fetch_data(url):
    try:
        # Using 'timeout' parameter based on memory, NOT 'max_wait'
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.Timeout:
        print("Request timed out")
        return None
```

Step 3 - STORE:
solve_coding_task(
  task="Created API fetch function with timeout handling",
  use_memory=true,
  store_result=true
)

Result: Success! The memory prevented you from using the wrong 'max_wait' parameter. The system now has another successful example of correct timeout usage.
```

## Integration with Other AI Assistants
This ReasoningBank memory system is SHARED across all your AI coding assistants (Cline, Cursor, Claude, etc.). When you or any assistant stores a bug fix, it becomes available to all future sessions with any assistant. You're building a persistent institutional knowledge base that makes all your AI assistants smarter over time.

## Pre-Code Checklist
Before writing any code, verify:
- [ ] Called retrieve_memories with task description
- [ ] Read all retrieved memories
- [ ] Noted any error warnings (error_context present)
- [ ] Understand what to avoid from failure memories
- [ ] Understand what to apply from success memories

## Post-Code Checklist
After completing any coding task, verify:
- [ ] Called solve_coding_task to store result
- [ ] If any bug occurred, included complete error_context
- [ ] All 6 error_context fields are filled out
- [ ] Root cause (why_happened) is explained, not just symptoms
- [ ] Summary is searchable for future similar situations

## Error Context Quick Reference Card

```
error_context = {
  "error_type": "<Exception class or category>",
  
  "error_message": "<Exact error text from traceback>",
  
  "what_was_wrong": "<Specific incorrect code or approach>",
  
  "how_fixed": "<Exact correction applied>",
  
  "why_happened": "<Root cause - WHY did this happen? Not just what>",
  
  "summary": "<Brief searchable description for semantic matching>"
}
```

## Statistics and Monitoring
You can check how the memory system is performing:
```
get_statistics()
```

This shows:
- Total memories stored
- Success vs failure ratio
- Memories with error context
- Success rate improvement over time

## Final Note
This is YOUR persistent memory. Every bug you document, every success you store, makes the system smarter. Help it learn from every experience, and it will help you avoid repeating mistakes. The quality of learning depends on the quality of error_context you provide.

Think of this as building your own personal StackOverflow that learns from YOUR specific mistakes and successes.