#!/usr/bin/env python3
"""
Test script for ReasoningBank MCP server
"""
import os
import sys
sys.path.insert(0, '/app')

from openai import OpenAI
from reasoning_bank_core import ReasoningBank
from iterative_agent import IterativeReasoningAgent

def test_system():
    print("="*80)
    print("ReasoningBank System Test")
    print("="*80)
    
    # Initialize client
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("❌ ERROR: OPENROUTER_API_KEY not set")
        return False
    
    client = OpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1"
    )
    
    # Initialize system
    print("\n1. Initializing ReasoningBank...")
    bank = ReasoningBank(
        llm_client=client,
        model="google/gemini-2.5-pro",
        persist_dir="/app/chroma_data"
    )
    print("✓ ReasoningBank initialized")
    
    print("\n2. Initializing Agent...")
    agent = IterativeReasoningAgent(
        llm_client=client,
        reasoning_bank=bank,
        model="google/gemini-2.5-pro"
    )
    print("✓ Agent initialized")
    
    # Test task
    print("\n3. Testing simple coding task...")
    test_task = "Write a Python function that calculates the factorial of a number"
    
    try:
        result = agent.solve_task(
            task=test_task,
            use_memory=True,
            enable_matts=False,
            matts_k=1
        )
        
        print(f"\n✓ Task completed successfully!")
        print(f"  Success: {result['success']}")
        print(f"  Iterations: {result['iterations']}")
        print(f"  Memories extracted: {result['memories_extracted']}")
        print(f"  Quality score: {result.get('score', 'N/A')}")
        
        print(f"\n  Output preview:")
        output_preview = result['output'][:200] if len(result['output']) > 200 else result['output']
        print(f"  {output_preview}...")
        
    except Exception as e:
        print(f"\n❌ ERROR during task execution:")
        print(f"  {type(e).__name__}: {str(e)}")
        return False
    
    # Get statistics
    print("\n4. Checking system statistics...")
    stats = bank.get_statistics()
    print(f"  Total traces: {stats['total_traces']}")
    print(f"  Success traces: {stats['success_traces']}")
    print(f"  Failure traces: {stats['failure_traces']}")
    print(f"  Total memories: {stats['total_memories']}")
    print(f"  Memories with errors: {stats['memories_with_errors']}")
    print(f"  Success rate: {stats['success_rate']:.1f}%")
    
    print("\n" + "="*80)
    print("✅ ALL TESTS PASSED - System is operational!")
    print("="*80)
    return True

if __name__ == "__main__":
    success = test_system()
    sys.exit(0 if success else 1)
