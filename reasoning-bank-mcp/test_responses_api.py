#!/usr/bin/env python3
import os
import sys
from responses_alpha_client import ResponsesAPIClient

# Initialize client
api_key = os.getenv("OPENROUTER_API_KEY")
if not api_key:
    print("ERROR: OPENROUTER_API_KEY not set")
    sys.exit(1)

client = ResponsesAPIClient(
    api_key=api_key,
    base_url="https://openrouter.ai/api/alpha/responses",
    default_reasoning_effort="medium"
)

print("Testing Responses API Alpha client...")
print(f"API Key: {api_key[:20]}...")
print()

# Test simple request
try:
    print("Sending test request...")
    result = client.create(
        model="google/gemini-2.5-pro",
        messages=[
            {"role": "user", "content": "Say hello in one word"}
        ],
        max_output_tokens=50,
        temperature=0.7
    )
    
    print(f"SUCCESS!")
    print(f"Content: {result.content}")
    print(f"Input tokens: {result.input_tokens}")
    print(f"Output tokens: {result.output_tokens}")
    print(f"Reasoning tokens: {result.reasoning_tokens}")
    print(f"Total tokens: {result.total_tokens}")
    
except Exception as e:
    print(f"ERROR: {str(e)}")
    import traceback
    traceback.print_exc()
