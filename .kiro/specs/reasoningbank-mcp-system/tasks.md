# Implementation Plan

- [x] 1. Set up project structure and core dependencies

  - Create directory structure for reasoning-bank-mcp with subdirectories for data, traces, and logs
  - Create requirements.txt with all Python dependencies (FastMCP, ChromaDB, sentence-transformers, OpenAI, requests, structlog)
  - Create .env.example file with required environment variables (OPENROUTER_API_KEY, REASONING_BANK_DATA, REASONING_BANK_TRACES)
  - Create config.py for centralized configuration management
  - _Requirements: 1.4, 5.5, 12.3_

- [x] 2. Implement custom exception hierarchy

  - Create exceptions.py with ReasoningBankError base class
  - Implement specific exception classes (MemoryRetrievalError, MemoryStorageError, LLMGenerationError, InvalidTaskError, JSONParseError, EmbeddingError, APIKeyError, TokenBudgetExceededError, MemoryValidationError)
  - Add error messages and context attributes to each exception class
  - _Requirements: 5.5, 7.4_

- [x] 3. Implement Responses API client

  - Create responses_alpha_client.py with ResponsesAPIClient class
  - Implement message format conversion from OpenAI to Responses API format
  - Create ResponsesAPIResult dataclass with reasoning token tracking
  - Implement create() method with proper error handling
  - Add support for configurable reasoning effort levels (low, medium, high)
  - _Requirements: 5.5, 7.1_

- [x] 4. Implement retry logic with exponential backoff

  - Create retry_utils.py with with_retry decorator
  - Implement exponential backoff algorithm with jitter
  - Add logic to distinguish retryable vs non-retryable errors
  - Implement retry counter and logging for debugging
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [x] 5. Implement LLM response caching layer

  - Create cached_llm_client.py with CachedLLMClient class
  - Implement LRU cache with OrderedDict for response storage
  - Create cache key generation using SHA256 hash of request parameters
  - Implement TTL-based cache expiration logic
  - Add cache hit/miss tracking for statistics
  - Implement cache eviction when size limit exceeded
  - Only cache deterministic calls (temperature=0.0)
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

- [x] 6. Implement storage adapter interface

  - Create storage_adapter.py with StorageBackendInterface abstract class
  - Define abstract methods: add_trace(), query_similar_memories(), get_statistics()
  - Implement ChromaDBAdapter with ChromaDB integration
  - Add embedding generation using sentence-transformers
  - Implement query_similar_memories with semantic search
  - Create factory function create_storage_backend() for backend selection
  - _Requirements: 1.4, 13.1, 13.2, 13.3, 13.4, 13.5_

- [x] 7. Implement workspace isolation manager

  - Create workspace_manager.py with WorkspaceManager class
  - Implement generate_workspace_id() using SHA256 hash of directory path
  - Add set_workspace() method to switch between workspaces
  - Implement workspace filtering in memory queries
  - Add get_workspace_name() for human-readable workspace identification
  - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_

- [x] 8. Implement core ReasoningBank memory management

  - Create reasoning_bank_core.py with ReasoningBank class
  - Implement MemoryItem dataclass with all required and optional fields
  - Create store_trace() method to persist reasoning traces with memory items
  - Implement retrieve_memories() with semantic search and composite scoring
  - Add compute_composite_score() combining similarity, recency, and error context
  - Implement get_genealogy() to trace memory evolution trees
  - Add get_statistics() for system metrics
  - Implement extract_learnings() to parse structured knowledge from LLM responses
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 8.1, 8.2, 8.3, 8.4, 8.5, 11.1, 11.2, 13.1, 13.2, 13.3, 13.4, 13.5, 15.1, 15.2, 15.3, 15.4, 15.5_

- [x] 9. Implement solution judging functionality

  - Add judge_solution() method to ReasoningBank class
  - Create judge prompt template with structured JSON output format
  - Implement JSON parsing with error handling for malformed responses
  - Extract verdict, score, reasoning, and learnings from judge response
  - Add error context extraction for failed solutions
  - _Requirements: 4.1, 4.2, 4.3, 4.4_

