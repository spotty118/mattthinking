# Reasoning Capture System

## 🧠 What You Have Now

Your ReasoningBank **automatically detects and captures ALL types of reasoning** in conversations - not just code, but logical thinking, analysis, problem-solving, and decision-making.

## 🎯 Reasoning Patterns Detected

### 1. **Logical Reasoning**
Detects: `because`, `therefore`, `thus`, `hence`, `as a result`

**Example:**
```
Q: "Why use async/await in JavaScript?"
A: "Because it makes asynchronous code easier to read. Therefore, 
   you can avoid callback hell and write cleaner code."

✓ Tagged: reasoning_logical
✓ Stored: Captures the causal reasoning
```

### 2. **Analytical Thinking**
Detects: `analyze`, `examine`, `consider`, `break down`

**Example:**
```
Q: "How should I structure this API?"
A: "Let's analyze the requirements. Consider the data flow, 
   examine the security needs, and break down the endpoints..."

✓ Tagged: reasoning_analytical
✓ Stored: Captures the analytical approach
```

### 3. **Sequential Thinking**
Detects: `first`, `then`, `next`, `finally`, `step by step`

**Example:**
```
Q: "How do I deploy this?"
A: "First, build the image. Then, push to registry. 
   Next, update the deployment. Finally, verify it's running."

✓ Tagged: reasoning_sequential
✓ Stored: Captures the step-by-step process
```

### 4. **Causal Reasoning**
Detects: `causes`, `leads to`, `results in`, `due to`

**Example:**
```
Q: "Why is my app slow?"
A: "Large bundle size causes slow load times. This leads to 
   poor user experience, which results in higher bounce rates."

✓ Tagged: reasoning_causal
✓ Stored: Captures cause-effect chains
```

### 5. **Problem-Solving**
Detects: `solution`, `solve`, `address`, `resolve`, `handle`

**Example:**
```
Q: "How do I handle this edge case?"
A: "The solution is to add validation. This solves the null 
   pointer issue and addresses the edge case properly."

✓ Tagged: reasoning_problem-solving
✓ Stored: Captures solution approach
```

### 6. **Decision-Making**
Detects: `choose`, `decide`, `option`, `tradeoff`, `pros and cons`

**Example:**
```
Q: "Should I use REST or GraphQL?"
A: "Let's consider the tradeoffs. REST is simpler but GraphQL 
   gives more flexibility. The decision depends on your use case."

✓ Tagged: reasoning_decision-making
✓ Stored: Captures decision process
```

### 7. **Deductive Reasoning**
Detects: `conclude`, `infer`, `deduce`, `implies`, `suggests`

**Example:**
```
Q: "What does this error mean?"
A: "The stack trace suggests a null reference. This implies the 
   object wasn't initialized. We can conclude the constructor failed."

✓ Tagged: reasoning_deductive
✓ Stored: Captures inference chain
```

### 8. **Comparative Analysis**
Detects: `compare`, `contrast`, `versus`, `different`, `similar`

**Example:**
```
Q: "Redis vs PostgreSQL for caching?"
A: "Let's compare them. Redis is faster for caching but PostgreSQL 
   offers more features. The contrast shows different use cases."

✓ Tagged: reasoning_comparative
✓ Stored: Captures comparison logic
```

### 9. **Strategic Thinking**
Detects: `strategy`, `plan`, `approach`, `method`, `technique`

**Example:**
```
Q: "How should we scale this?"
A: "The strategy is to use horizontal scaling. This approach 
   handles traffic spikes better than the alternative method."

✓ Tagged: reasoning_strategic
✓ Stored: Captures strategic planning
```

### 10. **Conceptual Understanding**
Detects: `concept`, `principle`, `theory`, `idea`, `notion`

**Example:**
```
Q: "Explain dependency injection"
A: "The core concept is inversion of control. This principle 
   allows loose coupling. The idea is to inject dependencies..."

✓ Tagged: reasoning_conceptual
✓ Stored: Captures conceptual explanation
```

## 📊 Difficulty Assessment

The system now automatically classifies difficulty based on reasoning complexity:

| Difficulty | Criteria | Example |
|-----------|----------|---------|
| **Complex** | 3+ reasoning patterns OR core task | Multi-step solution with analysis |
| **Moderate** | 1-2 reasoning patterns | Explanation with some logic |
| **Simple** | No reasoning patterns | Basic factual Q&A |

## 🎮 Examples of What Gets Captured

### Example 1: Pure Reasoning (No Code)

```
Q: "Why is microservices architecture popular?"

A: "Let's analyze this. First, microservices allow independent scaling, 
   which leads to better resource utilization. Second, they enable team 
   autonomy, because different teams can work on different services. 
   Therefore, development velocity increases. However, the tradeoff is 
   added complexity in orchestration."

Captured:
✓ reasoning_analytical ("analyze")
✓ reasoning_sequential ("first", "second")
✓ reasoning_causal ("leads to", "because")  
✓ reasoning_logical ("therefore")
✓ reasoning_decision-making ("tradeoff")

Difficulty: Complex (5 reasoning patterns)
Description: "Reasoning: analytical, sequential"
```

### Example 2: Problem-Solving with Steps

