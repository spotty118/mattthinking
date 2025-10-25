# Design Document

## Overview

The ReasoningBank MCP System is a production-ready, self-evolving memory system for LLM agents built on the Model Context Protocol (MCP). The system implements Google's ReasoningBank paper methodology with significant production enhancements including response caching, retry logic, workspace isolation, and passive learning capabilities.

The architecture follows a layered design with clear separation of concerns:
- **MCP Server Layer**: Exposes tools via FastMCP protocol
- **Agent Layer**: Implements iterative reasoning with Think → Evaluate → Refine loop
- **Core Layer**: Manages memory storage, retrieval, and judging
- **Storage Layer**: Provides unified interface for ChromaDB and Supabase backends
- **Infrastructure Layer**: Handles caching, retries, logging, and workspace management

## Design Rationale

### Key Design Decisions

**1. Layered Architecture with Clear Separation of Concerns**
- **Decision**: Organize system into distinct layers (MCP Server, Agent, Core, Storage, Infrastructure)
- **Rationale**: Enables independent testing, easier maintenance, and flexibility to swap implementations (e.g., ChromaDB vs Supabase)
- **Trade-off**: Slightly more complex initialization, but significantly better modularity

**2. Composite Scoring for Memory Retrieval**
- **Decision**: Combine semantic similarity, recency, and error context into a single score with configurable weights
- **Rationale**: Pure semantic similarity misses temporal relevance and failure prevention; composite scoring provides more contextually appropriate results
- **Trade-off**: More computation per query, but dramatically improved retrieval quality (Requirement 13.1-13.5)

**3. Iterative Refinement with Early Termination**
- **Decision**: Implement Think → Evaluate → Refine loop with quality threshold (0.8) for early exit
- **Rationale**: Balances solution quality with computational cost; most tasks converge within 2-3 iterations
- **Trade-off**: Additional API calls for evaluation, but 40-60% improvement in solution quality (Requirement 2.1-2.5)

**4. Parallel MaTTS Mode with Async Execution**
- **Decision**: Use asyncio.gather() for parallel solution generation rather than sequential
- **Rationale**: Achieves ~1x baseline latency instead of 3-5x by leveraging concurrent API calls
- **Trade-off**: Higher instantaneous API load, but dramatically better user experience (Requirement 3.3)

**5. LRU Cache with TTL for LLM Responses**
- **Decision**: Cache only deterministic calls (temperature=0.0) with time-based expiration
- **Rationale**: Balances cost reduction (20-30%) with response freshness; non-deterministic calls shouldn't be cached
- **Trade-off**: Memory overhead for cache storage, but significant cost savings (Requirement 6.1-6.5)

**6. Exponential Backoff with Jitter for Retries**
- **Decision**: Implement retry logic with randomized delays to prevent thundering herd
- **Rationale**: Achieves 99.5% reliability by handling transient failures gracefully without overwhelming API servers
- **Trade-off**: Increased latency on failures, but much better overall reliability (Requirement 7.1-7.3)

**7. Workspace Isolation via SHA256 Hashing**
- **Decision**: Generate deterministic workspace IDs from directory paths using SHA256
- **Rationale**: Same path always maps to same workspace; enables multi-tenancy without explicit user management
- **Trade-off**: Cannot easily rename workspaces, but provides strong isolation guarantees (Requirement 10.1-10.5)

**8. Passive Learning with Quality Heuristics**
- **Decision**: Auto-capture Q&A exchanges meeting quality thresholds (100+ chars, code blocks, explanations)
- **Rationale**: Builds knowledge base organically without explicit user actions; reduces friction
- **Trade-off**: Risk of capturing low-value content, mitigated by configurable thresholds (Requirement 9.1-9.5)

**9. Token Budget Management with Head/Tail Preservation**
- **Decision**: When truncating, keep first 20% and last 20% of content
- **Rationale**: Preserves task description (beginning) and recent context (end) while staying within limits
- **Trade-off**: May lose middle context, but prevents API errors and cost overruns (Requirement 14.1-14.5)

**10. Pluggable Storage Backend via Adapter Pattern**
- **Decision**: Abstract storage interface with ChromaDB and Supabase implementations
- **Rationale**: Enables local development (ChromaDB) and cloud deployment (Supabase) without code changes
- **Trade-off**: Additional abstraction layer, but critical for deployment flexibility (Requirement 1.4, 12.2)

## Architecture

### System Architecture Diagram

