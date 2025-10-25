# Integrated ReasoningBank System

## 🎯 What You Have Now

**CORE ReasoningBank + Passive Learning = Fully Integrated**

Your system now **automatically captures ALL reasoning** - both from:
1. **Core task solving** (solve_coding_task)
2. **Casual conversations** (passive Q&A)

## 🔄 How It Works

### When You Use CORE `solve_coding_task`:

```
1. Task arrives: "Write a binary search function"
   ↓
2. CORE REASONING BEGINS
   - Retrieves memories
   - Generates solution (iterative/MaTTS)
   - Self-evaluates quality
   - Refines if needed
   - Judges final quality
   - Extracts learnings
   ↓
3. STORAGE (happens twice now!)
   
   A. CORE Storage (existing):
      ✓ Stores as ReasoningTrace
      ✓ Extracts memory items
      ✓ Tags with patterns
      
   B. PASSIVE Learning (NEW - automatic!):
      ✓ Captures entire reasoning process
      ✓ Stores: task + solution + trajectory + score
      ✓ Tags: reasoning_iterative, reasoning_evaluation, etc.
      ✓ Marks as "Core reasoning task" (complex difficulty)
```

### When You Just Chat:

```
User: "What's the time complexity of quicksort?"
AI: "Average O(n log n), worst case O(n²)..."
   ↓
PASSIVE Learning (automatic):
   ✓ Detects: valuable (technical content)
   ✓ Stores to Supabase
   ✓ Marks as "Q&A" (moderate difficulty)
```

## 📊 Data Flow

```
┌─────────────────────────────────────────┐
│  solve_coding_task                      │
│  (Core ReasoningBank)                   │
└─────────────┬───────────────────────────┘
              │
              ├──► CORE Storage
              │    - ReasoningTrace
              │    - Memory extraction
              │    - Pattern tags
              │
              └──► PASSIVE Learning (NEW!)
                   - Full reasoning capture
                   - Reasoning pattern tags
                   - Sequential thinking markers
```

## 🏷️ New Tagging System

Your passive learner now auto-detects reasoning patterns:

| Pattern | Trigger Keywords | Tag Added |
|---------|-----------------|-----------|
| **Iterative** | iteration, refine, improve | `reasoning_iterative` |
| **Sequential** | step, then, next, first | `reasoning_sequential` |
| **Evaluation** | score, quality, assess | `reasoning_evaluation` |
| **Self-correction** | error, fix, correct, debug | `reasoning_self-correction` |
| **Multi-solution** | parallel, alternative, compare | `reasoning_multi-solution` |

## 🎯 Example: Full Integration

### Task: "Write a function to find palindromes"

**Step 1: solve_coding_task starts**
```
✓ Retrieving memories... (2 found)
✓ Generating solution (MaTTS parallel, k=3)
✓ Iteration 1: Quality score 0.7
✓ Iteration 2: Quality score 0.9 
✓ Final judgment: SUCCESS
```

**Step 2: CORE Storage**
```sql
INSERT INTO reasoning_traces (
  task = "Write a function to find palindromes",
  outcome = "success",
  trajectory = [...],
  num_memories = 1
)
```

**Step 3: PASSIVE Learning (automatic!)**
```sql
INSERT INTO memory_items (
  title = "Write a function to find palindromes",
  description = "Core reasoning task: ...",
  content = "Question: ... Answer: [includes full reasoning]",
  pattern_tags = ["python", "algorithm", "reasoning_iterative", "reasoning_evaluation"],
  difficulty_level = "complex",  -- marked as core reasoning
  domain_category = "python"
)
```

**Result:**
- ✅ Stored by CORE ReasoningBank
- ✅ **Also** passively captured with reasoning tags
- ✅ Future queries can find it via semantic search
- ✅ Reasoning patterns indexed for learning

## 🔍 Querying Your Knowledge

### Find Core Reasoning Tasks
```sql
SELECT * FROM memory_items 
WHERE 'reasoning_iterative' = ANY(pattern_tags)
AND difficulty_level = 'complex';
```

