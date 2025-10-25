"""
Responses API Alpha client for OpenRouter.

This module provides a client for the OpenRouter Responses API Alpha,
which supports extended reasoning capabilities with configurable effort levels.
It converts OpenAI-style messages to the Responses API format and tracks
reasoning tokens separately from output tokens.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Literal
import requests
import os
from exceptions import LLMGenerationError, APIKeyError
from performance_optimizer import APIConnectionPool


# Type alias for reasoning effort levels
ReasoningEffort = Literal["minimal", "low", "medium", "high"]


@dataclass
class ResponsesAPIResult:
    """
    Result from a Responses API call with reasoning token tracking.
    
    Attributes:
        content: The generated text content
        reasoning_tokens: Number of tokens used for reasoning (extended thinking)
        output_tokens: Number of tokens in the final output
        input_tokens: Number of tokens in the input prompt
        total_tokens: Total tokens used (reasoning + output + input)
        model: The model used for generation
        finish_reason: Why the generation stopped (e.g., "stop", "length")
    """
    content: str
    reasoning_tokens: int
    output_tokens: int
    input_tokens: int
    total_tokens: int
    model: str
    finish_reason: str
    
    def __repr__(self) -> str:
        """String representation showing token breakdown."""
        return (
            f"ResponsesAPIResult(content_length={len(self.content)}, "
            f"reasoning_tokens={self.reasoning_tokens}, "
            f"output_tokens={self.output_tokens}, "
            f"input_tokens={self.input_tokens}, "
            f"total_tokens={self.total_tokens})"
        )


class ResponsesAPIClient:
    """
    Client for OpenRouter Responses API Alpha.
    
    This client handles:
    - Message format conversion from OpenAI to Responses API format
    - Configurable reasoning effort levels
    - Reasoning token tracking
    - Error handling with retries
    - API key validation
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://openrouter.ai/api/v1",
        default_model: str = "google/gemini-2.0-flash-thinking-exp:free",
        default_reasoning_effort: ReasoningEffort = "medium",
        timeout: int = 120
    ):
        """
        Initialize the Responses API client.
        
        Args:
            api_key: OpenRouter API key (defaults to OPENROUTER_API_KEY env var)
            base_url: Base URL for OpenRouter API
            default_model: Default model to use for generation
            default_reasoning_effort: Default reasoning effort level
            timeout: Request timeout in seconds
            
        Raises:
            APIKeyError: If API key is not provided or found in environment
        """
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise APIKeyError(
                "OpenRouter API key not found. Set OPENROUTER_API_KEY environment variable.",
                key_name="OPENROUTER_API_KEY"
            )
        
        self.base_url = base_url.rstrip("/")
        self.default_model = default_model
        self.default_reasoning_effort = default_reasoning_effort
        self.timeout = timeout
        
        # API endpoint
        self.chat_endpoint = f"{self.base_url}/chat/completions"
        
        # Initialize connection pool for better performance
        try:
            self.connection_pool = APIConnectionPool(
                pool_size=10,
                max_retries=3,
                timeout=timeout
            )
            self.use_connection_pool = True
        except Exception as e:
            # Fallback to regular requests if connection pool fails
            self.connection_pool = None
            self.use_connection_pool = False
    
    def _convert_messages_to_responses_format(
        self,
        messages: List[Dict[str, str]]
    ) -> List[Dict[str, Any]]:
        """
        Convert OpenAI-style messages to Responses API format.
        
        OpenAI format:
            [{"role": "system", "content": "You are helpful"},
             {"role": "user", "content": "Hello"}]
        
        Responses API format:
            [{"type": "message",
              "role": "user",
              "content": [{"type": "input_text", "text": "Hello"}]}]
        
        Args:
            messages: List of OpenAI-style message dictionaries
            
        Returns:
            List of Responses API formatted messages
        """
        responses_messages = []
        
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            # System messages are typically prepended to user messages
            # or handled separately in Responses API
            if role == "system":
                # Convert system message to user message with context
                responses_messages.append({
                    "type": "message",
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": f"[System Context]: {content}"
                        }
                    ]
                })
            elif role == "user":
                responses_messages.append({
                    "type": "message",
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": content
                        }
                    ]
                })
            elif role == "assistant":
                responses_messages.append({
                    "type": "message",
                    "role": "assistant",
                    "content": [
                        {
                            "type": "output_text",
                            "text": content
                        }
                    ]
                })
        
        return responses_messages

    def create(
        self,
        model: Optional[str] = None,
        messages: Optional[List[Dict[str, str]]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        max_output_tokens: Optional[int] = None,
        reasoning_effort: Optional[ReasoningEffort] = None,
        **kwargs
    ) -> ResponsesAPIResult:
        """
        Create a chat completion using the Responses API.
        
        This method handles:
        - Message format conversion
        - API request with proper headers
        - Response parsing and token tracking
        - Error handling
        
        Args:
            model: Model to use (defaults to default_model)
            messages: List of OpenAI-style messages
            temperature: Sampling temperature (0.0 to 2.0)
            max_tokens: Maximum tokens to generate (legacy parameter)
            max_output_tokens: Maximum output tokens (preferred for Responses API)
            reasoning_effort: Reasoning effort level ("minimal", "low", "medium", "high")
            **kwargs: Additional parameters to pass to the API
            
        Returns:
            ResponsesAPIResult with content and token tracking
            
        Raises:
            LLMGenerationError: If API call fails or response is invalid
        """
        # Use defaults if not provided
        model = model or self.default_model
        reasoning_effort = reasoning_effort or self.default_reasoning_effort
        
        if not messages:
            raise LLMGenerationError(
                "Messages list cannot be empty",
                model=model
            )
        
        # Convert messages to Responses API format
        # For simplicity with OpenRouter, we'll use the standard OpenAI format
        # as OpenRouter supports both formats
        
        # Prepare request payload
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        
        # Add optional parameters - prefer max_output_tokens over max_tokens
        if max_output_tokens:
            payload["max_output_tokens"] = max_output_tokens
        elif max_tokens:
            payload["max_tokens"] = max_tokens
        
        # Add reasoning effort as a provider-specific parameter
        # This maps to the extended thinking capability
        if reasoning_effort:
            payload["reasoning_effort"] = reasoning_effort
        
        # Add any additional kwargs
        payload.update(kwargs)
        
        # Prepare headers
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/reasoning-bank-mcp",
            "X-Title": "ReasoningBank MCP Server"
        }
        
        try:
            # Make API request using connection pool if available
            if self.use_connection_pool and self.connection_pool:
                response = self.connection_pool.post(
                    self.chat_endpoint,
                    json=payload,
                    headers=headers
                )
            else:
                # Use tuple timeout format: (connect_timeout, read_timeout)
                # 10 seconds for connection, self.timeout for reading
                response = requests.post(
                    self.chat_endpoint,
                    json=payload,
                    headers=headers,
                    timeout=(10, self.timeout)
                )
            
            # Check for HTTP errors
            if response.status_code != 200:
                error_detail = response.text
                try:
                    error_json = response.json()
                    error_detail = error_json.get("error", {}).get("message", error_detail)
                except:
                    pass
                
                raise LLMGenerationError(
                    f"API request failed: {error_detail}",
                    model=model,
                    status_code=response.status_code,
                    context={"response": error_detail}
                )
            
            # Parse response
            response_data = response.json()
            
            # Extract content and token usage
            if "choices" not in response_data or len(response_data["choices"]) == 0:
                raise LLMGenerationError(
                    "API response missing choices",
                    model=model,
                    context={"response": response_data}
                )
            
            choice = response_data["choices"][0]
            content = choice.get("message", {}).get("content", "")
            finish_reason = choice.get("finish_reason", "unknown")
            
            # Extract token usage
            usage = response_data.get("usage", {})
            total_tokens = usage.get("total_tokens", 0)
            input_tokens = usage.get("prompt_tokens", 0)
            
            # For models with extended thinking, reasoning tokens may be tracked separately
            # Otherwise, we estimate based on the response structure
            reasoning_tokens = usage.get("reasoning_tokens", 0)
            output_tokens = usage.get("completion_tokens", 0)
            
            # If reasoning_tokens not provided, estimate from total
            if reasoning_tokens == 0 and total_tokens > 0:
                # Reasoning tokens = total - input - output (rough estimate)
                reasoning_tokens = max(0, total_tokens - input_tokens - output_tokens)
            
            return ResponsesAPIResult(
                content=content,
                reasoning_tokens=reasoning_tokens,
                output_tokens=output_tokens,
                input_tokens=input_tokens,
                total_tokens=total_tokens,
                model=model,
                finish_reason=finish_reason
            )
            
        except requests.exceptions.Timeout:
            raise LLMGenerationError(
                f"API request timed out after {self.timeout} seconds",
                model=model,
                context={"timeout": self.timeout}
            )
        except requests.exceptions.RequestException as e:
            raise LLMGenerationError(
                f"API request failed: {str(e)}",
                model=model,
                context={"error": str(e)}
            )
        except Exception as e:
            # Catch any other unexpected errors
            if isinstance(e, LLMGenerationError):
                raise
            raise LLMGenerationError(
                f"Unexpected error during API call: {str(e)}",
                model=model,
                context={"error": str(e), "type": type(e).__name__}
            )
    
    def validate_api_key(self) -> bool:
        """
        Validate that the API key is working by making a minimal test request.
        
        Returns:
            True if API key is valid, False otherwise
            
        Raises:
            APIKeyError: If API key validation fails
        """
        try:
            # Make a minimal request to test the API key
            result = self.create(
                messages=[{"role": "user", "content": "test"}],
                max_tokens=1,
                temperature=0.0
            )
            return True
        except LLMGenerationError as e:
            if e.context.get("status_code") == 401:
                raise APIKeyError(
                    "API key is invalid or expired",
                    key_name="OPENROUTER_API_KEY",
                    context={"status_code": 401}
                )
            # Other errors don't necessarily mean invalid key
            return False
