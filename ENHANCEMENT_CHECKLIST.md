# ReasoningBank Enhancement Implementation Checklist

**Last Updated:** October 16, 2025  
**Status:** Ready for implementation

---

## 🔴 Phase 1: Critical Fixes (5-6 hours)

### ✅ 1. Fix MaTTS Parallel Mode Performance Bug
**Effort:** 3-4 hours | **Priority:** CRITICAL

- [ ] Add asyncio import to `iterative_agent.py`
- [ ] Create `_solve_with_matts_parallel_async` method with true parallel execution
- [ ] Add `async def generate_trajectory` helper for concurrent execution
- [ ] Update `solve_task` to handle async MaTTS mode
- [ ] Test with k=3,5,7 and verify 3-5x speedup
- [ ] Update documentation to reflect async behavior

**Files:** `iterative_agent.py`

---

### ✅ 2. Apply Retry Logic to LLM Calls
**Effort:** 1 hour | **Priority:** CRITICAL

- [ ] Import `with_retry` from `retry_utils.py` in `reasoning_bank_core.py`
- [ ] Apply `@with_retry` decorator to `ReasoningBank._call_llm` (line 291)
- [ ] Import `with_retry` in `iterative_agent.py`
- [ ] Apply `@with_retry` decorator to `IterativeReasoningAgent._call_llm` (line 442)
- [ ] Test API failure recovery (simulate network errors)
- [ ] Verify retry logs appear in output

**Files:** `reasoning_bank_core.py`, `iterative_agent.py`

---

### ✅ 3. Add API Key Validation on Startup
**Effort:** 30 minutes | **Priority:** HIGH

- [ ] Add `_validate_api_key` method to `ReasoningBank.__init__`
- [ ] Call validation after client initialization (after line 122)
- [ ] Add try/except with descriptive error message
- [ ] Log successful validation
- [ ] Test with invalid key (should fail fast)
- [ ] Test with valid key (should pass silently)

**Files:** `reasoning_bank_core.py`

---

### ✅ 4. Sync MemoryItem Dataclass with Schema
**Effort:** 30 minutes | **Priority:** HIGH

- [ ] Add `id: str = field(default_factory=lambda: str(uuid.uuid4()))` to `MemoryItem` dataclass
- [ ] Import `field` from `dataclasses` if not already imported
- [ ] Update `MemoryItem.to_dict()` to include `id` field
- [ ] Update all memory creation points to handle new field
- [ ] Test memory genealogy tracking with IDs
- [ ] Verify backward compatibility with existing traces

**Files:** `reasoning_bank_core.py`

---

## 🟡 Phase 2: Production Features (5 hours)

### ✅ 5. Implement LLM Response Caching
**Effort:** 3 hours | **Priority:** HIGH

- [ ] Create `cached_llm_client.py` with `CachedLLMClient` class
- [ ] Implement `_cache_key` method (hash model + messages + temperature)
- [ ] Implement `create` method with TTL-based caching
- [ ] Add LRU eviction for cache size limit
- [ ] Only cache temperature=0.0 calls (deterministic)
- [ ] Import and wrap client in `reasoning_bank_core.py.__init__`
- [ ] Use config values for cache_size and ttl_seconds
- [ ] Add cache hit/miss logging
- [ ] Test cache effectiveness on repeated evaluations
- [ ] Measure token cost reduction

**Files:** `cached_llm_client.py` (new), `reasoning_bank_core.py`

---

### ✅ 6. Enhanced Memory Retrieval with Filtering
**Effort:** 2 hours | **Priority:** MEDIUM

- [ ] Update `retrieve_relevant_memories` signature with new parameters
- [ ] Add `include_failures`, `domain_filter`, `min_score` parameters
- [ ] Implement metadata-based filtering with ChromaDB where clause
- [ ] Add `_calculate_recency_score` helper method
- [ ] Implement composite scoring (relevance + recency + error_bonus)
- [ ] Sort by composite score and return top k
- [ ] Test filtering by outcome type
- [ ] Test filtering by domain
- [ ] Test score threshold filtering
- [ ] Document new parameters in docstring

**Files:** `reasoning_bank_core.py`

---

## 🟢 Phase 3: Quality & Observability (8-10 hours)

### ✅ 7. Structured Logging
**Effort:** 2 hours | **Priority:** MEDIUM

