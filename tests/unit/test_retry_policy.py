"""Unit tests for retry policy."""

import pytest
import asyncio
from app.services.retry_policy import RetryPolicy
from app.utils.exceptions import RetryableError, NonRetryableError


class TestRetryPolicy:
    """Test cases for RetryPolicy."""
    
    def test_classify_http_error_retryable(self):
        """Test classification of retryable HTTP errors."""
        assert RetryPolicy.classify_http_error(500) is True
        assert RetryPolicy.classify_http_error(502) is True
        assert RetryPolicy.classify_http_error(503) is True
        assert RetryPolicy.classify_http_error(504) is True
    
    def test_classify_http_error_non_retryable(self):
        """Test classification of non-retryable HTTP errors."""
        assert RetryPolicy.classify_http_error(400) is False
        assert RetryPolicy.classify_http_error(404) is False
        assert RetryPolicy.classify_http_error(409) is False
    
    def test_classify_http_error_other_5xx(self):
        """Test classification of other 5xx errors (retryable)."""
        assert RetryPolicy.classify_http_error(500) is True
        assert RetryPolicy.classify_http_error(505) is True
    
    def test_classify_http_error_other_4xx(self):
        """Test classification of other 4xx errors (non-retryable)."""
        assert RetryPolicy.classify_http_error(401) is False
        assert RetryPolicy.classify_http_error(403) is False
    
    def test_is_retryable_error_retryable(self):
        """Test identification of retryable errors."""
        error = RetryableError("Test error")
        assert RetryPolicy.is_retryable_error(error) is True
    
    def test_is_retryable_error_non_retryable(self):
        """Test identification of non-retryable errors."""
        error = NonRetryableError("Test error")
        assert RetryPolicy.is_retryable_error(error) is False
    
    def test_is_retryable_error_timeout(self):
        """Test identification of timeout errors (retryable)."""
        error = Exception("Request timeout")
        assert RetryPolicy.is_retryable_error(error) is True
    
    def test_is_retryable_error_connection(self):
        """Test identification of connection errors (retryable)."""
        error = Exception("Connection error")
        assert RetryPolicy.is_retryable_error(error) is True
    
    def test_is_retryable_error_other(self):
        """Test identification of other errors (non-retryable)."""
        error = Exception("Some other error")
        assert RetryPolicy.is_retryable_error(error) is False
    
    @pytest.mark.asyncio
    async def test_execute_with_retry_success_first_attempt(self):
        """Test successful execution on first attempt."""
        policy = RetryPolicy(max_retries=3)
        
        async def succeeds():
            return "success"
        
        result = await policy.execute_with_retry(succeeds)
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_execute_with_retry_success_after_retries(self):
        """Test successful execution after retries."""
        policy = RetryPolicy(max_retries=3, retry_delays=[0.01, 0.01, 0.01])
        
        attempt_count = 0
        
        async def fails_then_succeeds():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 2:
                raise RetryableError("Transient error")
            return "success"
        
        result = await policy.execute_with_retry(fails_then_succeeds)
        assert result == "success"
        assert attempt_count == 2
    
    @pytest.mark.asyncio
    async def test_execute_with_retry_non_retryable_error(self):
        """Test that non-retryable errors fail immediately."""
        policy = RetryPolicy(max_retries=3)
        
        attempt_count = 0
        
        async def fails_non_retryable():
            nonlocal attempt_count
            attempt_count += 1
            raise NonRetryableError("Permanent error")
        
        with pytest.raises(NonRetryableError):
            await policy.execute_with_retry(fails_non_retryable)
        
        # Should fail immediately, not retry
        assert attempt_count == 1
    
    @pytest.mark.asyncio
    async def test_execute_with_retry_exhausted(self):
        """Test that retries are exhausted after max attempts."""
        policy = RetryPolicy(max_retries=2, retry_delays=[0.01, 0.01])
        
        attempt_count = 0
        
        async def always_fails():
            nonlocal attempt_count
            attempt_count += 1
            raise RetryableError("Persistent error")
        
        with pytest.raises(RetryableError):
            await policy.execute_with_retry(always_fails)
        
        # Should attempt max_retries + 1 times
        assert attempt_count == 3
    
    def test_retry_delays(self):
        """Test custom retry delays."""
        delays = [0.1, 0.2, 0.3]
        policy = RetryPolicy(max_retries=3, retry_delays=delays)
        
        assert policy.retry_delays == delays
