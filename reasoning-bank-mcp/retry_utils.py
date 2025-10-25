"""
Retry logic with exponential backoff for API reliability.

This module provides a decorator for retrying failed operations with:
- Exponential backoff with jitter
- Distinction between retryable and non-retryable errors
- Comprehensive logging for debugging
- Configurable retry attempts and delays
"""

import time
import random
import logging
from functools import wraps
from typing import Callable, TypeVar, Any, Optional, Tuple, Type
from exceptions import LLMGenerationError, APIKeyError, ReasoningBankError

# Type variable for generic function return type
T = TypeVar('T')

# Configure logger
logger = logging.getLogger(__name__)


# HTTP status codes that are retryable (transient errors)
RETRYABLE_STATUS_CODES = {
    429,  # Too Many Requests (rate limit)
    500,  # Internal Server Error
    502,  # Bad Gateway
    503,  # Service Unavailable
    504,  # Gateway Timeout
}

# HTTP status codes that are NOT retryable (permanent errors)
NON_RETRYABLE_STATUS_CODES = {
    400,  # Bad Request
    401,  # Unauthorized (invalid API key)
    403,  # Forbidden
    404,  # Not Found
    422,  # Unprocessable Entity
}

# Exception types that should never be retried
NON_RETRYABLE_EXCEPTIONS = (
    APIKeyError,
    ValueError,
    TypeError,
    KeyError,
)


def is_retryable_error(exception: Exception) -> bool:
    """
    Determine if an error is retryable based on error type and status code.
    
    Retryable errors include:
    - Rate limits (429)
    - Server errors (500, 502, 503, 504)
    - Connection timeouts
    - Network errors
    
    Non-retryable errors include:
    - Invalid API keys (401)
    - Bad requests (400)
    - Not found (404)
    - Validation errors
    
    Args:
        exception: The exception to check
    
    Returns:
        True if the error should be retried, False otherwise
    """
    # Never retry certain exception types
    if isinstance(exception, NON_RETRYABLE_EXCEPTIONS):
        logger.debug(f"Non-retryable exception type: {type(exception).__name__}")
        return False
    
    # Check for status code in exception context
    if isinstance(exception, ReasoningBankError):
        status_code = exception.context.get('status_code')
        if status_code:
            if status_code in NON_RETRYABLE_STATUS_CODES:
                logger.debug(f"Non-retryable status code: {status_code}")
                return False
            if status_code in RETRYABLE_STATUS_CODES:
                logger.debug(f"Retryable status code: {status_code}")
                return True
    
    # Check for common retryable error patterns in message
    error_message = str(exception).lower()
    retryable_patterns = [
        'timeout',
        'connection',
        'rate limit',
        'too many requests',
        'server error',
        'service unavailable',
        'gateway',
    ]
    
    for pattern in retryable_patterns:
        if pattern in error_message:
            logger.debug(f"Retryable error pattern detected: {pattern}")
            return True
    
    # Default to non-retryable for unknown errors
    logger.debug(f"Unknown error type, treating as non-retryable: {type(exception).__name__}")
    return False


def exponential_backoff_with_jitter(
    attempt: int,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    jitter_factor: float = 0.25
) -> float:
    """
    Calculate delay for exponential backoff with jitter.
    
    The delay grows exponentially: base_delay * (2 ** attempt)
    Jitter is added to prevent thundering herd: ±jitter_factor of the delay
    
    Examples:
        attempt=0: ~1s (1.0 * 2^0 = 1.0)
        attempt=1: ~2s (1.0 * 2^1 = 2.0)
        attempt=2: ~4s (1.0 * 2^2 = 4.0)
        attempt=3: ~8s (1.0 * 2^3 = 8.0)
    
    Args:
        attempt: Current retry attempt number (0-indexed)
        base_delay: Base delay in seconds (default: 1.0)
        max_delay: Maximum delay in seconds (default: 60.0)
        jitter_factor: Jitter as fraction of delay (default: 0.25 = ±25%)
    
    Returns:
        Delay in seconds with jitter applied
    """
    # Calculate exponential delay
    delay = base_delay * (2 ** attempt)
    
    # Cap at maximum delay
    delay = min(delay, max_delay)
    
    # Add random jitter: ±jitter_factor of the delay
    # Example: if delay=4.0 and jitter_factor=0.25, jitter range is ±1.0
    jitter_range = delay * jitter_factor
    jitter = random.uniform(-jitter_range, jitter_range)
    
    final_delay = max(0.1, delay + jitter)  # Ensure minimum 0.1s delay
    
    logger.debug(
        f"Backoff calculation: attempt={attempt}, base={base_delay}s, "
        f"exponential={delay}s, jitter={jitter:.2f}s, final={final_delay:.2f}s"
    )
    
    return final_delay