```
Q: "How do I fix this memory leak?"

A: "First, identify where objects are retained. Then, examine the 
   reference chain. This approach helps you find the root cause. 
   The solution is to break circular references."

Captured:
✓ reasoning_sequential ("first", "then")
✓ reasoning_problem-solving ("fix", "solution")
✓ reasoning_strategic ("approach")
✓ reasoning_causal ("root cause")

Difficulty: Complex (4 reasoning patterns)
```

### Example 3: Decision with Tradeoffs

```
Q: "Should I use TypeScript?"

A: "Consider the pros and cons. TypeScript provides type safety, 
   which prevents many bugs. However, it adds compilation overhead. 
   The decision depends on project size - larger projects benefit more."

Captured:
✓ reasoning_decision-making ("pros and cons", "decision")
✓ reasoning_analytical ("consider")
✓ reasoning_causal ("prevents", "depends on")
✓ reasoning_comparative ("larger projects")

Difficulty: Complex (4 reasoning patterns)
```

### Example 4: Simple Factual

```
Q: "What port does HTTP use?"
A: "HTTP uses port 80."

Captured:
✗ No reasoning patterns

Difficulty: Simple
NOT stored (too basic)
```

## 🔄 What Happens Automatically

### During Conversations:

```
User asks question
    ↓
AI responds
    ↓
Passive Learner analyzes:
  ├─ Detects reasoning indicators
  ├─ Identifies reasoning patterns
  ├─ Counts pattern occurrences
  ├─ Assesses complexity
  └─ Determines if valuable
    ↓
If valuable:
  ├─ Extracts all reasoning tags
  ├─ Categorizes difficulty
  ├─ Generates description with reasoning types
  └─ Stores to Supabase with workspace_id
```

## 📈 Complexity Scoring

**Simple (not stored):**
- Factual questions
- No reasoning patterns
- Example: "What is X?"

**Moderate (stored):**
- 1-2 reasoning patterns
- Some explanation
- Example: "X is used because Y"

**Complex (stored, prioritized):**
- 3+ reasoning patterns
- Deep analysis
- Multiple perspectives
- Core reasoning tasks
- Example: Multi-step analysis with tradeoffs

## 🎯 Query Your Reasoning Library

### Find Logical Reasoning
```sql
SELECT * FROM memory_items 
WHERE 'reasoning_logical' = ANY(pattern_tags);
```

### Find Sequential Thinking Examples
```sql
SELECT * FROM memory_items 
WHERE 'reasoning_sequential' = ANY(pattern_tags);
```

### Find Complex Reasoning
```sql
SELECT * FROM memory_items 
WHERE difficulty_level = 'complex'
AND array_length(
  ARRAY(SELECT unnest(pattern_tags) WHERE unnest LIKE 'reasoning_%'), 
  1
) >= 3;
```

### Find Problem-Solving Patterns
```sql
SELECT title, pattern_tags, difficulty_level
FROM memory_items 
WHERE 'reasoning_problem-solving' = ANY(pattern_tags)
ORDER BY created_at DESC;
```

## 💡 Real-World Use Cases

### Use Case 1: Learning from Discussions

**Scenario:** Discussing architecture decisions

```
You: "Why choose event-driven architecture?"
AI: [Explains with reasoning about scalability, decoupling, etc.]

✓ Automatically captured
✓ Tagged: reasoning_logical, reasoning_causal, reasoning_strategic
✓ Available for future: "How to design scalable systems?"
```

### Use Case 2: Debugging Conversations

```
You: "Why is this failing?"
AI: "The error suggests X, which implies Y, therefore the solution is Z"

✓ Automatically captured  
✓ Tagged: reasoning_deductive, reasoning_causal, reasoning_problem-solving
✓ Available for similar debugging sessions
```

### Use Case 3: Design Discussions

```
You: "Compare approach A vs B"
AI: [Analyzes tradeoffs, pros/cons, different scenarios]

✓ Automatically captured
✓ Tagged: reasoning_comparative, reasoning_analytical, reasoning_decision-making
✓ Available for future design decisions
```

## 🎊 What This Means

**Every conversation that involves reasoning is now captured:**

✅ Logical arguments
✅ Analytical breakdowns
✅ Sequential processes  
✅ Cause-effect relationships
✅ Problem-solving approaches
✅ Decision-making logic
✅ Deductive inferences
✅ Comparisons and contrasts
✅ Strategic planning
✅ Conceptual explanations

**You're building a reasoning library that captures:**
- HOW problems are analyzed
- WHY decisions are made
- WHAT steps are taken
- WHICH approaches work
- WHEN tradeoffs matter

## 📊 Summary

| Feature | Status |
|---------|--------|
| Logical reasoning capture | ✅ Active |
| Analytical thinking capture | ✅ Active |
| Sequential process capture | ✅ Active |
| Causal chain capture | ✅ Active |
| Problem-solving capture | ✅ Active |
| Decision logic capture | ✅ Active |
| Deductive inference capture | ✅ Active |
| Comparative analysis capture | ✅ Active |
| Strategic planning capture | ✅ Active |
| Conceptual explanation capture | ✅ Active |
| Automatic difficulty assessment | ✅ Active |
| Workspace isolation | ✅ Active |
| Supabase cloud storage | ✅ Active |

**Your ReasoningBank now captures the THINKING behind the answers, not just the answers themselves!** 🧠✨
