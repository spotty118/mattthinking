"""
Configuration management for ReasoningBank MCP Server

This module provides centralized configuration with:
- Environment variable loading
- Pydantic validation
- Type safety
- Default values
"""

import os
from typing import Optional
from schemas import (
    ReasoningBankConfig,
    TokenBudgetConfig,
    ReasoningEffort,
    StorageBackend
)


def load_config_from_env() -> ReasoningBankConfig:
    """
    Load configuration from environment variables with fallback to defaults
    
    Environment variables:
        OPENROUTER_API_KEY: API key for OpenRouter
        REASONING_MODEL: Model identifier (default: google/gemini-2.5-pro)
        REASONING_EFFORT: Reasoning effort level (minimal, low, medium, high)
        MAX_ITERATIONS: Maximum refinement iterations
        SUCCESS_THRESHOLD: Quality threshold for success (0.0-1.0)
        RETRIEVAL_K: Number of memories to retrieve
        MAX_MEMORY_ITEMS: Max memory items per trace
        TEMPERATURE_GENERATE: Temperature for generation
        TEMPERATURE_JUDGE: Temperature for judging
        REASONING_BANK_DATA: ChromaDB storage directory
        REASONING_BANK_TRACES: Traces storage directory
        RETRY_ATTEMPTS: Number of API retry attempts
        RETRY_MIN_WAIT: Minimum wait between retries (seconds)
        RETRY_MAX_WAIT: Maximum wait between retries (seconds)
        ENABLE_CACHE: Enable LLM response caching (true/false)
        CACHE_SIZE: Maximum cache entries
        CACHE_TTL_SECONDS: Cache entry TTL
    
    Returns:
        Validated ReasoningBankConfig instance
    
    Raises:
        ValidationError: If configuration validation fails
    """
    
    # Parse reasoning effort from env
    reasoning_effort_str = os.getenv("REASONING_EFFORT", "medium").lower()
    try:
        reasoning_effort = ReasoningEffort(reasoning_effort_str)
    except ValueError:
        reasoning_effort = ReasoningEffort.MEDIUM
    
    # Parse storage backend from env
    storage_backend_str = os.getenv("STORAGE_BACKEND", "chromadb").lower()
    try:
        storage_backend = StorageBackend(storage_backend_str)
    except ValueError:
        storage_backend = StorageBackend.CHROMADB
    
    # Build token budget config
    token_budget = TokenBudgetConfig(
        max_output_tokens=int(os.getenv("MAX_OUTPUT_TOKENS", "9000")),
        max_prompt_tokens=int(os.getenv("MAX_PROMPT_TOKENS", "12000")),
        generation_tokens=int(os.getenv("GENERATION_TOKENS", "8000")),
        evaluation_tokens=int(os.getenv("EVALUATION_TOKENS", "3000")),
        judgment_tokens=int(os.getenv("JUDGMENT_TOKENS", "4000")),
        memory_extraction_tokens=int(os.getenv("MEMORY_EXTRACTION_TOKENS", "6000")),
        truncation_threshold=int(os.getenv("TRUNCATION_THRESHOLD", "12000")),
        truncation_head_ratio=float(os.getenv("TRUNCATION_HEAD_RATIO", "0.6"))
    )
    
    # Build main config
    config = ReasoningBankConfig(
        model=os.getenv("REASONING_MODEL", "google/gemini-2.5-pro"),
        reasoning_effort=reasoning_effort,
        api_key=os.getenv("OPENROUTER_API_KEY"),
        token_budget=token_budget,
        retrieval_k=int(os.getenv("RETRIEVAL_K", "3")),
        max_memory_items=int(os.getenv("MAX_MEMORY_ITEMS", "3")),
        max_iterations=int(os.getenv("MAX_ITERATIONS", "3")),
        success_threshold=float(os.getenv("SUCCESS_THRESHOLD", "0.8")),
        temperature_generate=float(os.getenv("TEMPERATURE_GENERATE", "0.7")),
        temperature_judge=float(os.getenv("TEMPERATURE_JUDGE", "0.0")),
        # Storage backend selection
        storage_backend=storage_backend,
        # ChromaDB configuration
        persist_directory=os.getenv("REASONING_BANK_DATA", "./chroma_data"),
        traces_directory=os.getenv("REASONING_BANK_TRACES", "./traces"),
        collection_name=os.getenv("COLLECTION_NAME", "reasoning_memories"),
        # Supabase configuration
        supabase_url=os.getenv("SUPABASE_URL"),
        supabase_key=os.getenv("SUPABASE_KEY"),
        supabase_traces_table=os.getenv("SUPABASE_TRACES_TABLE", "reasoning_traces"),
        supabase_memories_table=os.getenv("SUPABASE_MEMORIES_TABLE", "memory_items"),
        # Retry configuration
        retry_attempts=int(os.getenv("RETRY_ATTEMPTS", "3")),
        retry_min_wait=int(os.getenv("RETRY_MIN_WAIT", "2")),
        retry_max_wait=int(os.getenv("RETRY_MAX_WAIT", "10")),
        # Cache configuration
        enable_cache=os.getenv("ENABLE_CACHE", "true").lower() == "true",
        cache_size=int(os.getenv("CACHE_SIZE", "100")),
        cache_ttl_seconds=int(os.getenv("CACHE_TTL_SECONDS", "3600"))
    )
    
    return config


def get_config() -> ReasoningBankConfig:
    """
    Get validated configuration instance
    
    This is the main entry point for accessing configuration.
    Call this once at application startup and reuse the instance.
    
    Returns:
        Validated ReasoningBankConfig
    """
    return load_config_from_env()


# Convenience function for backwards compatibility
def get_token_budget() -> TokenBudgetConfig:
    """Get token budget configuration"""
    config = get_config()
    return config.token_budget


if __name__ == "__main__":
    # Test configuration loading
    print("=== ReasoningBank Configuration ===\n")
    
    config = get_config()
    
    print(f"Model: {config.model}")
    print(f"Reasoning Effort: {config.reasoning_effort.value}")
    print(f"Max Iterations: {config.max_iterations}")
    print(f"Success Threshold: {config.success_threshold}")
    print(f"Retrieval K: {config.retrieval_k}")
    print(f"\nToken Budget:")
    print(f"  Max Output Tokens: {config.token_budget.max_output_tokens}")
    print(f"  Generation Tokens: {config.token_budget.generation_tokens}")
    print(f"  Evaluation Tokens: {config.token_budget.evaluation_tokens}")
    print(f"\nRetry Configuration:")
    print(f"  Attempts: {config.retry_attempts}")
    print(f"  Min Wait: {config.retry_min_wait}s")
    print(f"  Max Wait: {config.retry_max_wait}s")
    print(f"\nCache Configuration:")
    print(f"  Enabled: {config.enable_cache}")
    print(f"  Size: {config.cache_size}")
    print(f"  TTL: {config.cache_ttl_seconds}s")
    print(f"\nStorage:")
    print(f"  Data Directory: {config.persist_directory}")
    print(f"  Traces Directory: {config.traces_directory}")
    
    # Validate API key
    if config.api_key:
        print(f"\n✅ API Key: Configured (length: {len(config.api_key)})")
    else:
        print("\n⚠️  API Key: Not configured (set OPENROUTER_API_KEY)")