def with_retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    retryable_exceptions: Optional[Tuple[Type[Exception], ...]] = None
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator for retrying functions with exponential backoff.
    
    Usage:
        @with_retry(max_retries=3, base_delay=1.0)
        def api_call():
            # Function that may fail transiently
            return make_request()
    
    Args:
        max_retries: Maximum number of retry attempts (default: 3)
        base_delay: Base delay for exponential backoff in seconds (default: 1.0)
        max_delay: Maximum delay between retries in seconds (default: 60.0)
        retryable_exceptions: Tuple of exception types to retry (default: all)
    
    Returns:
        Decorated function with retry logic
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception: Optional[Exception] = None
            
            for attempt in range(max_retries + 1):  # +1 for initial attempt
                try:
                    # Log attempt
                    if attempt == 0:
                        logger.debug(f"Executing {func.__name__}")
                    else:
                        logger.info(
                            f"Retry attempt {attempt}/{max_retries} for {func.__name__}"
                        )
                    
                    # Execute the function
                    result = func(*args, **kwargs)
                    
                    # Success - log if this was a retry
                    if attempt > 0:
                        logger.info(
                            f"✅ {func.__name__} succeeded after {attempt} retries"
                        )
                    
                    return result
                
                except Exception as e:
                    last_exception = e
                    
                    # Check if we should retry this exception
                    should_retry = is_retryable_error(e)
                    
                    # Check against custom retryable exceptions if provided
                    if retryable_exceptions and not isinstance(e, retryable_exceptions):
                        should_retry = False
                    
                    # Log the error
                    if should_retry and attempt < max_retries:
                        delay = exponential_backoff_with_jitter(
                            attempt, base_delay, max_delay
                        )
                        logger.warning(
                            f"⚠️  {func.__name__} failed with {type(e).__name__}: {str(e)[:100]}. "
                            f"Retrying in {delay:.2f}s (attempt {attempt + 1}/{max_retries})"
                        )
                        time.sleep(delay)
                    else:
                        # Non-retryable or out of retries
                        if not should_retry:
                            logger.error(
                                f"❌ {func.__name__} failed with non-retryable error: "
                                f"{type(e).__name__}: {str(e)[:100]}"
                            )
                        else:
                            logger.error(
                                f"❌ {func.__name__} failed after {max_retries} retries: "
                                f"{type(e).__name__}: {str(e)[:100]}"
                            )
                        raise
            
            # Should never reach here, but just in case
            if last_exception:
                raise last_exception
            
            raise RuntimeError(f"{func.__name__} failed without raising an exception")
        
        return wrapper
    
    return decorator


# Convenience decorators with preset configurations
def with_api_retry(func: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator for API calls with standard retry configuration.
    
    Uses 3 retries with 1s base delay and 60s max delay.
    
    Usage:
        @with_api_retry
        def call_openrouter_api():
            return requests.post(...)
    """
    return with_retry(max_retries=3, base_delay=1.0, max_delay=60.0)(func)


def with_database_retry(func: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator for database operations with retry configuration.
    
    Uses 2 retries with 0.5s base delay and 10s max delay.
    
    Usage:
        @with_database_retry
        def query_chromadb():
            return collection.query(...)
    """
    return with_retry(max_retries=2, base_delay=0.5, max_delay=10.0)(func)


if __name__ == "__main__":
    """Test retry logic with simulated failures"""
    
    # Configure logging for testing
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("=== Testing Retry Logic ===\n")
    
    # Test 1: Successful retry after transient failure
    print("Test 1: Transient failure (rate limit)")
    
    class Counter:
        def __init__(self):
            self.count = 0
    
    counter = Counter()
    
    @with_retry(max_retries=3, base_delay=0.5)
    def flaky_api_call():
        counter.count += 1
        if counter.count < 3:
            error = LLMGenerationError(
                "Rate limit exceeded",
                status_code=429
            )
            raise error
        return "Success!"
    
    try:
        result = flaky_api_call()
        print(f"✅ Result: {result}")
        print(f"   Succeeded after {counter.count} attempts\n")
    except Exception as e:
        print(f"❌ Failed: {e}\n")
    
    # Test 2: Non-retryable error (invalid API key)
    print("Test 2: Non-retryable error (invalid API key)")
    
    @with_retry(max_retries=3, base_delay=0.5)
    def invalid_api_key():
        raise APIKeyError("Invalid API key")
    
    try:
        invalid_api_key()
    except APIKeyError as e:
        print(f"✅ Correctly failed immediately: {e}\n")
    
    # Test 3: Exhausted retries
    print("Test 3: Exhausted retries")
    
    @with_retry(max_retries=2, base_delay=0.5)
    def always_fails():
        raise LLMGenerationError("Server error", status_code=500)
    
    try:
        always_fails()
    except LLMGenerationError as e:
        print(f"✅ Failed after exhausting retries: {e}\n")
    
    # Test 4: Exponential backoff calculation
    print("Test 4: Exponential backoff delays")
    for i in range(5):
        delay = exponential_backoff_with_jitter(i, base_delay=1.0)
        print(f"   Attempt {i}: {delay:.2f}s")
    
    print("\n=== All Tests Complete ===")