- [x] 10. Implement iterative reasoning agent

  - Create iterative_agent.py with IterativeReasoningAgent class
  - Implement solve_task() main entry point with Think → Evaluate → Refine loop
  - Create \_think_step() to generate solution attempts with memory context
  - Implement \_evaluate_step() to score solutions and provide feedback
  - Add \_refine_step() to improve solutions based on feedback
  - Implement loop detection using trajectory hashing
  - Add early termination when score exceeds success threshold (0.8)
  - Implement token budget management with estimation and truncation
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 14.1, 14.2, 14.3, 14.4, 14.5_

- [x] 11. Implement Memory-Aware Test-Time Scaling (MaTTS)

  - Add solve_with_matts() method to IterativeReasoningAgent
  - Implement parallel solution generation using asyncio.gather()
  - Add sequential mode as fallback option
  - Implement solution evaluation and best selection logic
  - Add optional refinement of best solution
  - Support configurable k parameter (number of parallel attempts)
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 12. Implement passive learning system

  - Create passive_learner.py with PassiveLearner class
  - Implement is_valuable() method with quality heuristics (code blocks, explanations, step-by-step)
  - Add extract_knowledge() using LLM to structure unstructured conversations
  - Implement auto-storage when quality thresholds are met
  - Add configuration for minimum answer length and auto-store toggle
  - Tag passively learned memories with source type metadata
  - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

- [x] 13. Implement knowledge retrieval component

  - Create knowledge_retrieval.py with KnowledgeRetriever class
  - Integrate with ReasoningBank for memory queries
  - Add filtering by domain category and pattern tags
  - Implement relevance ranking for retrieved knowledge
  - _Requirements: 1.2, 13.1, 13.2_

- [x] 14. Implement MCP server with FastMCP

  - Create reasoning_bank_server.py with FastMCP server initialization
  - Implement lifespan() context manager for component initialization
  - Add API key validation on startup with fail-fast behavior
  - Initialize all components (ReasoningBank, IterativeAgent, CachedLLMClient, PassiveLearner, WorkspaceManager, KnowledgeRetriever)
  - _Requirements: 5.5, 12.3_

- [x] 15. Implement solve_coding_task MCP tool

  - Create solve_coding_task() tool function with all parameters (task, use_memory, enable_matts, matts_k, matts_mode, store_result)
  - Add memory retrieval when use_memory=True
  - Integrate with IterativeAgent for solution generation
  - Support MaTTS mode when enable_matts=True
  - Store results to ReasoningBank when store_result=True
  - Return structured response with solution, trajectory, score, memories used
  - _Requirements: 5.1, 1.1, 1.2, 2.1, 3.1_

- [x] 16. Implement retrieve_memories MCP tool

  - Create retrieve_memories() tool function accepting query and n_results parameters
  - Call ReasoningBank.retrieve_memories() with composite scoring
  - Format memory items for response including error context flags
  - Return ranked list of relevant memories
  - _Requirements: 5.2, 1.2, 1.5_

- [x] 17. Implement get_memory_genealogy MCP tool

  - Create get_memory_genealogy() tool function accepting memory_id parameter
  - Call ReasoningBank.get_genealogy() to trace evolution tree
  - Format genealogy data with parent-child relationships
  - Return complete ancestry tree
  - _Requirements: 5.3, 8.1, 8.2, 8.3, 8.4, 8.5_

- [x] 18. Implement get_statistics MCP tool

  - Create get_statistics() tool function with no parameters
  - Collect metrics from ReasoningBank (total traces, success rate)
  - Collect cache metrics from CachedLLMClient (hit rate, total calls)
  - Collect API metrics (error rate, latency)
  - Return structured statistics response
  - _Requirements: 5.4, 11.1, 11.2, 11.3, 11.4, 11.5_

- [x] 19. Implement logging configuration

  - Create logging_config.py with structured logging setup
  - Configure file and console handlers
  - Add log rotation for production use
  - Implement log levels for different components
  - Add structured logging with context (workspace_id, trace_id)
  - _Requirements: 11.3_

