"""HTTP client for communicating with Hospital Directory API."""

import httpx
import asyncio
from typing import Optional, Dict, Any
from app.config import get_config
from app.services.retry_policy import RetryPolicy
from app.utils.exceptions import RetryableError, NonRetryableError, APIError
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class HospitalAPIClient:
    """Async HTTP client for Hospital Directory API."""
    
    def __init__(self, base_url: Optional[str] = None, retry_policy: Optional[RetryPolicy] = None):
        """
        Initialize Hospital API client.
        
        Args:
            base_url: Base URL for Hospital Directory API
            retry_policy: Retry policy for handling transient failures
        """
        config = get_config()
        self.base_url = base_url or config.HOSPITAL_API_URL
        self.timeout = config.REQUEST_TIMEOUT
        self.retry_policy = retry_policy or RetryPolicy()
        self.client = None
    
    async def __aenter__(self):
        """Context manager entry."""
        self.client = httpx.AsyncClient(timeout=self.timeout)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self.client:
            await self.client.aclose()
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make HTTP request to Hospital API.
        
        Args:
            method: HTTP method (GET, POST, PATCH, DELETE)
            endpoint: API endpoint path
            data: Request body data
            
        Returns:
            Response JSON
            
        Raises:
            RetryableError: If transient error occurs
            NonRetryableError: If permanent error occurs
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            logger.debug(f"Making {method} request to {url}")
            
            if not self.client:
                self.client = httpx.AsyncClient(timeout=self.timeout)
            
            response = await self.client.request(method, url, json=data)
            
            # Check for errors
            if response.status_code >= 400:
                error_msg = f"API error: {response.status_code}"
                try:
                    error_detail = response.json().get('detail', 'Unknown error')
                    error_msg = f"{error_msg} - {error_detail}"
                except:
                    pass
                
                # Determine if retryable
                if RetryPolicy.classify_http_error(response.status_code):
                    logger.warning(f"Retryable API error: {error_msg}")
                    raise RetryableError(error_msg, response.status_code)
                else:
                    logger.error(f"Non-retryable API error: {error_msg}")
                    raise NonRetryableError(error_msg, response.status_code)
            
            logger.debug(f"Request successful: {method} {endpoint}")
            return response.json()
        
        except (RetryableError, NonRetryableError):
            raise
        except httpx.TimeoutException as e:
            logger.warning(f"Request timeout: {str(e)}")
            raise RetryableError(f"Request timeout: {str(e)}")
        except httpx.ConnectError as e:
            logger.warning(f"Connection error: {str(e)}")
            raise RetryableError(f"Connection error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in API request: {str(e)}")
            raise APIError(f"Unexpected error: {str(e)}")
    
    async def create_hospital(
        self,
        name: str,
        address: str,
        phone: Optional[str] = None,
        batch_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a hospital record.
        
        Args:
            name: Hospital name
            address: Hospital address
            phone: Hospital phone (optional)
            batch_id: Batch ID for grouping hospitals
            
        Returns:
            Created hospital object
            
        Raises:
            RetryableError: If transient error occurs
            NonRetryableError: If permanent error occurs
        """
        payload = {
            'name': name,
            'address': address
        }
        
        if phone:
            payload['phone'] = phone
        
        if batch_id:
            payload['creation_batch_id'] = batch_id
        
        async def _create():
            return await self._make_request('POST', '/hospitals/', payload)
        
        return await self.retry_policy.execute_with_retry(_create)
    
    async def activate_batch(self, batch_id: str) -> Dict[str, Any]:
        """
        Activate all hospitals in a batch.
        
        Args:
            batch_id: Batch ID to activate
            
        Returns:
            Activation response
            
        Raises:
            RetryableError: If transient error occurs
            NonRetryableError: If permanent error occurs
        """
        async def _activate():
            return await self._make_request(
                'PATCH',
                f'/hospitals/batch/{batch_id}/activate'
            )
        
        return await self.retry_policy.execute_with_retry(_activate)
    
    async def get_batch(self, batch_id: str) -> Dict[str, Any]:
        """
        Get hospitals in a batch.
        
        Args:
            batch_id: Batch ID to retrieve
            
        Returns:
            Batch hospitals data
            
        Raises:
            RetryableError: If transient error occurs
            NonRetryableError: If permanent error occurs
        """
        async def _get():
            return await self._make_request('GET', f'/hospitals/batch/{batch_id}')
        
        return await self.retry_policy.execute_with_retry(_get)
    
    async def delete_batch(self, batch_id: str) -> Dict[str, Any]:
        """
        Delete all hospitals in a batch.
        
        Args:
            batch_id: Batch ID to delete
            
        Returns:
            Deletion response
            
        Raises:
            RetryableError: If transient error occurs
            NonRetryableError: If permanent error occurs
        """
        async def _delete():
            return await self._make_request('DELETE', f'/hospitals/batch/{batch_id}')
        
        return await self.retry_policy.execute_with_retry(_delete)
    
    async def close(self):
        """Close the HTTP client connection."""
        if self.client:
            await self.client.aclose()
