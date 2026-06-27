"""Custom application exceptions."""


class HospitalAPIException(Exception):
    """Base exception for Hospital API related errors."""
    pass


class ValidationError(HospitalAPIException):
    """Raised when input validation fails."""
    
    def __init__(self, message, details=None):
        self.message = message
        self.details = details or []
        super().__init__(self.message)


class APIError(HospitalAPIException):
    """Raised when external API call fails."""
    
    def __init__(self, message, status_code=None, is_retryable=False):
        self.message = message
        self.status_code = status_code
        self.is_retryable = is_retryable
        super().__init__(self.message)


class RetryableError(APIError):
    """Raised when a transient error occurs (retryable)."""
    
    def __init__(self, message, status_code=None):
        super().__init__(message, status_code, is_retryable=True)


class NonRetryableError(APIError):
    """Raised when a permanent error occurs (non-retryable)."""
    
    def __init__(self, message, status_code=None):
        super().__init__(message, status_code, is_retryable=False)


class BatchProcessingError(HospitalAPIException):
    """Raised when batch processing fails."""
    pass


class RepositoryError(HospitalAPIException):
    """Raised when repository operations fail."""
    pass