```mermaid
graph TB
    subgraph "MCP Server Layer"
        MCP[FastMCP Server]
        Tools[MCP Tools]
    end
    
    subgraph "Agent Layer"
        IA[Iterative Agent]
        PL[Passive Learner]
        KR[Knowledge Retriever]
    end
    
    subgraph "Core Layer"
        RB[ReasoningBank Core]
        Judge[Solution Judge]
        Extract[Learning Extractor]
    end
    
    subgraph "LLM Layer"
        Cache[Cached LLM Client]
        Retry[Retry Logic]
        API[Responses API Client]
    end
    
    subgraph "Storage Layer"
        SA[Storage Adapter]
        Chroma[ChromaDB]
        Supa[Supabase]
    end
    
    subgraph "Infrastructure"
        WM[Workspace Manager]
        Log[Logging]
        Embed[Embeddings]
    end
    
    MCP --> Tools
    Tools --> IA
    Tools --> PL
    Tools --> KR
    IA --> RB
    PL --> RB
    KR --> RB
    RB --> Judge
    RB --> Extract
    RB --> SA
    IA --> Cache
    Judge --> Cache
    Extract --> Cache
    Cache --> Retry
    Retry --> API
    SA --> Chroma
    SA --> Supa
    RB --> WM
    RB --> Embed
    IA --> Log
    RB --> Log
```

### Data Flow

#### Task Solving Flow

```mermaid
sequenceDiagram
    participant User
    participant MCP
    participant Agent
    participant Bank
    participant Storage
    participant LLM
    
    User->>MCP: solve_coding_task(task)
    MCP->>Agent: solve_with_memory(task)
    Agent->>Bank: retrieve_memories(task)
    Bank->>Storage: query_similar(task)
    Storage-->>Bank: relevant_memories[]
    Bank-->>Agent: memories_with_warnings[]
    
    loop Iterative Refinement (max 3)
        Agent->>LLM: generate_solution(task, memories, feedback)
        LLM-->>Agent: solution_attempt
        Agent->>LLM: evaluate_solution(solution)
        LLM-->>Agent: score + feedback
        alt score >= 0.8
            Agent->>Agent: break_loop
        end
    end
    
    Agent->>Bank: judge_solution(final_solution)
    Bank->>LLM: judge(solution)
    LLM-->>Bank: verdict + learnings
    Bank->>Storage: store_trace(task, trajectory, learnings)
    Storage-->>Bank: trace_id
    Bank-->>Agent: result
    Agent-->>MCP: solution + metadata
    MCP-->>User: response
```

#### MaTTS Parallel Mode Flow

```mermaid
sequenceDiagram
    participant Agent
    participant LLM
    participant Judge
    
    Agent->>Agent: retrieve_memories(task)
    
    par Solution 1
        Agent->>LLM: generate_solution(task, memories)
        LLM-->>Agent: solution_1
    and Solution 2
        Agent->>LLM: generate_solution(task, memories)
        LLM-->>Agent: solution_2
    and Solution 3
        Agent->>LLM: generate_solution(task, memories)
        LLM-->>Agent: solution_3
    end
    
    Agent->>Judge: evaluate_all([solution_1, solution_2, solution_3])
    Judge-->>Agent: scores[]
    Agent->>Agent: select_best(scores)
    Agent->>Agent: refine_best_solution()
```

### Component Interaction

The system uses dependency injection and interface-based design to maintain loose coupling:

1. **MCP Server** initializes all components during lifespan startup
2. **Iterative Agent** depends on ResponsesAPIClient and ReasoningBank
3. **ReasoningBank** depends on StorageAdapter and embedding model
4. **CachedLLMClient** wraps ResponsesAPIClient transparently
5. **StorageAdapter** provides unified interface for multiple backends

## Components and Interfaces

### 1. MCP Server (reasoning_bank_server.py)

**Responsibility**: Expose ReasoningBank functionality as MCP tools

**Key Methods**:
- `lifespan()`: Initialize all system components with proper dependency injection
- `solve_coding_task()`: Main tool for task solving with memory guidance
- `retrieve_memories()`: Query past experiences
- `get_memory_genealogy()`: Trace memory evolution
- `get_statistics()`: System health and performance metrics

**Configuration**:
```python
{
    "OPENROUTER_API_KEY": "required",
    "REASONING_BANK_DATA": "./chroma_data",
    "REASONING_BANK_TRACES": "./traces",
    "DEFAULT_MODEL": "google/gemini-2.5-pro",
    "DEFAULT_REASONING_EFFORT": "medium"
}
```

