#!/usr/bin/env python3
"""
Basic test script for IterativeReasoningAgent

This script validates:
- IterativeReasoningAgent class initialization
- solve_task() method structure
- Loop detection mechanism
- Token estimation and truncation
- Trajectory tracking
"""

import os
import sys

# Set up environment
if not os.getenv("OPENROUTER_API_KEY"):
    print("⚠️  OPENROUTER_API_KEY not set, using placeholder")
    os.environ["OPENROUTER_API_KEY"] = "test-key"

from iterative_agent import IterativeReasoningAgent, SolutionResult, IterationResult
from reasoning_bank_core import ReasoningBank, MemoryItem
from storage_adapter import ChromaDBAdapter
from cached_llm_client import CachedLLMClient
from responses_alpha_client import ResponsesAPIClient


def test_agent_initialization():
    """Test 1: Agent initialization"""
    print("\n" + "="*70)
    print("TEST 1: Agent Initialization")
    print("="*70)
    
    try:
        # Initialize components
        storage = ChromaDBAdapter(persist_directory="./chroma_data")
        llm_client = CachedLLMClient(
            ResponsesAPIClient(api_key=os.getenv("OPENROUTER_API_KEY"))
        )
        bank = ReasoningBank(storage_backend=storage, llm_client=llm_client)
        
        # Create agent
        agent = IterativeReasoningAgent(
            llm_client=llm_client,
            reasoning_bank=bank,
            max_iterations=3,
            success_threshold=0.8
        )
        
        print("\n✅ Agent initialized successfully:")
        print(f"   Max iterations: {agent.max_iterations}")
        print(f"   Success threshold: {agent.success_threshold}")
        print(f"   Temperature (generate): {agent.temperature_generate}")
        print(f"   Temperature (evaluate): {agent.temperature_evaluate}")
        print(f"   Max output tokens: {agent.max_output_tokens}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_token_estimation():
    """Test 2: Token estimation"""
    print("\n" + "="*70)
    print("TEST 2: Token Estimation")
    print("="*70)
    
    try:
        # Initialize components
        storage = ChromaDBAdapter(persist_directory="./chroma_data")
        llm_client = CachedLLMClient(
            ResponsesAPIClient(api_key=os.getenv("OPENROUTER_API_KEY"))
        )
        bank = ReasoningBank(storage_backend=storage, llm_client=llm_client)
        agent = IterativeReasoningAgent(llm_client=llm_client, reasoning_bank=bank)
        
        # Test token estimation
        short_text = "Hello world"
        long_text = "a" * 1000
        
        short_tokens = agent._estimate_tokens(short_text)
        long_tokens = agent._estimate_tokens(long_text)
        
        print(f"\n✅ Token estimation working:")
        print(f"   Short text ({len(short_text)} chars): ~{short_tokens} tokens")
        print(f"   Long text ({len(long_text)} chars): ~{long_tokens} tokens")
        
        # Verify estimation is reasonable (4 chars/token heuristic)
        assert short_tokens == len(short_text) // 4
        assert long_tokens == len(long_text) // 4
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_prompt_truncation():
    """Test 3: Prompt truncation"""
    print("\n" + "="*70)
    print("TEST 3: Prompt Truncation")
    print("="*70)
    
    try:
        # Initialize components
        storage = ChromaDBAdapter(persist_directory="./chroma_data")
        llm_client = CachedLLMClient(
            ResponsesAPIClient(api_key=os.getenv("OPENROUTER_API_KEY"))
        )
        bank = ReasoningBank(storage_backend=storage, llm_client=llm_client)
        agent = IterativeReasoningAgent(llm_client=llm_client, reasoning_bank=bank)
        
        # Create a long prompt
        long_prompt = "x" * 100000  # 100k chars
        max_tokens = 1000
        
        truncated = agent._truncate_prompt(long_prompt, max_tokens)
        
        print(f"\n✅ Prompt truncation working:")
        print(f"   Original: {len(long_prompt)} chars")
        print(f"   Truncated: {len(truncated)} chars")
        print(f"   Max tokens: {max_tokens} (~{max_tokens * 4} chars)")
        
        # Verify truncation happened
        assert len(truncated) < len(long_prompt)
        assert "[... Content truncated" in truncated
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_trajectory_hashing():
    """Test 4: Trajectory hashing for loop detection"""
    print("\n" + "="*70)
    print("TEST 4: Trajectory Hashing (Loop Detection)")
    print("="*70)
    
    try:
        # Initialize components
        storage = ChromaDBAdapter(persist_directory="./chroma_data")
        llm_client = CachedLLMClient(
            ResponsesAPIClient(api_key=os.getenv("OPENROUTER_API_KEY"))
        )
        bank = ReasoningBank(storage_backend=storage, llm_client=llm_client)
        agent = IterativeReasoningAgent(llm_client=llm_client, reasoning_bank=bank)
        
        # Test hashing
        solution1 = "def factorial(n): return 1 if n <= 1 else n * factorial(n-1)"
        solution2 = "def factorial(n): return 1 if n <= 1 else n * factorial(n-1)"
        solution3 = "def factorial(n): return n * factorial(n-1) if n > 1 else 1"
        
        hash1 = agent._compute_trajectory_hash(solution1)
        hash2 = agent._compute_trajectory_hash(solution2)
        hash3 = agent._compute_trajectory_hash(solution3)
        
        print(f"\n✅ Trajectory hashing working:")
        print(f"   Solution 1 hash: {hash1}")
        print(f"   Solution 2 hash: {hash2}")
        print(f"   Solution 3 hash: {hash3}")
        
        # Verify identical solutions have same hash
        assert hash1 == hash2, "Identical solutions should have same hash"
        
        # Verify different solutions have different hashes
        assert hash1 != hash3, "Different solutions should have different hashes"
        
        print("\n   ✓ Identical solutions: same hash")
        print("   ✓ Different solutions: different hashes")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_prompt_building():
    """Test 5: Prompt building for generation and refinement"""
    print("\n" + "="*70)
    print("TEST 5: Prompt Building")
    print("="*70)
    
    try:
        # Initialize components
        storage = ChromaDBAdapter(persist_directory="./chroma_data")
        llm_client = CachedLLMClient(
            ResponsesAPIClient(api_key=os.getenv("OPENROUTER_API_KEY"))
        )
        bank = ReasoningBank(storage_backend=storage, llm_client=llm_client)
        agent = IterativeReasoningAgent(llm_client=llm_client, reasoning_bank=bank)
        
        # Test generation prompt
        task = "Write a function to calculate fibonacci numbers"
        memories = []
        
        gen_prompt = agent._build_generation_prompt(task, memories)
        
        print("\n✅ Generation prompt built:")
        print(f"   Length: {len(gen_prompt)} chars")
        assert "# Task" in gen_prompt
        assert task in gen_prompt
        assert "# Solution" in gen_prompt
        print("   ✓ Contains task section")
        print("   ✓ Contains solution section")
        
        # Test refinement prompt
        previous_solution = "def fib(n): return n"
        feedback = "Missing recursive case"
        
        ref_prompt = agent._build_refinement_prompt(
            task, previous_solution, feedback, memories
        )
        
        print("\n✅ Refinement prompt built:")
        print(f"   Length: {len(ref_prompt)} chars")
        assert "# Task" in ref_prompt
        assert "# Previous Solution" in ref_prompt
        assert "# Evaluation Feedback" in ref_prompt
        assert previous_solution in ref_prompt
        assert feedback in ref_prompt
        print("   ✓ Contains task section")
        print("   ✓ Contains previous solution")
        print("   ✓ Contains feedback")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_evaluation_parsing():
    """Test 6: Evaluation response parsing"""
    print("\n" + "="*70)
    print("TEST 6: Evaluation Response Parsing")
    print("="*70)
    
    try:
        # Initialize components
        storage = ChromaDBAdapter(persist_directory="./chroma_data")
        llm_client = CachedLLMClient(
            ResponsesAPIClient(api_key=os.getenv("OPENROUTER_API_KEY"))
        )
        bank = ReasoningBank(storage_backend=storage, llm_client=llm_client)
        agent = IterativeReasoningAgent(llm_client=llm_client, reasoning_bank=bank)
        
        # Test valid evaluation response
        response1 = """Score: 0.85
Feedback: Good solution but could improve error handling"""
        
        score1, feedback1 = agent._parse_evaluation_response(response1)
        
        print("\n✅ Evaluation parsing working:")
        print(f"   Response: {response1[:50]}...")
        print(f"   Parsed score: {score1}")
        print(f"   Parsed feedback: {feedback1[:50]}...")
        
        assert score1 == 0.85
        assert "error handling" in feedback1
        
        # Test score clamping
        response2 = """Score: 1.5
Feedback: Excellent"""
        
        score2, feedback2 = agent._parse_evaluation_response(response2)
        assert score2 == 1.0, "Score should be clamped to 1.0"
        print("\n   ✓ Score clamping works (1.5 → 1.0)")
        
        # Test malformed response
        response3 = "This is a malformed response without proper format"
        score3, feedback3 = agent._parse_evaluation_response(response3)
        assert 0.0 <= score3 <= 1.0, "Should return valid score even for malformed input"
        print("   ✓ Handles malformed responses gracefully")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_state_reset():
    """Test 7: Agent state reset"""
    print("\n" + "="*70)
    print("TEST 7: Agent State Reset")
    print("="*70)
    
    try:
        # Initialize components
        storage = ChromaDBAdapter(persist_directory="./chroma_data")
        llm_client = CachedLLMClient(
            ResponsesAPIClient(api_key=os.getenv("OPENROUTER_API_KEY"))
        )
        bank = ReasoningBank(storage_backend=storage, llm_client=llm_client)
        agent = IterativeReasoningAgent(llm_client=llm_client, reasoning_bank=bank)
        
        # Add some state
        agent._trajectory_hashes.add("hash1")
        agent._trajectory_hashes.add("hash2")
        agent._total_tokens_used = 1000
        
        print(f"\n   Before reset:")
        print(f"   Trajectory hashes: {len(agent._trajectory_hashes)}")
        print(f"   Total tokens: {agent._total_tokens_used}")
        
        # Reset state
        agent.reset_state()
        
        print(f"\n✅ State reset successfully:")
        print(f"   Trajectory hashes: {len(agent._trajectory_hashes)}")
        print(f"   Total tokens: {agent._total_tokens_used}")
        
        assert len(agent._trajectory_hashes) == 0
        assert agent._total_tokens_used == 0
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("TESTING ITERATIVE REASONING AGENT")
    print("="*70)
    
    results = []
    
    # Run tests
    results.append(("Agent Initialization", test_agent_initialization()))
    results.append(("Token Estimation", test_token_estimation()))
    results.append(("Prompt Truncation", test_prompt_truncation()))
    results.append(("Trajectory Hashing", test_trajectory_hashing()))
    results.append(("Prompt Building", test_prompt_building()))
    results.append(("Evaluation Parsing", test_evaluation_parsing()))
    results.append(("State Reset", test_state_reset()))
    
    # Print summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