- [x] 20. Create Docker deployment configuration

  - Create Dockerfile with Python 3.11 base image
  - Add all application files and dependencies to Docker image
  - Create data directories (chroma_data, traces, logs) in container
  - Configure environment variables in Dockerfile
  - _Requirements: 12.1, 12.2, 12.3, 12.4_

- [x] 21. Create Docker Compose configuration

  - Create docker-compose.yml with service definition
  - Configure persistent volumes for chroma_data and traces
  - Map environment variables from .env file
  - Expose MCP server port (8000)
  - Add restart policy (unless-stopped)
  - _Requirements: 12.2, 12.3, 12.4, 12.5_

- [x] 22. Create deployment verification script

  - Create verify_deployment.py with automated checks
  - Verify environment variables are set
  - Check file structure completeness (11 required files)
  - Test Python imports for all modules
  - Verify Phase 1 enhancements (MaTTS, retry, API key validation, UUIDs)
  - Verify Phase 2 enhancements (caching, enhanced retrieval)
  - Check Dockerfile correctness
  - _Requirements: 12.3_

- [ ]\* 23. Create comprehensive test suite

  - [ ]\* 23.1 Create test_reasoning_bank_core.py
    - Write tests for memory storage and retrieval
    - Test composite scoring algorithm
    - Test genealogy tracking
    - Test error context capture
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 8.1, 8.2, 8.3, 8.4, 8.5_
  - [ ]\* 23.2 Create test_iterative_agent.py
    - Write tests for Think → Evaluate → Refine loop
    - Test loop detection
    - Test early termination on success threshold
    - Test token budget management
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 14.1, 14.2, 14.3, 14.4, 14.5_
  - [ ]\* 23.3 Create test_matts.py
    - Write tests for parallel solution generation
    - Test sequential mode fallback
    - Test solution selection logic
    - Verify performance characteristics (1x baseline, not 3-5x)
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_
  - [ ]\* 23.4 Create test_cached_llm_client.py
    - Write tests for cache hit/miss logic
    - Test TTL expiration
    - Test LRU eviction
    - Test deterministic call filtering (temperature=0.0)
    - Verify cache statistics tracking
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_
  - [ ]\* 23.5 Create test_retry_utils.py
    - Write tests for exponential backoff algorithm
    - Test jitter randomization
    - Test retryable vs non-retryable error distinction
    - Verify retry counter and max attempts
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_
  - [ ]\* 23.6 Create test_workspace_manager.py
    - Write tests for workspace ID generation (deterministic)
    - Test workspace switching
    - Test memory isolation between workspaces
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_
  - [ ]\* 23.7 Create test_passive_learner.py
    - Write tests for value detection heuristics
    - Test knowledge extraction
    - Test auto-storage logic
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_
  - [ ]\* 23.8 Create test_phase1_phase2.py
    - Write integration tests for Phase 1 features (MaTTS, retry, API validation, UUIDs)
    - Write integration tests for Phase 2 features (caching, enhanced retrieval)
    - _Requirements: 3.1, 6.1, 7.1, 8.1_
  - [ ]\* 23.9 Create test_end_to_end.py
    - Write end-to-end test for complete task solving flow
    - Test memory retrieval and reuse across tasks
    - Test error context learning and prevention
    - Verify workspace isolation in multi-tenant scenario
    - _Requirements: 1.1, 1.2, 1.5, 2.1, 4.1, 10.1_

- [x] 24. Create documentation files

  - Create README.md with project overview, features, and quick start guide
  - Create DEPLOYMENT_GUIDE.md with step-by-step deployment instructions
  - Create QUICK_REFERENCE.md with MCP tool usage examples
  - Document environment variables and configuration options
  - Add architecture diagrams and data flow illustrations
  - _Requirements: 12.3_

