# Requirements Document

## Introduction

The ReasoningBank MCP System is a self-evolving memory system for LLM agents that learns from both successes and failures to reduce hallucinations and improve problem-solving over time. Based on Google's ReasoningBank paper, the system implements an intelligent reasoning loop (Think → Evaluate → Refine → Store Learnings → Apply to Future Tasks) with vector-based semantic memory retrieval, parallel solution generation, and hallucination prevention through error context learning.

## Glossary

- **ReasoningBank**: The core memory management system that stores, retrieves, and manages reasoning traces and learned experiences
- **MCP Server**: Model Context Protocol server that exposes ReasoningBank functionality as tools to LLM agents
- **Iterative Agent**: The reasoning component that implements the Think → Evaluate → Refine loop for solution generation
- **MaTTS**: Memory-Aware Test-Time Scaling - a technique that generates multiple parallel solution attempts and selects the best one
- **Memory Item**: A structured unit of stored knowledge containing title, description, content, and optional error context
- **Reasoning Trace**: A complete record of a problem-solving attempt including task, trajectory, outcome, and extracted learnings
- **ChromaDB**: The vector database used for semantic memory storage and retrieval
- **Responses API**: The LLM API interface (OpenRouter) used for generating reasoning and solutions
- **Error Context**: Metadata attached to memories that captures failure patterns and bug information
- **Genealogy**: The parent-child relationship tracking between memories showing how knowledge evolved
- **Passive Learner**: A component that automatically captures valuable Q&A exchanges without explicit storage requests
- **Workspace Manager**: A component that provides isolation between different user workspaces or projects
- **Cached LLM Client**: A caching layer that reduces API costs by storing and reusing LLM responses

## Requirements

### Requirement 1: Memory Storage and Retrieval

**User Story:** As an AI agent, I want to store and retrieve past reasoning experiences, so that I can learn from previous successes and failures when solving new tasks.

#### Acceptance Criteria

1. WHEN a reasoning task is completed, THE ReasoningBank SHALL store the reasoning trace with task description, trajectory, outcome, and extracted memory items
2. WHEN retrieving memories for a new task, THE ReasoningBank SHALL return semantically similar past experiences ranked by composite score (relevance + recency + error context)
3. THE ReasoningBank SHALL assign a unique UUID to each memory item for tracking and genealogy purposes
4. THE ReasoningBank SHALL persist all memories to ChromaDB with vector embeddings for semantic search
5. WHEN a memory contains error context, THE ReasoningBank SHALL flag it as a warning during retrieval to prevent repeating past mistakes

### Requirement 2: Iterative Reasoning Loop

**User Story:** As an AI agent, I want to iteratively refine my solutions through evaluation feedback, so that I can produce higher quality results than single-pass generation.

#### Acceptance Criteria

1. WHEN solving a task, THE Iterative Agent SHALL execute a Think → Evaluate → Refine loop for up to 3 iterations
2. WHEN a solution achieves a quality score above 0.8, THE Iterative Agent SHALL terminate early and return the successful solution
3. WHEN evaluating a solution, THE Iterative Agent SHALL generate a numerical score and specific feedback for improvement
4. THE Iterative Agent SHALL detect reasoning loops by tracking trajectory hashes and terminate if repetition is detected
5. WHEN the maximum iteration limit is reached, THE Iterative Agent SHALL return the best solution generated across all iterations

### Requirement 3: Memory-Aware Test-Time Scaling (MaTTS)

**User Story:** As an AI agent, I want to generate multiple solution attempts in parallel and select the best one, so that I can improve solution quality through diversity and self-contrast.

#### Acceptance Criteria

1. WHEN MaTTS is enabled, THE Iterative Agent SHALL generate 3-5 parallel solution attempts simultaneously
2. THE Iterative Agent SHALL evaluate all generated solutions and select the one with the highest quality score
3. WHEN running in parallel mode, THE Iterative Agent SHALL complete all attempts in approximately 1x the time of a single attempt (not 3-5x)
4. THE Iterative Agent SHALL support both parallel and sequential MaTTS modes via configuration parameter
5. WHEN MaTTS is disabled, THE Iterative Agent SHALL fall back to single-solution generation

