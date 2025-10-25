#!/usr/bin/env python3
"""
Test script to verify the ResponsesAPIClient structure without making API calls.
"""

import sys
import os

# Test imports
try:
    from responses_alpha_client import ResponsesAPIClient, ResponsesAPIResult, ReasoningEffort
    print("✓ Successfully imported ResponsesAPIClient")
    print("✓ Successfully imported ResponsesAPIResult")
    print("✓ Successfully imported ReasoningEffort")
except ImportError as e:
    print(f"✗ Import failed: {e}")
    sys.exit(1)

# Test ResponsesAPIResult dataclass
try:
    result = ResponsesAPIResult(
        content="Test content",
        reasoning_tokens=100,
        output_tokens=50,
        input_tokens=25,
        total_tokens=175,
        model="test-model",
        finish_reason="stop"
    )
    print(f"✓ ResponsesAPIResult created: {result}")
    assert result.content == "Test content"
    assert result.reasoning_tokens == 100
    assert result.output_tokens == 50
    assert result.input_tokens == 25
    assert result.total_tokens == 175
    print("✓ ResponsesAPIResult attributes verified")
except Exception as e:
    print(f"✗ ResponsesAPIResult test failed: {e}")
    sys.exit(1)

# Test ResponsesAPIClient initialization with API key
try:
    # Set a dummy API key for testing initialization
    os.environ["OPENROUTER_API_KEY"] = "test-key-12345"
    client = ResponsesAPIClient()
    print("✓ ResponsesAPIClient initialized with default parameters")
    assert client.api_key == "test-key-12345"
    assert client.default_model == "google/gemini-2.0-flash-thinking-exp:free"
    assert client.default_reasoning_effort == "medium"
    print("✓ ResponsesAPIClient default values verified")
except Exception as e:
    print(f"✗ ResponsesAPIClient initialization failed: {e}")
    sys.exit(1)

# Test custom initialization
try:
    client = ResponsesAPIClient(
        api_key="custom-key",
        default_model="custom-model",
        default_reasoning_effort="high",
        timeout=60
    )
    print("✓ ResponsesAPIClient initialized with custom parameters")
    assert client.api_key == "custom-key"
    assert client.default_model == "custom-model"
    assert client.default_reasoning_effort == "high"
    assert client.timeout == 60
    print("✓ ResponsesAPIClient custom values verified")
except Exception as e:
    print(f"✗ Custom initialization failed: {e}")
    sys.exit(1)

# Test API key error
try:
    del os.environ["OPENROUTER_API_KEY"]
    from exceptions import APIKeyError
    try:
        client = ResponsesAPIClient()
        print("✗ Should have raised APIKeyError")
        sys.exit(1)
    except APIKeyError as e:
        print(f"✓ APIKeyError raised correctly: {e.message}")
except Exception as e:
    print(f"✗ API key error test failed: {e}")
    sys.exit(1)

# Test message format conversion
try:
    os.environ["OPENROUTER_API_KEY"] = "test-key"
    client = ResponsesAPIClient()
    
    messages = [
        {"role": "system", "content": "You are helpful"},
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"},
        {"role": "user", "content": "How are you?"}
    ]
    
    converted = client._convert_messages_to_responses_format(messages)
    print(f"✓ Message conversion successful: {len(converted)} messages converted")
    
    # Verify structure
    assert len(converted) == 4
    assert converted[0]["role"] == "user"  # system converted to user
    assert "[System Context]" in converted[0]["content"][0]["text"]
    assert converted[1]["role"] == "user"
    assert converted[2]["role"] == "assistant"
    print("✓ Message format conversion verified")
except Exception as e:
    print(f"✗ Message conversion test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test reasoning effort levels
try:
    valid_efforts = ["minimal", "low", "medium", "high"]
    for effort in valid_efforts:
        client = ResponsesAPIClient(
            api_key="test",
            default_reasoning_effort=effort
        )
        assert client.default_reasoning_effort == effort
    print(f"✓ All reasoning effort levels supported: {valid_efforts}")
except Exception as e:
    print(f"✗ Reasoning effort test failed: {e}")
    sys.exit(1)

print("\n" + "="*50)
print("All structure tests passed! ✓")
print("="*50)
print("\nNote: Actual API calls require:")
print("1. Valid OPENROUTER_API_KEY environment variable")
print("2. Network connectivity to OpenRouter API")
print("3. Run test_responses_api.py for full integration test")
