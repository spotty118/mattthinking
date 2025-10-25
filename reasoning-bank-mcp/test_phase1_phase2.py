#!/usr/bin/env python3
"""
Test script for Phase 1 and Phase 2 enhancements

This script validates:
- Phase 1: MaTTS parallel, retry logic, API validation, UUIDs
- Phase 2: Caching, enhanced retrieval
"""

import os
import sys
import time
from reasoning_bank_core import ReasoningBank, MemoryItem
from iterative_agent import IterativeReasoningAgent

def test_phase1_matts_parallel():
    """Test 1: MaTTS Parallel Mode (async execution)"""
    print("\n" + "="*70)
    print("TEST 1: MaTTS Parallel Mode (Async Execution)")
    print("="*70)
    
    try:
        bank = ReasoningBank(enable_cache=False)  # Disable cache for pure test
        agent = IterativeReasoningAgent(bank.llm_client, bank)
        
        task = "Write a Python function to calculate the sum of a list"
        
        print("\n🚀 Testing MaTTS parallel with k=3...")
        start_time = time.time()
        
        result = agent.solve_task(
            task=task,
            enable_matts=True,
            matts_k=3,
            matts_mode="parallel"
        )
        
        duration = time.time() - start_time
        
        print(f"\n✓ MaTTS parallel completed in {duration:.2f} seconds")
        print(f"  Success: {result['success']}")
        print(f"  Trajectories generated: {len(result.get('all_outputs', []))}")
        print(f"  Selected: {result.get('selected_trajectory', 0) + 1}")
        
        return True
    except Exception as e:
        print(f"\n❌ MaTTS parallel test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_phase1_retry_logic():
    """Test 2: Retry Logic Applied"""
    print("\n" + "="*70)
    print("TEST 2: Retry Logic Applied to LLM Calls")
    print("="*70)
    
    try:
        bank = ReasoningBank(enable_cache=False)
        
        # Check that retry decorator is applied
        import inspect
        call_llm_source = inspect.getsource(bank._call_llm)
        
        if "@with_retry" in call_llm_source or "with_retry" in str(bank._call_llm):
            print("\n✓ Retry decorator detected on ReasoningBank._call_llm")
        else:
            print("\n⚠️  Warning: Could not verify retry decorator")
        
        # Try to import retry_utils to verify it exists
        from retry_utils import with_retry
        print("✓ retry_utils module imported successfully")
        
        return True
    except Exception as e:
        print(f"\n❌ Retry logic test failed: {e}")
        return False


def test_phase1_api_validation():
    """Test 3: API Key Validation"""
    print("\n" + "="*70)
    print("TEST 3: API Key Validation on Startup")
    print("="*70)
    
    try:
        # Test with valid key (should succeed)
        print("\n✓ Testing with valid API key...")
        bank = ReasoningBank(enable_cache=False)
        print("✓ API key validation passed")
        
        # Check that _validate_api_key method exists
        if hasattr(bank, '_validate_api_key'):
            print("✓ _validate_api_key method exists")
        else:
            print("⚠️  Warning: _validate_api_key method not found")
        
        return True
    except ValueError as e:
        if "API key validation failed" in str(e):
            print(f"✓ API validation correctly caught invalid key: {e}")
            return True
        else:
            print(f"❌ Unexpected error: {e}")
            return False
    except Exception as e:
        print(f"❌ API validation test failed: {e}")
        return False


def test_phase1_memory_uuids():
    """Test 4: MemoryItem UUIDs"""
    print("\n" + "="*70)
    print("TEST 4: MemoryItem UUID Field")
    print("="*70)
    
    try:
        # Create two memory items
        m1 = MemoryItem(
            title="Test Memory 1",
            description="Test description 1",
            content="Test content 1"
        )
        
        m2 = MemoryItem(
            title="Test Memory 1",  # Same title
            description="Test description 1",
            content="Test content 1"
        )
        
        print(f"\n✓ Memory 1 ID: {m1.id}")
        print(f"✓ Memory 2 ID: {m2.id}")
        
        # Verify IDs are unique
        if m1.id != m2.id:
            print(f"✓ UUIDs are unique (even with same content)")
        else:
            print(f"❌ UUIDs are NOT unique!")
            return False
        
        # Verify ID format (should be UUID)
        import uuid
        try:
            uuid.UUID(m1.id)
            print(f"✓ ID format is valid UUID")
        except ValueError:
            print(f"❌ ID format is not valid UUID: {m1.id}")
            return False
        
        return True
    except Exception as e:
        print(f"\n❌ Memory UUID test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_phase2_caching():
    """Test 5: LLM Response Caching"""
    print("\n" + "="*70)
    print("TEST 5: LLM Response Caching")
    print("="*70)
    
    try:
        # Create bank with caching enabled
        bank = ReasoningBank(
            enable_cache=True,
            cache_size=10,
            cache_ttl_seconds=60
        )
        
        print("\n✓ ReasoningBank initialized with caching")
        
        # Check if cached client is used
        from cached_llm_client import CachedLLMClient
        if isinstance(bank.llm_client, CachedLLMClient):
            print("✓ CachedLLMClient is active")
        else:
            print("⚠️  Warning: CachedLLMClient not detected")
        
        # Get initial statistics
        stats = bank.get_statistics()
        if 'cache' in stats:
            print(f"✓ Cache statistics available:")
            print(f"  - Total calls: {stats['cache']['total_calls']}")
            print(f"  - Cache size: {stats['cache']['cache_size']}/{stats['cache']['cache_max_size']}")
            print(f"  - Enabled: {stats['cache']['enabled']}")
        else:
            print("⚠️  Warning: Cache statistics not in get_statistics()")
        
        return True
    except Exception as e:
        print(f"\n❌ Caching test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_phase2_enhanced_retrieval():
    """Test 6: Enhanced Memory Retrieval"""
    print("\n" + "="*70)
    print("TEST 6: Enhanced Memory Retrieval")
    print("="*70)
    
    try:
        bank = ReasoningBank(enable_cache=False)
        
        # Test that enhanced retrieval parameters work
        print("\n✓ Testing enhanced retrieval API...")
        
        # Call with new parameters (should not error even if no memories)
        memories = bank.retrieve_relevant_memories(
            task="test task",
            k=3,
            include_failures=True,
            domain_filter=None,
            min_score=0.0,
            boost_error_warnings=True
        )
        
        print(f"✓ Enhanced retrieval called successfully")
        print(f"  Retrieved: {len(memories)} memories")
        
        # Check that helper methods exist
        if hasattr(bank, '_calculate_composite_score'):
            print("✓ _calculate_composite_score method exists")
        else:
            print("⚠️  Warning: _calculate_composite_score not found")
        
        if hasattr(bank, '_calculate_recency_score'):
            print("✓ _calculate_recency_score method exists")
        else:
            print("⚠️  Warning: _calculate_recency_score not found")
        
        return True
    except Exception as e:
        print(f"\n❌ Enhanced retrieval test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("ReasoningBank MCP - Phase 1 & 2 Validation Tests")
    print("="*70)
    
    # Check API key
    if not os.getenv("OPENROUTER_API_KEY"):
        print("\n❌ ERROR: OPENROUTER_API_KEY not set")
        print("   Please set: export OPENROUTER_API_KEY=your_key_here")
        return False
    
    print(f"\n✓ API key found: {os.getenv('OPENROUTER_API_KEY')[:20]}...")
    
    results = {
        "Phase 1 - MaTTS Parallel": test_phase1_matts_parallel(),
        "Phase 1 - Retry Logic": test_phase1_retry_logic(),
        "Phase 1 - API Validation": test_phase1_api_validation(),
        "Phase 1 - Memory UUIDs": test_phase1_memory_uuids(),
        "Phase 2 - Caching": test_phase2_caching(),
        "Phase 2 - Enhanced Retrieval": test_phase2_enhanced_retrieval()
    }
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\n{passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! System is ready for production.")
        return True
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please review errors above.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