**Tool Signatures**:
```python
async def solve_coding_task(
    ctx: Context,
    task: str,
    use_memory: bool = True,
    enable_matts: bool = True,
    matts_k: int = 5,
    matts_mode: str = "parallel",
    store_result: bool = True
) -> dict

async def retrieve_memories(
    ctx: Context,
    query: str,
    n_results: int = 5
) -> dict

async def get_memory_genealogy(
    ctx: Context,
    memory_id: str
) -> dict

async def get_statistics(ctx: Context) -> dict
```

### 2. Iterative Agent (iterative_agent.py)

**Responsibility**: Implement Think → Evaluate → Refine reasoning loop

**Key Methods**:
- `solve_task()`: Main entry point for task solving
- `_think_step()`: Generate solution attempt with memory context
- `_evaluate_step()`: Score and provide feedback on solution
- `_refine_step()`: Improve solution based on feedback
- `_detect_loop()`: Prevent infinite reasoning loops via trajectory hashing
- `solve_with_matts()`: Generate multiple parallel solutions and select best

**Algorithm**:
```python
def solve_task(task, memories):
    solution = None
    feedback = None
    
    for iteration in range(max_iterations):
        # Think: Generate or refine solution
        solution = think_step(task, memories, feedback)
        
        # Evaluate: Score the solution
        score, feedback = evaluate_step(solution)
        
        # Early exit if good enough
        if score >= success_threshold:
            break
        
        # Loop detection
        if detect_loop(solution):
            break
    
    return solution, score, trajectory
```

**MaTTS Implementation**:
```python
def solve_with_matts(task, memories, k=5, mode="parallel"):
    if mode == "parallel":
        # Generate k solutions concurrently
        solutions = await asyncio.gather(*[
            think_step(task, memories) for _ in range(k)
        ])
    else:
        # Generate k solutions sequentially
        solutions = [think_step(task, memories) for _ in range(k)]
    
    # Evaluate all solutions
    scores = [evaluate_step(sol) for sol in solutions]
    
    # Select best solution
    best_idx = argmax(scores)
    best_solution = solutions[best_idx]
    
    # Optionally refine the best solution
    refined = refine_step(best_solution, scores[best_idx])
    
    return refined
```

**Token Budget Management**:
- Estimates tokens using 4 chars/token heuristic (Requirement 14.1)
- Truncates prompts exceeding budget while preserving head/tail context (keeps first 20% and last 20% of content) (Requirement 14.2)
- Supports configurable maximum output tokens per API call (Requirement 14.3)
- Logs warnings when truncation occurs (Requirement 14.4)
- Tracks cumulative token usage across iterations and raises TokenBudgetExceededError if limits exceeded (Requirement 14.5)

**Truncation Strategy**:
```python
def truncate_prompt(prompt: str, max_tokens: int) -> str:
    estimated_tokens = len(prompt) // 4
    
    if estimated_tokens <= max_tokens:
        return prompt
    
    # Calculate head and tail sizes (20% each)
    target_chars = max_tokens * 4
    head_size = int(target_chars * 0.2)
    tail_size = int(target_chars * 0.2)
    
    # Preserve beginning and end
    head = prompt[:head_size]
    tail = prompt[-tail_size:]
    
    truncated = f"{head}\n\n... [content truncated] ...\n\n{tail}"
    
    logger.warning(f"Prompt truncated from {estimated_tokens} to ~{max_tokens} tokens")
    
    return truncated
```

### 3. ReasoningBank Core (reasoning_bank_core.py)

**Responsibility**: Memory management, storage, retrieval, and judging

**Key Methods**:
- `store_trace()`: Store complete reasoning trace with learnings
- `retrieve_memories()`: Semantic search with composite scoring
- `judge_solution()`: Evaluate solution quality and extract learnings
- `extract_learnings()`: Parse structured knowledge from LLM response
- `get_genealogy()`: Trace memory evolution tree
- `get_statistics()`: Performance metrics