- [ ] 25. Create example usage scripts

  - [ ] 25.1 Create example_basic_task.py
    - Import and initialize ReasoningBank, IterativeAgent, and required components
    - Define a simple coding task (e.g., "Write a function to reverse a string")
    - Call agent.solve_task() with use_memory=True
    - Print solution, score, iterations, and extracted memories
    - Add comments explaining initialization, task solving flow, and output interpretation
    - _Requirements: 5.1_
  - [ ] 25.2 Create example_matts_mode.py
    - Initialize components similar to basic example
    - Define a moderately complex task (e.g., "Implement binary search with edge cases")
    - Call agent.solve_with_matts() with k=5, mode="parallel"
    - Print all generated solutions, scores, selected solution, and contrast analysis
    - Add comments explaining MaTTS benefits and when to use parallel vs sequential
    - _Requirements: 3.1_
  - [ ] 25.3 Create example_memory_retrieval.py
    - Initialize ReasoningBank and store 3-5 sample memories with different domains
    - Demonstrate retrieve_memories() with various queries
    - Show filtering by domain_category and include_failures parameters
    - Print retrieved memories with similarity scores and error context flags
    - Add comments explaining composite scoring and retrieval strategies
    - _Requirements: 5.2_
  - [ ] 25.4 Create example_genealogy.py
    - Store a trace with parent_memory_id to create genealogy chain
    - Store derived memories to build evolution tree
    - Call get_genealogy() for a memory with ancestors
    - Print complete ancestry tree with evolution stages
    - Visualize parent-child relationships (text-based tree diagram)
    - Add comments explaining genealogy tracking and use cases
    - _Requirements: 5.3_
  - [ ] 25.5 Add README for examples
    - Create examples/README.md with overview of all example scripts
    - Include prerequisites (environment setup, API keys)
    - Add expected output samples for each example
    - Include troubleshooting section for common issues
    - _Requirements: 5.1, 5.2, 5.3, 3.1_

- [ ] 26. Implement health check and monitoring

  - [ ] 26.1 Add health_check() tool to MCP server
    - Add @server.call_tool() decorated health_check() function in reasoning_bank_server.py
    - Return dict with: status ("healthy"/"degraded"/"unhealthy"), uptime_seconds, component_status (reasoning_bank, storage, llm_client)
    - Check if each component is initialized and responsive
    - Include basic metrics: total_traces, cache_hit_rate, last_api_call_latency
    - _Requirements: 11.1, 11.2_
  - [ ] 26.2 Implement comprehensive monitoring metrics
    - Add memory_growth_rate field to ReasoningBank.get_statistics() (traces per day)
    - Track cumulative token usage in CachedLLMClient (add tokens_used counter)
    - Add api_error_rate to statistics (failed_calls / total_calls)
    - Create export_monitoring_data() function that returns JSON with all metrics
    - Include timestamp, uptime, and system resource usage (memory, CPU if available)
    - _Requirements: 11.3, 11.4_

- [x] 27. Implement data retention and cleanup

  - [x] 27.1 Add trace cleanup functionality
    - Add cleanup_old_traces(retention_days: int = 90, workspace_id: Optional[str] = None) method to ReasoningBank
    - Query storage for traces older than retention_days
    - Delete traces and associated memory items from ChromaDB/Supabase
    - Return dict with: deleted_traces_count, deleted_memories_count, freed_space_mb
    - Log cleanup operations with timestamps and counts
    - _Requirements: 12.2_
  - [x] 27.2 Implement workspace deletion
    - Add delete_workspace(workspace_id: str, confirm: bool = False) method to WorkspaceManager
    - Raise error if confirm=False to prevent accidental deletion
    - Call storage_adapter to delete all records where workspace_id matches
    - Remove workspace from active workspace list
    - Return dict with: workspace_id, deleted_traces, deleted_memories, deletion_timestamp
    - _Requirements: 10.5_
  - [x] 27.3 Create backup/restore utilities
    - Create backup_restore.py module with BackupManager class
    - Implement backup_chromadb(output_path: str, workspace_id: Optional[str] = None) that exports to JSON/tar.gz
    - Implement restore_chromadb(backup_path: str, target_workspace_id: Optional[str] = None) that imports data
    - Add validate_backup(backup_path: str) to check integrity (schema version, checksums)
    - Support incremental backups by tracking last_backup_timestamp
    - Include metadata in backup: version, timestamp, trace_count, memory_count
    - _Requirements: 12.2_

