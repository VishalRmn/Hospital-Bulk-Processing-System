"""Retry policy for handling transient failures."""

import asyncio
from typing import Callable, TypeVar, Any
from app.utils.constants import (
    DEFAULT_MAX_RETRIES,
    DEFAULT_RETRY_DELAYS,
    RETRYABLE_STATUS_CODES,
    NON_RETRYABLE_STATUS_CODES
)
from app.utils.exceptions import RetryableError, NonRetryableError
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

T = TypeVar('T')


class RetryPolicy:
    """Handles retry logic with exponential backoff for transient failures."""
    
    def __init__(
        self,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_delays: list = None
    ):
        """
        Initialize retry policy.
        
        Args:
            max_retries: Maximum number of retry attempts
            retry_delays: List of delays (in seconds) between retries
        """
        self.max_retries = max_retries
        self.retry_delays = retry_delays or DEFAULT_RETRY_DELAYS
    
    @staticmethod
    def is_retryable_error(exception: Exception) -> bool:
        """
        Determine if an error is retryable.
        
        Args:
            exception: Exception to check
            
        Returns:
            True if error is retryable (transient)
        """
        if isinstance(exception, NonRetryableError):
            return False
        
        if isinstance(exception, RetryableError):
            return True
        
        # Check for connection/timeout errors
        error_str = str(exception).lower()
        if any(keyword in error_str for keyword in ['timeout', 'connection', 'network']):
            return True
        
        return False
    
    @staticmethod
    def classify_http_error(status_code: int) -> bool:
        """
        Classify HTTP status code as retryable or not.
        
        Args:
            status_code: HTTP status code
            
        Returns:
            True if error is retryable
        """
        if status_code in RETRYABLE_STATUS_CODES:
            return True
        if status_code in NON_RETRYABLE_STATUS_CODES:
            return False
        
        # Default: 5xx errors are retryable, 4xx are not
        return status_code >= 500
    
    async def execute_with_retry(
        self,
        func: Callable[..., Any],
        *args,
        **kwargs
    ) -> Any:
        """
        Execute a function with retry logic.
        
        Args:
            func: Async function to execute
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function
            
        Returns:
            Function result
            
        Raises:
            NonRetryableError: If a permanent error occurs
            RetryableError: If all retry attempts are exhausted
        """
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                logger.debug(f"Attempt {attempt + 1}/{self.max_retries + 1} for {func.__name__}")
                result = await func(*args, **kwargs)
                if attempt > 0:
                    logger.info(f"Success on retry attempt {attempt + 1}")
                return result
            
            except (RetryableError, NonRetryableError) as e:
                last_exception = e
                
                if isinstance(e, NonRetryableError):
                    logger.error(f"Non-retryable error on attempt {attempt + 1}: {e.message}")
                    raise
                
                if attempt < self.max_retries:
                    delay = self.retry_delays[attempt] if attempt < len(self.retry_delays) else self.retry_delays[-1]
                    logger.warning(
                        f"Retryable error on attempt {attempt + 1}: {e.message}. "
                        f"Retrying in {delay}s..."
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"All {self.max_retries + 1} attempts exhausted")
                    raise
            
            except Exception as e:
                last_exception = e
                
                if self.is_retryable_error(e):
                    if attempt < self.max_retries:
                        delay = self.retry_delays[attempt] if attempt < len(self.retry_delays) else self.retry_delays[-1]
                        logger.warning(
                            f"Retryable error on attempt {attempt + 1}: {str(e)}. "
                            f"Retrying in {delay}s..."
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(f"All {self.max_retries + 1} attempts exhausted: {str(e)}")
                        raise RetryableError(str(e))
                else:
                    logger.error(f"Non-retryable error on attempt {attempt + 1}: {str(e)}")
                    raise NonRetryableError(str(e))
        
        if last_exception:
            raise last_exception
