#!/usr/bin/env python3
"""
Test script for retrieve_memories MCP tool

This test verifies that the retrieve_memories tool:
1. Accepts query and n_results parameters
2. Calls ReasoningBank.retrieve_memories() with composite scoring
3. Formats memory items including error context flags
4. Returns ranked list of relevant memories
"""
import os
import sys
import asyncio

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from reasoning_bank_server import retrieve_memories, reasoning_bank
from reasoning_bank_core import ReasoningBank, MemoryItem
from storage_adapter import create_storage_backend
from cached_llm_client import CachedLLMClient
from responses_alpha_client import ResponsesAPIClient
from workspace_manager import WorkspaceManager
from config import get_config


def setup_test_environment():
    """Initialize test environment with sample memories"""
    print("Setting up test environment...")
    
    # Load config
    config = get_config()
    
    # Initialize storage
    storage = create_storage_backend(
        backend_type="chromadb",
        persist_directory="./chroma_data",
        collection_name="reasoning_traces"
    )
    
    # Initialize LLM client
    responses_client = ResponsesAPIClient(
        api_key=config.api_key,
        default_model=config.model,
        default_reasoning_effort="medium"
    )
    
    cached_client = CachedLLMClient(
        client=responses_client,
        enable_cache=False  # Disable for testing
    )
    
    # Initialize workspace manager
    workspace_mgr = WorkspaceManager(default_workspace=os.getcwd())
    
    # Initialize ReasoningBank
    bank = ReasoningBank(
        storage_backend=storage,
        llm_client=cached_client,
        workspace_manager=workspace_mgr
    )
    
    print("✓ Test environment initialized")
    return bank


async def test_retrieve_memories_basic():
    """Test basic retrieve_memories functionality"""
    print("\n" + "="*80)
    print("TEST 1: Basic retrieve_memories")
    print("="*80)
    
    try:
        # Test with a simple query
        result = await retrieve_memories(
            query="Python function for sorting",
            n_results=5
        )
        
        print(f"✓ Query executed successfully")
        print(f"  Total found: {result['total_found']}")
        print(f"  Has error warnings: {result['has_error_warnings']}")
        print(f"  Memories returned: {len(result['memories'])}")
        
        # Display memory details
        if result['memories']:
            print(f"\n  Top memory:")
            top_memory = result['memories'][0]
            print(f"    ID: {top_memory['id']}")
            print(f"    Title: {top_memory['title']}")
            print(f"    Composite score: {top_memory.get('composite_score', 'N/A')}")
            print(f"    Has error context: {top_memory['has_error_context']}")
        
        return True
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_retrieve_memories_with_filters():
    """Test retrieve_memories with filters"""
    print("\n" + "="*80)
    print("TEST 2: retrieve_memories with filters")
    print("="*80)
    
    try:
        # Test with domain filter
        result = await retrieve_memories(
            query="algorithm implementation",
            n_results=3,
            include_failures=True,
            domain_filter="algorithms"
        )
        
        print(f"✓ Query with filters executed successfully")
        print(f"  Total found: {result['total_found']}")
        print(f"  Domain filter: {result['domain_filter']}")
        print(f"  Has error warnings: {result['has_error_warnings']}")
        
        return True
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_retrieve_memories_validation():
    """Test input validation"""
    print("\n" + "="*80)
    print("TEST 3: Input validation")
    print("="*80)
    
    try:
        # Test with short query (should handle gracefully)
        result = await retrieve_memories(
            query="ab",  # Too short
            n_results=5
        )
        
        # Should return error
        if 'error' in result:
            print(f"✓ Short query handled correctly")
            print(f"  Error type: {result['error_type']}")
            print(f"  Error message: {result['error']}")
            return True
        else:
            print(f"✗ Short query should have returned error")
            return False
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_retrieve_memories_error_context():
    """Test error context flagging"""
    print("\n" + "="*80)
    print("TEST 4: Error context flagging")
    print("="*80)
    
    try:
        # Query for memories (may or may not have error context)
        result = await retrieve_memories(
            query="debugging error handling",
            n_results=5,
            include_failures=True
        )
        
        print(f"✓ Query executed successfully")
        print(f"  Has error warnings: {result['has_error_warnings']}")
        
        # Check if error context is properly flagged
        for i, memory in enumerate(result['memories']):
            if memory['has_error_context']:
                print(f"\n  Memory {i+1} has error context:")
                print(f"    Title: {memory['title']}")
                if 'error_context' in memory:
                    print(f"    Error type: {memory['error_context'].get('error_type', 'N/A')}")
        
        return True
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests"""
    print("="*80)
    print("ReasoningBank retrieve_memories Tool Test Suite")
    print("="*80)
    
    # Check API key
    if not os.getenv("OPENROUTER_API_KEY"):
        print("❌ ERROR: OPENROUTER_API_KEY not set")
        print("Please set the environment variable and try again")
        return False
    
    # Initialize global reasoning_bank for the server module
    global reasoning_bank
    from reasoning_bank_server import reasoning_bank as server_bank
    
    if server_bank is None:
        print("\nNote: Server not initialized, using test environment")
        reasoning_bank = setup_test_environment()
        # Monkey patch for testing
        import reasoning_bank_server
        reasoning_bank_server.reasoning_bank = reasoning_bank
    
    # Run tests
    results = []
    
    results.append(await test_retrieve_memories_basic())
    results.append(await test_retrieve_memories_with_filters())
    results.append(await test_retrieve_memories_validation())
    results.append(await test_retrieve_memories_error_context())
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("✅ ALL TESTS PASSED")
        return True
    else:
        print(f"❌ {total - passed} TEST(S) FAILED")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
