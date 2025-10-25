"""
Test for solve_coding_task MCP tool implementation

This test verifies that the solve_coding_task tool is properly implemented
with all required parameters and functionality.
"""

import asyncio
import os
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from reasoning_bank_server import solve_coding_task
from schemas import OutcomeType


def test_solve_coding_task_signature():
    """Test that solve_coding_task has the correct signature"""
    import inspect
    
    sig = inspect.signature(solve_coding_task)
    params = sig.parameters
    
    # Verify all required parameters exist
    assert 'task' in params
    assert 'use_memory' in params
    assert 'enable_matts' in params
    assert 'matts_k' in params
    assert 'matts_mode' in params
    assert 'store_result' in params
    
    # Verify default values
    assert params['use_memory'].default == True
    assert params['enable_matts'].default == False
    assert params['matts_k'].default == 3
    assert params['matts_mode'].default == "parallel"
    assert params['store_result'].default == True
    
    print("✅ solve_coding_task signature is correct")


async def test_solve_coding_task_basic():
    """Test basic solve_coding_task functionality with mocked components"""
    
    # Mock the global components
    import reasoning_bank_server
    
    # Create mock objects
    mock_config = Mock()
    mock_config.retrieval_k = 3
    mock_config.success_threshold = 0.8
    mock_config.temperature_judge = 0.0
    
    mock_reasoning_bank = Mock()
    mock_reasoning_bank.retrieve_memories = Mock(return_value=[])
    mock_reasoning_bank.judge_solution = Mock(return_value={
        "verdict": "success",
        "score": 0.85,
        "reasoning": "Good solution",
        "learnings": []
    })
    mock_reasoning_bank.store_trace = Mock(return_value="trace-123")
    
    mock_result = Mock()
    mock_result.solution = "def fibonacci(n): return n if n <= 1 else fibonacci(n-1) + fibonacci(n-2)"
    mock_result.score = 0.85
    mock_result.trajectory = []
    mock_result.iterations = 2
    mock_result.early_termination = True
    mock_result.loop_detected = False
    mock_result.total_tokens = 1500
    
    mock_iterative_agent = Mock()
    mock_iterative_agent.solve_task = Mock(return_value=mock_result)
    
    # Patch the global variables
    reasoning_bank_server.config = mock_config
    reasoning_bank_server.reasoning_bank = mock_reasoning_bank
    reasoning_bank_server.iterative_agent = mock_iterative_agent
    
    # Test the function
    result = await solve_coding_task(
        task="Write a fibonacci function",
        use_memory=True,
        enable_matts=False,
        store_result=True
    )
    
    # Verify the result structure
    assert "success" in result
    assert "solution" in result
    assert "score" in result
    assert "trajectory" in result
    assert "iterations" in result
    assert "memories_used" in result
    assert "early_termination" in result
    assert "trace_id" in result
    
    # Verify the values
    assert result["success"] == True
    assert result["score"] == 0.85
    assert result["iterations"] == 2
    assert result["early_termination"] == True
    assert result["trace_id"] == "trace-123"
    
    # Verify method calls
    mock_reasoning_bank.retrieve_memories.assert_called_once()
    mock_iterative_agent.solve_task.assert_called_once()
    mock_reasoning_bank.judge_solution.assert_called_once()
    mock_reasoning_bank.store_trace.assert_called_once()
    
    print("✅ solve_coding_task basic functionality works correctly")


