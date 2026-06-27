"""Abstract repository interface for batch persistence."""

from abc import ABC, abstractmethod
from typing import Optional
from app.models.batch import Batch


class BatchRepository(ABC):
    """Abstract base class for batch repository implementations."""
    
    @abstractmethod
    async def save(self, batch: Batch) -> None:
        """
        Save a batch.
        
        Args:
            batch: Batch object to save
        """
        pass
    
    @abstractmethod
    async def get(self, batch_id: str) -> Optional[Batch]:
        """
        Retrieve a batch by ID.
        
        Args:
            batch_id: Batch ID
            
        Returns:
            Batch object or None if not found
        """
        pass
    
    @abstractmethod
    async def update(self, batch: Batch) -> None:
        """
        Update a batch.
        
        Args:
            batch: Batch object with updated data
        """
        pass
    
    @abstractmethod
    async def delete(self, batch_id: str) -> None:
        """
        Delete a batch.
        
        Args:
            batch_id: Batch ID to delete
        """
        pass
    
    @abstractmethod
    async def list_all(self) -> list:
        """
        List all batches.
        
        Returns:
            List of all Batch objects
        """
        pass