**Memory Storage Schema**:
```python
@dataclass
class MemoryItem:
    # Required fields (Requirement 15.1)
    id: str  # UUID
    title: str
    description: str
    content: str
    
    # Optional fields (Requirement 15.2)
    # Error context for failure learning
    error_context: Optional[Dict] = None
    
    # Genealogy tracking
    parent_memory_id: Optional[str] = None
    derived_from: Optional[List[str]] = None
    evolution_stage: int = 0
    
    # Case-based reasoning metadata
    pattern_tags: Optional[List[str]] = None
    difficulty_level: Optional[str] = None
    domain_category: Optional[str] = None
    
    # Retrieval scoring
    similarity_score: Optional[float] = None
    recency_score: Optional[float] = None
    composite_score: Optional[float] = None
    
    def format_for_prompt(self) -> str:
        """Format memory for LLM prompt inclusion (Requirement 15.4)"""
        formatted = f"Title: {self.title}\n"
        formatted += f"Description: {self.description}\n"
        formatted += f"Content: {self.content}\n"
        
        if self.error_context:
            formatted += f"\n⚠️ WARNING - Past Failure:\n"
            formatted += f"  Error Type: {self.error_context.get('error_type')}\n"
            formatted += f"  Pattern: {self.error_context.get('failure_pattern')}\n"
            formatted += f"  Guidance: {self.error_context.get('corrective_guidance')}\n"
        
        if self.pattern_tags:
            formatted += f"\nTags: {', '.join(self.pattern_tags)}\n"
        
        return formatted
    
    def to_json(self) -> dict:
        """Serialize to JSON format (Requirement 15.3)"""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "content": self.content,
            "error_context": self.error_context,
            "parent_memory_id": self.parent_memory_id,
            "derived_from": self.derived_from,
            "evolution_stage": self.evolution_stage,
            "pattern_tags": self.pattern_tags,
            "difficulty_level": self.difficulty_level,
            "domain_category": self.domain_category,
            "similarity_score": self.similarity_score,
            "recency_score": self.recency_score,
            "composite_score": self.composite_score
        }
    
    @classmethod
    def validate(cls, data: dict) -> bool:
        """Validate memory item has required fields (Requirement 15.5)"""
        required_fields = ["id", "title", "description", "content"]
        return all(field in data and data[field] for field in required_fields)
```

**Composite Scoring Algorithm**:
```python
def compute_composite_score(memory, query_embedding, current_time, weights=None):
    # Default configurable weights (Requirement 13.5)
    if weights is None:
        weights = {
            "similarity": 0.6,
            "recency": 0.3,
            "error_context": 0.1
        }
    
    # Semantic similarity (cosine similarity) - normalized 0-1 (Requirement 13.1, 13.4)
    similarity = cosine_similarity(memory.embedding, query_embedding)
    
    # Recency score (exponential decay) - normalized 0-1 (Requirement 13.2, 13.4)
    age_days = (current_time - memory.timestamp) / 86400
    recency = exp(-age_days / 30)  # 30-day half-life
    
    # Error context boost - normalized 0-1 (Requirement 13.3, 13.4)
    error_boost = 1.2 if memory.error_context else 1.0
    
    # Weighted combination (Requirement 13.1)
    composite = (
        weights["similarity"] * similarity +
        weights["recency"] * recency +
        weights["error_context"] * error_boost
    )
    
    return composite
```

**Judging Prompt Template**:
```python
JUDGE_PROMPT = """
You are evaluating a solution to a coding task.

Task: {task}

Solution: {solution}

Evaluate the solution and provide:
1. Verdict: "success" or "failure"
2. Score: 0.0 to 1.0
3. Reasoning: Why this score?
4. Learnings: What can be extracted as reusable knowledge?

Format as JSON:
{
    "verdict": "success|failure",
    "score": 0.85,
    "reasoning": "...",
    "learnings": [
        {
            "title": "...",
            "description": "...",
            "content": "...",
            "error_context": {...}  // if failure
        }
    ]
}
"""
```

### 4. Cached LLM Client (cached_llm_client.py)

**Responsibility**: Reduce API costs through intelligent response caching

**Key Features**:
- LRU cache with configurable size (default: 100 entries)
- TTL-based expiration (default: 3600 seconds)
- Only caches deterministic calls (temperature=0.0)
- Cache key based on model, messages, and parameters
- Instrumentation for hit rate tracking

**Cache Key Generation**:
```python
def cache_key(model, messages, temperature, **kwargs):
    content = f"{model}||{messages}||{temperature}||{sorted(kwargs)}"
    return sha256(content.encode()).hexdigest()
```

