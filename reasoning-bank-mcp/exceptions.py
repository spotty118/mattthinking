"""
Custom exception hierarchy for ReasoningBank MCP System.

This module defines all custom exceptions used throughout the system,
providing clear error messages and context for debugging.
"""

from typing import Optional, Dict, Any


class ReasoningBankError(Exception):
    """
    Base exception class for all ReasoningBank errors.
    
    All custom exceptions in the system inherit from this base class,
    allowing for easy catching of all ReasoningBank-specific errors.
    """
    
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        """
        Initialize the exception with a message and optional context.
        
        Args:
            message: Human-readable error message
            context: Optional dictionary containing additional error context
        """
        super().__init__(message)
        self.message = message
        self.context = context or {}
    
    def __str__(self) -> str:
        """Return string representation with context if available."""
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            return f"{self.message} (Context: {context_str})"
        return self.message


class MemoryRetrievalError(ReasoningBankError):
    """
    Raised when memory retrieval from storage fails.
    
    This can occur due to database connection issues, query failures,
    or embedding generation problems during retrieval.
    """
    
    def __init__(self, message: str = "Failed to retrieve memories from storage", 
                 query: Optional[str] = None, 
                 context: Optional[Dict[str, Any]] = None):
        """
        Initialize memory retrieval error.
        
        Args:
            message: Error message
            query: The query that failed (if applicable)
            context: Additional error context
        """
        ctx = context or {}
        if query:
            ctx['query'] = query
        super().__init__(message, ctx)


class MemoryStorageError(ReasoningBankError):
    """
    Raised when storing memories to the database fails.
    
    This can occur due to database write failures, validation errors,
    or embedding generation problems during storage.
    """
    
    def __init__(self, message: str = "Failed to store memory to database",
                 memory_id: Optional[str] = None,
                 context: Optional[Dict[str, Any]] = None):
        """
        Initialize memory storage error.
        
        Args:
            message: Error message
            memory_id: ID of the memory that failed to store
            context: Additional error context
        """
        ctx = context or {}
        if memory_id:
            ctx['memory_id'] = memory_id
        super().__init__(message, ctx)


class LLMGenerationError(ReasoningBankError):
    """
    Raised when LLM API calls fail to generate responses.
    
    This can occur due to API errors, network issues, invalid prompts,
    or model-specific failures.
    """
    
    def __init__(self, message: str = "LLM failed to generate response",
                 model: Optional[str] = None,
                 status_code: Optional[int] = None,
                 context: Optional[Dict[str, Any]] = None):
        """
        Initialize LLM generation error.
        
        Args:
            message: Error message
            model: The model that failed to generate
            status_code: HTTP status code if applicable
            context: Additional error context
        """
        ctx = context or {}
        if model:
            ctx['model'] = model
        if status_code:
            ctx['status_code'] = status_code
        super().__init__(message, ctx)


class InvalidTaskError(ReasoningBankError):
    """
    Raised when a task description is invalid or malformed.
    
    This can occur when task descriptions are empty, too long,
    or contain invalid characters or formatting.
    """
    
    def __init__(self, message: str = "Invalid task description provided",
                 task: Optional[str] = None,
                 context: Optional[Dict[str, Any]] = None):
        """
        Initialize invalid task error.
        
        Args:
            message: Error message
            task: The invalid task description
            context: Additional error context
        """
        ctx = context or {}
        if task:
            # Truncate task if too long for error message
            ctx['task'] = task[:100] + "..." if len(task) > 100 else task
        super().__init__(message, ctx)


class JSONParseError(ReasoningBankError):
    """
    Raised when JSON parsing fails for LLM responses or stored data.
    
    This can occur when LLM returns malformed JSON or when stored
    data is corrupted.
    """
    
    def __init__(self, message: str = "Failed to parse JSON response",
                 raw_content: Optional[str] = None,
                 context: Optional[Dict[str, Any]] = None):
        """
        Initialize JSON parse error.
        
        Args:
            message: Error message
            raw_content: The raw content that failed to parse
            context: Additional error context
        """
        ctx = context or {}
        if raw_content:
            # Truncate content if too long
            ctx['raw_content'] = raw_content[:200] + "..." if len(raw_content) > 200 else raw_content
        super().__init__(message, ctx)


class EmbeddingError(ReasoningBankError):
    """
    Raised when embedding generation fails.
    
    This can occur due to model loading issues, invalid input text,
    or embedding service failures.
    """
    
    def __init__(self, message: str = "Failed to generate embeddings",
                 text: Optional[str] = None,
                 model_name: Optional[str] = None,
                 context: Optional[Dict[str, Any]] = None):
        """
        Initialize embedding error.
        
        Args:
            message: Error message
            text: The text that failed to embed
            model_name: The embedding model that failed
            context: Additional error context
        """
        ctx = context or {}
        if text:
            # Truncate text if too long
            ctx['text'] = text[:100] + "..." if len(text) > 100 else text
        if model_name:
            ctx['model_name'] = model_name
        super().__init__(message, ctx)


class APIKeyError(ReasoningBankError):
    """
    Raised when API key validation fails.
    
    This occurs during system initialization when required API keys
    are missing, invalid, or expired.
    """
    
    def __init__(self, message: str = "API key validation failed",
                 key_name: Optional[str] = None,
                 context: Optional[Dict[str, Any]] = None):
        """
        Initialize API key error.
        
        Args:
            message: Error message
            key_name: Name of the missing/invalid API key
            context: Additional error context
        """
        ctx = context or {}
        if key_name:
            ctx['key_name'] = key_name
        super().__init__(message, ctx)


class TokenBudgetExceededError(ReasoningBankError):
    """
    Raised when token budget limits are exceeded.
    
    This occurs when cumulative token usage exceeds configured limits
    during iterative reasoning or when prompts are too large.
    """
    
    def __init__(self, message: str = "Token budget exceeded",
                 tokens_used: Optional[int] = None,
                 token_limit: Optional[int] = None,
                 context: Optional[Dict[str, Any]] = None):
        """
        Initialize token budget exceeded error.
        
        Args:
            message: Error message
            tokens_used: Number of tokens used
            token_limit: The token limit that was exceeded
            context: Additional error context
        """
        ctx = context or {}
        if tokens_used is not None:
            ctx['tokens_used'] = tokens_used
        if token_limit is not None:
            ctx['token_limit'] = token_limit
        super().__init__(message, ctx)


class MemoryValidationError(ReasoningBankError):
    """
    Raised when memory item validation fails.
    
    This occurs when memory items are missing required fields,
    contain invalid data types, or violate schema constraints.
    """
    
    def __init__(self, message: str = "Memory item validation failed",
                 memory_id: Optional[str] = None,
                 validation_errors: Optional[list] = None,
                 context: Optional[Dict[str, Any]] = None):
        """
        Initialize memory validation error.
        
        Args:
            message: Error message
            memory_id: ID of the invalid memory item
            validation_errors: List of specific validation errors
            context: Additional error context
        """
        ctx = context or {}
        if memory_id:
            ctx['memory_id'] = memory_id
        if validation_errors:
            ctx['validation_errors'] = validation_errors
        super().__init__(message, ctx)
