# ReasoningBank CORE Features - Fully Active

## 🎯 The Original Vision: INTACT and WORKING

The **core ReasoningBank MCP server** is fully operational with all its original features. The passive learning and workspace isolation are **bonus additions** that don't interfere with the main functionality.

## 🧠 CORE Feature: `solve_coding_task`

This is the **heart** of ReasoningBank - the original idea from the Google ReasoningBank paper.

### How It Works

```
1. RETRIEVE relevant memories (past solutions, bug warnings)
   ↓
2. GENERATE solution (guided by memories)
   ↓
3. EVALUATE quality (self-assessment)
   ↓
4. REFINE if needed (iterative loop)
   ↓
5. JUDGE final quality (LLM-as-judge)
   ↓
6. EXTRACT learnings (memory items)
   ↓
7. STORE new memories (for future use)
```

### MCP Tool Usage

```python
# Your AI assistant calls this tool
solve_coding_task(
    task="Write a Python function to merge two sorted arrays",
    use_memory=True,          # Retrieve relevant past experiences
    enable_matts=True,        # Generate multiple solutions, pick best
    matts_k=5,               # Generate 5 parallel solutions
    matts_mode="parallel",   # or "sequential" for iterative refinement
    store_result=True        # Learn from this solution
)
```

## 🚀 Core Features (All Active)

### 1. **Iterative Reasoning** ✅
- Think → Evaluate → Refine loop
- Multiple iterations until quality threshold met
- Self-improvement through reflection

### 2. **MaTTS (Memory-Aware Test-Time Scaling)** ✅

**Parallel Mode:**
- Generates K different solutions simultaneously
- Self-contrast: compares solutions
- Selects best based on quality scoring

**Sequential Mode:**
- Iteratively refines one solution
- Each iteration improves on previous
- Guided by evaluation feedback

### 3. **Memory Retrieval** ✅
- Semantic search through past solutions
- Retrieves similar problems solved before
- **Bug warnings**: alerts about past errors
- Context-aware: uses relevant memories to guide solution

### 4. **Bug Context Learning** ✅
- Learns from failures, not just successes
- Stores error context (what went wrong, why, how fixed)
- Future tasks warned about similar pitfalls
- Reduces hallucinations by remembering mistakes

### 5. **Quality Judging** ✅
- LLM-as-judge evaluates solutions
- Confidence scoring (0.0 - 1.0)
- Detailed reasoning for judgments
- Success threshold: 0.8 (configurable)

### 6. **Memory Extraction** ✅

**From Successes:**
- Pattern: reusable approach
- Context: when it applies
- Insights: key learnings

**From Failures:**
- Pitfall: what went wrong
- Root cause: why it failed
- Prevention: how to avoid
- Alternative: better approach

## 📊 What You Have

### CORE ReasoningBank (Original)
```
✅ solve_coding_task tool
✅ Iterative reasoning engine
✅ MaTTS parallel/sequential modes
✅ Memory-guided generation
✅ Bug context learning
✅ Quality judging
✅ Memory extraction
✅ Supabase cloud storage
✅ Workspace isolation
```

### BONUS Features (Added)
```
✅ passive_learn tool (optional - doesn't interfere)
✅ Workspace isolation (keeps projects separate)
```

## 🎮 How to Use CORE Features

### Via AI Assistant

Your AI can call these MCP tools:

**Main Tool (CORE):**
```
solve_coding_task(
    task="your coding problem",
    use_memory=true,
    enable_matts=true,
    matts_k=5
)
```

**Memory Tools (CORE):**
```
retrieve_memories(query="binary search")
get_statistics()
```

**Workspace Tools (BONUS):**
```
set_workspace(directory_path="/path/to/project")
get_workspace_info()
```

**Passive Learning (BONUS):**
```
passive_learn(question="...", answer="...")
```

## 📈 Real Example: CORE in Action

### Task: "Write a binary search function"

**Step 1: Memory Retrieval**
```
Searching memories for: "binary search", "sorted array", "search algorithm"
Found: 2 relevant memories
  - Memory: "Binary search requires sorted array"
  - Warning: "Don't forget to handle empty array edge case"
```

**Step 2: Generate Solution (memory-guided)**
```python
def binary_search(arr, target):
    # Memory reminder: check for empty array
    if not arr:
        return -1
    
    left, right = 0, len(arr) - 1
    
    while left <= right:
        mid = (left + right) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    
    return -1
```

**Step 3: Evaluate**
```
Quality score: 0.85
Reasoning: "Correct implementation, handles edge cases, O(log n) time"
```

**Step 4: Judge**
```
Outcome: SUCCESS
Confidence: 0.90
```

**Step 5: Extract Learning**
```
Memory Item:
  Title: "Binary search with edge case handling"
  Pattern: "Two-pointer approach with bounds checking"
  Context: "Use for sorted array search problems"
  Insights:
    - Always check for empty array first
    - Integer overflow protection: mid = left + (right - left) // 2
```

**Step 6: Store**
```
✓ Stored to Supabase
✓ Workspace: current project
✓ Available for future retrieval
```

## 🔄 Memory Bank Growth

As you solve more tasks:

```
Task 1: Binary search
  → Stores: "Two-pointer search pattern"

Task 2: Merge sorted arrays  
  → Retrieves: "Two-pointer pattern" (from Task 1)
  → Stores: "Merge algorithm pattern"

Task 3: Find intersection
  → Retrieves: Both previous patterns
  → Builds on: existing knowledge
  → Stores: Combined insights
```

**The bank gets smarter over time!**

## 🎯 Key Difference from Passive Learning

| Feature | CORE solve_coding_task | BONUS passive_learn |
|---------|----------------------|---------------------|
| **Purpose** | Solve complex tasks with reasoning | Capture Q&A passively |
| **Process** | Iterative think-eval-refine | Simple store |
| **Memory use** | Retrieves & applies memories | Just stores |
| **Quality** | Judges & scores solutions | Auto-accepts if valuable |
| **Iterations** | Multiple refinements | Single pass |
| **MaTTS** | Yes (parallel/sequential) | No |
| **Bug learning** | Full error context | Basic |

## 💡 Recommendation

**Use CORE features for:**
- Complex coding tasks
- Algorithm implementations
- Problem-solving that needs reasoning
- When you want high-quality solutions
- Learning from failures

**Use passive learning for:**
- Quick Q&A capture
- Building knowledge base from conversations
- No active task solving needed

## ✅ Everything Still Works

The CORE ReasoningBank is **unchanged and fully functional**:
- All original features intact
- Supabase storage (upgrade, not replacement)
- Workspace isolation (keeps projects separate)
- Passive learning (optional bonus)

**Your original vision is alive and working!** 🎯