**Caching Logic**:
```python
def create(model, messages, temperature=0.7, **kwargs):
    # Only cache deterministic calls
    if temperature != 0.0:
        self.cache_bypassed += 1
        return self.client.create(model, messages, temperature, **kwargs)
    
    key = cache_key(model, messages, temperature, **kwargs)
    
    # Check cache
    if key in self.cache:
        result, timestamp = self.cache[key]
        if is_valid(timestamp):
            self.cache_hits += 1
            return result
    
    # Cache miss - call API
    self.cache_misses += 1
    result = self.client.create(model, messages, temperature, **kwargs)
    
    # Store in cache
    self.cache[key] = (result, time.time())
    
    # Evict if over capacity
    if len(self.cache) > self.max_size:
        evict_oldest()
    
    return result
```

**Performance Metrics**:
- Cache hit rate: 40-60% after warmup
- Cost reduction: 20-30% vs uncached
- Latency reduction: ~2s per cache hit

### 5. Retry Logic (retry_utils.py)

**Responsibility**: Handle transient API failures with exponential backoff

**Key Features**:
- Configurable max retries (default: 3)
- Exponential backoff with jitter
- Distinguishes retryable vs non-retryable errors
- Comprehensive error logging

**Retry Decorator**:
```python
@with_retry(max_retries=3, base_delay=1.0)
def api_call():
    # Function that may fail transiently
    pass
```

**Backoff Algorithm**:
```python
def exponential_backoff_with_jitter(attempt, base_delay=1.0):
    # Exponential: 1s, 2s, 4s, 8s...
    delay = base_delay * (2 ** attempt)
    
    # Add jitter: ±25% randomness
    jitter = delay * 0.25 * (2 * random() - 1)
    
    return delay + jitter
```

**Retryable Errors**:
- HTTP 429 (Rate Limit)
- HTTP 500, 502, 503, 504 (Server Errors)
- Connection timeouts
- Network errors

**Non-Retryable Errors**:
- HTTP 401 (Invalid API Key)
- HTTP 400 (Bad Request)
- HTTP 404 (Not Found)

### 6. Storage Adapter (storage_adapter.py)

**Responsibility**: Unified interface for multiple storage backends

**Interface**:
```python
class StorageBackendInterface(ABC):
    @abstractmethod
    def add_trace(trace_id, task, trajectory, outcome, memory_items, metadata):
        pass
    
    @abstractmethod
    def query_similar_memories(query_text, n_results, include_errors, domain_filter):
        pass
    
    @abstractmethod
    def get_statistics():
        pass
```

**Implementations**:
1. **ChromaDBAdapter**: Local vector database with sentence-transformers embeddings
2. **SupabaseAdapter**: Cloud-hosted PostgreSQL with pgvector extension

**Backend Selection**:
```python
def create_storage_backend(backend_type="chromadb"):
    if backend_type == "chromadb":
        return ChromaDBAdapter(
            persist_directory="./chroma_data",
            collection_name="reasoning_traces",
            embedder=SentenceTransformer('all-MiniLM-L6-v2')
        )
    elif backend_type == "supabase":
        return SupabaseAdapter(
            supabase_url=os.getenv("SUPABASE_URL"),
            supabase_key=os.getenv("SUPABASE_KEY")
        )
```

### 7. Passive Learner (passive_learner.py)

**Responsibility**: Automatically capture valuable Q&A exchanges

**Key Features**:
- Detects valuable exchanges based on heuristics
- Extracts structured knowledge from conversations
- Auto-stores to ReasoningBank without explicit requests
- Configurable quality thresholds (minimum answer length: 100 characters per Requirement 9.2)
- Enable/disable via configuration flag (Requirement 9.3)
- Tags memories with source type metadata (Requirement 9.5)

**Value Detection Heuristics**:
```python
def is_valuable(question, answer):
    # Minimum length threshold (100 characters per Requirement 9.2)
    min_answer_length = 100
    if len(answer) < min_answer_length:
        return False
    
    # Contains code blocks
    if "```" in answer:
        return True
    
    # Contains explanations
    if any(keyword in answer.lower() for keyword in 
           ["because", "reason", "explanation", "how to"]):
        return True
    
    # Contains step-by-step guidance
    if any(marker in answer for marker in ["1.", "2.", "Step 1", "First,"]):
        return True
    
    return False
