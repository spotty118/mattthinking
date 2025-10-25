"""
Basic verification test for CachedLLMClient implementation.

This script tests core functionality:
- Cache key generation
- Cache hit/miss logic
- TTL expiration
- LRU eviction
- Statistics tracking
"""

import time
from unittest.mock import Mock, MagicMock
from cached_llm_client import CachedLLMClient, CacheStatistics
from responses_alpha_client import ResponsesAPIResult


def test_cache_key_generation():
    """Test that cache keys are deterministic and unique."""
    print("Testing cache key generation...")
    
    # Create mock client
    mock_client = Mock()
    mock_client.default_model = "test-model"
    
    cached_client = CachedLLMClient(mock_client)
    
    # Same parameters should produce same key
    key1 = cached_client._generate_cache_key(
        model="test-model",
        messages=[{"role": "user", "content": "test"}],
        temperature=0.0,
        max_tokens=100,
        max_output_tokens=None,
        reasoning_effort="medium"
    )
    
    key2 = cached_client._generate_cache_key(
        model="test-model",
        messages=[{"role": "user", "content": "test"}],
        temperature=0.0,
        max_tokens=100,
        max_output_tokens=None,
        reasoning_effort="medium"
    )
    
    assert key1 == key2, "Same parameters should produce same cache key"
    
    # Different parameters should produce different key
    key3 = cached_client._generate_cache_key(
        model="test-model",
        messages=[{"role": "user", "content": "different"}],
        temperature=0.0,
        max_tokens=100,
        max_output_tokens=None,
        reasoning_effort="medium"
    )
    
    assert key1 != key3, "Different parameters should produce different cache key"
    
    print("✓ Cache key generation works correctly")


def test_cache_hit_miss():
    """Test cache hit and miss logic."""
    print("\nTesting cache hit/miss logic...")
    
    # Create mock client
    mock_client = Mock()
    mock_client.default_model = "test-model"
    
    # Mock the create method to return a result
    mock_result = ResponsesAPIResult(
        content="test response",
        reasoning_tokens=100,
        output_tokens=50,
        input_tokens=20,
        total_tokens=170,
        model="test-model",
        finish_reason="stop"
    )
    mock_client.create = Mock(return_value=mock_result)
    
    cached_client = CachedLLMClient(mock_client, max_cache_size=10, ttl_seconds=60)
    
    messages = [{"role": "user", "content": "test"}]
    
    # First call should be a cache miss
    result1 = cached_client.create(
        model="test-model",
        messages=messages,
        temperature=0.0
    )
    
    assert mock_client.create.call_count == 1, "First call should hit API"
    assert result1.content == "test response"
    
    # Second call with same parameters should be a cache hit
    result2 = cached_client.create(
        model="test-model",
        messages=messages,
        temperature=0.0
    )
    
    assert mock_client.create.call_count == 1, "Second call should use cache"
    assert result2.content == "test response"
    
    # Check statistics
    stats = cached_client.get_statistics()
    assert stats.cache_hits == 1, f"Expected 1 cache hit, got {stats.cache_hits}"
    assert stats.cache_misses == 1, f"Expected 1 cache miss, got {stats.cache_misses}"
    assert stats.hit_rate == 0.5, f"Expected 50% hit rate, got {stats.hit_rate}"
    
    print("✓ Cache hit/miss logic works correctly")


def test_non_deterministic_bypass():
    """Test that non-deterministic calls (temperature != 0.0) bypass cache."""
    print("\nTesting non-deterministic bypass...")
    
    # Create mock client
    mock_client = Mock()
    mock_client.default_model = "test-model"
    
    mock_result = ResponsesAPIResult(
        content="test response",
        reasoning_tokens=100,
        output_tokens=50,
        input_tokens=20,
        total_tokens=170,
        model="test-model",
        finish_reason="stop"
    )
    mock_client.create = Mock(return_value=mock_result)
    
    cached_client = CachedLLMClient(mock_client)
    
    messages = [{"role": "user", "content": "test"}]
    
    # Call with temperature != 0.0 should bypass cache
    result1 = cached_client.create(
        model="test-model",
        messages=messages,
        temperature=0.7
    )
    
    result2 = cached_client.create(
        model="test-model",
        messages=messages,
        temperature=0.7
    )
    
    # Both calls should hit the API
    assert mock_client.create.call_count == 2, "Non-deterministic calls should bypass cache"
    
    # Check statistics
    stats = cached_client.get_statistics()
    assert stats.cache_bypassed == 2, f"Expected 2 bypassed calls, got {stats.cache_bypassed}"
    assert stats.cache_hits == 0, "No cache hits expected for non-deterministic calls"
    
    print("✓ Non-deterministic bypass works correctly")


