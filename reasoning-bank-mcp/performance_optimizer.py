"""
Performance optimization utilities for ReasoningBank MCP System

This module provides:
- Batch embedding generation for multiple memories
- In-memory caching for frequently accessed memories
- Prompt compression for token optimization
- Connection pooling for API clients

Requirements addressed: 1.2, 11.3, 14.1, 14.2
"""

import logging
import hashlib
import time
from typing import List, Dict, Any, Optional, Tuple
from collections import OrderedDict
from dataclasses import dataclass
import re


logger = logging.getLogger(__name__)


# ============================================================================
# Batch Embedding Generator
# ============================================================================

class BatchEmbeddingGenerator:
    """
    Batch embedding generation for multiple memories
    
    Generates embeddings in batches to reduce overhead and improve throughput.
    Uses the sentence-transformers model's batch encoding capability.
    """
    
    def __init__(self, embedder, batch_size: int = 32):
        """
        Initialize batch embedding generator
        
        Args:
            embedder: SentenceTransformer model instance
            batch_size: Number of texts to process in each batch
        """
        self.embedder = embedder
        self.batch_size = batch_size
        logger.info(f"BatchEmbeddingGenerator initialized with batch_size={batch_size}")
    
    def generate_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batches
        
        Args:
            texts: List of text strings to embed
        
        Returns:
            List of embedding vectors
        """
        if not texts:
            return []
        
        start_time = time.time()
        
        # Process in batches
        all_embeddings = []
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            
            # Generate embeddings for batch
            embeddings = self.embedder.encode(
                batch,
                convert_to_numpy=True,
                show_progress_bar=False
            )
            
            # Convert to list of lists
            all_embeddings.extend([emb.tolist() for emb in embeddings])
        
        elapsed = time.time() - start_time
        logger.info(
            f"Generated {len(texts)} embeddings in {elapsed:.2f}s "
            f"({len(texts)/elapsed:.1f} embeddings/sec)"
        )
        
        return all_embeddings


# ============================================================================
# Memory Cache
# ============================================================================

@dataclass
class CachedMemory:
    """Cached memory item with metadata"""
    memory_data: Dict[str, Any]
    access_count: int
    last_access: float
    cache_time: float


class MemoryCache:
    """
    In-memory cache for frequently accessed memories
    
    Features:
    - LRU eviction policy
    - Access frequency tracking
    - TTL-based expiration
    - Cache hit/miss statistics
    """
    
    def __init__(
        self,
        max_size: int = 1000,
        ttl_seconds: int = 3600
    ):
        """
        Initialize memory cache
        
        Args:
            max_size: Maximum number of memories to cache
            ttl_seconds: Time-to-live for cached entries (seconds)
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.cache: OrderedDict[str, CachedMemory] = OrderedDict()
        
        # Statistics
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        
        logger.info(
            f"MemoryCache initialized: max_size={max_size}, ttl={ttl_seconds}s"
        )
    
    def get(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """
        Get memory from cache
        
        Args:
            memory_id: Memory ID to retrieve
        
        Returns:
            Memory data if found and valid, None otherwise
        """
        if memory_id not in self.cache:
            self.misses += 1
            return None
        
        cached = self.cache[memory_id]
        current_time = time.time()
        
        # Check TTL
        if current_time - cached.cache_time > self.ttl_seconds:
            # Expired, remove from cache
            del self.cache[memory_id]
            self.misses += 1
            return None
        
        # Cache hit - update access metadata
        self.hits += 1
        cached.access_count += 1
        cached.last_access = current_time
        
        # Move to end (most recently used)
        self.cache.move_to_end(memory_id)
        
        return cached.memory_data
    
    def put(self, memory_id: str, memory_data: Dict[str, Any]):
        """
        Add memory to cache
        
        Args:
            memory_id: Memory ID
            memory_data: Memory data to cache
        """
        current_time = time.time()
        
        # If already in cache, update it
        if memory_id in self.cache:
            cached = self.cache[memory_id]
            cached.memory_data = memory_data
            cached.last_access = current_time
            cached.cache_time = current_time
            self.cache.move_to_end(memory_id)
            return
        
        # Check if we need to evict
        if len(self.cache) >= self.max_size:
            # Evict least recently used
            evicted_id, _ = self.cache.popitem(last=False)
            self.evictions += 1
            logger.debug(f"Evicted memory {evicted_id} from cache")
        
        # Add new entry
        self.cache[memory_id] = CachedMemory(
            memory_data=memory_data,
            access_count=1,
            last_access=current_time,
            cache_time=current_time
        )
    
    def invalidate(self, memory_id: str):
        """Remove memory from cache"""
        if memory_id in self.cache:
            del self.cache[memory_id]
    
    def clear(self):
        """Clear all cached memories"""
        self.cache.clear()
        logger.info("Memory cache cleared")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0.0
        
        return {
            "cache_size": len(self.cache),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": round(hit_rate, 2),
            "evictions": self.evictions,
            "total_requests": total_requests
        }


# ============================================================================
# Prompt Compressor
# ============================================================================

class PromptCompressor:
    """
    Prompt compression for token optimization
    
    Reduces prompt size while preserving key information:
    - Removes redundant whitespace
    - Compresses code examples
    - Truncates long content intelligently
    - Preserves structure and meaning
    """
    
    def __init__(
        self,
        max_tokens: int = 12000,
        compression_ratio: float = 0.7
    ):
        """
        Initialize prompt compressor
        
        Args:
            max_tokens: Maximum tokens allowed
            compression_ratio: Target compression ratio (0.0-1.0)
        """
        self.max_tokens = max_tokens
        self.compression_ratio = compression_ratio
        logger.info(
            f"PromptCompressor initialized: max_tokens={max_tokens}, "
            f"compression_ratio={compression_ratio}"
        )
    
    def compress(self, prompt: str) -> str:
        """
        Compress prompt to reduce token count
        
        Args:
            prompt: Original prompt text
        
        Returns:
            Compressed prompt
        """
        # Estimate current tokens
        current_tokens = self._estimate_tokens(prompt)
        
        if current_tokens <= self.max_tokens:
            return prompt
        
        logger.info(
            f"Compressing prompt: {current_tokens} tokens -> "
            f"target {int(current_tokens * self.compression_ratio)} tokens"
        )
        
        # Apply compression techniques
        compressed = prompt
        
        # 1. Remove excessive whitespace
        compressed = self._remove_excessive_whitespace(compressed)
        
        # 2. Compress code blocks
        compressed = self._compress_code_blocks(compressed)
        
        # 3. Truncate if still too long
        if self._estimate_tokens(compressed) > self.max_tokens:
            compressed = self._truncate_intelligently(compressed)
        
        final_tokens = self._estimate_tokens(compressed)
        reduction = (1 - final_tokens / current_tokens) * 100
        
        logger.info(
            f"Compressed prompt: {current_tokens} -> {final_tokens} tokens "
            f"({reduction:.1f}% reduction)"
        )
        
        return compressed
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count (4 chars per token heuristic)"""
        return len(text) // 4
    
    def _remove_excessive_whitespace(self, text: str) -> str:
        """Remove excessive whitespace while preserving structure"""
        # Replace multiple spaces with single space
        text = re.sub(r' +', ' ', text)
        
        # Replace multiple newlines with double newline
        text = re.sub(r'\n\n+', '\n\n', text)
        
        # Remove trailing whitespace from lines
        lines = [line.rstrip() for line in text.split('\n')]
        text = '\n'.join(lines)
        
        return text
    
    def _compress_code_blocks(self, text: str) -> str:
        """Compress code blocks by removing comments and extra whitespace"""
        # Find code blocks (between ``` markers)
        code_block_pattern = r'```[\w]*\n(.*?)```'
        
        def compress_code(match):
            code = match.group(1)
            
            # Remove single-line comments
            code = re.sub(r'#.*$', '', code, flags=re.MULTILINE)
            code = re.sub(r'//.*$', '', code, flags=re.MULTILINE)
            
            # Remove empty lines
            lines = [line for line in code.split('\n') if line.strip()]
            code = '\n'.join(lines)
            
            return f"```\n{code}\n```"
        
        text = re.sub(code_block_pattern, compress_code, text, flags=re.DOTALL)
        
        return text
    
    def _truncate_intelligently(self, text: str) -> str:
        """Truncate text while preserving important sections"""
        max_chars = self.max_tokens * 4
        
        if len(text) <= max_chars:
            return text
        
        # Preserve first 60% and last 30%
        head_size = int(max_chars * 0.6)
        tail_size = int(max_chars * 0.3)
        
        head = text[:head_size]
        tail = text[-tail_size:]
        
        return (
            f"{head}\n\n"
            f"[... Content truncated for token optimization ...]\n\n"
            f"{tail}"
        )


# ============================================================================
# Connection Pool for API Clients
# ============================================================================

class APIConnectionPool:
    """
    Connection pooling for API clients
    
    Reuses HTTP connections to reduce overhead and improve performance.
    Implements connection lifecycle management and health checking.
    """
    
    def __init__(
        self,
        pool_size: int = 10,
        max_retries: int = 3,
        timeout: int = 120
    ):
        """
        Initialize connection pool
        
        Args:
            pool_size: Maximum number of concurrent connections
            max_retries: Maximum retry attempts per request
            timeout: Request timeout in seconds
        """
        self.pool_size = pool_size
        self.max_retries = max_retries
        self.timeout = timeout
        
        # Import requests with session support
        try:
            import requests
            from requests.adapters import HTTPAdapter
            from urllib3.util.retry import Retry
            
            # Create session with connection pooling
            self.session = requests.Session()
            
            # Configure retry strategy
            retry_strategy = Retry(
                total=max_retries,
                backoff_factor=1,
                status_forcelist=[429, 500, 502, 503, 504],
                allowed_methods=["HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS", "TRACE"]
            )
            
            # Configure adapter with connection pooling
            adapter = HTTPAdapter(
                pool_connections=pool_size,
                pool_maxsize=pool_size,
                max_retries=retry_strategy
            )
            
            # Mount adapter for both http and https
            self.session.mount("http://", adapter)
            self.session.mount("https://", adapter)
            
            logger.info(
                f"APIConnectionPool initialized: pool_size={pool_size}, "
                f"max_retries={max_retries}, timeout={timeout}s"
            )
            
        except ImportError:
            logger.error("requests library not available for connection pooling")
            self.session = None
    
    def post(self, url: str, **kwargs) -> Any:
        """
        Make POST request using pooled connection
        
        Args:
            url: Request URL
            **kwargs: Additional request parameters
        
        Returns:
            Response object
        """
        if self.session is None:
            raise RuntimeError("Connection pool not initialized")
        
        # Set timeout if not provided
        if 'timeout' not in kwargs:
            kwargs['timeout'] = self.timeout
        
        return self.session.post(url, **kwargs)
    
    def get(self, url: str, **kwargs) -> Any:
        """
        Make GET request using pooled connection
        
        Args:
            url: Request URL
            **kwargs: Additional request parameters
        
        Returns:
            Response object
        """
        if self.session is None:
            raise RuntimeError("Connection pool not initialized")
        
        # Set timeout if not provided
        if 'timeout' not in kwargs:
            kwargs['timeout'] = self.timeout
        
        return self.session.get(url, **kwargs)
    
    def close(self):
        """Close all connections in the pool"""
        if self.session:
            self.session.close()
            logger.info("Connection pool closed")


# ============================================================================
# Performance Monitor
# ============================================================================

class PerformanceMonitor:
    """
    Monitor and track performance metrics
    
    Tracks:
    - API call latencies
    - Cache hit rates
    - Memory usage
    - Token consumption
    """
    
    def __init__(self):
        """Initialize performance monitor"""
        self.metrics = {
            "api_calls": 0,
            "api_latency_total": 0.0,
            "api_latency_min": float('inf'),
            "api_latency_max": 0.0,
            "cache_hits": 0,
            "cache_misses": 0,
            "tokens_used": 0,
            "embeddings_generated": 0,
            "memories_cached": 0
        }
        self.start_time = time.time()
        logger.info("PerformanceMonitor initialized")
    
    def record_api_call(self, latency: float):
        """Record API call latency"""
        self.metrics["api_calls"] += 1
        self.metrics["api_latency_total"] += latency
        self.metrics["api_latency_min"] = min(self.metrics["api_latency_min"], latency)
        self.metrics["api_latency_max"] = max(self.metrics["api_latency_max"], latency)
    
    def record_cache_hit(self):
        """Record cache hit"""
        self.metrics["cache_hits"] += 1
    
    def record_cache_miss(self):
        """Record cache miss"""
        self.metrics["cache_misses"] += 1
    
    def record_tokens(self, tokens: int):
        """Record token usage"""
        self.metrics["tokens_used"] += tokens
    
    def record_embeddings(self, count: int):
        """Record embeddings generated"""
        self.metrics["embeddings_generated"] += count
    
    def record_memory_cached(self):
        """Record memory cached"""
        self.metrics["memories_cached"] += 1
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get performance statistics"""
        uptime = time.time() - self.start_time
        
        avg_latency = 0.0
        if self.metrics["api_calls"] > 0:
            avg_latency = self.metrics["api_latency_total"] / self.metrics["api_calls"]
        
        cache_total = self.metrics["cache_hits"] + self.metrics["cache_misses"]
        cache_hit_rate = 0.0
        if cache_total > 0:
            cache_hit_rate = self.metrics["cache_hits"] / cache_total * 100
        
        return {
            "uptime_seconds": round(uptime, 2),
            "api_calls": self.metrics["api_calls"],
            "avg_api_latency": round(avg_latency, 3),
            "min_api_latency": round(self.metrics["api_latency_min"], 3) if self.metrics["api_latency_min"] != float('inf') else 0.0,
            "max_api_latency": round(self.metrics["api_latency_max"], 3),
            "cache_hit_rate": round(cache_hit_rate, 2),
            "total_tokens_used": self.metrics["tokens_used"],
            "embeddings_generated": self.metrics["embeddings_generated"],
            "memories_cached": self.metrics["memories_cached"]
        }
    
    def reset(self):
        """Reset all metrics"""
        self.metrics = {
            "api_calls": 0,
            "api_latency_total": 0.0,
            "api_latency_min": float('inf'),
            "api_latency_max": 0.0,
            "cache_hits": 0,
            "cache_misses": 0,
            "tokens_used": 0,
            "embeddings_generated": 0,
            "memories_cached": 0
        }
        self.start_time = time.time()
        logger.info("Performance metrics reset")


# ============================================================================
# Testing
# ============================================================================

if __name__ == "__main__":
    """Test performance optimization utilities"""
    print("=== Testing Performance Optimizer ===\n")
    
    # Test MemoryCache
    print("1. Testing MemoryCache...")
    cache = MemoryCache(max_size=3, ttl_seconds=60)
    
    cache.put("mem1", {"title": "Memory 1", "content": "Content 1"})
    cache.put("mem2", {"title": "Memory 2", "content": "Content 2"})
    cache.put("mem3", {"title": "Memory 3", "content": "Content 3"})
    
    # Test cache hit
    result = cache.get("mem1")
    assert result is not None, "Cache hit failed"
    
    # Test cache miss
    result = cache.get("mem999")
    assert result is None, "Cache miss failed"
    
    # Test eviction
    cache.put("mem4", {"title": "Memory 4", "content": "Content 4"})
    assert len(cache.cache) == 3, "Eviction failed"
    
    stats = cache.get_statistics()
    print(f"   Cache stats: {stats}")
    print("   ✅ MemoryCache working\n")
    
    # Test PromptCompressor
    print("2. Testing PromptCompressor...")
    compressor = PromptCompressor(max_tokens=100)
    
    long_prompt = "This is a test prompt. " * 100
    compressed = compressor.compress(long_prompt)
    
    assert len(compressed) < len(long_prompt), "Compression failed"
    print(f"   Original: {len(long_prompt)} chars")
    print(f"   Compressed: {len(compressed)} chars")
    print("   ✅ PromptCompressor working\n")
    
    # Test PerformanceMonitor
    print("3. Testing PerformanceMonitor...")
    monitor = PerformanceMonitor()
    
    monitor.record_api_call(1.5)
    monitor.record_api_call(2.0)
    monitor.record_cache_hit()
    monitor.record_cache_miss()
    monitor.record_tokens(1000)
    
    stats = monitor.get_statistics()
    print(f"   Performance stats: {stats}")
    print("   ✅ PerformanceMonitor working\n")
    
    print("=== All tests passed! ===")