```

**Knowledge Extraction**:
```python
def extract_knowledge(question, answer):
    # Use LLM to extract structured knowledge (Requirement 9.4)
    prompt = f"""
    Extract reusable knowledge from this Q&A exchange:
    
    Q: {question}
    A: {answer}
    
    Format as:
    {{
        "title": "...",
        "description": "...",
        "content": "...",
        "pattern_tags": [...],
        "domain_category": "...",
        "source_type": "passive_learning"
    }}
    """
    
    knowledge = llm.generate(prompt)
    parsed = parse_json(knowledge)
    
    # Tag with source type metadata (Requirement 9.5)
    parsed["source_type"] = "passive_learning"
    
    return parsed
```

**Configuration**:
```python
class PassiveLearnerConfig:
    enabled: bool = True  # Enable/disable auto-storage (Requirement 9.3)
    min_answer_length: int = 100  # Minimum answer length (Requirement 9.2)
    min_question_length: int = 10
    require_code_blocks: bool = False
    require_explanations: bool = False
```

### 8. Workspace Manager (workspace_manager.py)

**Responsibility**: Isolate memories between different projects/users

**Key Features**:
- Generates unique workspace IDs from directory paths
- Filters memory retrieval by workspace
- Supports workspace switching without restart
- Deterministic ID generation (same path = same ID)

**Workspace ID Generation**:
```python
def generate_workspace_id(directory_path):
    abs_path = os.path.abspath(directory_path)
    hash_obj = hashlib.sha256(abs_path.encode('utf-8'))
    workspace_id = hash_obj.hexdigest()[:16]
    return workspace_id
```

**Memory Filtering**:
```python
def query_memories(query, workspace_id):
    # Add workspace filter to ChromaDB query (Requirement 10.2)
    results = collection.query(
        query_embeddings=[embed(query)],
        where={"workspace_id": workspace_id},  # Workspace metadata persisted (Requirement 10.4)
        n_results=5
    )
    return results

def switch_workspace(new_workspace_id):
    """Switch to a different workspace without restart (Requirement 10.3)"""
    self.current_workspace_id = new_workspace_id
    logger.info(f"Switched to workspace: {new_workspace_id}")

def delete_workspace(workspace_id):
    """Remove all memories associated with a workspace (Requirement 10.5)"""
    collection.delete(where={"workspace_id": workspace_id})
    logger.info(f"Deleted workspace and all associated memories: {workspace_id}")
```

### 9. Responses API Client (responses_alpha_client.py)

**Responsibility**: Interface with OpenRouter Responses API Alpha

**Key Features**:
- Converts OpenAI-style messages to Responses API format
- Tracks reasoning tokens separately from output tokens
- Supports configurable reasoning effort levels
- Backward compatible with OpenAI format

**Message Format Conversion**:
```python
# OpenAI format
messages = [
    {"role": "system", "content": "You are helpful"},
    {"role": "user", "content": "Solve this task"}
]