async def test_solve_coding_task_with_matts():
    """Test solve_coding_task with MaTTS enabled"""
    
    import reasoning_bank_server
    
    # Create mock objects
    mock_config = Mock()
    mock_config.retrieval_k = 3
    mock_config.success_threshold = 0.8
    mock_config.temperature_judge = 0.0
    
    mock_reasoning_bank = Mock()
    mock_reasoning_bank.retrieve_memories = Mock(return_value=[])
    mock_reasoning_bank.judge_solution = Mock(return_value={
        "verdict": "success",
        "score": 0.90,
        "reasoning": "Excellent solution",
        "learnings": []
    })
    mock_reasoning_bank.store_trace = Mock(return_value="trace-456")
    
    mock_result = Mock()
    mock_result.solution = "def fibonacci(n): ..."
    mock_result.score = 0.90
    mock_result.trajectory = []
    mock_result.iterations = 1
    mock_result.early_termination = True
    mock_result.loop_detected = False
    mock_result.total_tokens = 2000
    
    mock_iterative_agent = Mock()
    mock_iterative_agent.solve_with_matts = Mock(return_value=mock_result)
    
    # Patch the global variables
    reasoning_bank_server.config = mock_config
    reasoning_bank_server.reasoning_bank = mock_reasoning_bank
    reasoning_bank_server.iterative_agent = mock_iterative_agent
    
    # Test with MaTTS enabled
    result = await solve_coding_task(
        task="Write a fibonacci function",
        use_memory=True,
        enable_matts=True,
        matts_k=5,
        matts_mode="parallel",
        store_result=True
    )
    
    # Verify MaTTS was called
    mock_iterative_agent.solve_with_matts.assert_called_once()
    call_args = mock_iterative_agent.solve_with_matts.call_args
    assert call_args[1]['k'] == 5
    assert call_args[1]['mode'] == "parallel"
    
    # Verify result
    assert result["success"] == True
    assert result["score"] == 0.90
    
    print("✅ solve_coding_task with MaTTS works correctly")


async def test_solve_coding_task_without_memory():
    """Test solve_coding_task with use_memory=False"""
    
    import reasoning_bank_server
    
    # Create mock objects
    mock_config = Mock()
    mock_config.retrieval_k = 3
    mock_config.success_threshold = 0.8
    mock_config.temperature_judge = 0.0
    
    mock_reasoning_bank = Mock()
    mock_reasoning_bank.retrieve_memories = Mock(return_value=[])
    mock_reasoning_bank.judge_solution = Mock(return_value={
        "verdict": "success",
        "score": 0.75,
        "reasoning": "Acceptable solution",
        "learnings": []
    })
    
    mock_result = Mock()
    mock_result.solution = "def fibonacci(n): ..."
    mock_result.score = 0.75
    mock_result.trajectory = []
    mock_result.iterations = 3
    mock_result.early_termination = False
    mock_result.loop_detected = False
    mock_result.total_tokens = 1800
    
    mock_iterative_agent = Mock()
    mock_iterative_agent.solve_task = Mock(return_value=mock_result)
    
    # Patch the global variables
    reasoning_bank_server.config = mock_config
    reasoning_bank_server.reasoning_bank = mock_reasoning_bank
    reasoning_bank_server.iterative_agent = mock_iterative_agent
    
    # Test without memory
    result = await solve_coding_task(
        task="Write a fibonacci function",
        use_memory=False,
        enable_matts=False,
        store_result=False
    )
    
    # Verify memory retrieval was not called
    mock_reasoning_bank.retrieve_memories.assert_not_called()
    
    # Verify result
    assert result["memories_used"] == 0
    assert result["trace_id"] is None  # Not stored
    
    print("✅ solve_coding_task without memory works correctly")


async def test_solve_coding_task_error_handling():
    """Test solve_coding_task error handling"""
    
    import reasoning_bank_server
    
    # Test with invalid task (too short)
    result = await solve_coding_task(
        task="short",
        use_memory=False,
        store_result=False
    )
    
    # Verify error response
    assert result["success"] == False
    assert "error" in result
    assert result["error_type"] == "InvalidTaskError"
    
    print("✅ solve_coding_task error handling works correctly")


def run_tests():
    """Run all tests"""
    print("=" * 60)
    print("Testing solve_coding_task implementation")
    print("=" * 60)
    
    # Test 1: Signature
    test_solve_coding_task_signature()
    
    # Test 2: Basic functionality
    asyncio.run(test_solve_coding_task_basic())
    
    # Test 3: MaTTS mode
    asyncio.run(test_solve_coding_task_with_matts())
    
    # Test 4: Without memory
    asyncio.run(test_solve_coding_task_without_memory())
    
    # Test 5: Error handling
    asyncio.run(test_solve_coding_task_error_handling())
    
    print("=" * 60)
    print("✅ All tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    run_tests()