def test_ttl_expiration():
    """Test that cache entries expire based on TTL."""
    print("\nTesting TTL expiration...")
    
    # Create mock client
    mock_client = Mock()
    mock_client.default_model = "test-model"
    
    mock_result = ResponsesAPIResult(
        content="test response",
        reasoning_tokens=100,
        output_tokens=50,
        input_tokens=20,
        total_tokens=170,
        model="test-model",
        finish_reason="stop"
    )
    mock_client.create = Mock(return_value=mock_result)
    
    # Use very short TTL for testing
    cached_client = CachedLLMClient(mock_client, ttl_seconds=1)
    
    messages = [{"role": "user", "content": "test"}]
    
    # First call - cache miss
    result1 = cached_client.create(
        model="test-model",
        messages=messages,
        temperature=0.0
    )
    
    assert mock_client.create.call_count == 1
    
    # Wait for TTL to expire
    time.sleep(1.5)
    
    # Second call after TTL - should be cache miss again
    result2 = cached_client.create(
        model="test-model",
        messages=messages,
        temperature=0.0
    )
    
    assert mock_client.create.call_count == 2, "Expired entry should trigger new API call"
    
    print("✓ TTL expiration works correctly")


def test_lru_eviction():
    """Test that LRU eviction works when cache is full."""
    print("\nTesting LRU eviction...")
    
    # Create mock client
    mock_client = Mock()
    mock_client.default_model = "test-model"
    
    mock_result = ResponsesAPIResult(
        content="test response",
        reasoning_tokens=100,
        output_tokens=50,
        input_tokens=20,
        total_tokens=170,
        model="test-model",
        finish_reason="stop"
    )
    mock_client.create = Mock(return_value=mock_result)
    
    # Small cache size for testing
    cached_client = CachedLLMClient(mock_client, max_cache_size=2)
    
    # Add 3 entries (should evict the first one)
    cached_client.create(
        model="test-model",
        messages=[{"role": "user", "content": "test1"}],
        temperature=0.0
    )
    
    cached_client.create(
        model="test-model",
        messages=[{"role": "user", "content": "test2"}],
        temperature=0.0
    )
    
    cached_client.create(
        model="test-model",
        messages=[{"role": "user", "content": "test3"}],
        temperature=0.0
    )
    
    # Cache should have max 2 entries
    assert cached_client.get_cache_size() <= 2, f"Cache size should be <= 2, got {cached_client.get_cache_size()}"
    
    # First entry should have been evicted, so this should be a cache miss
    mock_client.create.reset_mock()
    cached_client.create(
        model="test-model",
        messages=[{"role": "user", "content": "test1"}],
        temperature=0.0
    )
    
    assert mock_client.create.call_count == 1, "Evicted entry should trigger new API call"
    
    print("✓ LRU eviction works correctly")


def test_statistics():
    """Test statistics tracking."""
    print("\nTesting statistics tracking...")
    
    # Create mock client
    mock_client = Mock()
    mock_client.default_model = "test-model"
    
    mock_result = ResponsesAPIResult(
        content="test response",
        reasoning_tokens=100,
        output_tokens=50,
        input_tokens=20,
        total_tokens=170,
        model="test-model",
        finish_reason="stop"
    )
    mock_client.create = Mock(return_value=mock_result)
    
    cached_client = CachedLLMClient(mock_client)
    
    # Make various calls
    messages = [{"role": "user", "content": "test"}]
    
    # Cache miss
    cached_client.create(model="test-model", messages=messages, temperature=0.0)
    
    # Cache hit
    cached_client.create(model="test-model", messages=messages, temperature=0.0)
    
    # Bypassed (non-deterministic)
    cached_client.create(model="test-model", messages=messages, temperature=0.7)
    
    stats = cached_client.get_statistics()
    
    assert stats.cache_hits == 1
    assert stats.cache_misses == 1
    assert stats.cache_bypassed == 1
    assert stats.total_requests == 3
    assert stats.hit_rate == 0.5  # 1 hit out of 2 cacheable requests
    
    print(f"✓ Statistics tracking works correctly: {stats}")


def run_all_tests():
    """Run all tests."""
    print("=" * 60)
    print("Running CachedLLMClient verification tests")
    print("=" * 60)
    
    try:
        test_cache_key_generation()
        test_cache_hit_miss()
        test_non_deterministic_bypass()
        test_ttl_expiration()
        test_lru_eviction()
        test_statistics()
        
        print("\n" + "=" * 60)
        print("✓ All tests passed!")
        print("=" * 60)
        return True
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        return False
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