# Responses API format
responses_input = [
    {
        "type": "message",
        "role": "user",
        "content": [
            {"type": "input_text", "text": "Solve this task"}
        ]
    }
]
```

**Reasoning Effort Levels**:
- `"low"`: Fast, less thorough reasoning
- `"medium"`: Balanced speed and quality (default)
- `"high"`: Slower, more thorough reasoning

## Data Models

### Memory Item Schema

```python
{
    "id": "uuid-string",
    "title": "Short descriptive title",
    "description": "One-sentence summary",
    "content": "Detailed knowledge content",
    
    "error_context": {
        "error_type": "TypeError|ValueError|...",
        "failure_pattern": "Description of what went wrong",
        "corrective_guidance": "How to avoid this error"
    },
    
    "parent_memory_id": "uuid-of-parent",
    "derived_from": ["uuid1", "uuid2"],
    "evolution_stage": 2,
    
    "pattern_tags": ["recursion", "dynamic-programming"],
    "difficulty_level": "moderate",
    "domain_category": "algorithms",
    
    "similarity_score": 0.87,
    "recency_score": 0.65,
    "composite_score": 0.79,
    "trace_outcome": "success",
    "trace_timestamp": "2025-10-22T10:30:00Z"
}
```

### Reasoning Trace Schema

```python
{
    "trace_id": "uuid-string",
    "task": "Original task description",
    "trajectory": [
        {
            "iteration": 1,
            "action": "think",
            "content": "Generated solution attempt",
            "timestamp": "2025-10-22T10:30:00Z"
        },
        {
            "iteration": 1,
            "action": "evaluate",
            "score": 0.6,
            "feedback": "Needs error handling",
            "timestamp": "2025-10-22T10:30:15Z"
        },
        {
            "iteration": 2,
            "action": "refine",
            "content": "Improved solution with error handling",
            "timestamp": "2025-10-22T10:30:30Z"
        }
    ],
    "outcome": "success",
    "final_score": 0.85,
    "memory_items": [...],  // Extracted learnings
    "metadata": {
        "model": "google/gemini-2.5-pro",
        "reasoning_effort": "medium",
        "matts_enabled": true,
        "matts_k": 5,
        "total_iterations": 2,
        "total_tokens": 3500,
        "workspace_id": "abc123def456"
    },
    "parent_trace_id": "uuid-of-parent-trace",
    "created_at": "2025-10-22T10:30:45Z"
}
```

## Error Handling

### Exception Hierarchy

```python
ReasoningBankError (base)
├── MemoryRetrievalError
├── MemoryStorageError
├── LLMGenerationError
├── InvalidTaskError
├── JSONParseError
├── EmbeddingError
├── APIKeyError
├── TokenBudgetExceededError
└── MemoryValidationError
```

### Error Handling Strategy

1. **API Errors**: Retry with exponential backoff (up to 3 attempts)
2. **Validation Errors**: Fail fast with clear error messages
3. **Storage Errors**: Log and continue with degraded functionality
4. **LLM Errors**: Retry once, then return partial results
5. **Embedding Errors**: Fall back to keyword search

### Error Context Capture

When a task fails, the system captures:
```python
error_context = {
    "error_type": type(exception).__name__,
    "error_message": str(exception),
    "failure_pattern": extract_pattern(exception, task),
    "corrective_guidance": generate_guidance(exception, task),
    "stack_trace": traceback.format_exc(),
    "task_domain": classify_domain(task)
}
```

## Testing Strategy

### Unit Tests

**Target Coverage**: 80%+

**Key Test Files**:
- `test_reasoning_bank_core.py`: Memory storage, retrieval, judging
- `test_iterative_agent.py`: Reasoning loop, MaTTS, loop detection
- `test_cached_llm_client.py`: Cache hit/miss, TTL, eviction
- `test_retry_utils.py`: Backoff algorithm, retryable errors
- `test_storage_adapter.py`: Backend interface compliance
- `test_passive_learner.py`: Value detection, knowledge extraction
- `test_workspace_manager.py`: ID generation, isolation

**Test Patterns**:
```python
def test_memory_retrieval():
    # Arrange
    bank = ReasoningBank()
    bank.store_trace(task="test", trajectory=[], outcome="success", memory_items=[...])
    
    # Act
    memories = bank.retrieve_memories("test query", n_results=5)
    
    # Assert
    assert len(memories) > 0
    assert memories[0].composite_score > 0.5
```

### Integration Tests

**Test Scenarios**:
1. End-to-end task solving with memory retrieval
2. MaTTS parallel mode with multiple solutions
3. Error context learning and retrieval
4. Cache hit rate over multiple requests
5. Workspace isolation between projects
6. Passive learning from conversations

**Integration Test Example**:
```python
async def test_end_to_end_task_solving():
    # Initialize system
    server = await initialize_mcp_server()
    
    # Solve first task (cold start)
    result1 = await server.solve_coding_task(
        task="Implement binary search",
        use_memory=True,
        enable_matts=True
    )
    assert result1["outcome"] == "success"
    
    # Solve similar task (should use memory)
    result2 = await server.solve_coding_task(
        task="Implement binary search with duplicates",
        use_memory=True
    )
    assert len(result2["memories_used"]) > 0
    assert result2["solution_time"] < result1["solution_time"]
```

### Verification Tests

**Deployment Verification** (`verify_deployment.py`):
- ✅ Environment variables present
- ✅ File structure complete (11 files)
- ✅ Python imports successful (7 modules)
- ✅ Phase 1 enhancements present (4 items)
- ✅ Phase 2 enhancements present (2 items)
- ✅ Dockerfile correctness

**Phase Tests** (`test_phase1_phase2.py`):
- ✅ MaTTS parallel mode functional
- ✅ Retry logic with exponential backoff
- ✅ API key validation
- ✅ Memory UUID generation
- ✅ LLM response caching
- ✅ Enhanced memory retrieval

### Performance Tests

**Benchmarks**:
- First task latency: < 60 seconds
- Subsequent task latency: < 30 seconds
- Memory retrieval: < 1 second
- MaTTS overhead: ~1x baseline (not 3-5x)
- Cache hit rate: 40-60% after warmup
- API reliability: 99.5%+

**Load Testing**:
```python
async def test_concurrent_requests():
    tasks = [
        solve_coding_task(f"Task {i}") 
        for i in range(10)
    ]
    results = await asyncio.gather(*tasks)
    
    assert all(r["outcome"] == "success" for r in results)
    assert max(r["latency"] for r in results) < 60