- [ ] Add `structlog>=23.1.0` to `requirements.txt`
- [ ] Configure structlog in `reasoning_bank_core.py`
- [ ] Replace all `print()` statements with `logger.info/warning/error`
- [ ] Replace basic `logging` calls with structured `logger` calls
- [ ] Add context to all log statements (task, scores, tokens, etc.)
- [ ] Update `iterative_agent.py` to use structured logging
- [ ] Test JSON log output format
- [ ] Document log schema for monitoring

**Files:** `requirements.txt`, `reasoning_bank_core.py`, `iterative_agent.py`

---

### ✅ 8. Comprehensive Test Suite
**Effort:** 6-8 hours | **Priority:** MEDIUM

- [ ] Create `tests/` directory
- [ ] Create `tests/__init__.py`
- [ ] Create `tests/conftest.py` with shared fixtures
- [ ] Create `tests/test_reasoning_bank.py` with core tests
- [ ] Create `tests/test_iterative_agent.py` with agent tests
- [ ] Create `tests/test_memory_retrieval.py` with search tests
- [ ] Create `tests/test_retry_logic.py` with retry tests
- [ ] Create `tests/test_caching.py` with cache tests
- [ ] Add `pytest>=7.4.0` to `requirements.txt`
- [ ] Add `pytest-asyncio>=0.21.0` to `requirements.txt`
- [ ] Add `pytest-cov>=4.1.0` to `requirements.txt`
- [ ] Configure pytest in `pyproject.toml` or `pytest.ini`
- [ ] Run tests and achieve 80%+ coverage
- [ ] Add CI/CD test runner configuration

**Files:** `tests/` directory (multiple files), `requirements.txt`, `pytest.ini`

---

### ✅ 9. Docker Health Check Improvements
**Effort:** 15 minutes | **Priority:** LOW

- [ ] Update `docker-compose.yml` healthcheck section
- [ ] Add API key existence check
- [ ] Add ChromaDB initialization check
- [ ] Test health check with missing API key (should fail)
- [ ] Test health check with valid setup (should pass)
- [ ] Update documentation with health check behavior

**Files:** `docker-compose.yml`

---

## Testing Checklist

### Unit Tests
- [ ] Test memory consolidation
- [ ] Test memory retrieval (empty, single, multiple)
- [ ] Test memory filtering by outcome
- [ ] Test memory filtering by domain
- [ ] Test cache hit/miss behavior
- [ ] Test retry logic with failures
- [ ] Test API key validation (valid/invalid)
- [ ] Test async MaTTS generation

### Integration Tests
- [ ] Test full task solving workflow
- [ ] Test MaTTS parallel mode end-to-end
- [ ] Test memory persistence and loading
- [ ] Test ChromaDB integration
- [ ] Test OpenRouter API integration (mocked)

### Performance Tests
- [ ] Benchmark MaTTS parallel vs sequential
- [ ] Measure cache hit rate on repeated tasks
- [ ] Measure retry overhead on failures
- [ ] Measure memory retrieval latency

---

## Validation Criteria

### Phase 1 Completion
- [ ] MaTTS parallel mode shows 3-5x speedup for k=3-5
- [ ] API calls automatically retry on transient failures
- [ ] Invalid API keys cause immediate startup failure
- [ ] All memory items have unique UUIDs

### Phase 2 Completion
- [ ] Cache hit rate reaches 40-60% on evaluation calls
- [ ] Memory retrieval supports filtering and ranking
- [ ] Token costs reduced by 20-30% with caching

### Phase 3 Completion
- [ ] All logs output as structured JSON
- [ ] Test coverage exceeds 80%
- [ ] Docker health checks validate full system state

---

## Post-Implementation

### Documentation Updates
- [ ] Update README.md with new features
- [ ] Update API documentation for new parameters
- [ ] Add performance benchmarks to docs
- [ ] Document configuration options for cache/retry

### Deployment
- [ ] Build new Docker image
- [ ] Test in staging environment
- [ ] Monitor metrics after deployment
- [ ] Collect performance data

### Monitoring
- [ ] Set up metrics collection for cache hit rate
- [ ] Monitor API retry success rate
- [ ] Track MaTTS parallel performance improvements
- [ ] Monitor memory retrieval quality

---

## Priority Order for Maximum Impact

1. **Start Here:** Fix MaTTS parallel mode (biggest performance gain)
2. **Then:** Apply retry logic (biggest reliability gain)
3. **Then:** Add API key validation (prevent runtime failures)
4. **Then:** Implement caching (cost reduction)
5. **Then:** Everything else (quality improvements)

**Total Estimated Time:** 18-21 hours across all phases
**Critical Path:** 5-6 hours (Phase 1 only)