### Requirement 4: Error Context Learning

**User Story:** As an AI agent, I want to capture and learn from my failures and bugs, so that I can avoid repeating the same mistakes in future tasks.

#### Acceptance Criteria

1. WHEN a reasoning trace results in failure, THE ReasoningBank SHALL extract error patterns and store them as error context in memory items
2. WHEN retrieving memories for a new task, THE ReasoningBank SHALL prioritize memories with error context that match the current task domain
3. THE ReasoningBank SHALL include error warnings in the prompt context when relevant past failures are detected
4. WHEN storing error context, THE ReasoningBank SHALL capture the error type, failure pattern, and corrective guidance
5. THE ReasoningBank SHALL support querying memories specifically by error context flags

### Requirement 5: MCP Tool Interface

**User Story:** As a user or external system, I want to interact with ReasoningBank through standardized MCP tools, so that I can integrate it with various LLM agents and workflows.

#### Acceptance Criteria

1. THE MCP Server SHALL expose a `solve_coding_task` tool that accepts task description, memory settings, and MaTTS configuration
2. THE MCP Server SHALL expose a `retrieve_memories` tool that accepts a query string and returns ranked relevant memories
3. THE MCP Server SHALL expose a `get_memory_genealogy` tool that accepts a memory UUID and returns its evolution tree
4. THE MCP Server SHALL expose a `get_statistics` tool that returns system performance metrics including success rate and cache hit rate
5. WHEN an API key is missing or invalid, THE MCP Server SHALL fail fast with a clear error message during initialization

### Requirement 6: LLM Response Caching

**User Story:** As a system operator, I want to cache LLM responses to reduce API costs, so that I can operate the system more economically without sacrificing functionality.

#### Acceptance Criteria

1. THE Cached LLM Client SHALL cache LLM responses based on prompt hash and model parameters
2. WHEN a cached response exists for a prompt, THE Cached LLM Client SHALL return it without making an API call
3. THE Cached LLM Client SHALL achieve a 20-30% cost reduction through cache hits after warmup period
4. THE Cached LLM Client SHALL track cache hit rate and expose it through system statistics
5. THE Cached LLM Client SHALL invalidate cache entries based on configurable TTL or cache size limits

### Requirement 7: API Reliability and Retry Logic

**User Story:** As a system operator, I want the system to handle transient API failures gracefully, so that temporary network issues don't cause task failures.

#### Acceptance Criteria

1. WHEN an API call fails with a transient error, THE Retry Logic SHALL retry with exponential backoff up to 3 attempts
2. THE Retry Logic SHALL add random jitter to backoff delays to prevent thundering herd problems
3. THE Retry Logic SHALL achieve 99.5% API reliability through automatic retry handling
4. WHEN all retry attempts are exhausted, THE Retry Logic SHALL raise a clear error with the underlying failure reason
5. THE Retry Logic SHALL distinguish between retryable errors (rate limits, timeouts) and non-retryable errors (invalid API key)

### Requirement 8: Memory Genealogy Tracking

**User Story:** As a user, I want to understand how memories evolved from parent experiences, so that I can trace the lineage of learned knowledge.

#### Acceptance Criteria

1. WHEN creating a new memory from an existing one, THE ReasoningBank SHALL record the parent memory UUID
2. THE ReasoningBank SHALL track evolution stage numbers to indicate how many generations a memory has evolved
3. WHEN querying genealogy, THE ReasoningBank SHALL return the complete ancestry tree including all parent and derived memories
4. THE ReasoningBank SHALL support querying all memories derived from a specific parent memory
5. THE ReasoningBank SHALL include genealogy metadata in memory retrieval results for context

### Requirement 9: Passive Learning

**User Story:** As an AI agent, I want to automatically capture valuable Q&A exchanges without explicit storage requests, so that I can build knowledge from natural interactions.

#### Acceptance Criteria

1. WHEN a Q&A exchange meets quality thresholds, THE Passive Learner SHALL automatically extract and store memory items
2. THE Passive Learner SHALL filter out low-quality exchanges based on minimum answer length (100 characters)
3. THE Passive Learner SHALL support enabling/disabling auto-storage via configuration
4. WHEN passive learning is enabled, THE Passive Learner SHALL extract structured knowledge from unstructured conversations
5. THE Passive Learner SHALL tag passively learned memories with metadata indicating their source type