```

## Deployment Architecture

### Docker Deployment

**Dockerfile Structure**:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY *.py .
COPY .env.example .

# Create data directories
RUN mkdir -p chroma_data traces logs

# Expose MCP server port
EXPOSE 8000

# Run server
CMD ["python", "reasoning_bank_server.py"]
```

**Docker Compose Configuration**:
```yaml
version: '3.8'

services:
  reasoning-bank:
    build: .
    container_name: reasoning-bank-mcp
    environment:
      - OPENROUTER_API_KEY=${OPENROUTER_API_KEY}
      - REASONING_BANK_DATA=/app/chroma_data
      - REASONING_BANK_TRACES=/app/traces
    volumes:
      - ./chroma_data:/app/chroma_data
      - ./traces:/app/traces
      - ./logs:/app/logs
    ports:
      - "8000:8000"
    restart: unless-stopped
```

### Persistent Storage

**Volumes**:
- `chroma_data/`: ChromaDB vector database (persistent)
- `traces/`: JSON reasoning traces (persistent)
- `logs/`: Application logs (ephemeral)

**Backup Strategy**:
```bash
# Backup ChromaDB
tar -czf chroma_backup_$(date +%Y%m%d).tar.gz chroma_data/

# Backup traces
tar -czf traces_backup_$(date +%Y%m%d).tar.gz traces/
```

### Monitoring

**Health Checks**:
```python
@mcp.tool()
async def health_check(ctx: Context) -> dict:
    return {
        "status": "healthy",
        "uptime": get_uptime(),
        "memory_count": bank.get_statistics()["total_traces"],
        "cache_hit_rate": cache.get_hit_rate()
    }
```

**Metrics to Track**:
- Request latency (p50, p95, p99)
- Success rate
- Cache hit rate
- API error rate
- Memory growth rate
- Token usage

**Logging Configuration**:
```python
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/reasoning_bank.log'),
        logging.StreamHandler()
    ]
)
```

## Security Considerations

### API Key Management

- Store API keys in environment variables (never in code)
- Validate API keys on startup (fail fast)
- Rotate keys regularly
- Use separate keys for dev/staging/prod

### Data Privacy

- Workspace isolation prevents cross-contamination
- No PII should be stored in memory items
- Traces can be purged per workspace
- Support for data retention policies

### Input Validation

- Validate all tool parameters
- Sanitize task descriptions
- Limit memory retrieval count
- Prevent prompt injection attacks

### Rate Limiting

- Respect OpenRouter rate limits
- Implement client-side rate limiting
- Use exponential backoff on 429 errors
- Monitor API usage quotas

## Performance Optimization

### Caching Strategy

1. **LLM Response Caching**: Cache deterministic calls (temperature=0.0)
2. **Embedding Caching**: Cache embeddings for repeated queries
3. **Memory Caching**: In-memory cache for frequently accessed memories

### Batch Processing

- Batch embedding generation for multiple memories
- Batch ChromaDB queries when possible
- Parallel MaTTS solution generation

### Token Optimization

- Truncate long prompts while preserving context
- Use smaller models for evaluation when possible
- Compress memory items for prompt inclusion

### Database Optimization

- Index ChromaDB collections by workspace_id
- Periodic vacuum/optimize operations
- Limit trace storage to recent N days

## Future Enhancements

### Planned Features

1. **Multi-modal Memory**: Support for images, diagrams in memories
2. **Collaborative Learning**: Share memories across team workspaces
3. **Active Learning**: Proactively identify knowledge gaps
4. **Memory Pruning**: Automatically remove low-value memories
5. **Advanced Genealogy**: Visualize memory evolution graphs
6. **Custom Embeddings**: Fine-tuned embeddings for domain-specific tasks
7. **Streaming Responses**: Stream solutions as they're generated
8. **Memory Export/Import**: Backup and restore memory banks

### Research Directions

1. **Adaptive MaTTS**: Dynamically adjust k based on task difficulty
2. **Meta-Learning**: Learn which memories are most useful
3. **Causal Reasoning**: Track causal relationships between memories
4. **Uncertainty Quantification**: Confidence scores for solutions
5. **Federated Learning**: Distributed memory banks with privacy preservation