- [x] 28. Optimize performance and resource usage

  - Implement batch embedding generation for multiple memories
  - Add in-memory caching for frequently accessed memories
  - Optimize ChromaDB queries with proper indexing
  - Implement prompt compression for token optimization
  - Add connection pooling for API clients
  - _Requirements: 1.2, 11.3, 14.1, 14.2_

- [ ] 28.1 Integrate performance optimizations into core system

  - [ ] 28.1.1 Integrate BatchEmbeddingGenerator into storage adapters
    - Import BatchEmbeddingGenerator from performance_optimizer in storage_adapter.py
    - In ChromaDBAdapter.**init**(), create BatchEmbeddingGenerator(self.embedder, batch_size=32)
    - Update add_trace() to collect all memory texts and call batch_generator.generate_batch() once
    - Update SupabaseAdapter similarly for batch embedding generation
    - Measure and log performance improvement (embeddings/sec)
    - _Requirements: 1.2, 11.3_
  - [ ] 28.1.2 Integrate MemoryCache into ReasoningBank
    - Import MemoryCache from performance_optimizer in reasoning_bank_core.py
    - Add self.memory_cache = MemoryCache(max_size=1000, ttl_seconds=3600) to **init**()
    - In retrieve_memories(), check cache for each memory_id before querying storage
    - In store_trace(), call memory_cache.put() for each new memory item
    - Add cache statistics to get_statistics() output
    - _Requirements: 1.2, 11.3_
  - [ ] 28.1.3 Integrate PromptCompressor into IterativeAgent
    - Import PromptCompressor from performance_optimizer in iterative_agent.py
    - Add self.compressor = PromptCompressor(max_tokens=12000) to **init**()
    - In \_think_step() and \_evaluate_step(), call compressor.compress() on prompts before LLM calls
    - Track compression_count and avg_compression_ratio in agent statistics
    - Log when compression is applied with before/after token counts
    - _Requirements: 14.1, 14.2_
  - [ ] 28.1.4 Integrate APIConnectionPool into ResponsesAPIClient
    - Import APIConnectionPool from performance_optimizer in responses_alpha_client.py
    - Add self.connection_pool = APIConnectionPool(pool_size=10) to **init**()
    - Replace requests.post() calls with self.connection_pool.post()
    - Add connection pool statistics to client (active_connections, total_requests)
    - Implement **del**() to call connection_pool.close() on cleanup
    - _Requirements: 11.3_
  - [ ] 28.1.5 Integrate PerformanceMonitor across all components
    - Import PerformanceMonitor from performance_optimizer in reasoning_bank_server.py
    - Create global performance_monitor instance during lifespan startup
    - In CachedLLMClient.create(), call monitor.record_api_call(latency) and monitor.record_cache_hit/miss()
    - In storage adapters, call monitor.record_embeddings(count) after batch generation
    - In ReasoningBank.store_trace(), call monitor.record_memory_cached() for each memory
    - Update get_statistics() tool to include monitor.get_statistics() in response
    - _Requirements: 11.1, 11.2, 11.3, 11.4_