### Requirement 10: Workspace Isolation

**User Story:** As a multi-tenant system operator, I want to isolate memories between different users or projects, so that knowledge doesn't leak across workspace boundaries.

#### Acceptance Criteria

1. THE Workspace Manager SHALL support creating isolated memory spaces for different workspaces
2. WHEN retrieving memories, THE Workspace Manager SHALL filter results to only include memories from the current workspace
3. THE Workspace Manager SHALL support switching between workspaces without restarting the system
4. THE Workspace Manager SHALL persist workspace metadata alongside memory items for filtering
5. WHEN a workspace is deleted, THE Workspace Manager SHALL remove all associated memories from storage

### Requirement 11: System Monitoring and Statistics

**User Story:** As a system operator, I want to monitor system performance and health metrics, so that I can identify issues and optimize configuration.

#### Acceptance Criteria

1. THE ReasoningBank SHALL track total reasoning traces stored and success/failure rates
2. THE ReasoningBank SHALL track cache hit rates and API call statistics
3. THE ReasoningBank SHALL track memory retrieval latency and embedding generation time
4. WHEN statistics are requested, THE ReasoningBank SHALL return current metrics in structured format
5. THE ReasoningBank SHALL support resetting statistics counters for testing and benchmarking

### Requirement 12: Docker Deployment

**User Story:** As a system operator, I want to deploy ReasoningBank in a containerized environment, so that I can ensure consistent runtime behavior across different hosts.

#### Acceptance Criteria

1. THE Dockerfile SHALL include all required Python dependencies and application files
2. THE Docker Compose configuration SHALL define persistent volumes for ChromaDB data and reasoning traces
3. WHEN the container starts, THE MCP Server SHALL validate environment variables and fail fast if required keys are missing
4. THE Docker deployment SHALL expose the MCP server on a configurable port
5. THE Docker container SHALL support graceful shutdown and cleanup of resources

### Requirement 13: Enhanced Memory Retrieval

**User Story:** As an AI agent, I want memory retrieval to consider multiple factors beyond semantic similarity, so that I get the most relevant and useful memories for my current task.

#### Acceptance Criteria

1. THE ReasoningBank SHALL compute composite scores combining semantic similarity, recency, and error context relevance
2. WHEN computing recency scores, THE ReasoningBank SHALL apply exponential decay based on memory age
3. WHEN error context is present, THE ReasoningBank SHALL boost scores for memories matching the current task's error patterns
4. THE ReasoningBank SHALL normalize all score components to a 0-1 range before combining
5. THE ReasoningBank SHALL support configurable weights for each score component (similarity, recency, error context)

### Requirement 14: Token Budget Management

**User Story:** As an AI agent, I want to manage token budgets effectively, so that I don't exceed API limits or incur excessive costs.

#### Acceptance Criteria

1. THE Iterative Agent SHALL estimate token counts for prompts before making API calls
2. WHEN a prompt exceeds token budget, THE Iterative Agent SHALL truncate content while preserving head and tail context
3. THE Iterative Agent SHALL support configurable maximum output tokens per API call
4. WHEN truncation occurs, THE Iterative Agent SHALL log a warning indicating content was omitted
5. THE Iterative Agent SHALL track cumulative token usage across all iterations and raise an error if budget is exceeded

### Requirement 15: Structured Memory Schema

**User Story:** As a developer, I want memories to follow a consistent structured schema, so that I can reliably parse and process stored knowledge.

#### Acceptance Criteria

1. THE MemoryItem SHALL contain required fields: id, title, description, content
2. THE MemoryItem SHALL support optional fields: error_context, parent_memory_id, pattern_tags, difficulty_level, domain_category
3. THE MemoryItem SHALL support serialization to JSON format for storage and transmission
4. THE MemoryItem SHALL provide a format_for_prompt method that renders memory content for LLM consumption
5. WHEN validating a memory item, THE ReasoningBank SHALL reject items missing required fields
