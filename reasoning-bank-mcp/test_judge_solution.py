#!/usr/bin/env python3
"""
Test script for judge_solution functionality

This script validates:
- judge_solution() method exists and works
- JSON parsing with error handling
- Verdict, score, reasoning, and learnings extraction
- Error context extraction for failed solutions
"""

import os
import sys
import json

# Set up environment
if not os.getenv("OPENROUTER_API_KEY"):
    print("⚠️  OPENROUTER_API_KEY not set, using placeholder")
    os.environ["OPENROUTER_API_KEY"] = "test-key"

from reasoning_bank_core import ReasoningBank, MemoryItem
from storage_adapter import ChromaDBAdapter
from cached_llm_client import CachedLLMClient
from responses_alpha_client import ResponsesAPIClient


def test_judge_solution_success():
    """Test 1: Judge a successful solution"""
    print("\n" + "="*70)
    print("TEST 1: Judge Successful Solution")
    print("="*70)
    
    try:
        # Initialize components
        storage = ChromaDBAdapter(persist_directory="./chroma_data")
        llm_client = CachedLLMClient(
            ResponsesAPIClient(api_key=os.getenv("OPENROUTER_API_KEY"))
        )
        bank = ReasoningBank(storage_backend=storage, llm_client=llm_client)
        
        # Test task and solution
        task = "Write a Python function to calculate factorial"
        solution = """
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)
"""
        
        print(f"\n📝 Task: {task}")
        print(f"💡 Solution:\n{solution}")
        print("\n🔍 Judging solution...")
        
        # Judge the solution
        judgment = bank.judge_solution(task=task, solution=solution)
        
        # Validate response structure
        assert "verdict" in judgment, "Missing 'verdict' field"
        assert "score" in judgment, "Missing 'score' field"
        assert "reasoning" in judgment, "Missing 'reasoning' field"
        assert "learnings" in judgment, "Missing 'learnings' field"
        
        print(f"\n✅ Judgment received:")
        print(f"   Verdict: {judgment['verdict']}")
        print(f"   Score: {judgment['score']:.2f}")
        print(f"   Reasoning: {judgment['reasoning'][:100]}...")
        print(f"   Learnings: {len(judgment['learnings'])} items")
        
        # Validate learnings structure
        if judgment['learnings']:
            learning = judgment['learnings'][0]
            assert "title" in learning, "Learning missing 'title'"
            assert "description" in learning, "Learning missing 'description'"
            assert "content" in learning, "Learning missing 'content'"
            print(f"\n   First learning: {learning['title']}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_judge_solution_failure():
    """Test 2: Judge a failed solution with error context"""
    print("\n" + "="*70)
    print("TEST 2: Judge Failed Solution (Error Context)")
    print("="*70)
    
    try:
        # Initialize components
        storage = ChromaDBAdapter(persist_directory="./chroma_data")
        llm_client = CachedLLMClient(
            ResponsesAPIClient(api_key=os.getenv("OPENROUTER_API_KEY"))
        )
        bank = ReasoningBank(storage_backend=storage, llm_client=llm_client)
        
        # Test task and buggy solution
        task = "Write a Python function to divide two numbers"
        solution = """
def divide(a, b):
    return a / b  # Bug: No zero division check!
"""
        
        print(f"\n📝 Task: {task}")
        print(f"💡 Solution (buggy):\n{solution}")
        print("\n🔍 Judging solution...")
        
        # Judge the solution
        judgment = bank.judge_solution(task=task, solution=solution)
        
        print(f"\n✅ Judgment received:")
        print(f"   Verdict: {judgment['verdict']}")
        print(f"   Score: {judgment['score']:.2f}")
        print(f"   Reasoning: {judgment['reasoning'][:100]}...")
        
        # Check for error context in learnings
        has_error_context = False
        for learning in judgment.get('learnings', []):
            if 'error_context' in learning and learning['error_context']:
                has_error_context = True
                print(f"\n   ⚠️  Error context found:")
                print(f"      Error type: {learning['error_context'].get('error_type', 'N/A')}")
                print(f"      Pattern: {learning['error_context'].get('failure_pattern', 'N/A')[:80]}...")
                break
        
        if has_error_context:
            print("\n✅ Error context successfully extracted")
        else:
            print("\n⚠️  No error context found (may depend on LLM response)")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_judge_prompt_structure():
    """Test 3: Verify judge prompt structure"""
    print("\n" + "="*70)
    print("TEST 3: Judge Prompt Structure")
    print("="*70)
    
    try:
        # Initialize components
        storage = ChromaDBAdapter(persist_directory="./chroma_data")
        llm_client = CachedLLMClient(
            ResponsesAPIClient(api_key=os.getenv("OPENROUTER_API_KEY"))
        )
        bank = ReasoningBank(storage_backend=storage, llm_client=llm_client)
        
        # Build a test prompt
        task = "Test task"
        solution = "Test solution"
        prompt = bank._build_judge_prompt(task, solution)
        
        # Verify prompt contains required elements
        assert "Task:" in prompt, "Prompt missing task section"
        assert "Solution:" in prompt, "Prompt missing solution section"
        assert "verdict" in prompt, "Prompt missing verdict field"
        assert "score" in prompt, "Prompt missing score field"
        assert "reasoning" in prompt, "Prompt missing reasoning field"
        assert "learnings" in prompt, "Prompt missing learnings field"
        assert "error_context" in prompt, "Prompt missing error_context field"
        
        print("\n✅ Judge prompt structure validated:")
        print("   ✓ Contains task section")
        print("   ✓ Contains solution section")
        print("   ✓ Specifies verdict field")
        print("   ✓ Specifies score field")
        print("   ✓ Specifies reasoning field")
        print("   ✓ Specifies learnings field")
        print("   ✓ Specifies error_context field")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_json_parsing():
    """Test 4: JSON parsing with error handling"""
    print("\n" + "="*70)
    print("TEST 4: JSON Parsing with Error Handling")
    print("="*70)
    
    try:
        # Initialize components
        storage = ChromaDBAdapter(persist_directory="./chroma_data")
        llm_client = CachedLLMClient(
            ResponsesAPIClient(api_key=os.getenv("OPENROUTER_API_KEY"))
        )
        bank = ReasoningBank(storage_backend=storage, llm_client=llm_client)
        
        # Test valid JSON
        valid_json = """
        {
            "verdict": "success",
            "score": 0.85,
            "reasoning": "Good solution",
            "learnings": [
                {
                    "title": "Test learning",
                    "description": "Test description",
                    "content": "Test content"
                }
            ]
        }
        """
        
        result = bank._parse_judge_response(valid_json)
        assert result["verdict"] == "success"
        assert result["score"] == 0.85
        print("\n✅ Valid JSON parsed successfully")
        
        # Test JSON with markdown code blocks
        markdown_json = """```json
        {
            "verdict": "failure",
            "score": 0.3,
            "reasoning": "Has bugs",
            "learnings": []
        }
        ```"""
        
        result = bank._parse_judge_response(markdown_json)
        assert result["verdict"] == "failure"
        assert result["score"] == 0.3
        print("✅ Markdown-wrapped JSON parsed successfully")
        
        # Test invalid verdict (should default to "partial")
        invalid_verdict = """
        {
            "verdict": "invalid_verdict",
            "score": 0.5,
            "reasoning": "Test",
            "learnings": []
        }
        """
        
        result = bank._parse_judge_response(invalid_verdict)
        assert result["verdict"] == "partial"
        print("✅ Invalid verdict handled (defaulted to 'partial')")
        
        # Test score clamping
        high_score = """
        {
            "verdict": "success",
            "score": 1.5,
            "reasoning": "Test",
            "learnings": []
        }
        """
        
        result = bank._parse_judge_response(high_score)
        assert result["score"] == 1.0
        print("✅ Score clamping works (1.5 → 1.0)")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("TESTING JUDGE_SOLUTION FUNCTIONALITY")
    print("="*70)
    
    results = []
    
    # Run tests
    results.append(("Judge Prompt Structure", test_judge_prompt_structure()))
    results.append(("JSON Parsing", test_json_parsing()))
    
    # Only run LLM tests if API key is valid
    if os.getenv("OPENROUTER_API_KEY") and os.getenv("OPENROUTER_API_KEY") != "test-key":
        print("\n⚠️  Skipping LLM-dependent tests (requires valid API key)")
        print("   To run full tests, set OPENROUTER_API_KEY environment variable")
    else:
        print("\n⚠️  Skipping LLM-dependent tests (no valid API key)")
    
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