- [ ] 29. Add input validation and security

  - [ ] 29.1 Implement parameter validation
    - Create validation.py module with ValidationError exception
    - Add validate_task_input(task: str) that checks: min_length=10, max_length=10000, no null bytes
    - Add validate_numeric_param(value: int, min_val: int, max_val: int, param_name: str)
    - In solve_coding_task(), validate task, matts_k (2-10), and other numeric params
    - In retrieve_memories(), validate query (min_length=3) and n_results (1-20)
    - Raise InvalidTaskError with descriptive message on validation failure
    - _Requirements: 5.5_
  - [ ] 29.2 Implement prompt injection prevention
    - Add sanitize_task_description(task: str) -> str function in validation.py
    - Remove/escape patterns: system prompts ("You are now...", "Ignore previous..."), code injection attempts
    - Replace suspicious Unicode characters with safe equivalents
    - Truncate excessively long inputs (>10000 chars) with warning
    - Log sanitization events with original and sanitized versions
    - Apply sanitization in solve_coding_task() before processing
    - _Requirements: 5.5_
  - [ ] 29.3 Add rate limiting
    - Create rate_limiter.py with RateLimiter class using token bucket algorithm
    - Implement check_rate_limit(workspace_id: str, operation: str) -> bool
    - Configure limits: 100 API calls/hour per workspace, 1000/day global
    - Store rate limit state in memory (dict with workspace_id -> {tokens, last_refill})
    - In solve_coding_task(), check rate limit before processing, raise RateLimitError if exceeded
    - Return error response with: error="rate_limit_exceeded", retry_after_seconds, current_usage
    - _Requirements: 5.5_
  - [ ] 29.4 Add memory retrieval limits
    - Add MAX_RETRIEVAL_RESULTS = 20 constant in reasoning_bank_core.py
    - In retrieve_memories(), validate n_results <= MAX_RETRIEVAL_RESULTS
    - Raise MemoryRetrievalError if limit exceeded with message including max allowed
    - Add warning log if n_results > 10 (performance concern)
    - _Requirements: 5.5_
  - [ ] 29.5 Validate memory schema before storage
    - Import MemoryItemSchema from schemas in reasoning_bank_core.py
    - In store_trace(), validate each memory item: MemoryItemSchema.model_validate(memory_dict)
    - Catch ValidationError and log detailed error with field names and values
    - Skip invalid memories but continue storing valid ones
    - Return validation_errors list in store_trace() response
    - Add memory_validation_failures counter to statistics
    - _Requirements: 15.5_

- [x] 30. Create migration utilities

  - Create migrate_to_supabase.py for ChromaDB to Supabase migration
  - Implement SupabaseAdapter in storage_adapter.py
  - Add supabase_schema.sql with database schema
  - Create supabase_storage.py with Supabase client integration
  - Document migration process and rollback procedures
  - _Requirements: 1.4, 12.2_

- [ ] 31. Integrate Pydantic schemas across the system

  - [ ] 31.1 Update ReasoningBank to use Pydantic schemas
    - Import MemoryItemSchema, ReasoningTraceSchema, TrajectoryStep from schemas in reasoning_bank_core.py
    - Update MemoryItem dataclass to inherit from MemoryItemSchema (or replace entirely)
    - Update store_trace() signature to accept List[MemoryItemSchema] instead of List[dict]
    - Update retrieve_memories() to return List[MemoryItemSchema] with .model_dump() for serialization
    - Update get_genealogy() to return genealogy data using MemoryItemSchema
    - Add try/except blocks for ValidationError with descriptive error messages
    - _Requirements: 15.1, 15.2, 15.3, 15.4, 15.5_
  - [ ] 31.2 Update MCP tools to use Pydantic input/output schemas
    - In solve_coding_task(), parse input using SolveCodingTaskInput.model_validate(params)
    - Return response using SolveCodingTaskOutput.model_dump() for JSON serialization
    - In retrieve_memories(), parse input using RetrieveMemoriesInput.model_validate(params)
    - Return response using RetrieveMemoriesOutput.model_dump()
    - In get_statistics(), return GetStatisticsOutput.model_dump()
    - Add error handling for validation errors with clear user-facing messages
    - Use schemas.get_mcp_tool_schemas() to generate JSON schemas for MCP protocol
    - _Requirements: 5.1, 5.2, 5.3, 5.4_
  - [ ] 31.3 Update configuration to use ReasoningBankConfig
    - Import ReasoningBankConfig from schemas in config.py
    - Replace get_config() to return ReasoningBankConfig instance
    - Load environment variables using Pydantic's Config.env_prefix or manual os.getenv()
    - Add validation for required fields (api_key, storage paths)
    - Update all components to use config.model_dump() or config.field_name for access
    - Add config.model_dump_json() for exporting configuration
    - _Requirements: 5.5, 12.3_
  - [ ] 31.4 Add schema validation throughout the system
    - In IterativeAgent, validate trajectory steps using TrajectoryStep.model_validate()
    - In PassiveLearner.extract_knowledge(), validate extracted memories with MemoryItemSchema
    - In storage adapters, validate data before insertion using appropriate schemas
    - Add comprehensive error handling: catch ValidationError, log details, raise custom exceptions
    - Add validation statistics: track validation_successes and validation_failures
    - Include validation metrics in get_statistics() output
    - _Requirements: 15.5_