### Find Simple Q&A
```sql
SELECT * FROM memory_items 
WHERE difficulty_level = 'moderate'
AND NOT EXISTS (
  SELECT 1 FROM unnest(pattern_tags) t 
  WHERE t LIKE 'reasoning_%'
);
```

### Find Sequential Thinking Examples
```sql
SELECT * FROM memory_items 
WHERE 'reasoning_sequential' = ANY(pattern_tags);
```

## 💡 What This Means

### 1. **Double Learning**
Every core task is now learned **twice**:
- Once by the CORE (structured memory extraction)
- Once by PASSIVE (full context capture)

### 2. **Reasoning Pattern Library**
You're building a library of:
- How problems are solved iteratively
- How solutions are evaluated
- How quality is judged
- How refinements happen

### 3. **Sequential Thinking Capture**
The system now captures:
- Step-by-step reasoning
- Thought processes
- Quality improvements over iterations
- Multi-solution comparisons

### 4. **Rich Retrieval**
Future tasks can retrieve:
- Similar problems
- Similar reasoning approaches
- Similar quality scores
- Similar iteration patterns

## 📈 Benefits

### For CORE solve_coding_task:
✅ Works exactly as before
✅ **Plus** gets passively captured
✅ Reasoning process preserved
✅ No extra work required

### For Users:
✅ Every interaction builds knowledge
✅ Casual Q&A captured automatically
✅ Core reasoning deeply indexed
✅ Workspace isolated (no mixing)

### For Learning:
✅ Learns from successes
✅ Learns from failures
✅ Learns from reasoning processes
✅ Learns from casual discussions

## 🎮 How to Use

### Option 1: Use CORE (Recommended for complex tasks)
```python
# Your AI calls this
solve_coding_task(
    task="Complex algorithm implementation",
    enable_matts=True,
    matts_k=5,
    matts_mode="sequential"  # or "parallel"
)

# Result:
# ✓ Core reasoning executed
# ✓ Memory extracted
# ✓ PASSIVE learning auto-captured
# ✓ Reasoning patterns tagged
```

### Option 2: Just Chat (Automatic)
```
User: "How do I handle errors in Python?"
AI: [Explains exception handling]

# Behind the scenes:
# ✓ Passive learning auto-captures
# ✓ Stores if valuable
# ✓ Tags with patterns
```

### Option 3: Manual Passive Learning
```python
# Your AI can explicitly call this
passive_learn(
    question="What is dependency injection?",
    answer="[Full explanation]",
    force=True
)
```

## 🔧 Configuration

### Current Settings:

**Passive Learning:**
- ✅ Enabled by default
- ✅ Auto-store: True
- ✅ Min length: 100 characters
- ✅ Integrated with CORE

**Workspace Isolation:**
- ✅ Auto-detects from directory
- ✅ Each project isolated
- ✅ Zero cross-contamination

**Storage:**
- ✅ Supabase cloud
- ✅ pgvector semantic search
- ✅ Workspace-scoped queries

## 🎯 Summary

**What you asked for:**
> "I want passive learning on by default even with the main core for sequential thinking as well"

**What you got:**
✅ Passive learning **integrated** with core solve_coding_task
✅ Auto-captures **all reasoning processes**
✅ Tags **sequential thinking patterns**
✅ Marks core tasks as **"complex"** vs casual Q&A as **"moderate"**
✅ Stores **full trajectories** including iterations and scores
✅ **Zero configuration needed** - works automatically

**Every time you use solve_coding_task:**
1. CORE does its job (memory-guided reasoning)
2. PASSIVE **automatically** captures the entire process
3. Both stored to Supabase with workspace isolation
4. Reasoning patterns tagged for future retrieval

**You're building a knowledge base of:**
- ✅ Solutions
- ✅ Reasoning processes
- ✅ Quality judgments
- ✅ Iterative improvements
- ✅ Sequential thinking steps
- ✅ Error patterns
- ✅ Success patterns

**Everything you do makes the system smarter!** 🧠🎯
